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
#    MAKES NO WARRANTY AND HAS NOR LIABILITY ARISING FROM ANY USE OF THE
#    SOFTWARE IN ANY HIGH RISK OR STRICT LIABILITY ACTIVITIES.

# Brief: Update utility, can be called directly from gpi or run as a separate 
#        program.

import os
import sys
import subprocess

# Check for Anaconda PREFIX, or assume that THIS file location is the CWD.
GPI_PREFIX = '/opt/anaconda1anaconda2anaconda3' # ANACONDA
if GPI_PREFIX == '/opt/'+''.join(['anaconda'+str(i) for i in range(1,4)]):
    GPI_PREFIX, _ = os.path.split(os.path.dirname(os.path.realpath(__file__)))

GPI_LIB_DIR = GPI_PREFIX
if not GPI_PREFIX.endswith('lib'):
    GPI_LIB_DIR = os.path.join(GPI_PREFIX, 'lib')
if GPI_LIB_DIR not in sys.path:
    sys.path.insert(0, GPI_LIB_DIR)

from gpi import QtGui, QtCore, Signal


class UpdateWindow(QtGui.QWidget):
    
    def __init__(self):
        super().__init__()

        if not condaIsAvailable():
            return

        okButton = QtGui.QPushButton("OK")
        cancelButton = QtGui.QPushButton("Cancel")

        hbox = QtGui.QHBoxLayout()
        hbox.addStretch(1)
        hbox.addWidget(okButton)
        hbox.addWidget(cancelButton)

        vbox = QtGui.QVBoxLayout()
        vbox.addStretch(1)
        vbox.addLayout(hbox)

        self.setLayout(vbox)

        self.setGeometry(300, 300, 250, 150)
        self.setWindowTitle('GPI Update')
        self.show()
        self.raise_()

    def condaIsAvailable(self):
        try:
            subprocess.check_call('conda --version')
            return True
        except:
            print('\'conda\' failed to execute, aborting...')
        return False

    def getLatestPkgVersion(self, name, channel):
        try:
            output = subprocess.check_output('conda search -c '+channel+' -f '+name+' -o --json', shell=True)
        except subprocess.CalledProcessError as e:
            print(cmd, e.output)
            sys.exit(e.returncode)

        conda = json.loads(output)
        print(conda)

    def getLatestGPIVersion(self):
        pass

def update():
    app = QtGui.QApplication(sys.argv)
    win = UpdateWindow()
    sys.exit(app.exec_())

if __name__ == '__main__':
    update()
