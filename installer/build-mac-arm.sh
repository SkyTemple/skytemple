#!/bin/bash

# Call with "PACKAGE_VERSION=[version number] ./build-mac.sh"
# The version from the current pip install of SkyTemple is used if no version number is set.
set -e

generate_version_file() {
  location=$(pip3 show $1 | grep Location | cut -d":" -f 2 | cut -c2-)
  pip3 show $1 | grep Version | cut -d":" -f 2 | cut -c2- > $location/$1/VERSION
}

# The VERSION files for a few dependencies are missing for some reason, so generate them from 'pip show' commands
generate_version_file cssselect2
generate_version_file tinycss2
generate_version_file cairosvg
generate_version_file cairocffi

# Create the icon
# https://www.codingforentrepreneurs.com/blog/create-icns-icons-for-macos-apps
mkdir skytemple.iconset
icons_path=../skytemple/data/icons/hicolor
cp $icons_path/16x16/apps/skytemple.png skytemple.iconset/icon_16x16.png
cp $icons_path/32x32/apps/skytemple.png skytemple.iconset/icon_16x16@2x.png
cp $icons_path/32x32/apps/skytemple.png skytemple.iconset/icon_32x32.png
cp $icons_path/64x64/apps/skytemple.png skytemple.iconset/icon_32x32@2x.png
cp $icons_path/128x128/apps/skytemple.png skytemple.iconset/icon_128x128.png
cp $icons_path/256x256/apps/skytemple.png skytemple.iconset/icon_128x128@2x.png
cp $icons_path/256x256/apps/skytemple.png skytemple.iconset/icon_256x256.png
cp $icons_path/512x512/apps/skytemple.png skytemple.iconset/icon_256x256@2x.png
cp $icons_path/512x512/apps/skytemple.png skytemple.iconset/icon_512x512.png

iconutil -c icns skytemple.iconset
rm -rf skytemple.iconset

# Build the app
pyinstaller skytemple-mac.spec --noconfirm
rm skytemple.icns

# Since the library search path for the app is wrong, execute a shell script that sets is correctly
# and launches the app instead of launching run_skytemple directly
appdir=dist/SkyTemple.app/Contents/MacOS
