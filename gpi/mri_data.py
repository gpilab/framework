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
from typing import List, Any, Dict, Optional
import os
import hashlib
from .defines import GPI_SHDM_PATH

@dataclass
class Coordinates:
    coords: Optional[np.ndarray] = None  # Coordinates array
    coords_cg: Optional[np.ndarray] = None  # Constant gradient coordinates array
    sdc: Optional[np.ndarray] = None  # Sampling density compensation
    sdc_cg: Optional[np.ndarray] = None  # Constant gradient sampling density compensation
    tmap: Optional[np.ndarray] = None  # Time-map array

@dataclass
class MRIData:
    """
    A class to represent MRI data with support for memory-mapped files and shared memory.
    """
    memmap_threshold: int = 32  # Threshold in MB for using memory-mapped files
    idata: np.ndarray = field(init=False)  # Image data array
    axes_labels: List[str] = field(default_factory=list)  # Mandatory axes labels
    coordinates: Coordinates = field(default_factory=Coordinates)  # Coordinates category
    data_params: Optional[Dict[str, Any]] = None  # Optional dictionary of data parameters
    global_params: Optional[Dict[str, Any]] = None  # Optional dictionary of global parameters
    extra_arrays: Dict[str, np.ndarray] = field(default_factory=dict)  # User-defined arrays

    def __init__(self, idata_shape, axes_labels, dtype=np.complex64, nodeID=None, portname=None, data_params=None, global_params=None):
        if len(idata_shape) != len(axes_labels):
            raise ValueError("MRIData: The length of idata_shape and axes_labels must be the same.")
        self.idata = self._initialize_data(idata_shape, dtype, nodeID, portname)
        self.axes_labels = axes_labels
        self.coordinates = Coordinates()  # Initialize coordinates
        self.data_params = data_params if data_params else {}
        self.global_params = global_params if global_params else {}
        self.extra_arrays = {}  # Initialize extra arrays

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
    
    def add_array(self, name: str, array: np.ndarray):
        """Add a new array with a specified name."""
        if name in self.extra_arrays:
            raise ValueError(f"An array with the name '{name}' already exists.")
        self.extra_arrays[name] = array

    def get_array(self, name: str) -> np.ndarray:
        """Retrieve an array by its name."""
        if name not in self.extra_arrays:
            raise KeyError(f"No array found with the name '{name}'.")
        return self.extra_arrays[name]

    def remove_array(self, name: str):
        """Remove an array by its name."""
        if name in self.extra_arrays:
            del self.extra_arrays[name]
        else:
            raise KeyError(f"No array found with the name '{name}'.")

    def update_global_params(self, **kwargs):
        """Update global parameters."""
        if self.global_params is None:
            self.global_params = {}
        self.global_params.update(kwargs)

    def update_data_params(self, **kwargs):
        """Update data parameters."""
        if self.data_params is None:
            self.data_params = {}
        self.data_params.update(kwargs)

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
            'coordinates': {
                'coords': self.coordinates.coords,
                'coords_cg': self.coordinates.coords_cg,
                'sdc': self.coordinates.sdc,
                'sdc_cg': self.coordinates.sdc_cg,
                'tmap': self.coordinates.tmap,
            },
            'axes_labels': self.axes_labels,
            'data_params': self.data_params,
            'global_params': self.global_params,
            'extra_arrays': {k: v.tolist() for k, v in self.extra_arrays.items()}  # Convert arrays to lists for serialization
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
        instance = cls(
            idata_shape=idata_shape,
            axes_labels=data['axes_labels'],
            dtype=idata_dtype,
            data_params=data.get('data_params', {}),
            global_params=data.get('global_params', {})
        )
        instance.idata = idata
        instance.coordinates = Coordinates(
            coords=data['coordinates']['coords'],
            coords_cg=data['coordinates']['coords_cg'],
            sdc=data['coordinates']['sdc'],
            sdc_cg=data['coordinates']['sdc_cg'],
            tmap=data['coordinates']['tmap']
        )
        instance.extra_arrays = {k: np.array(v) for k, v in data.get('extra_arrays', {}).items()}  # Reconstruct arrays
        return instance

    def clone(self) -> 'MRIData':
        """Clones the MRIData object."""
        new_instance = MRIData(
            idata_shape=self.idata.shape,
            axes_labels=self.axes_labels,
            dtype=self.idata.dtype,
            data_params=self.data_params.copy() if self.data_params else None,
            global_params=self.global_params.copy() if self.global_params else None
        )
        new_instance.idata = np.copy(np.asarray(self.idata))
        new_instance.coordinates = Coordinates(
            coords=np.copy(self.coordinates.coords) if self.coordinates.coords is not None else None,
            coords_cg=np.copy(self.coordinates.coords_cg) if self.coordinates.coords_cg is not None else None,
            sdc=np.copy(self.coordinates.sdc) if self.coordinates.sdc is not None else None,
            sdc_cg=np.copy(self.coordinates.sdc_cg) if self.coordinates.sdc_cg is not None else None,
            tmap=np.copy(self.coordinates.tmap) if self.coordinates.tmap is not None else None
        )
        new_instance.extra_arrays = {k: np.copy(v) for k, v in self.extra_arrays.items()}
        return new_instance
    
    def help(self):
        """Prints examples and method usages of the MRIData class."""
        help_text = """
        MRIData Class Usage:

        Initialization:
        
        mri_data = MRIData(idata_shape=(10, 20, 30, 40), axes_labels=['slice', 'channel', 'arm', 'sample'], dtype=np.complex64)
        # Example with portID and portname ofr memmory mapping large dataset to minize RAM usage
        shape_large = (10000, 10000)
        axes_labels_large = ['x', 'y']
        mri_data_large = MRIData(idata_shape=shape_large, axes_labels=axes_labels_large, nodeID=self.node.getID(), portname='<outport_title>')
        print("Large data idata type:", type(mri_data_large.idata))
        

        Accessing and Modifying idata:
        idata = mri_data.idata
        mri_data.idata[0, 0] = 1.0

        Adding, Retrieving, and Removing Extra Arrays:
        mri_data.add_array('new_array', np.array([1, 2, 3]))
        array = mri_data.get_array('new_array')
        mri_data.remove_array('new_array')
        
        # Example for Coordinates:
        coords = np.array([[1, 2, 3], [4, 5, 6]])
        coords_cg = np.array([[7, 8, 9], [10, 11, 12]])
        sdc = np.array([0.1, 0.2, 0.3])
        sdc_cg = np.array([0.4, 0.5, 0.6])
        tmap = np.array([0.7, 0.8, 0.9])

        mri_data.coordinates.coords = coords
        mri_data.coordinates.coords_cg = coords_cg
        mri_data.coordinates.sdc = sdc
        mri_data.coordinates.sdc_cg = sdc_cg
        mri_data.coordinates.tmap = tmap

        print("Coordinates:", mri_data.coordinates.coords)
        print("Constant Gradient Coordinates:", mri_data.coordinates.coords_cg)
        print("Sampling Density Compensation:", mri_data.coordinates.sdc)
        print("Constant Gradient Sampling Density Compensation:", mri_data.coordinates.sdc_cg)
        print("Time-map:", mri_data.coordinates.tmap)
        
        
        Updating Parameters:
        mri_data.update_global_params(field_strength=3.0, trajectory='spiral')
        mri_data.update_data_params('echo_time'=12.0, contrast='GRE')

        Cloning:
        cloned_data = mri_data.clone()

        Example Usage:
        shape = (100, 100)
        axes_labels = ['x', 'y']
        mri_data = MRIData(idata_shape=shape, axes_labels=axes_labels, dtype=np.float32)
        print("idata shape:", mri_data.get_idata().shape)

        shape_4d = (10, 20, 30, 40)
        axes_labels_4d = ['slice', 'channel', 'arm', 'sample']
        mri_data_4d = MRIData(idata_shape=shape_4d, axes_labels=axes_labels_4d, dtype=np.complex64)
        print("4D idata shape:", mri_data_4d.get_idata().shape)
        """
        print(help_text)


