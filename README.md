# NP Atlas Curator WEB APP EDITION

_Version 3.3.1_

## Changes

- Docker compose deployment
- Nginx -> Traefik reverse proxy
- Added Flower monitoring for Background tasks
- Migrate Checker/Inserter to NP Atlas API

### Deployment

Configure `docker-compose.yml` and `flask.env`, `mysql.env` as required then simply run `docker-compose up -d`.

**Example flask.env**

```
export FLASK_APP=run.py
export FLASK_CONFIG=development
export FLASK_ENV=development
export DBSERVER=mysql
export DBUSER=jvansan
export DBPASSWORD=<REPLACEME>
export REDIS=redis
export ATLAS_APIKEY=<REPLACEME>
export API_BASE_URL=<REPLACEME>
export API_USERNAME=admin
export API_PASSWORD=<REPLACEME>
export API_CLIENT_ID=curator
# Allow without SSL for dev
# export OAUTHLIB_INSECURE_TRANSPORT=1
# Enable Slack notifications
# export SLACK_WEBHOOK_URL=<REPLACE_ME>
```

**Example mysql.env**

```
MYSQL_DATABASE=npatlas_curation
MYSQL_USER=jvansan
MYSQL_PASSWORD=<REPLACEME>
MYSQL_ROOT_PASSWORD=<REPLACEME>
```

### Note

_Requires an Anaconda or Miniconda Python distribution in order to
install RDKit._
