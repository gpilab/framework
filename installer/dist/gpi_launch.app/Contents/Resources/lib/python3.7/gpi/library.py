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

# Logic for searching for nodes and networks within the library path and
# generating a mouse menu.
#
# TODO: possibly make the library a global for all canvases


import os
import shutil
import subprocess
from functools import partial

# gpi
from gpi import QtCore, QtGui, QtWidgets
from .config import Config
from .defaultTypes import GPITYPE_PASS
from .defines import isWidget, isGPIType, isExternalNode
from .catalog import Catalog, CatalogObj
from .defaultTypes import GPIDefaultType
from .defines import isGPIModFile, isGPITypeFile, isGPINetworkFile, GPI_PYMOD_PRE_EXT
from .loader import loadMod, PKGroot, appendSysPath
from .node import Node
from .sysspecs import Specs

from .logger import manager

# start logger for this module
log = manager.getLogger(__name__)

NOPATH_MESSAGE = "<em>No library selected...</em>"

class SearchMenu(QtWidgets.QMenu):
    '''A menu class that leaves keyboard focus with its parent.'''
    def __init__(self, menuPos, parent=None):
        super().__init__(parent=parent)
        self._menuPos = menuPos
        self._parent = parent

    def show(self):
        self.popup(self._menuPos)
        self._parent.grabKeyboard()

    def close(self):
        super().close()
        self._parent.releaseKeyboard()

class NodeCatalogItem(CatalogObj):
    '''A single entry to a Node database. For information such as library,
    path, type, etc...
    '''

    def __init__(self, fullpath):

        dn = os.path.dirname
        bn = os.path.basename

        self.fullpath = fullpath

        # determine if there is an editable code file for direct node edit access
        self.editable_path = None
        epath, ext = os.path.splitext(fullpath)
        epath += '.py'
        if os.path.isfile(epath):
            self.editable_path = epath

        # 'SpiralCoords_GPI.py' and path
        fil = bn(fullpath)
        path = dn(fullpath)

        # get module name and lib name
        name, ext = os.path.splitext(fil)  # 'SpiralCoords_GPI' '.py'

        # verify the '_GPI' before the file extension
        self.isNodeFile = False
        if name.endswith(GPI_PYMOD_PRE_EXT):
            self.isNodeFile = True

        name = name.split(GPI_PYMOD_PRE_EXT)[0]  # get node's display name 'SpiralCoords'
        second = bn(path)  # 'GPI' if the GPI dir is used
        third = bn(dn(path))  # 'core' if GPI-dir is NOT used
        lib_path = dn(path)

        # skip the GPI directory name by removing it from path
        if second == 'GPI':
            # 'spiral'
            second = bn(dn(path))
            # 'core'
            third = bn(dn(dn(path)))
            lib_path = dn(dn(path))

        # save node info
        self.name = name
        self.second = second
        self.third = third
        self._lib_path = lib_path
        self.path = path
        self.ext = [ext]

        self.pkg_root = None
        if self.path:
            self.pkg_root = PKGroot(self.path)

        # This is the only element that cannot be duplicated across nodes
        self._id = self.third+'.'+self.second+'.'+self.name
        self.thrd_sec = self.third+'.'+self.second

        # add to sys path in class node module has pkg.module refs
        if self.pkg_root:
            appendSysPath(self.pkg_root)

        # try loading the node module
        self.mod = None
        self.widgetNames = []
        #self.load()

    def key(self):
        return self._id

    def lib(self):
        return self.third

    def lib_path(self):
        return self._lib_path

    def sameLib(self, item):
        return item.lib_path() == self.lib_path()

    def libWarn(self, item):
        msg = 'Multiple library paths with the name: \''+str(self.lib())+'\'\n' \
                + 'Paths:\n\t* ' + str(self.lib_path()) +'\n\t  '+ str(item.lib_path()) \
                + '\nNode:\n\t  ' + str(self.key())+' '+str(item.ext)+'\n' \
                + 'Skipping duplicate library...'
        log.warn(msg)

    def find(self, key):
        return (key in self.types)

    def reload(self):
        log.info("reload: "+str(self.fullpath))
        self.load()

    def load(self):

        # clear previous instance
        self.mod = None

        # enforce filename law
        if not self.isNodeFile:
            log.error('Not a valid GPI node filename, skipping. ('+str(self.fullpath)+')')
            return

        # verify that there is a node description
        mod = loadMod(self.fullpath)
        if mod:
            if hasattr(mod, 'ExternalNode'):
                if isExternalNode(getattr(mod, 'ExternalNode')):
                    self.mod = mod
                else:
                    log.error('ExternalNode object found, but it is not a GPI node def. ('+str(self.fullpath)+')')
                    return
            else:
                log.error('No ExternalNode definition found, skipping. ('+str(self.fullpath)+')')
                return
        else:
            log.error('Module not loadable, skipping. ('+str(self.fullpath)+')')
            return

        if self.mod:
            # check if it has widget definitions
            self.widgetNames = []  # re-init list in case of reload
            for name in dir(self.mod):
                if isWidget(getattr(self.mod, name)):
                    self.widgetNames.append(name)

            if len(self.widgetNames):
                log.info(str(self.fullpath)+' contains widget definitions:  '+str(self.widgetNames))

    def valid(self):
        return self.isLoaded() # and self.isNodeFile

    def validExt(self):
        return self.isNodeFile

    def isLoaded(self):
        if self.mod:
            return True
        else:
            return False

    def hasWidgets(self):
        return len(self.widgetNames) > 0

    def getWidget(self, name):
        if name in self.widgetNames:
            return getattr(self.mod, name)

    def appendExt(self, ext):
        self.ext.append(ext)
        self.ext = list(set(self.ext))

    def merge(self, m):

        if not self.sameLib(m):
            self.libWarn(m)
            return

        # this handles collisions between nodes found with the same id
        self.ext += m.ext
        self.ext = list(set(self.ext))

    def description(self):
        # return the node description class
        return self.mod.ExternalNode

    def __str__(self):
        return '< '+self._id+', '+str(self.path)+', '+str(self.ext) +' >'

