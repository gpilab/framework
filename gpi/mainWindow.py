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
import time
import logging
import subprocess


# gpi
from gpi import QtCore, QtGui, QtWidgets, VERSION, RELEASE_DATE
from .config import Config
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
from .settings_dialog import SettingsDialog
from .sysspecs import Specs

# start logger for this module
log = manager.getLogger(__name__)


class _GenerateLibDialog(QtWidgets.QDialog):
    """Dialog for creating a new GPI user library."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Generate User Library")
        self.setMinimumWidth(540)

        default_parent = os.path.join(os.path.expanduser('~'), 'gpi')
        default_lib = 'my_nodes'

        form = QtWidgets.QFormLayout()

        parent_row = QtWidgets.QHBoxLayout()
        self._parent_edit = QtWidgets.QLineEdit(default_parent)
        browse_btn = QtWidgets.QPushButton("Browse…")
        browse_btn.clicked.connect(self._browse)
        parent_row.addWidget(self._parent_edit)
        parent_row.addWidget(browse_btn)
        form.addRow("Parent folder:", parent_row)

        self._lib_edit = QtWidgets.QLineEdit(default_lib)
        form.addRow("Library name:", self._lib_edit)

        self._sub_edit = QtWidgets.QPlainTextEdit("nodes")
        self._sub_edit.setPlaceholderText("one per line, e.g.\nnodes\nutils\nexamples")
        self._sub_edit.setFixedHeight(72)
        form.addRow("Sub-library names:", self._sub_edit)

        self._preview = QtWidgets.QLabel()
        self._preview.setWordWrap(True)
        form.addRow("Will create:", self._preview)

        btns = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)

        vbox = QtWidgets.QVBoxLayout()
        vbox.addLayout(form)
        vbox.addSpacing(8)
        vbox.addWidget(btns)
        self.setLayout(vbox)

        self._parent_edit.textChanged.connect(self._update_preview)
        self._lib_edit.textChanged.connect(self._update_preview)
        self._sub_edit.textChanged.connect(self._update_preview)
        self._update_preview()

    def _browse(self):
        d = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Select Parent Folder", self._parent_edit.text())
        if d:
            self._parent_edit.setText(os.path.normpath(d))

    def _sub_names(self):
        raw = self._sub_edit.toPlainText()
        names = [s.strip() for s in raw.splitlines() if s.strip()]
        return names if names else ["nodes"]

    def _update_preview(self):
        parent = self._parent_edit.text().strip()
        lib = self._lib_edit.text().strip()
        subs = self._sub_names()
        if parent and lib:
            lines = []
            for i, sub in enumerate(subs, 1):
                node_file = f"sample_node{i}_GPI.py"
                lines.append(os.path.join(parent, lib, sub, 'GPI', node_file))
            self._preview.setText("\n".join(lines))
        else:
            self._preview.setText("(fill in all fields above)")

    def values(self):
        return (
            self._parent_edit.text().strip(),
            self._lib_edit.text().strip(),
            self._sub_names(),
        )


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

            best_style = None
            qt_styles = list(QtWidgets.QStyleFactory.keys())
            if Specs.inWindows() and 'Fusion' in qt_styles:
                log.debug("Choosing Fusion style.")
                best_style = 'Fusion'
            elif Specs.inOSX() and 'Macintosh (aqua)' in qt_styles:
                log.debug("Choosing Mac aqua style.")
                best_style = 'Macintosh (aqua)'
            elif 'Fusion' in qt_styles:
                log.debug("Choosing Fusion style.")
                best_style = 'Fusion'
            elif 'Cleanlooks' in qt_styles:
                log.debug("Choosing Cleanlooks style.")
                best_style = 'Cleanlooks'

            # if 'Macintosh (aqua)' in list(QtGui.QStyleFactory.keys()):
            #     log.debug("Choosing Mac aqua style.")
            #     best_style = 'Macintosh (aqua)'
            # elif 'Cleanlooks' in list(QtGui.QStyleFactory.keys()):
            #     log.debug("Choosing Cleanlooks style.")
            #     best_style = 'Cleanlooks'

            if best_style:
                QtWidgets.QApplication.setStyle(QtWidgets.QStyleFactory.create(best_style))
                QtWidgets.QApplication.setPalette(
                    QtWidgets.QApplication.style().standardPalette())

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
        log.debug("generateConfigFile(): called")
        Config.generateConfigFile()

    def migrateConfigFile(self):
        """Import settings from gpi.conf into QSettings (one-time migration)."""
        if not Config.configFileExists():
            QtWidgets.QMessageBox.information(
                self, "Migrate from gpi.conf",
                "No gpi.conf file found at:\n" + str(Config.configFilePath()) +
                "\n\nNothing to migrate.")
            return
        ok = Config.migrateFromConfigFile()
        if ok:
            QtWidgets.QMessageBox.information(
                self, "Migrate from gpi.conf",
                "Settings imported from gpi.conf and saved to GPI Settings.\n"
                "You can now open File → Settings to review them.")
        else:
            QtWidgets.QMessageBox.warning(
                self, "Migrate from gpi.conf",
                "Migration failed. Check the log for details.")

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
        dlg = _GenerateLibDialog(self)
        if dlg.exec_() != QtWidgets.QDialog.Accepted:
            return
        parent_dir, lib_name, sub_names = dlg.values()
        if not parent_dir or not lib_name:
            QtWidgets.QMessageBox.warning(
                self, "Generate User Library",
                "Parent folder and library name are required.")
            return
        try:
            Config.generateUserLib(parent_dir, lib_name, sub_names)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(
                self, "Generate User Library",
                f"Failed to create library:\n{exc}")
            return
        sub_list = "\n".join(
            f"  {os.path.join(parent_dir, lib_name, s, 'GPI', f'sample_node{i+1}_GPI.py')}"
            for i, s in enumerate(sub_names))
        QtWidgets.QMessageBox.information(
            self, "Generate User Library",
            f"Library '{lib_name}' created successfully.\n\n"
            f"Example nodes:\n{sub_list}\n\n"
            f"'{parent_dir}' has been added to your library paths.")
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

        # ── File ──────────────────────────────────────────────────────────────
        self.fileMenu = QtWidgets.QMenu("&File", self)
        self.fileMenu.addAction(QtWidgets.QAction(
            "New Tab", self, shortcut="Ctrl+T", triggered=self.addNewCanvasTab))
        self.fileMenu.addSeparator()
        self.fileMenu.addAction(QtWidgets.QAction(
            "Settings…", self, shortcut="Ctrl+,", triggered=self.openSettings))
        self.menuBar().addMenu(self.fileMenu)

        # ── Library ───────────────────────────────────────────────────────────
        # Node / library management (was "Config")
        self.libraryMenu = QtWidgets.QMenu("&Library", self)
        self.libraryMenu.addAction("Scan For New Nodes", self.rescanKnownLibs)
        self.libraryMenu.addAction("Create New Node…", self.createNewNode)
        self.libraryMenu.addSeparator()
        self.libraryMenu.addAction("Generate User Library…", self.generateUserLib)
        self.menuBar().addMenu(self.libraryMenu)

        # ── Window ────────────────────────────────────────────────────────────
        self.windowMenu = QtWidgets.QMenu("&Window", self)
        self.windowMenu_closeAct = QtWidgets.QAction(
            "Close Node Panels", self, shortcut="Ctrl+X",
            triggered=self.closeAllNodeMenus)
        self.windowMenu.addAction(self.windowMenu_closeAct)
        self.menuBar().addMenu(self.windowMenu)

        # ── Debug ─────────────────────────────────────────────────────────────
        self.debugMenu = QtWidgets.QMenu("&Debug", self)

        self.debugMenu.addAction("Console", self.console)
        self.debugMenu.addSeparator()

        # Logger level sub-menu
        self.loggerMenu = self.debugMenu.addMenu("Logger Level")
        self._loglevel_debug_act    = QtWidgets.QAction("Debug",    self, checkable=True, triggered=lambda: self.setLoggerLevel(logging.DEBUG))
        self._loglevel_info_act     = QtWidgets.QAction("Info",     self, checkable=True, triggered=lambda: self.setLoggerLevel(logging.INFO))
        self._loglevel_node_act     = QtWidgets.QAction("Node",     self, checkable=True, triggered=lambda: self.setLoggerLevel(logger.GPINODE))
        self._loglevel_warn_act     = QtWidgets.QAction("Warn",     self, checkable=True, triggered=lambda: self.setLoggerLevel(logging.WARNING))
        self._loglevel_error_act    = QtWidgets.QAction("Error",    self, checkable=True, triggered=lambda: self.setLoggerLevel(logging.ERROR))
        self._loglevel_critical_act = QtWidgets.QAction("Critical", self, checkable=True, triggered=lambda: self.setLoggerLevel(logging.CRITICAL))
        self.loggerMenuGroup = QtWidgets.QActionGroup(self)
        for act in (self._loglevel_debug_act, self._loglevel_info_act,
                    self._loglevel_node_act,  self._loglevel_warn_act,
                    self._loglevel_error_act, self._loglevel_critical_act):
            self.loggerMenuGroup.addAction(act)
            self.loggerMenu.addAction(act)

        # Initialize log level
        if Commands.logLevel():
            self.setLoggerLevel(Commands.logLevel())
            self.setLoggerLevelMenuCheckbox(Commands.logLevel())
        else:
            self._loglevel_warn_act.setChecked(True)
            self.setLoggerLevel(logging.WARNING)

        self.debugMenu.addSeparator()
        self.debugMenu.addAction("Print sys.path",    self.printSysPath)
        self.debugMenu.addAction("Print sys.modules", self.printSysModules)
        self.menuBar().addMenu(self.debugMenu)

        # ── Help ──────────────────────────────────────────────────────────────
        self.helpMenu = QtWidgets.QMenu("&Help", self)
        self.helpMenu.addAction("About GPI…", self.about)
        self.checkForUpdate = QtWidgets.QAction(
            "Check For Updates…", self, triggered=self.openUpdater)
        self.checkForUpdate.setMenuRole(QtWidgets.QAction.ApplicationSpecificRole)
        self.helpMenu.addAction(self.checkForUpdate)
        self.helpMenu.addSeparator()
        self.helpMenu.addAction("Documentation", self.openWebsite)
        self.helpMenu.addAction("Examples", self.openExamplesFolder)
        self.helpMenu.addSeparator()
        self.helpMenu.addAction("Keyboard Shortcuts…", self.openShortcuts)
        self.helpMenu.addSeparator()
        self.helpMenu.addAction("Migrate from gpi.conf…", self.migrateConfigFile)
        self.menuBar().addMenu(self.helpMenu)

    
    def openShortcuts(self):
        self.shortcuts.show()
        # self.shortcutsWin.raise_()

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

    def openSettings(self):
        graph = self.tabs.currentWidget()
        node_catalog = graph.getLibrary()._known_GPI_nodes if graph else None
        dlg = SettingsDialog(self, node_catalog=node_catalog)
        dlg.exec()

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


