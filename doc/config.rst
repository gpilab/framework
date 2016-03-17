#############
Configuration
#############

The following section covers the default GPI setup and more advanced
configurations using the ``.gpirc`` file.

.gpirc
======
The ``.gpirc`` file is a configuration file that can set the behavior of a few
essential settings.  GPI looks for this file in the user's home directory.
This file is not installed by default, but can be generated as needed by
selecting the *Config → Generate Config File* option from the main menu.

To show the configuration settings, whether you have a ``.gpirc`` file or not,
the following command can be entered into a terminal window::

    $ gpi --config

The output provides information about the configured paths, file associations,
and additional make directives used by the ``gpi_make`` command.

Library Directories
-------------------
By default, GPI is set to look for user node libraries in your ``~/gpi``
directory, and in the GPI application directory (which is platform and
installation dependent).

The *core* node library comes pre-packaged with most GPI installations. Most
user defined repositories or open source repositories (e.g. from GitHub) should
be checked out into the user's ``~/gpi`` directory. GPI can assist you in
creating a personal node repository if you select *Config → Generate User
Library* from the menu bar; this will create a new empty library in
``~/gpi/<username>``.

The searched directories can be changed or added to by modifying the ``.gpirc``
file under the ``[PATH]`` label.  The ``LIB_DIRS`` variable stores each path in a
colon separated list::

    [PATH]
    LIB_DIRS = ~/gpi:/opt/gpi/node

The library directory can be specified directly or directories containing
libraries. Adding any directories in this section will *override the default
search locations*.
