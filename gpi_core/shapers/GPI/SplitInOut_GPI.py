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
        self.addInPort('data_combined', 'MRIDATA')

        self.addOutPort('data_in', 'MRIDATA')
        self.addOutPort('data_out', 'MRIDATA')
        self.addOutPort('nav', 'NPYarray')

    def compute(self):

        # GETTING PORT DATA
        data_combined = self.getData('data_combined')
        data_params = data_combined.data_params
        spiral_gen_params = data_params.get('spiral_gen_params', None)
        if spiral_gen_params is None:
            self.log.error("Spiral generation parameters not found in input data.")
            self.setData('data_out', data_combined)
            return 0

        direction = spiral_gen_params['spiraldirect']

        if direction == 'in':
            self.setData('data_in', data_combined)
            self.setData('data_out', None)
            self.setData('nav', None)
            return 0

        elif direction == 'out':
            self.setData('data_in', None)
            self.setData('data_out', data_combined)
            self.setData('nav', None)
            return 0

        elif direction in ['in-out', 'out-in']:
            readout_lengths = data_params.get('readout_lengths', {})
            readout_lengths_cg = data_params.get('readout_lengths_cg', {})
            nshots = data_combined.coordinates.coords.shape[0]
            nechoes = spiral_gen_params.get('nechoes', 1)
            dwell = spiral_gen_params.get('dwell', 1e-6)
            axes_labels = data_combined.axes_labels

            len_in  = readout_lengths.get('in', 0)
            len_out = readout_lengths.get('out', 0)
            len_nav = readout_lengths.get('nav', 0)
            len_in_cg  = readout_lengths_cg.get('in', 0)
            len_out_cg = readout_lengths_cg.get('out', 0)

            if direction == 'in-out':
                offset_in, offset_out = 0, len_in + len_nav
                offset_nav = len_in
                offset_in_cg, offset_out_cg = 0, len_in_cg
                block = len_in + len_nav + len_out
                block_cg = len_in_cg + len_out_cg
            else:  # 'out-in' (no nav)
                offset_out, offset_in = 0, len_out
                offset_out_cg, offset_in_cg = 0, len_out_cg
                offset_nav = None
                block = len_out + len_in
                block_cg = len_out_cg + len_in_cg

            def allocate_mriData(base_shape, label_override, nsamp, portname):
                shape = list(base_shape)
                shape[-1] = nsamp
                return self.init_mriData(tuple(shape), label_override, portname)

            def build_dataset(portname, l_main, l_cg, offset, offset_cg, tmap_key):
                echo_flag = nechoes > 1
     

                if echo_flag:
                    base_shape = list(data_combined.idata.shape)
                    base_shape[-1]  = l_main
                    base_shape.insert(-3, nechoes)
                    axes_labels_echo = axes_labels.copy()
                    axes_labels_echo.insert(-3, 'echo')
                    mri_data = allocate_mriData(base_shape, axes_labels_echo, l_main, portname)
                    narms = data_combined.coordinates.coords.shape[-3]
                    nsamples = data_combined.idata.shape[-2]
                    ndim = data_combined.coordinates.coords.shape[-1]

                    mri_data.coordinates.coords = np.zeros((nshots, nechoes, narms,  l_main, ndim), dtype=np.float32)
                    mri_data.coordinates.sdc = np.zeros((nshots, nechoes, narms, l_main), dtype=np.float32)
                    mri_data.coordinates.coords_cg = np.zeros((nshots, nechoes, narms, l_cg, ndim), dtype=np.float32)
                    mri_data.coordinates.sdc_cg = np.zeros((nshots, nechoes,  narms, l_cg), dtype=np.float32)

                    for e in range(nechoes):
                        s_idx = e * block + offset
                        e_idx = s_idx + l_main
                        for s in range(nshots):
                            mri_data.idata[...,s, e, :, :] = data_combined.idata[..., s, :, s_idx:e_idx]

                            mri_data.coordinates.coords[s, e, :, :, :] = data_combined.coordinates.coords[s,:, s_idx:e_idx, :]
                            mri_data.coordinates.sdc[s, e, :, :]       = data_combined.coordinates.sdc[s,:, s_idx:e_idx]

                            mri_data.coordinates.coords_cg[s, e, :, :, :] = data_combined.coordinates.coords_cg[s,:, offset_cg:offset_cg + l_cg, :]
                            mri_data.coordinates.sdc_cg[s, e, :, :]       = data_combined.coordinates.sdc_cg[s,:, offset_cg:offset_cg + l_cg]
                else:
                    base_shape = data_combined.idata.shape
                    axes_labels_echo = axes_labels
                    mri_data = allocate_mriData(base_shape, axes_labels_echo, l_main, portname)
                    s_idx = offset
                    e_idx = s_idx + l_main
                    mri_data.idata = data_combined.idata[..., s_idx:e_idx]

                    mri_data.coordinates.coords = data_combined.coordinates.coords[:, :, s_idx:e_idx, :]
                    mri_data.coordinates.sdc    = data_combined.coordinates.sdc[:, :, s_idx:e_idx]

                    mri_data.coordinates.coords_cg = data_combined.coordinates.coords_cg[:, :, offset_cg:offset_cg + l_cg, :]
                    mri_data.coordinates.sdc_cg    = data_combined.coordinates.sdc_cg[:, :, offset_cg:offset_cg + l_cg]

                mri_data.coordinates.tmap_in  = data_combined.coordinates.tmap_in if tmap_key == 'in'  else 0
                mri_data.coordinates.tmap_out = data_combined.coordinates.tmap_out if tmap_key == 'out' else 0
                mri_data.data_params = {k: v for k, v in data_params.items()
                                        if k not in ['readout_lengths', 'readout_lengths_cg']}
                mri_data.data_params['tau'] = l_main * dwell
                mri_data.data_params['spiral_gen_params']['spiraldirect'] = tmap_key
                return mri_data

            data_in  = build_dataset('data_in',  len_in,  len_in_cg,  offset_in,  offset_in_cg,  'in')
            data_out = build_dataset('data_out', len_out, len_out_cg, offset_out, offset_out_cg, 'out')

            self.setData('data_in', data_in)
            self.setData('data_out', data_out)

            # Optional: extract nav only for 'in-out'
            if direction == 'in-out' and len_nav > 0:
                if nechoes > 1:
                    nav = np.stack([
                        data_combined.idata[..., :, :, e * block + offset_nav : e * block + offset_nav + len_nav]
                        for e in range(nechoes)
                    ], axis=-3)  # echo axis before arm/sample
                else:
                    s = offset_nav
                    nav = data_combined.idata[..., s : s + len_nav]
                self.setData('nav', nav)
            else:
                self.setData('nav', None)

        return 0


    #%% # Function to allocate memory for large arrays
    def init_mriData(self, shape, axes_labels, title):
        mri_data = gpi.MRIData(idata_shape=shape, axes_labels=axes_labels, nodeID=self.node.getID(), portname=title)
        
        return mri_data