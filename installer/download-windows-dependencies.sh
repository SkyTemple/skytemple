#!/bin/sh
if [ "$1" = "i686" ]; then
  curl https://skytemple.org/build_deps/win32/py_desmume-0.0.3.post2-cp39-cp39-mingw_i686.whl -O
  curl https://skytemple.org/build_deps/win32/skytemple_rust-0.0.1.post0-cp39-cp39-mingw_i686.whl -O
  curl https://skytemple.org/build_deps/win32/tilequant-0.4.0.post0-cp39-cp39-mingw_i686.whl -O
  curl https://skytemple.org/build_deps/win32/igraph-0.8.2-cp39-cp39-mingw_i686.whl -O
  curl https://skytemple.org/build_deps/armips.exe -O
else
  curl https://skytemple.org/build_deps/py_desmume-0.0.3-cp39-cp39-mingw_x86_64.whl -O
  curl https://skytemple.org/build_deps/skytemple_rust-0.0.1.post0-cp39-cp39-mingw_x86_64.whl -O
  curl https://skytemple.org/build_deps/tilequant-0.4.0.post0-cp39-cp39-mingw_x86_64.whl -O
  curl https://skytemple.org/build_deps/igraph-0.8.2-cp39-cp39-mingw_x86_64.whl -O
  curl https://skytemple.org/build_deps/armips.exe -O
fi

# Dummy python-igraph package to force not trying to install it (it has been renamed to igraph, see above.)
curl https://skytemple.org/build_deps/python_igraph-99.0.0-py3-none-any.whl -O
