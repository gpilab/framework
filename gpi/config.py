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

import ast
import os
import json
import traceback
import glob

# gpi
from .associate import Bindings, BindCatalogItem
from gpi import VERSION
from .logger import manager
from .sysspecs import Specs

log = manager.getLogger(__name__)

# Settings are stored alongside the GPI package — no home-dir pollution.
GPI_PREFIX = os.path.dirname(os.path.realpath(__file__))
SP_PREFIX  = os.path.dirname(GPI_PREFIX)
GPI_SETTINGS_FILE = os.path.join(GPI_PREFIX, 'gpi_settings.json')

# Legacy file names (used only for one-time migration)
_LEGACY_FILENAME = 'gpi.conf' if Specs.inWindows() else '.gpirc'
_LEGACY_PATH = os.path.join(os.path.expanduser('~'), _LEGACY_FILENAME)

### ENVIRONMENT VARIABLES
USER_HOME = os.path.expanduser('~')

USER_LIB_BASE_PATH_DEFAULT = os.path.join(USER_HOME, 'gpi')
_userNameKey = 'USERNAME' if Specs.inWindows() else 'USER'
USER_LIB_PATH_DEFAULT = os.path.join(
    USER_LIB_BASE_PATH_DEFAULT, os.environ.get(_userNameKey, 'UserNodes'))

GPI_NET_PATH_DEFAULT  = USER_HOME
GPI_DATA_PATH_DEFAULT = USER_HOME
GPI_FOLLOW_CWD = True

GPI_SP_NODE_LIBS = glob.glob(os.path.join(SP_PREFIX, 'gpi_*'))
GPI_LIBRARY_PATH_DEFAULT = [USER_LIB_BASE_PATH_DEFAULT, SP_PREFIX]


###############################################################################

