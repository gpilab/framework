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

# Brief: A module for configuring gpi thru the ~/.gpirc file
import os
import traceback
import configparser
import glob

# gpi
from .associate import Bindings, BindCatalogItem
from gpi import VERSION
from .logger import manager
from .sysspecs import Specs

# start logger for this module
log = manager.getLogger(__name__)

# for windows
if Specs.inWindows():
    GPIRC_FILENAME = 'gpi.conf'
else:
    GPIRC_FILENAME = '.gpirc'

### ENVIRONMENT VARIABLES
if Specs.inWindows():
    USER_HOME = os.path.expanduser('~')
else:
    USER_HOME = os.environ['HOME']

USER_LIB_BASE_PATH_DEFAULT = os.path.join(USER_HOME, 'gpi')
if Specs.inWindows():
    userNameKey = 'USERNAME'
else:
    userNameKey = 'USER'
USER_LIB_PATH_DEFAULT = os.path.join(USER_LIB_BASE_PATH_DEFAULT, os.environ.get(userNameKey, 'UserNodes'))

ANACONDA_PREFIX='/opt/anaconda1anaconda2anaconda3' # is this needed?
GPI_PREFIX = os.path.dirname(os.path.realpath(__file__))
SP_PREFIX = os.path.dirname(GPI_PREFIX)

GPI_NET_PATH_DEFAULT = USER_HOME
GPI_DATA_PATH_DEFAULT = USER_HOME
GPI_FOLLOW_CWD = True

# Build the distro default to include any gpi_<name> packages in site-packages
GPI_SP_NODE_LIBS = glob.glob(os.path.join(SP_PREFIX,'gpi_*'))
GPI_LIBRARY_PATH_DEFAULT = [USER_LIB_BASE_PATH_DEFAULT,SP_PREFIX]


###############################################################################

