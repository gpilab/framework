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

'''
Classes for loading and saving each version of gpi networks.  Each class
corresponds to a particular network file description.  Upon load, the network
file type is determined and then the appropriate class is installed. On write,
the latest network description is used.
'''


# TODO: add a header to the pickle file
#       -create a gpickle class that pickles the network description
#        and prepends version info before the pickle info


import os
import re
import sys
import json
import numpy as np
import time
import codecs
import pickle
import traceback

# gpi
from gpi import QtGui, QtCore, VERSION
from .config import Config
from .defines import GetHumanReadable_time, GetHumanReadable_bytes, TranslateFileURI
from .logger import manager
from .sysspecs import Specs
from .widgets import GPIFileDialog

# start logger for this module
log = manager.getLogger(__name__)

# convert json unserializable numpy types to python types
class numpy_json_encoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return super(numpy_json_encoder, self).default(obj)

def convert_keysandvals_to_string(dictionary):
    """Recursively converts unicode vals to strings.
    Operates on dictionaries, lists and dict-keys.
    """
    if not isinstance(dictionary, dict):
        if isinstance(dictionary, unicode):
            return str(dictionary.encode('latin1'))
        if isinstance(dictionary, list):
            return list(convert_keysandvals_to_string(k) for k in dictionary)
        return dictionary
    return dict((str(k.encode('latin1')), convert_keysandvals_to_string(v)) for k, v in dictionary.items())

class Network_Base(object):
    '''All networks should implement this base class and be named with the
    'Network_v<version>' where 'version' is a str(integer).
    '''
    GPINET_VERSION=''

    def __init__(self, fname, contents=None):
        # fname: filename for saving or loading
        # contents: an object containing network info compatible with the canvas'
        #   serializeCanvas() and deserializeCanvas() routines.
        pass

    def load(self):
        # open the file and load its contents into memory
        # -via pickle, config, xml, etc...
        pass

    def save(self):
        # open a file for writing and write the network object contents to disk
        pass

    def test(self):
        # test to see if the network file is THIS version, return True if it is.
        return False

    def version(self):
        # return the version number as a str
        return str(self.GPINET_VERSION)

    def __str__(self):
        # for sorting
        return self.version()

class Network_v1(Network_Base):
    '''The first version of the network interface compatible with the released
    GPI-beta.  The file format is pickled list() and dict() objects.  The original 
    released header doesn't necessarily contain a version number so network
    files w/o are assumed to be this version.
    '''
    GPINET_VERSION='1'

    def __init__(self, fname, contents=None):
        self._fname = fname  # not actually needed since parent did the loading
        self._contents = contents  # a shortcut if the caller did the reading
                                   # also used for storing network data to save

    def test(self):
        # there is no way of verifying the first network version so it always
        # returns false and is only invoked as a last resort.
        # the best we can do is read in the whole file and check some fields
        try:
            with open(self._fname, "rb") as fptr:
                contents = pickle.load(fptr, encoding="latin1")
        except:
            log.debug('Network_v1 test: '+str(traceback.format_exc()))
            return False

        # check for dictionary structure
        if not isinstance(contents, dict):
            log.debug('Network_v1 test: Failure: contents are not of type dict.')
            return False
        return True

    def load(self):
        # load file contents into memory
        with open(self._fname, "rb") as fptr:
            self._contents = pickle.load(fptr, encoding="latin1")
        return self.convert_incoming()

    def save(self):
        # save network contents to a file
        # convert to the right type
        self.convert_outgoing()
        try:
            with open(self._fname, "wb") as fptr:
                pickle.dump(self._contents, fptr)
            log.dialog("Network saved.")
        except:
            log.error("Saving network failed.")
            log.error(traceback.format_exc())

    def convert_incoming(self):
        # From file.
        # convert loaded data into common object format
        # -since its pickled its already in the right format

        # take this opportunity to print out some network file stats
        msg = 'Network file info:\n'
        if 'NETWORK_VERSION' in self._contents:
            msg += '\tnet-version: '+str(self._contents['NETWORK_VERSION']) + '\n'
        else:
            msg += '\tassumed net-version: '+str(self.version())+'\n'

        if 'GPI_VERSION' in self._contents:
            msg += '\tsaved with gpi-version: '+str(self._contents['GPI_VERSION']) + '\n'
        log.warn(msg)

        # BACKWARD COMPATIBILITY
        # add a dummy node key into all the node dicts
        # -since the key is an empty string, the lookup will fall back to
        #  finding the best match
        for node in self._contents['nodes']['nodes']:
            node['key'] = ''
            node['walltime'] = '0'
            node['avgwalltime'] = '0'
            node['stdwalltime'] = '0'

        return self._contents

    def convert_outgoing(self):
        # Takes input from canvas.  To file.
        # convert serialized data in memory to the type required by the file
        # format.  Since its a nested dict(), pickle can handle this directly.
        network = self._contents

        # network files are dictionaries that contain:
        # {'nodes': <a list of node settings>}
        #   -widget info
        #   -port info
        #   -connections
        #   -position
        #   -TODO: menu window position
        #   -TODO: original node path (not yet sure if
        #               specificity is better here)
        #
        # {'path': <a list of paths where nodes can be found>}
        #   -sys.path (accumulated dragNdrop, loads, etc...)
        #
        # Potential Future Additions:
        # {'canvas': <a list of canvas params>}
        #   -size, shape (depends on display)
        #network['path'] = sys.path  # no longer needed
        network['NETWORK_VERSION'] = self.version()
        network['GPI_VERSION'] = VERSION
        network['HEADER'] = 'This is a GPI Network File'

