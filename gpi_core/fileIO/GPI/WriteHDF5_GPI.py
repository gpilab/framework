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
# Date: 2014mar21

import re
import time
import datetime

import gpi

# get the date and time
def suffix():
    today = datetime.date.today().strftime("%Y.%m.%d")
    ctime = time.strftime("%H.%M.%S")
    suffix = today + "_" + ctime
    return suffix

def new_name(name):
    return name + "_" + suffix()

def unique_name(name, lst):
    # find a suitable name that doesn't already exist
    bname = new_name(name)
    while bname in lst:
        bname = new_name(name)
        time.sleep(1) # wait a second for a unique name
    return bname


class ExternalNode(gpi.NodeAPI):
    """Uses the HDF5 h5py project interface for writing arrays.

    INPUT - numpy array to write

    WIDGETS:
    File Browser - button to launch file browser, and typein widget, to give pathname for output file
    Write Mode - write at any event, or write only with new filename
    Write Now - write right now

    NOTE: This is a simple writer for writing 'dataset' objects from an HDF5 file.
    Since the files can be built in many different ways, this should be considered
    a good starting point for writing code to write your specific format.  More
    general use cases will be added in future releases.
    """

    def initUI(self):

       # Widgets
        self.addWidget(
            'SaveFileBrowser', 'File Browser', button_title='Browse',
            caption='Save File (*.hdf5)', filter='hdf5 (*.hdf5)')
        self.addWidget('StringBox', 'set-name', val='gpidata')
        self.addWidget('PushButton', 'compress (GZIP)', toggle=True)
        self.addWidget('PushButton', 'Write Mode', button_title='Write on New Filename', toggle=True)
        self.addWidget('PushButton', 'Write Now', button_title='Write Right Now', toggle=False)

        # IO Ports
        self.addInPort('in', 'NPYarray')

        # store for later use
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

        import h5py

        if self.getVal('Write Mode') or self.getVal('Write Now') or ('File Browser' in self.widgetEvents()):

            fname = self.URI(self.getVal('File Browser'))
            if not fname.endswith('.hdf5'):
                fname += '.hdf5'

            if fname == '.hdf5':
                return 0

            label = self.getVal('set-name')
            if label == '':
                self.log.warn('invalid set-name')
                return 0

            if self.getVal('compress (GZIP)'):
                kwargs = {}
                kwargs['compression'] = 'gzip'
                kwargs['compression_opts'] = 9
                data = self.getData('in')
                f = h5py.File(fname, "a")

                if label in list(f.keys()):
                    label = unique_name(label, list(f.keys()))
                    print("dataset label already exists in file, using \'"+label+"\'")

                dset = f.create_dataset(label, data=data, **kwargs)
                f.close()

            else:
                data = self.getData('in')
                f = h5py.File(fname, "a")

                if label in list(f.keys()):
                    label = unique_name(label, list(f.keys()))
                    print("dataset label already exists in file, using \'"+label+"\'")

                dset = f.create_dataset(label, data=data)
                f.close()

        return(0)
