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


#Author: Nick Zwart
#Date:  2012sep02
#Payal Bhavsar added read for ASCII type
#Date: Nov2013

import os
import sys
import time
import numpy as np
import gpi


def read(fname, datatype, numelem, skipbytes):
    ''' Read and cast data arrays from raw file format.
    datatype: 0:float32, 1:float64, 2:int32, 3:uint8, 4:int16,
              5:complex64, 6:complex128
    '''
    if not isinstance(fname, str):
        raise TypeError("read(): fname must be a string, got " + type(fname).__name__)

    _DTYPES = {
        0: np.float32,
        1: np.float64,
        2: np.int32,
        3: np.uint8,
        4: np.dtype('i2'),
        5: np.complex64,
        6: np.complex128,
    }
    if datatype not in _DTYPES:
        raise ValueError("read(): no valid datatype chosen: " + str(datatype))

    dt = np.dtype(_DTYPES[datatype])
    try:
        with open(fname, 'rb') as fil:
            fil.seek(skipbytes)
            raw = fil.read(numelem * dt.itemsize)
    except OSError as e:
        raise OSError("read(): cannot open file '{}': {}".format(fname, e)) from e

    return np.frombuffer(raw, dtype=dt).copy()


class ExternalNode(gpi.NodeAPI):
    """Reads raw data into several c-types: float, double, int, and char.
    OUTPUT: Numpy array of data

    WIDGETS:
    I/O Info: information about file
    File Browser: file browswer
    Skip Bytes: number of bytes past which to start reading data (e.g. size of header)
    <type>: type of data in file
    ndim:  Number of dimensions to fill (of output array)
    Dimension N: number of elements in the Nth dimension
    Compute: compute
    """

    def initUI(self):

        # Widgets
        self.addWidget('TextBox', 'I/O Info:')
        self.addWidget(
            'OpenFileBrowser', 'File Browser', button_title='Browse',
            caption='Open File', filter='raw (*.raw);;all (*)')
        self.addWidget('SpinBox', 'Skip Bytes:', val=0, min=0)
        self.addWidget('ExclusiveRadioButtons', '<type>', buttons=[
                       'float', 'double', 'int', 'char','short int', 'complex<float>',
                       'complex<double>'], val=0)

        self.ndim = 8
        self.dim_base_name = 'Dimension: '
        self.addWidget('Slider', 'ndim:', max=self.ndim, val=1, min=1)
        for i in range(self.ndim):
            self.addWidget('SpinBox', self.dim_base_name+str(i), min=1, val=1, max=gpi.GPI_INT_MAX)

        self.addWidget('PushButton', 'Compute', toggle=True)

        # IO Ports
        self.addOutPort('out', 'NPYarray')

        # store for later use
        self.URI = gpi.TranslateFileURI

    def validate(self):
        fname = self.URI(self.getVal('File Browser'))
        self.setDetailLabel(fname)

    def compute(self):

        import os
        import sys
        import time
        import numpy as np

        # visibility
        cdim = self.getVal('ndim:')
        dims = []
        nelem = 1
        for i in range(self.ndim):
            if i < cdim:
                self.setAttr(self.dim_base_name+str(i), visible=True)
                dims.append(self.getVal(self.dim_base_name+str(i)))
                nelem = nelem*self.getVal(self.dim_base_name+str(i))
            else:
                self.setAttr(self.dim_base_name+str(i), visible=False)

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
               "file size (bytes): "+str(fsize)+"\n"
        self.setAttr('I/O Info:', val=info)

        # compute block
        compute = self.getVal('Compute')
        dtype = self.getVal('<type>')
        skipbytes = self.getVal('Skip Bytes:')

        if not compute:
            return 0

        out = read(fname, dtype, nelem, skipbytes)

        try:
            out = out.reshape(dims)
        except ValueError:
            self.log.warn("ReadRaw: cannot reshape {} elements into {}".format(
                out.size, dims))
            return 0

        self.setData('out', out)

        return(0)
