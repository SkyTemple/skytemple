## Windows development setup

The Windows development setup since SkyTemple 1.5.0 uses the "normal" Python for Windows and GTK using gvsbuild.
Previously Msys2 + MingW was used, but this is no longer the case. The setup is now MSVC based, and as such requires
Microsoft Visual Studio to be installed, but these instructions will guide you through it.

A lot of these steps are (sometimes directly) taken from the [gvsbuild](https://github.com/wingtk/gvsbuild) README. 
If something here does not seem to work, you may want to cross-reference this and open an issue in the SkyTemple 
repository about it.
You can also cross-reference the GitHub Actions Workflow for the Windows build, as this is most-likely going to be 
up-to-date. But note that this focuses on bundling SkyTemple in an installer, but it still needs to do the 
same preperations to get there.

### 1. Choco
These steps will be using  [Chocolately](https://chocolatey.org/) as a package manager.

To install it, open PowerShell as an administrator, then execute:

```PowerShell
Set-ExecutionPolicy Bypass -Scope Process -Force; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
```

All following commands should also be run in an Administrator PowerShell for now.

You may need to restart PowerShell after this command.

If you do not want to use it, in the following steps, install the required software manually.

### 2. Dependencies

Install Git, Visual Studio, MSys2, Python (regular Windows release) and the VC Redistributable 2013:

```PowerShell
choco install -y git visualstudio2022-workload-vctools msys2 python vcredist2013
```

You may need to restart PowerShell.

Again, you can also install any of these manually or skip installing them using this command, should you already
have some of these installed.

The `-y` option will auto-accept all install scripts. If you are unsure, omit it and confirm them manually.

### 3. Install gvsbuild
The recommended way to install gvsbuild is with pipx. Open a new regular user
PowerShell terminal and execute:

```PowerShell
python -m pip install --user pipx
python -m pipx ensurepath
pipx install gvsbuild
```

Alternatively, you can also use git to clone the repository and install it.
Open a new regular user PowerShell terminal and execute:

```PowerShell
mkdir C:\gtk-build\github
cd C:\gtk-build\github
git clone https://github.com/wingtk/gvsbuild.git
cd C:\gtk-build\github\gvsbuild
python -m venv .venv
.\.venv\Scripts\activate.ps1
pip install .
```

Either way you may need to restart the shell multiple times. You may also need to update your PATH environment variable.
Follow the on-screen instructions.

### 4. Compile GTK and related packages

Compile GTK3 with GI and with the Python PyGObject Wheels.

```PowerShell
gvsbuild build --enable-gi --py-wheel gtk3 pygobject openssl gettext
```

This may take a while.

### 5. Update environment variables

Set the `Path`, `LIB` and `INCLUDE` environment variables so GTK binaries and libraries are found.

```PowerShell
$env:Path = "C:\gtk-build\gtk\x64\release\bin;" + $env:Path
$env:LIB = "C:\gtk-build\gtk\x64\release\lib;" + $env:LIB
$env:INCLUDE = "C:\gtk-build\gtk\x64\release\include;C:\gtk-build\gtk\x64\release\include\cairo;C:\gtk-build\gtk\x64\release\include\glib-2.0;C:\gtk-build\gtk\x64\release\include\gobject-introspection-1.0;C:\gtk-build\gtk\x64\release\lib\glib-2.0\include;" + $env:INCLUDE
```

You may want to set these envrionment variables system-wide so they are restored on boot. If you don't,
you may need to set these variables up every time you want to work on SkyTemple.

### 6. Create the SkyTemple Virtualenv (optional)

From now on you no longer need an administrator shell. You will need to have the environment setup correctly
though.

It's recommended you setup a dedicated Python virtual environment for SkyTemple. You can skip this and
install the packages directly in your system/user-wide Python environment.

One way to setup a virtualenv manually is:

```PowerShell
mkdir <some-directory-for-skytemple-dev>
cd <some-directory-for-skytemple-dev>
python -m venv .venv
.\.venv\Scripts\activate.ps1
```

But you can use whatever tools you want for it.

### 7. Clone SkyTemple repos and install dependencies

Setup a directory for SkyTemple development. You may have already done this in the previous step 
(`<some-directory-for-skytemple-dev>`).

If you have created a virtualenv, make sure it is activated. 

Make sure the Python `wheel` package is installed.

```PowerShell
pip install wheel
```

Now install the previously built Python PyGObject and pycairo wheels.

```PowerShell
cd <some-directory-for-skytemple-dev>
pip install --force-reinstall (Resolve-Path C:\gtk-build\build\x64\release\pygobject\dist\PyGObject*.whl)
pip install --force-reinstall (Resolve-Path C:\gtk-build\build\x64\release\pycairo\dist\pycairo*.whl)
```

You can now clone any SkyTemple repo and install it in editable mode. Some are:

   - https://github.com/SkyTemple/tilequant.git
   - https://github.com/SkyTemple/explorerscript.git
   - https://github.com/SkyTemple/py-desmume.git
   - https://github.com/SkyTemple/skytemple-rust.git
   - https://github.com/SkyTemple/skytemple-files.git
   - https://github.com/SkyTemple/skytemple-ssb-debugger.git
   - https://github.com/SkyTemple/skytemple-randomizer.git
   - https://github.com/SkyTemple/skytemple.git


Inside each of the repositories listed above (IN THE SAME ORDER AS LISTED*), execute:

```PowerShell
pip install -e .
```

This installs the package in "editable" mode, meaning changes you make to it will be applied directly; 
the package is installed directly from source (under Linux it uses Symlinks, don't know how it does it for Windows).

*: You can also skip cloning some repositories. For example if you only clone SkyTemple and run the above command,
all of the other sub-projects will be downloaded from PyPi. You won't be able to work on them then.

Some of the repositories may have additional requirements should you decide to clone and install them in editable mode, 
such as `skytemple-rust` requiring a Rust compiler to be installed.

Some packages have some additional extra features.

For `skytemple-files` you most likely want to run the following command instead to also get SpriteCollab features:

```PowerShell
pip install -e '.[spritecollab]'
```

For `skytemple` you want to run this command for eventserver support (required for the Textbox tool) and 
Discord presence support:

```PowerShell
pip install -e '.[eventserver,discord]'
```

Full example if you only clone `skytemple` and used the Virtualenv setup above:

```PowerShell
cd <some-directory-for-skytemple-dev>
.\.venv\Scripts\activate.ps1
git clone https://github.com/SkyTemple/skytemple.git
cd skytemple
pip install -e '.[eventserver,discord]'
```

You can then run SkyTemple and everything should work.

```PowerShell
# Run SkyTemple main UI:
python -m skytemple.main
# Run the randomizer
python -m skytemple_randomizer.frontend.gtk.main
```

## Troubleshooting

- I get an "armips could not be found" error when trying to apply ASM patches
   - A: Add the path to the armips executable (https://github.com/Kingcom/armips) to your PATH. You can also copy the executable into `skytemple-files/skytemple_files/_resources`.
