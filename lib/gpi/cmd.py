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

# Brief: Commandline option parsing.
#           -can initiate some simple commands

import sys
import logging
import optparse

# gpi
from .associate import isGPIAssociatedFile
from .defines import isGPIModFile, isGPINetworkFile
from gpi import VERSION
from . import logger
from .logger import manager
from .sysspecs import Specs

# start logger for this module
log = manager.getLogger(__name__)


class CmdParser(object):
    '''An object to parse input commandline args after the QApplication has
    done its own parsing.
    '''

    def __init__(self):
        '''Initialize all command-line parsed variables.
        '''
        self._argv = None
        self._options = None
        self._args = None

        # a place for string args option
        self._sargs = {}

        # no gui option
        self._nogui = False
        self._scriptMode = False

        # splash is on by default
        self._nosplash = False

        self._loadable_mods = []
        self._loadable_nets = []
        self._loadable_files = []  # associated files

        # tell the USAGE text that this is always 'gpi'
        self._parser = optparse.OptionParser(prog='gpi')

        # take in any filename for extension checking, then loading. 
        self._parser.add_option('--config', dest='dumpConfig', action='store_true', help='''GPI will read the User ENV and config file and dump the parsed info to stdout.''')
        self._parser.add_option('--log', dest='loglevel', action='store', choices=['debug', 'info', 'node', 'warn', 'error', 'critical'], help='''Change the output level of the logger: debug, info, node, warn, error, and critical''')
        self._parser.add_option('--nogui', dest='nogui', action='store_true', help='''causes GPI to run without a GUI for scripting.  Requires a network file.  The --script option is implied.''')
        self._parser.add_option('--script', dest='script', action='store_true', help='''causes GPI to terminate after the supplied network is finished executing.  Requires a network file.''')
        self._parser.add_option('-s', '--string', dest='string', action='append', type='string', default=[], help='''passes a string arg to a String-node by label.  Handles multiple args.  Syntax: -s <label1>:<string/path> -s <label2>:<string/path>.''')
        self._parser.add_option('--specs', dest='dumpSpecs', action='store_true', help='''GPI will create a platform specs file and exit.''')
        self._parser.add_option('--defines', dest='dumpDefines', action='store_true', help='''Show some internally used defines, such as temp directory paths.''')
        self._parser.add_option('--nosplash', dest='nosplash', action='store_true', help='''Skip the splash screen.''')

    def parse(self, argv):
        # keep a copy of what was parsed
        self._argv = list(argv)

        # options: processed args that use switches
        # args: leftover positional args
        self._options, self._args = self._parser.parse_args(self._argv)

        # check for loadable files
        self.checkArgsForFiles()

        # check and process string args
        self.storeStringNodeArgs()

        # make sure the user passes a network
        if self._options.nogui:
            if self.netCount():
                self._nogui = True
            else:
                log.error('the --nogui option was passed without a network, exiting.')
                sys.exit(1)

        # make sure the user passes a network
        if self._options.script:
            if self.netCount():
                self._scriptMode = True
            else:
                log.error('the --script option was passed without a network, exiting.')
                sys.exit(1)

        # set log level asap, don't wait for mainWindow to be set
        if self.logLevel():
            logger.manager.setLevel(self.logLevel())

        # run simple commands
        if self._options.dumpSpecs:
            self.dumpSpecs()

        if self._options.dumpDefines:
            self.dumpDefines()

        if self._options.dumpConfig:
            from .config import Config
            log.dialog('Config:\n'+str(Config))
            sys.exit(0)

        # splash
        self._nosplash = self._options.nosplash

    def dumpDefines(self):
        import gpi.defines
        msg = []
        for d in dir(gpi.defines):
            o = getattr(gpi.defines,d)
            if type(o) is str:
                if d.startswith('GPI'):
                    msg.append(d + ': ' + o + '\n')
        msg = sorted(msg)
        msg = '\n'+''.join(msg)
        log.dialog(msg)
        sys.exit(0)

    def dumpSpecs(self):
        with open('specs.txt', 'wb') as specsfile:
            specsfile.write('# GPI (v'+str(VERSION)+') system specifications file.\n')
            for k,v in list(Specs.table().items()):
                msg = k+': '+str(v) + '\n'
                specsfile.write(msg)

        log.dialog('Specs file written, exiting.')
        sys.exit(0)

    def logLevel(self):
        if self._options.loglevel == 'debug':
            return logging.DEBUG
        if self._options.loglevel == 'info':
            return logging.INFO
        if self._options.loglevel == 'node':
            return logger.GPINODE
        if self._options.loglevel == 'warn':
            return logging.WARNING
        if self._options.loglevel == 'error':
            return logging.ERROR
        if self._options.loglevel == 'critical':
            return logging.CRITICAL

    def noGUI(self):
        return self._nogui

    def scriptMode(self):
        return self._scriptMode

    def noSplash(self):
        return self._nosplash

    def mods(self):
        return self._loadable_mods

    def nets(self):
        return self._loadable_nets

    def files(self):
        return self._loadable_files

    def stringNodeArg(self, key):
        if key in self._sargs:
            return self._sargs[key]
        log.error('\''+str(key)+'\' not found in string args.')

    def stringNodeLabels(self):
        return list(self._sargs.keys())

    def storeStringNodeArgs(self):
        # merge any redundant labels with warnings
        for arg in self._options.string:
            lab, path = arg.split(':')
            if lab in self._sargs:
                log.warn('input string label for arg: \''+ str(arg) + '\' already exists, skipping.') 
            else:
                self._sargs[lab] = path

    def __str__(self):
        msg = ''
        msg += 'Unparsed: '+str(self._args) + '\n'
        msg += 'Parsed: '+str(self._options) + '\n'
        return msg

    def modCount(self):
        return len(self._loadable_mods)

    def netCount(self):
        return len(self._loadable_nets)

    def fileCount(self):
        return len(self._loadable_files)

    def stringNodeArgCount(self):
        return len(self._sargs)

    def pendingCount(self):
        return self.modCount() + self.netCount() + self.fileCount() + self.stringNodeArgCount()

    def checkArgsForFiles(self):

        for arg in self._args:

            if isGPIModFile(arg):
                self._loadable_mods.append(arg)

            elif isGPINetworkFile(arg):
                self._loadable_nets.append(arg)

            elif isGPIAssociatedFile(arg):
                self._loadable_files.append(arg)

Commands = CmdParser()