class NetworkCatalogItem(CatalogObj):
    '''A single database entry to a GPI Network database.
    '''

    def __init__(self, fullpath):

        # TODO: more rigorous file checking (perhaps a magic number).

        dn = os.path.dirname
        bn = os.path.basename

        self.fullpath = fullpath

        # 'SpiralCoords_GPI.net' and path
        fil = bn(fullpath)
        path = dn(fullpath)

        # get module name and lib name
        name, ext = os.path.splitext(fil)  # 'SpiralCoords_GPI' '.net'

        # verify the '_GPI' before the file extension
        # determine whether to install net in the library menu
        self.isNetLibFile = False
        if name.endswith(GPI_PYMOD_PRE_EXT):
            self.isNetLibFile = True

        name = name.split(GPI_PYMOD_PRE_EXT)[0]  # get node's display name 'SpiralCoords'
        second = bn(path)  # 'GPI' if the GPI dir is used
        third = bn(dn(path))  # 'core' if GPI-dir is NOT used

        # skip the GPI directory name by removing it from path
        if second == 'GPI':
            # 'spiral'
            second = bn(dn(path))
            # 'core'
            third = bn(dn(dn(path)))

        # save net info
        self.name = name
        self.second = second
        self.third = third
        self.path = path
        self.ext = ext

        # This is the only element that cannot be duplicated across nodes
        self._id = self.third+'.'+self.second+'.'+self.name
        self.thrd_sec = self.third+'.'+self.second

    def valid(self):
        return isGPINetworkFile(self.fullpath) and self.isNetLibFile

    def key(self):
        return self._id

    def appendExt(self, ext):
        self.ext.append(ext)
        self.ext = list(set(self.ext))

    def merge(self, m):
        # this handles collisions between nodes found with the same id
        self.ext += m.ext
        self.ext = list(set(self.ext))

    def __str__(self):
        return self._id+', '+str(self.path)+', '+str(self.ext)

