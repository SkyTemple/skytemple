#!/usr/bin/env bash
set -x
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
set -e
# This configures Flatpak and builds SkyTemple as a Flatpak.
flatpak install org.gnome.Platform//42 org.gnome.Sdk//42

appstream-util validate-relax org.skytemple.SkyTemple.appdata.xml
flatpak-builder build-dir --force-clean org.skytemple.SkyTemple.yml

# flatpak-builder --user --install --force-clean build-dir org.skytemple.SkyTemple.yml
# flatpak run org.skytemple.SkyTemple
