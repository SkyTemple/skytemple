#!/usr/bin/env bash
# TODO: This is currently not tested; I'm running the PyInstaller / NSIS commands directly.
echo "Running _build.sh"

# Available scripts:
# package_installer: Package your application using NSIS. Arg 1: your NSI file.
# build_python: Run your python script using the SDK bundled python.
# build_pip: Run pip using the SDK bundled pip.
# build_pacman: Run pacman using the SDK build root.

# Otherwise the build would try to include all of C:\ProgramData...
export XDG_DATA_DIRS="${BUILD_ROOT}/${MINGW}/share"

# Install the python-igraph fork
echo "Installing python-igraph..."
build_pip python_igraph-*-cp38-cp38-mingw.whl

# Install py-desmume
echo "Installing py-desmume..."
build_pip py_desmume-*-cp38-cp38-mingw.whl

# Install skytemple_rust
echo "Installing skytemple_rust..."
build_pip skytemple_rust-*-cp38-cp38-mingw.whl

# Install tilequant
echo "Installing tilequant..."
build_pip tilequant-*-cp38-cp38-mingw.whl

# Installing Stage 2
echo "Installing Stage 2 requirements..."
build_pip -r requirements-stage-2.txt

# TODO: Include icons & themes

build_python -m pyinstaller skytemple.spec

# Remove unnesecary things
rm dist/skytemple/share/doc/* -rf
rm dist/skytemple/share/gtk-doc/* -rf
rm dist/skytemple/share/man/* -rf

package_installer skytemple.nsi
