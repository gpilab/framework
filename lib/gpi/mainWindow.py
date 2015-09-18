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


import sys
import time
import logging
import subprocess


# gpi
from gpi import QtCore, QtGui, VERSION, RELEASE_DATE
from .config import Config
from .console import Tee
from .canvasGraph import GraphWidget
from .cmd import Commands
from .defines import LOGO_PATH, GPI_DOCS_DIR
from . import logger
from .logger import manager
from .widgets import DisplayBox, TextBox, TextEdit
from .sysspecs import Specs

# start logger for this module
log = manager.getLogger(__name__)


class MainCanvas(QtGui.QMainWindow):
    """Implements the canvas QWidgets, contains the main menus and provides
    user settings via menu or rc file.
    """

    def __init__(self):
        super(MainCanvas, self).__init__()

        # useful for tracking number of file handles
        #self._report = QtCore.QTimer()
        #self._report.setInterval(1000)
        #self._report.timeout.connect(Specs.numOpenFiles)
        #self._report.start()

        # A statusbar widget
        self._statusLabel = QtGui.QLabel()

        # for copying between canvases
        self._copybuffer = None

        # TAB WIDGET
        self.tabs = QtGui.QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setTabPosition(QtGui.QTabWidget.North)
        self.tabs.tabCloseRequested.connect(self.closeCanvasTab)
        self.tabs.currentChanged.connect(self.tabChange)
        self.tabs.setMovable(True)
        self.setCentralWidget(self.tabs)
        self.tabs.show()

        # ADD TAB BUTTON
        self.addbutton = QtGui.QPushButton('+')
        self.addbutton.clicked[bool].connect(self.addNewCanvasTab)
        self.tabs.setCornerWidget(self.addbutton)

        # ADD CANVAS TABS
        self._canvasCnt = 1
        newGraph = GraphWidget("Canvas 1", self)
        newGraph._curState.connect(self.updateCanvasStatus)
        self.tabs.addTab(newGraph, "Canvas 1")

        # possible names for this project
        if (time.localtime().tm_mon == 4) and (time.localtime().tm_mday == 1):
            titleList = []
            titleList += ['Master Control Processor (MCP)']
            titleList += ['Code Flow GPI']
            titleList += ['Code Shepherd']
            titleList += ['Source Flow']
            titleList += ['Algorithm Processing Network (APN)']
            titleList += ['Visual Algorithm Processor (VAP)']
            titleList += ['Data-Analysing Robot Youth Lifeform (D.A.R.Y.L.)']
            titleList += ['Heuristically-programmed ALgorithmic computer (H.A.L.)']
            titleList += ['Johnny Five']
            titleList += ['Visual Programming Paradigm (Vpp)']
            titleList += ['Graphical Prototyping Platform (Gpp)']
            titleList += ['Node Commander (GPI)']
            titleList += ['Algorithm Dominator (GPI)']
            titleList += ['ProtoWizard (GPI)']
            titleList += ['Algorithm Maestro (GPI)']
            titleList += ['Node Guru (GPI)']
            titleList += ['Process Master (GPI)']
            titleList += ['Prototype Expert (GPI)']
            titleList += ['Algorithm Assemblage (GPI)']
            titleList += ['High Performance Algorithm Collider (GPI)']
            titleList += ['Cluster Flow (GPI)']
            titleList += ['Mothra (GPI)']
            titleList += ['Assimilator (GPI)']
            titleList += ['Algorithm Integrator (GPI)']
            titleList += ['Method Mapper (GPI)']
            titleList += ['Method Master (GPI)']
            titleList += ['Vfunc (Visual Functor)']

            from random import choice
            self.setWindowTitle(choice(titleList))

        else:
            self.setWindowTitle('Graphical Programming Interface (GPI)')

        # system tray icon
        #from .defines import ICON_PATH
        #self._gpiIcon = QtGui.QIcon(ICON_PATH)
        #self._trayicon = QtGui.QSystemTrayIcon(self._gpiIcon, parent=self)
        #self._trayicon.show()

        # don't bother with the menus if the gui is not up
        if not Commands.noGUI():
            self.createMenus()

            best_style = None
            if 'Macintosh (aqua)' in list(QtGui.QStyleFactory.keys()):
                log.debug("Choosing Mac aqua style.")
                best_style = 'Macintosh (aqua)'
            elif 'Cleanlooks' in list(QtGui.QStyleFactory.keys()):
                log.debug("Choosing Cleanlooks style.")
                best_style = 'Cleanlooks'
            if best_style:
                QtGui.QApplication.setStyle(QtGui.QStyleFactory.create(best_style))
                QtGui.QApplication.setPalette(
                    QtGui.QApplication.style().standardPalette())

            # Status Bar
            message = "A context menu is available by right-clicking"
            self.statusBar().addPermanentWidget(self._statusLabel)
            self.statusBar().showMessage(message)

            self.updateCanvasStatus()

    def setStatusTip(self, msg):
        self.statusBar().showMessage(msg)

    def updateCanvasStatus(self, curState=None):
        '''Modifies the QLabel portion of main window's statusBar.
        Shows the current state of the focused canvas.
        '''
        if curState is None:
            if self.tabs.currentWidget():
                curState = self.tabs.currentWidget().getCurStateSig()
            else:
                return  # Likely GPI is being closed.

        # update the canvas only if the supplied curState is also from the
        # current canvas -this needs to be redone 
        graph = self.tabs.currentWidget()
        if graph.title() == curState['title']:

            msg = curState['title']+": "+curState['msg']  # base message
            if 'walltime' in curState:
                msg += ' (Elapsed: '+ str(curState['walltime']) +')'
            self._statusLabel.setText(msg)  # quickly show this incase mem calc is too long

            # only do this calc if in Idle
            if curState['msg'] == 'Idle':

                # calculate the port-memory usage of the graph
                pmem = graph.totalPortMem()
                if pmem > 0:
                    msg += ' ['+graph.totalPortMem_disp(pmem)

                    if Specs.TOTAL_PHYMEM() == 0:
                        pct_physmem = ''
                        msg += pct_physmem
                    else:
                        pct_physmem = ', %.*f%s RAM' % (1, float(
                            100.0 * pmem/ Specs.TOTAL_PHYMEM()), '%')
                        msg += pct_physmem

                    msg += ']'

                    self._statusLabel.setText(msg)

    def updateNodeStatus(self, txt):
        '''Modifies the QLabel portion of main window's statusBar.
        A node's status can be updated textually by either naming steps,
        showing step #/total, or with percentages.
        '''
        self._statusLabel.setText(txt)

    def quitConfirmed(self):
        '''Make sure an accidental quit doesn't ruin the user's day.
        '''
        reply = QtGui.QMessageBox.question(self, 'Message',
                    "Quit without saving?", QtGui.QMessageBox.Yes | 
                        QtGui.QMessageBox.No, QtGui.QMessageBox.No)

        if reply == QtGui.QMessageBox.Yes:
            return True
        else:
            return False

    def addNewCanvasTab(self):
        '''Push a new GraphWidget into the tabbar.
        '''
        self._canvasCnt += 1
        title = "Canvas "+str(self._canvasCnt)
        newGraph = GraphWidget(title, self)
        newGraph._curState.connect(self.updateCanvasStatus)
        self.tabs.addTab(newGraph, title)
        self.tabs.setCurrentIndex(self.tabs.count()-1)

    def tabChange(self, index):
        log.debug("tabChange: "+str(index))
        self.updateCanvasStatus()

    def closeEvent(self, event):
        '''close all graphs before shutting down.
        '''
        if not self.quitConfirmed():
            event.ignore()
            return

        while self.tabs.count():
            self.tabs.widget(0).close()
            self.tabs.removeTab(0)
        event.accept()

    def closeCanvasTab(self, index):
        '''Leave at least one tab open.
        '''
        if self.tabs.count() == 1:
            return

        # delete all nodes before closeing by calling the close procedure
        if self.tabs.widget(index).closeGraphWithDialog():
            self.tabs.removeTab(index)

    def console(self):
        log.debug("MainCanvas(): console()")
        self.txtbox = TextEdit('Console')

        # Redirect stdio
        sys.stdout = Tee(sys.stdout)
        sys.stderr = Tee(sys.stderr)

        # NOTE: this is only good for QThread NOT Multiprocess.
        sys.stdout.newStreamTxt.connect(self.consoleWrite)
        sys.stderr.newStreamTxt.connect(self.consoleWrite)

        # set layout
        wdgvbox = QtGui.QVBoxLayout()
        wdgvbox.addWidget(self.txtbox)

        # set master widget
        self.consoleWdg = QtGui.QWidget()
        self.consoleWdg.setLayout(wdgvbox)
        self.consoleWdg.show()
        self.consoleWdg.raise_()

    def consoleWrite(self, m):
        self.txtbox.wdg.moveCursor(QtGui.QTextCursor.End)
        self.txtbox.wdg.insertPlainText(m)

    def about(self):
        # Display
        image = QtGui.QImage(LOGO_PATH)
        dispbox = DisplayBox('')
        dispbox.set_pixmap(QtGui.QPixmap.fromImage(image))
        dispbox.set_scale(0.157)
        dispbox.set_interp(True)

        # Text
        tab = '&nbsp;&nbsp;&nbsp;&nbsp;'
        txt = '<center><font size=4><b>Graphical Programming Interface (GPI)</b></font><br><b><a href=http://gpilab.com>gpilab.com</a></b><br><br>' +\
              'Nicholas Zwart<br>Barrow Neurological Institute<br>Phoenix, Arizona' +\
              '<br><br>' +\
              tab + 'Release: '+ str(VERSION) + ' (' + str(RELEASE_DATE) +')' +\
              '<p>'+\
              'GPI is a graphical development environment designed for rapid prototyping '+\
              'of numeric algorithms.'+\
              '</p>'+\
              '<p>'+\
              'GPI development is sponsored by Philips Healthcare.'+\
              '</p></center>'
        txtbox = TextBox('')
        txtbox.set_val(txt)
        txtbox.set_wordwrap(True)
        txtbox.set_openExternalLinks(True)

        # set layout
        wdgvbox = QtGui.QVBoxLayout()
        wdgvbox.addWidget(dispbox)
        wdgvbox.addWidget(txtbox)
        wdgvbox.setStretch(0, 2)

        # set master widget
        self.aboutWdg = QtGui.QWidget()
        self.aboutWdg.setLayout(wdgvbox)
        # self.aboutWdg.setSizePolicy(QtGui.QSizePolicy.Minimum, \
        #   QtGui.QSizePolicy.Preferred)
        # self.aboutWdg.setMaximumWidth(420)
        self.aboutWdg.show()
        self.aboutWdg.raise_()
        log.debug(str(dispbox.sizeHint()))

    def generateConfigFile(self):
        # a place for a user dialog if need be
        log.debug("generateConfigFile(): called")
        Config.generateConfigFile()

        #reply = QtGui.QMessageBox.question(self, 'Message',
        #                                   "Overwrite Existing" +
        #                                   " Configuration File (" +
        #                                   self._configFileName + ")?",
        #                                   QtGui.QMessageBox.Yes |
        #                                   QtGui.QMessageBox.No,
        #                                   QtGui.QMessageBox.No)
        #if reply == QtGui.QMessageBox.No:
        #    log.info("generateConfigFile(): aborted.")
        #    return

    def generateUserLib(self):
        log.debug("generateUserLib(): called")
        Config.generateUserLib()
        graph = self.tabs.currentWidget()
        graph.rescanLibrary()

    def createNewNode(self):
        log.debug("createNewNode(): called")
        graph = self.tabs.currentWidget()
        graph.getLibrary().showNewNodeListWindow()

    def rescanKnownLibs(self):
        log.debug("Scanning LIB_DIRS for new nodes and libs.")
        graph = self.tabs.currentWidget()
        graph.rescanLibrary()

    def createMenus(self):

        # STYLE
        #self.styleMenu = QtGui.QMenu("&Style", self)
        #ag = QtGui.QActionGroup(self.styleMenu, exclusive=True)
        #for s in QtGui.QStyleFactory.keys():  # get menu items based on keys
        #    a = ag.addAction(QtGui.QAction(s, self.styleMenu, checkable=True))
        #    self.styleMenu.addAction(a)
        #ag.selected.connect(self.changeStyle)
        #self.menuBar().addMenu(self.styleMenu)

        # FILE
        self.fileMenu = QtGui.QMenu("&File", self)
        fileMenu_newTab = QtGui.QAction("New Tab", self, shortcut="Ctrl+T", triggered=self.addNewCanvasTab)
        self.fileMenu.addAction(fileMenu_newTab)
        self.fileMenu.addAction("Create New Node", self.createNewNode)
        self.menuBar().addMenu(self.fileMenu)

        # CONFIG
        self.configMenu = QtGui.QMenu("&Config", self)
        self.configMenu.addAction("Generate Config File (" +
                                  str(Config.configFilePath()) + ")",
                                  self.generateConfigFile)
        self.configMenu.addAction("Generate User Library (" +
                                  str(Config.userLibPath()) + ")",
                                  self.generateUserLib)
        self.configMenu.addAction("Scan For New Nodes",
                                  self.rescanKnownLibs)

        #self.configMenu.addAction("Rescan Config File (" +
        #                          str(Config.configFilePath()) + ")",
        #                          Config.loadConfigFile)
        self.menuBar().addMenu(self.configMenu)

        # DEBUG
        self.debugMenu = QtGui.QMenu("&Debug")
        ag = QtGui.QActionGroup(self.debugMenu, exclusive=False)

        ## logger output sub-menu
        self.loggerMenu = self.debugMenu.addMenu("Logger Level")
        self._loglevel_debug_act = QtGui.QAction("Debug", self, checkable=True,
                triggered=lambda: self.setLoggerLevel(logging.DEBUG))
        self._loglevel_info_act = QtGui.QAction("Info", self, checkable=True,
                triggered=lambda: self.setLoggerLevel(logging.INFO))

        self._loglevel_node_act = QtGui.QAction("Node", self, checkable=True,
                triggered=lambda: self.setLoggerLevel(logger.GPINODE))

        self._loglevel_warn_act = QtGui.QAction("Warn", self, checkable=True,
                triggered=lambda: self.setLoggerLevel(logging.WARNING))
        self._loglevel_error_act = QtGui.QAction("Error", self, checkable=True,
                triggered=lambda: self.setLoggerLevel(logging.ERROR))
        self._loglevel_critical_act = QtGui.QAction("Critical", self, checkable=True,
                triggered=lambda: self.setLoggerLevel(logging.CRITICAL))
        self.loggerMenuGroup = QtGui.QActionGroup(self)
        self.loggerMenuGroup.addAction(self._loglevel_debug_act)
        self.loggerMenuGroup.addAction(self._loglevel_info_act)
        self.loggerMenuGroup.addAction(self._loglevel_node_act)
        self.loggerMenuGroup.addAction(self._loglevel_warn_act)
        self.loggerMenuGroup.addAction(self._loglevel_error_act)
        self.loggerMenuGroup.addAction(self._loglevel_critical_act)
        self.loggerMenu.addAction(self._loglevel_debug_act)
        self.loggerMenu.addAction(self._loglevel_info_act)
        self.loggerMenu.addAction(self._loglevel_node_act)
        self.loggerMenu.addAction(self._loglevel_warn_act)
        self.loggerMenu.addAction(self._loglevel_error_act)
        self.loggerMenu.addAction(self._loglevel_critical_act)

        # initialize the log level -default
        if Commands.logLevel():
            #self._loglevel_warn_act.setChecked(True)
            self.setLoggerLevel(Commands.logLevel())
            self.setLoggerLevelMenuCheckbox(Commands.logLevel())
        else:
            self._loglevel_warn_act.setChecked(True)
            self.setLoggerLevel(logging.WARNING)

        # console submenu
        #a = ag.addAction(QtGui.QAction("Console", self.debugMenu,
        #        checkable=False))
        #self.connect(a, QtCore.SIGNAL("triggered()"), self.console)
        #self.debugMenu.addAction(a)

        #a = ag.addAction(QtGui.QAction("Debug Info", self.debugMenu, checkable=True))
        #self.debugMenu.addAction(a)
        #ag.selected.connect(self.debugOptions)

        # DEBUG
        self.debugMenu.addAction("Print sys.paths", self.printSysPath)
        self.debugMenu.addAction("Print sys.modules", self.printSysModules)
        self.menuBar().addMenu(self.debugMenu)

        # WINDOW
        self.windowMenu = QtGui.QMenu("Window", self)
        self.windowMenu_closeAct = QtGui.QAction("Close Node Menus (Current Tab)", self, shortcut="Ctrl+X", triggered=self.closeAllNodeMenus)
        self.windowMenu.addAction(self.windowMenu_closeAct)
        self.menuBar().addMenu(self.windowMenu)

        # HELP
        self.helpMenu = QtGui.QMenu("&Help", self)
        aboutAction = self.helpMenu.addAction("&About")
        self.connect(aboutAction, QtCore.SIGNAL("triggered()"), self.about)
        self.helpMenu_openDocs = QtGui.QAction("Documentation", self, triggered=self.openWebsite)
        self.helpMenu.addAction(self.helpMenu_openDocs)
        self.helpMenu_openDocs = QtGui.QAction("Examples", self, triggered=self.openExamplesFolder)
        self.helpMenu.addAction(self.helpMenu_openDocs)
        self.menuBar().addMenu(self.helpMenu)

    # TODO: move this and others like it to a common help-object that can errorcheck.
    def openWebsite(self):
        if not QtGui.QDesktopServices.openUrl(QtCore.QUrl('http://docs.gpilab.com')):
            QtGui.QMessageBox.information(self, 'Documentation',"Documentation can be found at\nhttp://docs.gpilab.com", QtGui.QMessageBox.Close)
    
    def openDocsFolder(self):

        if Specs.inOSX():
            subprocess.Popen("open " + GPI_DOCS_DIR, shell=True)
        elif Specs.inLinux():
            subprocess.Popen("xdg-open " + GPI_DOCS_DIR, shell=True)

        log.dialog("GPI documentation can be found in: "+GPI_DOCS_DIR)

    def openExamplesFolder(self):

        if Specs.inOSX():
            subprocess.Popen("open " + GPI_DOCS_DIR+'/Examples', shell=True)
        elif Specs.inLinux():
            subprocess.Popen("xdg-open " + GPI_DOCS_DIR+'/Examples', shell=True)

        log.dialog("GPI examples can be found in: "+GPI_DOCS_DIR+'/Examples')

    def closeAllNodeMenus(self):
        self.tabs.currentWidget().closeAllNodeMenus()

    def setLoggerLevel(self, lev):
        manager.setLevel(lev)

    def setLoggerLevelMenuCheckbox(self, lev):
        if lev == logging.DEBUG:
            self._loglevel_debug_act.setChecked(True)
        if lev == logging.INFO:
            self._loglevel_info_act.setChecked(True)
        if lev == logger.GPINODE:
            self._loglevel_node_act.setChecked(True)
        if lev == logging.WARNING:
            self._loglevel_warn_act.setChecked(True)
        if lev == logging.ERROR:
            self._loglevel_error_act.setChecked(True)
        if lev == logging.CRITICAL:
            self._loglevel_critical_act.setChecked(True)

    def printSysPath(self):
        print("Current module search path (sys.path):")
        for path in sys.path:
            print(path)

    def printSysModules(self):
        print("Current modules loaded (sys.modules):")
        for k in sorted(sys.modules.keys()):
            v = sys.modules[k]
            print((k + " : " + str(v)))
            if False:
                if k.lower().count('spiral'):
                    print(("key: " + k + ", " + str(v)))
                elif str(v).lower().count('spiral'):
                    print(("key: " + k + ", " + str(v)))

    def changeStyle(self, action):
        # UI style
        log.debug("MainCanvas(): ChangeStyle called:")
        log.debug(str(action.text()))
        QtGui.QApplication.setStyle(QtGui.QStyleFactory.create(action.text()))
        QtGui.QApplication.setPalette(
            QtGui.QApplication.style().standardPalette())

    def debugOptions(self, action):
        if action.text() == "Debug Info":
            self.printSysPath()
        #if action.text() == "Console":
        #    print "MainCanvas(): Console"


