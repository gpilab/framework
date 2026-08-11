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
    '''Redirects a stdio stream to a pyqtSignal (for a live console window)
    while also keeping a capped, shared history buffer so the console window
    can be closed by default and still show everything printed before it was
    opened. '''

    newStreamTxt = gpi.Signal(str)
    errorWritten = gpi.Signal(str)   # emitted for stderr text or ERROR/CRITICAL log lines

    # Shared (class-level) so both the stdout and stderr Tee instances write
    # into the same interleaved history, independent of whether any console
    # window/widget has ever been created. Entries are (text, is_stderr) so
    # a console window opened late can still colorize its prefilled history.
    _MAX_BUFFER_CHARS = 200_000
    _buffer = []
    _buffer_len = 0

    def __init__(self, stdIO=None, parent=None, is_stderr=False):
        """Redirect to a pyqtSignal and stdIO stream.
        stdIO = alternate stream ( can be the original sys.stdout )
        is_stderr = True if this wraps stderr (all stderr text is treated as
            an error, since GPI only writes tracebacks/faulthandler dumps there)
        """
        super(Tee, self).__init__(parent)
        self._stdIO = stdIO
        self._fromProc = False
        self._is_stderr = is_stderr

    def setMultiProc(self, val=True):
        self._fromProc = val
    def isMultiProc(self):
        return self._fromProc

    @classmethod
    def get_buffered_text(cls):
        """Everything written so far, e.g. to prefill a console window opened late."""
        return ''.join(t for t, _ in cls._buffer)

    @classmethod
    def get_buffered_entries(cls):
        """[(text, is_stderr), ...] written so far, for a colorized prefill."""
        return list(cls._buffer)

    def write(self, m):
        if not self.isMultiProc():
            Tee._buffer.append((m, self._is_stderr))
            Tee._buffer_len += len(m)
            while Tee._buffer_len > Tee._MAX_BUFFER_CHARS and Tee._buffer:
                dropped, _ = Tee._buffer.pop(0)
                Tee._buffer_len -= len(dropped)

            self.newStreamTxt.emit(m)

            if m.strip() and (self._is_stderr or ' - ERROR - ' in m or ' - CRITICAL - ' in m):
                self.errorWritten.emit(m)

        if self._stdIO:
            self._stdIO.write(m)

    def flush(self):
        if self._stdIO:
            self._stdIO.flush()



# tee both stdout and stderr for the console
#sys.stdout = StreamBuf(sys.stdout)
#sys.stderr = sys.stdout
