from typing import List, Optional
from pydantic import BaseModel, Extra


class Compound(BaseModel, extra=Extra.forbid):
    name: str
    smiles: str
    source_organism: Optional[str]


class BaseArticle(BaseModel, extra=Extra.forbid):
    doi: Optional[str]
    pmid: Optional[int]
    journal: Optional[str]
    year: Optional[str]
    volume: Optional[str]
    issue: Optional[str]
    pages: Optional[str]
    title: Optional[str]
    authors: Optional[str]
    abstract: Optional[str]


class Article(BaseArticle):
    compounds: List[Compound]
    notes: Optional[str]


class Dataset(BaseModel, extra=Extra.forbid):
    instructions: Optional[str]
    articles: List[Article]