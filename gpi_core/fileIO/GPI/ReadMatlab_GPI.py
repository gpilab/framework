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


# Author: Ashley Anderson
# adapted from Nick Zwart's HDF4 Reader
# Date: 2014aug20

import gpi
import os

class ExternalNode(gpi.NodeAPI):
    """Reads Matlab (.mat) files using the h5py (for files >= v7.3) or scipy libs.
    """

    def initUI(self):

        # Widgets
        self.addWidget('TextBox', 'I/O Info:')
        self.addWidget(
            'OpenFileBrowser', 'File Browser', button_title='Browse',
            caption='Open File', filter='matlab files (*.mat)')
        self.addWidget('ComboBox', 'dataset')

        # IO Ports
        self.addOutPort('out', 'NPYarray')

        # store for later use
        self.URI = gpi.TranslateFileURI
        self.oldfmt = True

    def validate(self):
        fname = self.URI(self.getVal('File Browser'))

        # check that the path actually exists
        if not os.path.exists(fname):
            self.log.node("Path does not exist: "+str(fname))
            return 0

        self.setDetailLabel(fname)

        all_names = []
        import scipy.io
        try:
            all_names = scipy.io.whosmat(fname)
            all_names = [name[0] for name in all_names]
            self.oldfmt = True
        except (ValueError,NotImplementedError) as e:
            self.log.warn("Not an old (<v7.3) .mat file - trying HDF5")
            self.oldfmt = False

        if not self.oldfmt:
            import h5py
            f = h5py.File(fname, "r")

            # show available keys
            def append_if_dataset(name,obj):
                if isinstance(obj,h5py.Dataset):
                    all_names.append(name)
            f.visititems(append_if_dataset)

            f.close()

        if 'File Browser' in self.widgetEvents():
            # we only care to change the combo box if the filename has changed
            self.setAttr('dataset', items=all_names)

        self.log.info("self.oldfmt is {}".format(self.oldfmt))

        return 0

    def compute(self):
        import time
        import numpy as np

        # start file browser
        fname = self.URI(self.getVal('File Browser'))

        # check that the path actually exists
        if not os.path.exists(fname):
            self.log.node("Path does not exist: "+str(fname))
            return 0


        # show some file stats
        fstats = os.stat(fname)
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

        setname = self.getVal('dataset')

        # this all assumes the data can be represented as a numpy array!
        if self.oldfmt:
            info += "Pre-v7.3 Matlab file\n"
            import scipy.io
            mdict = scipy.io.loadmat(fname, variable_names=(setname,))
            data = mdict[setname]
        else:
            info += "v7.3+ Matlab file (HDF5)\n"
            import h5py
            f = h5py.File(fname, "r")
            data = f[setname].value
            f.close()

        self.setAttr('I/O Info:',val=info)
        self.setData('out', data)
        return 0
