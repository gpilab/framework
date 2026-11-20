"""Classic keeps the original node sizing and stacked text layout."""

import os
from types import MethodType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from gpi import QtCore, QtGui, QtWidgets
from gpi.node import Node, NodeAppearance


class ClassicAppearanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def make_node(self):
        appearance = NodeAppearance()
        node = SimpleNamespace(
            name="ReadHDF5",
            title_font=appearance.titleQFont(),
            _label_font=appearance.labelQFont(),
            _detailLabel_font=appearance.textQFont(),
            _label_inset=0, _detailLabel_inset=0, _label_maxLen=64,
            _left_margin=5, _right_margin=11, _top_margin=6, _bottom_margin=7,
            inportList=[], outportList=[], _load_failed=False, beingHovered=False,
            _nodeIF=SimpleNamespace(
                getLabel=lambda: "Selected data",
                getDetailLabel=lambda: "A long file path with enough text to widen the node",
                getDetailLabelElideMode=lambda: QtCore.Qt.ElideMiddle),
            getCurState=lambda: None,
            _computeState=object(), _computeErrorState=object(),
            _validateError=object(), _initUIErrorState=object(),
            isSelected=lambda: False, isWaiting=lambda: False, progressON=lambda: False,
            _reload_timer=SimpleNamespace(isActive=lambda: False),
            _progress_done=SimpleNamespace(isActive=lambda: False),
            drawProcessingRim=Mock(),
        )
        for name in (
            "getTitleSize", "getLabelSize", "getDetailLabelSize", "getMaxPortWidth",
            "getNodeWidth", "getNodeHeight", "getNodeWidth_V", "getNodeHeight_V",
            "_isHorizontalFlow", "_currentNodeWidth", "getOutPortVOffset",
        ):
            setattr(node, name, MethodType(getattr(Node, name), node))
        return node

    def test_classic_sizes_detail_label_like_develop(self):
        node = self.make_node()
        with patch("gpi.node.Config", SimpleNamespace(APPEARANCE_STYLE="Classic")):
            metrics = QtGui.QFontMetricsF(node._detailLabel_font)
            detail = metrics.elidedText(
                node._nodeIF.getDetailLabel(), QtCore.Qt.ElideMiddle,
                node.getTitleSize()[0] * 3)
            expected_width = metrics.horizontalAdvance(detail) + node._right_margin
            self.assertAlmostEqual(node.getDetailLabelSize()[0], expected_width)
            self.assertAlmostEqual(node.getNodeWidth(), expected_width)
            self.assertGreater(node.getNodeWidth(), node.getTitleSize()[0])
            self.assertAlmostEqual(
                node.getOutPortVOffset(),
                node.getLabelSize()[1] + node.getDetailLabelSize()[1] + 9)

    def test_classic_text_rows_do_not_overlap_and_body_has_no_shadow(self):
        node = self.make_node()
        with patch("gpi.node.Config", SimpleNamespace(APPEARANCE_STYLE="Classic")):
            painter = Mock()
            Node.paint(node, painter, QtWidgets.QStyleOptionGraphicsItem(), None)
            rows = [call.args[0] for call in painter.drawText.call_args_list]
            self.assertEqual(len(rows), 3)
            self.assertEqual(rows[0].top(), -node._top_margin)
            self.assertEqual(rows[0].height(), node.getTitleSize()[1])
            self.assertLessEqual(rows[0].bottom(), rows[1].top())
            self.assertLessEqual(rows[1].bottom(), rows[2].top())
            painter.drawRoundedRect.assert_called_once()

            node.getCurState = lambda: node._computeState
            Node.paint(node, Mock(), QtWidgets.QStyleOptionGraphicsItem(), None)
            node.drawProcessingRim.assert_not_called()

    def test_classic_and_dark_render_with_real_qpainter(self):
        node = self.make_node()
        for theme in ("Classic", "Dark"):
            for mode in (QtCore.Qt.ElideMiddle, "wrap"):
                with self.subTest(theme=theme, mode=mode):
                    node._nodeIF.getDetailLabelElideMode = lambda mode=mode: mode
                    settings = SimpleNamespace(
                        APPEARANCE_STYLE=theme, LAYOUT_DIRECTION="Vertical")
                    with patch("gpi.node.Config", settings):
                        image = QtGui.QImage(500, 300, QtGui.QImage.Format_ARGB32)
                        image.fill(QtCore.Qt.transparent)
                        painter = QtGui.QPainter(image)
                        painter.translate(20, 20)
                        try:
                            Node.paint(node, painter, QtWidgets.QStyleOptionGraphicsItem(), None)
                        finally:
                            painter.end()
                        self.assertGreater(image.pixelColor(20, 20).alpha(), 0)
                        if theme == "Dark":
                            self.assertEqual(
                                node.getNodeWidth(),
                                max(node.getTitleSize()[0], node.getLabelSize()[0], 4))


if __name__ == "__main__":
    unittest.main()
