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

# Brief: A GPI type extension for built-in python types.

from gpi import GPIDefaultType, osuper

# Maximum displayable string length for tips.
GPI_MAX_STR_LEN_DISP = 20

# standard python int




class INT(GPIDefaultType):
    """Enforcement for the standard python-int."""

    # Have the user pass the defining port traits to be checked.
    def __init__(self):
        super(INT, self).__init__()

        self._type = int  # the class is implicitly this type
        self._range = None  # useful for imposing widget settings

    def edgeTip(self, data):
        if data is None:
            return ""
        return str(data)

    def toolTip_Data(self, data):
        msg = str(self._type) + '\n'
        msg += "val: "+str(data)
        return msg

    def toolTip_Port(self):
        msg = str(self._type) + '\n'
        if self._range is not None:
            msg += "range: "+str(self._range)
        return msg

    def setDataAttr(self, data):
        return osuper(INT, self).setDataAttr(data)

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

        if self._range is not None:
            if type_cls._range is not None:
                # make sure the uport range is a subset of this one
                if self._range[0] > type_cls._range[0]:
                    return False
                if self._range[1] < type_cls._range[1]:
                    return False

        return True

    def matchesData(self, data):
        if self._type != type(data):
            return False

        if self._range is not None:
            # make sure data falls within the range.
            if self._range[0] > data:
                return False
            if self._range[1] < data:
                return False

        return True

    # setters
    def set_range(self, val):
        """int | Specify an integer range using a tuple (min, max)."""
        if type(val) != tuple:
            raise Exception("ERROR: \'range\' requires an \'tuple\'!")
        if len(val) != 2:
            raise Exception(
                "ERROR: \'range\' requires an \'tuple\' of len = 2!")
        for dim in val:
            if type(dim) != self._type:
                raise Exception("ERROR: \'range\' requires a \'tuple\' of \'"
                                + str(self._type)+"\' types!")
        self._range = val


# standard python float
class FLOAT(GPIDefaultType):
    """Enforcement for the standard python-float.
    """

    # Have the user pass the defining port traits to be checked.
    def __init__(self):
        super(FLOAT, self).__init__()

        self._type = float  # the class is implicitly this type
        self._range = None  # useful for imposing widget settings

    def edgeTip(self, data):
        if data is None:
            return ""
        return str(data)

    def toolTip_Data(self, data):
        msg = str(self._type) + '\n'
        msg += "val: "+str(data)
        return msg

    def toolTip_Port(self):
        msg = str(self._type) + '\n'
        if self._range is not None:
            msg += "range: "+str(self._range)
        return msg

    def setDataAttr(self, data):
        return osuper(FLOAT, self).setDataAttr(data)

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

        if self._range is not None:
            if type_cls._range is not None:
                # make sure the uport range is a subset of this one
                if self._range[0] > type_cls._range[0]:
                    return False
                if self._range[1] < type_cls._range[1]:
                    return False

        return True

    def matchesData(self, data):
        if self._type != type(data):
            return False

        if self._range is not None:
            # make sure data falls within the range.
            if self._range[0] > data:
                return False
            if self._range[1] < data:
                return False

        return True

    # setters
    def set_range(self, val):
        """float | Specify a float range using a tuple (min, max)."""
        if type(val) != tuple:
            raise Exception("ERROR: \'range\' requires an \'tuple\'!")
        if len(val) != 2:
            raise Exception(
                "ERROR: \'range\' requires an \'tuple\' of len = 2!")
        for dim in val:
            if type(dim) != self._type:
                raise Exception("ERROR: \'range\' requires a \'tuple\' of \'"
                                + str(self._type)+"\' types!")
        self._range = val

# standard python long


class LONG(GPIDefaultType):
    """Enforcement for the standard python-long."""

    # Have the user pass the defining port traits to be checked.
    def __init__(self):
        super(LONG, self).__init__()

        self._type = int  # the class is implicitly this type
        self._range = None  # useful for imposing widget settings

    def edgeTip(self, data):
        if data is None:
            return ""
        return str(data)

    def toolTip_Data(self, data):
        msg = str(self._type) + '\n'
        msg += "val: "+str(data)
        return msg

    def toolTip_Port(self):
        msg = str(self._type) + '\n'
        if self._range is not None:
            msg += "range: "+str(self._range)
        return msg

    def setDataAttr(self, data):
        return osuper(LONG, self).setDataAttr(data)

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

        if self._range is not None:
            if type_cls._range is not None:
                # make sure the uport range is a subset of this one
                if self._range[0] > type_cls._range[0]:
                    return False
                if self._range[1] < type_cls._range[1]:
                    return False

        return True

    def matchesData(self, data):
        if self._type != type(data):
            return False

        if self._range is not None:
            # make sure data falls within the range.
            if self._range[0] > data:
                return False
            if self._range[1] < data:
                return False

        return True

    # setters
    def set_range(self, val):
        """tuple(int,int) | Specify an integer range using a tuple (min, max)."""
        if type(val) != tuple:
            raise Exception("ERROR: \'range\' requires an \'tuple\'!")
        if len(val) != 2:
            raise Exception(
                "ERROR: \'range\' requires an \'tuple\' of len = 2!")
        for dim in val:
            if type(dim) != self._type:
                raise Exception("ERROR: \'range\' requires a \'tuple\' of \'"
                                + str(self._type)+"\' types!")
        self._range = val