class GPITYPECatalogItem(CatalogObj):
    '''Object specific to GPITYPE plugins.
    1) input the full path: /path-to-plugin-dir/mytype_GPITYPE.py or .pyc
    2) this will try to verify the path
    3) try to load the python module
    4) failures will be flagged
    '''

    def __init__(self, fullpath):

        if type(fullpath) is not str:
            log.error('GPITYPECatalogItem requires a string argument.')

        self.fullpath = fullpath
        self.name, ext = os.path.splitext(fullpath)
        self.path, self.name = os.path.split(self.name)
        self.ext = [ext]

        # unique name
        self._id = self.path+'/'+self.name

        # try to have python load the module
        self.mod = loadMod(fullpath)

        # Extract the GPITYPES from the module for checking and keep a list of names.
        self.types = []
        for cn in dir(self.mod):
            cls = getattr(self.mod, cn)
            if isGPIType(cls):
                log.info('\t'+fullpath+' has GPITYPE: '+cn)
                self.types.append(cn)

    def valid(self):
        return self.isLoaded()

    def isLoaded(self):
        if self.mod:
            return True
        else:
            return False

    def key(self):
        return self._id

    def appendExt(self, ext):
        self.ext.append(ext)
        self.ext = list(set(self.ext))

    def merge(self, m):
        # this handles collisions between nodes found with the same id
        self.ext += m.ext
        self.ext = list(set(self.ext))

    def __str__(self):
        return self._id+', '+str(self.path)+', '+str(self.ext)

    def hasType(self, key):
        # GPITYPE libraries can hold multiple types. Usually, the type is what
        # is searched for.
        return (key in self.types)

    def type(self, key):
        # return the type object associated with the key name.
        if self.hasType(key):
            return getattr(self.mod, key)()

