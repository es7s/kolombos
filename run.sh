#!/usr/bin/bash

path="$(dirname "$(readlink -f "$0")")"
export PYTHONPATH="$path"
"$path"/venv/bin/python -m kolombo "$@"