class Network_v2(Network_Base):
    '''The second version of the network interface.  This version supports new
    2-level library scope which exists as an extra tag in the node settings dict.
    The file format is pickled list() and dict() objects.  The original 
    released header doesn't necessarily contain a version number so network
    files w/o are assumed to be this version.
    '''
    GPINET_VERSION='2'

    def __init__(self, fname, contents=None):
        self._fname = fname  # not actually needed since parent did the loading
        self._contents = contents  # a shortcut if the caller did the reading
                                   # also used for storing network data to save

    def test(self):
        # the best we can do is read in the whole file and check some fields
        try:
            with open(self._fname, "rb") as fptr:
                contents = pickle.load(fptr, encoding="latin1")
        except:
            log.debug('Network_v2 test: '+str(traceback.format_exc()))
            return False

        # check for dictionary structure
        if not isinstance(contents, dict):
            log.debug('Network_v2 test: Failure: contents are not of type dict.')
            return False

        # check the version
        if 'NETWORK_VERSION' in contents:
            if str(contents['NETWORK_VERSION']) == self.version():
                return True
        return False

    def load(self):
        # load file contents into memory
        with open(self._fname, "rb") as fptr:
            self._contents = pickle.load(fptr, encoding="latin1")
        return self.convert_incoming()

    def save(self):
        # save network contents to a file
        # convert to the right type
        self.convert_outgoing()
        try:
            with open(self._fname, "wb") as fptr:
                pickle.dump(self._contents, fptr)
            log.dialog("Network saved.")
        except:
            log.error("Saving network failed.")
            log.error(traceback.format_exc())

    def convert_incoming(self):
        # From file.
        # convert loaded data into common object format
        # -since its pickled its already in the right format

        # take this opportunity to print out some network file stats
        msg = 'Network file info:\n'
        if 'NETWORK_VERSION' in self._contents:
            msg += '\tnet-version: '+str(self._contents['NETWORK_VERSION']) + '\n'

        if 'GPI_VERSION' in self._contents:
            msg += '\tsaved with gpi-version: '+str(self._contents['GPI_VERSION']) + '\n'

        if 'DATETIME' in self._contents:
            msg += '\tdate saved: '+str(self._contents['DATETIME']) + '\n'

        if 'WALLTIME' in self._contents:
            msg += '\twall time: '+str(GetHumanReadable_time(float(self._contents['WALLTIME']))) + '\n'

        if 'TOTAL_PMEM' in self._contents:
            msg += '\ttotal port mem: '+str(GetHumanReadable_bytes(int(self._contents['TOTAL_PMEM']))) + '\n'

        if 'PLATFORM' in self._contents:
            for k,v in list(self._contents['PLATFORM'].items()):
                msg += '\t'+k+': '+str(v)+'\n'

        log.dialog(msg)

        return self._contents

    def convert_outgoing(self):
        # Takes input from canvas.  To file.
        # convert serialized data in memory to the type required by the file
        # format.  Since its a nested dict(), pickle can handle this directly.
        network = self._contents

        # network files are dictionaries that contain:
        # {'nodes': <a list of node settings>}
        #   -widget info
        #   -port info
        #   -connections
        #   -position
        #   -TODO: menu window position
        #   -TODO: original node path (not yet sure if
        #               specificity is better here)
        #
        # {'path': <a list of paths where nodes can be found>}
        #   -sys.path (accumulated dragNdrop, loads, etc...)
        #
        # Potential Future Additions:
        # {'canvas': <a list of canvas params>}
        #   -size, shape (depends on display)
        #network['path'] = sys.path  # no longer needed
        network['NETWORK_VERSION'] = self.version()
        network['GPI_VERSION'] = VERSION
        network['HEADER'] = 'This is a GPI Network File'
        network['DATETIME'] = str(time.asctime(time.localtime()))

        # network['PLATFORM']
        network['PLATFORM'] = Specs.table()

