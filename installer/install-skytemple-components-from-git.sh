#!/bin/sh
set -e

if [ "$(expr substr $(uname -s) 1 5)" != "MINGW" ]; then
  pip3 install git+https://github.com/SkyTemple/tilequant.git
  pip3 install git+https://github.com/SkyTemple/skytemple-rust.git
  pip3 install git+https://github.com/SkyTemple/py-desmume.git
fi

pip3 install git+https://github.com/SkyTemple/explorerscript.git
pip3 install git+https://github.com/SkyTemple/skytemple-files.git
pip3 install git+https://github.com/SkyTemple/skytemple-eventserver.git
pip3 install git+https://github.com/SkyTemple/skytemple-dtef.git
pip3 install git+https://github.com/SkyTemple/skytemple-icons.git
pip3 install git+https://github.com/SkyTemple/skytemple-ssb-debugger.git
