## kolombos       ## Control chars and ESC sequences visualizer
## (C) 2022       ## A. Shavykin <0.delameter@gmail.com>
##----------------##-------------------------------------------------------------
.ONESHELL:
.PHONY: help test

PROJECT_NAME = kolombos
PROJECT_NAME_PUBLIC = ${PROJECT_NAME}
PROJECT_NAME_PRIVATE = ${PROJECT_NAME}-delameter

include .env.dist
-include .env
export
VERSION ?= 0.0.0

BOLD   := $(shell tput -Txterm bold)
GREEN  := $(shell tput -Txterm setaf 2)
YELLOW := $(shell tput -Txterm setaf 3)
RESET  := $(shell tput -Txterm sgr0)


## Common commands

help:   ## Show this help
	@fgrep -h "##" $(MAKEFILE_LIST) | fgrep -v @fgrep | sed -Ee 's/^(##)\s*([^#]+)#*\s*(.*)/\1${YELLOW}\2${RESET}#\3/' -e 's/(.+):(#|\s)+(.+)/##   ${GREEN}\1${RESET}#\3/' | column -t -s '#'

prepare:  ## Prepare environment for module building
	pip3 install --upgrade build twine
	python3 -m venv venv
	. venv/bin/activate
	pip3 install -r requirements.txt

demolish-build:  ## Purge build output folders
	rm -f -v dist/* ${PROJECT_NAME_PUBLIC}.egg-info/* ${PROJECT_NAME_PRIVATE}.egg-info/*


## Testing / Pre-build

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

generate-legend: ## Update legend.ansi from the template
	@. venv/bin/activate
	PYTHONPATH=${PWD} python3 dev/generate_legend.py

test: ## Run tests
	@. venv/bin/activate
	python3 -s -m unittest -v

depends:  ## Build and display module dependency graph
	mkdir -p dev/diagrams
	pydeps ${PROJECT_NAME} --rmprefix ${PROJECT_NAME}. -o dev/diagrams/imports.svg
	pydeps ${PROJECT_NAME} --rmprefix ${PROJECT_NAME}. -o dev/diagrams/cycles.svg 	   --show-cycle                       --no-show
	pydeps ${PROJECT_NAME} --rmprefix ${PROJECT_NAME}. -o dev/diagrams/imports-ext.svg --pylib  --collapse-target-cluster --no-show


## Releasing (dev)

build-dev: ## Create new private build (<kolombos-delameter>)
build-dev: demolish-build
	sed -E -i "s/^name.+/name = ${PROJECT_NAME_PRIVATE}/" setup.cfg
	python3 -m build
	sed -E -i "s/^name.+/name = ${PROJECT_NAME_PUBLIC}/" setup.cfg

upload-dev: ## Upload last successful build to dev repo
	python3 -m twine upload --repository testpypi dist/* \
			-u ${PYPI_USERNAME} -p ${PYPI_PASSWORD_DEV} --verbose

install-dev: ## Install latest private build from dev repo
	pip install -i https://test.pypi.org/simple/ ${PROJECT_NAME_PRIVATE}==${VERSION}

install-dev-public: ## Install latest public build from dev repo
	pip install -i https://test.pypi.org/simple/ ${PROJECT_NAME_PUBLIC}==${VERSION}


## Releasing (PRIMARY)

build: ## Create new public build (<kolombos>)
build: demolish-build
	python3 -m build

upload: ## Upload last successful build to PRIMARY repo
	python3 -m twine upload dist/* -u ${PYPI_USERNAME} -p ${PYPI_PASSWORD} --verbose

install: ## Install latest public build from PRIMARY repo
	pip install ${PROJECT_NAME_PUBLIC}==${VERSION}


##-----------------------##-------------------------------------------------------------
## To install private    ## #
## build over public one:## #
# make build upload-dev install-dev-public :##
##                       ## #                                               (dont do that)
########################### #
