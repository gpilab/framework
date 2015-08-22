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

import os
import hashlib
import numpy as np

# gpi
from .defines import GPI_SHDM_PATH
from .logger import manager
from .sysspecs import Specs

# start logger for this module
log = manager.getLogger(__name__)


class FileHandle(object):
    '''Hold a filename as a reference to an actual file.  If THIS object
    looses its reference then make sure the associated file is also deleted.
    By default this file will be created in the GPI tmp directory and will be
    named after the node it is called in.

    path: /tmp (default GPI tmp dir)
    filename: additional to the nodeid
    suffix: additional to the nodeid
    nodeid: node's location in memory (id())
    '''
    def __init__(self, path=None, filename=None, suffix=None, nodeid=None):

        ## build the filepath one step at a time

        self._fullpath = ''
        if path:
            self._fullpath = str(path)
        else:
            self._fullpath = GPI_SHDM_PATH

        if nodeid:
            self._fullpath += str(nodeid)

        if filename:
            self._fullpath += str(filename)

        if suffix:
            self._fullpath += str(suffix)

        if os.path.exists(self._fullpath):
            log.warn('The path: \'' + self._fullpath + '\' already exists, continuing...')

    def __str__(self):
        return self._fullpath

    def __del__(self):
        self.clear()

    def clear(self):
        if os.path.isfile(self._fullpath):
            os.remove(self._fullpath)


