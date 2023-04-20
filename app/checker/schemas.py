# IMPORTANT: THESE MODELS MUST MATCH NPATLAS_API SCHEMAS
# These were copied and trimmed from the repo
# Idea: Add CI Check to confirm?

from enum import Enum
from typing import Optional

from pydantic import BaseModel  # pylint: disable=no-name-in-module


class TaxonRanks(str, Enum):
    genus = "genus"
    family = "family"
    order = "order"
    class_ = "class"
    phylum = "phylum"
    kingdom = "kingdom"
    domain = "domain"


# Insertion Models
class ReferenceBase(BaseModel):
    pmid: Optional[int]
    authors: str = "N/A"
    title: str = "N/A"
    journal: str
    year: Optional[int]
    volume: Optional[str]
    issue: Optional[str]
    pages: Optional[str]
    # Hide until we start supporting patents
    # patent_number: Optional[str]


class ReferenceIn(ReferenceBase):
    doi: str
    abstract: Optional[str]


class ReferenceUpdate(ReferenceBase):
    pass


# Journal
class JournalBase(BaseModel):
    title: str


class JournalIn(JournalBase):
    pass


# Common Models
class StructureBase(BaseModel):
    smiles: str


class NameBase(BaseModel):
    name: str


class DoiBase(BaseModel):
    doi: str


# Isolations
class IsolationBase(BaseModel):
    origin_doi: str
    origin_taxon_id: int
    origin_species: str


class CompoundOrgUpdate(IsolationBase):
    pass


class CompoundIn(IsolationBase, StructureBase, NameBase):
    # Inherits props from Mixins
    pass


class CompoundNameUpdate(NameBase):
    # Inherits props from Base
    pass


# Structures
class CompoundStructure(StructureBase):
    pass


# Reassignments
class CompoundReassignmentBase(DoiBase, StructureBase):
    # Inherits props from Mixins
    pass


class CompoundReassignmentAdd(CompoundReassignmentBase):
    # Inherits props from Base
    current_structure: bool


class CompoundReassignmentUpdate(CompoundReassignmentBase):
    # Inherits props from Base
    structure_id: int

