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
#    MAKES NO WARRANTY AND HAS NOR LIABILITY ARISING FROM ANY USE OF THE
#    SOFTWARE IN ANY HIGH RISK OR STRICT LIABILITY ACTIVITIES.

# All methods, defs and members needed by node developers must be imported
# automatically into the gpi namespace.  This way users only need to
# import gpi, then use things like gpi.REQUIRED for ports etc...
import warnings
warnings.filterwarnings("ignore", ".*Applications.GPI.*import.*")

VERSION = '1.0.0'
RELEASE_DATE = '2015Sep22'

# Print version info each time.
_version = 'GPI '+VERSION+' ('+RELEASE_DATE+')'
_copyright = 'Copyright (C) 2014 Dignity Health'
_disclaimer = '''\
This program comes with ABSOLUTELY NO WARRANTY; see the LICENSE for details.

    NO CLINICAL USE.  THE SOFTWARE IS NOT INTENDED FOR COMMERCIAL PURPOSES
AND SHOULD BE USED ONLY FOR NON-COMMERCIAL RESEARCH PURPOSES.  THE SOFTWARE
MAY NOT IN ANY EVENT BE USED FOR ANY CLINICAL OR DIAGNOSTIC PURPOSES.  YOU
ACKNOWLEDGE AND AGREE THAT THE SOFTWARE IS NOT INTENDED FOR USE IN ANY HIGH
RISK OR STRICT LIABILITY ACTIVITY, INCLUDING BUT NOT LIMITED TO LIFE SUPPORT
OR EMERGENCY MEDICAL OPERATIONS OR USES.  LICENSOR MAKES NO WARRANTY AND HAS
NOR LIABILITY ARISING FROM ANY USE OF THE SOFTWARE IN ANY HIGH RISK OR STRICT
LIABILITY ACTIVITIES.
'''

print((_version+'  '+_copyright+'\n'+_disclaimer))

# transitioning tool
from . import qtapi
QtCore = qtapi.QtCore
QtGui = qtapi.import_module("QtGui")
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
