import logging
import re
from typing import List

from app import db
from app.checker.NameString import NameString, decapitalize_first
from app.checker.ResolveEnum import ResolveEnum
from app.models import (
    CheckerArticle,
    CheckerCompound,
    CheckerDataset,
    Dataset,
    Journal,
    Problem,
    Retraction,
    Taxon,
)
from app.utils import atlas_api
from app.utils.Compound import Compound, inchikey_from_smiles


class Checker:
    def __init__(self, dataset_id, *args, **kwargs):
        self.dataset_id = dataset_id

        self.task = kwargs.get("celery_task", None)
        self.logger = kwargs.get("logger") or self.default_logger()

        self.review_list = []
        self.checked_compound_inchikeys = dict()
        self._journals = []

    @property
    def atlas_journals(self):
        """Memoized copy of Journal titles in Atlas"""
        if not self._journals:
            self._journals = atlas_api.get_journals()
        return self._journals

    def update_status(self, current, total, status):
        if self.task:
            self.task.update_state(
                state="PROGRESS",
                meta={"current": current, "total": total, "status": status},
            )
        self.logger.info("PROGRESS: {}/{}\nStatus: {}".format(current, total, status))

    def run(self, standardize_compounds=False, restart=False):
        self.logger.info("Setting up dataset")
        dataset = Dataset.query.get_or_404(self.dataset_id)
        total = len(dataset.articles)

        for i, article in enumerate(dataset.get_articles()):

            # Safely skip over previously retracted articles
            if self.check_reject_article(article):
                article.is_nparticle = False
                commit()

            # Skip over articles which are not properly curated
            if not article.completed or article.needs_work or not article.is_nparticle:
                self.logger.warning("Skipping article {}".format(article.id))
                continue

            check_art = self.create_checker_article(article, restart=restart)

            self.update_status(i, total, check_art.doi)
            self.check_article(check_art)

            for compound in article.compounds:
                check_compound = self.create_checker_compound(
                    compound, standardize=standardize_compounds, restart=restart
                )
                if (
                    check_compound.inchikey
                    not in self.checked_compound_inchikeys.keys()
                ):
                    self.checked_compound_inchikeys[check_compound.inchikey] = [
                        check_compound.id
                    ]
                else:
                    self.checked_compound_inchikeys[check_compound.inchikey].append(
                        check_compound.id
                    )
                self.check_compound(check_compound)
                # Add the checked list after checking complete

        self.logger.info("Done checking!")
        self.logger.info("There are %d problems to review", len(self.review_list))
        self.save_review_list()
        dataset.checker_dataset.completed = True
        dataset.checker_dataset.running = False
        commit()

    def save_review_list(self):
        Problem.query.filter_by(dataset_id=self.dataset_id).delete()
        commit()
        for corr in self.review_list:
            prob = Problem(
                dataset_id=self.dataset_id,
                problem=corr.problem,
                article_id=corr.article_id,
                compound_id=corr.compound_id,
            )

            db_add_commit(prob)

        self.logger.info("Saved %d problems to DB", len(self.review_list))

    def check_article(self, checker_article):
        if not checker_article.resolved:
            self.check_doi(checker_article)
            self.check_pmid(checker_article)
            self.check_journal(checker_article)
            self.check_year(checker_article)
            self.check_volume(checker_article)
            self.check_issue(checker_article)
            self.check_pages(checker_article)
            self.check_authors(checker_article)
            self.check_title(checker_article)
            self.check_abstract(checker_article)
            commit()

    def check_reject_article(self, article):
        return (
            bool(Retraction.query.filter_by(article_doi=article.doi).first())
            if article.doi
            else None
        )

    def check_compound(self, checker_compound):
        """
        Two main options:
         1 - This compound is already in the Atlas as has been recurated
            a -> checker_compound should have npaid
            b -> checker has restarted and problem is resolved ("resolve" not Null)
         2 - This a potentially new compound
        """
        if self.check_reject_compound(checker_compound):
            checker_compound.resolve = ResolveEnum.REJECT.value
            commit()

        # If this compound has been checked and resolve don't worry about it's structure
        if not checker_compound.resolve:
            # Check internally if compound has been seen before
            id_list = self.checked_compound_inchikeys.get(checker_compound.inchikey)
            if len(id_list) != 1:
                self.logger.error("Internal redundancy of compounds!")
                self.add_problem(
                    checker_compound.get_article_id(),
                    "internal_duplicate",
                    comp_id=checker_compound.id,
                )

            # Branch 2 - potentially new compound
            if not checker_compound.npaid:
                # Check if structure is a duplicate
                # First find connectivity matches
                if self.compound_flat_match(checker_compound):
                    if self.compound_full_match(checker_compound):
                        self.add_problem(
                            checker_compound.get_article_id(),
                            "duplicate",
                            comp_id=checker_compound.id,
                        )
                    # Impose strict verification for flat matches
                    # else:
                    #     self.add_problem(
                    #         checker_compound.get_article_id(),
                    #         "flat_match",
                    #         comp_id=checker_compound.id,
                    #     )
                # Check for name match (ignores "Not named")
                if self.compound_name_match(checker_compound):
                    self.add_problem(
                        checker_compound.get_article_id(),
                        "name_match",
                        comp_id=checker_compound.id,
                    )
            # Branch 1 - recurated compound
            # Only check if the structure has changed
            elif checker_compound.npaid:
                # Check if structure has changed
                if self.npaid_changed(checker_compound):
                    if self.compound_full_match(checker_compound):
                        self.add_problem(
                            checker_compound.get_article_id(),
                            "duplicate",
                            comp_id=checker_compound.id,
                        )
                    # Impose strict verification for flat matches
                    else:
                        self.add_problem(
                            checker_compound.get_article_id(),
                            "flat_match",
                            comp_id=checker_compound.id,
                        )
                else:
                    checker_compound.resolve = ResolveEnum.UPDATE.value

        self.check_source_organism(checker_compound)
        commit()

    def check_reject_compound(self, compound):
        res = Retraction.query.filter(
            Retraction.compound_inchikey == compound.inchikey
        ).all()
        if not res:
            res = Retraction.query.filter(
                Retraction.compound_name == compound.name
            ).all()
        return bool(res)

    @staticmethod
    def create_checker_article(article, standardize=False, restart=False):
        # Start fresh if not restarting
        if not restart:
            if article.checker_article:
                db.session.delete(article.checker_article)
                commit()
            check_art = CheckerArticle(
                id=article.id,
                pmid=article.pmid,
                doi=article.doi,
                npa_artid=article.npa_artid,
                journal=article.journal,
                year=article.year,
                volume=article.volume,
                issue=article.issue,
                pages=article.pages,
                authors=article.authors,
                title=article.title,
                abstract=article.abstract,
            )

            db_add_commit(check_art)
        else:
            check_art = article.checker_article

        return check_art

    def create_checker_compound(self, db_compound, standardize=False, restart=False):
        # If restarting check if anything was changed in the dataset
        restart_changed = False
        if (
            restart
            and db_compound.checker_compound
            and not db_compound.checker_compound.resolve
        ):
            if (
                inchikey_from_smiles(db_compound.smiles)
                != db_compound.checker_compound.inchikey
            ):
                self.logger.warning("Re-creating compound because structure changed!")
                restart_changed = True

        # Start fresh if not restarting
        if (db_compound.checker_compound and not restart) or restart_changed:
            db.session.delete(db_compound.checker_compound)
            commit()

        # Regularize the name
        # Especially important for "not named" or similar
        reg_name = NameString(db_compound.name)
        reg_name.regularize_name()

        # Currently not standardizing because it takes ~10x longer
        # compounds are pre-standardized
        reg_compound = Compound(
            db_compound.smiles, name=reg_name.get_name(), standardize=standardize
        )
        reg_compound.cleanStructure()

        genus, species = split_source_organism(db_compound.source_organism)
        if not restart or restart_changed:
            check_compound = CheckerCompound(
                id=db_compound.id,
                name=reg_name.get_name(),
                formula=reg_compound.formula,
                smiles=reg_compound.smiles,
                inchi=reg_compound.inchi,
                inchikey=reg_compound.inchikey,
                molblock=reg_compound.molblock,
                source_genus=genus,
                source_species=species,
                npaid=db_compound.npaid,
            )

            db_add_commit(check_compound)
        else:
            check_compound = db_compound.checker_compound

        return check_compound

    def default_logger(self, *args, **kwargs):
        """Logging util function

        Parameters
        ----------
        worker : str
            Description of worker
        level : logging.LEVEL, optional
            Default to INFO logging, set to log.DEBUG for development
        """
        level = kwargs.get("level", "INFO")
        logging.basicConfig(
            format="%(levelname)s: %(message)s", level=logging.getLevelName(level)
        )

    def add_problem(self, art_id, problem, comp_id=None):
        self.review_list.append(Correction(art_id, problem, comp_id))

    ## Start Checker Rules
    def check_doi(self, checker_article):
        regexp = re.compile(r"^(10.\d{4,9})\/([-._;()/:+A-Za-z0-9]+)$")
        if checker_article.doi:
            # if re.search(r'^(http|dx|doi)', checker_article.doi):
            checker_article.doi = clean_doi(checker_article.doi)
            match = regexp.match(checker_article.doi)
            if not match:
                self.add_problem(checker_article.id, "doi")
        else:
            self.add_problem(checker_article.id, "missing_doi")

    def check_pmid(self, checker_article):
        # Make sure integer
        # This is enforced by datatype in DB
        pass

    def check_journal(self, checker_article):
        journal = Journal.check_journal_match(checker_article.journal)
        if journal:
            checker_article.journal = journal.journal
            checker_article.journal_abbrev = journal.abbrev
            if not journal.journal in self.atlas_journals:
                self.add_problem(checker_article.id, "missing_journal")
        else:
            self.add_problem(checker_article.id, "journal")

    def check_year(self, checker_article):
        # Make sure year string is valid
        match = re.match("^[1-2][0-9]{3}$", str(checker_article.year))
        if not match:
            self.add_problem(checker_article.id, "year")

    def check_volume(self, checker_article):
        # > 6 characters or special characters FLAG
        if checker_article.volume:
            if len(checker_article.volume) > 6:
                self.add_problem(checker_article.id, "volume")

    def check_issue(self, checker_article):
        # > 6 characters or special characters FLAG
        if checker_article.issue:
            if len(checker_article.issue) > 6:
                self.add_problem(checker_article.id, "issue")

    def check_pages(self, checker_article):
        # only first pages #s INT < 100,000
        # INT-INT
        # or alphabetical characters
        # Watchout for en dash and em dash
        pages = checker_article.pages
        if pages:
            pages = re.sub(u"\u2013|\u2014", "-", pages)
            if re.search("^[0-9]", pages):
                res = [x.strip() for x in pages.split("-") if x]
                res = clean_num_pages(res)
                # Add problem if any string is greater than 6 characters
                if [x for x in res if len(x) > 6]:
                    self.add_problem(checker_article.id, "pages")
                else:
                    checker_article.pages = "-".join(res)
            elif re.search("^[A-Za-z]", pages):
                # Do nothing for now
                # max length = 10
                pass
            else:
                # Check pages if they don't start with Alphanumeric char
                self.add_problem(checker_article.id, "pages")

    def check_authors(self, checker_article):
        # at least 6 char, no numbers
        if len(checker_article.authors) < 6 or has_numbers(checker_article.authors):
            self.add_problem(checker_article.id, "authors")

    def check_title(self, checker_article):
        # at least > 6 char
        if len(checker_article.title) < 6:
            self.add_problem(checker_article.id, "title")

    def check_abstract(self, checker_article):
        # If abstract, should be min 20 char
        # Probably should be more!
        # "No abstract" is common
        if checker_article.abstract:
            if len(checker_article.abstract) < 20:
                self.add_problem(checker_article.id, "abstract")

    def check_source_organism(self, checker_compound):
        taxa = atlas_api.search_taxa(checker_compound.source_genus)
        if len(taxa) == 1:
            checker_compound.atlas_taxon_id = taxa[0]["id"]
        elif len(taxa) > 1:
            self.add_problem(
                checker_compound.get_article_id(),
                "mutliple_taxa",
                comp_id=checker_compound.id,
            )
        else:
            tax = Taxon.search_alternatives(checker_compound.source_genus)
            if tax:
                checker_compound.atlas_taxon_id = tax.atlas_taxon_id
            else:
                self.add_problem(
                    checker_compound.get_article_id(),
                    "genus",
                    comp_id=checker_compound.id,
                )

    def compound_flat_match(self, compound):
        """
        Query NP Atlas API to see if there is a flat match
        Return boolean match
        """
        res = atlas_api.search_inchikey(compound.inchikey.split("-")[0])
        return bool(res)

    def compound_full_match(self, compound):
        """
        Query NP Atlas API to see if there is a full match
        Return boolean match
        """
        res = atlas_api.search_inchikey(compound.inchikey)
        return bool(res)

    def compound_name_match(self, compound):
        """
        Query NP Atlas DB to see if there is a name match
        Return boolean match
        """
        res = None
        if compound.name != "Not named":
            res = atlas_api.search_name(compound.name)
        return bool(res)

    def npaid_changed(self, compound):
        """
        Query NP Atlas DB to see if a compound has changed in
        structure
        Return boolean
        """
        changed = True
        if compound.npaid:
            res = atlas_api.get_compound(compound.npaid)
            changed = compound.inchikey != res.get("inchikey")
        return changed


