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
import sys
import psutil
import time
import logging
import subprocess


# gpi
from gpi import QtCore, QtGui, QtWidgets, VERSION, RELEASE_DATE
from .config import Config
from .theme import apply_gpi_theme, win32_set_dark_titlebar

from .console import Tee
from .canvasGraph import GraphWidget
from .cmd import Commands
from .defines import LOGO_PATH, GPI_DOCS_DIR
from . import logger
from .logger import manager
from .widgets import DisplayBox, TextBox, TextEdit
from .sysspecs import Specs
from .shortcuts import Shortcuts
from .update import UpdateWindow
from .sysspecs import Specs
from .settings_dialog import SettingsDialog
from .new_library_dialog import NewLibraryDialog

# start logger for this module
log = manager.getLogger(__name__)


class MainCanvas(QtWidgets.QMainWindow):
    """
    - Implements the canvas QWidgets, contains the main menus and provides user
      settings via menu or rc file.

    - Anchors the canvas and provides the main menu and status bar.
    """

    def __init__(self):
        super(MainCanvas, self).__init__()

        # useful for tracking number of file handles
        #self._report = QtCore.QTimer()
        #self._report.setInterval(1000)
        #self._report.timeout.connect(Specs.numOpenFiles)
        #self._report.start()

        # Flag for avoiding double call to closeEvent in PyQt5
        # https://bugreports.qt.io/browse/QTBUG-43344
        self.already_closed = False

        # A statusbar widget
        self._statusLabel = QtWidgets.QLabel()

        # for copying between canvases
        self._copybuffer = None

        # TAB WIDGET
        self.tabs = QtWidgets.QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setTabPosition(QtWidgets.QTabWidget.North)
        self.tabs.tabCloseRequested.connect(self.closeCanvasTab)
        self.tabs.currentChanged.connect(self.tabChange)
        self.tabs.setMovable(True)
        self.setCentralWidget(self.tabs)
        self.tabs.show()

        # ADD TAB BUTTON
        self.addbutton = QtWidgets.QPushButton('+')
        self.addbutton.clicked[bool].connect(self.addNewCanvasTab)
        self.tabs.setCornerWidget(self.addbutton)

        # SHORTCUTS
        self.shortcuts = Shortcuts()

        # ADD CANVAS TABS
        self._canvasCnt = 1
        newGraph = GraphWidget("Canvas 1", self)
        newGraph._curState.connect(self.updateCanvasStatus)
        self.tabs.addTab(newGraph, "Canvas 1")

        newGraph.addShortcuts(self.shortcuts.parseShortcuts(True))
        self.shortcuts.shortcuts_changed.connect(lambda: newGraph.updateShortcuts(self.shortcuts.parseShortcuts(True)))

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

        # system tray icon (this actually works in Ubuntu)
        from .defines import ICON_PATH
        self._gpiIcon = QtGui.QIcon(ICON_PATH)
        self.setWindowIcon(self._gpiIcon)
        #self._trayicon = QtWidgets.QSystemTrayIcon(self._gpiIcon, parent=self)
        #self._trayicon.show()

        # don't bother with the menus if the gui is not up
        if not Commands.noGUI():
            self.createMenus()

            apply_gpi_theme(QtWidgets.QApplication.instance(),
                            Config.APPEARANCE_STYLE)

            # Status Bar
            message = "A context menu is available by right-clicking"
            self.statusBar().addPermanentWidget(self._statusLabel)
            self.statusBar().showMessage(message)

            self.updateCanvasStatus()

        # Pre-warm the GPI_PROCESS worker pool so the first node doesn't pay
        # the ~1s Python spawn cost.  Runs after the UI is shown.
        QtCore.QTimer.singleShot(0, self._prewarm_executor)

    def _prewarm_executor(self):
        from .functor import _get_executor
        _get_executor()

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

                # Process RSS = actual resident pages (matches Task Manager).
                # Port MEM = total mapped data size (can exceed RAM with memmaps).
                try:
                    rss = psutil.Process().memory_info().rss
                except Exception:
                    rss = 0

                pmem = graph.totalPortMem()
                if pmem > 0 or rss > 0:
                    parts = []
                    if rss > 0 and Specs.TOTAL_PHYMEM() > 0:
                        from gpi.defines import GetHumanReadable_bytes
                        pct = 100.0 * rss / Specs.TOTAL_PHYMEM()
                        parts.append(f'GPI RAM: {GetHumanReadable_bytes(rss)}, {pct:.1f}%')
                    if pmem > 0:
                        parts.append(f'Port Data: {GetHumanReadable_bytes(pmem)}')
                    msg += ' [' + ' | '.join(parts) + ']'
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
        reply = QtWidgets.QMessageBox.question(self, 'Message',
                    "Quit without saving?", QtWidgets.QMessageBox.Yes |
                        QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)

        if reply == QtWidgets.QMessageBox.Yes:
            self.already_closed = True
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

        newGraph.addShortcuts(self.shortcuts.parseShortcuts(True))
        self.shortcuts.shortcuts_changed.connect(lambda: newGraph.updateShortcuts(self.shortcuts.parseShortcuts(True)))

    def tabChange(self, index):
        log.debug("tabChange: "+str(index))
        self.updateCanvasStatus()

    def closeEvent(self, event):
        if self.already_closed is False:
            '''close all graphs before shutting down.
            '''
            if not self.quitConfirmed():
                event.ignore()
                return
        else:
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
        wdgvbox = QtWidgets.QVBoxLayout()
        wdgvbox.addWidget(self.txtbox)

        # set master widget
        self.consoleWdg = QtWidgets.QWidget()
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
        wdgvbox = QtWidgets.QVBoxLayout()
        wdgvbox.addWidget(dispbox)
        wdgvbox.addWidget(txtbox)
        wdgvbox.setStretch(0, 2)

        # set master widget
        self.aboutWdg = QtWidgets.QWidget()
        self.aboutWdg.setLayout(wdgvbox)
        # self.aboutWdg.setSizePolicy(QtWidgets.QSizePolicy.Minimum, \
        #   QtWidgets.QSizePolicy.Preferred)
        # self.aboutWdg.setMaximumWidth(420)
        self.aboutWdg.show()
        self.aboutWdg.raise_()
        log.debug(str(dispbox.sizeHint()))

    def generateConfigFile(self):
        # a place for a user dialog if need be
        log.debug("generateConfigFile(): called")
        Config.generateConfigFile()

        #reply = QtWidgets.QMessageBox.question(self, 'Message',
        #                                   "Overwrite Existing" +
        #                                   " Configuration File (" +
        #                                   self._configFileName + ")?",
        #                                   QtWidgets.QMessageBox.Yes |
        #                                   QtWidgets.QMessageBox.No,
        #                                   QtWidgets.QMessageBox.No)
        #if reply == QtWidgets.QMessageBox.No:
        #    log.info("generateConfigFile(): aborted.")
        #    return

    def generateUserLib(self):
        log.debug("generateUserLib(): called")
        dlg = NewLibraryDialog(parent=self)
        if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            graph = self.tabs.currentWidget()
            if graph is not None:
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

        # ── FILE ──────────────────────────────────────────────────────────────
        self.fileMenu = QtWidgets.QMenu("&File", self)
        self.fileMenu.addAction(
            QtWidgets.QAction("New Tab", self, shortcut="Ctrl+T",
                              triggered=self.addNewCanvasTab)
        )
        self.fileMenu.addSeparator()
        self.fileMenu.addAction(
            QtWidgets.QAction("Settings...", self, shortcut="Ctrl+,",
                              triggered=self.openSettings)
        )
        self.menuBar().addMenu(self.fileMenu)

        # ── LIBRARY ───────────────────────────────────────────────────────────
        # (was "Config" — node/library management actions)
        self.libraryMenu = QtWidgets.QMenu("&Library", self)
        self.libraryMenu.addAction("Create New Library", self.generateUserLib)
        self.libraryMenu.addSeparator()
        self.libraryMenu.addAction("Create New Node", self.createNewNode)
        self.libraryMenu.addAction("Scan For New Nodes", self.rescanKnownLibs)
        self.menuBar().addMenu(self.libraryMenu)

        # ── VIEW ──────────────────────────────────────────────────────────────
        # (was separate "Window" and "Shortcuts" menus)
        self.viewMenu = QtWidgets.QMenu("&View", self)
        self.viewMenu.addAction(
            QtWidgets.QAction("Close Node Menus (Current Tab)", self,
                              shortcut="Ctrl+X",
                              triggered=self.closeAllNodeMenus)
        )
        self.viewMenu.addSeparator()
        self.viewMenu.addAction(
            QtWidgets.QAction("Modify Shortcuts", self,
                              triggered=self.openShortcuts)
        )

        self.viewMenu.addSeparator()
        self.layoutMenu = self.viewMenu.addMenu("Layout (Dark theme)")
        self._layout_vert_act = QtWidgets.QAction(
            "Vertical (default)", self, checkable=True,
            triggered=lambda: self.setLayoutDirection('Vertical'))
        self._layout_horiz_act = QtWidgets.QAction(
            "Horizontal", self, checkable=True,
            triggered=lambda: self.setLayoutDirection('Horizontal'))
        self._layout_group = QtWidgets.QActionGroup(self)
        self._layout_group.addAction(self._layout_vert_act)
        self._layout_group.addAction(self._layout_horiz_act)
        self.layoutMenu.addAction(self._layout_vert_act)
        self.layoutMenu.addAction(self._layout_horiz_act)
        if Config.LAYOUT_DIRECTION == 'Horizontal':
            self._layout_horiz_act.setChecked(True)
        else:
            self._layout_vert_act.setChecked(True)

        self.menuBar().addMenu(self.viewMenu)

        # ── DEBUG ─────────────────────────────────────────────────────────────
        self.debugMenu = QtWidgets.QMenu("&Debug", self)

        self.loggerMenu = self.debugMenu.addMenu("Logger Level")
        self._loglevel_debug_act = QtWidgets.QAction(
            "Debug", self, checkable=True,
            triggered=lambda: self.setLoggerLevel(logging.DEBUG))
        self._loglevel_info_act = QtWidgets.QAction(
            "Info", self, checkable=True,
            triggered=lambda: self.setLoggerLevel(logging.INFO))
        self._loglevel_node_act = QtWidgets.QAction(
            "Node", self, checkable=True,
            triggered=lambda: self.setLoggerLevel(logger.GPINODE))
        self._loglevel_warn_act = QtWidgets.QAction(
            "Warn", self, checkable=True,
            triggered=lambda: self.setLoggerLevel(logging.WARNING))
        self._loglevel_error_act = QtWidgets.QAction(
            "Error", self, checkable=True,
            triggered=lambda: self.setLoggerLevel(logging.ERROR))
        self._loglevel_critical_act = QtWidgets.QAction(
            "Critical", self, checkable=True,
            triggered=lambda: self.setLoggerLevel(logging.CRITICAL))

        self.loggerMenuGroup = QtWidgets.QActionGroup(self)
        for act in (self._loglevel_debug_act, self._loglevel_info_act,
                    self._loglevel_node_act, self._loglevel_warn_act,
                    self._loglevel_error_act, self._loglevel_critical_act):
            self.loggerMenuGroup.addAction(act)
            self.loggerMenu.addAction(act)

        if Commands.logLevel():
            self.setLoggerLevel(Commands.logLevel())
            self.setLoggerLevelMenuCheckbox(Commands.logLevel())
        else:
            self._loglevel_warn_act.setChecked(True)
            self.setLoggerLevel(logging.WARNING)

        self.debugMenu.addSeparator()
        self.debugMenu.addAction("Print sys.paths", self.printSysPath)
        self.debugMenu.addAction("Print sys.modules", self.printSysModules)
        self.menuBar().addMenu(self.debugMenu)

        # ── HELP ──────────────────────────────────────────────────────────────
        self.helpMenu = QtWidgets.QMenu("&Help", self)
        aboutAct = QtWidgets.QAction("&About", self, triggered=self.about)
        self.helpMenu.addAction(aboutAct)
        self.helpMenu.addAction(
            QtWidgets.QAction("Documentation", self, triggered=self.openWebsite)
        )
        self.helpMenu.addAction(
            QtWidgets.QAction("Examples", self, triggered=self.openExamplesFolder)
        )
        self.helpMenu.addSeparator()
        checkUpdateAct = QtWidgets.QAction("Check For Updates...", self,
                                           triggered=self.openUpdater)
        checkUpdateAct.setMenuRole(QtWidgets.QAction.ApplicationSpecificRole)
        self.helpMenu.addAction(checkUpdateAct)
        self.menuBar().addMenu(self.helpMenu)

    
    def setLayoutDirection(self, direction):
        Config.LAYOUT_DIRECTION = direction
        Config.saveConfigFile()
        for i in range(self.tabs.count()):
            w = self.tabs.widget(i)
            if w is not None:
                w.refreshLayout()
                QtCore.QTimer.singleShot(50, w._autoOrganizeAll)

    def showEvent(self, event):
        super().showEvent(event)
        win32_set_dark_titlebar(self, Config.APPEARANCE_STYLE != 'Classic')

    def openSettings(self):
        library = None
        graph = self.tabs.currentWidget()
        if graph is not None and hasattr(graph, 'getLibrary'):
            library = graph.getLibrary()
        dlg = SettingsDialog(parent=self, library=library)

        def _on_theme_changed():
            app = QtWidgets.QApplication.instance()
            apply_gpi_theme(app, Config.APPEARANCE_STYLE)
            dark = Config.APPEARANCE_STYLE != 'Classic'
            win32_set_dark_titlebar(self, dark)
            # Sync View > Layout menu checkmarks
            if Config.LAYOUT_DIRECTION == 'Horizontal':
                self._layout_horiz_act.setChecked(True)
            else:
                self._layout_vert_act.setChecked(True)
            # Reposition ports/edges, repaint, and auto-organize
            for i in range(self.tabs.count()):
                w = self.tabs.widget(i)
                if w is not None:
                    try:
                        w.refreshLayout()
                        w.scene().update()
                        w.viewport().update()
                        QtCore.QTimer.singleShot(50, w._autoOrganizeAll)
                    except Exception:
                        pass

        dlg.settings_applied.connect(_on_theme_changed)

        def _on_paths_changed():
            lib = graph.getLibrary() if graph is not None and hasattr(graph, 'getLibrary') else None
            if lib is not None:
                lib.rescan()

        dlg.library_paths_changed.connect(_on_paths_changed)
        dlg.exec()

    def openShortcuts(self):
        self.shortcuts.show()

    def openUpdater(self):
        self._updateWin = UpdateWindow(dry_run=False)
        self._updateWin.show()
        self._updateWin.raise_()

    # TODO: move this and others like it to a common help-object that can errorcheck.
    def openWebsite(self):
        if not QtGui.QDesktopServices.openUrl(QtCore.QUrl('http://docs.gpilab.com')):
            QtWidgets.QMessageBox.information(self, 'Documentation',"Documentation can be found at\nhttp://docs.gpilab.com", QtWidgets.QMessageBox.Close)

    def openDocsFolder(self):
        self._openFolder(GPI_DOCS_DIR)
        log.dialog("GPI documentation can be found in: "+GPI_DOCS_DIR)

    def openExamplesFolder(self):
        examples_dir = os.path.join(GPI_DOCS_DIR, 'Examples')
        self._openFolder(examples_dir)
        log.dialog("GPI examples can be found in: "+examples_dir)

    def _openFolder(self, path):
        if Specs.inOSX():
            subprocess.Popen(["open", path])
        elif Specs.inLinux():
            subprocess.Popen(["xdg-open", path])
        elif Specs.inWindows():
            os.startfile(path)
        else:
            log.warn("Cannot open folder on this OS: " + path)

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
        QtWidgets.QApplication.setStyle(QtWidgets.QStyleFactory.create(action.text()))
        QtWidgets.QApplication.setPalette(
            QtWidgets.QApplication.style().standardPalette())

    def debugOptions(self, action):
        if action.text() == "Debug Info":
            self.printSysPath()
        #if action.text() == "Console":
        #    print "MainCanvas(): Console"


