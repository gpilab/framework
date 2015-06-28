#    Copyright (C) 2014  Dignity Health
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#    NO CLINICAL USE.  THE SOFTWARE IS NOT INTENDED FOR COMMERCIAL PURPOSES
#    AND SHOULD BE USED ONLY FOR NON-COMMERCIAL RESEARCH PURPOSES.  THE
#    SOFTWARE MAY NOT IN ANY EVENT BE USED FOR ANY CLINICAL OR DIAGNOSTIC
#    PURPOSES.  YOU ACKNOWLEDGE AND AGREE THAT THE SOFTWARE IS NOT INTENDED FOR
#    USE IN ANY HIGH RISK OR STRICT LIABILITY ACTIVITY, INCLUDING BUT NOT
#    LIMITED TO LIFE SUPPORT OR EMERGENCY MEDICAL OPERATIONS OR USES.  LICENSOR
#    MAKES NO WARRANTY AND HAS NOR LIABILITY ARISING FROM ANY USE OF THE
#    SOFTWARE IN ANY HIGH RISK OR STRICT LIABILITY ACTIVITIES.

import os
import hashlib
import numpy as np

# gpi
from .defines import GPI_SHDM_PATH
from .logger import manager
from .sysspecs import Specs

# start logger for this module
log = manager.getLogger(__name__)


# List all types that are handled. This tells the deserializing side what to do
class ProxyType(object):
    np_ndarray = 0
    np_memmap = 1
    np_ndarray_segmented = 2

class DataProxy(dict):
    '''Holds all file descriptor information for any object that is
    serializeable.  The method functions facilitate serialization and
    deserialization on either side of the Proxy-Manager.

    NUMPY:
        Numpy arrays must be segments that are smaller than 2GiB (2^31 bytes).

    NUMPY-MMAP:
        MMAP file descriptors are passed through the proxy only if there are
        enough available resources (i.e. rlimit).
    '''
    def __init__(self):
        super(DataProxy, self).__init__()

    def getSHMF(self, nodeID, name='local'):
        '''return a unique shared mem handle for this gpi instance, node and port.
        '''
        # make sure the user supplied string is a unique, consistent and valid filename
        hsh = hashlib.md5(str(name)).hexdigest()
        return os.path.join(GPI_SHDM_PATH, str(hsh)+'_'+str(nodeID))

    # select the correct proxy data for np-ndarrays and memmaps
    def NDArray(self, data, shdf=None, nodeID=None, portname=None):
        # if the user creates a memmapped numpy w/o using allocArray()
        if type(data) is np.memmap:
            self._setNDArrayMemmapFromNDArrayMemmap(data)
        # if the user is using an ndarray interface directly
        elif type(data) is np.ndarray:
            # if the user creates a memmapped numpy using allocArray()
            if shdf is not None:
                self._setNDArrayMemmapFromWrappedNDarrayMemmap(data, shdf)
            # if the user doesn't generate a memmapped array ahead of
            # setData().
            else:
                self._setNDArrayMemmapFromNDArray(data, nodeID, portname)
        return self

    # if an np-ndarray is passed then copy it to an np-memmap
    def _setNDArrayMemmapFromNDArray(self, data, nodeID, portname):
        self['proxy_type'] = ProxyType.np_memmap
        self['shape'] = tuple(data.shape)
        self['dtype'] = data.dtype
        self['shdf'] = self.getSHMF(nodeID, portname)
        fp = np.memmap(self['shdf'], dtype=data.dtype, mode='w+', shape=self['shape'])
        fp[:] = data[:] # full copy

    # if the np-memmap is already generated and passed directly then just copy
    # the relevant information
    def _setNDArrayMemmapFromNDArrayMemmap(self, data):
        self['proxy_type'] = ProxyType.np_memmap
        self['shape'] = tuple(data.shape)
        self['shdf'] = data.filename
        self['dtype'] = data.dtype

    # if a numpy array is wrapping a memmap'd array then pass the name
    def _setNDArrayMemmapFromWrappedNDarrayMemmap(self, data, shdf):
        self['proxy_type'] = ProxyType.np_memmap
        self['shape'] = tuple(data.shape)
        self['dtype'] = data.dtype
        self['shdf'] = shdf

    # create and return an np-ndarray wrapped memmap
    # return handles to both the wrapped and memmap'd data
    def _genNDArrayMemmap(self, shape=(1,), dtype=np.float32, nodeID=0, portname='local'):
        fn = self.getSHMF(nodeID, portname)
        shd = np.memmap(fn, dtype=dtype, mode='w+', shape=tuple(shape))
        buf = np.frombuffer(shd.data, dtype=shd.dtype)
        buf.shape = shd.shape
        return buf, shd

    # return a reference to whatever data was sent
    def getData(self):
        if self['proxy_type'] == ProxyType.np_memmap:
            shd = np.memmap(self['shdf'], dtype=self['dtype'], mode='r', shape=self['shape'])

            # make this look like a normal numpy array, since 
            # functions like np.copy() don't work the same.
            buf = np.frombuffer(shd.data, dtype=shd.dtype)
            buf.shape = shd.shape
            return buf



