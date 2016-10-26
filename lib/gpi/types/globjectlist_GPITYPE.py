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

# Brief: A GPI type extension for GPI-GL object arrays.


from gpi import GPIDefaultType, osuper
import gpi.GLObjects as glo


class GLOList(GPIDefaultType):
    """Allows passing GPI-GL object definitions to be passed in lists.
    """

    # Have the user pass the defining port traits to be checked.
    def __init__(self):
        super(GLOList, self).__init__()

        self._type = glo.ObjectList  # the class is implicitly this type

    def edgeTip(self, data):
        if type(data) == self._type:
            if data.len() != 1:
                msg = '\n' + str(data.len()) + ' GLObjs'
            else:
                msg = '\n' + str(data.len()) + ' GLObj'
            return msg
        return osuper(GLOList, self).edgeTip(data)

    def toolTip_Data(self, data):
        if type(data) == self._type:
            msg = str(type(data))
            if data.len() != 1:
                msg += '\n' + str(data.len()) + ' GLObjs'
            else:
                msg += '\n' + str(data.len()) + ' GLObj'
            return msg
        else:
            return osuper(GLOList, self).toolTip_Data(data)

    def toolTip_Port(self):
        msg = []
        msg.append(str(self._type))
        return '\n'.join(msg)

    def setDataAttr(self, data):
        return osuper(GLOList, self).setDataAttr(data)

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
        if self._type != type(data):
            return False
        return True

