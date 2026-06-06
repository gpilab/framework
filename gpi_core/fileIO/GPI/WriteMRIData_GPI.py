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
from gpi import MRIData
import h5py
import json
import numpy as np

def save_to_hdf5(mri_data: MRIData, compress: bool, file_path: str) -> None:
    """Saves the MRIData object and global parameters to an HDF5 file with compression."""
    with h5py.File(file_path, 'w') as f:
        compression = 'gzip' if compress else None
        f.create_dataset('idata', data=mri_data.idata, compression=compression)
        f.create_dataset('axes_labels', data=np.array(mri_data.axes_labels, dtype='S'), compression=compression)  # Save as byte strings
        if mri_data.coordinates.coords is not None:
            f.create_dataset('coords', data=mri_data.coordinates.coords, compression=compression)
        if mri_data.coordinates.coords_cg is not None:
            f.create_dataset('coords_cg', data=mri_data.coordinates.coords_cg, compression=compression)
        if mri_data.coordinates.sdc is not None:
            f.create_dataset('sdc', data=mri_data.coordinates.sdc, compression=compression)
        if mri_data.coordinates.sdc_cg is not None:
            f.create_dataset('sdc_cg', data=mri_data.coordinates.sdc_cg, compression=compression)
        # Add tmap_in and tmap_out if they exist
        for attr in ['tmap_in', 'tmap_out']:
            data = getattr(mri_data.coordinates, attr, None)
            if data is not None and data.ndim == 2:
                f.create_dataset(attr, data=data, compression=compression)
        if mri_data.csm is not None:
            f.create_dataset('csm', data=mri_data.csm, compression=compression)
        # Save extra arrays
        if mri_data.extra_arrays:
            group = f.create_group('extra_arrays')
            for name, array in mri_data.extra_arrays.items():
                if array is not None:
                    group.create_dataset(name, data=array, compression=compression)

        # Serialize data_params and global_params
        if mri_data.data_params:
            data_params_serializable = mri_data.data_params.copy()
            for key, value in data_params_serializable.items():
                if isinstance(value, np.ndarray):
                    data_params_serializable[key] = value.tolist()
            f.attrs['data_params'] = json.dumps(data_params_serializable)
        
        if mri_data.global_params:
            global_params_serializable = mri_data.global_params.copy()
            for key, value in global_params_serializable.items():
                if isinstance(value, np.ndarray):
                    global_params_serializable[key] = value.tolist()
            f.attrs['global_params'] = json.dumps(global_params_serializable)
            
class ExternalNode(gpi.NodeAPI):
    '''Node summary goes here.
    '''

    def initUI(self):

        # IO Ports
        self.addWidget(
            'SaveFileBrowser', 'File Browser', button_title='Browse',
            caption='Save File (*.mridata)', directory='~/',
            filter='mridata (*.mridata)')
        
        self.addWidget('PushButton', 'Write Mode', button_title='Write on New Filename', toggle=True)
        self.addWidget('PushButton', 'Write Now', button_title='Write Right Now', toggle=False)
        self.addWidget('PushButton', 'compress (GZIP)', toggle=True)
        # IO Ports
        self.addInPort('mri_data_in', 'MRIDATA')
        
        # IO Ports
        self.addInPort('csm', 'NPYarray', obligation=gpi.OPTIONAL)
        self.addInPort('global_params', 'DICT', obligation=gpi.OPTIONAL)

        # store for later use
        self.URI = gpi.TranslateFileURI
        
    def validate(self):

        if self.getVal('Write Mode'):
            self.setAttr('Write Mode', button_title="Write on Every Event")
        else:
            self.setAttr('Write Mode', button_title="Write on New Filename")

        return 0

    def compute(self):
        

        if self.getVal('Write Mode') or self.getVal('Write Now') or ('File Browser' in self.widgetEvents()):

            fname = self.URI(self.getVal('File Browser'))
            if not fname.endswith('.mridata'):
                fname += '.mridata'

            if fname == '.mridata':
                return 0

            mri_data:MRIData = self.getData('mri_data_in')
            
            csm = self.getData('csm')
            global_params = self.getData('global_params')
            
            # help print
            #mri_data.help()
            
            # example to add new npy array to mri_data
            #new_array = np.zeros((100, 100))
            #mri_data.add_array('new_array', new_array)
            
            #add csm to mri_data
            mri_data.csm = csm
            
            # add lobal param to mri_data
            if global_params:
                mri_data.global_params.update(global_params)
            
            compress = self.getVal('compress (GZIP)')
            save_to_hdf5(mri_data, compress, fname)

        return(0)
    

