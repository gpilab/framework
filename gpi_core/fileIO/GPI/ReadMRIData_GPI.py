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


# Author: Guru Krishnamoorthy
# Date: 2025Jan02

import gpi
import numpy as np
from gpi import MRIData
import h5py
import json
import os

class ExternalNode(gpi.NodeAPI):
    '''Node summary goes here.
    '''

    def initUI(self):

        # IO Ports
        self.addWidget(
            'OpenFileBrowser', 'File Browser', button_title='Browse',
            caption='Open File', filter='mridata (*.mridata)')
        
        self.addOutPort('mri_data', 'MRIDATA')
        self.addOutPort('global_params', 'DICT')
        
        # store for later use
        self.URI = gpi.TranslateFileURI

    def compute(self):
        
        # start file browser
        fname = self.URI(self.getVal('File Browser'))

        # check that the path actually exists
        if not os.path.exists(fname):
            self.log.warn("ReadMRIData: path does not exist: " + str(fname))
            return 0

        mri_data = load_from_hdf5(fname)
        
        self.setData('mri_data', mri_data)
        self.setData('global_params', mri_data.global_params)
        
        return 0
    
def load_from_hdf5(file_path: str) -> 'MRIData':
    """Loads the MRIData object from an HDF5 file."""
    with h5py.File(file_path, 'r') as f:
        idata = f['idata'][:]
        axes_labels = f['axes_labels'][:]
        axes_labels = [label.decode('utf-8') for label in axes_labels]
        coords = f['coords'][:] if 'coords' in f else None
        coords_cg = f['coords_cg'][:] if 'coords_cg' in f else None
        sdc = f['sdc'][:] if 'sdc' in f else None
        sdc_cg = f['sdc_cg'][:] if 'sdc_cg' in f else None
        tmap_in = f['tmap_in'][:] if 'tmap_in' in f else None
        tmap_out = f['tmap_out'][:] if 'tmap_out' in f else None
        data_params = json.loads(f.attrs['data_params'])
        global_params = json.loads(f.attrs.get('global_params', '{}'))
        csm = f['csm'][:] if 'csm' in f else None
        
        
        # Convert lists back to numpy arrays in data_params
        for key, value in data_params.items():
            if isinstance(value, list):
                data_params[key] = np.array(value)

        # Convert lists back to numpy arrays in global_params
        for key, value in global_params.items():
            if isinstance(value, list):
                global_params[key] = np.array(value)
                
        mri_data = MRIData(idata_shape=idata.shape, axes_labels=axes_labels, dtype=idata.dtype)
        mri_data.idata = idata
        mri_data.coordinates.coords = coords
        mri_data.coordinates.coords_cg = coords_cg
        mri_data.coordinates.sdc = sdc
        mri_data.coordinates.sdc_cg = sdc_cg
        mri_data.coordinates.tmap_in = tmap_in
        mri_data.coordinates.tmap_out = tmap_out
        mri_data.data_params = data_params
        mri_data.global_params = global_params
        mri_data.csm = csm
        
        # Read extra arrays
        if 'extra_arrays' in f:
            extra_arrays_group = f['extra_arrays']
            for name in extra_arrays_group:
                array = extra_arrays_group[name][:]
                mri_data.add_array(name, array)

    return mri_data

