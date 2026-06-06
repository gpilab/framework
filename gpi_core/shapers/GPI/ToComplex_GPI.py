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


# Author: Jim Pipe
# Date: 2014Jan

import gpi


class ExternalNode(gpi.NodeAPI):

    """Node to read either real and imaginary or magnitude and phase data and convert to complex data

    INPUT:
    inLeft: input numpy array
    inRight: input numpy array

    OUTPUT:
    out:  output numpy array

    WIDGETS:
    Operation:  Determines what is done
      If both input ports (L and R) are populated
        L+iR - combines the two fields of same size to complex
          data inLeft - Real
          data inRight - Imaginary
        L exp(iR) - combines the two fields of same size to complex
          data inLeft - Magnitude
          data inRight - Phase
      If a single input port P is populated
        Real - output complex data with input's real channel and all zeros in the imaginary channel
        Imag - output complex data with input's imaginary channel and all zeros in the real channel
        Phase - output complex data with magnitude = 1 and phase given by input
        Vec2Cmplx - if the last dimension is 2, change this to R/I

     Phase: pick degrees or radians when appropriate

     OutType: single or double precision complex type
    """

    def initUI(self):
        self.addInPort('inLeft', 'NPYarray', obligation=gpi.OPTIONAL)
        self.addInPort('inRight', 'NPYarray', obligation=gpi.OPTIONAL)
        self.addOutPort('out', 'NPYarray')

        self.addWidget('ExclusiveRadioButtons', 'Operation', buttons=['Real', 'Imag', 'Phase', 'Vec2Cmplx'], val=0)
        self.addWidget('ExclusiveRadioButtons', 'Combine Operation', buttons=['L+iR', 'L exp(iR)'], val=0)

        self.addWidget('ExclusivePushButtons', 'Phase', buttons=['Deg', 'Rad', 'Cyc'], val=0)
        self.addWidget('ExclusivePushButtons', 'OutType', buttons=['Complex64', 'Complex128'], val=0)

    def validate(self):
        data1 = self.getData('inLeft')
        data2 = self.getData('inRight')
        singleCase = 0

        # No input ports connected
        if (data1 is None and data2 is None):
            self.setAttr('Operation', visible=False)
            self.setAttr('Combine Operation', visible=False)

        # Both input ports connected
        elif (data1 is not None and data2 is not None):
            if data1.shape != data2.shape:
                self.log.warn("data shapes must match")
                return(1)
            else:
                self.setAttr('Combine Operation', visible=True)
                self.setAttr('Operation', visible=False)

            if self.getVal('Combine Operation') == 1:
                self.setAttr('Phase', visible = True)
            else:
                self.setAttr('Phase', visible = False)

        # Left input port connected
        else:
            if data1 is not None:
                if data1.shape[-1] == 2:
                    singleCase = 1
            else:
                if data2.shape[-1] == 2:
                    singleCase = 2

            if singleCase != 0:
                self.setAttr('Operation', visible=True)
                self.setAttr('Combine Operation', visible=False)
                self.setAttr('Operation', buttons=['Real', 'Imag', 'Phase', 'Vec2Cmplx'])
            else:
                self.setAttr('Operation', visible=True)
                self.setAttr('Combine Operation', visible=False)
                self.setAttr('Operation', buttons=['Real', 'Imag', 'Phase'])

            if self.getVal('Operation') == 2:
                self.setAttr('Phase', visible = True)
            else:
                self.setAttr('Phase', visible = False)

        return(0)

    def compute(self):
        import numpy as np

        data1 = self.getData('inLeft')
        data2 = self.getData('inRight')
        op = self.getVal('Operation')
        cop = self.getVal('Combine Operation')
        phase = self.getVal('Phase')
        outtype = self.getVal('OutType')

        # Both ports connected: 'L+iR' or 'L exp(iR)'
        if (data1 is not None) and (data2 is not None):
            if cop == 0:  # L+iR
                out = data1 + 1j * data2
            elif cop == 1:  # L exp(iR)
                if phase == 0:  # Degrees
                    out = data1 * np.exp(1j * np.radians(data2))
                elif phase == 1: # radians
                    out = data1 * np.exp(1j * data2)
                else: # cycles
                    out = data1 * np.exp(1j * 2 * np.pi * data2)
            else:
                out = None

        # Left port connected
        elif (data1 is not None or data2 is not None):
            if data1 is None: # Swap if data1 is emtpy
                data1 = data2

            if op == 0:   # Real
                out = data1.astype(complex)
            elif op == 1:  # Imag
                out = data1 * 1j
            elif op == 2:  # Phase
                if phase == 0:  # Degrees
                    out = np.exp(1j * np.radians(data1))
                elif phase == 1: # Radians
                    out = np.exp(1j * data1)
                else: # cycles
                    out = np.exp(1j * 2 * np.pi * data1)
            elif op == 3:  # Vec2Cmplx
                if data1.shape[-1] != 2:
                    self.log.warn('The \'Vec2Cmplx\' option is not valid for vec != 2')
                    return 1
                out = data1[..., 0] + 1j * data1[..., 1]
            else:
                out = None

        # No port connected
        else:
            out = None

        # Output data if at least one port connected
        if out is not None:
            if outtype == 0:
                self.setData('out', out.astype(np.complex64))
            elif outtype == 1:
                self.setData('out', out.astype(np.complex128))

        return(0)