class Correction(object):
    """
    Object to store data which needs review
    """

    def __init__(self, art_id, problem, comp_id=None):
        self.verify_problem(problem)
        self.article_id = art_id
        self.compound_id = comp_id
        self.problem = problem

    def __repr__(self):
        return "{}: {} -> {}".format(self.article_id, self.compound_id, self.problem)

    @staticmethod
    def verify_problem(problem):
        # fmt: off
        assert (
            problem == "doi"                    # DOI formatting
            or problem == "missing_doi"         # No DOI present
            or problem == "pmid"                # PMID formatting
            or problem == "journal"             # Journal not in Checker
            or problem == "missing_journal"     # Journal not in Atlas
            or problem == "year"                # Year formatting
            or problem == "volume"              # Volume formatting
            or problem == "issue"               # Issue formatting
            or problem == "authors"             # Author string formatting
            or problem == "title"               # Title formatting
            or problem == "pages"               # Page formatting
            or problem == "abstract"            # Abstract formatting
            or problem == "duplicate"           # Duplicate entry to Atlas
            or problem == "flat_match"          # Flat match entry with Atlas
            or problem == "genus"               # TODO
            or problem == "mutliple_taxa"       # TODO
            or problem == "name_match"          # Name matches Atlas
            or problem == "internal_duplicate"  # Internal dataset InChIKey duplicate
        )
        # fmt: on


