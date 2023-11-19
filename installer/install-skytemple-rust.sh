#!/bin/sh
# Installs the latest skytemple-rust version for the current platform.
# If dev build: Latest is master. Otherwise latest is taken from "release" branch
# which MUST point to the latest release.
set -xe

branch="master"
wheel_name="skytemple_rust-*-cp311-cp311-win_amd64.whl"

if [ -n "$IS_MACOS" ]; then
  wheel_name="skytemple_rust-*-cp311-cp311-macosx_10_9_x86_64.whl"
fi

url="https://nightly.link/SkyTemple/skytemple-rust/workflows/build-test-publish/$branch/wheels.zip"

rm -rf tmp_rust || true

mkdir tmp_rust
cd tmp_rust
curl -LO $url
unzip wheels.zip
eval pip3 install $wheel_name

rm -rf tmp_rust || true
