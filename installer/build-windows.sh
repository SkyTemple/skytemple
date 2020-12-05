#!/bin/sh
export XDG_DATA_DIRS="${BUILD_ROOT}/${MINGW}/share"

generate_version_file() {
  location=$(pip3 show $1 | grep Location | cut -d":" -f 2 | cut -c2-)
  pip3 show $1 | grep Version | cut -d":" -f 2 | cut -c2- > $location/$1/VERSION
}

# The VERSION files for a few dependencies are missing for some reason, so generate them from 'pip show' commands
generate_version_file cssselect2
generate_version_file tinycss2
generate_version_file cairosvg

rm build -rf || true
rm dist -rf || true

pip install python_igraph-*-cp38-cp38-mingw.whl
pip install py_desmume-*-cp38-cp38-mingw.whl
pip install skytemple_rust-*-cp38-cp38-mingw.whl
pip install tilequant-*-cp38-cp38-mingw.whl
pip3 install -r ../requirements-mac-windows.txt
pip3 install ..

pyinstaller skytemple.spec

# Remove unnecessary things
rm dist/skytemple/share/doc/* -rf
rm dist/skytemple/share/gtk-doc/* -rf
rm dist/skytemple/share/man/* -rf

# Write the version number to files that are read at runtime
version=$1 || $(python3 -c "import pkg_resources; print(pkg_resources.get_distribution(\"skytemple\").version)")

echo $version > dist/VERSION
