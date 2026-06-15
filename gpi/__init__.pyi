# Type stub for the gpi package — used by IDEs (Pylance, PyCharm) instead of
# __init__.py.  The runtime __init__.py has an if/else on GPI_WORKER_MODE that
# confuses static analysers; this stub always exposes the real, annotated API.

from typing import Any

# ── Core node base class and type aliases ─────────────────────────────────────
from .nodeAPI import NodeAPI as NodeAPI
from .nodeAPI import WidgetType as WidgetType
from .nodeAPI import PortType as PortType

# ── Constants used in initUI / compute ───────────────────────────────────────
from .defines import REQUIRED as REQUIRED
from .defines import OPTIONAL as OPTIONAL
from .defines import GPI_PROCESS as GPI_PROCESS
from .defines import GPI_THREAD as GPI_THREAD
from .defines import GPI_APPLOOP as GPI_APPLOOP
from .defines import GPI_PORT_EVENT as GPI_PORT_EVENT
from .defines import GPI_WIDGET_EVENT as GPI_WIDGET_EVENT
from .defines import GPI_INIT_EVENT as GPI_INIT_EVENT
from .defines import GPI_REQUEUE_EVENT as GPI_REQUEUE_EVENT

# ── Qt re-exports (nodes that do UI work import these from gpi) ───────────────
from PyQt6 import QtCore as QtCore
from PyQt6 import QtGui as QtGui
from PyQt6 import QtWidgets as QtWidgets
from PyQt6.QtCore import pyqtSignal as Signal
from PyQt6.QtCore import pyqtSlot as Slot

# ── Widget classes (node authors subclass or reference these) ─────────────────
from .widgets import GenericWidgetGroup as GenericWidgetGroup
from .widgets import BasicPushButton as BasicPushButton
from .widgets import BasicDoubleSpinBox as BasicDoubleSpinBox
from .widgets import BasicSpinBox as BasicSpinBox
from .widgets import BasicSlider as BasicSlider
from .widgets import BasicCWFCSliders as BasicCWFCSliders
from .widgets import HidableGroupBox as HidableGroupBox
from .widgets import SaveFileBrowser as SaveFileBrowser
from .widgets import OpenFileBrowser as OpenFileBrowser
from .widgets import TextEdit as TextEdit
from .widgets import TextBox as TextBox
from .widgets import StringBox as StringBox
from .widgets import DisplayBox as DisplayBox
from .widgets import WebBox as WebBox
from .widgets import PushButton as PushButton
from .widgets import DoubleSpinBox as DoubleSpinBox
from .widgets import SpinBox as SpinBox
from .widgets import Slider as Slider
from .widgets import ExclusivePushButtons as ExclusivePushButtons
from .widgets import NonExclusivePushButtons as NonExclusivePushButtons
from .widgets import ComboBox as ComboBox
from .widgets import ExclusiveRadioButtons as ExclusiveRadioButtons

# ── Version ───────────────────────────────────────────────────────────────────
VERSION: str
__version__: str
