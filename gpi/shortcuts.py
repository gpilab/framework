import json

from gpi import QtCore, QtGui, Signal
from .config import Config


# Ordered list of configurable canvas shortcuts: (action_id, label, default_sequence)
CANVAS_SHORTCUT_DEFAULTS = [
    ("undo",          "Undo",                   "Ctrl+Z"),
    ("redo",          "Redo",                   "Ctrl+Y"),
    ("copy",          "Copy",                   "Ctrl+C"),
    ("paste",         "Paste",                  "Ctrl+V"),
    ("paste_connect", "Paste with Connections", "Ctrl+Shift+V"),
    ("delete",        "Delete Selected",        "Del"),
    ("select_all",    "Select All",             "Ctrl+A"),
    ("find",          "Find Node",              "Ctrl+F"),
    ("load",          "Load Network",           "Ctrl+L"),
    ("save",          "Save Network",           "Ctrl+S"),
    ("reload",        "Reload Node",            "Ctrl+R"),
    ("organize",      "Organize Nodes",         "Ctrl+O"),
    ("pause",         "Pause / Unpause",        "Ctrl+P"),
    ("close_menus",   "Close All Node Menus",   "Ctrl+X"),
    ("zoom_in",       "Zoom In",                "+"),
    ("zoom_out",      "Zoom Out",               "-"),
]

_DEFAULTS = {aid: seq for aid, _, seq in CANVAS_SHORTCUT_DEFAULTS}


class CanvasShortcuts(QtCore.QObject):
    """Configurable canvas key bindings backed by gpi_settings.json via Config."""

    changed = Signal()

    def __init__(self):
        super().__init__()
        self._bindings = {}   # {action_id: key_string}
        self._ks_cache = {}   # {action_id: QKeySequence}
        self.load()

    # ── Public API ────────────────────────────────────────────────────────────

    def load(self):
        self._bindings = dict(_DEFAULTS)
        overrides = Config.CANVAS_SHORTCUT_OVERRIDES
        self._bindings.update({k: v for k, v in overrides.items() if k in _DEFAULTS})
        self._rebuild_cache()

    def save(self, bindings):
        """Persist {action_id: key_string} into gpi_settings.json and emit changed."""
        self._bindings = bindings
        self._rebuild_cache()
        overrides = {k: v for k, v in bindings.items() if v != _DEFAULTS.get(k)}
        Config.CANVAS_SHORTCUT_OVERRIDES = overrides
        Config.saveConfigFile()
        self.changed.emit()

    def reset_to_defaults(self):
        self._bindings = dict(_DEFAULTS)
        self._rebuild_cache()
        Config.CANVAS_SHORTCUT_OVERRIDES = {}
        Config.saveConfigFile()
        self.changed.emit()

    def get(self, action_id):
        return self._bindings.get(action_id, _DEFAULTS.get(action_id, ''))

    def matches(self, action_id, key, modifiers):
        """Return True if key+modifiers matches the binding for action_id."""
        ks = self._ks_cache.get(action_id)
        if ks is None or ks.isEmpty():
            return False
        # PyQt5: int(enum) works directly.
        # PyQt6: KeyboardModifier/Key are proper Python enums; use .value.
        def _to_int(v):
            try:
                return int(v)
            except TypeError:
                return v.value
        pressed = QtGui.QKeySequence(_to_int(modifiers) | _to_int(key))
        no_match = getattr(QtGui.QKeySequence, 'NoMatch',
                           getattr(QtGui.QKeySequence.SequenceMatch, 'NoMatch', 0))
        return ks.matches(pressed) != no_match

    def all_bindings(self):
        """Return [(action_id, label, current_sequence)] for the settings UI."""
        return [(aid, lbl, self._bindings.get(aid, dflt))
                for aid, lbl, dflt in CANVAS_SHORTCUT_DEFAULTS]

    # ── Internal ──────────────────────────────────────────────────────────────

    def _rebuild_cache(self):
        self._ks_cache = {aid: QtGui.QKeySequence(ks) for aid, ks in self._bindings.items()}


# ── Node-deploy shortcuts ─────────────────────────────────────────────────────

class Shortcuts(QtCore.QObject):
    """Node-deploy shortcut model backed by gpi_settings.json via Config."""

    shortcuts_changed = Signal()

    def __init__(self):
        super().__init__()

    def parseShortcuts(self, data_only=False):
        """Return list of 'key:node' strings (data_only=True) or (key, node) pairs."""
        pairs = [(str(k), str(n)) for k, n in Config.NODE_SHORTCUTS if k and n]
        if data_only:
            return [f"{k}:{v}" for k, v in pairs]
        return pairs

    def savePairs(self, pairs):
        """Persist (key, node) pairs into gpi_settings.json and emit shortcuts_changed."""
        Config.NODE_SHORTCUTS = [[k, n] for k, n in pairs if k and n]
        Config.saveConfigFile()
        self.shortcuts_changed.emit()
