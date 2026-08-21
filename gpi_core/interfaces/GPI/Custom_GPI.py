# Copyright (c) 2014, Dignity Health
# 
#     The GPI core node library is licensed under
# either the BSD 3-clause or the LGPL v. 3.
# 
#     Under either license, the following additional term applies:
# 
#         NO CLINICAL USE.  THE SOFTWARE IS NOT INTENDED FOR COMMERCIAL
# PURPOSES AND SHOULD BE USED ONLY FOR NON-COMMERCIAL RESEARCH PURPOSES.  THE
# SOFTWARE MAY NOT IN ANY EVENT BE USED FOR ANY CLINICAL OR DIAGNOSTIC
# PURPOSES.  YOU ACKNOWLEDGE AND AGREE THAT THE SOFTWARE IS NOT INTENDED FOR
# USE IN ANY HIGH RISK OR STRICT LIABILITY ACTIVITY, INCLUDING BUT NOT LIMITED
# TO LIFE SUPPORT OR EMERGENCY MEDICAL OPERATIONS OR USES.  LICENSOR MAKES NO
# WARRANTY AND HAS NOR LIABILITY ARISING FROM ANY USE OF THE SOFTWARE IN ANY
# HIGH RISK OR STRICT LIABILITY ACTIVITIES.
# 
#     If you elect to license the GPI core node library under the LGPL the
# following applies:
# 
#         This file is part of the GPI core node library.
# 
#         The GPI core node library is free software: you can redistribute it
# and/or modify it under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation, either version 3 of the License,
# or (at your option) any later version. GPI core node library is distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even
# the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU Lesser General Public License for more details.
# 
#         You should have received a copy of the GNU Lesser General Public
# License along with the GPI core node library. If not, see
# <http://www.gnu.org/licenses/>.


# Author: Nick Zwart
# Date: 2012oct28

import gpi
from gpi import QtCore
import os
import sys
from textwrap import dedent
import traceback

# exec()'d under this filename so tracebacks/SyntaxErrors can be traced back
# to a line in the 'Python Code' widget instead of showing '<string>'.
_CODE_FILENAME = '<Custom Node Code>'

# how long to wait after the last keystroke before re-checking syntax
_SYNTAX_CHECK_DELAY_MS = 400


def _user_frames(tb):
    '''Split a traceback's frames into (noise, user) at the first frame that
    belongs to the exec()'d code, so internal GPI call frames can be hidden.'''
    frames = traceback.extract_tb(tb)
    for i, f in enumerate(frames):
        if f.filename == _CODE_FILENAME:
            return frames[i:]
    return frames


