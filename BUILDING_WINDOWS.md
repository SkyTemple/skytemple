Windows development setup
-------------------------

All of these commands should be run in the MSys environment that is set up in step 1.

1. Install Python and the Pygobject dependencies, as explained here (for development!):
   https://pygobject.readthedocs.io/en/latest/getting_started.html#windows-getting-started
2. Install additional packages: `pacman -S mingw-w64-x86_64-python-pip mingw-w64-x86_64-gtksourceview4 mingw-w64-x86_64-python-pillow mingw-w64-x86_64-toolchain mingw-w64-x86_64-gtksourceview3`
3. Install the binary wheels from https://skytemple.org/build_deps/:
   ```
   pip install py_desmume-0.0.4-cp39-cp39-mingw.whl
   pip install python_igraph-0.8.2-cp39-cp39-mingw.whl
   pip install skytemple_rust-0.0.1-cp39-cp39-mingw.whl
   ```
   If you want to know how to build these yourself, see "Building binary dependencies".
4. Clone the SkyTemple repositories:
   - https://github.com/SkyTemple/tilequant.git
   - https://github.com/SkyTemple/explorerscript.git
   - https://github.com/SkyTemple/skytemple-files.git
   - https://github.com/SkyTemple/skytemple-ssb-debugger.git
   - https://github.com/SkyTemple/skytemple.git
5. Inside each of the repositories listed above (IN THE SAME ORDER AS LISTED), execute:
   ```
   pip install -e .
   ```
   This installs the package in "editable" mode, meaning changes you make to it will be applied directly; 
   the package is installed directly from source (under Linux it uses Symlinks, don't know how it does it for Windows).
   You can also skip cloning some repositories. For example if you only clone SkyTemple and run the above command,
   all of the other sub-projects will be downloaded from PyPi. You won't be able to work on them then.
6. You should be good to go:
   ```
   # Run SkyTemple main UI:
   python -m skytemple.main
   # Run ExplorerScript test export/import script (warning, hardcoded to my machine by default. The other packages have similar debug scripts):
   python -m skytemple_files.script.ssb.dbg.export_explorerscript_test
   ```


Building binary dependencies
----------------------------

### skytemple_rust
1. Make sure you have a Rust toolchain (nightly) setup in MingW.
2. Clone https://github.com/SkyTemple/skytemple-rust.git
3. Create the following symlink (PyO3, the lib that creates the Python bindings, requires python38 without the dot):
   ln -s /mingw64/lib/libpython3.8.dll.a /mingw64/lib/libpython38.dll.a
4. Run `pip install -e .`

### python-igraph
1. Clone Python Igraph with this Pull Request applied:
   https://github.com/igraph/python-igraph/pull/297
2. Install the dependencies of python-igraph.
3. Run `pip install -e .`

### py-desmume
1. Clone https://github.com/SkyTemple/desmume
2. Checkout the `binary-interface` branch.
3. Go to `desmume/src/frontend/interface/windows` and build the Visual Studio project in there.
4. Clone https://github.com/SkyTemple/py-desmume
5. Put the output DLL of step 3 inside the `desmume` directory of that repo.
6. Run `pip install -e .`
