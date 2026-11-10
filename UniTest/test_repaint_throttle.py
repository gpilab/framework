"""Test that canvas repaints are throttled to ~60fps via requestRepaint()."""
import sys
import time

from gpi import QtCore, QtWidgets
app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

from gpi.canvasGraph import GraphWidget

# Build a minimal GraphWidget (needs a Library scan stub — use noGUI mode)
from gpi.cmd import Commands
Commands._noGUI = True   # suppress actual painting in _doRepaint

gw = GraphWidget(title="test_canvas", parent=None)

# ── 1. Structural: _repaint_timer is single-shot, 16ms ───────────────────────
assert hasattr(gw, '_repaint_timer'), "FAIL: no _repaint_timer"
assert hasattr(gw, '_repaint_pending'), "FAIL: no _repaint_pending"
assert gw._repaint_timer.isSingleShot(), "FAIL: timer must be single-shot"
assert gw._repaint_timer.interval() == 16, f"FAIL: expected 16ms, got {gw._repaint_timer.interval()}"
print("PASS: _repaint_timer is single-shot at 16ms")

# ── 2. _repaint_pending flag set immediately on requestRepaint() ─────────────
# Reset any pending state from __init__ before testing
gw._repaint_timer.stop()
gw._repaint_pending = False
gw.requestRepaint()
assert gw._repaint_pending, "FAIL: _repaint_pending not set after requestRepaint()"
print("PASS: _repaint_pending set after requestRepaint()")

# ── 3. Multiple calls before timer fires don't stack ────────────────────────
# Manually reset and call many times
gw._repaint_timer.stop()
gw._repaint_pending = False

call_count = [0]
original_do = gw._doRepaint
def counting_repaint():
    call_count[0] += 1
    original_do()
gw._doRepaint = counting_repaint
gw._repaint_timer.timeout.disconnect()
gw._repaint_timer.timeout.connect(counting_repaint)

# Fire 50 requests in the same event-loop tick
for _ in range(50):
    gw.requestRepaint()

# Timer hasn't fired yet — pending should be True
assert gw._repaint_pending, "FAIL: pending should still be True"

# Let the timer fire
deadline = time.time() + 1
while gw._repaint_pending and time.time() < deadline:
    app.processEvents(QtCore.QEventLoop.AllEvents, 20)

assert call_count[0] == 1, f"FAIL: expected 1 repaint, got {call_count[0]}"
assert not gw._repaint_pending, "FAIL: pending should be False after paint"
print(f"PASS: 50 requestRepaint() calls collapsed into {call_count[0]} actual repaint")

# ── 4. viewAndSceneForcedUpdate delegates to requestRepaint ─────────────────
gw._repaint_pending = False
gw._repaint_timer.stop()
gw.viewAndSceneForcedUpdate()
assert gw._repaint_pending, "FAIL: viewAndSceneForcedUpdate should set _repaint_pending"
gw._repaint_timer.stop()
gw._repaint_pending = False
print("PASS: viewAndSceneForcedUpdate delegates to requestRepaint()")

# ── 5. No legacy _timer ──────────────────────────────────────────────────────
assert not hasattr(gw, '_timer'), "FAIL: legacy _timer still present"
print("PASS: legacy _timer removed")

print("\nAll repaint throttle tests passed.")
