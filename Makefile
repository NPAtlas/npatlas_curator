NAME := atlas_curator
VERSION := $(shell poetry version --short)
REGISTRY := ghcr.io/npatlas

all: build-docker tag push

build-docker:
	docker build -t $(NAME):$(VERSION) .

tag:
	docker tag $(NAME):$(VERSION) $(REGISTRY)/$(NAME):$(VERSION)

push:
	docker push $(REGISTRY)/$(NAME):$(VERSION)

dev:
	dotenv -f flask.env run flask run

echo-name:
	echo $(REGISTRY)/$(NAME):$(VERSION)

poetryversion:
	poetry version $(version) 
	
# Use like `make version=VERSION version`
version: poetryversion
	$(eval NEW_VERS := $(shell cat pyproject.toml | grep "^version = \"*\"" | cut -d'"' -f2))
	sed -i "s/__version__ = .*/__version__ = \"$(NEW_VERS)\"/g" app/__init__.py
	sed -i "s|$(REGISTRY)/$(NAME)\:.*|$(REGISTRY)/$(NAME):$(NEW_VERS)|g" docker-compose.yml docker-compose.prod.yml