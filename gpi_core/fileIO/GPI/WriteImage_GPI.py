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


# Author: Dallas Turley

import gpi
import numpy as np

class ExternalNode(gpi.NodeAPI):
    """Uses the numpy PIL interface for writing arrays. File types are specified in the bottom of the file browser
    Currently lossless TIFF and compressed JPEG are fully supported.

    INPUT - Image array to write. This node is designed to write to file the output of the ImageDisplay node.
        Image can be MxNx3 or MxNx4
        If the shape is MxNx3, the array will store the RGB bands as the last dimension
        If the shape is MxNx4, the array will store RGBA as the last dimension

    WIDGETS:
    File Browser - button to launch file browser, and typein widget, to give pathname for output file
      ***NOTE: If no extension (filetype) is specified, the input will be written as a .tiff file.
      Automatically appending the filetype based on the chosen file filter (in the Save File dialog box)
      has yet to be implemented. 
    Write Mode - write at any event, or write only with new filename
    Write Now - write right now
    """
    
    def execType(self):
        return gpi.GPI_THREAD

    def initUI(self):
       # Widgets
        self.addWidget(
            'SaveFileBrowser', 'File Browser', button_title='Browse',
            caption='Save Image', filter='tiff (*.tiff);;jpg (*.jpg);;all (*)')
        self.addWidget('PushButton', 'Write Mode', button_title='Write on New Filename', toggle=True)
        self.addWidget('PushButton', 'Write Now', button_title='Write Right Now', toggle=False)

        # IO Ports
        self.addInPort('in', 'NPYarray', dtype=np.uint8, ndim=3)

        # store for later use
        self.URI = gpi.TranslateFileURI

    def validate(self):
        fname = self.URI(self.getVal('File Browser'))
        self.setDetailLabel(fname)

        if self.getVal('Write Mode'):
            self.setAttr('Write Mode', button_title="Write on Every Event")
        else:
            self.setAttr('Write Mode', button_title="Write on New Filename")

        data = self.getData('in')
        if data.ndim != 3:
            self.log.warn("data must be 3D (RGB or RGBA in last dim)")
            return 1
        if data.shape[-1] not in (3,4):
            self.log.warn("The last dimension for 3D data must be 3 or 4")
            return 1

        return 0

    def compute(self):

        import numpy as np
        from PIL import Image

        data = self.getData('in').copy()

        if data.ndim == 3:
            data[...,(0,2)] = data[...,(2,0)]

        #Note: scipy.misc.imsave() uses the Python Imaging Library (PIL) which automatically 
        #chooses the format in which to save files based on the file extension (.jpg, .tif, etc)

        if self.getVal('Write Mode') or self.getVal('Write Now') or ('File Browser' in self.widgetEvents()):

            fname = self.URI(self.getVal('File Browser'))
            if fname == '':
                return 0

            #the following are valid, supported image filetype extensions
            ext_list = ('.jpg', '.tiff')
            if (fname.lower().endswith(ext_list)):
                pass
            else:
                fname += '.tiff'

            img = Image.fromarray(data)
            img.save(fname)
            self.log.info("File Written : " +str(fname))

        return(0)
