############
Introduction
############

GPI is a development environment for scientific algorithms that provides a
visual workspace for assembling algorithms. Algorithm elements (i.e. nodes) can
be linked together to form a flow diagram. Each node is executed according to
the hierarchy of the diagram.

.. image:: http://i1.wp.com/gpilab.com/wp-contents/gif/SpiralRecon_SliceLoop.gif
    :align: center
    :width: 50%

Integrated Development Environment
==================================

GPI can be thought of as an integrated development environment for Python. GPI
nodes can leverage the scientific computing capabilities of numeric libraries
such as Numpy and Scipy. The goal of GPI is to minimize the barrier to
organizing and developing complex scientific algorithms (i.e. in the form of
GPI nodes). To this end, GPI provides a GUI for a basic set of tools to
visualize data, manipulate data and I/O for common scientific data formats.

.. image:: http://i2.wp.com/gpilab.com/wp-content/uploads/2015/11/CanvasAsAScript.png
    :align: center
    :width: 50%

Collaboration Platform
======================

At the node level, the common API and UI elements allow other developers to
easily integrate and use your code. Node libraries can be easily developed
among multiple users via a revision system without having to manage the GPI
framework. This allows algorithm developers to pick and choose existing nodes
(either stock or from their collaborators) and focus on the task of prototyping
their new algorithm.

.. image:: http://i0.wp.com/gpilab.com/wp-content/uploads/2015/11/Developers_SpiralToF.png
    :align: center
    :width: 50%

Teaching Tool
=============

The visual and modular nature of GPI allows complex algorithms to be easily
examined and explored. Users can visualize the data flow at each point in an
algorithm and tap any point to start their own algorithm. This feature allows
concise communication of your work with your collaborators as it provides an
intuitive mechanism for others to start interacting with your research.

.. image:: http://i1.wp.com/gpilab.com/wp-content/uploads/2015/11/CompressedSensing.png
    :align: center
    :width: 50%

Reconstruction Framework
========================

The GPI framework is being developed for Magnetic Resonance Imaging (MRI)
research. This means the thrust of the core toolbox is primarily geared towards
k-space image reconstructions. However, the GPI framework is simply an event
driven pipeline that can be used for any data processing. We also use it for
spin physics simulations and simulating k-space data.

.. image:: http://i1.wp.com/gpilab.com/wp-contents/gif/SpinSim.gif
    :align: center
    :width: 50%
