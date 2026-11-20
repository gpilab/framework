import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import textwrap
import unittest
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import gpi


ROOT = Path(__file__).resolve().parent.parent
path = ROOT / 'gpi_core' / 'display' / 'GPI' / 'Matplotlib3D_GPI.py'
spec = importlib.util.spec_from_file_location('matplotlib3d', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class TestMatplotlib3D(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = gpi.QtWidgets.QApplication.instance() or gpi.QtWidgets.QApplication([])

    def test_restoring_square_axes_updates_plot_and_schedules_redraw(self):
        with patch.object(module, '_probe_opengl_functional', return_value=False):
            widget = module.MatplotDisplay3D('Plot')
        self.addCleanup(widget.deleteLater)
        self.addCleanup(widget._updatetimer.stop)
        for enabled in (True, False):
            with self.subTest(enabled=enabled):
                widget._updatetimer.stop()
                widget.set_square_axes(enabled)
                self.assertEqual(widget.get_square_axes(), enabled)
                self.assertTrue(widget._updatetimer.isActive())
                widget._on_draw()
                aspect = widget.axes.get_box_aspect()
                self.assertAlmostEqual(aspect[0] / aspect[2],
                                       1.0 if enabled else 4.0 / 3.0)

    def test_launch_shares_shaders_across_windows_and_reparenting(self):
        code = textwrap.dedent(r'''
            import sys
            from unittest.mock import patch
            import numpy as np
            from OpenGL import GL
            from gpi import QtCore, QtGui, QtWidgets
            import gpi.launch as launcher
            from pyqtgraph.opengl import GLViewWidget, GLLinePlotItem

            class Finished(Exception):
                pass

            def check_views():
                app = QtWidgets.QApplication.instance()
                views = []
                parent = QtWidgets.QWidget()
                parent.resize(32, 32)
                parent.move(-10000, -10000)
                try:
                    for _ in range(2):
                        view = GLViewWidget()
                        views.append(view)
                        view.resize(32, 32)
                        view.move(-10000, -10000)
                        view.show()
                        app.processEvents()
                        if view.context() is None or not view.context().isValid():
                            sys.exit(77)
                    assert QtGui.QOpenGLContext.areSharing(
                        views[0].context(), views[1].context())
                    for view in views:
                        view.makeCurrent()
                        program = GLLinePlotItem.getShaderProgram()
                        assert GL.glIsProgram(program)
                        view.doneCurrent()
                        view.addItem(GLLinePlotItem(pos=np.array(
                            [[0, 0, 0], [1, 1, 1]], dtype=np.float32)))
                        assert not view.grabFramebuffer().isNull()
                    views[0].setParent(parent)
                    parent.show()
                    views[0].show()
                    app.processEvents()
                    views[0].makeCurrent()
                    assert GL.glIsProgram(program)
                    views[0].doneCurrent()
                    assert not views[0].grabFramebuffer().isNull()
                    for view in views:
                        view.makeCurrent()
                        with program:
                            pass
                        view.doneCurrent()
                finally:
                    for view in views:
                        view.close()
                        view.deleteLater()
                    parent.close()
                    parent.deleteLater()
                    QtCore.QCoreApplication.sendPostedEvents(
                        None, QtCore.QEvent.DeferredDelete)
                raise Finished()

            with patch.object(launcher, '_enable_crashlog'), \
                 patch.object(launcher, '_arm_startup_hang_watchdog'), \
                 patch('gpi.cmd.Commands.parse'), \
                 patch('gpi.mainWindow.MainCanvas', side_effect=check_views):
                try:
                    launcher.launch()
                except Finished:
                    pass
        ''')
        result = subprocess.run(
            [sys.executable, '-c', code], cwd=ROOT, capture_output=True,
            text=True, timeout=60)
        if result.returncode == 77:
            self.skipTest('No functional OpenGL widget context on this platform')
        output = result.stdout + result.stderr
        self.assertEqual(result.returncode, 0, output)
        self.assertNotIn('Error while drawing item', output)
        self.assertNotIn('GLError', output)


if __name__ == '__main__':
    unittest.main()
