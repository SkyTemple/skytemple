|logo|

SkyTemple
=========

|build| |crowdin| |pypi-version| |pypi-downloads| |pypi-license| |pypi-pyversions| |discord|

.. |logo| image:: https://raw.githubusercontent.com/SkyTemple/skytemple/master/skytemple/data/icons/hicolor/256x256/apps/skytemple.png

.. |crowdin| image:: https://badges.crowdin.net/skytemple/localized.svg
    :target: https://crowdin.com/project/skytemple
    :alt: Localization Progress

.. |build| image:: https://img.shields.io/github/workflow/status/SkyTemple/skytemple/Build,%20test%20and%20publish
    :target: https://pypi.org/project/skytemple/
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
    :target: https://discord.gg/skytemple
    :alt: Discord

.. |kofi| image:: https://www.ko-fi.com/img/githubbutton_sm.svg
    :target: https://ko-fi.com/I2I81E5KH
    :alt: Ko-Fi

ROM hacking tool for Pokémon Mystery Dungeon Explorers of Sky.

It is available for Linux, macOS and Windows.

It includes a Python library for editing the ROM through Python (skytemple-files_)
and a debugger / script editor is integrated into the UI of SkyTemple (skytemple-ssb-debugger_).
Inside the debugger you can edit the game's scripts via the programming language ExplorerScript_.

.. _skytemple-files: https://github.com/SkyTemple/skytemple-files
.. _skytemple-ssb-debugger: https://github.com/SkyTemple/skytemple-ssb-debugger
.. _ExplorerScript: https://github.com/SkyTemple/ExplorerScript

|kofi|

Support and Features
~~~~~~~~~~~~~~~~~~~~
See the `Project Pokémon forums page`_.

.. _Project Pokémon forums page: https://projectpokemon.org/home/forums/topic/57303-pmd2-skytemple-rom-editor-maps-scripts-debugger/

Windows & macOS
~~~~~~~~~~~~~~~
To download SkyTemple for Windows and macOS head over to the `Project Pokémon`_ page.

.. _Project Pokémon: https://projectpokemon.org/home/files/file/4193-skytemple-pmd2-rom-edtior/

If you want to set up SkyTemple for development, see the "BUILDING_WINDOWS.md" or "BUILDING_MACOS.md" file.

Linux
~~~~~

Flatpak
-------
SkyTemple is distributed as a Flatpak on `Flathub`_ for all major Linux distributions.

|flathub_badge|

.. _Flathub: https://flathub.org/apps/details/org.skytemple.SkyTemple

.. |flathub_badge| image:: https://flathub.org/assets/badges/flathub-badge-en.png
    :target: https://flathub.org/apps/details/org.skytemple.SkyTemple
    :alt: Install on Flathub
    :width: 240px

This Flatpak contains everything needed to use all SkyTemple features.

Source repository for the Flatpak: https://github.com/flathub/org.skytemple.SkyTemple

Manual
------
The Linux version can be installed manually/"natively" via Pip.

For this Python 3.8+ must be installed and GTK+ 3
(which you most likely both have). Additionally GtkSourceView 4 is required
(package ``gtksourceview4`` on Arch and ``libgtksourceview-4-dev`` on Ubuntu).

Then install SkyTemple via pip::

    pip install --upgrade skytemple[eventserver,discord]

You may need to run pip3 instead and/or need to update pip by running::

    pip3 install --upgrade pip

After this, you can run ``skytemple`` to run it.
If this doesn't work, you don't have ``~/.local/bin`` in your PATH.
Run ``~/.local/bin/skytemple`` instead.

To be able to apply patches, you need to install armips_. Sadly they don't provide builds. However
for Arch Linux a version is available through the AUR_.

.. _armips: https://github.com/Kingcom/armips
.. _AUR: https://aur.archlinux.org/packages/armips/

If you want to set up SkyTemple for development, clone the repos and install in editable
mode instead. See the steps 4 and onward in "BUILDING_WINDOWS.md".
