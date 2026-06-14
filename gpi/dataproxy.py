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
import atexit
import uuid
import numpy as np
import copy
from collections import OrderedDict
from typing import Optional, Dict, Set

# gpi
from .defines import GPI_SHDM_PATH
from .logger import manager
from .sysspecs import Specs
from .mri_data import MRIData

# start logger for this module
log = manager.getLogger(__name__)


# List all types that are handled. This tells the deserializing side what to do
class ProxyType(object):
    null = -1
    np_ndarray = 0
    np_memmap = 1
    segmented = 2
    mri_data = 3


class FileDescriptorManager(object):
    """Manages file descriptors for memmap'd arrays with LRU eviction.

    Prevents "too many open files" errors by:
    - Tracking open memmap file descriptors
    - Evicting LRU entries when approaching system limits or the count cap
    - Providing dynamic threshold calculation based on available FDs
    """

    MAX_OPEN_MEMMAPS = 32  # hard cap on simultaneously open memmap FDs

    def __init__(self, min_reserve_pct=0.15):
        self.open_memmaps: Dict[str, np.memmap] = {}
        self.access_order = OrderedDict()
        self.created_files: Set[str] = set()  # every file we ever created this session
        self.min_reserve_pct = min_reserve_pct
        self.eviction_count = 0
        
    def get_available_fds(self) -> int:
        """Calculate available file descriptors."""
        return Specs.availableFileDescriptors()
    
    def get_safe_threshold_bytes(self) -> int:
        """Calculate dynamic size threshold based on available FDs.
        
        Returns a size threshold in bytes. Arrays smaller than this should
        be sent directly instead of using memmap to prevent FD exhaustion.
        
        Formula: Adapts based on how many FDs are available:
        - If plenty of FDs available: larger threshold (16 MiB)
        - If running low on FDs: smaller threshold (4 MiB)
        """
        available = self.get_available_fds()
        reserve = Specs.safeFileDescriptorReserve()
        
        # Hardcoded minimum to prevent too many small memaps
        min_threshold = 2**22  # 4 MiB
        # Default threshold with plenty of FDs
        default_threshold = 2**24  # 16 MiB
        
        if available < (reserve * 2):
            # Running low - use small threshold
            return min_threshold
        else:
            # Plenty available - use comfortable threshold
            return default_threshold
    
    def register_memmap(self, filepath: str, memmap_obj: np.memmap) -> None:
        self.open_memmaps[filepath] = memmap_obj
        self.access_order[filepath] = True
        self.created_files.add(filepath)
        self._evict_if_needed()
    
    def access_memmap(self, filepath: str) -> None:
        if filepath in self.access_order:
            self.access_order.move_to_end(filepath)
    
    def _evict_if_needed(self) -> None:
        """Evict LRU memmaps if over the count cap or approaching the FD limit."""
        # Count-based cap: keep at most MAX_OPEN_MEMMAPS open regardless of FD pressure.
        while len(self.open_memmaps) > self.MAX_OPEN_MEMMAPS:
            self._evict_lru()
            self.eviction_count += 1
        # FD-pressure-based eviction: evict 10% when the system is running low.
        if not Specs.canAllocateFileDescriptor(count=1):
            num_to_evict = max(1, len(self.open_memmaps) // 10)
            for _ in range(num_to_evict):
                if self.open_memmaps:
                    self._evict_lru()
                    self.eviction_count += 1
    
    def _evict_lru(self) -> None:
        """Evict the least-recently-used memmap."""
        if not self.access_order:
            return

        lru_filepath = next(iter(self.access_order))

        try:
            # Removing from the dict releases the last reference to the memmap
            # object so Python can finalize it (closes the underlying FD).
            del self.open_memmaps[lru_filepath]
            del self.access_order[lru_filepath]
            log.debug(f"Evicted LRU memmap: {lru_filepath} (total evictions: {self.eviction_count})")
        except Exception as e:
            log.warn(f"Error evicting LRU memmap {lru_filepath}: {e}")
    
    def get_stats(self) -> Dict[str, int]:
        """Return statistics about FD usage."""
        return {
            'open_memmaps': len(self.open_memmaps),
            'available_fds': self.get_available_fds(),
            'safe_threshold_bytes': self.get_safe_threshold_bytes(),
            'total_evictions': self.eviction_count
        }
    
    def cleanup(self) -> None:
        """Close all tracked memmaps and delete backing files created this session."""
        for filepath in list(self.open_memmaps.keys()):
            try:
                del self.open_memmaps[filepath]
                del self.access_order[filepath]
            except (KeyError, OSError):
                pass
        for filepath in list(self.created_files):
            try:
                if os.path.exists(filepath):
                    os.unlink(filepath)
            except OSError:
                pass
        self.created_files.clear()


# Global instance for use throughout the dataproxy module
_fd_manager = FileDescriptorManager()
atexit.register(_fd_manager.cleanup)

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
        '''Return a unique-per-write path for a memmap backing file.

        Using a UUID prevents the deterministic-name collision that caused data
        corruption: if the same node was triggered twice (e.g., on load and on a
        parameter change) the second write would silently overwrite the first
        file while the first proxy was still in transit, so the main process
        would read the wrong data.  With unique names every write is isolated.
        Backing files are deleted at session end via the atexit cleanup.
        '''
        return os.path.join(GPI_SHDM_PATH, f'{uuid.uuid4().hex}_{nodeID}')

    def isSegmented(self):
        return self['proxy_type'] == ProxyType.segmented

    # select the correct proxy data for np-ndarrays and memmaps
    def NDArray(self, data, shdf=None, nodeID=None, portname=None):

        # if the user creates a memmapped numpy w/o using allocArray()
        if type(data) is np.memmap and data.filename is not None:
            # it's a *real* np.memmap
            self._setNDArrayMemmapFromNDArrayMemmap(data)
            if data.filename:
                _fd_manager.access_memmap(data.filename)

        # if the user is using an ndarray interface directly
        else:

            # if the user creates a memmapped numpy using allocArray()
            if shdf is not None:
                self._setNDArrayMemmapFromWrappedNDarrayMemmap(data, shdf)
                if shdf:
                    _fd_manager.access_memmap(shdf)

            # normal numpy arrays
            else:
                # Use dynamic threshold based on available file descriptors
                threshold = _fd_manager.get_safe_threshold_bytes()

                # if the array is small then just send it directly instead of
                # using up a file handle
                if data.nbytes < threshold:
                    self._setNDArrayFromNDArray(data)

                # we're too close to the open file limit so start using segmented proxy
                elif not Specs.canAllocateFileDescriptor():
                    return self._genNDArraySegmentsFromNDArray(data)
            
                # in the normal case we'll use memmap to pass data.
                else:
                    try:
                        self._setNDArrayMemmapFromNDArray(data, nodeID, portname)
                    except OSError:
                        # Rare: temp dir full, permission error, etc.
                        log.warn("memmap creation failed, falling back to direct array")
                        self._setNDArrayFromNDArray(data)
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
        self['seg'] = seg.tobytes()
        self['seg_shape'] = seg.shape[0]  # Store segment's length (since it's flattened)
        self['dtype'] = seg.dtype         # Store dtype for reconstruction
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
        raw_segs = [s['seg'] for s in segments]
        
        # Efficiently join the raw byte objects 
        full_byte_buffer = b''.join(raw_segs)
        
        # Extract necessary information for reconstruction
        dtype = segments[0]['dtype']
        oshape = segments[0]['oshape']
        
        # Reconstruct the NumPy array directly from the byte buffer
        lrgNPY = np.frombuffer(full_byte_buffer, dtype=dtype)
        
        # Reshape to the original shape
        lrgNPY.shape = oshape
        return lrgNPY

    # if an np-ndarray is passed then copy it to an np-memmap
    def _setNDArrayMemmapFromNDArray(self, data, nodeID, portname):
        self['proxy_type'] = ProxyType.np_memmap
        self['shape'] = tuple(data.shape)
        self['dtype'] = data.dtype
        self['shdf'] = self.getSHMF(nodeID, portname)
        fp = np.memmap(self['shdf'], dtype=data.dtype, mode='w+', shape=self['shape'])
        fp[:] = data[:]  # full copy
        fp.flush()        # ensure pages are visible to the main process before read
        _fd_manager.register_memmap(self['shdf'], fp)

    # if the np-memmap is already generated and passed directly then just copy
    # the relevant information
    def _setNDArrayMemmapFromNDArrayMemmap(self, data):
        self['proxy_type'] = ProxyType.np_memmap
        self['shape'] = tuple(data.shape)
        self['shdf'] = data.filename
        self['dtype'] = data.dtype
        # .npy files loaded with mmap_mode='r' have a non-zero offset (the header).
        # Storing it here ensures getData() maps from the correct byte position.
        self['offset'] = int(getattr(data, 'offset', 0))

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
        if not Specs.canAllocateFileDescriptor():
            log.warn("Maxed out file handles, pre-alloc will be ndarray...")
            return np.ndarray(shape, dtype=dtype), None

        fn = self.getSHMF(nodeID, portname)
        shd = np.memmap(fn, dtype=dtype, mode='w+', shape=tuple(shape))
        _fd_manager.register_memmap(fn, shd)
        return shd.view(np.ndarray), shd

    # return a reference to whatever data was sent
    def getData(self):
        if self['proxy_type'] == ProxyType.np_memmap:
            # mode='c' (copy-on-write): zero-copy open, writable, writes stay private.
            # view(np.ndarray) strips the memmap subclass so downstream code sees a
            # plain ndarray; the memmap object is kept alive via ndarray.base.
            # offset is non-zero for .npy files (their header precedes the data).
            offset = self.get('offset', 0)
            shd = np.memmap(self['shdf'], dtype=self['dtype'], mode='c',
                            shape=self['shape'], offset=offset)
            _fd_manager.access_memmap(self['shdf'])
            return shd.view(np.ndarray)
        elif self['proxy_type'] == ProxyType.np_ndarray:
            return self['data']
        elif self['proxy_type'] == ProxyType.mri_data:
            return MRIData.deserialize(self)
        elif self['proxy_type'] == ProxyType.segmented:
            log.error('Segmented Type: this IF requires a list of segment proxy objects')
            return

    # all segments must pass through the proxy separately
    def getDataFromSegments(self, segments):
        if segments[0]['proxy_type'] == ProxyType.segmented:
            if segments[0]['seg_type'] == ProxyType.np_ndarray:
                return self._assembleNDArraySegments(segments)
            
        
    def setMRIData(self, mri_data: MRIData, nodeID: Optional[int], portname: Optional[str]):
        """Set MRIData object in the proxy."""
        self['proxy_type'] = ProxyType.mri_data
        self.update(mri_data.serialize(nodeID, portname))
        
        return self