# standard python complex
class COMPLEX(GPIDefaultType):
    """Enforcement for the standard python-complex."""

    # Have the user pass the defining port traits to be checked.
    def __init__(self):
        super(COMPLEX, self).__init__()

        self._type = complex  # the class is implicitly this type

    def edgeTip(self, data):
        if data is None:
            return ""
        return str(data)

    def toolTip_Data(self, data):
        msg = str(self._type) + '\n'
        msg += "val: "+str(data)
        return msg

    def toolTip_Port(self):
        return str(self._type)

    def setDataAttr(self, data):
        return osuper(COMPLEX, self).setDataAttr(data)

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

# standard python string


class STRING(GPIDefaultType):
    """Enforcement for the standard python-str."""

    # Have the user pass the defining port traits to be checked.
    def __init__(self):
        super(STRING, self).__init__()

        self._type = str  # the class is implicitly this type

    def edgeTip(self, data):
        if data is None:
            return ""
        if len(data) < GPI_MAX_STR_LEN_DISP:
            return str(data)
        else:
            return str(data[0:GPI_MAX_STR_LEN_DISP] + "...")

    def toolTip_Data(self, data):
        msg = str(self._type) + '\n'
        if data is not None:
            if len(data) < GPI_MAX_STR_LEN_DISP:
                msg += "val: "+str(data)
            else:
                msg += "val: "+str(data[0:GPI_MAX_STR_LEN_DISP] + "...")
        return msg

    def toolTip_Port(self):
        return str(self._type)

    def setDataAttr(self, data):
        return osuper(STRING, self).setDataAttr(data)

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

# standard python list


class LIST(GPIDefaultType):
    """Enforcement for the standard python-list."""

    # Have the user pass the defining port traits to be checked.
    def __init__(self):
        super(LIST, self).__init__()

        self._type = list  # the class is implicitly this type

    def edgeTip(self, data):
        if data is None:
            return ""
        return "len(list) = "+str(len(data))

    def toolTip_Data(self, data):
        msg = str(self._type) + '\n'
        if data is not None:
            msg += "len(list) = "+str(len(data))
        return msg

    def toolTip_Port(self):
        msg = str(self._type)
        return msg

    def setDataAttr(self, data):
        return osuper(LIST, self).setDataAttr(data)

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

# standard python tuple


class TUPLE(GPIDefaultType):
    """Enforcement for the standard python-tuple."""

    # Have the user pass the defining port traits to be checked.
    def __init__(self):
        super(TUPLE, self).__init__()

        self._type = tuple  # the class is implicitly this type

    def edgeTip(self, data):
        if data is None:
            return ""
        return "len(tuple) = "+str(len(data))

    def toolTip_Data(self, data):
        msg = str(self._type) + '\n'
        if data is not None:
            msg += "len(tuple) = "+str(len(data))
        return msg

    def toolTip_Port(self):
        msg = str(self._type)
        return msg

    def setDataAttr(self, data):
        return osuper(TUPLE, self).setDataAttr(data)

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

# standard python tuple


class DICT(GPIDefaultType):
    """Enforcement for the standard python-dict."""

    # Have the user pass the defining port traits to be checked.
    def __init__(self):
        super(DICT, self).__init__()

        self._type = dict  # the class is implicitly this type

    def edgeTip(self, data):
        if data is None:
            return ""
        return "len(dict) = "+str(len(data))

    def toolTip_Data(self, data):
        msg = str(self._type) + '\n'
        if data is not None:
            msg += "len(dict) = "+str(len(data))
        return msg

    def toolTip_Port(self):
        msg = str(self._type)
        return msg

    def setDataAttr(self, data):
        return osuper(DICT, self).setDataAttr(data)

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
