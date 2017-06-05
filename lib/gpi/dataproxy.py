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
#    MAKES NO WARRANTY AND HAS NO LIABILITY ARISING FROM ANY USE OF THE
#    SOFTWARE IN ANY HIGH RISK OR STRICT LIABILITY ACTIVITIES.

'''This module is an extension for handling specific data types such as
Numpy-arrays. '''

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
    null = -1
    np_ndarray = 0
    np_memmap = 1
    segmented = 2

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
        #self['proxy_type'] = ProxyType.null

    def getSHMF(self, nodeID, name='local'):
        '''return a unique shared mem handle for this gpi instance, node and port.
        '''
        # make sure the user supplied string is a unique, consistent and valid filename
        hsh = hashlib.md5(str(name).encode('utf8')).hexdigest()

        # add a little salt with the random int generator - this will just grow
        # the ports don't keep track of these file names for cleanup
        #hsh = hashlib.md5(str(name)+str(np.random.randint(0,999))).hexdigest()

        return os.path.join(GPI_SHDM_PATH, str(hsh)+'_'+str(nodeID))

    def isSegmented(self):
        return self['proxy_type'] == ProxyType.segmented

    # select the correct proxy data for np-ndarrays and memmaps
    def NDArray(self, data, shdf=None, nodeID=None, portname=None):

        # if the user creates a memmapped numpy w/o using allocArray()
        if type(data) is np.memmap and data.filename is not None:
            # it's a *real* np.memmap
            self._setNDArrayMemmapFromNDArrayMemmap(data)

        # if the user is using an ndarray interface directly
        else:

            # if the user creates a memmapped numpy using allocArray()
            if shdf is not None:
                self._setNDArrayMemmapFromWrappedNDarrayMemmap(data, shdf)

            # normal numpy arrays
            else:

                # if the array is small then just send it directly instead of
                # using up a file handle
                if data.nbytes < 2**25: # 32MiB 
                    self._setNDArrayFromNDArray(data)

                # we're too close to the open file limit so start using segmented proxy
                elif Specs.openFileLimitThresh():
                    return self._genNDArraySegmentsFromNDArray(data)
            
                # in the normal case we'll use memmap to pass data.
                else:
                    self._setNDArrayMemmapFromNDArray(data, nodeID, portname)
        return self

    # no tricks just pass the np ndarray directly
    def _setNDArrayFromNDArray(self, data):
        self['proxy_type'] = ProxyType.np_ndarray
        self['data'] = data

    # np ndarray segment
    def _setNDArraySegmentFromNDArray(self, seg, oshape, no, total, did):
        self['proxy_type'] = ProxyType.segmented
        self['seg_type'] = ProxyType.np_ndarray
        self['id'] = did
        self['seg'] = seg 
        self['oshape'] = oshape
        self['no.'] = no
        self['total'] = total
        return self

    # if the process is out of file handles or the byte size of the array is
    # below the threshold, then use the segmented approach
    # returns a list of DataProxy objects.
    def _genNDArraySegmentsFromNDArray(self, data):

        log.info("------ SPLITTING LARGE NPY ARRAY >1GiB")
        div = int(data.nbytes/(2**30)) + 1 # 1GiB 

        oshape = list(data.shape)
        fshape = [np.prod(data.shape)]
        if not data.flags['C_CONTIGUOUS']:
            log.warn('Output array is not contiguous, forcing contiguity.')
            data = np.ascontiguousarray(data)
        data.shape = fshape  # flatten
        segs = np.array_split(data, div)
        did = id(data)

        buf = []
        cnt = 0
        tot = len(segs)
        for seg in segs:
            buf.append(DataProxy()._setNDArraySegmentFromNDArray(seg, oshape, cnt, tot, did))
            cnt += 1
        return buf

    # assemble all the numpy chunks into one array and return the array
    def _assembleNDArraySegments(self, segments):
        log.info("_assembleNDArraySegments(): ------ APPENDING LARGE NPY ARRAY SEGMENTS")

        if len(segments) != segments[0]['total']:
            log.error('Failed to proxy all numpy array segments. Aborting.')
            return

        # order the segments based on their 'no.'
        segments = sorted(segments, key=lambda d: d['no.'])

        # gather array segments and reshape NPY array
        segs = [s['seg'] for s in segments]
        lrgNPY = np.concatenate(segs)
        lrgNPY.shape = segments[0]['oshape']
        return lrgNPY

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

        # too close to the open file limit so just give the user a normal array
        if Specs.openFileLimitThresh():
            log.warn("Maxed out file handles, pre-alloc will be ndarray...")
            return np.ndarray(shape, dtype=dtype), None

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
        elif self['proxy_type'] == ProxyType.np_ndarray:
            return self['data']
        elif self['proxy_type'] == ProxyType.segmented:
            log.error('Segmented Type: this IF requires a list of segment proxy objects')
            return

    # all segments must pass through the proxy separately
    def getDataFromSegments(self, segments):
        if segments[0]['proxy_type'] == ProxyType.segmented:
            if segments[0]['seg_type'] == ProxyType.np_ndarray:
                return self._assembleNDArraySegments(segments)
