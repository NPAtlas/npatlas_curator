from oauthlib.oauth2 import LegacyApplicationClient
from requests_oauthlib import OAuth2Session


def get_oauth_session(client_id: str) -> OAuth2Session:
    return OAuth2Session(client=LegacyApplicationClient(client_id=client_id))
