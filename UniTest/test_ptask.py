"""Test that PTask uses a watcher thread instead of a 10ms QTimer poll."""
import sys
import time
import platform
import threading

from gpi import QtCore, QtWidgets
app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

from gpi.functor import _PTaskWatcher, PTask, Return

# ── 1. Structural: no QTimer in PTask ────────────────────────────────────────
assert not hasattr(PTask, '_timer'), "FAIL: PTask still has _timer class attr"
p = PTask(lambda: 0, "t", "l", None)
assert not hasattr(p, '_timer'), "FAIL: PTask instance still has _timer"
assert hasattr(p, '_watcher'), "FAIL: PTask has no _watcher attr"
print("PASS: PTask has no _timer; has _watcher")

# ── 2. _PTaskWatcher: completes when joined process exits ────────────────────
class FakeProcess:
    """Minimal duck-type for _PTaskWatcher — just needs join()."""
    def __init__(self, delay=0.05):
        self._delay = delay
        self._done = threading.Event()
        self._t = threading.Thread(target=self._work, daemon=True)

    def _work(self):
        time.sleep(self._delay)
        self._done.set()

    def start(self):
        self._t.start()

    def join(self):
        self._t.join()

fake = FakeProcess(delay=0.05)
fake.start()

watcher_fired = threading.Event()
watcher = _PTaskWatcher(fake)
watcher._complete.connect(lambda: watcher_fired.set())
watcher.start()

deadline = time.time() + 3
while not watcher_fired.is_set() and time.time() < deadline:
    app.processEvents(QtCore.QEventLoop.AllEvents, 20)

assert watcher_fired.is_set(), "FAIL: watcher did not fire after process exit"
print("PASS: _PTaskWatcher emits _complete when process exits (no polling)")

# ── 3. _PTaskWatcher: cancel() suppresses the signal ────────────────────────
fake2 = FakeProcess(delay=0.05)
fake2.start()

fired_after_cancel = threading.Event()
watcher2 = _PTaskWatcher(fake2)
watcher2._complete.connect(lambda: fired_after_cancel.set())
watcher2.cancel()   # cancel before start
watcher2.start()

deadline = time.time() + 0.5
while time.time() < deadline:
    app.processEvents(QtCore.QEventLoop.AllEvents, 20)

assert not fired_after_cancel.is_set(), "FAIL: watcher fired despite cancel()"
print("PASS: _PTaskWatcher.cancel() suppresses signal emission")

# ── 4. Full PTask integration (non-Windows only — spawn context works on macOS/Linux) ──
if platform.system() != 'Windows':
    import multiprocessing
    ctx = multiprocessing.get_context('fork')
    mgr = ctx.Manager()
    proxy = mgr.list()

    done_ev = threading.Event()
    result = {}

    def _compute():
        return 0   # success

    pt = PTask(_compute, "node", "label", proxy)
    # Wire up finished signal before start
    def _on_finished():
        result['fired'] = 'finished'
        done_ev.set()
    def _on_terminated():
        result['fired'] = 'terminated'
        done_ev.set()
    pt.finished.connect(_on_finished)
    pt.terminated.connect(_on_terminated)
    pt.start()

    deadline = time.time() + 10
    while not done_ev.is_set() and time.time() < deadline:
        app.processEvents(QtCore.QEventLoop.AllEvents, 50)

    mgr.shutdown()
    assert done_ev.is_set(), "FAIL: PTask did not complete within 10s"
    assert result.get('fired') == 'finished', f"FAIL: expected 'finished', got {result}"
    print(f"PASS: full PTask round-trip — signal={result['fired']}")
else:
    print("SKIP: full PTask process test skipped on Windows (GPI_PROCESS not used there)")

print("\nAll PTask tests passed.")
