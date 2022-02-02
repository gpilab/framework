#!/usr/bin/env python

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

# Brief: The main launcher for starting a GPI GUI session.

import sys
import os

# workaround for the Accelerate/multiprocessing bug that causes silent crashes
# when using numpy linear algebra packages on macOS
if sys.platform == 'darwin':
    os.environ["VECLIB_MAXIMUM_THREADS"] = '1'

# gpi
from gpi import QtGui, QtWidgets, QtCore, Signal
from gpi.cmd import Commands
from gpi.defines import PLOGO_PATH, ICON_PATH
from gpi.mainWindow import MainCanvas

INCLUDE_EULA=False

class Splash(QtWidgets.QSplashScreen):
    '''The splash screen that appears at GPI launch.  This contains a copy of
    the boilerplate required by Dignity Health.
    '''

    terms_accepted = Signal()

    def __init__(self, image_path):

        # find the limiting desktop dimension (w or h)
        pm = QtGui.QPixmap.fromImage(QtGui.QImage(image_path))
        g = QtWidgets.QDesktopWidget().availableGeometry()
        w = g.width()
        h = g.height()
        r = float(pm.width())/1 if pm.height() == 0 else pm.height()  # aspect ratio
        if (w <= pm.width()):
            h = int(w/r)
        if (h <= pm.height()):
            w = int(h*r)

        # the splash is almost useless below 500pts
        if w < 500:
            w = 500

        # resize the image based on new width
        if (w != g.width()) or (h != g.height()):
            pm = pm.scaledToWidth(int(w*0.8), mode=QtCore.Qt.SmoothTransformation)

        # scale subsequent parameters based on new image width
        iw = pm.width()
        ih = pm.height()

        super(Splash, self).__init__(pm)

        # use a timer instead of the EULA
        self._timer = QtCore.QTimer()
        self._timer.timeout.connect(self.terms_accepted.emit)
        self._timer.setSingleShot(True)
        if not INCLUDE_EULA:
            self._timer.start(2000)

        panel = QtWidgets.QWidget()
        pal = QtGui.QPalette(QtGui.QColor(255, 255, 255)) # white
        panel.setAutoFillBackground(True)
        panel.setPalette(pal)

        lic = '''
THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
        '''
        self.lic = QtWidgets.QTextEdit(lic)
        self.lic.setReadOnly(True)

        button_title = 'Agree'
        self.wdg1 = QtWidgets.QPushButton(button_title, self)
        self.wdg1.setCheckable(False)
        self.wdg1.setFixedSize(int(iw*0.2),int(iw*0.05))
        self.wdg1.clicked[bool].connect(self.accept)

        button_title = 'Quit'
        self.wdg2 = QtWidgets.QPushButton(button_title, self)
        self.wdg2.setCheckable(False)
        self.wdg2.setFixedSize(int(iw*0.2),int(iw*0.05))
        self.wdg2.clicked[bool].connect(self.reject)

        buf = 'Click Agree to start GPI or Quit to exit.'
        new_fw = iw * 0.45
        for fw_i in range(20,0,-1):
            f = QtGui.QFont('gill sans', fw_i)
            fm = QtGui.QFontMetricsF(f)
            cfw = fm.width(buf)
            if cfw < new_fw:
                break
        f = QtGui.QFont('gill sans', fw_i)

        self.prompt = QtWidgets.QLabel(buf)
        self.prompt.setAlignment(QtCore.Qt.AlignCenter)
        self.prompt.setFont(f)

        wdgLayout = QtWidgets.QHBoxLayout()
        #wdgLayout.setContentsMargins(0, 0, 0, 0)  # no spaces around this item
        #wdgLayout.setSpacing(0)
        #wdgLayout.addSpacerItem(QtWidgets.QSpacerItem(iw/2,1,hPolicy=QtWidgets.QSizePolicy.Minimum))
        wdgLayout.addWidget(self.prompt)
        wdgLayout.addWidget(self.wdg1)
        #wdgLayout.addSpacerItem(QtWidgets.QSpacerItem(int(iw*0.01),1,hPolicy=QtWidgets.QSizePolicy.Minimum))
        wdgLayout.addWidget(self.wdg2)
        #wdgLayout.addSpacerItem(QtWidgets.QSpacerItem(1,1,hPolicy=QtWidgets.QSizePolicy.MinimumExpanding))


        # a small panel
        vbox_p = QtWidgets.QVBoxLayout()
        vbox_p.setContentsMargins(10,10,10,10)
        vbox_p.setSpacing(10)
        vbox_p.addWidget(self.lic)
        vbox_p.addLayout(wdgLayout)
        panel.setLayout(vbox_p)

        # white space | panel
        vbox = QtWidgets.QVBoxLayout()
        #vbox.setContentsMargins(0, 0, 0, int(iw*0.02))  # no spaces around this item
        vbox.setContentsMargins(0, 0, 0, 0)  # no spaces around this item
        vbox.setSpacing(0)

        vbox.addSpacerItem(QtWidgets.QSpacerItem(iw,(1-0.28)*ih,hPolicy=QtWidgets.QSizePolicy.Minimum,vPolicy=QtWidgets.QSizePolicy.Minimum))

        #vbox.addWidget(self.lic)
        vbox.addWidget(panel)
        #vbox.addLayout(wdgLayout)

        if INCLUDE_EULA:
            self.setLayout(vbox)

        self._accept = False

    def mousePressEvent(self, event):
        pass

    def accept(self):
        self.terms_accepted.emit()

    def reject(self):
        # tell Qt to quit right away.
        QtCore.QCoreApplication.instance().quit()

def launch():
    '''Starts the main application loop, parses any user config and commandline
    args.'''

    # start main application
    # for debugging force widgetcount
    #app = QtWidgets.QApplication(sys.argv+['-widgetcount'])
    app = QtWidgets.QApplication(sys.argv)
    app.setWindowIcon(QtGui.QIcon(ICON_PATH))

    # parse commandline arguments
    try:
        # PyQt4
        Commands.parse(app.argv())
    except AttributeError:
        # PyQt5
        Commands.parse(app.arguments())
    #print Commands

    # start a mainwindow widget instance
    widget = MainCanvas()

    # start splash
    # only raise in GUI mode, don't raise in cmdline mode.
    if not Commands.noGUI():

        if not Commands.noSplash():
            spl = Splash(PLOGO_PATH)

            def closeraise():
                spl.finish(widget)
                widget.show()
                widget.raise_()

            spl.terms_accepted.connect(closeraise)
            spl.show()
            spl.raise_()
            app.processEvents() # allow gui to update

        else:
            dummy = QtWidgets.QSplashScreen()
            dummy.show()
            dummy.finish(widget)
            widget.show()
            widget.raise_()

    sys.exit(app.exec_())

if __name__ == '__main__':
    launch()
