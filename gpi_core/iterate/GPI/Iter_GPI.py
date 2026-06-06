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
# Date: 2012dec10

import gpi


class ExternalNode(gpi.NodeAPI):
    """A node that allows cyclic connections and provides a countdown for
    iterative algorithms.

    INPUTS:
    n+1 - input for iterations, typically data taken from output "n" and processed 
    n_0 - initial condition

    OUTPUT:
    n - value of data at nth iteration

    WIDGETS:
    Current Iteration - reports current iteration index
    Max Iteration - enter number of desired iterations
    Start/Stop - starts/stops iterations
    Reset - resets iteration count to zero and data to initial condition (at input n_0)
    """

    def initUI(self):
        # Widgets
        self.addWidget(wdg='TextBox', title='Current Iteration', val='0')
        self.addWidget(wdg='SpinBox', title='Max Iteration', min=0)
        self.addWidget(wdg='PushButton', title='Start/Stop', toggle=True)
        self.addWidget(wdg='PushButton', title='Reset')

        # IO Ports
        self.addInPort(title='n+1', type='PASS', obligation=gpi.OPTIONAL, cyclic=True)
        self.addInPort(title='n_0', type='PASS', obligation=gpi.REQUIRED)
        self.addOutPort(title='n', type='PASS')

    def validate(self):
        '''This function runs before compute() as a GPI_APPLOOP exec-type.
        Here, widgets (bounds, limits, etc...) can be modified to ensure they
        are correctly validated before the widget values are used in the
        compute() routine -where widgets are buffered and any modifications are
        applied after compute() runs.
        '''

        # if init changes then reset the count and stop iteration
        if 'n_0' in self.portEvents():
            self.setAttr('Reset', val=True)

        return 0

    def compute(self):
        '''This is where the main algorithm should be implemented.
        '''
        reset = self.getVal('Reset')
        on = self.getVal('Start/Stop')
        iternum = int(self.getVal('Current Iteration'))
        maxiter = self.getVal('Max Iteration')
        np1 = self.getData('n+1')
        init = self.getData('n_0')

        if reset:
            self.setAttr('Start/Stop', val=False)
            self.setAttr('Current Iteration', val='0')
            self.setData('n', init)

        elif on:
            if iternum >= maxiter:
                self.setAttr('Start/Stop', val=False)
                return 0
            elif iternum == 0:
                self.setAttr('Current Iteration', val=str(iternum+1))
                self.setData('n', init)
            else:
                self.setAttr('Current Iteration', val=str(iternum+1))
                self.setData('n', np1)

        else:
            self.setData('n', None)

        if (maxiter-1) > 0:
            self.setStatus(str(iternum*100.0/(maxiter-1)) + "%")

        return 0

    def execType(self):
        '''Could be GPI_THREAD, GPI_PROCESS, GPI_APPLOOP'''
        return gpi.GPI_THREAD
