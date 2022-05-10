## kolombos       ## Control chars and ESC sequences visualizer
## (C) 2022       ## A. Shavykin <0.delameter@gmail.com>
##----------------##-------------------------------------------------------------
.ONESHELL:
.PHONY: help test

PROJECT_NAME = kolombos

include .env.dist
-include .env
export
VERSION ?= 0.0.0

## Common commands

BOLD   := $(shell tput -Txterm bold)
GREEN  := $(shell tput -Txterm setaf 2)
YELLOW := $(shell tput -Txterm setaf 3)
RESET  := $(shell tput -Txterm sgr0)

help:
	@fgrep -h "##" $(MAKEFILE_LIST) | fgrep -v @fgrep | sed -Ee 's/^##\s*([^#]+)#*\s*(.*)/${YELLOW}\1${RESET}#\2/' -e 's/(.+):(#|\s)+(.+)/##   ${GREEN}\1${RESET}#\3/' | column -t -s '#'

cleanup:
	rm -f -v dist/* ${PROJECT_NAME}.egg-info/*

prepare:
	pip3 install --upgrade build twine

init-venv:
	python3 -m venv venv
	. venv/bin/activate
	pip3 install -r requirements.txt

test: ## Run tests
test: init-venv
	. venv/bin/activate
	python3 -s -m unittest -v

set-version: ## Set new package version
	@echo "Current version: ${YELLOW}${VERSION}${RESET}"
	read -p "New version (press enter to keep current): " VERSION
	if [ -z $$VERSION ] ; then echo "No changes" && return 0 ; fi
	if [ ! -f .env ] ; then cp -u .env.dist .env ; fi
	sed -E -i "s/^VERSION.+/VERSION=$$VERSION/" .env
	sed -E -i "s/^VERSION.+/VERSION=$$VERSION/" .env.dist
	sed -E -i "s/^version.+/version = $$VERSION/" setup.cfg
	sed -E -i "s/^__version__.+/__version__ = '$$VERSION'/" ${PROJECT_NAME}/version.py
	echo "Updated version: ${GREEN}$$VERSION${RESET}"

generate-legend: ## Generate legend.ansi from template
generate-legend: init-venv
	. venv/bin/activate
	PYTHONPATH=${PWD} python3 dev/generate_legend.py

build: ## Build module
build: cleanup
	python3 -m build

## Test repository

upload-dev: ## Upload module to test repository
	python3 -m twine upload --repository testpypi dist/* -u ${PYPI_USERNAME} -p ${PYPI_PASSWORD}

install-dev: ## Install module from test repository
	pip install -i https://test.pypi.org/simple/ ${PROJECT_NAME}-delameter==${VERSION}

## Primary repository

upload: ## Upload module
	echo "upload"

install: ## Install module
	pip install ${PROJECT_NAME}==${VERSION}

##