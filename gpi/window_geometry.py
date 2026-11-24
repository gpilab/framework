"""Initial window placement for WSLg's multi-monitor desktop."""

import os

from gpi import QtCore, QtGui


def _target_screen(reference):
    screen = reference.window().screen() if reference is not None else None
    if screen is None:
        screen = QtGui.QGuiApplication.screenAt(QtGui.QCursor.pos())
    if screen is None:
        screen = QtGui.QGuiApplication.primaryScreen()
    return screen


def place_initial_window(window, reference=None, *, preferred_size=None):
    """Keep a newly opened WSLg window within its target screen."""
    if not os.environ.get('WSL_DISTRO_NAME') or not os.environ.get('WAYLAND_DISPLAY'):
        return

    screen = _target_screen(reference)
    if screen is None:
        return

    available = screen.availableGeometry()
    # Qt sees the Linux output, not the Windows work area or host-side frame.
    # Leave room for WSLg's host scaling, decorations, and the taskbar.
    width_limit = max(1, available.width() * 3 // 4)
    height_limit = max(1, available.height() * 3 // 4)
    desired = window.sizeHint() if preferred_size is None else preferred_size
    desired = desired.expandedTo(window.minimumSizeHint())
    desired = desired.expandedTo(window.minimumSize())
    width = max(1, min(desired.width(), width_limit))
    height = max(1, min(desired.height(), height_limit))
    window.resize(width, height)
    window.move(available.center() - QtCore.QPoint(window.width() // 2,
                                                    window.height() // 2))

    if QtGui.QGuiApplication.platformName() == 'xcb':
        # XWayland can replace the requested position when the window maps.
        def recover_if_clipped():
            if not window.isVisible() or window.isMaximized() or window.isFullScreen():
                return
            frame = window.frameGeometry()
            title = QtCore.QRect(frame.x(), frame.y(), frame.width(), min(32, frame.height()))
            if any(output.availableGeometry().contains(title)
                   for output in QtGui.QGuiApplication.screens()):
                return
            target = _target_screen(reference)
            if target is not None:
                offset = QtCore.QPoint(frame.width() // 2, frame.height() // 2)
                window.move(target.availableGeometry().center() - offset)

        timer = QtCore.QTimer(window)
        timer.setSingleShot(True)
        timer.timeout.connect(recover_if_clipped)
        timer.timeout.connect(timer.deleteLater)
        timer.start(250)
