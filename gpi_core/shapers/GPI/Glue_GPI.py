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
# Date: 2013Aug

import gpi

class ExternalNode(gpi.NodeAPI):
    """Node to serially append input data to output data in specified direction

    INPUT: input numpy array

    OUTPUT: data containing glued-together pieces of input data

    WIDGETS:
    Autoadd: when true, any new incoming data automatically gets glued to
        output data
    Add Now: when pressed, existing data at input port is glued to output data
    Glue Dimension: dimension in which to glue input data together
        A negative one here means a "new" dim 0, not the typical python -1
        wrapped dim. Once the gluing starts, this cannot be changed until
        output data are cleared
    Glue Dim Size: Reports back size along the gluing dimension
    Clear Output: Press twice in a row to clear output data (must press
        twice!).
    """

    def initUI(self):
        # Widgets
        self.addWidget('PushButton', 'AutoAdd',
                       button_title='OFF', toggle=True)
        self.addWidget('PushButton', 'Add Now',
                       button_title='ADD', toggle=False)
        self.addWidget('Slider', 'Glue Dimension', min=-1, max=0, val=-1)
        self.addWidget('SpinBox', 'Glue Dim Size', min=0, max=0, val=0)
        self.addWidget('PushButton', 'Clear Output',
                       button_title='RESET OUTPUT', toggle=True)

        # IO Ports
        self.addInPort('indat', 'NPYarray')
        self.addOutPort('outdat', 'NPYarray')

    def validate(self):

        # Must Press 'Clear Output' twice in a row, for safety
        # Any other event after first press will reset 'Clear Output'
        if 'Clear Output' in self.widgetEvents():
            if self.getVal('Clear Output'):
                self.setAttr('Clear Output', button_title='PRESS TO CONFIRM')
            else:
                self.setAttr('Clear Output', button_title='RESET OUTPUT')
        else:
            if self.getVal('Clear Output'):
                self.setAttr('Clear Output', val=0)
                self.setAttr('Clear Output', button_title='RESET OUTPUT')

        # When building data, don't let user change dimensions
        out = self.getData('outdat')
        if out is not None:
            fixdim = self.getVal('Glue Dimension')
            self.setAttr('Glue Dimension', min = fixdim, max = fixdim)
        else:
            data = self.getData('indat')
            if data is not None:
                self.setAttr('Glue Dimension', min = -1, max=data.ndim)

        if self.getVal('AutoAdd'):
            self.setAttr('AutoAdd', button_title='ON')
        else:
            self.setAttr('AutoAdd', button_title='OFF')

        return 0

    def compute(self):
        '''This is where the main algorithm should be implemented.
        '''
        import numpy as np

        indata  = self.getData('indat')
        outdata = self.getData('outdat')
        gd = self.getVal('Glue Dimension')
        gd0 = max(gd, 0) # when gd is -1, need to make it 0 for some calcs

        # Clear output data on 2nd click of 'Clear Output'
        if 'Clear Output' in self.widgetEvents():
            if not self.getVal('Clear Output'):
                outdata = None

        else:
            if self.getVal('AutoAdd') or self.getVal('Add Now'):
                # Add an extra dimension to indata if glueing in that direction
                if gd == indata.ndim:
                    indata = np.expand_dims(indata, gd)
                if gd == -1:
                    indata = np.expand_dims(indata, 0)

                if outdata is None:
                    outdata = indata.copy()
                    self.setAttr('Glue Dimension',min=gd,max=gd,val=gd)
                else:
                    outdata = np.append(outdata, indata,axis=gd0)

        if outdata is not None:
            gds = np.array(outdata.shape)[gd0]
            self.setAttr('Glue Dim Size', min=gds, max=gds, val=gds)
        else:
            self.setAttr('Glue Dim Size', min=0, max=0, val=0)
            if indata is not None:
                self.setAttr('Glue Dimension', min=-1, max=indata.ndim)
            else:
                self.setAttr('Glue Dimension', min=-1, max=0, val=-1)

        self.setData('outdat', outdata)

        return 0

    def execType(self):
        '''Could be GPI_THREAD, GPI_PROCESS, GPI_APPLOOP'''
        return gpi.GPI_THREAD
