.. _devguide-rst:

###############################
GPI Framework Developer's Guide
###############################

This guide introduces the various structures of the GPI framework, discusses
the runtime entry points and covers some of the package dependencies for
mastering a GPI distro.

The Framework
=============

The 'framework' and 'core-node' projects are separate entities.  The framework
provides the UI, runtime environment and build environment for the node
libraries.  This means the framework doesn't provide any of the scientific
algorithms itself, however, it pulls together some basic numeric packages (C++
and Python) to facilitate the development of nodes.

The repository that holds the framework project can be accessed here:
https://github.com/gpilab/framework

The framework project is organized in the following directory structure:

- bin/
- doc/
- include/
- launch/
- lib/

The following sections introduce the software contained in each of these
directories.

bin/
----
The 'bin/' directory holds the launching mechanisms for starting GPI (either as
a GUI or a command-line utility), the command-line make, or running
the updater.  These mechanisms are accessed by the following scripts:

- gpi_launch
- gpi_make
- gpi_update

The scripts are fairly simple, they may take command-line arguments and
generally access a section of the main gpi library (discussed in the 'lib'
section).  Their purpose is to be configurable for a specific Anaconda Python
install and make OS specific changes necessary to run GPI.

For example, the following code block is take from **gpi_launch**:

.. code-block:: python

    #!/usr/bin/env python

    ...

    import sys, os

    # Check for Anaconda PREFIX, or assume that THIS file location is the CWD.
    GPI_PREFIX = '/opt/anaconda1anaconda2anaconda3' # ANACONDA
    if GPI_PREFIX == '/opt/' + 'anaconda1anaconda2anaconda3':
        GPI_PREFIX, _ = os.path.split(os.path.dirname(os.path.realpath(__file__)))
        GPI_LIB_DIR = os.path.join(GPI_PREFIX, 'lib')
        if GPI_LIB_DIR not in sys.path:
            sys.path.insert(0, GPI_LIB_DIR)

    # gpi
    from gpi import launch

    if __name__ == '__main__':
        launch.launch()

The shebang at the top specifies the first python instance in the user
environment should be used to start this launching script.  This means that
you could download the framework project and run it against any Python
installation, provided it has the necessary dependencies.  The subsequent bit
of logic determines whether the 'conda' package manager was used to install
GPI; if it has, then the **GPI_PREFIX** will point to the location of the
**gpi** library within the Anaconda Python installation.  If 'conda' wasn't
used then the script uses dead reckoning to determine the location of the
**gpi** library assuming the script was initiated within the framework
directory structure.  This is the same basic process in each script.

doc/
----
The 'doc/' directory contains the very documentation that you are reading now.
It is written in `reStructuredText <http://docutils.sourceforge.net/rst.html>`_
and is compiled using the `Sphinx <http://www.sphinx-doc.org/en/stable/index.html>`_
documentation generator.  This is auto-generated for each commit and hosted by
the `ReadTheDocs <https://readthedocs.org/>`_ project.

To build these docs locally (if you intend to modify them), install 
`Sphinx <http://www.sphinx-doc.org/en/stable/index.html>`_ and simply run:

.. code-block:: bash

    $ make html

in the 'doc/' directory.  Then open the relevant '.html' files that have been
generated under the 'doc/_build/' directory.

include/
--------
The 'include/' directory contains the API code for a Python-C interface called
**PyFI**.  While the GPI UI doesn't call on this code, it is provided as a
portability layer for GPI nodes that depend on Python-C modules, written with
:ref:`pyfi_api-rst`.  While you can still write GPI nodes with Python extension
modules supported by
`SWIG <http://www.swig.org/index.php>`_ or `Boost <http://www.boost.org/>`_
these will be extra dependencies of your node library that will have to be
communicated to your end users.

At the time PyFI was written, the aforementioned SWIG and Boost libraries
didn't yet have the capability to transfer numeric arrays between Python and C
without copying the data.  This was being developed in a project called
`Boost.NumPy <https://github.com/ndarray/Boost.NumPy>`_, and is now part of the
Boost.Python support package.  PyFI also has the capability of allocating
numeric arrays from Python, to be used in the embedded C routine, which
circumvents the need to copy data between Python and C.

launch/
-------




