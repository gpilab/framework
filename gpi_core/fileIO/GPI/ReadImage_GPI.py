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


import os, sys
import numpy as np
import gpi

class ExternalNode(gpi.NodeAPI):
    """Read images into GPI as numpy arrays. Many image file types are supported by PIL (Python Imaging Library)
    The file types specifically implemented in this node are PNG, JPEG, TIFF and BMP. PIL supports other image
    file types, but the node's ability to read these types into GPI are not guaranteed.
    For more information on supported file types, see
    http://www.pythonware.com/products/pil
    http://effbot.org/imagingbook/pil-index.htm

    OUTPUT: Numpy array read from image file.

    WIDGETS: I/O Info - Gives info on data file and type
    File Browser - button to launch file browser, and typein widget if the pathway is known
    Gray Scale - button to flatten the last dimension of jpg and png images.
        If toggle is on, output is a grey-scale float32 array with the same dimensions as the original image
        If toggle is off, output is a uint8 array with the last dimension BGRA
    """
    def execType(self):
        return gpi.GPI_PROCESS #this is safest

    def initUI(self):
        self.addWidget('TextBox', 'I/O Info:')
        self.addWidget('OpenFileBrowser', 'File Browser', button_title='Browse', caption='Open File', filter='png (*.png);;jpg (*.jpg);;tiff (*.tiff);;all (*)')
        self.addWidget('PushButton', 'Gray Scale', toggle=True)
        self.addWidget('PushButton', 'Swap Colors (RGB -> BGR)', toggle=True, val=0, button_title='RGB')

        self.addOutPort(title='out', type='NPYarray')

        self.URI = gpi.TranslateFileURI

    def validate(self) :
        if self.getVal('Swap Colors (RGB -> BGR)') :
            self.setAttr('Swap Colors (RGB -> BGR)', button_title="BGR")
        else :
            self.setAttr('Swap Colors (RGB -> BGR)', button_title="RGB")

        fname = self.URI(self.getVal('File Browser'))
        self.setDetailLabel(fname)

        return 0

    def compute(self):
        import numpy as np
        import time
        from PIL import Image

        flat = self.getVal('Gray Scale')
        swap = self.getVal('Swap Colors (RGB -> BGR)')

        #start file browser
        fname = self.URI(self.getVal('File Browser'))

        # ignore this case
        if fname == '':
            return 0

        #check that the path actually exists
        if not os.path.exists(fname):
            self.log.warn("Path does not exist: "+str(fname))
            return 0

        #show some file stats
        fstats = os.stat(fname)
        #creation
        ctime = time.strftime('%d/%m/20%y', time.localtime(fstats.st_ctime))
        # mod time
        mtime = time.strftime('%d/%m/20%y', time.localtime(fstats.st_mtime))
        # access time
        atime = time.strftime('%d/%m/20%y', time.localtime(fstats.st_atime))
        # filesize
        fsize = fstats.st_size
        # user id
        uid = fstats.st_uid
        # group id
        gid = fstats.st_gid

        # read the data
        img = Image.open(fname)
        if flat:
            img = img.convert('L')
        elif img.mode == 'RGB' :
            img = img.convert('RGBA')

        imgarr = np.array(img)

        if swap and imgarr.shape[-1] > 1 :
            red = imgarr[:,:,2]
            blu = imgarr[:,:,1]
            grn = imgarr[:,:,0]
            if imgarr.shape[-1] == 4 :
                alf = imgarr[:,:,3]
            else :
                alf = 255. * np.ones((blu.shape),dtype=np.uint8)

            out = np.zeros(imgarr.shape,dtype=imgarr.dtype)
            out[:,:,0] = red
            out[:,:,1] = blu
            out[:,:,2] = grn
            out[:,:,3] = alf
        else :
            out = imgarr

        d1 = list(out.shape)
        info = "created: "+str(ctime)+"\n" \
               "accessed: "+str(atime)+"\n" \
               "modified: "+str(mtime)+"\n" \
               "UID: "+str(uid)+"\n" \
               "GID: "+str(gid)+"\n" \
               "file size (bytes): "+str(fsize)+"\n" \
               "dimensions: "+str(d1)+"\n" \
               "type: "+str(out.dtype)+"\n" \
               "output color band: RGBA"+"\n"
        self.setAttr('I/O Info:', val=info)

        self.setData('out', out)

        return 0

