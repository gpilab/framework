"""Size-aware Sugiyama layout for canvas nodes, independent of Qt."""

from grandalf.graphs import Edge, Graph, Vertex
from grandalf.layouts import SugiyamaLayout, VertexViewer


def layered_layout(nodes, edges, sizes, horizontal=False, port_edges=()):
    """Return node centers; input order provides deterministic tie-breaking.

    Feedback edges are reversed only inside the layout engine, never in the
    canvas. Virtual nodes reserve space for edges spanning multiple layers.
    Optional port edges are (source, destination, output index, input index)
    tuples used to order topologically interchangeable siblings.
    """
    if not nodes:
        return {}

    vertices = {node: Vertex(node) for node in nodes}
    order = {node: index for index, node in enumerate(nodes)}
    for node, vertex in vertices.items():
        width, height = sizes[node]
        vertex.view = (VertexViewer(height, width) if horizontal
                       else VertexViewer(width, height))

    pairs = sorted({(source, dest) for source, dest in edges
                    if source in vertices and dest in vertices and source != dest},
                   key=lambda pair: (order[pair[0]], order[pair[1]]))
    graph = Graph(list(vertices.values()),
                  [Edge(vertices[source], vertices[dest]) for source, dest in pairs])
    incoming_ports = {node: [] for node in nodes}
    outgoing_ports = {node: [] for node in nodes}
    for source, dest, output_index, input_index in port_edges:
        if source in vertices and dest in vertices and source != dest:
            outgoing_ports[source].append((order[dest], input_index))
            incoming_ports[dest].append((order[source], output_index))

    positions = {}
    cross_cursor = 0.0
    for component in sorted(graph.C, key=lambda comp: min(order[v.data] for v in comp.V())):
        layout = SugiyamaLayout(component)
        layout.xspace = 15
        layout.yspace = 20
        layout.init_all(optimize=True)
        for iteration in range(8):
            for layer, crossings in layout.ordering_step():
                pass
        for layer in layout.layers:
            siblings = {}
            for index, vertex in enumerate(layer):
                if layout.grx[vertex].dummy:
                    continue
                neighbors = (tuple(sorted(order[parent.data] for parent in vertex.N(-1))),
                             tuple(sorted(order[child.data] for child in vertex.N(+1))))
                siblings.setdefault(neighbors, []).append((index, vertex))
            for group in siblings.values():
                ordered = sorted((vertex for index, vertex in group), key=lambda vertex: (
                    sorted(incoming_ports[vertex.data]), sorted(outgoing_ports[vertex.data]),
                    order[vertex.data]))
                for (index, previous), vertex in zip(group, ordered):
                    layer[index] = vertex
            layer.setup(layout)
        layout.setxy()
        component_nodes = [vertex.data for vertex in component.V()]
        coords = {node: (vertices[node].view.xy[::-1] if horizontal
                         else vertices[node].view.xy) for node in component_nodes}
        left = min(coords[node][0] - sizes[node][0] / 2 for node in component_nodes)
        top = min(coords[node][1] - sizes[node][1] / 2 for node in component_nodes)
        for node, (coord_x, coord_y) in coords.items():
            positions[node] = (coord_x - left + (0 if horizontal else cross_cursor),
                               coord_y - top + (cross_cursor if horizontal else 0))
        if horizontal:
            cross_cursor += max(coords[node][1] + sizes[node][1] / 2
                                for node in component_nodes) - top + 60
        else:
            cross_cursor += max(coords[node][0] + sizes[node][0] / 2
                                for node in component_nodes) - left + 60
    return positions