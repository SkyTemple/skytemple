#!/bin/sh

# Call with "PACKAGE_VERSION=[version number] ./build-windows.sh"
# The version from the current pip install of SkyTemple is used if no version number is set.
set -e

export XDG_DATA_DIRS="${BUILD_ROOT}/${MINGW}/share"

rm build -rf || true
rm dist -rf || true

# Dummy python-igraph package to force not trying to install it (it has been renamed to igraph.)
pip3 install python_igraph*.whl
pip3 install igraph-*-mingw*.whl
pip3 install py_desmume-*-mingw*.whl
pip3 install tilequant-*-mingw*.whl
# we allow pre releases here for skytemple-rust master builds.
pip3 install --pre -r ../requirements-mac-windows.txt
pip3 install ..


if [ -n "$IS_DEV_BUILD" ]; then
  ./install-skytemple-components-from-git.sh
fi

pyinstaller skytemple.spec

# Write the version number to files that are read at runtime
version=$PACKAGE_VERSION || $(python3 -c "import pkg_resources; print(pkg_resources.get_distribution(\"skytemple\").version)")

echo $version > dist/skytemple/VERSION
echo $version > dist/skytemple/data/VERSION
