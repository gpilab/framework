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

''' A pymod loader for managing loaded nodes, types, and widgets. '''


import os
import sys
import importlib
import importlib.util
import importlib.machinery
import traceback
import py_compile

# gpi
from .defines import GPI_PYMOD_EXTS
from .logger import manager

# start logger for this module
log = manager.getLogger(__name__)

def consolidatePaths(plist):
    '''Take the set() of all abspaths().  Doesn't guarantee original order.
    '''
    nlist = []
    for l in plist:
        nlist.append(os.path.abspath(l))
    nlist = list(set(nlist))
    return nlist

def appendSysPath(path):
    '''Put a new path at the end of sys.path if it doesn't already exist.
    '''
    if path not in sys.path:
        #print 'adding path to sys: '+path
        sys.path.append(path)

def consolidateSysPath():
    '''Run consolitatePaths() on sys.path.
    '''
    sys.path = consolidatePaths(sys.path)

def PKGroot(fullpath):
    '''See if the file or directory pointed to by fullpath is a package dir
    or subpackage dir.  Return the highest package dir.
    '''
    # strip off filename if included
    path = fullpath
    if not os.path.isdir(fullpath):
        path = os.path.dirname(fullpath)

    # skip ./GPI dir
    if os.path.basename(path) == 'GPI':
        path = os.path.dirname(path)

    # find root package dir
    root_found = False
    while not root_found:

        # check if cur dir is part of a package
        if os.path.isfile(path + '/__init__.py'):
            path = os.path.dirname(path)
        else:
            root_found = True

    return path


def loadMod(fullpath):
    '''Load modules .py or .pyc from the given path and store in sys.modules
    using the fullpath as the key.  This will allow all plugins and node
    descriptions to be unique, even if they have the same name.
    '''

    if not os.path.isfile(fullpath):
        log.error('The supplied path is not a file: '+str(fullpath))
        return None

    # exclude the file extension to allow reloads
    store_name, ext = os.path.splitext(fullpath)
    if ext not in GPI_PYMOD_EXTS:
        log.error('The filename is not a valid pymod: '+str(fullpath))
        return None

    # optionally pre-compile .py files
    if ext == '.py':
        if os.access(os.path.dirname(fullpath), os.W_OK):
            # Force compile every time b/c some virtual machines somehow get
            # incorrect timestamps which causes node updates not to be taken.
            try:
                py_compile.compile(fullpath, doraise=True)
                log.info('SUCCESS: '+fullpath)
            except:
                log.error(str(traceback.format_exc()) + '\nFAILED:'+fullpath)
        else:
            log.info('Cannot compile, permission denied: '+str(fullpath))

    # Load the module from its full filesystem path.
    # store_name (path without extension) is used as the sys.modules key so
    # every node file has a unique identity even when filenames collide.
    try:
        spec = importlib.util.spec_from_file_location(store_name, fullpath)
        if spec is None:
            log.error(str(fullpath)+' failed to create a module spec in loadMod')
            return None
        mod = importlib.util.module_from_spec(spec)
        sys.modules[store_name] = mod   # register before exec so circular imports work
        spec.loader.exec_module(mod)
    except:
        log.error(str(fullpath)+' module failed to load in loadMod with:\n' + str(traceback.format_exc()))
        sys.modules.pop(store_name, None)
        return None

    return mod


def findAndLoadMod(name, path=None, store_name=None):
    '''Load modules .py or .pyc from sys.path or path, if given.
    'path' must be a list.

    DEPRECATED
        -not sure when this stopped being used or if find_module()
        affords us anything over the loadMod().
    '''

    if store_name is None:
        store_name = name

    if path is not None:
        for p in path:
            if not os.path.isdir(p):
                log.error('The supplied path is not a directory: '+str(p))

    # If a search path list is given, look for name.py / name.pyc in each dir.
    if path is not None:
        for search_dir in path:
            for ext in ('.py', '.pyc'):
                candidate = os.path.join(search_dir, name + ext)
                if os.path.isfile(candidate):
                    return loadMod(candidate)
        log.error('Failed to locate module '+str(name)+' in supplied paths')
        return None

    # No path given — use importlib to find the module on sys.path.
    try:
        spec = importlib.util.find_spec(name)
    except (ModuleNotFoundError, ValueError):
        spec = None

    if spec is None or spec.origin is None:
        log.error('Failed to locate module: '+str(name))
        return None

    return loadMod(spec.origin)
