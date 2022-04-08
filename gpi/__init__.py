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
VERSION_FPATH=GPI_PKG_PATH+'/VERSION'
VERSION = '1.4.8'
__version__ = VERSION
RELEASE_DATE = '2022-04-08'
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

print((_version+'  '+_copyright+'\n'+_disclaimer))

# transitioning tool
from . import qtapi
QtCore = qtapi.QtCore
QtGui = qtapi.import_module("QtGui")
QtWidgets = qtapi.import_module("QtWidgets")
QtMultimedia = qtapi.import_module("QtMultimedia")
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

# redirect stdout
#from . import console

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

from .parallel import *
parallel = Parallel()
