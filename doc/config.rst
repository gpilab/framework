.. _config-rst:

#############
Configuration
#############

Configure GPI through *File → Settings*. Settings are saved automatically in
``gpi_settings.json`` at the following per-user locations:

* Windows: ``%APPDATA%\gpi\gpi_settings.json``
* macOS/Linux: ``~/.gpi/gpi_settings.json``

Legacy ``.gpirc`` files are no longer supported or read, including by the build
tools. They are not migrated automatically; re-enter any custom settings through
*File → Settings*. The old ``--ignore-gpirc`` build option has been removed;
use ``--ignore-config`` to ignore user JSON settings during a build.

To show the current configuration settings, enter::

    $ gpi --config

The output provides information about the configured paths, file associations,
and additional make directives used by the ``gpi_make`` command.

Library Directories
-------------------
GPI includes the installed ``gpi_core`` library automatically. Add custom node
library directories through *File → Settings → Paths*. To create a personal
node library, use *Library → Create New Library*.

Library directories are stored as a JSON list under ``PATH`` → ``LIB_DIRS``,
not as a colon-separated string. Required installed library directories are
retained automatically.

Port Connections
----------------
Use *File → Settings → General → Port connections* to choose **Straight** or
**Curly** connections in the Dark theme. Click **OK** or **Apply** to update
existing connections and save the choice. Curly is the default.
Both straight and curly connections attach at the centers of the ports.

This option is hidden in the Classic theme, which always uses straight lines.
The Dark theme choice is retained when switching themes and restarting GPI.
It is stored under ``APPEARANCE`` → ``CONNECTION_STYLE`` in the settings JSON.

Build Settings
--------------
Use *File → Settings → Make* to configure additional libraries, include
directories, library directories, and compiler flags. These settings are stored
under the JSON ``MAKE`` object as ``LIBS``, ``INC_DIRS``, ``LIB_DIRS``, and
``CFLAGS`` lists.
