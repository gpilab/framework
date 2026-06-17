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

import os
import json
import traceback
import glob
import sysconfig

# gpi
from .associate import Bindings, BindCatalogItem
from gpi import VERSION
from .logger import manager
from .sysspecs import Specs

log = manager.getLogger(__name__)

# GPI_PREFIX: the source/installed package directory (for templates, icons, etc.)
GPI_PREFIX = os.path.dirname(os.path.realpath(__file__))
SP_PREFIX  = os.path.dirname(GPI_PREFIX)

def _resolve_config_dir():
    """Return a writable gpi/ folder inside the active conda/virtualenv site-packages.

    This keeps runtime config files (settings, shortcuts) out of the source tree
    so they are never accidentally shared or committed.  Falls back to ~/.gpi if
    site-packages is read-only (e.g. system Python).
    """
    sp = sysconfig.get_paths().get('purelib', '')
    candidate = os.path.join(sp, 'gpi')
    try:
        os.makedirs(candidate, exist_ok=True)
        probe = os.path.join(candidate, '.write_probe')
        with open(probe, 'w') as f:
            f.write('')
        os.unlink(probe)
        return candidate
    except OSError:
        fallback = os.path.join(os.path.expanduser('~'), '.gpi')
        os.makedirs(fallback, exist_ok=True)
        return fallback

# All runtime config files live here — NOT in the source tree.
GPI_CONFIG_DIR    = _resolve_config_dir()
GPI_SETTINGS_FILE = os.path.join(GPI_CONFIG_DIR, 'gpi_settings.json')

### ENVIRONMENT VARIABLES
USER_HOME = os.path.expanduser('~')

USER_LIB_BASE_PATH_DEFAULT = os.path.join(USER_HOME, 'gpi')
_userNameKey = 'USERNAME' if Specs.inWindows() else 'USER'
USER_LIB_PATH_DEFAULT = os.path.join(
    USER_LIB_BASE_PATH_DEFAULT, os.environ.get(_userNameKey, 'UserNodes'))

GPI_NET_PATH_DEFAULT  = USER_HOME
GPI_DATA_PATH_DEFAULT = USER_HOME
GPI_FOLLOW_CWD = True

# Site-packages of the active conda/virtualenv env — works for both editable and
# installed packages.  sysconfig gives the real path regardless of install mode.
_SP_PURELIB = sysconfig.get_paths().get('purelib', SP_PREFIX)
GPI_SP_NODE_LIBS = glob.glob(os.path.join(_SP_PURELIB, 'gpi_*'))
GPI_LIBRARY_PATH_DEFAULT = [_SP_PURELIB]


###############################################################################

