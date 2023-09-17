Plugin Development
==================

This is the documentation for developing and distributing plugins
for SkyTemple. The documentation on how to install and use plugins,
as well as general information, can be found on our wiki_.

.. _wiki: https://wiki.skytemple.org/index.php/Plugin

Overview
--------
A SkyTemple plugin is a Python `distribution package`_ that contains
at least one `entry point`_ for the group ``skytemple.module``.

Entries in the entry point can use an arbitrary key and the value
must point to a class that subclasses `AbstractModule`_.

Modules can then modify SkyTemple's behaviour and add their own views
to the main item tree (the tree on the left side of the UI when a ROM
is loaded). Since they are Python packages, pretty much everything is
theoretically possible.

.. _distribution package: https://packaging.python.org/en/latest/guides/distributing-packages-using-setuptools/
.. _entry point: https://packaging.python.org/en/latest/specifications/entry-points/
.. _AbstractModule: https://github.com/SkyTemple/skytemple/blob/master/skytemple/core/abstract_module.py

Loading Plugins
---------------
Depending on how SkyTemple is installed, there are two ways plugins are
discovered and loaded. Understanding these mechanisms is important.

Via ``site-packages``
~~~~~~~~~~~~~~~~~~~~~
If SkyTemple is installed as a regular Python package using tools like
``pip``, then you can just install your plugin as a regular Python
package. You can do this by using ``pip``. The editable mode (``pip -e``)
is also supported for ease of development.

Note that this is also referred to sometimes as the "development setup".
End-users of SkyTemple are unlikely to install SkyTemple this way, and
will probably install it via the Flatpak or PyInstaller distributions,
see below.

Via SkyTemple's plugin loader
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
No matter how SkyTemple is installed, it also has a built-in plugin loader
that loads wheels_ placed in the ``plugins`` directory of SkyTemple's
configuration directory.

This directory should be at the following location:

- Linux: ``~/.config/skytemple/plugins`` (``$XDG_CONFIG_HOME`` is used)
- MacOS: ``~/Library/Preferences/skytemple/plugins``
- Windows: ``C:\Users\<username>\AppData\Local\skytemple\plugins``

