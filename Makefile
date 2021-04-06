all: build-docker push

build-docker:
	docker build -t atlas_curator:3.2.1 .

push:
	docker tag atlas_curator:3.2.1 registry.jvansan.duckdns.org/atlas_curator:3.2.1
	docker push registry.jvansan.duckdns.org/atlas_curator:3.2.1

dev:
	dotenv -f flask.env run flask run