#!/usr/bin/env python

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
# Brief: A GPI type extension for MRIDATA object arrays.

from gpi import GPIDefaultType, osuper
from gpi.mri_data import MRIData
import numpy as np
import inspect

class MRIDATA(GPIDefaultType):
    """Enforcement for the standard python-dict."""

    # Have the user pass the defining port traits to be checked.
    def __init__(self):
        super(MRIDATA, self).__init__()

        self._type = MRIData  # the class is implicitly this type

    def edgeTip(self, data):
        if data is None:
            return ""
        
        idata_shape = str(data.idata.shape) if hasattr(data, 'idata') and hasattr(data.idata, 'shape') else "unknown"
        space = data.axes_labels if hasattr(data, 'axes_labels') else "unknown"
        
        return f"idata shape = {idata_shape}, space: {space}"

    def toolTip_Data(self, data):
        msg = ''
        if data is not None:
            if hasattr(data, 'idata') and hasattr(data.idata, 'shape'):
                msg += f"idata shape: {data.idata.shape}\n"
            if hasattr(data, 'axes_labels'):
                msg += f"axes_labels: {data.axes_labels}\n"
            for key, value in data.data_params.items():
                if key == 'echo_times' and isinstance(value, np.ndarray) and value.ndim == 2:
                    msg += f"  {key}(msec):\n"
                    msg += "                " + "\t".join([f"Echo {j}" for j in range(value.shape[1])]) + "\n"
                    for i, row in enumerate(value):
                        msg += f"    Shot {i}: " + "\t".join(f"{v:.2f}" for v in row) + "\n"
                else:
                    msg += f"  {key}: {value:.2f}\n" if isinstance(value, float) else f"  {key}: {value}\n"
        else:
            return osuper(MRIDATA, self).toolTip_Data(data)
            
        return msg

    def toolTip_Port(self):
        msg = str(self._type)
        return msg

    def setDataAttr(self, data):
        return osuper(MRIData, self).setDataAttr(data)

    def matchesType(self, type_cls):

        if self.isFreeType(type_cls):
            self.log.info(str(self.__class__)+"matchesType(): upstream port is free.")
            return True

        # if this isn't true then these classes
        # cannot be compared any further
        # the input is the upstream port
        if type(type_cls) != type(self):
            self.log.info(str(self.__class__)+"matchesType(): port class cannot be compared.")
            return False

        return True

    def matchesData(self, data):
        return (self._type == type(data))