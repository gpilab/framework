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

# Brief: This setup can be used to force the APIv2 for future compatibility.

import os

from .logger import manager
# start logger for this module
log = manager.getLogger(__name__)

def import_module(moduleName):
    p = __import__('PyQt4', globals(), locals(), [moduleName], 0)
    return getattr(p, moduleName)

on_rtd = os.environ.get('READTHEDOCS', None) == 'True'
if not on_rtd:
    import sip
    # To determine which API's to set:
    #   http://pyqt.sourceforge.net/Docs/PyQt4/incompatible_apis.html
    _APIv2 = True
    if _APIv2:
        sip.setapi('QDate', 2)
        sip.setapi('QDateTime', 2)
        sip.setapi('QString', 2)
        sip.setapi('QTextStream', 2)
        sip.setapi('QTime', 2)
        sip.setapi('QUrl', 2)
        sip.setapi('QVariant', 2)

    # stub in PyQt4 imports
    import PyQt4.QtCore as _QtCore
    QtCore = _QtCore

    Signal = QtCore.pyqtSignal
    Slot = QtCore.pyqtSlot
    Property = QtCore.pyqtProperty

else: # READTHEDOCS

    # mock Qt when we are generating documentation at readthedocs.org
    class Mock(object):
        def __init__(self, *args, **kwargs):
            pass
    
        def __call__(self, *args, **kwargs):
            return Mock()
    
        @classmethod
        def __getattr__(cls, name):
            if name in ('__file__', '__path__'):
                return '/dev/null'
            elif name in ('__name__', '__qualname__'):
                return name
            elif name == '__annotations__':
                return {}
            else:
                return Mock()
    
    QtGui = Mock()
    QtCore = Mock()
    QtTest = Mock()
    Qt = Mock()
    QEvent = Mock()
    QApplication = Mock()
    QWidget = Mock()
    qInstallMsgHandler = Mock()
    qInstallMessageHandler = Mock()
    qDebug = Mock()
    qWarning = Mock()
    qCritical = Mock()
    qFatal = Mock()
    QtDebugMsg = Mock()
    QtWarningMsg = Mock()
    QtCriticalMsg = Mock()
    QtFatalMsg = Mock()
    QT_API = '<none>' 

    Signal = Mock()
    Slot = Mock()
    Property = Mock()
