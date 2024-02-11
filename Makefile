NAME := npatlas-curator
VERSION := $(shell poetry version --short)
REGISTRY := 697769791234.dkr.ecr.us-west-2.amazonaws.com

all: build-docker tag push


ecr-login:
	aws ecr get-login-password --region us-west-2 --profile sfu | docker login --username AWS --password-stdin $(REGISTRY)

build-docker:
	docker build --platform=linux/amd64 -t $(NAME):$(VERSION) .

tag:
	docker tag $(NAME):$(VERSION) $(REGISTRY)/$(NAME):$(VERSION)

push: ecr-login
	docker push $(REGISTRY)/$(NAME):$(VERSION)

dev:
	dotenv -f flask.env run flask run

echo-name:
	echo $(REGISTRY)/$(NAME):$(VERSION)

# Use like `make version`
update-version:
	$(eval NEW_VERS := $(shell cat pyproject.toml | grep "^version = \"*\"" | cut -d'"' -f2))
	sed -i '' -e "s/__version__ = .*/__version__ = \"$(NEW_VERS)\"/g" app/__init__.py
	sed -i '' -e "s|$(REGISTRY)/$(NAME)\:.*|$(REGISTRY)/$(NAME):$(NEW_VERS)|g" docker-compose.yml docker-compose.prod.yml