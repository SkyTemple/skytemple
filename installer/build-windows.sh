#!/bin/sh

# Call with build-windows.sh [version number]
# The version from the current pip install of SkyTemple is used if no version number is set.
set -e

export XDG_DATA_DIRS="${BUILD_ROOT}/${MINGW}/share"

generate_version_file() {
  location=$(pip3 show $1 | grep Location | cut -d":" -f 2 | cut -c2-)
  pip3 show $1 | grep Version | cut -d":" -f 2 | cut -c2- > $location/$1/VERSION
}

rm build -rf || true
rm dist -rf || true

pip install python_igraph-*-mingw.whl
pip install py_desmume-*-mingw.whl
pip install skytemple_rust-*-mingw.whl
pip install tilequant-*-mingw.whl
pip3 install -r ../requirements-mac-windows.txt
pip3 install ..

# The VERSION files for a few dependencies are missing for some reason, so generate them from 'pip show' commands
generate_version_file cssselect2
generate_version_file tinycss2
generate_version_file cairosvg

pyinstaller skytemple.spec

# Remove unnecessary things
rm dist/skytemple/share/doc/* -rf
rm dist/skytemple/share/gtk-doc/* -rf
rm dist/skytemple/share/man/* -rf

# Write the version number to files that are read at runtime
version=$1 || $(python3 -c "import pkg_resources; print(pkg_resources.get_distribution(\"skytemple\").version)")

echo $version > dist/VERSION
