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


# Brief: A GPI type extension for numpy arrays.

import inspect
import numpy as np

# gpi
from gpi import GPIDefaultType, osuper


class NPYarray(GPIDefaultType):
    """The NPYarray type provides port enforcement for numpy
    multidimensional arrays (ndarray).  The enforcement parms
    are type (ndarray), dtype, ndim, dimension range (drange),
    shape, and vec (the len of the last dim).  Enforcement
    priority for aliased parms goes ndim->drange->shape.  Although
    shape and vec can overlap, they are enforced independently.
    """

    # Have the user pass the defining port traits to be checked.
    def __init__(self):
        super(NPYarray, self).__init__()

        self._type = [np.ndarray, np.memmap]  # the class is implicitly this type
        self._dtype = []  # a list of types
        self._ndim = None
        self._drange = None
        self._shape = None
        self._vec = None  # the last dim-length

    def edgeTip(self, data):
        if type(data) in self._type:
            msg = str(data.shape)
            return msg
        return osuper(NPYarray, self).edgeTip(data)

    def toolTip_Data(self, data):
        if type(data) in self._type:
            msg = str(data.dtype) + '\n'
            msg += "shape: "+str(data.shape)
            return msg
        else:
            return osuper(NPYarray, self).toolTip_Data(data)

    def toolTip_Port(self):
        msg = []
        msg.append(str(self._type))
        if len(self._dtype) > 0:
            msg.append(str(self._dtype))
        if self._ndim:
            msg.append("ndim: "+str(self._ndim))
        elif self._drange:  # ndim takes precedence.
            msg.append("drange: "+str(self._drange))
        elif self._shape:  # drange takes precedence.
            msg.append("shape: "+str(self._shape))
        if self._vec:
            msg.append("vec: "+str(self._vec))
        return '\n'.join(msg)

    def setDataAttr(self, data):
        # set NPY array to read-only
        # so downstream mods don't accidentally
        # edit it.
        if type(data) in self._type:
            data.flags.writeable = False
            if not data.flags['C_CONTIGUOUS']:
                cf = inspect.currentframe().f_back.f_back
                try:
                    pname = '\''+str(cf.f_locals['pnumORtitle'])+'\''
                except:
                    pname = '(can\'t resolve port name)'
                try:
                    fname = '\''+str(cf.f_back.f_locals['self'].__module__)+'\''
                except:
                    fname = '(can\'t reslove file name)'
                self.log.warn(__name__+': Output array is not contiguous, forcing contiguity:\n\tFILE: '+fname+', PORT: '+pname)
                data = np.ascontiguousarray(data)
            return data
        else:
            return osuper(NPYarray, self).setDataAttr(data)

    def matchesType(self, type_cls):

        if self.isFreeType(type_cls):
            self.log.info(str(self.__class__)+ "matchesType(): upstream port is free.")
            return True

        # if this isn't true then these classes
        # cannot be compared any further
        # the input is the upstream port
        if type(type_cls) != type(self):
            self.log.info(str(self.__class__)+ "matchesType(): port class cannot be compared.")
            return False

        if len(self._dtype) and len(type_cls._dtype):
            # if at least one type in the list matches, then pass it
            typ_passed = False
            for typ in type_cls._dtype:
                if typ in self._dtype:
                    typ_passed = True

            if not typ_passed:
                self.log.info(str(self.__class__)+ "matchesType(): dtype doesn't match.")
                return False

        if self._ndim is not None:
            if type_cls._ndim is not None:
                if self._ndim != type_cls._ndim:
                    self.log.info(str(self.__class__)+ "matchesType(): ndim doesn't match.")
                    return False

        elif self._drange is not None:
            if type_cls._drange is not None:
                if self._drange != type_cls._drange:
                    self.log.info(str(self.__class__)+ "matchesType(): drange doesn't match.")
                    return False

        elif self._shape is not None:
            if type_cls._shape is not None:
                if self._shape != type_cls._shape:
                    self.log.info(str(self.__class__)+ "matchesType(): shape doesn't match.")
                    return False

        if self._vec is not None:
            if type_cls._vec is not None:
                if self._vec != type_cls._vec:
                    self.log.info(str(self.__class__)+ "matchesType(): vec doesn't match.")
                    return False

        return True

    def matchesData(self, data):
        if type(data) not in self._type:
            return False

        if len(self._dtype):
            if not data.dtype in self._dtype:
                return False

        if self._ndim:
            if self._ndim != data.ndim:
                return False

        elif self._drange:
            if (data.ndim < self._drange[0]) or (data.ndim > self._drange[1]):
                return False

        elif self._shape:
            if self._shape != data.shape:
                return False

        if self._vec:
            if self._vec != data.shape[-1]:
                return False

        return True

    # setters
    def set_ndim(self, val):
        """int | Set enforcement for the number of dimensions.  Requires (int)."""
        if type(val) != int:
            raise Exception("ERROR: \'ndim\' requires an \'int\'!")
        self._ndim = val

    def set_drange(self, val):
        """tuple(int,int) | Requires a dimension range tuple (min, max)."""
        if type(val) != tuple:
            raise Exception("ERROR: \'drange\' requires an \'tuple\'!")
        if len(val) != 2:
            raise Exception(
                "ERROR: \'drange\' requires an \'tuple\' of len = 2!")
        for dim in val:
            if type(dim) != int:
                raise Exception(
                    "ERROR: \'drange\' requires a \'tuple\' of \'int\' types!")
        self._drange = val

    def set_dtype(self, val):
        """numpy dtype | Requires an NPY type (i.e. float32, complex64, etc...)"""
        if type(val) is list:
            for t in val:
                if type(t) != type:
                    raise Exception("ERROR: \'dtype\' requires a \'type\'!")
            self._dtype = val
            return

        if type(val) != type:
            raise Exception("ERROR: \'dtype\' requires a \'type\'!")
        self._dtype.append(val)

    def set_shape(self, val):
        """tuple(int,int,...) | Requires the dimension lengths in an integer tuple."""
        if type(val) != tuple:
            raise Exception("ERROR: \'shape\' requires a \'tuple\'!")
        for dim in val:
            if type(dim) != int:
                raise Exception(
                    "ERROR: \'shape\' requires a \'tuple\' of \'int\' types!")
        self._shape = val

    def set_vec(self, val):
        """int | Requires an integer representing the length of the last
        (most varying) dimension (or shape[-1]).
        """
        if type(val) != int:
            raise Exception("ERROR: \'vec\' requires an \'int\'!")
        if val <= 0:
            raise Exception("ERROR: \'vec\' requires an \'int\' > 0!")
        self._vec = val
