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

# Classes for loading and saving each version of gpi networks.
# TODO: add a header to the pickle file
#       -create a gpickle class that pickles the network description
#        and prepends version info before the pickle info


import os
import sys
import time
import pickle
import traceback

# gpi
from gpi import QtGui, VERSION
from .defines import GetHumanReadable_time, GetHumanReadable_bytes
from .logger import manager
from .sysspecs import Specs

# start logger for this module
log = manager.getLogger(__name__)


class Network_Base(object):
    '''All networks should implement this base class and be named with the
    'Network_v<version>' where 'version' is a str(integer).
    '''
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


class Network_v2(Network_Base):
    '''The second version of the network interface.  This version supports new
    2-level library scope which exists as an extra tag in the node settings dict.
    The file format is pickled list() and dict() objects.  The original 
    released header doesn't necessarily contain a version number so network
    files w/o are assumed to be this version.
    '''

    def __init__(self, fname, contents=None):
        self._version = '2'
        self._fname = fname  # not actually needed since parent did the loading
        self._contents = contents  # a shortcut if the caller did the reading
                                   # also used for storing network data to save

    def load(self):
        # load file contents into memory
        # -since its a pickle file, this as already been done by the parent
        #  when checking the version.
        # -file operations would go here
        if self._contents is None:
            # this shouldn't happen
            log.error('parent didnt unpickle!')
            return

        return self.convert_incoming()

    def save(self):
        # save network contents to a file
        # file operations go here

        # convert to the right type
        self.convert_outgoing()

        try:
            fptr = open(self._fname, "w")
            pickle.dump(self._contents, fptr)
            fptr.close()
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
            for k,v in self._contents['PLATFORM'].iteritems():
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
        network['NETWORK_VERSION'] = self._version
        network['GPI_VERSION'] = VERSION
        network['HEADER'] = 'This is a GPI Network File'
        network['DATETIME'] = str(time.asctime(time.localtime()))

        # network['PLATFORM']
        network['PLATFORM'] = Specs.table()


class Network_v1(Network_Base):
    '''The first version of the network interface compatible with the released
    GPI-beta.  The file format is pickled list() and dict() objects.  The original 
    released header doesn't necessarily contain a version number so network
    files w/o are assumed to be this version.
    '''

    def __init__(self, fname, contents=None):
        self._version = '1'
        self._fname = fname  # not actually needed since parent did the loading
        self._contents = contents  # a shortcut if the caller did the reading
                                   # also used for storing network data to save

    def load(self):
        # load file contents into memory
        # -since its a pickle file, this as already been done by the parent
        #  when checking the version.
        # -file operations would go here
        if self._contents is None:
            # this shouldn't happen
            log.error('parent didnt unpickle!')
            return

        return self.convert_incoming()

    def save(self):
        # save network contents to a file
        # file operations go here

        # convert to the right type
        self.convert_outgoing()

        try:
            fptr = open(self._fname, "w")
            pickle.dump(self._contents, fptr)
            fptr.close()
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
            msg += '\tassumed net-version: '+str(self._version)+'\n'

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
        network['NETWORK_VERSION'] = self._version
        network['GPI_VERSION'] = VERSION
        network['HEADER'] = 'This is a GPI Network File'


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

    def determine_version(self, fname):
        # check the file format for version and format info
        # -loading is the only way to check if its pickled, so just return
        # the unpickled contents along with the version.  In the future, if
        # pickle is no longer used, then the other format will be checked
        # first, then pickle as a backup.
        try:
            fptr = open(fname, "r")
            contents = pickle.load(fptr)
            fptr.close()
        except:
            contents = None
            log.error('Network file \''+str(fname)+'\' cannot be read. \n' + \
                    '\tIt is either corrupted, permissions are not set, or it contains serialized objects that are version specific (OS or PyQt).')
            log.error(traceback.format_exc())
            return 'UNREADABLE'

        # check for dictionary structure
        if not isinstance(contents, dict):
            log.error("No description dictionary found.  This is probably not a GPI network file.")
            return 'UNREADABLE'

        # check the version
        if 'NETWORK_VERSION' in contents:
            version = contents['NETWORK_VERSION']
        else:
            # assume pre-version compat
            version = '1'

        # This is a shortcut for the pickling format since the only test is to
        # actually read all the data in.  The footprint for this function should
        # be to return the version only.  Future formats will probably have a
        # header section that is easier to read as a separate step.
        self._unpickled_contents = contents


        if version != self._latest_net_version:
            log.warn('This network was saved in an older format, please re-save this network.')

        return version

    def loadNetworkFromFile(self, fname):
        # Used with drops, command-line input, and dialog input

        # check for valid filename
        if not os.path.isfile(fname):
            log.error("\'" + str(fname) + "\' is not a valid filename, skipping.")
            return

        # determine network format obj type by version and load contents
        # TODO: make this automatically choose the right loader object
        ver = self.determine_version(fname)
        if ver == self._latest_net_version:
            net = self._latest_net_class(fname, contents=self._unpickled_contents)
        elif hasattr(sys.modules[__name__], 'Network_v'+ver):
            net = getattr(sys.modules[__name__], 'Network_v'+ver)(fname, contents=self._unpickled_contents)
        else:
            log.error('Network version cannot be determined, skipping.')
            return

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
        start_path = os.path.expanduser('~/')
        log.info("File browser start path: " + start_path)

        dia = QtGui.QFileDialog.getOpenFileName(self._parent,
                                                'Open Session (*.net)',
                                                start_path,
                                                filter='GPI network (*.net)')
        fname = str(dia)

        return self.loadNetworkFromFile(fname)


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

        dia = QtGui.QFileDialog.getSaveFileName(self._parent,
                                                'Save Session (*.net)',
                                                os.path.expanduser('~/'),
                                                filter='GPI network (*.net)')
        fname = str(dia)

        # check for user pressing the cancel button
        if fname == '':
            log.info("Save was cancelled.")
            return

        self.saveNetworkToFile(fname, network)

