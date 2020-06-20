macOS Setup
===========

This document is split in two sections:
1. Installing SkyTemple on macOS as an end-user
2. Installing & building SkyTemple for development setup.

Installing SkyTemple on macOS as an end-user
--------------------------------------------
This is only tested on macOS Catalina.

There is no pre-packaged version of SkyTemple yet for macOS. You need to install SkyTemple
manually via [brew](https://brew.sh/).

You will need to run the following commands in the Terminal.

1. Install brew, Python and Pygobject, as described here:  
   https://pygobject.readthedocs.io/en/latest/getting_started.html#macosx-logo-macos
   
2. You additionally need to run: 
   ```
   brew install python@3.8 gtksourceview3 adwaita-icon-theme
   ```
2. In the following step, replace "USER" with your username.  
   Run these commands and **re-open the Terminal**:
   ```
   echo 'export PATH=/usr/local/opt/python@3.8/bin:$PATH' >> ~/.zshrc
   ```
2. Install SkyTemple itself:
   ```
   pip3 install skytemple
   ```
   
If the installation fails because of ``skytemple-rust`` or ``py-desmume``, you probably have a different
Python version or MacOS version than the developers of SkyTemple when they uploaded packages for them.
You can go to our Discord and ask if we can provide the packages for your system, but the chances are slim.
You can also try compiling those yourself, see "Building binary dependencies".

If you want to upgrade SkyTemple run:
```
pip install --upgrade skytemple
```
When upgrading you might want to check if the wheels explained in 3. have new versions and
install them first.

Optional:
- To have support for applying patches, you need to install armips:  
  https://github.com/Emory-M/armips
- Install the McMojave GTK theme for a more native look:  
  https://www.gnome-look.org/p/1275087/  
  
  To install it, extract the xz file for BOTH the dark or light theme and put their contents in `/Users/USER/.themes`.
  
  If the theme is installed SkyTemple will pick it instead of the default theme. 
  Future versions of SkyTemple will allow you to choose any installed theme.


To start SkyTemple, run `skytemple` in a Termial. We don't provide an application starter yet.

Installing & building SkyTemple for development setup.
------------------------------------------------------

Follow the instructions for end-users, but instead of Step 4, continue with this:

4. Clone the SkyTemple repositories:
   - https://github.com/SkyTemple/tilequant.git
   - https://github.com/SkyTemple/explorerscript.git
   - https://github.com/SkyTemple/skytemple-files.git
   - https://github.com/SkyTemple/skytemple-ssb-debugger.git
   - https://github.com/SkyTemple/skytemple.git
5. Inside each of the repositories listed above (IN THE SAME ORDER AS LISTED), execute:
   ```
   pip3 install -e .
   ```
   This installs the package in "editable" mode, meaning changes you make to it will be applied directly; 
   the package is installed directly from source (under Linux it uses Symlinks, don't know how it does it for Windows).
   You can also skip cloning some repositories. For example if you only clone SkyTemple and run the above command,
   all of the other sub-projects will be downloaded from PyPi. You won't be able to work on them then.
6. You should be good to go:
   ```
   # Run SkyTemple main UI:
   python3 -m skytemple.main
   # Run ExplorerScript test export/import script (warning, hardcoded to my machine by default. The other packages have similar debug scripts):
   python3 -m skytemple_files.script.ssb.dbg.export_explorerscript_test
   ```


### Building binary dependencies
These are the instructions on how you can compile the binary dependencies of SkyTemple yourself.

#### skytemple_rust
1. Make sure you have a Rust toolchain (nightly) setup.
2. Clone https://github.com/SkyTemple/skytemple-rust.git
3. Run `pip3 install -r dev-requirements.txt `
3. Run `python3 setup.py build_ext`
3. Run `pip3 install -e . `

#### py-desmume
1. Make sure you have the GNU build tools installed (Autoconf, Automake, Libtool) and some additional dependencies:
   ``brew install coreutils libtool automake sdl``
1. Add the binaries without the ``g`` prefix to the ``PATH``:
   ```
   export PATH="/usr/local/opt/coreutils/libexec/gnubin:$PATH"
   # Also for glibtool - You can do this more elegant via an extra directory if you want! 
   # Just setting LIBTOOL won't work!
   sudo ln -s $(which glibtool) /usr/local/opt/coreutils/libexec/gnubin/libtool
   ```
2. Clone https://github.com/SkyTemple/py-desmume
3. Run `pip3 install -r dev-requirements.txt `
3. Run `python3 setup.py build`
3. Run `pip3 install -e . `
