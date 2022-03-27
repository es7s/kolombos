## kolombo        ## Control chars and ESC sequences visualizer
## (C) 2022       ## A. Shavykin <0.delameter@gmail.com>
##----------------##-------------------------------------------------------------
.ONESHELL:
.PHONY: help

BOLD   := $(shell tput -Txterm bold)
GREEN  := $(shell tput -Txterm setaf 2)
YELLOW := $(shell tput -Txterm setaf 3)
RESET  := $(shell tput -Txterm sgr0)

include .env.dist
-include .env
export
VERSION ?= 0.0.0

## Common commands

help:
	@fgrep -h "##" $(MAKEFILE_LIST) | fgrep -v @fgrep | sed -Ee 's/^##\s*([^#]+)#*\s*(.*)/${YELLOW}\1${RESET}#\2/' -e 's/(.+):(#|\s)+(.+)/##   ${GREEN}\1${RESET}#\3/' | column -t -s '#'

cleanup:
	rm -f -v dist/*

set-version: ## set new package version
	@echo "Current version: ${YELLOW}${VERSION}${RESET}"
	read -p "New version (press enter to keep current): " VERSION
	if [ -z $$VERSION ] ; then echo "No changes" && return 0 ; fi
	if [ ! -f .env ] ; then cp -u .env.dist .env ; fi
	sed -E -i "s/^VERSION.+/VERSION=$$VERSION/" .env
	sed -E -i "s/^version.+/version = $$VERSION/" setup.cfg
	echo "Updated version: ${GREEN}$$VERSION${RESET}"

build: ## build module
	python3 -m build

## Deploying (dev)

upload-dev: ## upload module to test repository
	python3 -m twine upload --repository testpypi dist/* -u ${PYPI_USERNAME} -p ${PYPI_PASSWORD}

install-dev: ## install module from test repository
	pip install -i https://test.pypi.org/simple/ kolombo-delameter==${VERSION}

release-dev: ## build, upload and install using test repository
release-dev: cleanup build upload-dev install-dev

## Deploying (dist)

upload: ## upload module
	echo "upload"

install: ## install module
	echo "install"

release: ## build, upload and install module
release: cleanup build upload install

##
