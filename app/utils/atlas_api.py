"""Utility functions accessing NP Atlas API"""
from os import getenv
from typing import Dict, List
from urllib.parse import quote

import requests

BASE_URL = getenv("API_BASE_URL", "http://localhost/api/v1")
APIKEY = getenv("ATLAS_APIKEY")
if APIKEY:
    headers = {"X-Api-Key": APIKEY}
else:
    headers = {}


def prefix_url(url):
    return f"{BASE_URL}/{url}"


def get_compound(npaid: int) -> Dict:
    r = requests.get(prefix_url(f"compound/{npaid}"), headers=headers)
    r.raise_for_status()
    return r.json()


def get_compound_molblock(npaid: int) -> str:
    r = requests.get(prefix_url(f"compound/{npaid}/mol?encode=file"), headers=headers)
    r.raise_for_status()
    return r.text


def search_inchikey(structure: str) -> List[Dict]:
    r = requests.post(
        prefix_url(
            f"compounds/structureSearch?structure={structure}&type=inchikey&method=sim",
        ),
        headers=headers,
    )
    return r.json()


def search_name(name: str) -> List[str]:
    url_name = quote(name)
    r = requests.get(
        prefix_url(f"compounds/?name={url_name}&limit=10"), headers=headers
    )
    return r.json()


def get_reference(doi: str) -> Dict:
    url_doi = quote(doi)
    r = requests.get(prefix_url(f"reference/{url_doi}"), headers=headers)
    r.raise_for_status()
    return r.json()


def get_journals() -> List[str]:
    r = requests.get(prefix_url("reference/journals"), headers=headers)
    r.raise_for_status()
    return r.json()


def search_taxa(taxon: str) -> List[Dict]:
    taxon = taxon.strip()
    r = requests.post(
        prefix_url("taxon/search") + f"?taxon={taxon}&rank=all", headers=headers
    )
    return r.json()


def get_ranks() -> List[str]:
    r = requests.get(prefix_url("taxon/"), headers=headers)
    return r.json()


def get_rank_taxa(rank: str) -> List[str]:
    r = requests.get(prefix_url(f"taxon/{rank}/"), headers=headers)
    return r.json()


def get_taxon(taxon: str, rank: str) -> Dict:
    r = requests.get(prefix_url(f"taxon/{rank}/{taxon}"), headers=headers)
    r.raise_for_status()
    return r.json()
