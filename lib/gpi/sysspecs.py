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
#    MAKES NO WARRANTY AND HAS NOR LIABILITY ARISING FROM ANY USE OF THE
#    SOFTWARE IN ANY HIGH RISK OR STRICT LIABILITY ACTIVITIES.

# Brief: A class for getting relevant system specifications.


import platform
try:
    import psutil
except:
    psutil = None

# gpi
from .defines import GetHumanReadable_bytes


class SysSpecs(object):
    
    def __init__(self):

        # determine OS
        self._inOSX = (platform.system() == 'Darwin')
        self._inLinux = (platform.system() == 'Linux')
        self._inWindows = (platform.system() == 'Windows')

        self._plat = {}

        # platform
        self._plat['HOSTNAME'] = str(platform.node())
        self._plat['PLATFORM'] = str(platform.platform())
        self._plat['OS'] = str(platform.system())
        if self.inOSX():
            self._plat['OSX'] = str(platform.mac_ver()[0])
        self._plat['PYTHON'] = str(platform.python_implementation())
        self._plat['PYTHON_VERSION'] = str(platform.python_version())

        # psutil
        if psutil:
            # not sure what the default behavior is for psutil

            try:
                self._plat['TOTAL_PHYMEM'] = psutil.TOTAL_PHYMEM
            except:
                self._plat['TOTAL_PHYMEM'] = 0

            self._plat['TOTAL_PHYMEM_STR'] = GetHumanReadable_bytes(self._plat['TOTAL_PHYMEM'])

            try:
                self._plat['NUM_CPUS'] = psutil.NUM_CPUS
            except:
                self._plat['NUM_CPUS'] = 0

    # determine OS for easy downstream use
    def inOSX(self):
        return self._inOSX

    def inLinux(self):
        return self._inLinux

    def inWindows(self):
        return self._inWindows

    def TOTAL_PHYMEM(self):
        return self._plat['TOTAL_PHYMEM']

    def NUM_CPUS(self):
        return self._plat['NUM_CPUS']

    def table(self):
        return self._plat

# instantiate a copy for the rest of GPI
Specs = SysSpecs()
