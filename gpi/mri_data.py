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
#    Author: Guru Krishnamoorthy
#    Date: January 14, 2025

import numpy as np
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
import os
import hashlib
from .defines import GPI_SHDM_PATH

@dataclass
class MRIData:
    """
    A class to represent MRI data with support for memory-mapped files and shared memory.
    Attributes
    ----------
    memmap_threshold : int
        Threshold in MB for using memory-mapped files.
    idata : np.ndarray
        Image data array.
    coords : Optional[np.ndarray]
        Coordinates array.
    coords_cg : Optional[np.ndarray]
        Constant gradient coordinates array.
    sdc : Optional[np.ndarray]
        Sampling density compensation.
    sdc_cg : Optional[np.ndarray]
        Constant gradient sampling density compensation.
    tmap : Optional[np.ndarray]
        Time-map array.
    data_params : Dict[str, Any]
        Dictionary of data parameters.
    nodeID : Optional[int]
        Node ID for shared memory.
    portname : Optional[str]
        Port name for shared memory.
    Methods
    -------
    __init__(idata_shape, dtype=np.complex64, nodeID=None, portname=None):
        Initializes the MRIData object with the given image data shape and data type.
    _initialize_data(shape: tuple, dtype, nodeID: Optional[int], portname: Optional[str]) -> np.ndarray:
        Initializes the data array, using memory-mapped files if necessary.
    getSHMF(nodeID: int, name: str = 'local') -> str:
        Generates a filename for shared memory file.
    update_params(contrast: str, echo_times: np.ndarray, axes_labels: list, space: str, tau: float, extra_params: Optional[dict] = None):
        Updates the data parameters.
    serialize(portname: Optional[str] = None, nodeID: Optional[int] = None) -> dict:
        Serializes the object to a dictionary.
    deserialize(data: dict) -> 'MRIData':
        Deserializes the object from a dictionary.
    clone(other: 'MRIData') -> 'MRIData':
        Clones the object.
    """
    
    memmap_threshold: int = 32  # Threshold in MB for using memory-mapped files
    idata: np.ndarray = field(init=False)  # Image data array
    coords: Optional[np.ndarray] = None  # Coordinates array
    coords_cg: Optional[np.ndarray] = None  # Constant gradient coordinates array
    sdc: Optional[np.ndarray] = None  # sampling density compensation
    sdc_cg: Optional[np.ndarray] = None  # Constant gradient sampling density compensation
    tmap: Optional[np.ndarray] = None  # Time-map array
    data_params: Dict[str, Any] = field(default_factory=lambda: {
        "contrast": "SE",
        "space": "kspace",
        "tau": 10.0,
        "axes_labels": [],
        "echo_times": [],
        "extra_params": {}
    })  # Dictionary of data parameters
    nodeID: Optional[int] = None  # Node ID for shared memory
    portname: Optional[str] = None  # Port name for shared memory

    def __init__(self, idata_shape, dtype=np.complex64, nodeID=None, portname=None):
        self.idata = self._initialize_data(idata_shape, dtype, nodeID, portname)
        self.coords = None
        self.coords_cg = None
        self.sdc = None
        self.sdc_cg = None
        self.tmap = None
        self.data_params = {}

    def _initialize_data(self, shape: tuple, dtype, nodeID: Optional[int], portname: Optional[str]) -> np.ndarray:
        # Initialize the data array, using memory-mapped files if necessary
        size_in_bytes = np.prod(shape) * np.dtype(dtype).itemsize
        if size_in_bytes > self.memmap_threshold * 1024 * 1024 and nodeID is not None and portname is not None:
            filename = self.getSHMF(nodeID, portname)
            return np.memmap(filename, dtype=dtype, mode='w+', shape=shape)
        else:
            return np.zeros(shape, dtype=dtype)

    def getSHMF(self, nodeID: int, name: str = 'local') -> str:
        # Generate a filename for shared memory file
        hsh = hashlib.md5(str(name).encode('utf8')).hexdigest()
        return os.path.join(GPI_SHDM_PATH, f"{hsh}_{nodeID}")

    def update_params(self, contrast: str, echo_times: np.ndarray, axes_labels: list,
                      space: str, tau: float, extra_params: Optional[dict] = None):
        # Update the data parameters
        self.data_params.update({
            "contrast": contrast,
            "echo_times": echo_times,
            "axes_labels": axes_labels,
            "space": space,
            "tau": tau,
            "extra_params": extra_params or {}
        })

    def serialize(self, portname: Optional[str] = None, nodeID: Optional[int] = None) -> dict:
        # Serialize the object to a dictionary
        if isinstance(self.idata, np.ndarray) and self.idata.nbytes > self.memmap_threshold * 1024 * 1024:
            
            if nodeID is None or portname is None:
                nodeID = 0
                portname = 'default'
                
            filename = self.getSHMF(nodeID, portname)
            memmap_idata = np.memmap(filename, dtype=self.idata.dtype, mode='w+', shape=self.idata.shape)
            memmap_idata[:] = self.idata[:]
            self.idata = memmap_idata

        return {
            'idata_shape': self.idata.shape,
            'idata_dtype': self.idata.dtype.str,
            'idata_filename': self.idata.filename if isinstance(self.idata, np.memmap) else None,
            'idata': None if isinstance(self.idata, np.memmap) else self.idata,
            'coords': self.coords,
            'coords_cg': self.coords_cg,
            'sdc': self.sdc,
            'sdc_cg': self.sdc_cg,
            'tmap': self.tmap,
            'data_params': self.data_params
        }

    @classmethod
    def deserialize(cls, data: dict) -> 'MRIData':
        # Deserialize the object from a dictionary
        idata_shape = data['idata_shape']
        idata_dtype = np.dtype(data['idata_dtype'])
        idata_filename = data['idata_filename']
        if idata_filename is not None:
            idata = np.memmap(idata_filename, dtype=idata_dtype, mode='r', shape=idata_shape)
        else:
            idata = data['idata']
        instance = cls(idata_shape=idata_shape, dtype=idata_dtype)
        instance.idata = idata
        instance.coords = data['coords']
        instance.coords_cg = data['coords_cg']
        instance.sdc = data['sdc']
        instance.sdc_cg = data['sdc_cg']
        instance.tmap = data['tmap']
        instance.data_params = data['data_params']
        return instance

    @classmethod
    def clone(cls, other: 'MRIData') -> 'MRIData':
        # Clone the object
        new_instance = cls(idata_shape=other.idata.shape, dtype=other.idata.dtype)
        new_instance.idata = np.copy(np.asarray(other.idata))
        new_instance.coords = np.copy(other.coords) if other.coords is not None else None
        new_instance.coords_cg = np.copy(other.coords_cg) if other.coords_cg is not None else None
        new_instance.sdc = np.copy(other.sdc) if other.sdc is not None else None
        new_instance.sdc_cg = np.copy(other.sdc_cg) if other.sdc_cg is not None else None
        new_instance.tmap = np.copy(other.tmap) if other.tmap is not None else None
        new_instance.data_params = other.data_params.copy()
        return new_instance

def main():
    # Example usage of MRIData class
    shape_small = (100, 100)
    mri_data_small = MRIData(idata_shape=shape_small)
    print("Small data idata type:", type(mri_data_small.idata))

    shape_large = (10000, 10000)
    mri_data_large = MRIData(idata_shape=shape_large, nodeID=1, portname='port1')
    print("Large data idata type:", type(mri_data_large.idata))

    serialized_data = mri_data_large.serialize(nodeID=1, portname='port1')
    deserialized_data = MRIData.deserialize(serialized_data)
    print("Deserialized data idata type:", type(deserialized_data.idata))

    echo_times = np.array([10, 20, 30])
    axes_labels = ['x', 'y', 'z']
    mri_data_small.update_params(contrast="GRE", echo_times=echo_times, axes_labels=axes_labels, space="ispace", tau=15.0)
    print("Updated data_params:", mri_data_small.data_params)

    new_data = MRIData.clone(mri_data_small)
    print("Cloned data idata type:", type(new_data.idata))


if __name__ == "__main__":
    main()
