#!/bin/sh
set -e

pip3 uninstall -y explorerscript && pip3 install git+https://github.com/SkyTemple/explorerscript.git
pip3 uninstall -y skytemple-files && pip3 install git+https://github.com/SkyTemple/skytemple-files.git
pip3 uninstall -y skytemple-eventserver && pip3 install git+https://github.com/SkyTemple/skytemple-eventserver.git
pip3 uninstall -y skytemple-dtef && pip3 install git+https://github.com/SkyTemple/skytemple-dtef.git
pip3 uninstall -y skytemple-icons && pip3 install git+https://github.com/SkyTemple/skytemple-icons.git
pip3 uninstall -y skytemple-ssb-debugger && pip3 install git+https://github.com/SkyTemple/skytemple-ssb-debugger.git
