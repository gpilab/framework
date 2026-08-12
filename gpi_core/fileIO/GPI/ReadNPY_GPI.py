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
# Date: 2012 Nov 02

import os
import time
import gpi
import numpy as np

class ExternalNode(gpi.NodeAPI):
    """Read arrays that were written as Numpy files
    
    OUTPUT: Numpy array read from file

    WIDGETS:
    I/O Info - Gives info on data file and data type
    File Browser - button to launch file browser, and typein widget if the pathway is known.
    Squeeze - option for squeezing data, which removes all dimensions of length 1 (all data preserved)
    """

    def execType(self):
        # default executable type
        return gpi.GPI_THREAD
        # return gpi.GPI_PROCESS # this is the safest
        # return gpi.GPI_APPLOOP

    def initUI(self):

       # Widgets
        self.addWidget('TextBox', 'I/O Info:')
        self.addWidget('OpenFileBrowser', 'File Browser',
                button_title='Browse', caption='Open File', filter='numpy (*.npy)')
        self.addWidget('PushButton', 'Squeeze', toggle=True)

        # IO Ports
        self.addOutPort(title='out', type='NPYarray')

        self.URI = gpi.TranslateFileURI
        self.fname = None

    def validate(self):
        self.fname = self.URI(self.getVal('File Browser'))
        self.setDetailLabel(self.fname)

    def compute(self):

        import os
        import time
        import numpy as np

        fname = self.fname

        # check that the path actually exists
        if not fname or not os.path.exists(fname):
            self.log.warn("Path does not exist: "+str(fname))
            self.setAttr('I/O Info:', val="File not found:\n"+str(fname))
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

        # read the data
        # mmap_mode='r' avoids loading the whole file into RAM while reading.
        # Copy out of the mmap and drop it so the OS file mapping is released
        # here in compute() instead of staying open for the node's lifetime,
        # which would otherwise keep the file locked against modification.
        try:
            mm = np.load(fname, mmap_mode='r')
            out = np.array(mm)
            del mm
        except Exception as error:
            self.log.error('ReadNPY: failed to read {}: {}'.format(fname, error))
            self.setAttr('I/O Info:', val="Failed to read file:\n{}\n\n{}".format(fname, error))
            return 0

        if self.getVal('Squeeze'):
            out = out.squeeze()

        d1 = list(out.shape)
        info = "created: "+str(ctime)+"\n" \
               "accessed: "+str(atime)+"\n" \
               "modified: "+str(mtime)+"\n" \
               "UID: "+str(uid)+"\n" \
               "GID: "+str(gid)+"\n" \
               "file size (bytes): "+str(fsize)+"\n" \
               "dimensions: "+str(d1)+"\n" \
               "type: "+str(out.dtype)+"\n"
        self.setAttr('I/O Info:', val=info)

        self.setData('out', out)

        return(0)