def main():
    # Example usage of MRIData class
    shape_small = (100, 100)
    axes_labels = ['x', 'y']
    global_params = {"key1": "value1", "key2": "value2"}
    mri_data_small = MRIData(idata_shape=shape_small, axes_labels=axes_labels, global_params=global_params)
    print("Small data global_params:", mri_data_small.global_params)

    shape_large = (10000, 10000)
    mri_data_large = MRIData(idata_shape=shape_large, axes_labels=axes_labels, nodeID=1, portname='port1')
    print("Large data idata type:", type(mri_data_large.idata))

    # Updating coordinates example
    new_coords = np.array([[1, 2], [3, 4]])
    new_coords_cg = np.array([[5, 6], [7, 8]])
    new_sdc = np.array([0.1, 0.2])
    mri_data_small.coordinates.coords = new_coords
    mri_data_small.coordinates.coords_cg = new_coords_cg
    mri_data_small.coordinates.sdc = new_sdc
    print("Updated coordinates:", mri_data_small.coordinates)

    serialized_data = mri_data_large.serialize(nodeID=1, portname='port1')
    deserialized_data = MRIData.deserialize(serialized_data)
    print("Deserialized data global_params:", deserialized_data.global_params)

    new_data = MRIData.clone(mri_data_small)
    print("Cloned data global_params:", new_data.global_params)

if __name__ == "__main__":
    main()
