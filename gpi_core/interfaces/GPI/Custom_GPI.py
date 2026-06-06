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
import sys
from textwrap import dedent
import traceback


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

        self.addWidget('TextBox', 'Status', val='Ready.')

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

    def compute(self):

        import sys

        code = str(self.getVal('Python Code'))

        try:
            self.setAttr('Status', val='Running input user code.')
            exec(code)
            self.setAttr('Status', val='User code executed successfully.')
            self.setAttr('Status', val='Ready.')

        except:
            self.log.warn("ERROR: User code failed to execute!")
            self.setData('out1', None)
            self.setData('out2', None)
            self.setData('out3', None)
            self.setData('out4', None)

            txt = "ERROR: User code failed to execute:\n\n"
            txt += traceback.format_exc()

            self.setAttr('Status', val=txt)

        return(0)
