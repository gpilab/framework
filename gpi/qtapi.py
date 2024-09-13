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

from .logger import manager
# start logger for this module
log = manager.getLogger(__name__)

import qtpy
import qtpy.QtCore as _QtCore
API_NAME = qtpy.API_NAME
API_NAME = API_NAME.split(' ')[0]  # truncate e.g. 'PyQt4 (API v2)' to 'PyQt4'

QtCore = _QtCore

def import_module(moduleName):
    p = __import__('qtpy', globals(), locals(), [moduleName], 0)
    return getattr(p, moduleName)

# QtWebKit or QtWebEngine may not be available. The modules will be set to None
# in this case. QtOpenGL is also deprecated in modern Qt.
def import_optional_module(moduleName):
    try:
        p = __import__(API_NAME, globals(), locals(), [moduleName], 0)
        return getattr(p, moduleName)
    except (AttributeError,ImportError) as e:
        return None

QtOpenGL = import_optional_module('QtOpenGL')
QtWebKit = import_optional_module('QtWebKit')
QtWebKitWidgets = import_optional_module('QtWebKitWidgets')
QtWebEngineWidgets = import_optional_module('QtWebEngineWidgets')

try:
    # PyQt4 and PySide
    QWebView = QtWebKit.QWebView
except AttributeError:
    QWebView = None
    if QtWebKitWidgets is not None:
        try:
            # PyQt5 and PySide2
            QWebView = QtWebKitWidgets.QWebView
        except:
            pass

Signal = QtCore.Signal
Slot = QtCore.Slot
Property = QtCore.Property
