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

import gpi
import os
import h5py

class ExternalNode(gpi.NodeAPI):
    """Reads HDF5 files using the h5py project libs.

    NOTE: This is a simple reader for getting 'dataset' objects from an HDF5 file.
    Since the files can be built in many different ways, this should be considered
    a good starting point for writing code to read your specific format.  More
    general use cases will be added in future releases.
    """

    def initUI(self):

        # Widgets
        self.addWidget('TextBox', 'I/O Info:')
        self.addWidget(
            'OpenFileBrowser', 'File Browser', button_title='Browse',
            caption='Open File', filter='hdf5 (*.hdf5);;hdf5 (*.h5)')
        self.addWidget('ComboBox', 'dataset')
        self.addWidget('PushButton', 'reload datasets')
        self.addWidget('PushButton', 'read', toggle=True, val=False)
        # self.addWidget('StringBox', 'set-name', val='gpidata')

        # IO Ports
        self.addOutPort('out', 'NPYarray')

        # store for later use
        self.URI = gpi.TranslateFileURI
        self.fname = None

    def validate(self):
        self.fname = self.URI(self.getVal('File Browser'))

        if ('File Browser' in self.widgetEvents()
             or 'reload datasets' in self.widgetEvents()):
            self.setAttr('read', val=False)

            # check that the path actually exists
            if not os.path.exists(self.fname):
                self.log.node("Path does not exist: " + self.fname)
                return 1

            f = h5py.File(self.fname, "r")

            # show available keys
            self.dataset_names = []
            def append_if_dataset(name, obj):
                if isinstance(obj, h5py.Dataset):
                    self.dataset_names.append(name)
            f.visititems(append_if_dataset)
            self.setAttr('dataset', items=self.dataset_names)

            f.close()

        if self.getVal('dataset') is not None:
            self.setDetailLabel(self.fname + "::" + self.getVal('dataset'))
        else:
            self.setDetailLabel(self.fname)

        return 0

    def compute(self):
        import time
        import numpy as np

        # check that the path actually exists
        if self.fname is None or not os.path.exists(self.fname):
            self.log.node("Path does not exist: " + str(self.fname))
            return 0

        # show some file stats
        fstats = os.stat(self.fname)
        # creation
        ctime = time.strftime('%d/%m/20%y', time.localtime(fstats.st_ctime))
        # mod time
        mtime = time.strftime('%d/%m/20%y', time.localtime(fstats.st_mtime))
        # access time
        atime = time.strftime('%d/%m/20%y', time.localtime(fstats.st_atime))
        # filesize
        fsize = fstats.st_size
        # user id
        uid = fstats.st_uid
        # group id
        gid = fstats.st_gid

        info = "created: "+str(ctime)+"\n" \
               "accessed: "+str(atime)+"\n" \
               "modified: "+str(mtime)+"\n" \
               "UID: "+str(uid)+"\n" \
               "GID: "+str(gid)+"\n" \
               "file size (bytes): "+str(fsize)+"\n" \

        self.setAttr('I/O Info:',val=info)

        # get file pointer
        f = h5py.File(self.fname, "r")

        setname = self.getVal('dataset')

        if self.getVal('read'):
            # assuming the dataset is a numpy array
            data1 = f[setname][()]
            try:
                data = data1['real'] + 1j*data1['imag']  # handle complex structured arrays (e.g. GE)
            except (ValueError, KeyError):
                data = data1
            self.setData('out', data)
            f.close()

        return 0
