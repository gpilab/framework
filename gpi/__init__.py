#    Copyright (C) 2014  Dignity Health
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#    NO CLINICAL USE.  THE SOFTWARE IS NOT INTENDED FOR COMMERCIAL PURPOSES
#    AND SHOULD BE USED ONLY FOR NON-COMMERCIAL RESEARCH PURPOSES.  THE
#    SOFTWARE MAY NOT IN ANY EVENT BE USED FOR ANY CLINICAL OR DIAGNOSTIC
#    PURPOSES.  YOU ACKNOWLEDGE AND AGREE THAT THE SOFTWARE IS NOT INTENDED FOR
#    USE IN ANY HIGH RISK OR STRICT LIABILITY ACTIVITY, INCLUDING BUT NOT
#    LIMITED TO LIFE SUPPORT OR EMERGENCY MEDICAL OPERATIONS OR USES.  LICENSOR
#    MAKES NO WARRANTY AND HAS NO LIABILITY ARISING FROM ANY USE OF THE
#    SOFTWARE IN ANY HIGH RISK OR STRICT LIABILITY ACTIVITIES.

# All methods, defs and members needed by node developers must be imported
# automatically into the gpi namespace.  This way users only need to
# import gpi, then use things like gpi.REQUIRED for ports etc...
import warnings
warnings.filterwarnings("ignore", ".*Applications.GPI.*import.*")

import os
import time

GPI_PKG_PATH=os.path.dirname(os.path.abspath( __file__ ))  # get location of THIS gpi python-package
VERSION_FPATH=os.path.join(GPI_PKG_PATH, 'VERSION')
VERSION = '2.0.0'
__version__ = VERSION
RELEASE_DATE = '2026-06-12'
try:
    with open(VERSION_FPATH, 'r') as f:
        for l in f.readlines():
            if l.count('PKG_VERSION'):
                VERSION = l.split(':')[-1].strip()
            if l.count('BUILD_DATE'):
                RELEASE_DATE = l.split(':')[-1].strip()
except:
    pass

# Print version info each time.
_version = 'GPI '+VERSION+' ('+RELEASE_DATE+')'
_copyright = ''
_disclaimer = '''\
This program comes with ABSOLUTELY NO WARRANTY; see the LICENSE for details.

    NO CLINICAL USE.  THE SOFTWARE IS NOT INTENDED FOR COMMERCIAL PURPOSES
AND SHOULD BE USED ONLY FOR NON-COMMERCIAL RESEARCH PURPOSES.  THE SOFTWARE
MAY NOT IN ANY EVENT BE USED FOR ANY CLINICAL OR DIAGNOSTIC PURPOSES.  YOU
ACKNOWLEDGE AND AGREE THAT THE SOFTWARE IS NOT INTENDED FOR USE IN ANY HIGH
RISK OR STRICT LIABILITY ACTIVITY, INCLUDING BUT NOT LIMITED TO LIFE SUPPORT
OR EMERGENCY MEDICAL OPERATIONS OR USES.  LICENSOR MAKES NO WARRANTY AND HAS
NO LIABILITY ARISING FROM ANY USE OF THE SOFTWARE IN ANY HIGH RISK OR STRICT
LIABILITY ACTIVITIES.
'''

import os as _os
_GPI_WORKER_MODE = _os.environ.get('GPI_WORKER_MODE') == '1'

if not _GPI_WORKER_MODE:
    print((_version+'  '+_copyright+'\n'+_disclaimer))

if _GPI_WORKER_MODE:
    # ------------------------------------------------------------------ #
    # Lightweight worker mode — no Qt, no widgets, no banner.             #
    # Workers only need the type/constant/data-proxy layer so that        #
    # ExternalNode subclasses can be imported and compute() can run.      #
    # ------------------------------------------------------------------ #
    import types as _types

    # Stub Qt namespaces so `from gpi import QtCore` in node files works
    QtCore = _types.SimpleNamespace()
    QtGui = _types.SimpleNamespace()
    QtWidgets = _types.SimpleNamespace(
        QGraphicsItem=_types.SimpleNamespace(UserType=65536)
    )
    QtMultimedia = _types.SimpleNamespace()
    QtOpenGL = _types.SimpleNamespace()
    QtWebKit = None
    QtWebKitWidgets = None
    QtWebEngineWidgets = None
    QWebView = None
    QT_API_NAME = 'stub'
    Qimport = lambda name: _types.SimpleNamespace()

    # Stub signal/slot so class-level `finished = gpi.Signal()` doesn't crash
    class Signal:
        def __init__(self, *args): pass
        def connect(self, *args): pass
        def disconnect(self, *args): pass
        def emit(self, *args): pass
    Slot = lambda f: f
    Property = lambda *a: (lambda f: f)

    # All data-type constants and helpers nodes use at import time
    from .defines import *
    from .numba_stub import autojit, jit
    from .defaultTypes import *
    from .mri_data import *

    # Stub NodeAPI base class — actual behaviour is provided by NodeComputeStub
    class NodeAPI:
        """Stub base class for worker processes (no Qt needed)."""
        pass

    # Some node files define widget-group subclasses at module level.
    # Provide a no-op base so those class definitions succeed.
    class GenericWidgetGroup:
        """Stub base class for worker processes (no Qt needed)."""
        pass

else:
    # ------------------------------------------------------------------ #
    # Full interactive mode                                               #
    # ------------------------------------------------------------------ #
    # transitioning tool
    from . import qtapi
    QtCore = qtapi.QtCore
    QtGui = qtapi.import_module("QtGui")
    QtWidgets = qtapi.import_module("QtWidgets")
    try:
        QtMultimedia = qtapi.import_module("QtMultimedia")
    except Exception:
        import types as _types_mm
        QtMultimedia = _types_mm.SimpleNamespace()  # not available in all Qt installs
    QT_API_NAME = qtapi.API_NAME
    QtWebKit = qtapi.QtWebKit
    QtWebKitWidgets = qtapi.QtWebKitWidgets
    QtWebEngineWidgets = qtapi.QtWebEngineWidgets
    QWebView = qtapi.QWebView
    QtOpenGL = qtapi.QtOpenGL
    Qimport = qtapi.import_module
    Signal = qtapi.Signal
    Slot = qtapi.Slot
    Property = qtapi.Property

    # commandline parsing
    from . import cmd

    # all global vars
    from .defines import *

    # numba decorators
    from .numba_stub import autojit, jit

    # default type class
    from .defaultTypes import *

    # all widget elements and default widgets
    from .widgets import *

    # widget menu
    from .nodeAPI import *

    from .remote import *
    remote = run_on_server

    from .mri_data import *

    from .parallel import *
    parallel = Parallel()
