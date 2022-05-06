NAME := atlas_curator
# VERSION := $(shell git describe --tags)
VERSION := 3.3.7
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
