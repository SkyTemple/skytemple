#!/bin/sh
export XDG_DATA_DIRS="${BUILD_ROOT}/${MINGW}/share"

rm build -rf
rm dist -rf

# Just a build script to build locally without much setup.
pip uninstall skytemple skytemple-files skytemple-ssb-debugger explorerscript py-desmume skytemple-rust tilequant py-desmume -y
pip install python_igraph-*-cp38-cp38-mingw.whl
pip install py_desmume-*-cp38-cp38-mingw.whl
pip install skytemple_rust-*-cp38-cp38-mingw.whl
pip install ../../explorerscript
pip install ../../tilequant
pip install ../../files
pip install ../../ssb_debugger
