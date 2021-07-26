from celery.utils.log import get_task_logger
from flask import (
    abort,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import login_required
from requests.exceptions import HTTPError, RequestException

from app import cache, celery, config, db
from app.admin.views import require_admin
from app.models import (
    AltJournal,
    Taxon,
    CheckerArticle,
    CheckerCompound,
    CheckerDataset,
    Dataset,
    Journal,
    Problem,
)
from app.utils import atlas_api, oauth_session
from app.utils.pubchem_smiles_standardizer import get_standardized_smiles

from . import checker
from .Checker import Checker
from .forms import (
    AtlasJournalForm,
    CompoundForm,
    GenusForm,
    JournalForm,
    SimpleIntForm,
    SimpleStringForm,
)
from .Inserter import Inserter
from .ResolveEnum import ResolveEnum

logger = get_task_logger(__name__)


#####################################################################
###                      CELERY TASKS                             ###
#####################################################################


@celery.task(bind=True)
def start_checker_task(self, dataset_id, standardize_compounds=False, restart=False):

    checker = Checker(dataset_id, celery_task=self, logger=logger)
    checker.run(standardize_compounds=standardize_compounds, restart=restart)
    result = "/admin/resolve/dataset{}".format(dataset_id)

    return {"current": 100, "total": 100, "status": "Task completed!", "result": result}


@celery.task
def standardize_dataset(ds_id):
    dataset = Dataset.query.get(ds_id)
    if dataset.checker_dataset:
        dataset.checker_dataset.standardized = False
    commit()
    run_standardization(ds_id)


@celery.task(bind=True)
def insert_dataset(self, dataset_id):
    inserter = Inserter(dataset_id, celery_task=self, logger=logger)
    result = inserter.run()

    return {"current": 100, "total": 100, "status": "Task completed!", "result": result}


#####################################################################
###                      FLASK VIEWS                              ###
#####################################################################


@checker.route("/insert/dataset<int:dataset_id>", methods=["POST"])
@login_required
@require_admin
def start_insert_dataset(dataset_id):
    task = insert_dataset.delay(dataset_id=dataset_id)

    return jsonify({"task_id": task.id}), 202


@checker.route("/insertstatus")
@login_required
@require_admin
def inserterstatus():
    task_id = request.args.get("taskid")
    task = insert_dataset.AsyncResult(task_id)

    if task.state == "PENDING":
        current_app.logger.debug("PENDING...")
        response = {
            "state": task.state,
            "current": 0,
            "total": 1,
            "status": "Pending...",
        }
    elif task.state != "FAILURE":
        current_app.logger.debug(
            "{}: {}/{} - {}".format(
                task.state,
                task.info.get("current", 0),
                task.info.get("total", 1),
                task.info.get("status", "Failed"),
            )
        )
        response = {
            "state": task.state,
            "current": task.info.get("current", 0),
            "total": task.info.get("total", 1),
            "status": task.info.get("status", "Failed..."),
        }
        if "result" in task.info:
            response["result"] = task.info["result"]
    else:
        response = {
            "state": task.state,
            "current": 1,
            "total": 1,
            "status": str(task.info),
        }

    return jsonify(response)


@checker.route("/standardize/dataset<int:dataset_id>", methods=["POST"])
@login_required
@require_admin
def startstandard(dataset_id):
    task = standardize_dataset.delay(ds_id=dataset_id)
    checker_dataset = CheckerDataset.query.filter_by(dataset_id=dataset_id).first()

    if not checker_dataset:
        checker_dataset = CheckerDataset(dataset_id=dataset_id, celery_task_id=task.id)
        db_add_commit(checker_dataset)

    else:
        checker_dataset.celery_task_id = task.id
        checker_dataset.standardized = False
        commit()

    return jsonify({"task_id": task.id}), 202


@checker.route("/standardstatus")
@login_required
@require_admin
def standard_status():
    task_id = request.args.get("taskid")
    task = standardize_dataset.AsyncResult(task_id)
    response = {"state": task.state}

    return jsonify(response)


@checker.route("/checkerstart/dataset<int:dataset_id>", methods=["POST"])
@login_required
@require_admin
def startchecker(dataset_id):
    standard = bool(request.args.get("standard", False))
    restart = bool(request.args.get("restart", False))

    current_app.logger.info(
        "Compound standardization is %s", "ON" if standard else "OFF"
    )
    checker_task = start_checker_task.delay(
        dataset_id=dataset_id, standardize_compounds=standard, restart=restart
    )
    checker_dataset = CheckerDataset.query.filter_by(dataset_id=dataset_id).first()

    if not checker_dataset:
        abort(404)
    checker_dataset.celery_task_id = checker_task.id
    checker_dataset.completed = False
    checker_dataset.running = True

    try:
        db.session.commit()
    except:
        db.session.rollback()
        flash("Error: database could not be reached")
        abort(400)

    return jsonify({"task_id": checker_task.id}), 202


@checker.route("/checkerstatus")
@login_required
def checkerstatus():
    task_id = request.args.get("taskid")
    if not task_id:
        abort(400)
    checker_task = start_checker_task.AsyncResult(task_id)

    if checker_task.state == "PENDING":
        current_app.logger.debug("PENDING...")
        response = {
            "state": checker_task.state,
            "current": 0,
            "total": 1,
            "status": "Pending...",
        }
    elif checker_task.state != "FAILURE":
        current_app.logger.debug(
            "{}: {}/{} - {}".format(
                checker_task.state,
                checker_task.info.get("current", 0),
                checker_task.info.get("total", 1),
                checker_task.info.get("status", "Failed"),
            )
        )
        response = {
            "state": checker_task.state,
            "current": checker_task.info.get("current", 0),
            "total": checker_task.info.get("total", 1),
            "status": checker_task.info.get("status", "Failed..."),
        }
        if "result" in checker_task.info:
            response["result"] = checker_task.info["result"]
    else:
        response = {
            "state": checker_task.state,
            "current": 1,
            "total": 1,
            "status": str(checker_task.info),
        }

    return jsonify(response)


@checker.route("/checkerrunning", methods=["GET"])
@login_required
def checkerrunning():
    ds_id = request.args.get("dsid")
    if not ds_id:
        abort(400)
    dataset = Dataset.query.get_or_404(ds_id)

    if dataset.standard_running():
        response = {
            "standard": True,
            "running": False,
            "complete": False,
            "task_id": dataset.checker_task_id(),
        }
    elif dataset.checker_running():
        response = {
            "standard": False,
            "running": True,
            "complete": False,
            "task_id": dataset.checker_task_id(),
        }
    elif (
        not dataset.standard_running()
        and not dataset.checker_completed()
        or dataset.inserted()
    ):
        response = {
            "standard": False,
            "running": False,
            "complete": False,
            "task_id": None,
        }
    elif dataset.checker_completed():
        response = {
            "standard": False,
            "running": False,
            "complete": True,
            "task_id": dataset.checker_task_id(),
        }
    else:
        response = {}

    return jsonify(response)


@checker.route("/admin/resolve/dataset<int:ds_id>")
@login_required
@require_admin
def problem_list(ds_id):
    problems = Problem.query.filter_by(dataset_id=ds_id).all()
    ds = Dataset.query.get_or_404(ds_id)
    inserted = ds.inserted()
    insert_errors = ds.insert_errors()
    return render_template(
        "checker/problems.html",
        ds_id=ds_id,
        problems=problems,
        inserted=inserted,
        insert_errors=insert_errors,
    )


@checker.route("/_search_journal")
def journal_autocomplete():
    search = request.args.get("search")
    current_app.logger.debug("Search = %s", search)
    journals = Journal.query.filter(
        db.or_(Journal.journal.like(search + "%"), Journal.abbrev.like(search + "%"))
    ).all()
    current_app.logger.debug(journals)

    return jsonify(results=[x.journal for x in journals])


@cache.cached(timeout=120)
def get_all_taxa():
    data = {}
    for rank in atlas_api.get_ranks():
        data[rank] = [
            x.get("original_name").lower() for x in atlas_api.get_rank_taxa(rank)
        ]
    return data


@checker.route("/_search_taxon")
def taxon_autocomplete():
    cached_taxa = get_all_taxa()
    search = request.args.get("search", "").lower()
    rank = request.args.get("rank")
    current_app.logger.debug("Search = %s", search)
    rank_data = cached_taxa.get(rank, [])
    return jsonify(results=[x.capitalize() for x in rank_data if x.startswith(search)])


@checker.route(
    "/admin/resolve/dataset<int:ds_id>/problem<int:prob_id>", methods=["GET", "POST"]
)
@login_required
@require_admin
def resolve_problem(ds_id, prob_id):

    # Get all the necessary data from the database
    problem = Problem.query.get_or_404(prob_id)
    article = CheckerArticle.query.get_or_404(problem.article_id)
    dataset = Dataset.query.get_or_404(ds_id)
    cur_id = problem.dataset.curator.id

    if problem.compound_id:
        compound = CheckerCompound.query.get_or_404(problem.compound_id)
    else:
        compound = None

    # Make sure problem is associated with this dataset
    if problem.dataset_id != ds_id:
        abort(404)

    # Get next problem for redirection
    current_problem_idx = dataset.problems.index(problem)
    next_problem_idx = current_problem_idx + 1
    if next_problem_idx == len(dataset.problems):
        next_problem_id = None
    else:
        next_problem_id = dataset.problems[next_problem_idx].id
    if current_problem_idx == 0:
        prev_problem_id = None
    else:
        prev_problem_id = dataset.problems[current_problem_idx - 1].id

    form = None
    npa_compounds = None
    if problem.problem == "journal":
        form = journal_form_factory(article)
    elif problem.problem == "missing_journal":
        form = atlas_journal_form_factory(article)
    elif problem.problem == "genus":
        form = genus_form_factory(compound)
    elif (
        problem.problem == "flat_match"
        or problem.problem == "duplicate"
        or problem.problem == "name_match"
        or problem.problem == "internal_duplicate"
    ):
        npa_compounds = get_npa_compounds(compound)
        form = compound_form_factory(article, compound)
        if compound.npaid:
            form.select.default = 1

    else:
        form = simple_problem_form_factory(problem, article)

    force = form.force.data
    if form.validate_on_submit() or force or (form.is_submitted() and form.reject.data):
        if form.reject.data:
            article.article.is_nparticle = False
            problem.resolved = True
            commit()
        else:
            if force:
                article.resolved = True

            # TODO: resolve this logic
            # This ensures that a replacement of an NPAID doesn't leave another
            # NPAID with a matching InchiKey
            #             if form.__class__.__name__ == "CompoundForm":
            #                 if form.select.data == "replace":
            #                     npa_match = [x for x in npa_compounds if x.npaid == form.npaid.data][0]
            #                     if npa_match.inchikey != compound.inchikey:
            #                         flash("You can't select that NPAID to replace!", category='danger')
            #                         flash_errors(form)
            #                         return render_template('checker/resolve.html', ds_id=ds_id,
            #                            problem=problem, article=article, form=form,
            #                            compound=compound, cur_id=cur_id,
            #                            npa_compounds=npa_compounds)
            # except:
            #     flash("Unknown error...")
            #     # abort(500)

            save_resolve_data(form, article, compound)
            problem.resolved = True
            commit()

        if next_problem_id:
            return redirect(
                url_for("checker.resolve_problem", ds_id=ds_id, prob_id=next_problem_id)
            )
        else:
            return redirect(url_for("checker.problem_list", ds_id=ds_id))

    else:
        flash_errors(form)

    next_problem_url = (
        url_for("checker.resolve_problem", ds_id=ds_id, prob_id=next_problem_id)
        if next_problem_id
        else None
    )
    prev_problem_url = (
        url_for("checker.resolve_problem", ds_id=ds_id, prob_id=prev_problem_id)
        if prev_problem_id
        else None
    )

    return render_template(
        "checker/resolve.html",
        ds_id=ds_id,
        problem=problem,
        article=article,
        form=form,
        compound=compound,
        cur_id=cur_id,
        npa_compounds=npa_compounds,
        next_problem_url=next_problem_url,
        prev_problem_url=prev_problem_url,
    )


#####################################################################
###                      HELPER FUNCTIONS                         ###
#####################################################################


def flash_errors(form):
    for field, errors in form.errors.items():
        for error in errors:
            flash(
                "Error in the %s field - %s" % (getattr(form, field).label.text, error),
                "danger",
            )


def simple_problem_form_factory(problem, article):
    if problem.problem == "year":
        form = create_numeric_form(article.year, problem.problem)
    elif problem.problem == "pmid":
        form = create_numeric_form(article.pmid, problem.problem)
    elif problem.problem == "doi":
        form = create_string_form(article.doi, problem.problem)
    elif problem.problem == "volume":
        form = create_string_form(article.volume, problem.problem)
    elif problem.problem == "issue":
        form = create_string_form(article.issue, problem.problem)
    elif problem.problem == "authors":
        form = create_string_form(article.authors, problem.problem)
    elif problem.problem == "title":
        form = create_string_form(article.title, problem.problem)
    elif problem.problem == "pages":
        form = create_string_form(article.pages, problem.problem)
    elif problem.problem == "abstract":
        form = create_string_form(article.abstract, problem.problem)
    return form


def create_numeric_form(value, type_):
    return SimpleIntForm(value=value, type_=type_)


def create_string_form(value, type_):
    return SimpleStringForm(value=value, type_=type_)


def journal_form_factory(article):
    return JournalForm(
        value=article.journal,
        new_journal_full=article.journal,
        alt_journal=article.journal,
    )


def atlas_journal_form_factory(article):
    return AtlasJournalForm(value=article.journal, journal_title=article.journal)


def genus_form_factory(compound):
    return GenusForm(
        value=compound.source_genus,
        new_genus_name=compound.source_genus,
        alt_genus_name=compound.source_genus,
    )


def compound_form_factory(article, compound):
    return CompoundForm(
        value=compound.id, notes=article.article.notes, npaid=compound.npaid
    )


class NPACompound(object):
    """
    Utility storage class for passing data to Jinja
    """

    def __init__(self, npaid, name, molblock, inchikey):
        self.npaid = npaid
        self.name = name
        self.molblock = molblock
        self.inchikey = inchikey


def get_npa_compounds(compound):
    compounds = []
    if compound.npaid:
        res = atlas_api.get_compound(compound.npaid)
        if res:
            compounds.append(
                NPACompound(
                    res.get("id"),
                    res.get("original_name"),
                    atlas_api.get_compound_molblock(compound.npaid),
                    res.get("inchikey"),
                )
            )

    struct_res = atlas_api.search_inchikey(compound.inchikey.split("-")[0])
    for r in struct_res:
        id_ = r.get("npaid")
        if id_ not in [x.npaid for x in compounds]:
            compounds.append(
                NPACompound(
                    id_,
                    r.get("original_name"),
                    atlas_api.get_compound_molblock(id_),
                    r.get("inchikey"),
                )
            )
    if compound.name != "Not named":
        name_res = atlas_api.search_name(compound.name)
        for r in name_res:
            id_ = r.get("npaid")
            if id_ not in [x.npaid for x in compounds]:
                compounds.append(
                    NPACompound(
                        id_,
                        r.get("original_name"),
                        atlas_api.get_compound_molblock(id_),
                        r.get("inchikey"),
                    )
                )
    return compounds


def save_resolve_data(form, article, compound):
    # Check form in simple classes
    # These changes are all article data
    if form.__class__.__name__ in ["SimpleIntForm", "SimpleStringForm"]:
        attribute = form.type_.data
        value = form.value.data or None
        setattr(article, attribute, value)

    # Check if journal class
    elif form.__class__.__name__ == "JournalForm":
        save_journal(form, article)

    # Check if atlas journal class
    elif form.__class__.__name__ == "AtlasJournalForm":
        save_atlas_journal(form, article)

    # Check if genus/taxon class
    elif form.__class__.__name__ == "GenusForm":
        save_taxon(form, compound)

    # Check if compound class
    elif form.__class__.__name__ == "CompoundForm":
        save_compound(form, article, compound)
    else:
        abort(500)


def save_journal(form, article):
    option = form.select.data
    if option == "alt":
        article.journal = form.alt_journal.data
        journal = Journal.query.filter_by(journal=article.journal).first()
        if not journal:
            abort(500)
        alt = AltJournal(
            altjournal=form.value.data.lower().replace(".", ""), journal=journal
        )
        db_add_commit(alt)

    elif option == "new":
        article.journal = form.new_journal_full.data
        new = Journal(
            journal=form.new_journal_full.data, abbrev=form.new_journal_abbrev.data
        )
        db_add_commit(new)

    else:
        abort(500)


def _get_atlas_api_client():
    client = oauth_session.get_oauth_session(client_id=None)
    client.fetch_token(
        token_url=config.API_BASE_URL + "/token",
        username=config.API_USERNAME,
        password=config.API_PASSWORD,
        client_id=config.API_CLIENT_ID,
        client_secret=config.SECRET_KEY,
    )
    return client


def save_atlas_journal(form, article):
    try:
        client = _get_atlas_api_client()
        r = client.post(
            f"{config.API_BASE_URL}/reference/addJournal",
            json={"title": form.journal_title.data},
        )
        r.raise_for_status()
    except HTTPError:
        abort(500)


def save_taxon(form, compound):
    data = form.data

    if data["select"] == "alt":
        try:
            tax = atlas_api.get_taxon(
                taxon=data["alt_taxon_name"], rank=data["taxon_rank"]
            )
        except HTTPError as e:
            flash(e)
            abort(500)
        alt = Taxon.query.filter(Taxon.atlas_taxon_id == tax["id"]).first()
        if not alt:
            alt = Taxon(taxon=tax["name"], atlas_taxon_id=tax["id"], alternatives="")
        alt.alternatives += f"@{data['value']}@"
        db_add_commit(alt)
    elif data["select"] == "new":
        post_data = {
            "name": data["new_taxon_name"],
            "parent_id": data["new_taxon_parent_id"],
            "taxon_db": data["new_taxon_external_db"],
            "external_id": data["new_taxon_external_id"],
            "rank": data["taxon_rank"],
        }
        try:
            client = _get_atlas_api_client()
            r = client.post(
                f"{config.API_BASE_URL}/taxon/",
                json=post_data,
            )
            r.raise_for_status()
        except Exception as e:
            flash(e)
            abort(500)
        compound.atlas_taxon_id = r.json()["id"]
        commit()
    else:
        flash("Invalid Taxon Form Option")
        abort(500)


def save_compound(form, article, compound):
    # Save new notes
    article.article.notes = form.notes.data

    # Handle the compounds
    option = form.select.data
    if option == "new":
        compound.resolve = ResolveEnum.NEW.value
    elif option == "replace":
        compound.npaid = form.npaid.data
        compound.resolve = ResolveEnum.REPLACE.value
    elif option == "keep":
        compound.resolve = ResolveEnum.KEEP.value
    # Hidden for now
    # elif option == "synonym":
    #     compound.npaid = form.npaid.data
    #     compound.resolve = ResolveEnum.SYNONYM.value
    elif option == "needs_work":
        article.article.needs_work = True
    else:
        flash(option)
        abort(500)

    commit()


def run_standardization(dataset_id):
    dataset = Dataset.query.get_or_404(dataset_id)
    for compound in dataset.get_compounds():
        smiles = compound.smiles
        try:
            compound.smiles = get_standardized_smiles(smiles)
            db.session.commit()
        except (ValueError, TypeError, RequestException):
            print("Error standardizing SMILES %s", smiles)
            db.session.rollback()
    dataset.checker_dataset.standardized = True
    try:
        commit()
    except:
        flash("Could not reach database!")
        abort(500)


def db_add_commit(db_object):
    db.session.add(db_object)
    commit()


def commit():
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e
