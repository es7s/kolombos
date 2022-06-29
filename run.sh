#!/bin/bash
cd "$(dirname "$(readlink -f "$0")")" || exit 127

. venv/bin/activate
PYTHONPATH=${PWD} python3 -m kolombos "$@"