class Library(object):
    '''Contains all the Node, Network, and GPIType path searching, mouse menu
    generation and indexing for the node library.  The contents of the library
    are loaded at startup (each time) and when the user adds Nodes via drag'n
    drop or menu contexts.
    '''

    def __init__(self, parent):
        self._parent = parent  # must be a Qt parent for signalling
        self._known_GPI_nodes = Catalog()  # list of all modules within each lib
        self._known_GPI_networks = Catalog()  # all networks in each lib
        self._known_GPI_types = Catalog() # all GPI types found in init search
        self.extTypes = dict()
        self._listwdg = None  # for searching node list

        self.generateNewNodeListWindow()

        self._lib_menus = {}  # third level menu (holds second lev list)
        self._lib_second = {}  # second level menu (holds node list)
        self._lib_menu = []  # third level menu list

        self.scanGPIModulesIn_LibraryPath(recursion_depth=3)
        self.generateLibMenus()
        self.generateNewNodeList()

    def showNewNodeListWindow(self):
        self._list_win.show()

    def _get_new_node_name(self):
        fname = self._new_node_name_field.text()
        if fname == "":
            fname = self._new_node_name_field.placeholderText()
        if not fname.endswith(GPI_PYMOD_PRE_EXT + '.py'):
            fname += GPI_PYMOD_PRE_EXT + '.py'
        return fname

    def _createNewNode(self):
        # copy node template to this library, and open it up
        fullpath = self._new_node_path

        new_node_created = False
        if os.path.exists(fullpath):
            log.warn("Didn't create new node at path: " + fullpath +
                     " (file already exists)")
        else:
            try:
                shutil.copyfile(Config.GPI_NEW_NODE_TEMPLATE_FILE,
                                fullpath)
            except OSError as e:
                print(e)
                log.warn("Didn't create new node at path: " + fullpath)
            else:
                log.dialog("New node created at path: " + fullpath)
                new_node_created = True
                self.rescan()

        self._list_win.hide()

        if new_node_created:
            # instantiate our new node on the canvas
            canvas = self._parent
            pos = QtCore.QPoint(0, 0)
            node = self.findNode_byPath(fullpath)
            sig = {'sig': 'load', 'subsig': node, 'pos': pos}
            canvas.addNodeRun(sig)

            # now open the file for editing (stolen from node.py)
            if Specs.inOSX():
                # OSX users set their launchctl associated file prefs
                command = "open \"" + fullpath + "\""
                subprocess.Popen(command, shell=True)
            # Linux users set their editor choice
            # TODO: this should be moved to config
            elif Specs.inLinux():
                editor = 'gedit'
                if os.environ.has_key("EDITOR"):
                    editor = os.environ["EDITOR"]
                command = editor + " \"" + fullpath + "\""
                subprocess.Popen(command, shell=True)
            else:
                log.warn("Quick-Edit unavailable for this OS, aborting...")

    def _setQTLabelElided(self, label, text):
        fm = QtGui.QFontMetrics(label.font())
        width = label.width()
        elided_text = fm.elidedText(text, QtCore.Qt.ElideMiddle, width)
        label.setText(elided_text)

    def _newNodeNameEdited(self):
        new_name = self._get_new_node_name()
        current_path = self._new_node_path
        if current_path != '':
            path, old_name = os.path.split(current_path)
            fullpath = os.path.join(path, new_name)
            self._new_node_path = fullpath
            self._setQTLabelElided(self._new_node_path_field, fullpath)

    # This slot is called whenever a list item is clicked. This is used to
    # update the path and set the enabled/disabled state of the create node
    # button.
    def _listItemClicked(self, item):
        idx, label = self._new_node_list_index
        if idx == 0:
            self._create_button.setDisabled(True)
            self._new_node_path_field.setText(NOPATH_MESSAGE)
            self._new_node_path = ''
        elif idx == 1:
            if item.text() == '..':
                self._create_button.setDisabled(True)
                self._new_node_path_field.setText(NOPATH_MESSAGE)
                self._new_node_path = ''
            else:
                for k in self._known_GPI_nodes.keys():
                    node = self._known_GPI_nodes.get(k)
                    if node.thrd_sec == '.'.join((label, item.text())):
                        fullpath = os.path.join(node.path, self._get_new_node_name())
                        self._new_node_path = fullpath
                        self._setQTLabelElided(self._new_node_path_field, fullpath)
                        self._create_button.setEnabled(True)
                        break
        elif idx == 2:
            self._create_button.setEnabled(True)

    # This slot is called whenever a list item is double-clicked. This is used
    # for navigation of the library lists when creating a new node.
    def _listItemDoubleClicked(self, item):
        new_node_created = False

        idx, label = self._new_node_list_index
        if idx == 0:
            self.generateNewNodeList(item.text())
        elif item.text() == '..':
            new_index = label.split('.')
            if idx == 1:
                self.generateNewNodeList()
            else:
                self.generateNewNodeList('.'.join(new_index[:idx-1]))
        elif idx < 2:
            new_index = '.'.join((label, item.text()))
            self.generateNewNodeList(new_index)

    def scanForNewNodes(self):
        log.dialog("Scanning for newly created modules and libraries...")
        self.scanGPIModulesIn_LibraryPath(recursion_depth=3)
        self.regenerateLibMenus()
        log.dialog("Finished rescanning.")

    def rescan(self):

        # remove all libs for a fresh rescan
        self._known_GPI_nodes = Catalog()  # list of all modules within each lib
        self._known_GPI_networks = Catalog()  # all networks in each lib
        self._known_GPI_types = Catalog() # all GPI types found in init search
        self.extTypes = dict()

        log.dialog("Rescanning for newly created modules and libraries...")
        self.scanGPIModulesIn_LibraryPath(recursion_depth=3)
        self.regenerateLibMenus()
        self.generateNewNodeList()
        log.dialog("Finished rescanning.")

    def getUserLibsWithPaths(self):
        return None

    def getType(self, key):
        # GPITYPE
        # if requested type was returned, then include a True, else False.

        if key == GPITYPE_PASS:
            return (GPIDefaultType(), True)

        typObj = self._known_GPI_types.intrafind('hasType', key)
        if typObj is None:
            log.info('Requested port-type: \''+str(key)+'\' not found.  Using \'' + str(GPITYPE_PASS) + '\' instead.')
            return (GPIDefaultType(), False)
        else:
            return (typObj.type(key), True)

    def findNode_byName(self, name):
        # expose the catalog's find function
        return self._known_GPI_nodes.find('name', name)

    def findNode_byPath(self, path):
        return self._known_GPI_nodes.find('fullpath', path)

    def findNode_byLibrary(self, name, second, third):
        key = third+'.'+second+'.'+name
        if key in list(self._known_GPI_nodes.keys()):
            return self._known_GPI_nodes.get(key)

    def findNode_byKey(self, key):
        if key in list(self._known_GPI_nodes.keys()):
            return self._known_GPI_nodes.get(key)

    def findNode_byClosestMatch(self, name, wdg_port_names):
        # find all nodes with the same name, then try to match as many widget
        # and port names from the list.
        log.debug('Find node by closest match: '+str(name))

        byname = self._known_GPI_nodes.list('name', name)

        if byname is None:
            log.warn('No node found with name \''+str(name)+'\'')
            return None

        if len(byname) == 0:
            log.warn(str(name) + ' node not found.')
            return None

        if len(byname) == 1:
            log.info('Found one match for '+str(name))
            return byname[0]

        any_cnt = []
        exact_cnt = []
        for item in byname:

            # need an instance to check the node's widget and port names
            cur_names = Node(None, nodeCatItem=item).getWidgetAndPortNames()

            # try checking for any match type
            cnt = 0
            for wpn in wdg_port_names:
                match = False
                for cn in cur_names:
                    # if one is in the other or the other is in the one
                    if cn.lower().count(wpn.lower()) or wpn.lower().count(cn.lower()):
                        match = True
                if match:
                    cnt += 1
            any_cnt.append(cnt*100.0/len(wdg_port_names))

            # try checking for exact match type
            cnt = 0
            for wpn in wdg_port_names:
                if wpn in cur_names:
                    cnt += 1
            exact_cnt.append(cnt*100.0/len(wdg_port_names))

        msg = 'Find Node: '+str(name)+'\n'
        msg += 'Candidates:\n'
        for item, cpc, epc in zip(byname, any_cnt, exact_cnt):
            msg += '\t'+str(item.fullpath) + ' any: '+str(cpc)+'%, exact: '+str(epc)+'%\n'

        if len(set(exact_cnt)) > 1:
            msg += 'Exact Name Match:\n'

            chosen_item = byname[0]
            chosen_score = exact_cnt[0]
            for item, epc in zip(byname, exact_cnt):
                if chosen_score < epc:
                    chosen_score = epc
                    chosen_item = item

            msg +='\tChosen: ' + str(item.fullpath) + ', MP: ' + str(chosen_score) + '%'
            log.warn(msg)
            return chosen_item

        if len(set(any_cnt)) > 1:
            msg += 'Any Name Match:\n'

            chosen_item = byname[0]
            chosen_score = any_cnt[0]
            for item, epc in zip(byname, any_cnt):
                if chosen_score < epc:
                    chosen_score = epc
                    chosen_item = item

            msg += '\tChosen: ' + str(item.fullpath) + ', MP: ' +str(chosen_score)+'%'
            log.warn(msg)
            return chosen_item

        log.warn(msg)
        log.warn('No node distinction found, choosing first match: '+str(byname[0].fullpath))
        return byname[0]

    def addNode(self, item, check=True):
        if check:
            item.load()
            if not item.valid():
                return -1

        existing = self.findNode_byKey(item.key())
        if not existing:
            self._known_GPI_nodes.append(item)
            return 1
        elif not existing.sameLib(item):
            existing.libWarn(item)
            return -1
        return 0 # already in database

    def listWdg(self):
        return self._listwdg

    def libMenus(self):
        return self._lib_menus

    def libMenu(self):
        return self._lib_menu

    def searchMenu(self, txt, parent, mousemenu):
        # this menu needs to be rebuilt everytime a character changes

        # don't bother if the user just cleared the search
        if len(txt) == 0:
            return

        pos = self._parent.mapToGlobal(self._parent._event_pos + QtCore.QPoint(mousemenu.sizeHint().width(), 0))

        # close any existing search menu and assign the new one
        self.removeSearchPopup()

        searchMenu = SearchMenu(pos, parent=parent)
        self.generateNodeSearchActions(str(txt), searchMenu, mousemenu)

        self._listwdg = searchMenu
        searchMenu.show()

    def removeSearchPopup(self):
        if self._listwdg is not None:
            self._listwdg.close()
            self._listwdg = None

    def addNodeAndCloseMouseMenu(self, s, searchmenu, mousemenu):
        '''Close all menus and related objects.
        NOTE: THIS ORDER MUST BE PRESERVED!!!
        '''
        self.removeSearchPopup()
        mousemenu.close()
        self._parent.activateWindow()
        self._parent.update()
        self._parent.addNodeRun(s)

    def scanGPIModulesIn_LibraryPath(self, recursion_depth=1):
        new_sys_paths = []
        types_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'types')
        for spath in Config.GPI_LIBRARY_PATH + [types_path]:
            path = os.path.realpath(spath)  # remove excess '/'
            if os.path.isdir(path):
                self.scanGPIModules(path, recursion_depth)

        log.info("GPI mods/nets/types found:")
        log.info(str(self._known_GPI_nodes))
        log.info(str(self._known_GPI_networks))
        log.info(str(self._known_GPI_types))
        log.info('number of nodes: '+str(len(self._known_GPI_nodes)))
        log.info('number of networks: '+str(len(self._known_GPI_networks)))
        log.info('number of types: '+str(len(self._known_GPI_types)))

    # TODO: move this and others like it to a common help-object that can errorcheck.
    def openGPIRCHelp(self):
        if not QtGui.QDesktopServices.openUrl(QtCore.QUrl('http://docs.gpilab.com')):
            QtWidgets.QMessageBox.information(self, 'Documentation',"Documentation can be found at\nhttp://docs.gpilab.com", QtWidgets.QMessageBox.Close)

    # http://docs.gpilab.com/Configuration/#configuration-library-directories
    def openLIBDIRSHelp(self):
        if not QtGui.QDesktopServices.openUrl(QtCore.QUrl('http://docs.gpilab.com/Configuration/#configuration-library-directories')):
            QtWidgets.QMessageBox.information(self, 'Documentation',"Documentation can be found at\nhttp://docs.gpilab.com", QtWidgets.QMessageBox.Close)

    def regenerateLibMenus(self):
        self._lib_menus = {}  # third level menu (holds second lev list)
        self._lib_second = {}  # second level menu (holds node list)
        self._lib_menu = []  # third level menu list
        self.generateLibMenus()
        self.generateNewNodeList()

    def generateLibMenus(self):
        # default menu if no libraries are found
        numnodes = len(list(self._known_GPI_nodes.keys()))
        if numnodes == 0:
            self._lib_menus['No Nodes Found'] = QtWidgets.QMenu('No Nodes Found')
            buf = 'Check your ~/.gpirc for the correct LIB_DIRS.'
            act = QtWidgets.QAction(buf, self._parent, triggered = self.openLIBDIRSHelp)
            self._lib_menus['No Nodes Found'].addAction(act)

            for m in sorted(list(self._lib_menus.keys()), key=lambda x: x.lower()):
                mm = self._lib_menus[m]
                mm.setTearOffEnabled(False)
                self._lib_menu.append(mm)

            return

        # NODE MENU
        # setup libs using node id. ex: core.mathematics.sum
        # the ids of
        for k in sorted(self._known_GPI_nodes.keys(), key=lambda x: x.lower()):
            node = self._known_GPI_nodes.get(k)
            if node.third not in self._lib_menus:
                #self._lib_menus[node.third] = QtWidgets.QMenu(node.third.capitalize())
                self._lib_menus[node.third] = QtWidgets.QMenu(node.third)
                self._lib_menus[node.third].setTearOffEnabled(True)

            if node.thrd_sec not in self._lib_second:
                self._lib_second[node.thrd_sec] = QtWidgets.QMenu(node.second)
                self._lib_second[node.thrd_sec].setTearOffEnabled(True)
                ma = self._lib_menus[node.third].addMenu(self._lib_second[node.thrd_sec])

            sm = self._lib_second[node.thrd_sec]

            # TODO: try setting up hotkeys/shortcuts for specific nodes
            a = QtWidgets.QAction(node.name, self._parent, statusTip="Click to instantiate the \'"+str(node.name)+"\' node.")
            s = {'subsig': node}
            a.triggered.connect(partial(self._parent.addNodeRun, sig=s))
            sm.addAction(a)

        # NETWORK MENU
        for sm in list(self._lib_second.values()):
            sm.addSeparator()

        for k in sorted(list(self._known_GPI_networks.keys()), key=lambda x: x.lower()):
            net = self._known_GPI_networks.get(k)
            if net.third not in self._lib_menus:
                #self._lib_menus[net.third] = QtWidgets.QMenu(net.third.capitalize())
                self._lib_menus[net.third] = QtWidgets.QMenu(net.third)
                self._lib_menus[net.third].setTearOffEnabled(True)

            if net.thrd_sec not in self._lib_second:
                self._lib_second[net.thrd_sec] = QtWidgets.QMenu(net.second)
                self._lib_second[net.thrd_sec].setTearOffEnabled(True)
                self._lib_menus[net.third].addMenu(self._lib_second[node.thrd_sec])

            sm = self._lib_second[net.thrd_sec]
            a = QtWidgets.QAction(net.name + ' (net)', self._parent, statusTip="Click to instantiate the \'"+str(net.name)+"\' network.")
            s = {'sig': 'load', 'subsig': 'net', 'path': net.fullpath}
            a.triggered.connect(partial(self._parent.addNodeRun, sig=s))
            sm.addAction(a)

        for m in sorted(list(self._lib_menus.keys()), key=lambda x: x.lower()):
            mm = self._lib_menus[m]
            mm.setTearOffEnabled(True)
            self._lib_menu.append(mm)

    # each time this is called it goes through all the nodes to populate the
    # list
    def generateNewNodeList(self, top_lib=None):
        list_items = set()
        new_node_path = ''
        for k in self._known_GPI_nodes.keys():
            node = self._known_GPI_nodes.get(k)
            if top_lib is None:
                list_items.add(node.third)
            elif node.third == top_lib:
                list_items.add(node.second)
            elif node.thrd_sec == top_lib:
                list_items.add(node.name)
                if new_node_path == '':
                    new_node_path = os.path.join(node.path,
                                                 self._get_new_node_name())

        self._new_node_path = new_node_path
        if self._new_node_path == '':
            self._new_node_path_field.setText(NOPATH_MESSAGE)
        else:
            self._setQTLabelElided(self._new_node_path_field, new_node_path)

        self._new_node_list.clear()
        if top_lib is not None:
            self._new_node_list.addItem("..")

        [self._new_node_list.addItem(item) for item in list_items]

        if top_lib is None:
            idx = 0
            list_label = "GPI Libraries"
        else:
            new_label = top_lib.split('.')
            idx = len(new_label)
            list_label = u' \u2799 '.join(["GPI Libraries"] + new_label)

        self._list_label.setText(list_label)
        self._new_node_list_index = (idx, top_lib)

        if idx > 1:
            self._create_button.setEnabled(True)
        else:
            self._create_button.setDisabled(True)

    # generate the new node list window
    def generateNewNodeListWindow(self):
        # the New Node window
        self._list_win = QtWidgets.QWidget()
        self._list_win.setFixedWidth(500)
        self._new_node_list = QtWidgets.QListWidget(self._list_win)

        self._create_button = QtWidgets.QPushButton("Create Node", self._list_win)
        self._create_button.setDisabled(True)
        self._create_button.clicked.connect(self._createNewNode)
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch(1)
        button_layout.addWidget(self._create_button)

        self._new_node_list.itemDoubleClicked.connect(self._listItemDoubleClicked)
        self._new_node_list.itemClicked.connect(self._listItemClicked)

        self._list_label = QtWidgets.QLabel("GPI Libraries", self._list_win)

        node_name_layout = QtWidgets.QHBoxLayout()
        new_node_name_label = QtWidgets.QLabel("Name:", self._list_win)
        self._new_node_name_field = QtWidgets.QLineEdit(self._list_win)
        self._new_node_name_field.setPlaceholderText("NewNodeName_GPI.py")
        self._new_node_name_field.textChanged.connect(self._newNodeNameEdited)
        node_name_layout.addWidget(new_node_name_label)
        node_name_layout.addWidget(self._new_node_name_field)

        new_node_path_label = QtWidgets.QLabel("Path:", self._list_win)
        self._new_node_path = ''
        self._new_node_path_field = QtWidgets.QLabel(NOPATH_MESSAGE, self._list_win)
        self._new_node_path_field.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        path_layout = QtWidgets.QHBoxLayout()
        path_layout.addWidget(new_node_path_label)
        path_layout.addWidget(self._new_node_path_field)

        list_layout = QtWidgets.QVBoxLayout()
        list_layout.addWidget(self._list_label)
        list_layout.addWidget(self._new_node_list)
        list_layout.addLayout(node_name_layout)
        list_layout.addLayout(path_layout)
        list_layout.addLayout(button_layout)
        self._list_win.setLayout(list_layout)

    def scanGPIModules(self, ipath, recursion_depth=1):
        ocnt = ipath.count('/')
        for path, dn, fn in os.walk(ipath):
            # TODO: instead of checking for hidden svn dirs, just choose any hidden dir
            if (path.count('/') - ocnt <= recursion_depth) and not path.count('/.svn'):
                for fil in os.listdir(path):

                    fullpath = path+'/'+fil

                    if isGPIModFile(fullpath):

                        item = NodeCatalogItem(fullpath)
                        if Config.IMPORT_CHECK:
                            item.load()  # load check
                            if item.valid():
                                self._known_GPI_nodes.append(item)
                        else:
                            self._known_GPI_nodes.append(item)

                    elif isGPITypeFile(fullpath):

                        item = GPITYPECatalogItem(fullpath)
                        if item.valid():
                            self._known_GPI_types.append(item)

                    elif isGPINetworkFile(fullpath):

                        item = NetworkCatalogItem(fullpath)
                        if item.valid():
                            self._known_GPI_networks.append(item)

    def generateNodeSearchActions(self, txt, menu, mousemenu):

        # user query
        txt = txt.lower()

        # NODE SEARCH
        # search using txt string
        sortedMods = []
        if len(txt) > 2:  # match anywhere in name
            for node in list(self._known_GPI_nodes.values()):
                if node.name.lower().find(txt) > -1:
                    sortedMods.append(node)
        else:  # only match from start of name
            for node in list(self._known_GPI_nodes.values()):
                if node.name.lower().startswith(txt):
                    sortedMods.append(node)
        sortedMods = sorted(sortedMods, key=lambda x: x.name.lower())

        # create actions and add them to the menu
        for node in sortedMods:

            a = QtWidgets.QAction(node.name+" (" + node.thrd_sec + ")", self._parent, statusTip="Click to instantiate the \'"+str(node.name)+"\' node.")
            s = {'subsig': node}

            # The way this signal is connected, the
            # s-dict is fully copied which is required to pass the correct
            # mod name.
            a.triggered.connect(partial(self.addNodeAndCloseMouseMenu,
                                        s=s, searchmenu=menu,
                                        mousemenu=mousemenu))
            menu.addAction(a)


        # NETWORK SEARCH
        # search using txt string
        if True:
            sortedMods= []
            if len(txt) > 2:
                for net in list(self._known_GPI_networks.values()):
                    if net.name.lower().find(txt) > -1:
                        sortedMods.append(net)

            else:
                for net in list(self._known_GPI_networks.values()):
                    if net.name.lower().startswith(txt):
                        sortedMods.append(net)
            sortedMods = sorted(sortedMods, key=lambda x: x.name.lower())

            if len(sortedMods):
                menu.addSeparator()

            # create actions and add them to the menu
            for net in sortedMods:
                a = QtWidgets.QAction(net.name+" (net) (" + net.thrd_sec + ")", self._parent, statusTip="Click to instantiate the \'"+str(net.name)+"\' network.")
                s = {'sig': 'load', 'subsig': 'net', 'path': net.fullpath}
                a.triggered.connect(partial(self.addNodeAndCloseMouseMenu,
                                            s=s, searchmenu=menu,
                                            mousemenu=mousemenu))
                menu.addAction(a)
