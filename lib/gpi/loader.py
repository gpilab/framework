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
import imp
import sys
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

    # make import params
    fp = open(fullpath, "rb")
    description = (ext, 'rb', 1)

    # load .py
    if ext == '.py':

        # only attempt compilation if the directory is writeable 
        #   -this helps with distributed libraries.
        if os.access(os.path.dirname(fullpath), os.W_OK):

            # Force compile every time b/c some virtual machines somehow get
            # incorrect timestaps which causes node updates not to be taken.
            try:
                py_compile.compile(fullpath, doraise=True)
                log.info('SUCCESS: '+fullpath)
            except:
                log.error(str(traceback.format_exc()) + '\nFAILED:'+fullpath)

        else:
            log.info('Cannot compile, permission denied: '+str(fullpath))

        try:
            mod = imp.load_module(store_name, fp, fullpath, description)
        except: # ImportError:
            log.error(str(fullpath)+' module failed to load in loadMod(.py) with:\n' + str(traceback.format_exc()))
            return None
        finally:
            if fp:
                fp.close()

    # load compiled .pyc, etc...
    else:
        try:
            mod = imp.load_compiled(store_name, fullpath, fp)
        except: # ImportError:
            log.error(str(fullpath)+' module failed to load in loadMod(\'compiled\') with:\n' + str(traceback.format_exc()))
            return None
        finally:
            if fp:
                fp.close()

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
        cnt = 0
        for p in path:
            if not os.path.isdir(p):
                log.error('The supplied path is not a directory: '+str(p))
                cnt += 1
            if len(path) == cnt:
                log.error('None of the supplied paths are valid dirs, skipping load().')
                return None

    # make import params
    try:
        if path is not None:
            fp, pathname, description = imp.find_module(name, path)
        else:
            fp, pathname, description = imp.find_module(name)
    except: # ImportError:
        log.error('Failed to locate module: '+str(name))
        return None

    # load .py
    if description[0] == '.py':

        # Force compile every time b/c some virtual machines somehow get
        # incorrect timestaps which causes node updates not to be taken.
        #try:
        #    compileall.compile_file(pathname)
        #    print pathname
        #    log.dialog('findAndLoadMod: py compiled.')
        #except:
        #    log.dialog('findAndLoadMod: py not compiled.')

        try:
            mod = imp.load_module(store_name, fp, pathname, description)
        except: # ImportError:
            log.error(str(name)+' module failed to load in findAndLoadMod(.py) with:\n' + str(traceback.format_exc()))
            return None
        finally:
            if fp:
                fp.close()

    # load compiled .pyc, etc...
    else:
        try:
            mod = imp.load_compiled(store_name, pathname, fp)
        except: # ImportError:
            log.error(str(name)+' module failed to load in findAndLoadMod(compiled) with:\n' + str(traceback.format_exc()))
            return None
        finally:
            if fp:
                fp.close()

    return mod
