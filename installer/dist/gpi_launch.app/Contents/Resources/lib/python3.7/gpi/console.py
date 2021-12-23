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

# Brief: tee stdout and stderr to a built-in console.
# TODO: 1) find a way to get stdout from c-pymods.
#       2) possibly integrate qconsole or similar terminal emulator to launch gpi


import sys

# gpi
import gpi
from gpi import QtCore

## rediect objects for stdout

class StreamBuf(object):

    def __init__(self, stdout):
        self._stdout = stdout
    
    def write(self, msg):
        self._stdout.write('gpi: '+msg)

    def flush(self):
        self._stdout.flush()

# support functions
# http://shallowsky.com/blog/programming/python-tee.html
class Tee(QtCore.QObject):
    '''(Mostly Unused) An attempt at providing console output to a GPI internal
    console window.  This is part of an unfinished feature that is meant to
    give the user easy access to logging information. '''

    newStreamTxt = gpi.Signal(str)

    def __init__(self, stdIO=None, parent=None):
        """Redirect to a pyqtSignal and stdIO stream.
        stdIO = alternate stream ( can be the original sys.stdout )
        """
        super(Tee, self).__init__(parent)
        self._stdIO = stdIO
        self._fromProc = False

    def setMultiProc(self, val=True):
        self._fromProc = val
    def isMultiProc(self):
        return self._fromProc

    def write(self, m):
        #if self._color and self._edit:
        #    tc = self._edit.textColor()
        #    self._edit.setTextColor(self._color)
#
#        if self._edit:
#            self._edit.moveCursor(QtGui.QTextCursor.End)
#            self._edit.insertPlainText( m )
#
#        if self._color and self._edit:
#            self._edit.setTextColor(tc)
#
        if not self.isMultiProc():
            self.newStreamTxt.emit(m)

        if self._stdIO:
            self._stdIO.write(m)

    def flush(self):
        self._stdIO.flush()



# tee both stdout and stderr for the console
#sys.stdout = StreamBuf(sys.stdout)
#sys.stderr = sys.stdout
