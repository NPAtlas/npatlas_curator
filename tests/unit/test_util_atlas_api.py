from app.utils import atlas_api


def test_prefix_url():
    url = "compound/1"
    expected = "https://npatlas-dev.chem.sfu.ca/api/v1/compound/1"
    assert atlas_api.prefix_url(url) == expected
