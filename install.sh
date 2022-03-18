#!/usr/bin/bash
cd "$(dirname "$(readlink -f "$0")")" || exit 127
echo "INSTALLING KOLOMBO"  # @fixme temp
ln -fv -s "$(realpath ./src/kolombo/app.py)" "$HOME/bin/es7s/kolombo"
echo "DONE"
