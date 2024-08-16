Set-PSDebug -Trace 1
$ErrorActionPreference = "Stop"

if (test-path build) {
  rm build -r -force
}
if (test-path dist) {
  rm dist -r -force
}

# Download armips and other binary depedencies
curl https://skytemple.org/build_deps/armips.exe -O

# Install themes
curl https://skytemple.org/build_deps/Arc.zip -O
unzip Arc.zip
curl https://skytemple.org/build_deps/ZorinBlue.zip -O
unzip ZorinBlue.zip

# SDL2
curl https://skytemple.org/build_deps/SDL2.dll -O

# Install NSIS
curl https://skytemple.org/build_deps/nsis.zip -O
unzip -o nsis.zip -d "C:\Program Files (x86)\NSIS"

python -m venv C:\skytemple-venv
C:\skytemple-venv\Scripts\activate.ps1

# Update to at least setuptools 71.0.0 due to potential issues with the hooks in PyInstaller 6.10+
pip install 'setuptools>=71.0.0'

# Install PyInstaller
pip install setuptools wheel 'pyinstaller~=6.10'

# Install certifi for cert handling
pip3 install -U certifi

# Generate MO localization files
bash .\generate-mo.sh

# install SkyTemple
pip install -r ../requirements-frozen.txt
pip install '..[eventserver]'
# pip likes to troll us. Force reinstall the proper PyGObject versions
pip install --force-reinstall (Resolve-Path C:\gtk-build\build\x64\release\pygobject\dist\PyGObject*.whl)
pip install --force-reinstall (Resolve-Path C:\gtk-build\build\x64\release\pycairo\dist\pycairo*.whl)

if ($env:IS_DEV_BUILD) {
  bash .\install-skytemple-components-from-git.sh
}

pyinstaller --log-level=DEBUG skytemple.spec
if ($LASTEXITCODE) { exit $LASTEXITCODE }

if(!(Test-Path ".\dist\skytemple\skytemple.exe")){
    exit 1
}

python gen_list_files_for_nsis.py dist\skytemple install_list.nsh uninstall_list.nsh

if ($LASTEXITCODE) { exit $LASTEXITCODE }
