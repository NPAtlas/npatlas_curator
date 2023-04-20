import os


class Config(object):
    """
    Common configurations
    """

    DEBUG = True
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    REMEMBER_COOKIE_DURATION = 604800 # seven days

class DevelopmentConfig(Config):
    """
    Development configurations
    """

    # SQLALCHEMY_ECHO = True
    # LOGIN_DISABLED = True
    


class ProductionConfig(Config):
    """
    Production configurations
    """

    DEBUG = False

class TestingConfig(Config):
    """
    Testing configurations
    """

    TESTING = True
    REMEMBER_COOKIE_DURATION = 0 

app_config = {
    "default": DevelopmentConfig,
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}

DBSERVER = os.getenv("DBSERVER", "127.0.0.1")
DBUSER = os.getenv("DBUSER", "jvansan")
DBPASSWORD = os.getenv("DBPASSWORD", "jvansan")
DBPORT = os.getenv("DBPORT", "3306")
SECRET_KEY = os.urandom(24)
SQLALCHEMY_DATABASE_URI = (
    f"mysql+pymysql://{DBUSER}:{DBPASSWORD}@{DBSERVER}:{DBPORT}/npatlas_curation"
)
REDISSERVER = os.getenv("REDIS", "127.0.0.1")
REDIS_DATABASE_URI = "redis://{}:6379".format(REDISSERVER)
# THESE SHOULD NOT BE DEFAULTS
API_BASE_URL = os.getenv("API_BASE_URL")
API_USERNAME = os.getenv("API_USERNAME")
API_PASSWORD = os.getenv("API_PASSWORD")
API_CLIENT_ID = os.getenv("API_CLIENT_ID")
if not all([API_BASE_URL, API_USERNAME, API_PASSWORD, API_CLIENT_ID]):
    raise ValueError("Missing API configuration")
