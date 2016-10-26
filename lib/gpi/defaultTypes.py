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


from .defines import ExternalType
from .logger import manager
# start logger for this module
log = manager.getLogger(__name__)

GPITYPE_PASS = 'PASS'

def osuper(cls, obj):
    '''for some reason (possibly old-style-class), super() fails in this
    module when using multiple canvases.  So instead of calling super()
    just return a handle to a new GPIDefaultType() instance.
    '''
    try:
        return super(cls, obj)
    except:
        return GPIDefaultType()
    return self

class GPIDefaultType(object):
    """This default class is the base class of all GPITypes.  It
    provides default behavior for edgeTips and toolTips.  The
    default behavior for port and data type matching is to pass.
    """
    GPIType = ExternalType  # ensures the subclass is of THIS class

    def __init__(self):
        # setup logger for subclasses
        self.log = manager.getLogger(__name__)

    def edgeTip(self, data):
        """Returns brief information for posting
        on the connection pipe. A one liner.
        """
        return ""

    def toolTip_Data(self, data):
        """Returns brief information for posting
        in the port's tool tip. This has specifics
        about the data being held at the outport.
        """
        return str(type(data))

    def toolTip_Port(self):
        """Returns brief information for posting
        in the port's tool tip about the port
        enforcement.
        """
        return str(GPITYPE_PASS)

    def matchesType(self, type_cls):
        """Returns True if self matches type_cls.
        By default all types match.
        Fail-usable in case the porttype
        can't be found.  type_cls is of the
        upstream port since the inPort is the
        limiting factor.
        """
        return True

    def isFreeType(self, type_cls=None):
        """Determine whether the compared type
        is implementing pass behavior (which
        is currently the default).
        """

        # With no args, 'self' is checked.
        if type_cls is None:
            if type(self) == GPIDefaultType:
                return True
            return False

        # test input class
        if type(type_cls) == GPIDefaultType:
            return True
        return False

    def matchesData(self, indata):
        """Returns True if self matches input data.
        By default all data matches.
        Fail-usable in case the porttype
        can't be found.
        """
        return True

    def setDataAttr(self, data):
        """Set any attributes on the data object
        (e.g. numpy arrays need to be readonly).
        the data object can be modified and
        returned in this hook.
        Passthrough by default.
        """
        return data

    def setTypeParms(self, **kwargs):
        """Use the kwargs dict to set user
        specified args to add<In/Out>Port()
        """
        for k, v in list(kwargs.items()):
            setter = "set_"+k
            if hasattr(self, setter):
                getattr(self, setter)(v)
            else:
                log.warn('No attribute \''+str(k)+'\' in port-type \''+str(GPITYPE_PASS)+'\',\n\t\tCheck your requested port-type in addInPort() or addOutPort().')
