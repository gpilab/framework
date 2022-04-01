import gpi
from gpi import QtGui, QtWidgets, QtCore, Signal
import pathlib
from os.path import exists
import random

class Shortcuts(QtWidgets.QWidget):
    '''A simple UI to display the GPI shortcuts.
    '''
    shortcuts_changed = gpi.Signal()

    def __init__(self):
        super().__init__()

        self.rows = 0
        self.shortcuts = {}

        help_text =  QtWidgets.QLabel("\
            Adding a shortcut:\n\
            You can use any letter,  number,  special character alone,  with Shift,  or with Ctrl\n\n\
            I  -->  ImageViewer\n\
            Ctrl+F  -->  FFTW\n\
            Shift++  -->  Math\n\
            Ctrl+Shift+G  -->  Grid\n\
            ")
        add_button = QtWidgets.QPushButton("Add Shortcut")
        add_button.clicked.connect(lambda: self.addShortcut())
        save_button = QtWidgets.QPushButton("Save Changes")
        save_button.clicked.connect(lambda: self.saveShortcuts())

        self.vbox = QtWidgets.QVBoxLayout()
        self.grid = QtWidgets.QGridLayout()
        self.vbox.addWidget(help_text)
        self.vbox.addLayout(self.grid)
        self.vbox.addWidget(add_button)
        self.vbox.addWidget(save_button)

        self.setLayout(self.vbox)


        self.shortcuts_path = pathlib.Path.joinpath(pathlib.Path(__file__).parent,"shortcuts.txt")
        file_exists = exists(self.shortcuts_path)
        if not file_exists:
            f = open(self.shortcuts_path, 'w')
            f.close()

        self.parseShortcuts()


        # window properties
        self.resize(700, 200)
        frameGm = self.frameGeometry()
        screen = QtWidgets.QApplication.desktop().screenNumber(QtWidgets.QApplication.desktop().cursor().pos())
        centerPoint = QtWidgets.QApplication.desktop().screenGeometry(screen).center()
        frameGm.moveCenter(centerPoint)
        self.move(frameGm.topLeft())
        self.setWindowTitle('GPI Shortcuts')

    def addShortcut(self, shortcut="", node=""):
        shortcut_input = QtWidgets.QLineEdit(shortcut)
        node_input = QtWidgets.QLineEdit(node)
        self.grid.addWidget(shortcut_input, self.rows, 0)
        self.grid.addWidget(node_input, self.rows, 1)
        remove_button = QtWidgets.QPushButton("X")
        if shortcut == "": shortcut = int(random.random()*100000)
        remove_button.clicked.connect(lambda: self.removeShorcut(shortcut))
        self.grid.addWidget(remove_button, self.rows, 2)
        self.shortcuts[shortcut] = [shortcut_input, node_input, remove_button]
        self.rows += 1

    def removeShorcut(self, shortcut):
        shortcut_input, node_input, remove_button = self.shortcuts[shortcut]
        shortcut_input.setParent(None)
        node_input.setParent(None)
        remove_button.setParent(None)
        del self.shortcuts[shortcut]
        self.rows -= 1

    def parseShortcuts(self, data_only=False):
        with open(self.shortcuts_path) as file:
            shortcuts = [line.rstrip() for line in file]

        if data_only: return shortcuts

        for shortcut in shortcuts:
            shortcut = shortcut.split(":")
            if len(shortcut) == 2:
                node = shortcut.pop()
                self.addShortcut(shortcut[0], node)


    def saveShortcuts(self):
        with open(self.shortcuts_path, 'w') as file:
            for key in self.shortcuts.keys():
                shortcut_input, node_input, remove_button = self.shortcuts[key]
                if shortcut_input.text() and node_input.text():
                    file.write(f"{shortcut_input.text()}:{node_input.text()}\n")
        
        self.shortcuts_changed.emit()
        self.close()

