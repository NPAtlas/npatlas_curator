import os

DBSERVER = os.getenv("DBSERVER", "127.0.0.1")
SECRET_KEY = os.urandom(24)
SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://jvansan:jvansan@{DBSERVER}/npatlas_curation"
# THESE SHOULD NOT BE DEFAULTS
API_BASE_URL = os.getenv("API_BASE_URL")
API_USERNAME = os.getenv("API_USERNAME")
API_PASSWORD = os.getenv("API_PASSWORD")
API_CLIENT_ID = os.getenv("API_CLIENT_ID")
if not all([API_BASE_URL, API_USERNAME, API_PASSWORD, API_CLIENT_ID]):
    raise ValueError("Missing API configuration")
