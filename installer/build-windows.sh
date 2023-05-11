#!/bin/sh

# Call with "PACKAGE_VERSION=[version number] ./build-windows.sh"
# The version from the current pip install of SkyTemple is used if no version number is set.
set -ex

rm build -rf || true
rm dist -rf || true

pip3 install -U certifi

pip3 install -r ../requirements-mac-windows.txt
pip3 install ..

if [ -n "$IS_DEV_BUILD" ]; then
  ./install-skytemple-components-from-git.sh
fi

pyinstaller skytemple.spec

# Check if we need to copy the cacert file
if [ -f "dist/skytemple/certifi/cacert.pem" ]; then
  echo "Moved cacert to correct place"
  cp -rf dist/skytemple/certifi/cacert.pem dist/skytemple/certifi.pem
fi

# Write the version number to files that are read at runtime
version=$PACKAGE_VERSION || $(python3 -c "import pkg_resources; print(pkg_resources.get_distribution(\"skytemple\").version)")

echo $version > dist/skytemple/VERSION
echo $version > dist/skytemple/data/VERSION