You can open the configuration directory from SkyTemple ("Open config
directory...").

A plugin wheel placed in these directories is automatically loaded after
the user confirms it on start. This is the primary way to distribute
plugins. The section "Distribution_" will go into more details on how
to create these wheels.

.. _wheels: https://packaging.python.org/en/latest/guides/distributing-packages-using-setuptools/#wheels

Basic Plugin Structure
----------------------
A SkyTemple plugin is usually at least made up of the following files and
directories (where ``name_of_your_package`` is the name of your package):

.. code-block:: text

    name_of_your_package/
        __init__.py
        module.py
    LICENSE
    MANIFEST.in
    pyproject.toml

LICENSE
~~~~~~~
SkyTemple is licensed under `GPLv3+`_. As such your plugin must be licensed under
the same license or a newer version.

pyproject.toml
~~~~~~~~~~~~~~
The `pyproject.toml`_ file is the new standard for defining Python packages.
It contains the following minimal contents:

.. code-block:: toml

    # The build system, see documentation for info.
    [build-system]
    requires = ["setuptools"]
    build-backend = "setuptools.build_meta"

    [project]
    name = "name_of_your_package"
    requires-python = ">=3.8"
    keywords = ["skytemple", "skytemple-plugin"]
    license = {text = "GPL-3.0-or-later"}
    classifiers = [
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
    ]
    dependencies = [
        # See the `Dependencies` section.
        'skytemple >= 1.6.0',
        'skytemple-files >= 1.6.0',
        'pmdsky-debug-py',
        'range-typed-integers >= 1.0.0',
        'pygobject >= 3.26.0'
    ]

    # This is the entry point definition for your plugin.
    [project.entry-points."skytemple.module"]
    # Replace the key with a name describing your plugin and the value with
    # the path to your module class.
    name_of_your_package = "name_of_your_package.module:ExampleModule"


MANIFEST.in
~~~~~~~~~~~
This file contains a definition of additional non-Python files that are included
in your package, see the example plugin.


name_of_your_package/
~~~~~~~~~~~~~~~~~~~~~
This is your package's code. It must contain a ``__init__.py`` (all sub-packages also),
it can be empty. In this example the ``module.py`` contains the module:


.. code-block:: py3

    from __future__ import annotations

    from typing import List

    from skytemple.core.abstract_module import AbstractModule
    from skytemple.core.item_tree import ItemTree
    from skytemple.core.rom_project import RomProject


    class ExamplePlugin(AbstractModule):
        def __init__(self, rom_project: RomProject):
            """
            Your plugin gets passed in the RomProject when it is created.
            This is your primary way to interact with the game and other modules.

            Note that `__init__` is called to create an instance of your module whenever a ROM
            is loaded. If you want to perform one-time initialization when SkyTemple starts
            use the classmethod load.
            """

        @classmethod
        def depends_on(cls) -> List[str]:
            """
            This returns a list of modules that your plugin needs. This can be another plugin module
            or one of the built-in modules, which are listed in SkyTemple's setup.py
            (or in the future it's pyproject.toml).

            You can reference these other modules and rely on functionality in them.
            """
            return []

        @classmethod
        def sort_order(cls) -> int:
            """
            A number that is used to sort all of the items in the main item tree of the SkyTemple UI.

            Experiment with this until you find a value you are happy with.
            """
            return 0

        def load_tree_items(self, item_tree: ItemTree):
            """
            This is the heart of your plugin (if your plugin's purpose is to show views in the UI.
            You can add new views to the main item tree on the left of SkyTemple's UI here.

            You must implement this, but you can also do just nothing,
            if your UI does not actually provide new views.

            You can also manipulate other items in the item tree, but this is not recommended, since
            it could easily break with updates.
            """
            pass

.. _GPLv3+: https://www.gnu.org/licenses/gpl-3.0.html.en
.. _pyproject.toml: https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html

Dependencies
------------
Your plugin can not pull in any dependencies not bundled with SkyTemple, if you intend
to distribute it via the ``plugins`` directory (see "`Via SkyTemple's plugin loader`_").

You can rely on the following dependencies being bundled with SkyTemple.

SkyTemple 1.6
~~~~~~~~~~~~~
- GTK 3.24 (Note: SkyTemple will eventually switch to GTK 4. Try to only use GTK 4 compatible widgets).
- ndspy 3
- skytemple-files 1.6
- pmdsky-debug-py in the same version skytemple-files requires
- skytemple-dtef 1.6
- skytemple-icons 1.3
- explorerscript 0.1
- skytemple-rust 1.6
- dungeon_eos 0.0.5+
- range-typed-integers 1
- pygobject 3.40.0+
- pycairo 1.18+
- tilequant 1
- skytemple-ssb-debugger 1.6
- CairoSVG 2.7
- packaging
- wheel
- importlib_metadata on Python < 3.9
- importlib_resources on Python < 3.9


Example Plugin
--------------
An example plugin that also shows a lot of the APIs you can use and how to build custom views
can be found at:

https://github.com/SkyTemple/skytemple-example-plugin/

Additionally you can reference
`built-in modules <https://github.com/SkyTemple/skytemple/tree/master/skytemple/module>`_.

Distribution
------------
In order to distribute your plugin you need to create a Wheel for it.

To do this, install the ``wheel`` package on your system via ``pip``.
After this run the following command:

.. code-block:: shell

    pip wheel --no-deps <path to your package>

If you used the basic examples this will usually produce a file with the
``.whl`` file extension and the string ``py3-none-any`` in its name.
This is a "Pure Python wheel" and can be installed on any platform. You
can give this your users and they can place it in the plugins directory.

If the string ``py3-none-any`` is not in the wheel filename, you have
built a "Platform Wheel". Continue reading below.

Bundling Binaries
-----------------
By default Python distributions produce "Pure Python wheels". These wheels
only contain Python source code and no binaries.

If your package links against binary code, eg. C/Rust it will become a
"Platform Wheel". It does not matter if your binary code is a
Python module (a CPython extension) or if you just use it dynamically
via ``ctypes``.

A "Platform Wheel" is always bound to a specific Python release,
architecture and operating system. Linux Wheels must be built
using the manylinux_ Docker images in order to be distributable.

Please provide wheels for all Python versions and platforms supported
by SkyTemple. This is currently:

- Python 3.8 - 3.11
- Architecture x86_64 for Windows 10+, MacOS 11+, Linux (``manylinux2014``).
- Architecture aarch64: Linux (``manylinux2014``).

To make integration easier, you can use ``setuptools`` plugins:

- setuptools_rust_ can be used to bundle Rust code in your package.
  You can either use different bindings if you want to create real
  Python modules written in Rust, or set the binding to ``NoBinding``
  if you plan to load it via ``ctypes``
  (`example repository <https://github.com/suzusuzu/rust-python-ctypes/tree/master>`_
  for the latter).
- setuptools_dso_ can be used to bundle C libraries that will be used via `ctypes`.

`Tilequant`_ is an example on a Python package using "setuptools_dso" and
skytemple-rust_ for a package using "setuptools_rust".

You need to build a wheel for each platform and prompt your users to use the correct
one depending on their platform.

The PyInstaller/Flatpak distributions of SkyTemple currently use the following Python
versions:

- Linux Flatpak: 3.10
- MacOS PyInstaller: 3.11
- Windows PyInstaller: 3.11

.. _manylinux: https://github.com/pypa/manylinux
.. _setuptools_rust: https://pypi.org/project/setuptools-rust/
.. _setuptools_dso: https://pypi.org/project/setuptools-dso/
.. _Tilequant: https://github.com/SkyTemple/tilequant
.. _skytemple-rust: https://github.com/SkyTemple/skytemple-rust
