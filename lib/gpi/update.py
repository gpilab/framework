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

# Brief: Update utility, can be called directly from gpi or run as a separate
#        program.

import os
import re
import sys
import json
import time
import subprocess

from gpi import QtGui, QtWidgets, QtCore, Signal
from .widgets import TextBox
from .runnable import ExecRunnable, Runnable
from .sysspecs import Specs

# get the anaconda path to ensure that THIS installation is being updated
ANACONDA_PREFIX = '/opt/anaconda1anaconda2anaconda3' # ANACONDA
if ANACONDA_PREFIX == '/opt/'+'anaconda1anaconda2anaconda3':
    # get the path from the user env
    if Specs.inWindows():
        ANACONDA_PREFIX = os.path.dirname(subprocess.check_output('where conda', shell=True).decode('latin1').strip())
    else:
        ANACONDA_PREFIX = os.path.dirname(subprocess.check_output('which conda', shell=True).decode('latin1').strip())
    ANACONDA_PREFIX = os.path.dirname(ANACONDA_PREFIX) # strip off the 'bin'

class JSONStreamLoads(object):
    ''' Load multiple json objects from string.
    Returns loaded objects in a list.
    '''

    def __init__(self, in_str, linefeed=True):

        if type(in_str) == str:
            self._buffer = in_str
        else:
            raise TypeError("JSONStreamLoads(): input must be of type \'str\'.")

        self._load = self.loadAll()

    def load(self):
        return self._load

    def loadAll(self):
        return json.loads(self._buffer)


