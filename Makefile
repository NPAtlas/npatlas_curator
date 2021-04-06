NAME := atlas_curator
# VERSION := $(shell git describe --tags)
VERSION := 3.2.1
REGISTRY := registry.jvansan.duckdns.org

all: build-docker push

build-docker:
	docker build -t $(NAME):$(VERSION) .

push:
	docker tag $(NAME):$(VERSION) $(REGISTRY)/$(NAME):$(VERSION)
	docker push $(REGISTRY)/$(NAME):$(VERSION)

dev:
	dotenv -f flask.env run flask run

echo-name:
	echo $(REGISTRY)/$(NAME):$(VERSION)