class Network_v3(Network_v2):
    '''The third version of the network interface.  This version supports
    the json data file format for better multi-platform support.
    '''
    GPINET_VERSION='3'

    def __init__(self, fname, contents=None):
        super(Network_v3, self).__init__(fname, contents)
        self._fname = fname  # not actually needed since parent did the loading
        self._contents = contents  # a shortcut if the caller did the reading
                                   # also used for storing network data to save

        # write a simple header that can verify the network version directly
        # without having to read the whole file.
        self._header = "# This file was written with GPI v"+str(VERSION)
        self._header += " using Network v"+str(self.version())
        self._header += ". Do not edit this line.\n"

        # validate the network version and potentially the GPI version
        self._header_regex = "(GPI|gpi)\s+v([\w.]+).*[Nn]et.*v([\d]+)"

    def test(self):
        try:
            with open(self._fname, "r", encoding='utf8') as fptr:
                # check the first line in the file
                match = re.compile(self._header_regex).search(fptr.readline())
                if match:
                    if match.group(3) == self.version():
                        # if the versions match, thats gold
                        return True
        except:
            log.debug('Network_v3 test: '+str(traceback.format_exc()))
            return False
        return False

    def save(self):
        # save network contents to a file
        # file operations go here

        # convert to the right type
        self.convert_outgoing()

        try:
            with open(self._fname, "w", encoding='utf8') as fptr:
                fptr.write(self._header)
                json.dump(self._contents, fptr, sort_keys=True, indent=1, cls=numpy_json_encoder)
            log.dialog("Network saved.")
        except:
            log.error("Saving network failed. "+str(traceback.format_exc()))

    def load(self):
        # load network dict
        with open(self._fname, "r", encoding='utf8') as fptr:
            fptr.readline() # header
            self._contents = json.load(fptr)
        return self.convert_incoming()


########################################################################
# Network IO Manager Class

