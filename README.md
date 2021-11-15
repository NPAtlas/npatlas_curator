# NP Atlas Curator WEB APP EDITION

_Version 3.3.6_


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

### Development

For development purposes, a sandbox environment can be created in just a few
commands using Docker Compose. Make sure you're logged into the GitHub container
registry to be able to pull all the necessary images, following the instruction
[@ghcr.](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)


**First**, you will need to create and configure the appropiate environment
files (you should be able to copy+paste these):

1. flask.env
```bash
export FLASK_APP=run.py
export FLASK_CONFIG=development
export FLASK_ENV=development
export DBSERVER=mysql
export DBUSER=npatlas
export DBPASSWORD=npatlas
export REDIS=redis
export ATLAS_APIKEY=ATLAS_APIKEY
export API_BASE_URL=api/api/v1
export API_USERNAME=admin
export API_PASSWORD=admin
export API_CLIENT_ID=curator
```

2. mysql.env

```bash
export MYSQL_DATABASE=npatlas_curation
export MYSQL_USER=npatlas
export MYSQL_PASSWORD=npatlas
export MYSQL_ROOT_PASSWORD=ROOT_PASSWORD
```

3. api.env

```bash
export LOG_LEVEL=debug
export MODULE_NAME=atlas.main
export DATABASE_URL=postgresql://npatlas:npatlas@atlasdb/np_atlas_dev
export AUTH_DATABASE_URL=postgresql://npatlas:npatlas@atlasdb/authentication
export DEV_DEPLOYMENT=true
export REDIS_URL=redis
export API_ENDPOINT=/api/v1
export SECRET_KEY=TOPSECRET
export IP_RATELIMIT=10000
```

4. psql.env

```bash
export POSTGRES_USER=npatlas
export POSTGRES_PASSWORD=npatlas
```

**Second**, you need to create the necessary docker volumes to allow for
persistent data. You can skip this step if you don't want to preserve any data,
but you will need to alter the `docker-compose.dev.yml` file to specify
non-external volumes (simple commend out the `external: true` lines in the
volume block at the bottom of the file).

```bash
docker volume create psqldata
docker volume create mysqldata
docker volume create redisdata
```

**Third**, you can now spin up your development docker containers:

```bash
docker-compose -f docker-compose.dev.yml up -d
```

If you go to http://localhost you should see the NP Atlas Curator home page.

**Fourth**, you need to create admin users for both the curator app, and the NP
Atlas API. This also requires properly setting up *3 databases* (1 curator app,
2 for NP Atlas API)...

1. Curator App

I have created a convenience CLI in the Flask App for creating users, including admins:

```bash
# setup the flask DB tables for the first time
docker-compose -f docker-compose.dev.yml exec site flask db upgrade
# create admin user for curator app
docker-compose -f docker-compose.dev.yml exec site flask users create --username admin --password admin --email test@test.com --admin
```

2. NP Atlas API

Setting up the NP Atlas API requires loading a DB dump, adding an API Key to
Redis, and creating an authentication DB + API admin. You can skip the last step
of adding the API admin unless you need to test the Inserter functionality.
Make sure you have a SQL dump loaded into the `./data` directory.

```bash
# setup npatlas database
docker-compose -f docker-compose.dev.yml exec atlasdb psql -U npatlas -c 'create database np_atlas_dev' 
docker-compose -f docker-compose.dev.yml exec -T atlasdb psql -d np_atlas_dev -U npatlas < ./data/npatlas_dev.psql
docker-compose -f docker-compose.dev.yml exec atlasdb psql -U npatlas -c 'alter database np_atlas_dev set search_path to np_atlas,rdk,public;'
# setup authentication database
docker-compose -f docker-compose.dev.yml exec atlasdb psql -U npatlas -c 'create database authentication'
# last step here would be to add admin user, but I'm going to skip this as it's a bunch of extra work...
# setup apikey
docker-compose -f docker-compose.dev.yml exec redis redis-cli -n 0 SET ATLAS_APIKEY 0
# restart all the services to make sure things load properly
docker-compose -f docker-compose.dev.yml restart
```
