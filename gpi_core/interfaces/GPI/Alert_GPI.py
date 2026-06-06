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
# Date: 2013mar03

import os
import gpi


class ExternalNode(gpi.NodeAPI):
    """Warn the user when this node has received data.  Either thru terminal
    bell or OSX voice synth.  The voice settings can be changed in the System Preferences.
    """

    def initUI(self):

        # test for the existence of say
        try:
            if not os.system('/usr/bin/say \"\"'):
                self._say = True
            else:
                self._say = False
        except:
            self._say = False

        # personalize it
        try:
            name = str(os.getlogin()).capitalize()+', y'
        except:
            name = 'Y'

        # Widgets
        self.addWidget('PushButton', 'Voice', toggle=True, val=False, visible=self._say)
        self.addWidget('StringBox', 'Text to Voice', val=name+"our G.P.I. network has reached the Alert node.", visible=self._say)
        self.addWidget('PushButton', 'Terminal Bell', toggle=True, val=False)
        self.addWidget('SpinBox', 'Iterations', val=1, min=1)

        # IO Ports
        self.addInPort('any', 'PASS', obligation=gpi.OPTIONAL)


    def compute(self):
        '''This is where the main algorithm should be implemented.
        '''

        if self.getVal('Voice'):
            for i in range(self.getVal('Iterations')):
                try:
                    os.system('/usr/bin/say \"'+self.getVal('Text to Voice')+'\"')
                except:
                    log.error('Failing to execute \'say\' command.')

        if self.getVal('Terminal Bell'):
            for i in range(self.getVal('Iterations')):
                print('\a')

        return 0
