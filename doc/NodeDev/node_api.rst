########
Node API
########
.. automodule:: gpi.nodeAPI
.. autoclass:: NodeAPI

Core Functions
==============
.. automethod:: NodeAPI.initUI
.. automethod:: NodeAPI.validate
.. automethod:: NodeAPI.compute

Widget Functions
================
.. _adding-widgets:

Adding Widgets
--------------
.. automethod:: NodeAPI.addWidget

.. _accessing-widgets:

Accessing Widget Data
---------------------
.. automethod:: NodeAPI.getVal
.. automethod:: NodeAPI.setAttr
.. automethod:: NodeAPI.getAttr

Port Functions
==============
.. _adding-ports:

Adding Ports
------------
.. automethod:: NodeAPI.addInPort
.. automethod:: NodeAPI.addOutPort

.. _accessing-ports:

Accessing Port Data
-------------------
.. automethod:: NodeAPI.setData
.. automethod:: NodeAPI.getData

Event Functions
===============
.. automethod:: NodeAPI.getEvents
.. automethod:: NodeAPI.portEvents
.. automethod:: NodeAPI.widgetEvents

Additional Functions
====================
.. automethod:: NodeAPI.setDetailLabel
.. automethod:: NodeAPI.getDetailLabel

.. automethod:: NodeAPI.starttime
.. automethod:: NodeAPI.endtime

.. currentmodule:: gpi.node_profiler
.. autofunction:: profiler

Logging (through ``NodeAPI.log``)
---------------------------------
.. currentmodule:: gpi.logger
.. automethod:: PrintLogger.debug
.. automethod:: PrintLogger.info
.. automethod:: PrintLogger.node
.. automethod:: PrintLogger.warn
.. automethod:: PrintLogger.error
.. automethod:: PrintLogger.critical
