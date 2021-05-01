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

# Change "run_skytemple" to "pre_run_skytemple" in the launcher info to launch the shell script instead of the app
sed -i '' 's/run_skytemple/pre_run_skytemple/' dist/SkyTemple.app/Contents/Info.plist

# Create a shell script that sets LD_LIBRARY_PATH and the working directory, then launches SkyTemple
cat > $appdir/pre_run_skytemple << EOF
#!/bin/sh

# Fix paths
export LD_LIBRARY_PATH="\$(dirname \$0)"
export PATH="\$PATH:\$(dirname \$0)/skytemple_files/_resources"

# Fix the language 🥲
# The output of "defaults read -g AppleLanguages" looks like this, so we need to extract
# the language code and replace "-" with "_".
# (
#     "de-DE",
#     "en-US"
# )
language="\$(defaults read -g AppleLanguages | grep -o "\w\w-\w\w" | head -1 | sed -e "s/-/_/")"
export LC_ALL="\$language.UTF-8"

# Run the SkyTemple binary
"\$(dirname \$0)/run_skytemple"
EOF

chmod +x $appdir/pre_run_skytemple

# Write the version number to files that are read at runtime
version=$PACKAGE_VERSION || $(python3 -c "import pkg_resources; print(pkg_resources.get_distribution(\"skytemple\").version)")

echo $version > $appdir/VERSION
echo $version > $appdir/data/VERSION
