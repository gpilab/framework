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

class ExternalNode(gpi.NodeAPI):
    '''Node summary goes here.
    '''

    def initUI(self):

        # IO Ports
        self.addInPort('mri_data_in', 'MRIDATA')
        self.addWidget('TextBox', 'Data info: ')

        self.addOutPort('data', 'NPYarray')
        self.addOutPort('coords', 'NPYarray')
        self.addOutPort('sdc', 'NPYarray')
        self.addOutPort('coords_cg', 'NPYarray')
        self.addOutPort('sdc_cg', 'NPYarray')
        self.addOutPort('tmap_in', 'NPYarray')
        self.addOutPort('tmap_out', 'NPYarray')
        self.addOutPort('csm', 'NPYarray')
        self.addOutPort('data_params', 'DICT')
        self.addOutPort('global_params', 'DICT')

        
        self.addOutPort('extra_array1', 'NPYarray')
        self.addOutPort('extra_array2', 'NPYarray')

    def compute(self):

        # GETTING PORT DATA
        mri_data_in = self.getData('mri_data_in')
        try:
            # SETTING PORT DATA
            self.setData('data', mri_data_in.idata)
            self.setData('coords', mri_data_in.coordinates.coords)
            self.setData('coords_cg', mri_data_in.coordinates.coords_cg)
            self.setData('sdc', mri_data_in.coordinates.sdc)
            self.setData('sdc_cg', mri_data_in.coordinates.sdc_cg)
            self.setData('tmap_in', mri_data_in.coordinates.tmap_in if mri_data_in.coordinates.tmap_in is not None and mri_data_in.coordinates.tmap_in.ndim == 2 else None)
            self.setData('tmap_out', mri_data_in.coordinates.tmap_out if mri_data_in.coordinates.tmap_out is not None and mri_data_in.coordinates.tmap_out.ndim == 2 else None)
            
            self.setData('csm', mri_data_in.csm)


            # Set extra arrays to output ports
            for i, (name, array) in enumerate(mri_data_in.extra_arrays.items()):  
                if i <= 2:
                    array_name = f'extra_array{i+1}'
                    self.setData(array_name, array)



            self.setData('data_params', mri_data_in.data_params or None)
            self.setData('global_params', mri_data_in.global_params or None)

            # Adding dimensions of the variables to the info string
            info_str = "Data Dimensions:\n"
            info_str += f"  data: {mri_data_in.idata.shape}\n\n"

            info_str += "coordinates Dimensions:\n"
            info_str += f"  coords: {mri_data_in.coordinates.coords.shape}\n"
            info_str += f"  sdc: {mri_data_in.coordinates.sdc.shape}\n"
            info_str += f"  coords_cg: {mri_data_in.coordinates.coords_cg.shape}\n"
            info_str += f"  sdc_cg: {mri_data_in.coordinates.sdc_cg.shape}\n"
            info_str += f"  tmap_in: {mri_data_in.coordinates.tmap_in.shape}\n"
            info_str += f"  tmap_out: {mri_data_in.coordinates.tmap_out.shape}\n"

            # Creating a formatted print of the info dictionary
            info_str += "\nData Params:\n"
            info_str += f"axes_labels: {mri_data_in.axes_labels}\n"
            for key, value in mri_data_in.data_params.items():
                if key == 'echo_times' and isinstance(value, np.ndarray) and value.ndim == 2:
                    info_str += f"  {key}(msec):\n"
                    info_str += "                " + "\t".join([f"Echo {j}" for j in range(value.shape[1])]) + "\n"
                    for i, row in enumerate(value):
                        info_str += f"    Shot {i}: " + "\t".join(f"{v:.2f}" for v in row) + "\n"
                else:
                    info_str += f"  {key}: {value:.2f}\n" if isinstance(value, float) else f"  {key}: {value}\n"


            info_str += "\n\n\n"
            for i, (name, array) in enumerate(mri_data_in.extra_arrays.items()):
                info_str += f"Extra Array 1:  {name}: {array.shape}\n"

            self.setAttr('Data info: ', val=info_str)



        except AttributeError as e:
            self.log.error(f"Error accessing rawData attributes: {e}")
            return 0



        return 0

