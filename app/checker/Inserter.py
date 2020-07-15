import datetime
import logging
import os
import json
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional
from urllib.parse import quote

from requests.exceptions import HTTPError

from app import config, db, models
from app.checker import schemas
from app.checker.ResolveEnum import ResolveEnum
from app.models import Dataset, Journal
from app.utils import atlas_api, oauth_session
from app.utils.Compound import Compound


class Action(str, Enum):
    INSERT = "insert"
    UPDATE = "update"


@dataclass
class ApiError:
    """
    Class for tracking errors during insertion/updating
    """

    action: Action
    original_data: Dict
    new_data: Dict
    api_response: str


class Inserter:
    """Inserter class interface"""

    def __init__(self, dataset_id: int, *args, **kwargs):
        self.dataset_id = dataset_id
        self.task = kwargs.get("celery_task", None)
        self.logger = kwargs.get("logger", self.default_logger())
        self.errors: List[ApiError] = []
        # Setup session with auth for insertion VIA API
        self._init_api_client()
        self._atlas_journals: List[str] = []

    @property
    def atlas_journals(self):
        if not self._atlas_journals:
            self._get_atlas_journals()
        return self._atlas_journals

    def _get_atlas_journals(self):
        self._atlas_journals = atlas_api.get_journals()

    def _init_api_client(self):
        self.client = oauth_session.get_oauth_session(client_id=None)
        self.client.fetch_token(
            token_url=config.API_BASE_URL + "/token",
            username=config.API_USERNAME,
            password=config.API_PASSWORD,
            client_id=config.API_CLIENT_ID,
            client_secret=config.SECRET_KEY,
        )

    def _api_call(
        self, endpoint: str, post_data: Dict, get_data: Dict, action: Action
    ) -> bool:
        """POST/PUT request to API admin with auth depending on action.
        Requires endpoint URL without BASE_URL and data as dict.
        Returns boolean of success status of API call.
        """
        if action == Action.INSERT:
            r = self.client.post(f"{config.API_BASE_URL}/{endpoint}", json=post_data)
        if action == Action.UPDATE:
            r = self.client.put(f"{config.API_BASE_URL}/{endpoint}", json=post_data)

        if not r.status_code == 200:
            self.logger.error(r.text)
            self.errors.append(
                ApiError(
                    action=action,
                    original_data=get_data,
                    new_data=post_data,
                    api_response=r.text,
                )
            )
            return False
        return True

    def update_status(self, current: int, total: int, status: str):
        if self.task:
            self.task.update_state(
                state="PROGRESS",
                meta={"current": current, "total": total, "status": status},
            )
        self.logger.info("PROGRESS: {}/{}\nStatus: {}".format(current, total, status))

    def run(self):
        dataset = Dataset.query.get(self.dataset_id)

        self.dataset_sanity_check(dataset)
        total = len(dataset.articles)
        self.update_status(0, total, "FIRING UP")

        # Iterate over checker_articles, double check the article is good
        # Add/update the data
        for idx, ds_article in enumerate(dataset.articles):
            # Skip over articles which are not completely curated/checked
            if (
                not ds_article.completed
                or ds_article.needs_work
                or not ds_article.is_nparticle
            ):
                self.logger.warning("Skipping article %d!", ds_article.id)
                continue

            self.update_status(idx, total, "RUNNING")

            c_article = ds_article.checker_article
            # Check if article is in Atlas
            try:
                atlas_ref = atlas_api.get_reference(doi=c_article.doi)
            except HTTPError:
                atlas_ref = None

            if not atlas_ref:
                self.logger.info("Adding Reference - %s", c_article.doi)
                success = self.new_reference(c_article)
            else:
                self.logger.info("Updating Reference %s", c_article.doi)
                success = self.update_reference(c_article, atlas_ref)

            # If Reference insertion success fails need to skip adding compounds
            if not success:
                self.logger.error(
                    "Reference %d failed to insert/update - skipping %d compounds.",
                    c_article.id,
                    len(ds_article.compounds),
                )
                continue

            # Iterate over compounds and add/update them
            # These functions also do association with origin + reference
            for ds_compound in ds_article.compounds:
                c_compound = ds_compound.checker_compound

                # Double check compound doesn't match Atlas without being handled
                if self.check_atlas_match(c_compound) and not c_compound.resolve:
                    self.logger.error("Found an uncaught match for a compound!")
                    self.logger.error("%s - %s", c_compound.name, c_compound.inchikey)
                    self.reject_dataset()

                # Assume new if no resolve enum value in DB
                resolve_id = c_compound.resolve or 1
                resolve = ResolveEnum(resolve_id)
                self.logger.debug("Resolving %s by %s-ing", c_compound.id, resolve.name)

                if resolve == ResolveEnum.NEW:
                    self.logger.info("Adding new compound: %s", c_compound.name)
                    self.new_compound(c_compound, c_article)

                elif resolve == ResolveEnum.KEEP:
                    self.logger.info("Keeping NP Atlas Compound %s", c_compound.name)
                    continue

                elif resolve == ResolveEnum.REPLACE or resolve == ResolveEnum.UPDATE:
                    self.logger.info("Replacing NPAID: %s", c_compound.npaid)
                    self.update_compound(c_compound, c_article)

                elif resolve == ResolveEnum.SYNONYM:
                    if not c_compound.npaid:
                        self.logger.error("Missing NPAID for synonym")
                        continue
                    self.logger.info(
                        "Adding synonym %s for %s", c_compound.name, c_compound.npaid
                    )
                    # TODO: Add implementation
                    # self._api_call("")

                else:  # Only possible if mis-handled reject during checking
                    self.logger.error(
                        "Dataset contains rejected compounds - "
                        + "There was an error in checker handling..."
                    )
                    self.reject_dataset()
        e_string = "No errors"
        if self.errors:
            e_string = json.dumps([e.asdict() for e in self.errors])
            self.logger.error(e_string)
            dataset.checker_dataset.errors = e_string
        dataset.checker_dataset.inserted = True
        commit()
        return e_string

    def new_compound(
        self, compound: models.CheckerCompound, reference: models.CheckerArticle
    ):
        """
        Add a new compound to the NP Atlas and associate origin with reference
        """
        data = schemas.CompoundIn(
            origin_doi=reference.doi,
            origin_taxon_id=compound.atlas_taxon_id,
            origin_species=compound.source_species,
            smiles=compound.smiles,
            name=compound.name,
        ).dict()
        self._api_call("compound/", post_data=data, get_data={}, action=Action.INSERT)

    def update_compound(
        self, compound: models.CheckerCompound, reference: models.CheckerArticle
    ):
        """
        Update compound in NP Atlas and associate origin with reference
        """
        if not compound.npaid:
            self.logger.error("Compound does not have an NPAID...")
            return
        atlas_compound = atlas_api.get_compound(npaid=compound.npaid)
        if not atlas_compound:
            self.logger.error("Compound NPAID does not exist in Atlas")
            return

        # Update the main compound details
        if atlas_compound.get("smiles") != compound.smiles:
            self._api_call(
                f"compound/{compound.npaid}/structure",
                post_data={"smiles": compound.smiles},
                get_data=atlas_compound,
                action=Action.UPDATE,
            )

        if atlas_compound.get("name") != compound.name:
            self._api_call(
                f"compound/{compound.npaid}/name",
                post_data={"name": compound.name},
                get_data=atlas_compound,
                action=Action.UPDATE,
            )

        # TODO: Fix Origin update logic
        if (
            atlas_compound.get("origin_organism", {}).get("taxon", {}).get("id")
            != compound.atlas_taxon_id
        ):
            self.errors.append(
                ApiError(
                    action=Action.UPDATE,
                    original_data=atlas_compound.get("origin_organism", {}).get(
                        "taxon", {}
                    ),
                    new_data={"atlas_taxon_id": compound.atlas_taxon_id},
                    api_response="",
                )
            )

    def check_atlas_match(self, inchikey):
        return any(atlas_api.search_inchikey(inchikey))

    def new_reference(self, article: models.CheckerArticle) -> bool:
        """
        Add a new article
        Returns boolean of success status
        """
        self.verify_journal(journal_title=article.journal)

        ref_in = schemas.ReferenceIn(
            doi=article.doi,
            abstract=article.abstract,
            pmid=article.pmid,
            authors=article.authors,
            title=article.title,
            journal=article.journal,
            year=article.year,
            volume=article.volume,
            issue=article.issue,
            pages=article.pages,
        )
        return self._api_call(
            "reference/", post_data=ref_in.dict(), get_data={}, action=Action.INSERT
        )

    def update_reference(self, article: models.CheckerArticle, atlas_ref: Dict) -> bool:
        """
        Update the articles data
        Returns boolean of success status
        """
        self.verify_journal(journal_title=article.journal)
        ref_in = schemas.ReferenceUpdate(
            pmid=article.pmid,
            authors=article.authors,
            title=article.title,
            journal=article.journal,
            year=article.year,
            volume=article.volume,
            issue=article.issue,
            pages=article.pages,
        ).dict()
        # Check if there are any real changes and skip if not
        if ref_in.items() <= atlas_ref.items():
            self.logger.debug("No changes detected - not updating article")
            return True
        else:
            self.logger.debug("Updating article")
            url_doi = quote(article.doi)
            return self._api_call(
                f"reference/{url_doi}",
                post_data=ref_in,
                get_data=atlas_ref,
                action=Action.UPDATE,
            )

    def verify_journal(self, journal_title: str):
        # Make sure journal is actually in Atlas DB
        if journal_title not in self.atlas_journals:
            self.logger.info(
                "Journal %s not in NP Atlas - adding the journal", journal_title
            )
            self._api_call(
                "reference/addJournal",
                post_data={"title": journal_title},
                get_data={},
                action=Action.INSERT,
            )
            # Refresh journal list after adding one
            self._get_atlas_journals()

    def dataset_sanity_check(self, dataset: models.Dataset):
        """
        Given a dataset from the Curator DB check several things
        0 Make sure not a training dataset and not already inserted
        1 Has the dataset been completed, standardized, and checked
        2 Are there any problems remaining for this dataset
        """
        if dataset.training or dataset.checker_dataset.inserted:
            self.reject_dataset()
        self.logger.debug("Passed First Sanity Check!")

        cdataset = dataset.checker_dataset
        dataset_ready = (
            dataset.completed and cdataset.standardized and cdataset.completed
        )
        if not dataset_ready:
            self.reject_dataset()
        self.logger.debug("Passed Second Sanity Check!")

        if dataset.problems:
            self.reject_dataset()
        self.logger.debug("Passed Third Sanity Check!")

    def reject_dataset(self):
        db.session.rollback()
        raise RuntimeError("Dataset is not ready for insertion")

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
        return logging.getLogger()


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
