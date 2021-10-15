import click
from flask import Blueprint
from sqlalchemy import exc
from .. import db
from ..models import Curator

usersbp = Blueprint("users", __name__)


@usersbp.cli.command('create')
@click.option('--username', required=True)
@click.option('--email', required=True)
@click.option('--password', required=True)
@click.option('--first_name', default=None)
@click.option('--last_name', default=None)
@click.option('--admin', is_flag=True)
def create(username, email, password, first_name, last_name, admin):
    """ Creates a user """
    print(f"Creating user: {username} {email}")
    u = Curator(
        email=email,
        username=username,
        password=password,
        first_name=first_name,
        last_name=last_name,
        is_admin=admin,
    )
    db.session.add(u)
    db.session.commit()
    print("Successfully added user!")