class ConfigManager(object):
    '''An object that can load and generate the gpi config file.
    The gpi config file can potentially hold configs for:
        library paths,
        network dir path,
        data dir path,
        plugin paths,
        filetype-node associations,
        canvas window start size,
        UI style
    '''

    def __init__(self):

        # general
        self._g_import_check = True

        # root dirs for organizing gpi related files.
        self._c_networkDir = GPI_NET_PATH_DEFAULT
        self._c_dataDir = GPI_DATA_PATH_DEFAULT
        self._c_configFileName = os.path.join(os.path.expanduser('~'), GPIRC_FILENAME)

        # all the fix'ns for an initial lib
        self._c_userLibraryBasePath = os.path.expanduser(USER_LIB_BASE_PATH_DEFAULT)
        self._c_userLibraryPath = os.path.expanduser(USER_LIB_PATH_DEFAULT)
        self._c_userLibraryPath_def = os.path.join(self._c_userLibraryPath, 'default')
        self._c_userLibraryPath_def_GPI = os.path.join(self._c_userLibraryPath_def, 'GPI')
        self._c_userLibraryPath_init = os.path.join(self._c_userLibraryPath, '__init__.py')
        self._c_userLibraryPath_def_init = os.path.join(self._c_userLibraryPath_def, '__init__.py')
        self._c_userLibraryPath_def_node = os.path.join(self._c_userLibraryPath_def_GPI, 'MyNode_GPI.py')

        # env vars
        self._c_gpi_lib_path = list(GPI_LIBRARY_PATH_DEFAULT)
        self._c_gpi_follow_cwd = GPI_FOLLOW_CWD

        self._new_node_template_file = os.path.join(GPI_PREFIX, 'nodeTemplate.py')

        # make vars
        self._make_libs = []
        self._make_lib_dirs = []
        self._make_inc_dirs = []
        self._make_cflags = []

        # try to read the config file
        try:
            self.loadConfigFile()
        except:
            log.error("The config file failed to load, using defaults. "+str(traceback.format_exc()))

    def __str__(self):

        msg = ''

        # general
        msg += 'GENERAL:\n'
        for o in dir(self):
            if o.startswith('_g_'):
                msg += str(o) + ': ' + str(getattr(self, o)) + '\n'

        # path
        msg += 'PATH:\n'
        for o in dir(self):
            if o.startswith('_c_'):
                msg += str(o) + ': ' + str(getattr(self, o)) + '\n'

        # even though bindings are external print them here for convenience
        msg += 'ASSOCIATIONS:\n'
        for v in sorted([str(x) for x in list(Bindings.values())]):
            msg += str(v) + '\n'

        # makefile modifications
        msg += 'MAKE:\n'
        for o in dir(self):
            if o.startswith('_make_'):
                msg += str(o) + ': ' + str(getattr(self, o)) + '\n'
        return msg

    @property
    def IMPORT_CHECK(self):
        return self._g_import_check

    @property
    def GPI_NET_PATH(self):
        return self._c_networkDir

    @property
    def GPI_DATA_PATH(self):
        return self._c_dataDir

    @property
    def GPI_FOLLOW_CWD(self):
        return self._c_gpi_follow_cwd

    @property
    def GPI_LIBRARY_PATH(self):
        return self._c_gpi_lib_path

    @property
    def GPI_NEW_NODE_TEMPLATE_FILE(self):
        return self._new_node_template_file

    @property
    def MAKE_LIBS(self):
        return self._make_libs

    @property
    def MAKE_LIB_DIRS(self):
        return self._make_lib_dirs

    @property
    def MAKE_INC_DIRS(self):
        return self._make_inc_dirs

    @property
    def MAKE_CFLAGS(self):
        return self._make_cflags

    def generateUserLib(self):

        self.initLibDir(self._c_userLibraryBasePath)
        self.initLibDir(self._c_userLibraryPath)
        self.initLibDir(self._c_userLibraryPath_def)
        self.initLibDir(self._c_userLibraryPath_def_GPI)

        self.initLibFile(self._c_userLibraryPath_init)
        self.initLibFile(self._c_userLibraryPath_def_init)

        if os.path.exists(self._c_userLibraryPath_def_node):
            log.dialog('The user library example node: '+str(self._c_userLibraryPath_def_node) + ' already exists, skipping.')
        else:
            with open(self._c_userLibraryPath_def_node, 'w') as initfile:
                log.dialog('Writing the example node: '+str(self._c_userLibraryPath_def_node) + '')
                initfile.write(self.exampleNodeCode())

    def exampleNodeCode(self):

        header = '# GPI (v'+str(VERSION)+') auto-generated library file.\n#\n'
        filename = '# FILE: '+str(self._c_userLibraryPath_def_node)+'\n#\n'

        buf = '''# For node API examples (i.e. widgets and ports) look at the
# core.interfaces.Template node.

import gpi

class ExternalNode(gpi.NodeAPI):
    \'\'\'About text goes here...
    \'\'\'

    def initUI(self):
        # Widgets
        self.addWidget('PushButton', 'MyPushButton', toggle=True)

        # IO Ports
        self.addInPort('in1', 'NPYarray')
        self.addOutPort('out1', 'NPYarray')

        return 0

    def compute(self):

        data = self.getData('in1')

        # algorithm code...

        self.setData('out1', data)

        return 0'''

        return header+filename+buf


    def initLibDir(self, path):
        if os.path.exists(path):
            log.dialog('The user library path: '+str(path) + ' already exists, skipping.')
        else:
            log.dialog('Writing the user library path: '+str(path) + '')
            os.mkdir(path)

    def initLibFile(self, path):
        if os.path.exists(path):
            log.dialog('The user library file: '+str(path) + ' already exists, skipping.')
        else:
            log.dialog('Writing the user library file: '+str(path) + '')
            with open(path, 'w') as initfile:
                initfile.write('# GPI (v'+str(VERSION)+') auto-generated library file.\n')



    def generateConfigFile(self, overwrite=False):

        # check for existing config file
        # -force user to remove, its safer
        if self.configFileExists() and not overwrite:
            log.dialog('Config file: '+str(self.configFilePath()) + ' already exists, skipping.')
            return

        with open(self._c_configFileName, 'w') as configfile:

            # Header
            configfile.write('# GPI (v'+str(VERSION)+') configuration file.\n')
            configfile.write('# Uncomment an option to activate it.\n')

            config = configparser.RawConfigParser()

            # Makefile mods
            configfile.write('\n[GENERAL]\n')
            configfile.write('# Add nodes to the library only if they \'import\'.\n')
            configfile.write('# GPI loads faster if this check is disabled.\n')
            configfile.write('#IMPORT_CHECK = False\n')

            # PATH Section
            configfile.write('\n[PATH]\n')
            configfile.write('# Add library paths for GPI nodes.\n')
            configfile.write('# Multiple paths are delimited with a \':\'.\n')
            configfile.write('#     (e.g. [default] LIB_DIRS = ~/gpi:'+GPI_PREFIX+'/gpi/node-libs/).\n')

            configfile.write('\n# A list of directories where nodes can be found.\n')
            configfile.write('# -To enable the exercises add \''+GPI_PREFIX+'/lib/gpi/doc/Training/exercises\'.\n')
            configfile.write('#LIB_DIRS = '+ ':'.join(GPI_LIBRARY_PATH_DEFAULT) + '\n')
            configfile.write('\n# Network file browser starts in this directory.\n')
            configfile.write('#NET_DIR = '+ GPI_NET_PATH_DEFAULT + '\n')
            configfile.write('\n# Widget file browser starts in this directory.\n')
            configfile.write('#DATA_DIR = '+ GPI_DATA_PATH_DEFAULT + '\n')
            configfile.write('\n# Follow the user\'s cwd. If True, the widget and network directories\n')
            configfile.write('# will change with the user input. If False, the browsers will alwasy open\n')
            configfile.write('# to the NET_DIR and DATA_DIR.\n')
            configfile.write('#FOLLOW_CWD = '+ str(GPI_FOLLOW_CWD)+ '\n')
            #configfile.write('\n# A list of directories where plugins can be found.\n')
            #configfile.write('#PLUGIN_DIRS = '+ ':'.join(GPI_PLUGIN_PATH_DEFAULT) + '\n')

            # File-type Association Section
            configfile.write('\n[ASSOCIATIONS]\n')
            configfile.write('# Add file-type associations with nodes.\n')
            configfile.write('#  ex. (file extension, node name, widget name)\n')

            # add default associations
            cnt = 0
            for key in sorted(Bindings.keys()):
                item = Bindings.get(key)
                configfile.write('#BIND_'+str(cnt) + ' = ' + str(item.asTuple()) + '\n')
                cnt += 1

            # Makefile mods
            configfile.write('\n[MAKE]\n')
            configfile.write('# Modify the gpi-make to include new libraries, library paths,\n')
            configfile.write('# and include paths.\n')
            configfile.write('# Example: (if blas is in \'/usr\' and lapack in \'/opt/lapack\'\n')
            configfile.write('#     g++ -I /usr/include -I /opt/lapack/include -L /usr/lib -L /opt/lapack/lib \n')
            configfile.write('#          -c x.cpp -lblas -llapack -o x.so -D_MY_MACRO_=helloworld -D_ANOTHER_\n')
            configfile.write('#LIBS = blas:lapack\n')
            configfile.write('#INC_DIRS = /usr/include:/opt/lapack/include\n')
            configfile.write('#LIB_DIRS = /usr/lib:/opt/lapack/lib\n')
            configfile.write('#CFLAGS = -D_MY_MACRO_=helloworld:-D_ANOTHER_\n')

        log.dialog(str(self._c_configFileName)+' written.')

    def loadConfigFile(self):
        # load private vars from config file

        if not self.configFileExists():
            log.info("loadConfigFile(): config file " + str(self._c_configFileName) + " doesn't exist, skipping.")
            return

        config = configparser.ConfigParser()
        config.read(self._c_configFileName)

        # print parse-able info
        #for s in config.sections():
        #    log.warn(str(config.items(s)))

        # actual paths and config options
        ap = lambda x: os.path.realpath(os.path.expanduser(x))  # single dirs
        aps = lambda x: [ ap(p) for p in x.split(':') ]  # multi-dirs
        ch = config.has_option  # if config has the option...
        cg = config.get
        oh = lambda x: x in os.environ
        oe = os.environ

        if config.has_section('GENERAL'):

            parm = self.parseMultiOPTS(config, 'GENERAL', 'IMPORT_CHECK', 'GPI_IMPORT_CHECK')
            if parm:
                if parm[0].lower() == 'true':
                    self._g_import_check = True
                elif parm[0].lower() == 'false':
                    self._g_import_check = False

        # PATH section
        #   Precedence is set by this config file, then env vars, then defaults.
        if config.has_section('PATH'):

            parm = self.parseMultiOPTS(config, 'PATH', 'LIB_DIRS', 'GPI_LIBRARY_PATH')
            if parm:
                parm = self.checkDirs(parm, 'PATH::LIB_DIRS')
                self._c_gpi_lib_path = parm

            parm = self.parseMultiOPTS(config, 'PATH', 'NET_DIR', 'GPI_NET_PATH')
            if parm:
                parm = self.checkDirs(parm, 'PATH::NET_DIR')
                self._c_networkDir = parm[0]  # only single dir

            parm = self.parseMultiOPTS(config, 'PATH', 'DATA_DIR', 'GPI_DATA_PATH')
            if parm:
                parm = self.checkDirs(parm, 'PATH::DATA_DIR')
                self._c_dataDir = parm[0]  # only single dir

            parm = self.parseMultiOPTS(config, 'PATH', 'FOLLOW_CWD', 'GPI_FOLLOW_CWD')
            if parm:
                if parm[0].lower() == 'true':
                    self._c_gpi_follow_cwd = True
                elif parm[0].lower() == 'false':
                    self._c_gpi_follow_cwd = False

            # parm = self.parseMultiOPTS(config, 'PATH', 'PLUGIN_DIRS', 'GPI_PLUGIN_PATH')
            # if parm:
            #     parm = self.checkDirs(parm, 'PATH::PLUGIN_DIRS')
            #     self._c_gpi_plugin_path = parm

        # File-type Association Section
        if config.has_section('ASSOCIATIONS'):

            for item in config.items('ASSOCIATIONS'):
                t = eval(str(item[1]))
                if item[0].lower().startswith('BIND_'.lower()):
                    if len(t) != 3:
                        log.error(str(self._c_configFileName) + ': error in assignment: ' + str(item))
                        continue
                    if (type(t) is not tuple) or (type(t[0]) is not str) or (type(t[1]) is not str) or (type(t[2]) is not str):
                        log.error(str(self._c_configFileName) + ': error in assignment: ' + str(item))
                    else:
                        Bindings.append(BindCatalogItem(t))

        # Makefile Section
        if config.has_section('MAKE'):
            parm = self.parseMultiOPTS(config, 'MAKE', 'LIBS', 'GPI_MAKE_LIBS')
            if parm:
                self._make_libs = parm

            parm = self.parseMultiOPTS(config, 'MAKE', 'LIB_DIRS', 'GPI_MAKE_LIB_PATH')
            if parm:
                parm = self.checkDirs(parm, 'MAKE::LIB_DIRS')
                self._make_lib_dirs = parm

            parm = self.parseMultiOPTS(config, 'MAKE', 'INC_DIRS', 'GPI_MAKE_INC_PATH')
            if parm:
                parm = self.checkDirs(parm, 'MAKE::INC_DIRS')
                self._make_inc_dirs = parm

            parm = self.parseMultiOPTS(config, 'MAKE', 'CFLAGS', 'GPI_MAKE_CFLAGS')
            if parm:
                self._make_cflags = parm

        log.dialog(str(self._c_configFileName) + ' has been loaded.')

    def parseMultiOPTS(self, config, section, option, env_opt=None, warnOnENV=True):
        # actual paths and config options
        #ap = lambda x: os.path.realpath(os.path.expanduser(x))  # single dirs
        ap = lambda x: x
        aps = lambda x: [ ap(p) for p in x.split(':') ]  # multi-dirs
        ch = config.has_option  # if config has the option...
        cg = config.get
        oh = lambda x: x in os.environ
        oe = os.environ

        if ch(section, option):
            return aps(cg(section, option))

        elif env_opt:
            if oh(env_opt):
                if warnOnENV:
                    log.warn('Setting from user environment. - '+str(env_opt))
                return aps(oe[env_opt])

    def checkDirs(self, l, opt):
        ap = lambda x: os.path.realpath(os.path.expanduser(x))  # single dirs

        # check each dir in the list and warn on non-existing dirs
        out = []
        for d in l:
            de = ap(d)  # expand paths
            out.append(de)
            if not os.path.isdir(de):
                log.warn('User Config: \''+str(opt)+'\': \''+str(d)+'\' is not a directory.')
        return out

    def configFileExists(self):
        return os.path.isfile(self._c_configFileName)

    def configFilePath(self):
        return self._c_configFileName

    def userLibPath(self):
        return self._c_userLibraryPath


# activate this upon first import
Config = ConfigManager()

#print Config
