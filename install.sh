#!/usr/bin/bash

cd "$(dirname "$(readlink -f "$0")")" || exit 127
echo "INSTALLING KOLOMBO"  # @fixme temp

ln -fv -s "$(realpath run.sh)" "$HOME/bin/es7s/kolombo"
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
deactivate

echo "DONE"
