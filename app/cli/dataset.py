"""Allow removing datasets from the database."""
import click
from flask import Blueprint

from .. import db
from ..models import Dataset

datasetbp = Blueprint("dataset", __name__)


@datasetbp.cli.command("list")
def list():
    """List all datasets in the database."""
    print("Listing all datasets:")
    for d in Dataset.query.all():
        print(
            f"ID: {d.id}, Curator: {d.curator.full_name if d.curator is not None else 'Unassigned'}, Description: {d.instructions} Completed: {d.completed}"
        )


@datasetbp.cli.command("reset")
@click.option("--dataset", required=True, help="Dataset id to remove")
def reset(dataset: int):
    """Reset checker dataset."""
    print(f"Removing dataset: {dataset}")
    d = Dataset.query.get(dataset)
    if d is None:
        print("Dataset not found!")
        return
    if d.checker_dataset is not None:
        db.session.delete(d.checker_dataset)
    db.session.commit()
    print("Successfully reset dataset!")


@datasetbp.cli.command("remove")
@click.option("--dataset", required=True, help="Dataset id to remove")
def remove(dataset: int):
    """Remove a dataset from the database."""
    print(f"Removing dataset: {dataset}")
    d = Dataset.query.get(dataset)
    if d is None:
        print("Dataset not found!")
        return
    db.session.delete(d)
    db.session.commit()
    print("Successfully removed dataset!")
