from app import data
import json
from functools import wraps
from pathlib import Path

from flask import abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from pydantic import ValidationError

from .. import db
from ..data.forms import ArticleForm
from ..models import Article, Compound, Curator, Dataset
from . import admin, schemas
from .forms import CuratorForm, DatasetForm

HERE = Path(__file__).parent


def require_admin(func):
    """
    Decorator to prevent non-admins from accessing the page
    When in development environment this is ignored
    """

    @wraps(func)
    def decorated_function(*args, **kwargs):
        if not current_app.config.get("LOGIN_DISABLED", False):
            if not current_user.is_admin:
                abort(403)
        return func(*args, **kwargs)

    return decorated_function


@admin.route("/admin/datasets")
@login_required
@require_admin
def list_datasets():
    """
    List all datasets and give checker access
    """
    # Get page
    page = request.args.get("page", 1, type=int)

    datasets = Dataset.query.order_by(Dataset.id.desc()).paginate(page, 10, False)

    next_url = (
        url_for("admin.list_datasets", page=datasets.next_num)
        if datasets.has_next
        else None
    )
    prev_url = (
        url_for("admin.list_datasets", page=datasets.prev_num)
        if datasets.has_prev
        else None
    )

    return render_template(
        "admin/datasets.html",
        datasets=datasets,
        title="List Datasets",
        next_url=next_url,
        prev_url=prev_url,
    )


@admin.route("/admin/articles")
@login_required
@require_admin
def list_articles():
    """
    List all articles
    """
    page = request.args.get("page", 1, type=int)
    articles = Article.query.paginate(page, 10, False)

    next_url = (
        url_for("admin.list_articles", page=articles.next_num)
        if articles.has_next
        else None
    )
    prev_url = (
        url_for("admin.list_articles", page=articles.prev_num)
        if articles.has_prev
        else None
    )

    return render_template(
        "admin/articles/articles.html",
        articles=articles,
        title="All Articles",
        article_redirect=lambda x: url_for("admin.article", id=x),
        next_url=next_url,
        prev_url=prev_url,
    )


@admin.route("/admin/articles/article<int:id>", methods=["GET", "POST"])
@login_required
@require_admin
def article(id):
    """
    See article from admin perspective
    """
    # Get article from DB and populate form
    article = Article.query.get_or_404(id)

    form = ArticleForm(obj=article)

    if form.validate_on_submit():
        form.populate_obj(article)

        actual_cmpds = []
        for cmpd in form.compounds:
            cmpd_form = cmpd.form
            db_cmpd = None
            if cmpd_form.id.data:
                db_cmpd = Compound.query.get(cmpd_form.id.data)
            if not db_cmpd:
                db_cmpd = Compound()

            db_cmpd.name = cmpd_form.name.data
            db_cmpd.smiles = cmpd_form.smiles.data
            db_cmpd.source_organism = cmpd_form.source_organism.data
            db_cmpd.cid = cmpd_form.cid.data
            db_cmpd.csid = cmpd_form.csid.data
            db_cmpd.cbid = cmpd_form.cbid.data

            if not db_cmpd.id:
                db.session.add(db_cmpd)

            actual_cmpds.append(db_cmpd)

        article.compounds = actual_cmpds

        try:
            db.session.commit()
            flash("Data saved!")
        except:
            db.session.rollback()
            flash("Error sending data to database...")

        return redirect(url_for("admin.list_articles"))

    return render_template("data/article.html", title="Article", form=form)


@admin.route("/admin/curators")
@login_required
@require_admin
def list_curators():
    """
    List all curators
    """
    curators = Curator.query.all()

    return render_template(
        "admin/curators/curators.html",
        curators=curators,
        title="Curators",
        data_redirect=lambda x: url_for("data.curator_dashboard", cur_id=x),
    )


