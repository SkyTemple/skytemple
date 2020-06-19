#!/bin/sh
# I don't get it. If I put this in the same script, it doesn't work.
pyinstaller skytemple.spec
sleep 20

# Remove unnesecary things
rm dist/skytemple/share/doc/* -rf
rm dist/skytemple/share/gtk-doc/* -rf
rm dist/skytemple/share/man/* -rf
rm dist/skytemple/share/themes/* -rf

# Install additional themes
cp -a bundling/themes/* dist/skytemple/share/themes/
