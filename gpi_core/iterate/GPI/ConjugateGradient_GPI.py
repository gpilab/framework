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
import numpy as np


class ExternalNode(gpi.NodeAPI):
    """A node that allows cyclic connections and provides a countdown for
    iterative algorithms using the conjugate gradient approach.  The code tries to
    match the nomenclature of the excellent article by Jonathan Richard Shewchuk,
    An Introduction to the Conjugate Gradient Methods Without the Agonizing Pain
    and in particular equations 45-49 on page 32 of that manuscript.

    The node will automatically step through a specified number of iterations

    So we are solving for Ax = b
    INPUTS: The first four inputs are initialization, the last one is for iteration
    d_in - initial guess for direction to move, equals b-Ax (Eq. 45)
    r_in - initial guess, same as d_in, equals b-Ax (Eq. 45)
    x_in - initial guess for x
    Ad_in - matrix A times d_in
    Adloop_in - used during iterations, this takes A multiplied by d_out (below)

    OUTPUTS:
    d_out - multiply this vector by A and send back to Adloop_in
    r_out - not really used, just FYI
    x_out - the final answer

    WIDGETS:
    Current Iteration - lets you know which iteration is being performed
    Max Iteration - enter the desired number of iterations
    Start/Stop - click on to start, click off to stop before iterations are done
    Step - click to step through one more iteration
    Reset - click to reset iteration count and begin with initial conditions
    """

    def initUI(self):
        # Widgets
        self.addWidget(wdg='TextBox', title='Current Iteration', val='0')
        self.addWidget(wdg='SpinBox', title='Max Iteration', min=0)
        self.addWidget(wdg='PushButton', title='Start/Stop', toggle=True)
        self.addWidget(wdg='PushButton', title='Step')
        self.addWidget(wdg='PushButton', title='Reset')

        # IO Ports
        self.addInPort(title='d_in', type='NPYarray')
        self.addInPort(title='r_in', type='NPYarray')
        self.addInPort(title='x_in', type='NPYarray')
        self.addInPort(title='Ad_in', type='NPYarray')
        self.addInPort(title='Adloop_in', type='NPYarray', obligation=gpi.OPTIONAL, cyclic=True)

        self.addOutPort(title='d_out', type='NPYarray')
        self.addOutPort(title='r_out', type='NPYarray')
        self.addOutPort(title='x_out', type='NPYarray')

    def validate(self):
        '''This function runs before compute() as a GPI_APPLOOP exec-type.
        Here, widgets (bounds, limits, etc...) can be modified to ensure they
        are correctly validated before the widget values are used in the
        compute() routine -where widgets are buffered and any modifications are
        applied after compute() runs.
        '''

        # if init changes then reset the count and stop iteration
        if set(self.portEvents()).intersection(set(['d_in', 'r_in', 'x_in', 'Ad_in'])):
            self.setAttr('Reset', val=True)

        return 0

    def compute(self):
        '''This is where the main algorithm should be implemented.
        '''
        reset = self.getVal('Reset')
        on = self.getVal('Start/Stop')
        iternum = int(self.getVal('Current Iteration'))
        maxiter = self.getVal('Max Iteration')
        step = self.getVal('Step')

        if step:
            maxiter += 1
            self.setAttr('Max Iteration', val=maxiter)
            on = True
            self.setAttr('Start/Stop', val=on)

        if reset:
            self.setAttr('Start/Stop', val=False)
            self.setAttr('Current Iteration', val='0')
            d_in = self.getData('d_in')
            r_in = self.getData('r_in')
            x_in = self.getData('x_in')
            self.setData('d_out', d_in)
            self.setData('r_out', r_in)
            self.setData('x_out', x_in)

        elif on:
            if iternum >= maxiter:
                self.setAttr('Start/Stop', val=False)
                return 0
            elif iternum == 0:
                self.setAttr('Current Iteration', val=str(iternum+1))

                d_in = self.getData('d_in')
                r_in = self.getData('r_in')
                x_in = self.getData('x_in')
                Ad_in = self.getData('Ad_in')

                (d_out, r_out, x_out) = self.do_cg(d_in, r_in, x_in, Ad_in)

                self.setData('d_out', d_out)
                self.setData('r_out', r_out)
                self.setData('x_out', x_out)

            else:
                self.setAttr('Current Iteration', val=str(iternum+1))

                Adloop_in = self.getData('Adloop_in')

                # copy last iter
                d_in = self.getData('d_out')
                r_in = self.getData('r_out')
                x_in = self.getData('x_out')

                (d_out, r_out, x_out) = self.do_cg(d_in, r_in, x_in, Adloop_in)

                self.setData('d_out', d_out)
                self.setData('r_out', r_out)
                self.setData('x_out', x_out)
        else:
            self.setData('d_out', None)
            self.setData('r_out', None)
            self.setData('x_out', None)

        return 0

    def execType(self):
        '''Could be GPI_THREAD, GPI_PROCESS, GPI_APPLOOP'''
        return gpi.GPI_THREAD


    def do_cg(self, d_in, r_in, x_in, Ad_in):

        d_out = np.zeros_like(d_in)
        r_out = np.zeros_like(r_in)
        x_out = np.zeros_like(x_in)

        # Calculate alpha
        # r^H r / (d^H Ad)
        rHr = np.dot(np.conj(r_in.flatten()), r_in.flatten()) 
        dHAd = np.dot(np.conj(d_in.flatten()), Ad_in.flatten())
        alpha = rHr/dHAd

        # Calculate x(i+1)
        # x(i) + alpha d(i)
        x_out = x_in + alpha * d_in

        # Calculate r(i+1)
        # r(i) - alpha Ad(i)
        r_out = r_in - alpha * Ad_in

        # Calculate beta
        # r(i+1)^H r(i+1) / (r(i)^H r(i))
        r1Hr1 = np.dot(np.conj(r_out.flatten()), r_out.flatten()) 
        beta = r1Hr1 / rHr

        # Calculate d(i+1)
        # r(i+1) + beta d(i)
        d_out = r_out + beta * d_in

        return (d_out, r_out, x_out)

