import pytest
from requests.exceptions import HTTPError
from app.utils import atlas_api


def test_get_compound():
    npaid = 1
    res = atlas_api.get_compound(npaid)
    assert isinstance(res, dict)
    assert res.get("npaid") == 1


def test_get_compound_bad():
    npaid = "NPAID"
    with pytest.raises(HTTPError):
        atlas_api.get_compound(npaid)


def test_search_inchikey_flat():
    flat_inchikey = "YPHMISFOHDHNIV"
    res = atlas_api.search_inchikey(flat_inchikey)
    assert len(res) > 0


def test_search_inchikey_full():
    inchikey = "YPHMISFOHDHNIV-LUTQBAROSA-N"
    res = atlas_api.search_inchikey(inchikey)
    assert len(res) > 0


def test_search_name():
    name = "Not named"
    res = atlas_api.search_name(name)
    assert len(res) > 0


def test_search_name_bad():
    name = "Not named!"
    res = atlas_api.search_name(name)
    assert len(res) == 0
