"""Utility functions accessing NP Atlas API"""
from os import getenv
from typing import Dict, List
from urllib.parse import quote

import requests

BASE_URL = "https://npatlas-dev.chem.sfu.ca/api/v1"

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


def search_inchikey(structure: str) -> List:
    r = requests.post(
        prefix_url(
            f"compounds/structureSearch?structure={structure}&type=inchikey&method=sim",
        ),
        headers=headers,
    )
    r.raise_for_status()
    return r.json()


def search_name(name: str) -> List:
    url_name = quote(name)
    r = requests.get(
        prefix_url(f"compounds/?name={url_name}&limit=10"), headers=headers
    )
    r.raise_for_status()
    return r.json()
