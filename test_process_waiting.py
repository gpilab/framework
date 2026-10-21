import os
import multiprocessing
import pickle
import tempfile
import time
import unittest
from concurrent.futures import Future, ProcessPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from gpi import QtCore, QtGui, QtWidgets
from gpi.defines import GPI_APPLOOP, GPI_PROCESS, GPI_THREAD
from gpi.functor import GPIFunctor, _FutureWatcher
from gpi.node import Node


def _worker_task(pid_file, release_file=None):
    Path(pid_file).write_text(str(os.getpid()))
    if release_file:
        deadline = time.monotonic() + 15
        while not Path(release_file).exists():
            if time.monotonic() > deadline:
                raise TimeoutError('Test worker was not released')
            time.sleep(0.01)
    return ('direct', pickle.dumps([['retcode', 0]]))


class TestProcessWaiting(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def pump_until(self, predicate):
        deadline = time.monotonic() + 3
        while not predicate() and time.monotonic() < deadline:
            self.app.processEvents(QtCore.QEventLoop.AllEvents, 20)
            time.sleep(0.01)
        self.assertTrue(predicate())

    def test_worker_marker_not_future_running_signals_start(self):
        with tempfile.TemporaryDirectory() as directory:
            pid_file = Path(directory) / 'worker.pid'
            pid_file.touch()
            future = Future()
            # ProcessPoolExecutor marks dispatched tasks running before a
            # worker is available to execute them.
            future.set_running_or_notify_cancel()
            watcher = _FutureWatcher(future, pid_file=str(pid_file))
            watcher.finished.disconnect(watcher._release)
            started = Mock()
            completed = Mock()
            watcher._started.connect(started)
            watcher._complete.connect(completed)
            watcher.start()
            try:
                self.pump_until(lambda: watcher.isRunning())
                time.sleep(0.15)
                self.app.processEvents()
                started.assert_not_called()
                pid_file.write_text(str(os.getpid()))
                self.pump_until(lambda: started.call_count == 1)
                future.set_result(('direct', pickle.dumps([['retcode', 0]])))
                self.pump_until(lambda: completed.call_count == 1)
                started.assert_called_once_with()
                completed.assert_called_once_with([['retcode', 0]])
            finally:
                if not future.done():
                    future.set_result(('direct', pickle.dumps([['retcode', 0]])))
                watcher.wait(3000)
                watcher._release()
                self.app.processEvents()

    def test_already_finished_worker_still_signals_start_before_completion(self):
        with tempfile.TemporaryDirectory() as directory:
            pid_file = Path(directory) / 'worker.pid'
            pid_file.write_text(str(os.getpid()))
            future = Future()
            future.set_result(('direct', pickle.dumps([['retcode', 0]])))
            watcher = _FutureWatcher(future, pid_file=str(pid_file))
            events = []
            watcher._started.connect(lambda: events.append('started'))
            watcher._complete.connect(lambda result: events.append('complete'))
            watcher.run()
            self.assertEqual(events, ['started', 'complete'])
            watcher._release()

    def test_second_process_waits_for_the_single_worker(self):
        with tempfile.TemporaryDirectory() as directory:
            first_pid = Path(directory) / 'first.pid'
            second_pid = Path(directory) / 'second.pid'
            release = Path(directory) / 'release'
            second_pid.touch()
            with ProcessPoolExecutor(max_workers=1,
                                     mp_context=multiprocessing.get_context('spawn')) as executor:
                first = executor.submit(_worker_task, str(first_pid), str(release))
                watcher = None
                try:
                    self.pump_until(first_pid.exists)
                    second = executor.submit(_worker_task, str(second_pid))
                    watcher = _FutureWatcher(second, pid_file=str(second_pid))
                    watcher.finished.disconnect(watcher._release)
                    started = Mock()
                    completed = Mock()
                    watcher._started.connect(started)
                    watcher._complete.connect(completed)
                    watcher.start()
                    self.pump_until(second.running)
                    self.app.processEvents()
                    started.assert_not_called()
                    self.assertEqual(second_pid.stat().st_size, 0)
                    release.touch()
                    self.pump_until(lambda: completed.call_count == 1)
                    started.assert_called_once_with()
                    completed.assert_called_once_with([['retcode', 0]])
                    self.assertEqual(first.result(), second.result())
                finally:
                    release.touch()
                    if watcher is not None:
                        watcher.wait(5000)
                        watcher._release()
                        self.app.processEvents()

    def make_functor(self, exec_type):
        node = Mock()
        node.name = 'test'
        node._nodeIF.execType.return_value = exec_type
        node.getModuleValidate.return_value = lambda: 0
        node.getModuleCompute.return_value = lambda: 0
        return node, GPIFunctor(node)

    def test_process_waits_then_resets_progress_clock_on_start(self):
        node, functor = self.make_functor(GPI_PROCESS)
        self.assertFalse(functor.isWaiting())
        with patch.object(functor._proc, 'start'), patch('gpi.functor.time.time', return_value=10):
            functor.start()
        self.assertTrue(functor.isWaiting())
        with patch('gpi.functor.time.time', return_value=30):
            functor._proc.started.emit()
        self.assertFalse(functor.isWaiting())
        with patch('gpi.functor.time.time', return_value=32):
            self.assertEqual(functor.curTime(), 2)
        node._updateProgress.assert_called()
        functor.terminate()
        self.assertFalse(functor.isWaiting())

    def test_non_process_tasks_do_not_wait(self):
        for exec_type in (GPI_THREAD, GPI_APPLOOP):
            with self.subTest(exec_type=exec_type):
                node, functor = self.make_functor(exec_type)
                with patch.object(functor._proc, 'start'):
                    functor.start()
                self.assertFalse(functor.isWaiting())

    def test_validation_failure_does_not_show_waiting(self):
        node, functor = self.make_functor(GPI_PROCESS)
        functor._validate = lambda: 1
        with patch.object(functor._proc, 'start') as start:
            functor.start()
        start.assert_not_called()
        self.assertFalse(functor.isWaiting())

    def test_process_completion_clears_waiting_even_without_start_notification(self):
        node, functor = self.make_functor(GPI_PROCESS)
        with patch.object(functor._proc, 'start'):
            functor.start()
        self.assertTrue(functor.isWaiting())
        with patch.object(functor, 'applyQueuedData'):
            functor.computeFinished()
        self.assertFalse(functor.isWaiting())

    def make_node(self, waiting=True):
        node = Mock()
        node._computeState = object()
        node.getCurState.return_value = node._computeState
        node.nodeCompute_thread.isWaiting.return_value = waiting
        node.isWaiting.side_effect = lambda: Node.isWaiting(node)
        node.maxWallTime.return_value = 5
        node._prog_thresh = 1
        node.nodeCompute_thread.curTime.return_value = 10
        node.progressON.side_effect = lambda: Node.progressON(node)
        node._isHorizontalFlow.return_value = False
        node.getNodeWidth.return_value = 100
        node.getNodeHeight.return_value = 30
        node._nodeIF = None
        node._load_failed = False
        node._progress_was_on = False
        node._left_margin = 10
        return node

    def test_waiting_draws_hourglass_without_progress_or_reload(self):
        node = self.make_node()
        self.assertFalse(Node.progressON(node))
        self.assertEqual(Node.getProgressWidth(node), 23)
        Node.paint(node, Mock(), SimpleNamespace(state=0), None)
        node.drawWaiting.assert_called_once()
        node.drawReload.assert_not_called()
        node.drawProgress.assert_not_called()
        node.drawRecalculating.assert_not_called()
        self.assertFalse(node._progress_was_on)

    def test_running_preserves_processing_animation(self):
        node = self.make_node(waiting=False)
        Node.paint(node, Mock(), SimpleNamespace(state=0), None)
        node.drawWaiting.assert_not_called()
        node.drawRecalculating.assert_called_once()
        self.assertTrue(node._progress_was_on)

    def test_idle_does_not_show_waiting(self):
        node = self.make_node()
        node.getCurState.return_value = object()
        self.assertFalse(Node.isWaiting(node))

    def test_hourglass_renders_in_both_themes_and_flow_directions(self):
        for style in ('Classic', 'Dark'):
            for width in (80, 140):
                with self.subTest(style=style, width=width):
                    image = QtGui.QImage(180, 40, QtGui.QImage.Format_ARGB32)
                    image.fill(QtCore.Qt.transparent)
                    painter = QtGui.QPainter(image)
                    painter.translate(10, 15)
                    node = SimpleNamespace(_currentNodeWidth=lambda: width)
                    try:
                        with patch('gpi.node.Config', SimpleNamespace(APPEARANCE_STYLE=style)):
                            Node.drawWaiting(node, painter)
                    finally:
                        painter.end()
                    pixels = [(x, y) for x in range(image.width())
                              for y in range(image.height())
                              if image.pixelColor(x, y).alpha()]
                    self.assertTrue(pixels)
                    self.assertTrue(all(width <= x <= width + 14 and 4 <= y <= 16
                                        for x, y in pixels))


if __name__ == '__main__':
    unittest.main()