# use conda to update to the latest package
class CondaUpdater(QtCore.QObject):
    '''Handles the underlying communication with the 'conda' program.
    '''

    pdone = Signal(int)
    message = Signal(str)
    failed = Signal(str)
    getStatus_done = Signal()
    updateAllPkgs_done = Signal()

    def __init__(self, conda_prefix=ANACONDA_PREFIX, dry_run=False):
        super().__init__()
        self._dry_run = dry_run
        self._conda_prefix = conda_prefix
        self._packages = ['gpi', 'gpi_core']
        # DDB - No docs for now on c-f, restore later
        # self._packages = ['gpi', 'gpi_core', 'gpi-docs']

        self._packages_for_installation = []
        self._packages_for_update = []

        self._current_versions = {}
        self._latest_versions = {}


    def _status_pdone(self, pct, cr=False):
        end = ''
        if pct == 100:
            end = '\n'
        msg = 'Searching for package updates: '+str(pct)+'%'
        print('\t'+msg+'\r', end=end)
        self.pdone.emit(pct)
        self.message.emit('Searching for package updates...')

    def getStatus(self):
        try:
            self._getStatus()
            self.getStatus_done.emit()
        except:
            self.failed.emit('Failed to fetch updates.')

    def _getStatus(self):

        self.checkConda()

        # total divisions are len(self._packages)*3
        pdone = 0
        divs = len(self._packages)*3 + 1
        step = int(100/divs)
        self._status_pdone(1)

        # Check for the current installed versions
        for pkg in self._packages:
            self._current_versions[pkg] = self.getInstalledPkgVersion(pkg)
            pdone += step
            self._status_pdone(pdone)

        # Check for the latest versions online
        for pkg in self._packages:
            if self._current_versions[pkg] is None:
                self._latest_versions[pkg] = self.updatePkg(pkg, dry_run=True, install=True)
            else:
                self._latest_versions[pkg] = self.updatePkg(pkg, dry_run=True)
            pdone += step
            self._status_pdone(pdone)

        # Sort targets into 'install' or 'update'
        for pkg in self._packages:
            # updates - if there is both an installed version and new version
            if (self._latest_versions[pkg] is not None) and \
                (self._current_versions[pkg] is not None):
                self._packages_for_update.append(pkg)
            # installs - if there is no installed version, the latest will be
            #            whatever is available.
            if (self._latest_versions[pkg] is not None) and \
                (self._current_versions[pkg] is None):
                self._packages_for_installation.append(pkg)
            pdone += step
            self._status_pdone(pdone)

        self._status_pdone(100)

    def __str__(self):
        msg = ''
        tab = '&nbsp;&nbsp;&nbsp;&nbsp;'

        # updates
        if len(self._packages_for_update):
            msg += 'The following packages will be updated:<br><br>'
            for pkg in self._packages_for_update:
                o = self._current_versions[pkg]
                n = self._latest_versions[pkg]
                msg += pkg + '<br>'
                msg += tab+str(o) + '&nbsp; &#10154; &nbsp;' + str(n) + '<br>'

        # installs
        if len(self._packages_for_installation):
            if msg != '':
                msg += '<br><br>'
            msg += 'The following packages will be installed:<br><br>'
            for pkg in self._packages_for_installation:
                n = self._latest_versions[pkg]
                msg += pkg + '<br>'
                msg += tab+str(n) + '<br>'

        if self.numberOfUpdates():
            msg += '<br><br>GPI will be <b>automatically restarted</b> after updating.' \
                 + '  Please make sure your networks are saved before proceeding.'

        if msg == '':
            msg = 'GPI is up to date.'

        return msg

    def statusMessage(self):
        return str(self)

    def checkConda(self):
        cmd_unix = 'conda --version >/dev/null 2>&1'
        cmd_win = 'conda --version > NUL' 
        try:
            if Specs.inWindows():
                subprocess.check_output(cmd_win, shell=True)
            else:
                subprocess.check_output(cmd_unix, shell=True)
        except subprocess.CalledProcessError as e:
            print('Failed to execute conda, aborting...')
            print(e.cmd, e.output)
            raise
        except:
            print('\'conda\' failed to execute, aborting...')
            print(cmd)
            raise

    def getInstalledPkgVersion(self, name):
        cmd = 'conda list --json'
        try:
            output = subprocess.check_output(cmd, shell=True).decode('utf8')
            conda = JSONStreamLoads(output).load()
            for pkg in conda:
                pkg_str = json.dumps(pkg)
                m = re.search(name+'-([0-9]+\.[0-9]+\.[0-9]+)-[^"]*', pkg_str)
                if m:
                    return m[1]
        except:
            print('Failed to retrieve installed package information on '+name+', skipping...')
            print(cmd)
            raise

    def _updateAllPkgs_pdone(self, pct, cr=False):
        end = ''
        if pct == 100:
            end = '\n'
        msg = 'Updating packages: '+str(pct)+'%'
        print('\t'+msg+'\r', end=end)
        self.pdone.emit(pct)

    def numberOfUpdates(self):
        return len(self._packages_for_installation) + len(self._packages_for_update)

    def updateAllPkgs(self):
        try:
            self._updateAllPkgs()
            self.updateAllPkgs_done.emit()
        except:
            self.failed.emit('Failed to install updates.')

    def _updateAllPkgs(self):
        if self._dry_run:
            self.message.emit('Package updates complete. Relaunching...')
            return

        # total divisions are the installation list plus the update list
        pdone = 0
        divs = self.numberOfUpdates() + 1
        step = int(100/divs)
        self._updateAllPkgs_pdone(1)

        tab = '&nbsp;&nbsp;&nbsp;&nbsp;'
        message_hdr = 'Updating packages...<br>'+tab

        # Install or update all the packages that have been determined.
        for pkg in self._packages_for_installation:
            # if there is no package (due to user changes) then install it
            self.updatePkg(pkg, install=True)
            pdone += step
            self._updateAllPkgs_pdone(pdone)
            self.message.emit(message_hdr+pkg)
        for pkg in self._packages_for_update:
            # if there is a latest version then update
            self.updatePkg(pkg)
            pdone += step
            self._updateAllPkgs_pdone(pdone)
            self.message.emit(message_hdr+pkg)

        self._updateAllPkgs_pdone(100)
        self.message.emit('Package updates complete. Relaunching...')

    def updatePkg(self, name, dry_run=False, install=False):
        # Updates to the latest package and returns the package string.
        #   -dry_run will just return the latest package string.
        #   -install will install the package if its not currently installed.

        conda_sub = 'update'
        if install: conda_sub = 'install'
        dry_cmd = ''
        if dry_run: dry_cmd = '--dry-run --no-deps'
        cmd = 'conda '+conda_sub+' '+name+' -y --json '+dry_cmd

        try:
            output = subprocess.check_output(cmd, shell=True).decode('utf8')
            if dry_run:
                conda = JSONStreamLoads(output).load()

                if conda['success']:
                    if 'message' in conda: # if we're up to date
                        return
                    for pkg in conda['actions']['LINK']:
                        pkg_str = pkg['dist_name']
                        if pkg_str.startswith(name):
                            m = re.search('-([0-9]+\.[0-9]+\.[0-9]+)-', pkg_str)
                            return m[1]
                else:
                    raise RuntimeError('conda returned a failure status.')
            else:
                m = re.search('\"success\": true', output)
                if m[0] is not None:
                    print("Successfully updated ",name)
                else:
                    print("Update unsuccessful, even though a newer package was found.")
                    print("This is likely due to a dependency problem. Please create an")
                    print("issue at https://github.com/conda-forge/gpi-feedstock ")
        except subprocess.CalledProcessError as e:
            print('Failed to update to new package. Please try again.')
            print('If the problem persists, create an issue at')
            print('https://github.com/conda-forge/gpi-feedstock')
            print(e.cmd, e.output)
            raise
        except:
            print('Failed to retrieve package update information.')
            print('This may be due to a network or package manager issue.')
            print('If the problem persists, create an issue at')
            print('https://github.com/conda-forge/gpi-feedstock')
            print(cmd)
            raise

