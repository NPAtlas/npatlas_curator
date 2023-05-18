from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo


class CuratorForm(FlaskForm):
    """
    For admin to add or edit curator
    """

    email = StringField("Email", validators=[DataRequired(), Email()])
    username = StringField("Username", validators=[DataRequired()])
    first_name = StringField("First name")
    last_name = StringField("Last name")
    password = StringField(
        "Password", validators=[DataRequired(), EqualTo("confirm_password")]
    )
    confirm_password = StringField("Confirm Password")
    submit = SubmitField("Submit Curator")


class DatasetForm(FlaskForm):
    """
    For admin to edit / assign datasets
    """

    instructions = StringField("Instructions")
    curator_id = SelectField("Curator", coerce=int, validate_choice=False)
    submit = SubmitField("Submit Dataset")


class DatasetDeleteForm(FlaskForm):
    """
    For admin to delete dataset
    """
    submit = SubmitField("Delete Dataset")