class ConfigManager(object):
    '''Manages GPI settings, persisted as JSON in the GPI package directory.'''

    def __init__(self):
        # general
        self._g_import_check = True

        # appearance
        self._appearance_style = 'Dark'
        self._layout_direction = 'Horizontal'

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

        # shortcuts (consolidated into gpi_settings.json)
        self._canvas_shortcut_overrides = {}   # {action_id: key_str} — non-defaults only
        self._node_shortcuts = []              # [[key_combo, node_key], ...]

        _first_run = not os.path.isfile(GPI_SETTINGS_FILE)
        try:
            self.loadConfigFile()
        except Exception:
            log.error("Config failed to load, using defaults. " + traceback.format_exc())
        if _first_run:
            # Write defaults immediately so the file exists after first launch.
            try:
                self.saveConfigFile()
            except Exception:
                pass

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def IMPORT_CHECK(self):
        return self._g_import_check

    @property
    def APPEARANCE_STYLE(self):
        return self._appearance_style

    @property
    def LAYOUT_DIRECTION(self):
        return self._layout_direction

    @LAYOUT_DIRECTION.setter
    def LAYOUT_DIRECTION(self, value):
        self._layout_direction = value

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

    @property
    def CANVAS_SHORTCUT_OVERRIDES(self):
        return self._canvas_shortcut_overrides

    @CANVAS_SHORTCUT_OVERRIDES.setter
    def CANVAS_SHORTCUT_OVERRIDES(self, val):
        self._canvas_shortcut_overrides = val

    @property
    def NODE_SHORTCUTS(self):
        return self._node_shortcuts

    @NODE_SHORTCUTS.setter
    def NODE_SHORTCUTS(self, val):
        self._node_shortcuts = val

    # ── Persistence ───────────────────────────────────────────────────────────

    def saveConfigFile(self):
        """Persist current in-memory settings to GPI_PREFIX/gpi_settings.json."""
        data = {
            'GENERAL': {},
            'APPEARANCE': {
                'STYLE': self._appearance_style,
                'LAYOUT': self._layout_direction,
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
            'CANVAS_SHORTCUTS': self._canvas_shortcut_overrides,
            'NODE_SHORTCUTS':   self._node_shortcuts,
        }
        with open(self._c_configFileName, 'w') as fh:
            json.dump(data, fh, indent=2)
        log.debug(self._c_configFileName + ' saved.')

    def loadConfigFile(self):
        """Load settings from JSON.  Uses defaults if file doesn't exist yet."""
        if not os.path.isfile(self._c_configFileName):
            return

        try:
            with open(self._c_configFileName, 'r') as fh:
                data = json.load(fh)
        except Exception:
            log.error("Failed to parse settings JSON: " + traceback.format_exc())
            return

        ap = lambda x: os.path.realpath(os.path.expanduser(x))

        a = data.get('APPEARANCE', {})
        self._appearance_style = str(a.get('STYLE', ''))
        self._layout_direction = str(a.get('LAYOUT', 'Horizontal'))

        p = data.get('PATH', {})
        if 'LIB_DIRS' in p:
            dirs = [os.path.normpath(ap(d)) for d in p['LIB_DIRS'] if isinstance(d, str)]
            dirs = self.checkDirs(dirs, 'PATH::LIB_DIRS')
            if _SP_PURELIB not in dirs:
                dirs.append(_SP_PURELIB)
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

        # Canvas shortcuts — migrate from old canvas_shortcuts.json on first load
        if 'CANVAS_SHORTCUTS' in data:
            self._canvas_shortcut_overrides = {str(k): str(v)
                                               for k, v in data['CANVAS_SHORTCUTS'].items()}
        else:
            old = os.path.join(GPI_CONFIG_DIR, 'canvas_shortcuts.json')
            if os.path.isfile(old):
                try:
                    self._canvas_shortcut_overrides = json.loads(open(old).read())
                except Exception:
                    pass

        # Node-deploy shortcuts — migrate from old shortcuts.txt on first load
        if 'NODE_SHORTCUTS' in data:
            self._node_shortcuts = [list(x) for x in data['NODE_SHORTCUTS']
                                    if isinstance(x, (list, tuple)) and len(x) >= 2]
        else:
            old = os.path.join(GPI_CONFIG_DIR, 'shortcuts.txt')
            if os.path.isfile(old):
                try:
                    pairs = []
                    for line in open(old).read().splitlines():
                        parts = line.split(':', 1)
                        if len(parts) == 2 and parts[0].strip() and parts[1].strip():
                            pairs.append([parts[0].strip(), parts[1].strip()])
                    self._node_shortcuts = pairs
                except Exception:
                    pass

        log.debug(self._c_configFileName + ' loaded.')

    def resetToDefaults(self):
        """Wipe the saved config file and reload from code defaults."""
        from .associate import Bindings, BindCatalogItem
        import sys as _sys, importlib as _il

        # Reset config fields to their __init__ defaults
        self._g_import_check    = True
        self._appearance_style  = 'Dark'
        self._layout_direction  = 'Horizontal'
        self._c_networkDir      = GPI_NET_PATH_DEFAULT
        self._c_dataDir         = GPI_DATA_PATH_DEFAULT
        self._c_gpi_lib_path    = list(GPI_LIBRARY_PATH_DEFAULT)
        self._c_gpi_follow_cwd  = GPI_FOLLOW_CWD
        self._make_libs                 = []
        self._make_lib_dirs             = []
        self._make_inc_dirs             = []
        self._make_cflags               = []
        self._canvas_shortcut_overrides = {}
        self._node_shortcuts            = []

        # Reload Bindings from associate.py defaults
        import gpi.associate as _assoc
        Bindings._db.clear()
        for b in sorted(x for x in dir(_assoc) if x.startswith('bind_')):
            item = BindCatalogItem(getattr(_assoc, b))
            Bindings.append(item)

        self.saveConfigFile()

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
