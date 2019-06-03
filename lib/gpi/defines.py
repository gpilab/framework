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

'''Miscellaneous constants used throughout GPI. These could be for z-buffer,
internal type conventions, uri conventions, etc...
'''


PREFIX='/opt/anaconda1anaconda2anaconda3'

import os
import sys
import inspect
import tempfile

#import gpi
from gpi import QtCore, QtGui, QtWidgets
from .logger import manager


# from:
# http://stackoverflow.com/questions/287871/print-in-terminal-with-colors-using-python
class Cl:
    HDR = '\033[95m'
    OKBL = '\033[94m'
    OKGR = '\033[92m'
    WRN = '\033[93m'
    FAIL = '\033[91m'
    ESC = '\033[0m'

# stringify and color - string-warn
def stw(s):
    return Cl.WRN+str(s)+Cl.ESC


# start logger for this module
log = manager.getLogger(__name__)

def terminalBell():
    #log.dialog('<< BELL >>')
    print('\a')

def GetHumanReadable_bytes(size, precision=2):
    # change size in bytes (int) to a string with nice display units
    suffixes = ['B', 'KB', 'MB', 'GB', 'TB']
    suffixIndex = 0
    while int(size) > 1024:
        suffixIndex += 1
        size = size / 1024.0
    return "%.*f %s" % (precision, size, suffixes[suffixIndex])

def GetHumanReadable_time(t, precision=3):
    # change seconds (float) to a string with nice display units
    t *= 1000.0  # sec -> msec
    suffixes = ['msec', 'sec', 'min', 'hrs', 'days', 'mo', 'yrs']
    div = [1000.0, 60.0, 60.0, 24.0, 30.0, 12.0]
    suffixIndex = 0
    while t > div[suffixIndex]:
        t = t / div[suffixIndex]
        suffixIndex += 1
        if suffixIndex >= len(div):
            break
    return "%.*f %s" % (precision, t, suffixes[suffixIndex])

def ThisFilePath():
    return os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe().f_back)))


# recursion limit info
log.info('Default Recursion Limit: '+str(sys.getrecursionlimit()))
# sys.setrecursionlimit(1500)
log.info('Set Recursion Limit: '+str(sys.getrecursionlimit()))

# location of gpi documents in the packaged distro
GPI_DOCS_DIR = PREFIX+'/share/doc/gpi'

# Node and module paths, local bundle should be searched first.
# The GPI_CWD only gives the path where gpi was invoked, not
# where it is located.
GPI_CWD = os.path.dirname(sys.argv[0])
#sys.path.insert(0, GPI_CWD)

RES_DIR = None
#if os.path.exists(GPI_CWD + "/_res"):
#    RES_DIR = GPI_CWD + "/_res"
#    sys.path.insert(0, RES_DIR)  # for packaging Linux
#elif os.path.exists(GPI_CWD + "/Contents/Resources/_res"):
#    RES_DIR = GPI_CWD + "/Contents/Resources/_res"
#    sys.path.insert(0, RES_DIR)  # for packaging OSX
#else:
#    RES_DIR = GPI_CWD + "/../"
#    sys.path.insert(0, GPI_CWD + "/../")  # for basic kcii setup
#log.debug(sys.path)

GPI_PKG_PATH=os.path.dirname(os.path.abspath( __file__ ))  # get location of THIS gpi python-package
LOGO_PATH = GPI_PKG_PATH+"/graphics/logo.png"
if not os.path.exists(LOGO_PATH):
    log.error("can't find logo.")
ICON_PATH = GPI_PKG_PATH+"/graphics/iclogo.png"
if not os.path.exists(ICON_PATH):
    log.error("can't find icon.")
PLOGO_PATH = GPI_PKG_PATH+"/graphics/slogo.png"
if not os.path.exists(PLOGO_PATH):
    log.error("can't find splash logo.")

# shared memory handles
GPI_SHDM_PATH_PREFIX = 'com.gpilab.GPI'
GPI_SHDM_PATH = tempfile.gettempdir()+'/'+GPI_SHDM_PATH_PREFIX
try:
    os.mkdir(GPI_SHDM_PATH)
    log.info('using shm path: '+GPI_SHDM_PATH)
except:
    log.info(GPI_SHDM_PATH+' already exists')
    if not os.access(GPI_SHDM_PATH, os.R_OK | os.W_OK | os.X_OK):
        GPI_SHDM_PATH = tempfile.mkdtemp(prefix=GPI_SHDM_PATH_PREFIX+'_')
        log.info('using shm path: '+GPI_SHDM_PATH)

#if os.path.exists(GPI_CWD + "/graphics/icons/logo.png"):
#    LOGO_PATH = GPI_CWD + "/graphics/icons/logo.png"
#elif RES_DIR:
#    if os.path.exists(RES_DIR + "/logo.png"):
#        LOGO_PATH = RES_DIR + "/logo.png"
#if LOGO_PATH is None:
#    log.error("can't find logo.")

# qt custom types
UserTYPE = QtWidgets.QGraphicsItem.UserType
EdgeTYPE = UserTYPE + 1
NodeTYPE = UserTYPE + 2
PortTYPE = UserTYPE + 3
InPortTYPE = UserTYPE + 4
OutPortTYPE = UserTYPE + 5
WidgetTYPE = UserTYPE + 6
ExternalNodeType = UserTYPE + 7
ExternalType = UserTYPE + 8
MacroNodeEdgeType = UserTYPE + 9
EdgeNodeType = UserTYPE + 10
PortEdgeType = UserTYPE + 11