class ExternalNode(gpi.NodeAPI):
    """This node provides a simple code input interface and editor for
    generating Python code to be executed in the node compute() on-the-fly.
    The editor includes syntax highlighting.  The four InPorts provided are
    labeled: 'in1', 'in2', 'in3', and 'in4' (similarly for the OutPorts).  This
    code is run in a Python exec statement and therefore has associated
    limitations (e.g. return statements).  New widgets cannot be added to the
    widget interface, however, packages that contain UI elements can be spawned
    using the Execution-Type 'Main Loop'.
    """

    def execType(self):
        # skip execType recursion by getting val from widget directly
        op = self.getWidget('Execution Type').get_val()
        if op == 0:
            return gpi.GPI_THREAD
        if op == 1:
            return gpi.GPI_PROCESS
        if op == 2:
            return gpi.GPI_APPLOOP

    def initUI(self):
        self.procType = gpi.GPI_APPLOOP

        self.addWidget('TextEdit', 'Status', val='Ready.',
                       readonly=True, highlight=False)

        code = '\n'.join((
            "in1 = self.getData('in1')",
            "in2 = self.getData('in2')",
            "in3 = self.getData('in3')",
            "in4 = self.getData('in4')",
            "",
            "import numpy as np",
            "# your code here...",
            "",
            "self.setData('out1', None)",
            "self.setData('out2', None)",
            "self.setData('out3', None)",
            "self.setData('out4', None)"))

        # Widgets
        self.addWidget('TextEdit', 'Python Code', val=code)
        self.addWidget('PushButton', 'Compute', button_title='Compute')
        self.addWidget('ExclusiveRadioButtons', 'Execution Type',
                       buttons=['Thread', 'Process', 'Main Loop'],
                       val=1, collapsed=True)

        # IO Ports
        self.addInPort('in1', 'PASS', obligation=gpi.OPTIONAL)
        self.addInPort('in2', 'PASS', obligation=gpi.OPTIONAL)
        self.addInPort('in3', 'PASS', obligation=gpi.OPTIONAL)
        self.addInPort('in4', 'PASS', obligation=gpi.OPTIONAL)
        self.addOutPort('out1', 'PASS')
        self.addOutPort('out2', 'PASS')
        self.addOutPort('out3', 'PASS')
        self.addOutPort('out4', 'PASS')

        # live syntax check, debounced -- purely a UI convenience, never
        # touches ports/data so it's safe regardless of Execution Type.
        # initUI() is replayed inside GPI_PROCESS workers too (so instance
        # attrs like self._syntax_timer exist there), but getWidget() only
        # returns real widgets in the main GUI process -- skip the direct
        # Qt signal connection there.
        self._syntax_timer = QtCore.QTimer()
        self._syntax_timer.setSingleShot(True)
        self._syntax_timer.setInterval(_SYNTAX_CHECK_DELAY_MS)
        self._syntax_timer.timeout.connect(self._check_syntax)
        if os.environ.get('GPI_WORKER_MODE') != '1':
            self.getWidget('Python Code').wdg.textChanged.connect(
                self._syntax_timer.start)

    def _check_syntax(self):
        code_widget = self.getWidget('Python Code')
        code_widget.clear_error_line()
        try:
            compile(code_widget.get_val(), _CODE_FILENAME, 'exec')
        except SyntaxError as e:
            if e.lineno is not None:
                code_widget.highlight_error_line(e.lineno)
            self.setAttr('Status', val="SYNTAX ERROR at line {}, column {}: {}"
                          .format(e.lineno, e.offset, e.msg))
            return
        self.setAttr('Status', val='Syntax OK.')

    def compute(self):

        import sys

        code = str(self.getVal('Python Code'))
        # use setAttr() rather than getWidget() -- under GPI_PROCESS, self is
        # a NodeComputeStub with no widget objects, and setAttr() is the
        # mechanism that marshals widget updates back to the main process
        # regardless of Execution Type.
        self.setAttr('Python Code', error_line=None)

        try:
            compiled = compile(code, _CODE_FILENAME, 'exec')
        except SyntaxError as e:
            self.log.warn("ERROR: User code failed to compile!")
            self.setData('out1', None)
            self.setData('out2', None)
            self.setData('out3', None)
            self.setData('out4', None)

            if e.lineno is not None:
                self.setAttr('Python Code', error_line=e.lineno)
            txt = "SYNTAX ERROR at line {}, column {}:\n{}\n{}\n{}".format(
                e.lineno, e.offset, e.msg, e.text or '',
                ' ' * (max(e.offset or 1, 1) - 1) + '^')
            self.setAttr('Status', val=txt)
            return 1

        try:
            self.setAttr('Status', val='Running input user code.')
            exec(compiled)
            self.setAttr('Status', val='User code executed successfully.')
            self.setAttr('Status', val='Ready.')

        except Exception:
            self.log.warn("ERROR: User code failed to execute!")
            self.setData('out1', None)
            self.setData('out2', None)
            self.setData('out3', None)
            self.setData('out4', None)

            # find the deepest frame that's actually in the user's code
            # (vs. this node's own exec() call site) to report/highlight,
            # and strip the internal GPI frames above it from what's shown.
            exc_type, exc_value, tb = sys.exc_info()
            user_frames = _user_frames(tb)
            full_tb = ''.join(
                traceback.format_list(user_frames) +
                traceback.format_exception_only(exc_type, exc_value))

            if user_frames and user_frames[-1].filename == _CODE_FILENAME:
                lineno = user_frames[-1].lineno
                self.setAttr('Python Code', error_line=lineno)
                txt = "ERROR at line {}: {}\n\n{}".format(
                    lineno, user_frames[-1].line or '', full_tb)
            else:
                txt = "ERROR: User code failed to execute:\n\n" + full_tb

            self.setAttr('Status', val=txt)

        return(0)
