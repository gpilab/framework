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


# Author: Payal Bhavsar
# Date: 2013Nov18

import gpi

class ExternalNode(gpi.NodeAPI):
    """A module for writing NPY arrays to a comma separated value list in ASCII text.

    INPUT: Numpy array to write to file

    WIDGETS:
    File Browser - button to launch file browser, and typein widget if the pathway is known.
    Write Mode - write at any event, or write only with new filename
    Write Now - write right now
    """

    def initUI(self):
       # Widgets
        self.addWidget(
            'SaveFileBrowser', 'File Browser', button_title='Browse',
            caption='Save File (*.csv)', filter='Comma Seperated Values (*.csv)')
        self.addWidget('PushButton', 'Write Mode', button_title='Write on New Filename', toggle=True)
        self.addWidget('PushButton', 'Write Now', button_title='Write Right Now', toggle=False)

        # IO Ports
        self.addInPort('in', 'NPYarray')

        self.URI = gpi.TranslateFileURI

    def validate(self):
        if self.getVal('Write Mode'):
            self.setAttr('Write Mode', button_title="Write on Every Event")
        else:
            self.setAttr('Write Mode', button_title="Write on New Filename")

        fname = self.URI(self.getVal('File Browser'))
        self.setDetailLabel(fname)

        return 0

    def compute(self):
        import numpy as np
        import csv

        if self.getVal('Write Mode') or self.getVal('Write Now') or ('File Browser'  in self.widgetEvents()):
            fname = self.URI(self.getVal('File Browser'))
            if not fname.endswith('.csv'):
                fname += '.csv'
            if fname == '.csv':
                return 0

            # get data and check it
            data = self.getData('in')
            if data.dtype in [np.complex, np.complex64, np.complex128, np.complex256]:
                self.log.warn('Complex data is not readable by most CSV readers including the ReadCSV node.\n\tYou can split your real and imag sets into another dimension if needed.')
            if len(data.shape) > 2:
                self.log.warn('ndim > 2 not supported')
                return 1

            np.savetxt(fname,data,delimiter=",")

        return(0)