@admin.route("/admin/curators/add", methods=["GET", "POST"])
@login_required
@require_admin
def add_curator():
    """
    Add a curator to the database
    """
    add_curator = True
    form = CuratorForm()
    if form.validate_on_submit():
        curator = Curator(
            email=form.email.data,
            username=form.username.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            password=form.password.data,
        )
        try:
            db.session.add(curator)
            with HERE.joinpath("npatlas_training_set_v2.json").open() as f:
                data = json.load(f)
                ds = add_dataset_to_db(data, commit=False)
                ds.curator = curator
                ds.training = 2
            db.session.commit()
            flash(
                "You have successfully added a new curator.\nNote the password is {}".format(
                    form.password.data
                )
            )
        except:
            db.session.rollback()
            flash("Error: Curator already exists")

        return redirect(url_for("admin.list_curators"))

    return render_template(
        "admin/curators/curator.html",
        action="Add",
        add_curator=add_curator,
        form=form,
        title="Add Curator",
    )


@admin.route("/admin/curators/edit/<int:id>", methods=["GET", "POST"])
@login_required
@require_admin
def edit_curator(id):
    """
    Edit a curator to the database
    """
    add_curator = False

    curator = Curator.query.get_or_404(id)
    form = CuratorForm(obj=curator)
    if form.validate_on_submit():
        curator.email = form.email.data
        curator.username = form.username.data
        curator.first_name = form.first_name.data
        curator.last_name = form.last_name.data
        curator.password = form.password.data
        try:
            db.session.commit()
            flash(
                "You have successfully added a new curator.\nNote the password is {}".format(
                    form.password.data
                )
            )
        except:
            db.session.rollback()
            flash("Error: Curator data could not be edited.")

        return redirect(url_for("admin.list_curators"))

    form.email.data = curator.email
    form.username.data = curator.username
    form.first_name.data = curator.first_name
    form.last_name.data = curator.last_name

    return render_template(
        "admin/curators/curator.html",
        action="Edit",
        add_curator=add_curator,
        form=form,
        title="Edit Curator",
    )


@admin.route("/admin/datasets/edit/<int:id>", methods=["GET", "POST"])
@login_required
@require_admin
def edit_dataset(id):
    """
    Edit a dataset curator or instructions
    """
    dataset = Dataset.query.get_or_404(id)
    curators = Curator.query.order_by("id").all()
    form = DatasetForm(obj=dataset)
    form.curator_id.choices = [(c.id, c.full_name) for c in curators]

    if form.validate_on_submit():
        dataset.curator_id = form.curator_id.data
        dataset.instructions = form.instructions.data
        try:
            db.session.commit()
            flash("You have successfully editted the Dataset")
        except:
            db.session.rollback()
            flash("Error: could not edit Dataset")

        return redirect(url_for("admin.list_datasets"))

    form.instructions.data = dataset.instructions

    return render_template("admin/edit_dataset.html", form=form)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ("json")


def create_dataset_from_schema(dataset: schemas.Dataset) -> Dataset:
    """Compose Flask-Sqlachemy instances from schema"""
    ds = Dataset(instructions=dataset.instructions)
    for art in dataset.articles:
        art_dict = art.dict()
        art_compounds = art_dict.pop("compounds")
        compounds = [Compound(**c) for c in art_compounds]
        article = Article(**art_dict)
        article.compounds = compounds
        ds.articles.append(article)
    return ds


@admin.route("/admin/datasets/add/", methods=["GET", "POST"])
@login_required
@require_admin
def add_dataset():
    """
    Add a dataset by uploading JSON file
    """
    json_schema = schemas.Dataset.schema_json(indent=2)
    if request.method == "POST":
        if "file" not in request.files:
            flash("No file part")
            return redirect(request.url)
        file = request.files["file"]
        # if user does not select file, browser also
        # submit an empty part without filename
        if file.filename == "":
            flash("No selected file")
            return redirect(request.url)
        if file and allowed_file(file.filename):
            data = json.load(file.stream)
            try:
                ds = add_dataset_to_db(data, commit=True)
            except ValidationError as e:
                flash(f"Invalid JSON Error: {e.json()}")
                return redirect(request.url)
            except TypeError:
                flash("Invalid JSON Error: The base is not an Object.")
                return redirect(request.url)
            flash(f"Dataset added with {len(ds.articles)} articles!")
            return redirect(request.url)

    return render_template("admin/add_dataset.html", json_schema=json_schema)


def add_dataset_to_db(data, commit=False):
    ds_schema = schemas.Dataset(**data)
    ds = create_dataset_from_schema(ds_schema)
    db.session.add(ds)
    if commit:
        db.session.commit()
    return ds