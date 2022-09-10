#!/bin/sh
# Installs the latest skytemple-rust version for the current platform.
# If dev build: Latest is master. Otherwise latest is taken from "release" branch
# which MUST point to the latest release.
set -xe

py_version=""

arch="MINGW64"
if [ "$1" = "i686" ]; then
  arch="MINGW32"
fi

branch="release"
if [ -n "$IS_DEV_BUILD" ]; then
  branch="master"
fi

platform="msys2"
if [ -n "$IS_MACOS" ]; then
  platform="macos-10.15"
  arch="x64"
  py_version="3.10"
fi

url="https://nightly.link/SkyTemple/skytemple-rust/workflows/build-test-publish/$branch/wheels-$platform-py$py_version-$arch.zip"

rm -rf tmp_rust || true

mkdir tmp_rust
cd tmp_rust
curl -LO $url
unzip *.zip
pip3 install *.whl

rm -rf tmp_rust || true
