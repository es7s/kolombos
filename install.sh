#!/usr/bin/bash

cd "$(dirname "$(readlink -f "$0")")" || exit 127
echo "INSTALLING KOLOMBO"  # @fixme temp
ln -fv -s "$(realpath run.sh)" "$HOME/bin/es7s/kolombo"
echo "DONE"