class UpdateWindow(QtWidgets.QWidget):
    '''A simple UI to display the GPI update process as its happening.
    '''

    _startGetStatus = Signal()

    def __init__(self, dry_run=False):
        super().__init__()

        self._updater = CondaUpdater(dry_run=dry_run)
        self._updater.getStatus_done.connect(self.showStatus)
        self._updater.getStatus_done.connect(self.showOKorUpdateButton)
        self._updater.failed.connect(self.initFailureMode)
        self._updater.updateAllPkgs_done.connect(self.relaunchProc)

        style = '''
            QProgressBar {
                background-color: rgb(226,226,226);
                border: 1px solid rgb(222,222,222);
                border-radius: 2px;
                text-align: center;
            }

            QProgressBar::chunk {
                background-color: #0099FF;
                height: 15px;
                width: 1px;
            }
        '''
        self._pbar = QtWidgets.QProgressBar(self)
        self._pbar.setStyleSheet(style)
        self._updater.pdone.connect(self.pdone)

        self._txtbox = TextBox('')
        self._txtbox.wdg.setTextFormat(QtCore.Qt.RichText)
        self._txtbox.set_wordwrap(True)
        self._txtbox.set_openExternalLinks(True)
        self._updater.message.connect(self._txtbox.set_val)
        self._txtbox.set_val('Checking for updates...')

        self._okButton = QtWidgets.QPushButton("OK")
        self._okButton.setVisible(False)
        self._cancelButton = QtWidgets.QPushButton("Cancel")
        self._cancelButton.clicked.connect(self.close)

        hbox = QtWidgets.QHBoxLayout()
        hbox.addStretch(1)
        hbox.addWidget(self._okButton)
        hbox.addWidget(self._cancelButton)

        vbox = QtWidgets.QVBoxLayout()
        vbox.addWidget(self._txtbox, 1)
        vbox.addWidget(self._pbar)
        vbox.addLayout(hbox)

        self.setLayout(vbox)

        self.setGeometry(300, 300, 400, 350)
        self.setWindowTitle('GPI Update')
        self.show()
        self.raise_()

        ExecRunnable(Runnable(self._updater.getStatus))

    def installUpdates(self):
        self._okButton.setVisible(False)
        ExecRunnable(Runnable(self._updater.updateAllPkgs))

    def pdone(self, pct):
        self._pbar.setValue(pct)
        if pct < 100:
            self._pbar.setVisible(True)
        else:
            self._pbar.setVisible(False)
            self._pbar.setValue(0)

    def showStatus(self):
        self._txtbox.set_val(self._updater.statusMessage())

    def initFailureMode(self, msg):
        self._pbar.setVisible(False)
        self._txtbox.set_val(msg)
        self._okButton.setVisible(False)
        self._cancelButton.setText('Close')

    def showOKorUpdateButton(self):
        if self._updater.numberOfUpdates():
            self._okButton.setText('Update && Relaunch')
            self._okButton.setVisible(True)
            self._okButton.clicked.connect(self.installUpdates)
        else:
            self._okButton.setVisible(False)
            self._cancelButton.setText('Close')

    def relaunchProc(self):
        try:
            self.update()
            QtWidgets.QApplication.processEvents() # allow gui to update
            time.sleep(5)
            args = sys.argv[:]
            args.insert(0, sys.executable)
            os.execv(sys.executable, args)
        except:
            self.initFailureMode('Failed to relaunch GPI.')

# For running as a separate application.
def update():
    app = QtWidgets.QApplication(sys.argv)
    win = UpdateWindow()
    sys.exit(app.exec_())