# =============================================================================
# ==========                Helper functions                      =============
# =============================================================================


def db_add_commit(db_object):
    db.session.add(db_object)
    commit()


def commit():
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e


def clean_doi(doi):
    regexp = re.compile("(https?://)(dx.)?doi.org/")
    return regexp.sub("", doi).strip()


def clean_num_pages(page_list):
    """
    Try to expand page numbers so that 100-10 -> 100-110
    """
    if len(page_list) == 2:
        if len(page_list[1]) < len(page_list[0]):
            plen = len(page_list[0]) - len(page_list[1])
            page_list[1] = page_list[0][0:plen] + page_list[1]
    return page_list


def has_numbers(input_string):
    return any(char.isdigit() for char in input_string)


def split_source_organism(org_string):
    org_string = org_string.strip()
    data = [x for x in org_string.split(" ") if x]
    # Check data makes sense
    if len(data) > 1:
        if data[0] in ["Unknown", "unknown"]:
            genus_index = 2
        else:
            genus_index = 1
        genus = "-".join(data[:genus_index])
        try:
            species = " ".join(data[genus_index:])
        except IndexError:
            species = "sp."
        if not species:
            species = "sp."
        species = clean_species(species)
    else:
        genus = data[0]
        species = "sp."
    return genus, species


def clean_species(species_string):
    species_string = decapitalize_first(species_string)
    # species_string = re.sub("^(?!sp.)sp$", "sp.", species_string)
    return re.sub(
        r"\b(sp|sps|sps\.|spp\.|spp)(?!\S)", "sp.", species_string, re.IGNORECASE
    )