def isMacroChildNode(inst):
    '''Determine if its a child node of a macro-node.
    '''
    if hasattr(inst, 'Type'):
        if inst.Type == PortEdgeType:
            return True
    return False

def isNode(inst):
    '''Determine if its a Node or descendent of a node.
    '''
    if hasattr(inst, 'Type'):
        if inst.Type == NodeTYPE:
            return True
    return False

def isWidget(inst):
    '''Determine if its a GPI Widget or descendent of a GenericWidgetGroup.
    '''
    if hasattr(inst, 'GPIWdgType'):
        if inst.GPIWdgType == WidgetTYPE:
            return True
    return False

def isGPIType(inst):
    '''Determine if the object is a GPIType description.
    '''
    if hasattr(inst, 'GPIType'):
        if inst.GPIType == ExternalType:
            return True
    return False

def isExternalNode(inst):
    '''Determine if the object is an ExternalNodeType description (NodeAPI).
    '''
    if hasattr(inst, 'GPIExtNodeType'):
        if inst.GPIExtNodeType == ExternalNodeType:
            return True
    return False


# global definitions
REQUIRED = 100
OPTIONAL = 200

# execution types
GPI_THREAD = 1000
GPI_PROCESS = 2000
GPI_APPLOOP = 3000

# limits
GPI_FLOAT_MAX = sys.float_info.max
GPI_FLOAT_MIN = -sys.float_info.max
GPI_FLOAT_MINSTEP = sys.float_info.min
GPI_INT_MAX = pow(2, 31) - 1  # max QWidgets can use
GPI_INT_MIN = -pow(2, 31)  # min QWidgets can use

# node state events
GPI_WIDGET_EVENT = '_WDG_EVENT_'
GPI_PORT_EVENT = '_PORT_EVENT_'
GPI_INIT_EVENT = '_INIT_EVENT_'
GPI_REQUEUE_EVENT = '_REQUEUE_EVENT_'

# python module file types
GPI_PYMOD_EXTS = ['.py', '.pyc', '.pyo', '.pyd']
GPI_PYMOD_PRE_EXT = '_GPI'
GPI_TYPE_EXTS = ['.py', '.pyc', '.pyo', '.pyd']
GPI_TYPE_PRE_EXT = '_GPITYPE'
GPI_NET_EXTS = ['.net']

def isGPIModFile(path):
    '''Determine if the path exists, isfile, endswith _GPI, and valid ext.
    '''
    if os.path.isfile(path):
        bname, ext = os.path.splitext(path)
        if bname.endswith(GPI_PYMOD_PRE_EXT) and (ext.lower() in GPI_PYMOD_EXTS):
            return True
    return False

def isGPITypeFile(path):
    '''Determine if the path exists, isfile, endswith _GPITYPE, and valid ext.
    '''
    if os.path.isfile(path):
        bname, ext = os.path.splitext(path)
        if bname.endswith(GPI_TYPE_PRE_EXT) and (ext.lower() in GPI_PYMOD_EXTS):
            return True
    return False

def isGPINetworkFile(path):
    '''Determine if the path exists, isfile, and valid ext.
    '''
    if os.path.isfile(path):
        bname, ext = os.path.splitext(path)
        if ext.lower() in GPI_NET_EXTS:
            return True
    return False


def TranslateFileURI(uri):
    '''Translate the given uri to a local path.
    '''
    # Check for cwd:// protocol, this will
    # grab cwd and replace it with the GPI_CWD.
    # NOTE: useful for packaging example networks
    # that point to relative data paths.
    if uri.startswith('cwd://'):
        # uri = GPI_CWD+'/'+uri.split('cwd://')[1]
        uri = RES_DIR + '/' + uri.split('cwd://')[1]
    # just strip the 'file://' URI
    elif uri.startswith('file://'):
        uri = uri.split('file://')[1]
    # exapand user $HOME
    elif uri.startswith('~/'):
        uri = os.path.expanduser(uri)

    return uri


def getKeyboardModifiers(supress=False):
    '''Just for testing purposes, replaces
    QtWidgets.QApplication.keyboardModifiers()
    '''
    #supress = True  # force off
    mod = QtWidgets.QApplication.keyboardModifiers()
    if not supress:
        if mod == QtCore.Qt.NoModifier:
            log.debug(" KeyboardMods: NoModifier")
        if mod == QtCore.Qt.ShiftModifier:
            log.debug(" KeyboardMods: ShiftModifier")
        if mod == QtCore.Qt.ControlModifier:
            log.debug(" KeyboardMods: ControlModifier")
        if mod == QtCore.Qt.AltModifier:
            log.debug(" KeyboardMods: AltModifier")
        if mod == QtCore.Qt.MetaModifier:
            log.debug(" KeyboardMods: MetaModifier")
        if mod == QtCore.Qt.KeypadModifier:
            log.debug(" KeyboardMods: KeypadModifier")
        if mod == QtCore.Qt.GroupSwitchModifier:
            log.debug(" KeyboardMods: GroupSwitchModifier")
    return mod


def printMouseEvent(event, supress=False):
    #supress = True
    if not supress:
        if event.buttons() & QtCore.Qt.LeftButton:
            log.debug(" Mouse: LeftButton")
        if event.buttons() & QtCore.Qt.RightButton:
            log.debug(" Mouse: RightButton")
        if event.buttons() & QtCore.Qt.MidButton:
            log.debug(" Mouse: MidButton")