class ConfigManager(object):
    '''Manages GPI settings, persisted as JSON in the GPI package directory.'''

    def __init__(self):
        # general
        self._g_import_check = True

        # appearance
        self._appearance_style = 'Dark'

        # paths
        self._c_networkDir    = GPI_NET_PATH_DEFAULT
        self._c_dataDir       = GPI_DATA_PATH_DEFAULT
        self._c_configFileName = GPI_SETTINGS_FILE

        self._c_userLibraryBasePath    = os.path.expanduser(USER_LIB_BASE_PATH_DEFAULT)
        self._c_userLibraryPath        = os.path.expanduser(USER_LIB_PATH_DEFAULT)
        self._c_userLibraryPath_def    = os.path.join(self._c_userLibraryPath, 'default')
        self._c_userLibraryPath_def_GPI  = os.path.join(self._c_userLibraryPath_def, 'GPI')
        self._c_userLibraryPath_init     = os.path.join(self._c_userLibraryPath, '__init__.py')
        self._c_userLibraryPath_def_init = os.path.join(self._c_userLibraryPath_def, '__init__.py')
        self._c_userLibraryPath_def_node = os.path.join(self._c_userLibraryPath_def_GPI, 'MyNode_GPI.py')

        self._c_gpi_lib_path   = list(GPI_LIBRARY_PATH_DEFAULT)
        self._c_gpi_follow_cwd = GPI_FOLLOW_CWD

        self._new_node_template_file = os.path.join(GPI_PREFIX, 'nodeTemplate.py')

        # make / build vars
        self._make_libs     = []
        self._make_lib_dirs = []
        self._make_inc_dirs = []
        self._make_cflags   = []

        try:
            self.loadConfigFile()
        except Exception:
            log.error("Config failed to load, using defaults. " + traceback.format_exc())

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def IMPORT_CHECK(self):
        return self._g_import_check

    @property
    def APPEARANCE_STYLE(self):
        return self._appearance_style

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

    # ── Persistence ───────────────────────────────────────────────────────────

    def saveConfigFile(self):
        """Persist current in-memory settings to GPI_PREFIX/gpi_settings.json."""
        data = {
            'GENERAL': {
                'IMPORT_CHECK': self._g_import_check,
            },
            'APPEARANCE': {
                'STYLE': self._appearance_style,
            },
            'PATH': {
                'LIB_DIRS':   self._c_gpi_lib_path,
                'NET_DIR':    self._c_networkDir,
                'DATA_DIR':   self._c_dataDir,
                'FOLLOW_CWD': self._c_gpi_follow_cwd,
            },
            'ASSOCIATIONS': [
                list(Bindings.get(k).asTuple())
                for k in sorted(Bindings.keys())
            ],
            'MAKE': {
                'LIBS':     self._make_libs,
                'LIB_DIRS': self._make_lib_dirs,
                'INC_DIRS': self._make_inc_dirs,
                'CFLAGS':   self._make_cflags,
            },
        }
        with open(self._c_configFileName, 'w') as fh:
            json.dump(data, fh, indent=2)
        log.dialog(self._c_configFileName + ' saved.')

    def loadConfigFile(self):
        """Load settings from JSON.  Falls back to legacy INI migration on first run."""
        if not os.path.isfile(self._c_configFileName):
            self._migrate_from_legacy()
            return

        try:
            with open(self._c_configFileName, 'r') as fh:
                data = json.load(fh)
        except Exception:
            log.error("Failed to parse settings JSON: " + traceback.format_exc())
            return

        ap = lambda x: os.path.realpath(os.path.expanduser(x))

        g = data.get('GENERAL', {})
        self._g_import_check = bool(g.get('IMPORT_CHECK', self._g_import_check))

        a = data.get('APPEARANCE', {})
        self._appearance_style = str(a.get('STYLE', ''))

        p = data.get('PATH', {})
        if 'LIB_DIRS' in p:
            dirs = [os.path.normpath(ap(d)) for d in p['LIB_DIRS'] if isinstance(d, str)]
            dirs = self.checkDirs(dirs, 'PATH::LIB_DIRS')
            if SP_PREFIX not in dirs:
                dirs.append(SP_PREFIX)
            self._c_gpi_lib_path = dirs
        if 'NET_DIR' in p:
            self._c_networkDir = os.path.normpath(ap(p['NET_DIR']))
        if 'DATA_DIR' in p:
            self._c_dataDir = os.path.normpath(ap(p['DATA_DIR']))
        if 'FOLLOW_CWD' in p:
            self._c_gpi_follow_cwd = bool(p['FOLLOW_CWD'])

        if 'ASSOCIATIONS' in data:
            Bindings._db.clear()
            for t in data['ASSOCIATIONS']:
                if isinstance(t, (list, tuple)) and len(t) == 3:
                    Bindings.append(BindCatalogItem(tuple(str(x) for x in t)))

        mk = data.get('MAKE', {})
        if 'LIBS'     in mk: self._make_libs     = list(mk['LIBS'])
        if 'LIB_DIRS' in mk: self._make_lib_dirs = self.checkDirs(mk['LIB_DIRS'], 'MAKE::LIB_DIRS')
        if 'INC_DIRS' in mk: self._make_inc_dirs = self.checkDirs(mk['INC_DIRS'], 'MAKE::INC_DIRS')
        if 'CFLAGS'   in mk: self._make_cflags   = list(mk['CFLAGS'])

        log.debug(self._c_configFileName + ' loaded.')

    def _migrate_from_legacy(self):
        """One-time import from the old ~/.gpirc / ~/gpi.conf INI file."""
        if not os.path.isfile(_LEGACY_PATH):
            return
        try:
            import configparser
            config = configparser.ConfigParser()
            config.read(_LEGACY_PATH)
            ap  = lambda x: os.path.realpath(os.path.expanduser(x))
            aps = lambda x: [ap(p) for p in x.split(os.pathsep)]
            ch, cg = config.has_option, config.get

            if config.has_section('GENERAL'):
                if ch('GENERAL', 'IMPORT_CHECK'):
                    self._g_import_check = cg('GENERAL', 'IMPORT_CHECK').lower() != 'false'

            if config.has_section('APPEARANCE'):
                if ch('APPEARANCE', 'STYLE'):
                    self._appearance_style = cg('APPEARANCE', 'STYLE').strip()

            if config.has_section('PATH'):
                if ch('PATH', 'LIB_DIRS'):
                    dirs = self.checkDirs(aps(cg('PATH', 'LIB_DIRS')), 'PATH::LIB_DIRS')
                    if SP_PREFIX not in dirs:
                        dirs.append(SP_PREFIX)
                    self._c_gpi_lib_path = dirs
                if ch('PATH', 'NET_DIR'):
                    self._c_networkDir = ap(cg('PATH', 'NET_DIR'))
                if ch('PATH', 'DATA_DIR'):
                    self._c_dataDir = ap(cg('PATH', 'DATA_DIR'))
                if ch('PATH', 'FOLLOW_CWD'):
                    self._c_gpi_follow_cwd = cg('PATH', 'FOLLOW_CWD').lower() != 'false'

            if config.has_section('ASSOCIATIONS'):
                for item in config.items('ASSOCIATIONS'):
                    if not item[0].lower().startswith('bind_'):
                        continue
                    try:
                        t = ast.literal_eval(item[1])
                        if isinstance(t, tuple) and len(t) == 3:
                            Bindings.append(BindCatalogItem(t))
                    except Exception:
                        pass

            if config.has_section('MAKE'):
                if ch('MAKE', 'LIBS'):
                    self._make_libs = aps(cg('MAKE', 'LIBS'))
                if ch('MAKE', 'LIB_DIRS'):
                    self._make_lib_dirs = self.checkDirs(aps(cg('MAKE', 'LIB_DIRS')), 'MAKE::LIB_DIRS')
                if ch('MAKE', 'INC_DIRS'):
                    self._make_inc_dirs = self.checkDirs(aps(cg('MAKE', 'INC_DIRS')), 'MAKE::INC_DIRS')
                if ch('MAKE', 'CFLAGS'):
                    self._make_cflags = aps(cg('MAKE', 'CFLAGS'))

            self.saveConfigFile()
            log.dialog('Migrated legacy config from ' + _LEGACY_PATH)
        except Exception:
            log.warn('Legacy config migration failed: ' + traceback.format_exc())

    # ── Helpers ───────────────────────────────────────────────────────────────

    def checkDirs(self, dirs, opt):
        ap = lambda x: os.path.realpath(os.path.expanduser(x))
        out = []
        for d in dirs:
            de = ap(d)
            out.append(de)
            if not os.path.isdir(de):
                log.warn("User Config: '{}': '{}' is not a directory.".format(opt, d))
        return out

    def configFileExists(self):
        return os.path.isfile(self._c_configFileName)

    def configFilePath(self):
        return self._c_configFileName

    def userLibPath(self):
        return self._c_userLibraryPath

    # ── User library scaffolding ──────────────────────────────────────────────

    def generateUserLib(self):
        self.initLibDir(self._c_userLibraryBasePath)
        self.initLibDir(self._c_userLibraryPath)
        self.initLibDir(self._c_userLibraryPath_def)
        self.initLibDir(self._c_userLibraryPath_def_GPI)
        self.initLibFile(self._c_userLibraryPath_init)
        self.initLibFile(self._c_userLibraryPath_def_init)
        if os.path.exists(self._c_userLibraryPath_def_node):
            log.dialog('Example node already exists, skipping: ' + self._c_userLibraryPath_def_node)
        else:
            with open(self._c_userLibraryPath_def_node, 'w') as f:
                log.dialog('Writing example node: ' + self._c_userLibraryPath_def_node)
                f.write(self.exampleNodeCode())

    def exampleNodeCode(self):
        header = '# GPI (v{}) auto-generated library file.\n#\n'.format(VERSION)
        filename = '# FILE: {}\n#\n'.format(self._c_userLibraryPath_def_node)
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
        return header + filename + buf

    def initLibDir(self, path):
        if os.path.exists(path):
            log.dialog('Library path already exists, skipping: ' + path)
        else:
            log.dialog('Creating library path: ' + path)
            os.mkdir(path)

    def initLibFile(self, path):
        if os.path.exists(path):
            log.dialog('Library file already exists, skipping: ' + path)
        else:
            log.dialog('Creating library file: ' + path)
            with open(path, 'w') as f:
                f.write('# GPI (v{}) auto-generated library file.\n'.format(VERSION))

    def __str__(self):
        msg = 'GENERAL:\n'
        for o in dir(self):
            if o.startswith('_g_'):
                msg += '  {}: {}\n'.format(o, getattr(self, o))
        msg += 'PATH:\n'
        for o in dir(self):
            if o.startswith('_c_'):
                msg += '  {}: {}\n'.format(o, getattr(self, o))
        msg += 'ASSOCIATIONS:\n'
        for v in sorted([str(x) for x in list(Bindings.values())]):
            msg += '  {}\n'.format(v)
        msg += 'MAKE:\n'
        for o in dir(self):
            if o.startswith('_make_'):
                msg += '  {}: {}\n'.format(o, getattr(self, o))
        return msg


# activate this upon first import
Config = ConfigManager()
