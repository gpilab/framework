#!/usr/bin/env python

#    Copyright (C) 2014  Dignity Health
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#    NO CLINICAL USE.  THE SOFTWARE IS NOT INTENDED FOR COMMERCIAL PURPOSES
#    AND SHOULD BE USED ONLY FOR NON-COMMERCIAL RESEARCH PURPOSES.  THE
#    SOFTWARE MAY NOT IN ANY EVENT BE USED FOR ANY CLINICAL OR DIAGNOSTIC
#    PURPOSES.  YOU ACKNOWLEDGE AND AGREE THAT THE SOFTWARE IS NOT INTENDED FOR
#    USE IN ANY HIGH RISK OR STRICT LIABILITY ACTIVITY, INCLUDING BUT NOT
#    LIMITED TO LIFE SUPPORT OR EMERGENCY MEDICAL OPERATIONS OR USES.  LICENSOR
#    MAKES NO WARRANTY AND HAS NO LIABILITY ARISING FROM ANY USE OF THE
#    SOFTWARE IN ANY HIGH RISK OR STRICT LIABILITY ACTIVITIES.
#
#    The code in this file was modifed/derived from the topsort.py with the
#    following license:
#
#       Permission is hereby granted to copy, modify and use the above source
#       code for any purpose as long as the following comment line is included
#       with it:
#
#           Original topological sort code written by Ofer Faigon
#           (www.bitformation.com) and used with permission

def topological_sort(items, partial_order):
    """Perform topological sort.
       items is a list of items to be sorted.
       partial_order is a list of pairs. If pair (a,b) is in it, it means
       that item a should appear before item b.
       Returns a list of the items in one of the possible orders, or None
       if partial_order contains a loop.
    """

    def add_node(graph, node):
        """Add a node to the graph if not already exists."""
        if node not in graph:
            graph[node] = [0] # 0 = number of arcs coming into this node.

    def add_arc(graph, fromnode, tonode):
        """Add an arc to a graph. Can create multiple arcs.
           The end nodes must already exist."""
        graph[fromnode].append(tonode)
        # Update the count of incoming arcs in tonode.
        graph[tonode][0] = graph[tonode][0] + 1

    # step 1 - create a directed graph with an arc a->b for each input
    # pair (a,b).
    # The graph is represented by a dictionary. The dictionary contains
    # a pair item:list for each node in the graph. /item/ is the value
    # of the node. /list/'s 1st item is the count of incoming arcs, and
    # the rest are the destinations of the outgoing arcs. For example:
    #           {'a':[0,'b','c'], 'b':[1], 'c':[1]}
    # represents the graph:   c <-- a --> b
    # The graph may contain loops and multiple arcs.
    # Note that our representation does not contain reference loops to
    # cause GC problems even when the represented graph contains loops,
    # because we keep the node names rather than references to the nodes.
    graph = {}
    for v in items:
        add_node(graph, v)
    for a,b in partial_order:
        add_arc(graph, a, b)

    # Step 2 - find all roots (nodes with zero incoming arcs).
    roots = [node for (node,nodeinfo) in list(graph.items()) if nodeinfo[0] == 0]

    # step 3 - repeatedly emit a root and remove it from the graph. Removing
    # a node may convert some of the node's direct children into roots.
    # Whenever that happens, we append the new roots to the list of
    # current roots.
    sorted = []
    while len(roots) != 0:
        # If len(roots) is always 1 when we get here, it means that
        # the input describes a complete ordering and there is only
        # one possible output.
        # When len(roots) > 1, we can choose any root to send to the
        # output; this freedom represents the multiple complete orderings
        # that satisfy the input restrictions. We arbitrarily take one of
        # the roots using pop(). Note that for the algorithm to be efficient,
        # this operation must be done in O(1) time.
        root = roots.pop()
        sorted.append(root)
        for child in graph[root][1:]:
            graph[child][0] = graph[child][0] - 1
            if graph[child][0] == 0:
                roots.append(child)
        del graph[root]
    if len(list(graph.items())) != 0:
        # There is a loop in the input.
        return None
    return sorted

def topsort(connection_list):
    """NRZ:
       The connection list is a list of pairs indicating flow direction through node ordering.
        -we only care about nodes with connections
            -so only itemize those nodes
    """
    # remove redundant connections
    c = set(connection_list)
    
    # list connected nodes
    l = set([ i for i,j in c ] + [ j for i,j in c ])

    return topological_sort(l,c)


if __name__ == '__main__':

    print("test topsort")
    print((topological_sort([1,2,3], [(1,2),(1,3),(3,2)]))) # --> [1,3,2]
    print((topological_sort([1,2], [(2,1),(2,1)]))) # --> [2,1]
    print((topological_sort([1,2], [(1,2),(2,1)]))) # --> None
    print((topological_sort([0,1,2], [(0,1),(1,2),(2,1)]))) # --> None


    # hashable type
    x = type
    y = int
    z = float
    print((topological_sort([x,y,z], [(x,y),(x,z),(z,y)]))) # --> [1,3,2]

    print((topsort( [(x,y),(x,z),(z,y)] )))

    print("cyclic and acylic graphs")
    print((topsort( [(1,2),(1,3),(3,2),(5,6),(5,7),(7,6),(7,5)] )))

    print("multiple graphs")
    print((topsort( [(1,2),(1,3),(3,2),(5,6),(5,7),(7,6)] )))




