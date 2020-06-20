|logo|

SkyTemple
=========

|build| |pypi-version| |pypi-downloads| |pypi-license| |pypi-pyversions| |discord|

.. |logo| image:: https://raw.githubusercontent.com/SkyTemple/skytemple/master/skytemple/data/icons/hicolor/256x256/apps/skytemple.png

.. |build| image:: https://jenkins.riptide.parakoopa.de/buildStatus/icon?job=skytemple%2Fmaster
    :target: https://jenkins.riptide.parakoopa.de/blue/organizations/jenkins/skytemple/activity
    :alt: Build Status

.. |pypi-version| image:: https://img.shields.io/pypi/v/skytemple
    :target: https://pypi.org/project/skytemple/
    :alt: Version

.. |pypi-downloads| image:: https://img.shields.io/pypi/dm/skytemple
    :target: https://pypi.org/project/skytemple/
    :alt: Downloads

.. |pypi-license| image:: https://img.shields.io/pypi/l/skytemple
    :alt: License (GPLv3)

.. |pypi-pyversions| image:: https://img.shields.io/pypi/pyversions/skytemple
    :alt: Supported Python versions

.. |discord| image:: https://img.shields.io/discord/710190644152369162?label=Discord
    :target: https://discord.gg/4e3X36f
    :alt: Discord

ROM hacking tool for Pokémon Mystery Dungeon Explorers of Sky.

It is available for Linux, macOS and Windows.

It includes a Python library for editing the ROM through Python (skytemple-files_)
and a debugger / script editor is integrated into the UI of SkyTemple (skytemple-ssb-debugger_).
Inside the debugger you can edit the game's scripts via the programming language ExplorerScript_.

.. _skytemple-files: https://github.com/SkyTemple/skytemple-files
.. _skytemple-ssb-debugger: https://github.com/SkyTemple/skytemple-ssb-debugger
.. _ExplorerScript: https://github.com/SkyTemple/ExplorerScript

Support and Features
~~~~~~~~~~~~~~~~~~~~
See the `Project Pokémon forums page`_.

.. _Project Pokémon forums page: https://projectpokemon.org/home/forums/topic/57303-pmd2-skytemple-rom-editor-maps-scripts-debugger/

Windows
~~~~~~~
To download SkyTemple for Windows head over to the `Project Pokémon`_ page.

.. _Project Pokémon: https://projectpokemon.org/home/files/file/4193-skytemple-pmd2-rom-edtior/

If you want to set up SkyTemple for development, see the "BUILDING_WINDOWS.md" file.

Linux
~~~~~
The Linux version can be installed via Pip. For this Python 3.6+ must be installed and GTK+
(which you most likely both have)::

    pip install --upgrade skytemple

You may need to run pip3 instead and/or need to update pip by running::

    pip3 install --upgrade pip

After this, you can run ``skytemple`` to run it.
If this doesn't work, you don't have ``~/.local/bin`` in your PATH.
Run ``~/.local/bin/skytemple`` instead.

To be able to apply patches, you need to install armips_. Sadly they don't provide builds. However
for Arch Linux a version is available through the AUR_.

.. _armips: https://github.com/Kingcom/armips
.. _AUR: https://aur.archlinux.org/packages/armips/

Are you a package maintainer for a distribution like Ubuntu or Arch Linux? Get in touch with me!

If you want to set up SkyTemple for development, clone the repos and install in editable
mode instead. See the steps 4 and onward in "BUILDING_WINDOWS.md".

macOS
~~~~~
For macOS the installation procedure is explained in "BUILDING_MACOS.md".
Please note that we can offer only very limited support for macOS.
