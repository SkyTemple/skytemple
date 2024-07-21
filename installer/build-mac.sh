#!/bin/bash

# Call with "PACKAGE_VERSION=[version number] ./build-mac.sh"
# The version from the current pip install of SkyTemple is used if no version number is set.
set -e

pip3 install -U certifi

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

# Download armips
curl https://skytemple.org/build_deps/mac/armips -O
chmod +x armips

# Install themes
curl https://skytemple.org/build_deps/Arc.zip -O
unzip Arc.zip > /dev/null
curl https://skytemple.org/build_deps/ZorinBlue.zip -O
unzip ZorinBlue.zip > /dev/null
mkdir -p share/themes
export XDG_DATA_DIRS="$(pwd)/share/:/usr/local/share/:/usr/share/:$XDG_DATA_DIRS"
cp -a Arc share/themes/Arc
cp -a Arc-Dark share/themes/Arc-Dark
cp -a ZorinBlue-Light share/themes/ZorinBlue-Light
cp -a ZorinBlue-Dark share/themes/ZorinBlue-Dark

# Build the app
pyinstaller --log-level=DEBUG skytemple-mac.spec --noconfirm

rm skytemple.icns
