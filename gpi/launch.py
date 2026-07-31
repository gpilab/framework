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

# IMPORTANT: Keep this module-level scope free of gpi/Qt imports.
# On Windows, multiprocessing (spawn) re-executes __main__ in every worker
# process.  Any module-level import here would run in those workers too.
# All real imports live inside launch() so workers see an empty module.

import sys
import os

# workaround for the Accelerate/multiprocessing bug that causes silent crashes
# when using numpy linear algebra packages on macOS
if sys.platform == 'darwin':
    os.environ["VECLIB_MAXIMUM_THREADS"] = '1'

# On Windows, numpy (MKL) loads libiomp5md.dll and PyTorch/Matplotlib can load
# libomp.dll, causing a fatal OpenMP dual-runtime conflict.  Must be set before
# any of those libraries are imported.
if sys.platform == 'win32':
    os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

    # Shortcuts (Start Menu/Desktop) launch pythonw.exe directly, bypassing
    # `conda activate`, so the env's Library\bin (Qt platform plugins,
    # freetype/libpng, OpenMP) is never added to the DLL search path. That's
    # invisible until a node first imports something that needs those DLLs
    # (e.g. matplotlib), at which point the process crashes with no traceback.
    # Re-derive and add those directories here, before any such import.
    _conda_prefix = os.environ.get('CONDA_PREFIX') or sys.prefix
    _dll_dirs = [
        os.path.join(_conda_prefix, 'Library', 'bin'),
        os.path.join(_conda_prefix, 'Library', 'mingw-w64', 'bin'),
        os.path.join(_conda_prefix, 'Library', 'usr', 'bin'),
        os.path.join(_conda_prefix, 'Scripts'),
    ]
    for _d in _dll_dirs:
        if os.path.isdir(_d):
            try:
                os.add_dll_directory(_d)
            except (AttributeError, OSError):
                pass
    _existing_path = os.environ.get('PATH', '')
    _missing = [d for d in _dll_dirs if os.path.isdir(d) and d not in _existing_path]
    if _missing:
        os.environ['PATH'] = os.pathsep.join(_missing + [_existing_path])

INCLUDE_EULA = False


def launch():
    '''Starts the main application loop, parses any user config and commandline
    args.'''

    from gpi import QtGui, QtWidgets, QtCore, Signal
    from gpi.cmd import Commands
    from gpi.defines import PLOGO_PATH, ICON_PATH
    from gpi.mainWindow import MainCanvas

    class Splash(QtWidgets.QSplashScreen):
        '''The splash screen that appears at GPI launch.'''

        terms_accepted = Signal()

        def __init__(self, image_path):
            pm = QtGui.QPixmap.fromImage(QtGui.QImage(image_path))
            g  = QtWidgets.QApplication.primaryScreen().availableGeometry()
            w  = g.width()
            h  = g.height()
            r  = float(pm.width()) / 1 if pm.height() == 0 else pm.height()
            if w <= pm.width():
                h = int(w / r)
            if h <= pm.height():
                w = int(h * r)
            if w < 500:
                w = 500
            if (w != g.width()) or (h != g.height()):
                pm = pm.scaledToWidth(int(w * 0.8),
                                      mode=QtCore.Qt.SmoothTransformation)
            iw = pm.width()
            ih = pm.height()

            super(Splash, self).__init__(pm)

            self._timer = QtCore.QTimer()
            self._timer.timeout.connect(self.terms_accepted.emit)
            self._timer.setSingleShot(True)
            if not INCLUDE_EULA:
                self._timer.start(2000)

            panel = QtWidgets.QWidget()
            pal   = QtGui.QPalette(QtGui.QColor(255, 255, 255))
            panel.setAutoFillBackground(True)
            panel.setPalette(pal)

            lic = (
                'THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND '
                'CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, '
                'INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF '
                'MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE '
                'DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR '
                'CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, '
                'SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT '
                'NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; '
                'LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) '
                'HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN '
                'CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR '
                'OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, '
                'EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.'
            )
            self.lic = QtWidgets.QTextEdit(lic)
            self.lic.setReadOnly(True)

            button_title = 'Agree'
            self.wdg1 = QtWidgets.QPushButton(button_title, self)
            self.wdg1.setCheckable(False)
            self.wdg1.setFixedSize(int(iw * 0.2), int(iw * 0.05))
            self.wdg1.clicked[bool].connect(self.accept)

            button_title = 'Quit'
            self.wdg2 = QtWidgets.QPushButton(button_title, self)
            self.wdg2.setCheckable(False)
            self.wdg2.setFixedSize(int(iw * 0.2), int(iw * 0.05))
            self.wdg2.clicked[bool].connect(self.reject)

            buf         = 'Click Agree to start GPI or Quit to exit.'
            splash_font = 'Segoe UI' if sys.platform == 'win32' else 'gill sans'
            new_fw      = iw * 0.45
            for fw_i in range(20, 0, -1):
                f   = QtGui.QFont(splash_font, fw_i)
                fm  = QtGui.QFontMetricsF(f)
                cfw = fm.horizontalAdvance(buf)
                if cfw < new_fw:
                    break
            f = QtGui.QFont(splash_font, fw_i)

            self.prompt = QtWidgets.QLabel(buf)
            self.prompt.setAlignment(QtCore.Qt.AlignCenter)
            self.prompt.setFont(f)

            wdgLayout = QtWidgets.QHBoxLayout()
            wdgLayout.addWidget(self.prompt)
            wdgLayout.addWidget(self.wdg1)
            wdgLayout.addWidget(self.wdg2)

            vbox_p = QtWidgets.QVBoxLayout()
            vbox_p.setContentsMargins(10, 10, 10, 10)
            vbox_p.setSpacing(10)
            vbox_p.addWidget(self.lic)
            vbox_p.addLayout(wdgLayout)
            panel.setLayout(vbox_p)

            vbox = QtWidgets.QVBoxLayout()
            vbox.setContentsMargins(0, 0, 0, 0)
            vbox.setSpacing(0)
            vbox.addSpacerItem(QtWidgets.QSpacerItem(
                iw, int((1 - 0.28) * ih),
                hPolicy=QtWidgets.QSizePolicy.Minimum,
                vPolicy=QtWidgets.QSizePolicy.Minimum))
            vbox.addWidget(panel)

            if INCLUDE_EULA:
                self.setLayout(vbox)

            self._accept = False

        def mousePressEvent(self, event):
            pass

        def accept(self):
            self.terms_accepted.emit()

        def reject(self):
            QtCore.QCoreApplication.instance().quit()

    # start main application
    # HiDPI — must be set before QApplication is created.
    # AA_Enable/UseHighDpi* exist in PyQt5 only; PyQt6 enables them unconditionally.
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
    try:
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)
    except AttributeError:
        pass  # PyQt6: always on, attributes removed
    try:
        QtWidgets.QApplication.setHighDpiScaleFactorRoundingPolicy(
            QtCore.Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    except AttributeError:
        pass  # Qt < 5.14 or PyQt6 where PassThrough is already the default
    app = QtWidgets.QApplication(sys.argv)
    app.setWindowIcon(QtGui.QIcon(ICON_PATH))

    Commands.parse(app.arguments())

    widget = MainCanvas()

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
            app.processEvents()
        else:
            dummy = QtWidgets.QSplashScreen()
            dummy.show()
            dummy.finish(widget)
            widget.show()
            widget.raise_()

    sys.exit(app.exec())


if __name__ == '__main__':
    launch()
