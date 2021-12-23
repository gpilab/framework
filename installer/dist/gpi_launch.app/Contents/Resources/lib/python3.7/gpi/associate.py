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

'''
File-node associations for data drag'n drop.
'''

import os
import sys

# gpi
from .catalog import Catalog, CatalogObj
from .logger import manager

# start logger for this module
log = manager.getLogger(__name__)

# bind<num> = ext, key or name, widget
# NOTE: currently this must be in alphabetical order to be correct in the
# .gpirc or --config display.
bind_1 = ('.csv', 'gpi_core.fileIO.ReadCSV', 'File Browser')
bind_2 = ('.data', 'gpi_core.fileIO.ReadPhilips', 'File Browser')
bind_3 = ('.hdf5', 'gpi_core.fileIO.ReadHDF5', 'File Browser')
bind_4 = ('.jpg', 'gpi_core.fileIO.ReadImage', 'File Browser')
bind_5 = ('.lab', 'gpi_core.fileIO.ReadPhilips', 'File Browser')
bind_6 = ('.list', 'gpi_core.fileIO.ReadPhilips', 'File Browser')
bind_7 = ('.mat', 'gpi_core.fileIO.ReadMatlab', 'File Browser')
bind_8 = ('.npy', 'gpi_core.fileIO.ReadNPY', 'File Browser')
bind_9 = ('.par', 'gpi_core.fileIO.ReadPhilips', 'File Browser')
bind_10 = ('.pickle', 'gpi_core.fileIO.ReadPickled', 'File Browser')
bind_11 = ('.png', 'gpi_core.fileIO.ReadImage', 'File Browser')
bind_12 = ('.raw', 'gpi_core.fileIO.ReadRaw', 'File Browser')
bind_13 = ('.rec', 'gpi_core.fileIO.ReadPhilips', 'File Browser')
bind_14 = ('.sin', 'gpi_core.fileIO.ReadPhilips', 'File Browser')
bind_15 = ('.xml', 'gpi_core.fileIO.ReadPhilips', 'File Browser')


# make a catalog of associations
Bindings = Catalog()

def isGPIAssociatedFile(fullpath):
    '''Determine if the path exists, isfile, and valid ext.
    '''
    if os.path.isfile(fullpath):
        bpath, ext = os.path.splitext(fullpath)
        if str(ext).lower() in list(Bindings.keys()):
            return True
    return False

def isGPIAssociatedExt(ext):
    '''Determine if the path exists, isfile, and valid ext.
    '''
    if str(ext).lower() in list(Bindings.keys()):
        return True
    return False

class BindCatalogItem(CatalogObj):
    '''Holds all necessary things for file associations.
    '''

    def __init__(self, bind):
        self.ext = bind[0].lower() # all extensions should be case-insensitive
        self.node = bind[1]
        self.wdg = bind[2]

    def key(self):
        # its most likely that this will be looked up by extension
        return self.ext.lower()

    def merge(self, e):
        # allow defaults to be overwritten
        log.info('\'' + str(self.key()) + '\' extension for \'' +str(e.node) + '\' is already assigned to \'' + str(self.node) + '\', replacing.')
        self.ext = e.ext
        self.node = e.node
        self.wdg = e.wdg

    def asTuple(self):
        return (self.ext, self.node, self.wdg)

    def __str__(self):
        return str(self.ext) + ' ' + str(self.node) + ' ' + str(self.wdg)

# load the default bindings
for b in [ x for x in dir(sys.modules[__name__]) if x.startswith('bind_') ]:
    if hasattr(sys.modules[__name__], b):
        item = BindCatalogItem(getattr(sys.modules[__name__], b))
        Bindings.append(item)

#print Bindings
