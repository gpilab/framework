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

''' A class for getting relevant system specifications.  These can be used to
display system information in the status bar, convey relative performance info
in networks, etc... '''


import psutil
import platform
# import resource

# gpi
from .defines import GetHumanReadable_bytes
from .logger import manager

# start logger for this module
log = manager.getLogger(__name__)


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

        # not sure what the default behavior is for psutil
        try:
            self._plat['TOTAL_PHYMEM'] = psutil.virtual_memory().total
        except:
            log.warn("Couldn't get TOTAL_PHYMEM from psutil.")
            self._plat['TOTAL_PHYMEM'] = 0

        self._plat['TOTAL_PHYMEM_STR'] = GetHumanReadable_bytes(self._plat['TOTAL_PHYMEM'])

        try:
            self._plat['NUM_CPUS'] = psutil.cpu_count()
        except:
            log.warn("Couldn't get NUM_CPUS from psutil.")
            self._plat['NUM_CPUS'] = 0

        # process interface for THIS process
        self._proc = psutil.Process()
        if not self._inWindows:
            import resource
            self._rlimit_nofile = resource.getrlimit(resource.RLIMIT_NOFILE)[0]
        else:
            self._rlimit_nofile = 10000
        self.findAndSetMaxOpenFilesLimit()
        log.info("open file limit: "+str(self.numOpenFilesLimit()))

    # OS resource limits
    def numOpenFiles(self):
        return self._proc.num_fds()

    def numOpenFilesLimit(self):
        # get the soft limit
        return self._rlimit_nofile

    # determine if the number of open files is within the limit thresh
    def openFileLimitThresh(self):
        return self.numOpenFiles() >= (self.numOpenFilesLimit() - 10)

    def findAndSetMaxOpenFilesLimit(self):
        maxFound = False
        if not self._inWindows:
            import resource
            lim = resource.getrlimit(resource.RLIMIT_NOFILE)[0]
            hard_lim = resource.getrlimit(resource.RLIMIT_NOFILE)[1]
            # if the hard limit is infinite (unlimited resources) cap it at 10000
            if hard_lim == resource.RLIM_INFINITY:
                lim = 10000
                hard_lim = 10000
        else:
            lim = 10000
            hard_lim = 10000

        while (not self._inWindows) and (not maxFound):
            try:
                lim += 10
                resource.setrlimit(resource.RLIMIT_NOFILE, (lim, hard_lim))
                self._rlimit_nofile = lim
            except:
                maxFound = True

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
