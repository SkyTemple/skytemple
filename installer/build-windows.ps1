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

# Install NSIS
curl https://skytemple.org/build_deps/nsis.zip -O
unzip -o nsis.zip -d "C:\Program Files (x86)\NSIS"

python -m venv C:\skytemple-venv
C:\skytemple-venv\Scripts\activate.ps1

# Install PyInstaller
pip install setuptools wheel pyinstaller

# Install PyGObject and pycairo
pip install --force-reinstall (Resolve-Path C:\gtk-build\build\x64\release\pygobject\dist\PyGObject*.whl)
pip install --force-reinstall (Resolve-Path C:\gtk-build\build\x64\release\pycairo\dist\pycairo*.whl)

# Install certifi for cert handling
pip install -U certifi

# install SkyTemple
pip install -r ../requirements-mac-windows.txt
pip install ..

if (-not $env:IS_DEV_BUILD) {
  bash .\install-skytemple-components-from-git.sh
}

pyinstaller skytemple.spec

if(!(Test-Path ".\dist\skytemple\skytemple.exe")){
    return 1
}

# Check if we need to copy the cacert file
if (Test-Path ".\dist\skytemple\certifi\cacert.pem") {
  echo "Moved cacert to correct place"
  cp -rf dist/skytemple/certifi/cacert.pem dist/skytemple/certifi.pem
}

echo $env:PACKAGE_VERSION | Out-File -FilePath dist/skytemple/VERSION -Encoding utf8
echo $env:PACKAGE_VERSION | Out-File -FilePath dist/skytemple/data/VERSION -Encoding utf8
