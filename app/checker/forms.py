from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    HiddenField,
    IntegerField,
    SelectField,
    StringField,
    SubmitField,
)
from wtforms.validators import DataRequired, Optional

from .schemas import TaxonRanks
from .validators import (
    DBSelectValidator,
    RankSelectValidator,
    SimpleValidator,
)


class ResolveBaseForm(FlaskForm):
    force = BooleanField("Force Data")
    submit = SubmitField("Submit Data")
    reject = SubmitField("Reject Article")


class SimpleStringForm(ResolveBaseForm):
    value = StringField(
        "Value", validators=[SimpleValidator()], render_kw={"autocomplete": "off"}
    )
    type_ = HiddenField("")


class SimpleIntForm(ResolveBaseForm):
    value = IntegerField(
        "Value", validators=[SimpleValidator()], render_kw={"autocomplete": "off"}
    )
    type_ = HiddenField("")


class JournalForm(ResolveBaseForm):
    value = HiddenField("")
    select = SelectField(
        "Select Option",
        choices=[("alt", "Alternative Journal"), ("new", "New Journal")],
        id="journalSelect",
    )
    new_journal_full = StringField("Add New Journal (Enter Full Journal Name)")
    new_journal_abbrev = StringField("Add New Journal (Enter Journal Abbrev)")
    alt_journal = StringField(
        "Add Alternative Journal (Select Correct Journal)",
        render_kw={"autocomplete": "on"},
    )


class AtlasJournalForm(ResolveBaseForm):
    value = HiddenField("")
    journal_title = StringField("Full title of Journal to be added to Atlas")


RANKS = [(x.value, x.value.capitalize()) for x in TaxonRanks]


class GenusForm(ResolveBaseForm):
    value = HiddenField("")
    select = SelectField(
        "Select Option",
        choices=[("alt", "Alternative Taxon"), ("new", "New Taxon")],
        id="genusSelect",
    )
    taxon_rank = SelectField(
        "Select Rank", choices=RANKS, validators=[RankSelectValidator()]
    )
    new_taxon_name = StringField("Add New Taxon Name")
    new_taxon_parent_id = IntegerField("Atlas API Parent Taxon ID", default=0)
    new_taxon_external_db = SelectField(
        "Select External DB",
        choices=[("lpsn", "LPSN"), ("mycobank", "Mycobank")],
        id="externalDbSelect",
        validators=[DBSelectValidator()],
    )
    new_taxon_external_id = StringField("External DB Taxon ID", default="0")
    alt_taxon_name = StringField(
        "Add Alternative Taxon Name (Select Correct Taxon)",
        render_kw={"autocomplete": "on"},
    )


COMPOUND_OPTIONS = [
    ("new", "New Compound"),
    ("replace", "Replace Atlas Compound"),
    ("keep", "Keep Atlas Compound"),
    ("needs_work", "Needs Work"),
    # ("synonym", "Add Compound Synonym"),
]


class CompoundForm(ResolveBaseForm):
    value = HiddenField("")
    select = SelectField(
        "Select Option:",
        choices=COMPOUND_OPTIONS,
        validators=[DataRequired()],
        id="compoundSelect",
    )
    npaid = IntegerField("Replace NPA ID:", validators=[Optional()])
    notes = StringField("Notes:")
