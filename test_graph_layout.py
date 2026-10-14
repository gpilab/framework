"""Focused tests for Ctrl+O's Qt-independent layered layout."""

import importlib.util
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch


spec = importlib.util.spec_from_file_location(
    "graph_layout", Path(__file__).parent / "gpi" / "graph_layout.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
layered_layout = module.layered_layout


class LayeredLayoutTests(unittest.TestCase):
    def layout(self, nodes, edges, horizontal=False, port_edges=()):
        sizes = {node: (90 + index * 7, 45 + index * 9)
                 for index, node in enumerate(nodes)}
        positions = layered_layout(nodes, edges, sizes, horizontal, port_edges)
        self.assertEqual(set(positions), set(nodes))
        for index, first in enumerate(nodes):
            for second in nodes[index + 1:]:
                self.assertTrue(
                    abs(positions[first][0] - positions[second][0]) >=
                    (sizes[first][0] + sizes[second][0]) / 2 - 1e-7 or
                    abs(positions[first][1] - positions[second][1]) >=
                    (sizes[first][1] + sizes[second][1]) / 2 - 1e-7,
                    f"Overlapping nodes: {first}, {second}")
        return positions

    def test_converging_branches_and_long_bypass(self):
        nodes = list("abcdefg")
        edges = [("a", "b"), ("b", "c"), ("c", "d"), ("d", "g"),
                 ("a", "e"), ("e", "f"), ("f", "g"), ("a", "g")]
        for horizontal in (False, True):
            positions = self.layout(nodes, edges, horizontal)
            flow_axis = 0 if horizontal else 1
            for source, dest in edges:
                self.assertLess(positions[source][flow_axis], positions[dest][flow_axis])
            self.assertAlmostEqual(positions["d"][flow_axis], positions["f"][flow_axis])

    def test_crossing_reduction(self):
        edges = [("a", "d"), ("b", "c"), ("root", "a"), ("root", "b"),
                 ("c", "sink"), ("d", "sink")]
        positions = self.layout(["root", "a", "b", "c", "d", "sink"], edges)
        self.assertGreater((positions["a"][0] - positions["b"][0]) *
                           (positions["d"][0] - positions["c"][0]), 0)

    def test_cycles_parallel_edges_and_disconnected_nodes(self):
        nodes = list("abcdef")
        edges = [("a", "b"), ("b", "c"), ("c", "a"),
                 ("a", "b"), ("c", "c"), ("d", "e")]
        for horizontal in (False, True):
            first = self.layout(nodes, edges, horizontal)
            self.assertEqual(first, self.layout(nodes, list(reversed(edges)), horizontal))

    def test_empty_and_isolated_nodes(self):
        self.assertEqual(layered_layout([], [], {}), {})
        self.layout(["only"], [])
        self.layout(list("abc"), [])

    def test_input_port_order_overrides_source_creation_order(self):
        sources = ["read3", "read0", "read4", "read1", "read2"]
        nodes = sources + ["nc3dcs"]
        edges = [(source, "nc3dcs") for source in sources]
        port_edges = [(source, "nc3dcs", 0, int(source[-1])) for source in sources]
        for horizontal in (False, True):
            positions = self.layout(nodes, edges, horizontal, port_edges)
            cross_axis = 1 if horizontal else 0
            ordered = sorted(sources, key=lambda node: positions[node][cross_axis])
            self.assertEqual(ordered, [f"read{index}" for index in range(5)])
            self.assertEqual(positions, self.layout(nodes, list(reversed(edges)), horizontal,
                                                    list(reversed(port_edges))))

    def test_output_port_order_for_equivalent_children(self):
        children = ["out2", "out0", "out1"]
        nodes = ["split"] + children
        edges = [("split", child) for child in children]
        port_edges = [("split", child, int(child[-1]), 0) for child in children]
        for horizontal in (False, True):
            positions = self.layout(nodes, edges, horizontal, port_edges)
            cross_axis = 1 if horizontal else 0
            self.assertEqual(sorted(children, key=lambda node: positions[node][cross_axis]),
                             ["out0", "out1", "out2"])


class CanvasOrganizeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from gpi import QtCore, QtWidgets
        from gpi.canvasGraph import GraphWidget
        from gpi.config import Config

        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        cls.config = Config
        cls.organize = staticmethod(GraphWidget.organizeSelectedNodes)

        class LayoutNode(QtWidgets.QGraphicsObject):
            def __init__(self, identifier):
                super().__init__()
                self.identifier = identifier
                self.inportList = []
                self.outportList = []
                self.setPos(identifier * 37, identifier * -23)

            def getID(self):
                return self.identifier

            def boundingRect(self):
                return QtCore.QRectF(-13, -13, 90 + self.identifier * 5,
                                    50 + self.identifier * 7)

            def paint(self, painter, option, widget=None):
                pass

        cls.node_class = LayoutNode

    def setUp(self):
        self.config = SimpleNamespace(APPEARANCE_STYLE="Dark", LAYOUT_DIRECTION="Horizontal")
        settings = patch.dict(self.organize.__globals__, {"Config": self.config})
        settings.start()
        self.addCleanup(settings.stop)

    def test_animation_repeatability_and_selection(self):
        original_style = self.config.APPEARANCE_STYLE
        original_direction = self.config.LAYOUT_DIRECTION
        try:
            for style, direction in (("Dark", "Horizontal"), ("Dark", "Vertical"),
                                     ("Classic", "Horizontal")):
                self.config.APPEARANCE_STYLE = style
                self.config.LAYOUT_DIRECTION = direction
                nodes = [self.node_class(index) for index in range(5)]
                for source, dest in ((nodes[0], nodes[1]), (nodes[0], nodes[2]),
                                     (nodes[1], nodes[3]), (nodes[2], nodes[3]),
                                     (nodes[3], nodes[4])):
                    edge = SimpleNamespace(
                        source=SimpleNamespace(portNum=len(source.outportList)),
                        dest=SimpleNamespace(getNode=lambda dest=dest: dest,
                                             portNum=len(dest.inportList)))
                    source.outportList.append(SimpleNamespace(edgeList=[edge]))
                    dest.inportList.append(SimpleNamespace(edgeList=[edge]))
                selected = nodes[:4]
                canvas = SimpleNamespace(getSelectedNodes=lambda: list(reversed(selected)))
                original_center = sum((node.pos() for node in selected), nodes[0].pos() * 0) / 4
                outside_position = nodes[4].pos()
                self.organize(canvas)
                canvas._node_anim_group.setCurrentTime(canvas._node_anim_group.duration())
                first_positions = [node.pos() for node in selected]
                new_center = sum(first_positions, nodes[0].pos() * 0) / 4
                self.assertAlmostEqual(original_center.x(), new_center.x())
                self.assertAlmostEqual(original_center.y(), new_center.y())
                self.assertEqual(nodes[4].pos(), outside_position)
                for index, node in enumerate(selected):
                    for other in selected[index + 1:]:
                        self.assertFalse(node.mapRectToScene(node.boundingRect()).intersects(
                            other.mapRectToScene(other.boundingRect())))
                canvas.getSelectedNodes = lambda: selected
                self.organize(canvas)
                canvas._node_anim_group.setCurrentTime(canvas._node_anim_group.duration())
                for node, previous in zip(selected, first_positions):
                    self.assertAlmostEqual(node.pos().x(), previous.x())
                    self.assertAlmostEqual(node.pos().y(), previous.y())
                self.assertIs(nodes[3].outportList[0].edgeList[0].dest.getNode(), nodes[4])
        finally:
            self.config.APPEARANCE_STYLE = original_style
            self.config.LAYOUT_DIRECTION = original_direction

    def test_empty_selection(self):
        canvas = SimpleNamespace(getSelectedNodes=lambda: [])
        self.organize(canvas)
        self.assertFalse(hasattr(canvas, "_node_anim_group"))

    def test_canvas_forwards_input_port_order(self):
        for direction in ("Horizontal", "Vertical"):
            self.config.LAYOUT_DIRECTION = direction
            sources = [self.node_class(index) for index in range(5)]
            dest = self.node_class(5)
            input_ports = [8, 0, 6, 2, 4]
            for source, input_index in zip(sources, input_ports):
                edge = SimpleNamespace(
                    source=SimpleNamespace(portNum=0),
                    dest=SimpleNamespace(getNode=lambda: dest, portNum=input_index))
                source.outportList.append(SimpleNamespace(edgeList=[edge]))
                dest.inportList.append(SimpleNamespace(edgeList=[edge]))
            canvas = SimpleNamespace(getSelectedNodes=lambda: [dest] + list(reversed(sources)))
            self.organize(canvas)
            canvas._node_anim_group.setCurrentTime(canvas._node_anim_group.duration())
            ordered = sorted(sources, key=lambda node: (
                node.mapRectToScene(node.boundingRect()).center().y()
                if direction == "Horizontal" else
                node.mapRectToScene(node.boundingRect()).center().x()))
            self.assertEqual([input_ports[sources.index(node)] for node in ordered],
                             sorted(input_ports))


if __name__ == "__main__":
    unittest.main()