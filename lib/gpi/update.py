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
import json
import subprocess

from gpi import QtGui, QtCore, Signal

# get the anaconda path to ensure that THIS installation is being updated
ANACONDA_PREFIX = '/opt/anaconda1anaconda2anaconda3' # ANACONDA
if ANACONDA_PREFIX == '/opt/'+''.join(['anaconda'+str(i) for i in range(1,4)]):
    # get the path from the user env
    ANACONDA_PREFIX = os.path.dirname(subprocess.check_output('which conda', shell=True).decode('latin1').strip())

# Load multiple json objects from string.
# Returns loaded objects in a list.
class JSONStreamLoads(object):

    def __init__(self, in_str, linefeed=True):

        if type(in_str) == str:
            self._buffer = in_str
        else:
            raise TypeError("JSONStreamLoads(): input must be of type \'str\'.")

        if linefeed:
            self._load = self.loadsByLine()
        else:
            self._load = self.loadsByCharacter()

    def objects(self):
        return self._load

    def loadsByLine(self):
        out = []
        buf = ''
        for l in self._buffer.splitlines():
            buf += l.strip().strip('\0')
            try:
                out.append(json.loads(buf))
                buf = ''
            except:
                pass
        return out

    def loadsByCharacter(self):
        out = []
        buf = ''
        for l in self._buffer:
            buf += l
            try:
                out.append(json.loads(buf.strip().strip('\0')))
                buf = ''
            except:
                pass
        return out

class UpdateWindow(QtGui.QWidget):
    
    def __init__(self):
        super().__init__()

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

class CondaUpdater(object):
    # use conda to update to the latest package

    def __init__(self, conda_prefix=ANACONDA_PREFIX):
        self._conda_prefix = conda_prefix
        self._channel = 'nckz'
        self._packages = ['gpi', 'gpi-core-nodes', 'gpi-docs']

        self.checkConda()

        # Check for the current installed versions
        self._current_versions = {}
        for pkg in self._packages:
            self._current_versions[pkg] = self.getInstalledPkgVersion(pkg)

        # Check for the latest versions online
        self._latest_versions = {}
        for pkg in self._packages:
            if self._current_versions[pkg] is None:
                self._latest_versions[pkg] = self.updatePkg(pkg, self._channel, dry_run=True, install=True)
            else:
                self._latest_versions[pkg] = self.updatePkg(pkg, self._channel, dry_run=True)

    def __str__(self):
        msg = ''

        # updates
        if len([ pkg for pkg in self._packages \
                if (self._latest_versions[pkg] is not None) and \
                (self._current_versions[pkg] is not None) ]):
            msg += 'The following packages will be updated:\n'
            for pkg in self._packages:
                o = self._current_versions[pkg]
                n = self._latest_versions[pkg]
                msg += '\t'+str(o) + ' => ' + str(n) + '\n'

        # installs
        if len([ pkg for pkg in self._packages \
                if (self._latest_versions[pkg] is not None) and \
                (self._current_versions[pkg] is None) ]):
            msg += 'The following packages will be installed:\n'
            for pkg in self._packages:
                n = self._latest_versions[pkg]
                msg += '\t'+str(n) + '\n'

        if msg == '':
            msg = 'GPI is totes up to date.'

        return msg

    def checkConda(self):
        cmd = self._conda_prefix+'/conda --version >/dev/null 2>&1'
        try:
            subprocess.check_output(cmd, shell=True)
        except subprocess.CalledProcessError as e:
            print('Failed to execute conda, aborting...')
            print(e.cmd, e.output)
            raise
        except:
            print('\'conda\' failed to execute, aborting...')
            print(cmd)
            raise

    def getInstalledPkgVersion(self, name):
        cmd = self._conda_prefix+'/conda list -f '+name+' --json'
        try:
            output = subprocess.check_output(cmd, shell=True).decode('utf8')
            conda = JSONStreamLoads(output).objects()[-1]
            return conda[-1]
        except:
            print('Failed to retrieve installed package information on '+name+', skipping...')
            print(cmd)

    def updateAllPkgs(self):
        # Install or update all the packages that have been determined.
        for pkg in self._packages:
            # if there is no package (due to user changes) then install it
            if self._current_versions[pkg] is None:
                self.updatePkg(pkg, self._channel, install=True)
            # if there is a latest version then update
            if self._latest_versions[pkg] is not None:
                self.updatePkg(pkg, self._channel)

    def updatePkg(self, name, channel, dry_run=False, install=False):
        # Updates to the latest package and returns the package string.
        #   -dry_run will just return the latest package string.
        #   -install will install the package if its not currently installed.

        conda_sub = 'update'
        if install: conda_sub = 'install'
        dry_cmd = ''
        if dry_run: dry_cmd = '--dry-run --no-deps'
        cmd = self._conda_prefix+'/conda '+conda_sub+' -c '+channel+' '+name+' -y --json '+dry_cmd

        try:
            output = subprocess.check_output(cmd, shell=True).decode('utf8')
            conda = JSONStreamLoads(output).objects()
            conda = conda[-1]

            if conda['success']:
                if 'message' in conda: # if we're up to date
                    return 
                for pkg in conda['actions']['LINK']:
                    if pkg.startswith(name):
                        return pkg.split()[0]
            else:
                raise RuntimeError('conda returned a failed fetch.')
        except subprocess.CalledProcessError as e:
            print('Failed to update to new package, aborting...')
            print(e.cmd, e.output)
            raise
        except:
            print('Failed to retrieve package update information, aborting...')
            print(cmd)
            raise

def update():

    updater = CondaUpdater()
    print(updater)
    updater.updateAllPkgs()

    return

    app = QtGui.QApplication(sys.argv)
    win = UpdateWindow()
    sys.exit(app.exec_())
