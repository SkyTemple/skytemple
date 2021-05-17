#!/bin/sh
if [ "$1" = "i686" ]; then
  curl https://skytemple.org/build_deps/win32/py_desmume-0.0.3.post2-cp38-cp38-mingw.whl -O
  curl https://skytemple.org/build_deps/win32/skytemple_rust-0.0.1.post0-cp38-cp38-mingw.whl -O
  curl https://skytemple.org/build_deps/win32/tilequant-0.4.0.post0-cp38-cp38-mingw.whl -O
  curl https://skytemple.org/build_deps/win32/python_igraph-0.8.2-cp38-cp38-mingw.whl -O
  curl https://skytemple.org/build_deps/armips.exe -O
else
  curl https://skytemple.org/build_deps/py_desmume-0.0.3-cp38-cp38-mingw.whl -O
  curl https://skytemple.org/build_deps/skytemple_rust-0.0.1.post0-cp38-cp38-mingw.whl -O
  curl https://skytemple.org/build_deps/tilequant-0.4.0.post0-cp38-cp38-mingw.whl -O
  curl https://skytemple.org/build_deps/python_igraph-0.8.2-cp38-cp38-mingw.whl -O
  curl https://skytemple.org/build_deps/armips.exe -O
fi