class Network(object):
    '''Determines the version of the file to be read, then chooses the correct
    loading object for that version.  The loading object must translate the
    file contents to the various object settings that make up the network
    description.  This object should handle the parent calls.
    '''

    def __init__(self, parent):
        self._parent = parent

        # this is a crutch: see determine_version()
        self._unpickled_contents = None

        self._latest_net_version = None
        self._latest_net_class = None

        # start with this path and then follow the user's cwd for this session
        self._current_working_dir = TranslateFileURI(Config.GPI_NET_PATH)

        self.getLatestClass()

    def getLatestClass(self):
        thismodule = sys.modules[__name__]
        netclasses = []
        for cls in dir(thismodule):
            if cls.startswith('Network_v'):
                netclasses.append(cls)
        versions = [x.split('Network_v')[1] for x in netclasses]

        self._latest_net_version = max(versions)
        self._latest_net_class = getattr(thismodule, 'Network_v'+self._latest_net_version)

    def netDesc(self):
        # all network objects that derive from Network_Base()
        l = []
        for mnam in dir(sys.modules[__name__]):
            mod = getattr(sys.modules[__name__], mnam)
            if hasattr(mod, 'GPINET_VERSION'):
                l.append(mod)
        l = sorted(l, key=str, reverse=True) # try highest version first
        return l

    def determine_version(self, fname):
        # check the file format for version and format info
        # -loading is the only way to check if its pickled, so just return
        # the unpickled contents along with the version.  In the future, if
        # pickle is no longer used, then the other format will be checked
        # first, then pickle as a backup.

        # loop over all of the Network description classes
        for obj in self.netDesc():
            # test the network file with the given class
            n = obj(fname)
            try:
                if n.test():
                    # set the version number if the network passed
                    version = n.version()
                    break
            except pickle.UnpicklingError:
                pass

        if version != self._latest_net_version:
            log.warn('This network was saved in an older format, please re-save this network.')

        return version

    def loadNetworkFromFile(self, fname):
        # Used with drops, command-line input, and dialog input
        log.debug('loadNetworkFromFile()')

        # check for valid filename
        if not os.path.isfile(fname):
            log.error("\'" + str(fname) + "\' is not a valid filename, skipping.")
            return

        # determine network format obj type by version and load contents
        # TODO: make this automatically choose the right loader object
        log.debug('determine_version()')
        ver = self.determine_version(fname)
        log.debug('version found: '+str(ver))
        if ver == self._latest_net_version:
            net = self._latest_net_class(fname, contents=self._unpickled_contents)
        elif hasattr(sys.modules[__name__], 'Network_v'+ver):
            net = getattr(sys.modules[__name__], 'Network_v'+ver)(fname, contents=self._unpickled_contents)
        else:
            log.error('Network version cannot be determined, skipping.')
            return

        log.debug('net.load() called')
        return net.load()  # network data objects

    def saveNetworkToFile(self, fname, network):
        # used for dialog, possibly command-line

        # enforce network filename consistency
        if not fname.endswith('.net'):
            fname += '.net'

        # always save in the latest version
        net = self._latest_net_class(fname, contents=network)
        net.save()

    def loadNetworkFromFileDialog(self):

        # start looking in user config'd network dir
        #start_path = os.path.expanduser(self._parent.parent._networkDir)
        #start_path = os.path.expanduser('~/')
        start_path = TranslateFileURI(Config.GPI_NET_PATH)
        log.info("File browser start path: " + start_path)

        # create dialog box
        kwargs = {}
        kwargs['filter'] = 'GPI network (*.net)'
        kwargs['caption'] = 'Open Session (*.net)'
        kwargs['directory'] = self._current_working_dir
        dia = GPIFileDialog(self._parent, **kwargs)

        # don't run if cancelled
        if dia.runOpenFileDialog():

            # save the current directory for next browse
            if Config.GPI_FOLLOW_CWD:
                self._current_working_dir = str(dia.directory().path())

            fname = str(dia.selectedFiles()[0])

            return self.loadNetworkFromFile(fname)

    def listMediaDirs(self):
        if Specs.inOSX():
            rdir = '/Volumes'
            if os.path.isdir(rdir):
                return ['file://'+rdir+'/'+p for p in os.listdir(rdir)]
        elif Specs.inLinux():
            rdir = '/media'
            if os.path.isdir(rdir):
                return ['file://'+rdir+'/'+p for p in os.listdir(rdir)]
            rdir = '/mnt'
            if os.path.isdir(rdir):
                return ['file://'+rdir+'/'+p for p in os.listdir(rdir)]
        return []

    def saveNetworkFromFileDialog(self, network):

        # make sure there is something worth saving
        nodes = network['nodes']
        layouts = network['layouts']

        log.debug(str(nodes))
        log.debug(str(layouts))

        if nodes is None:
            # Error message to user, should go to statusbar
            log.warn("No network data to save, skipping.")
            return

        if not len(nodes['nodes']) and not len(nodes['macroNodes']):
            # Error message to user, should go to statusbar
            log.warn("No network data to save, skipping.")
            return

        kwargs = {}
        kwargs['filter'] = 'GPI network (*.net)'
        kwargs['caption'] = 'Save Session (*.net)'
        kwargs['directory'] = self._current_working_dir
        dia = GPIFileDialog(self._parent, **kwargs)
        dia.selectFile('Untitled.net')

        # don't run if cancelled
        if dia.runSaveFileDialog():

            # save the current directory for next browse
            if Config.GPI_FOLLOW_CWD:
                self._current_working_dir = str(dia.directory().path())

            fname = dia.selectedFilteredFiles()[0]
            self.saveNetworkToFile(fname, network)
