"""Test that TTask uses QRunnable + thread pool instead of QThread."""
import sys
import time
import threading

# Need a QApplication before importing Qt widgets
from gpi import QtCore, QtWidgets
app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

from gpi.functor import TTask, _TTaskSignals

def wait_with_events(event, timeout=5):
    """Wait for a threading.Event while pumping the Qt event loop."""
    deadline = time.time() + timeout
    while not event.is_set() and time.time() < deadline:
        app.processEvents(QtCore.QEventLoop.AllEvents, 50)
    return event.is_set()

# 1. Class hierarchy
assert issubclass(TTask, QtCore.QRunnable), "TTask must be QRunnable"
assert not issubclass(TTask, QtCore.QThread), "TTask must NOT be QThread"
print("PASS: TTask is QRunnable, not QThread")

# 2. Signal interface
task = TTask(lambda: 0, "test", "label", None)
assert hasattr(task, "finished"), "must have finished signal"
assert hasattr(task, "terminated"), "must have terminated signal"
assert hasattr(task, "_retcode"), "must have _retcode"
print("PASS: signals and _retcode present")

# 3. Successful compute
done = threading.Event()
task2 = TTask(lambda: 0, "success_node", "label", None)
task2.finished.connect(lambda: done.set())
task2.start()
assert wait_with_events(done), "FAIL: task did not complete within 5s"
assert task2._retcode == 0, f"FAIL: expected retcode 0, got {task2._retcode}"
assert not task2.isRunning(), "FAIL: isRunning should be False after completion"
print(f"PASS: successful compute — retcode={task2._retcode}, isRunning={task2.isRunning()}")

# 4. Error handling — compute raises, retcode should be ComputeError (-1)
done3 = threading.Event()
def bad_compute():
    raise ValueError("intentional error")
task3 = TTask(bad_compute, "error_node", "label", None)
task3.finished.connect(lambda: done3.set())
task3.start()
assert wait_with_events(done3), "FAIL: error task did not complete"
from gpi.functor import Return
assert Return.isComputeError(task3._retcode), f"FAIL: expected ComputeError, got {task3._retcode}"
print(f"PASS: error handling — retcode={task3._retcode} (ComputeError)")

# 5. Thread pool reuse — run 5 tasks, verify all complete
pool = QtCore.QThreadPool.globalInstance()
dones = [threading.Event() for _ in range(5)]
tasks = []
for i, d in enumerate(dones):
    t = TTask(lambda: 0, f"node{i}", "label", None)
    t.finished.connect(d.set)
    tasks.append(t)
for t in tasks:
    t.start()
all_done = threading.Event()
def check_all():
    if all(d.is_set() for d in dones):
        all_done.set()
# poll until all done
deadline = time.time() + 5
while not all_done.is_set() and time.time() < deadline:
    app.processEvents(QtCore.QEventLoop.AllEvents, 50)
    if all(d.is_set() for d in dones):
        all_done.set()
assert all_done.is_set(), "FAIL: not all 5 tasks completed"
print(f"PASS: 5 concurrent tasks completed via pool (maxThreadCount={pool.maxThreadCount()})")

print("\nAll tests passed.")
