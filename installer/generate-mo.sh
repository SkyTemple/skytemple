#!/usr/bin/env bash
set -e
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

find $SCRIPT_DIR/../skytemple/data/locale -iname "*.po" -exec sh -c 'msgfmt -o "${1%.po}.mo" "$1"' sh {} \;
