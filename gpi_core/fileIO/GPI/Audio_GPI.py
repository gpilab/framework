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


# Author: Nick Zwart
# Date: 2013 Sep 17

import tempfile
import scipy.io.wavfile as spio
import numpy as np
import os
import time
from gpi import QtMultimedia

import gpi


class ExternalNode(gpi.NodeAPI):

    """Converts numpy arrays into .wav format for reproduction on the audio system,
       writes to /tmp directory, then plays .wav file.

    INPUT:
    1 dimensional real-valued array to be converted to audio.
    Data values are normalized internally.

    WIDGETS:
    Sample Rate (samp/sec) - D/A dwell time of waveform
    Loops - enter a number > 1 to play multiple times 
    Play - write waveform and play audio

    KNOWN ISSUES:
    None
"""

    def initUI(self):
        # Widgets
        self.addWidget('TextBox', 'Audio Info')
        self.addWidget('SpinBox', 'Sample Rate (samp/sec)', min=1, val=1000)
        self.addWidget('SpinBox', 'Loops', min=1, val=1)
        self.addWidget('PushButton', 'Play')

        self.addWidget(
            'SaveFileBrowser', 'File Browser', button_title='Browse',
            caption='Save File (*.wav)', filter='Wav (*.wav)')
        self.addWidget('PushButton', 'Write Now', button_title='Write Right Now', toggle=False)


        # IO Ports
        self.addInPort('wave source', 'NPYarray', ndim=1)

        self._tmpfile = tempfile.mkstemp(
            prefix='gpi_', suffix='.wav', dir='/tmp/', text=False)[1]
        self.URI = gpi.TranslateFileURI

    def validate(self):

        fname = self.URI(self.getVal('File Browser'))
        self.setDetailLabel(fname)

        return 0

    def compute(self):

        arr = self.getData('wave source')
        rate = self.getVal('Sample Rate (samp/sec)')
        loops = self.getVal('Loops')
        
        # make sure the wave is maximized for int16 dyn-range
        arr = (arr.astype(np.float32) / np.abs(arr)
               .max() * (pow(2, 15) - 1)).astype(np.int16)

        spio.write(self._tmpfile, rate, np.tile(arr,loops))

        try:
            s = QtMultimedia.QSound('')
            self.setAttr('Audio Info', val='Sound module is available.')
            dur = len(arr)*loops / rate
            s.play(self._tmpfile)
        except:
            self.setAttr('Audio Info', val='Sound module failed to load!\n Please visit www.github.com/gpilab/core-nodes/issues for help.')

        time.sleep(.01)
        os.remove(self._tmpfile)
        if self.getVal('Write Now') or ('File Browser' in self.widgetEvents()):

            fname = self.URI(self.getVal('File Browser'))
            if not fname.endswith('.wav'):
                fname += '.wav'

            spio.write(fname,rate,arr)

        return 0

    def execType(self):
        '''Could be GPI_THREAD, GPI_PROCESS, GPI_APPLOOP'''
        return gpi.GPI_APPLOOP
