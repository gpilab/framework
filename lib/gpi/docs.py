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

PREFIX='/opt/anaconda1anaconda2anaconda3'

import os
import sys
import inspect

GPI_PKG=PREFIX
GPI_FRAMEWORK=GPI_PKG+'lib/'
sys.path.insert(0, GPI_FRAMEWORK) # gpi
sys.path.insert(0, GPI_PKG) # plugin

# for API related docs
from gpi import VERSION
from gpi import RELEASE_DATE
import gpi.nodeAPI
import gpi.widgets
import types
from types import *

# for node docs
from gpi.config import Config
from gpi.library import NodeCatalogItem
from gpi.catalog import Catalog
from gpi.defines import isGPIModFile


# Node docs
class NodeDocs(object):
    '''(Deprecated) For grabbing the Node documentation for of each node found
    in all connected libraries.  This is used for listing all the nodes
    available. '''

    def __init__(self):
        #self._docText = '\n\n'+34*'-'+' NODE DOCS '+35*'-'+'\n\n'
        self._docText = ''
        self._known_GPI_nodes = Catalog()

        for path in Config.GPI_LIBRARY_PATH:
            self.scanGPIModules(path, recursion_depth=2)

        self.extractDocs()

    def scanGPIModules(self, ipath, recursion_depth=1):
        ocnt = ipath.count('/')
        new_sys_paths = []
        for path, dn, fn in os.walk(ipath):
            # TODO: instead of checking for hidden svn dirs, just choose any hidden dir
            if (path.count('/') - ocnt <= recursion_depth) and not path.count('/.svn'):
                for fil in os.listdir(path):

                    fullpath = path+'/'+fil

                    if isGPIModFile(fullpath):

                        item = NodeCatalogItem(fullpath)
                        item.load()  # load check
                        if item.valid():
                            self._known_GPI_nodes.append(item)
                        else:
                            print(("Failed to load: "+str(item)))


    def __str__(self):
        #return str(self._known_GPI_nodes)
        return self._docText
         
    def extractDocs(self):
        # look for ExternalNode
        cur_lib = ''
        cur_sub = ''
        for item in sorted(list(self._known_GPI_nodes.values()), key=lambda x: x.key().lower()):
            if hasattr(item.mod, 'ExternalNode'):
                cur_doc = str(inspect.getdoc(getattr(item.mod, 'ExternalNode')))

                numSpaces = 4
                cur_doc = "\n".join((numSpaces * " ") + i for i in cur_doc.splitlines())

                #self._docText += '\n'+80*'*'+'\n' 
                #self._docText += '\n\\subsection{'+str(item.key()).replace('_', '\_') +'}' + '\n\n'


                if item.third != cur_lib:
                    self._docText += '\n# '+str(item.third)+'\n'
                    cur_lib = item.third

                if item.second != cur_sub:
                    self._docText += '\n## '+str(item.second)+'\n'
                    cur_sub = item.second


                self._docText += '\n### '+str(item.name).replace('_', '\_') +'\n\n'
                #self._docText += '\n\\begin{lstlisting}\n'
                self._docText += str(cur_doc)
                self._docText += '\n\n'
                #self._docText += '\n\\end{lstlisting}\n'
                #self._docText += '\n'+80*'*'+'\n' 

            else:
                print((str(item) + ' Doesnt have ExternalNode definition, skipping...'))




# API docs
class GPIdocs(object):
    '''(Deprecated) For gathering all the relevant API documentation used in
    Node development. '''

    def __init__(self):
        self._docText = None
        self.parmList = []

        self.generateHelpText()

    def __str__(self):
        #return str(self._known_GPI_nodes)
        return self._docText

    def generateHelpText(self):
        """Gather the __doc__ string of the ExternalNode derived class,
        all the set_ methods for each attached widget, and any attached
        GPI-types from each of the ports.
        """
        # WIDGETS DOC
        # parm_doc = ""  # contains parameter info
        wdg_doc = "\n\n# WIDGETS\n"  # generic widget ref info
        wdg_doc += '''
        \nThis is a list of widgets and their associated attributes to aid in
        parameterizing and declaring widget.
        '''
        for name in dir(gpi.widgets):
            obj = getattr(gpi.widgets, name)
            if hasattr(obj, 'GPIWdgType'):
                self.parmList.append([name, obj])

        # get the generic group to filter out base members
        generic_wdg = None
        for parm in self.parmList:
            if parm[0] == 'GenericWidgetGroup':
                generic_wdg = parm
                #print parm[1].__dict__

                wdg_doc += "\n###  " + parm[0] + "\n"
                numSpaces = 8
                set_doc = "\n".join((" ") + i for i in str(
                    parm[1].__doc__).splitlines())
                wdg_doc += set_doc + "\n"
                wdg_doc += "attribute | type | description\n"
                wdg_doc += "--- | --- | ---\n"
                # set methods
                for member in dir(parm[1]):
                    if member.startswith('set_'):
                        #wdg_doc += (8 * " ") + member + inspect.formatargspec(
                        #    *inspect.getargspec(getattr(parm[1], member)))
                        wdg_doc += (" ") + "" + member.split('set_')[1] + " | "

                        set_doc = str(inspect.getdoc(getattr(parm[1], member)))
                        numSpaces = 1
                        set_doc = " ".join((
                            numSpaces * " ") + i for i in set_doc.splitlines())
                        wdg_doc += "" + set_doc + "\n"

        # now do other members
        for parm in self.parmList:
            if parm[0] == 'GenericWidgetGroup':
                continue

            wdg_doc += "\n###  " + parm[0] + "\n"
            numSpaces = 8
            set_doc = "\n".join((" ") + i for i in str(
                parm[1].__doc__).splitlines())
            wdg_doc += set_doc + "\n"
            wdg_doc += "attribute | type | description\n"
            wdg_doc += "--- | --- | ---\n"
            # set methods
            for member in dir(parm[1]):
                if member.startswith('set_'):
                    if member not in generic_wdg[1].__dict__ or member == 'set_val':
                        #wdg_doc += (8 * " ") + member + inspect.formatargspec(
                        #    *inspect.getargspec(getattr(parm[1], member)))
                        wdg_doc += (" ") + "" + member.split('set_')[1] + " | "

                        set_doc = str(inspect.getdoc(getattr(parm[1], member)))
                        numSpaces = 1
                        set_doc = " ".join((
                            numSpaces * " ") + i for i in set_doc.splitlines())
                        wdg_doc += "" + set_doc + "\n"

        # PORTS DOC
        port_doc = "\n\n# PORT Types\n"  # get the port type info
        port_doc += '''
        \nThe following types are used to define a node port for limiting the
        connection between nodes to the predefined port-types.  These labels are
        used when implementing `addInPort()` and `addOutPort()` port declaration
        functions.

        \n### PASS
        \nHas the affinity for any port type and allows any port connection.
        '''

        gpitype_libs = []
        for name in dir(plugin):
            if name.endswith('_GPITYPE'):
                gpitype_libs.append(name)

        gpitypes = []
        for name in gpitype_libs:
            lib = getattr(plugin, name)
            for oname in dir(lib):
                obj = getattr(lib, oname)
                if hasattr(obj, 'GPIType') and (oname is not 'GPIDefaultType'):
                    gpitypes.append([oname, obj])

        #for port in self.node.getPorts():
        for port in gpitypes:
            #typ = port.GPIType()
            #port_doc += "\n  \'" + port.portTitle + "\': " + \
            #    str(typ.__class__) + "|" + str(type(port)) + "\n"

            port_doc += "\n###   " + port[0] + "\n"

            # description
            numSpaces = 8
            set_doc = "\n".join((" ") + i for i in str(
                port[1].__doc__).splitlines())
            port_doc += set_doc + "\n"

            set_cnt = 0
            for member in dir(port[1]):
                if member.startswith('set_'):
                    set_cnt += 1

            if set_cnt:
                port_doc += "attribute | type | description\n"
                port_doc += "--- | --- | ---\n"

            # set methods
            for member in dir(port[1]):
                if member.startswith('set_'):
                    #port_doc += (8 * " ") + member + inspect.formatargspec(
                    #    *inspect.getargspec(getattr(port[1], member)))
                    port_doc += (" ") + "" + member.split('set_')[1] + " | "

                    set_doc = str(inspect.getdoc(getattr(port[1], member)))
                    numSpaces = 16
                    set_doc = " ".join((" ") + i for i in set_doc.splitlines())
                    port_doc += "" + set_doc + "\n"

        port_doc += "\n"

        # GETTERS/SETTERS
        getset_doc = "\n\n# GETTERS & SETTERS\n\n"
        getset_doc += '''
        \nGetters & Setters are functions that make up the node API.  They provide
        access to the UI elements (i.e. in-ports, out-ports, widgets).
        '''
        getset_doc += "\n## Node Initialization\n\n"
        getset_doc += '''
        \nThese methods are used to declare in-ports, out-ports and widgets within
        the `initUI()` node method.
        '''
        getset_doc += self.formatFuncDoc(gpi.nodeAPI.NodeAPI.addWidget)
        getset_doc += self.formatFuncDoc(gpi.nodeAPI.NodeAPI.addInPort)
        getset_doc += self.formatFuncDoc(gpi.nodeAPI.NodeAPI.addOutPort)
        getset_doc += "\n## Node Compute\n\n"
        getset_doc += '''
        \nThese methods are used to reference data from in-ports, out-ports and widgets
        within the `compute()` routine.
        '''
        getset_doc += self.formatFuncDoc(gpi.nodeAPI.NodeAPI.getVal)
        getset_doc += self.formatFuncDoc(gpi.nodeAPI.NodeAPI.getAttr)
        getset_doc += self.formatFuncDoc(gpi.nodeAPI.NodeAPI.setAttr)
        getset_doc += self.formatFuncDoc(gpi.nodeAPI.NodeAPI.getData)
        getset_doc += self.formatFuncDoc(gpi.nodeAPI.NodeAPI.setData)

        #self._docText = node_doc  # + wdg_doc + port_doc + getset_doc
        self._docText = wdg_doc + port_doc + getset_doc

        #self.wdgabout.setPlainText(self._docText)


    def formatFuncDoc(self, func):
        """Generate auto-doc for passed func obj."""
        numSpaces = 24
        fdoc = inspect.getdoc(func)
        set_doc = "\n".join((
            numSpaces * " ") + i for i in str(fdoc).splitlines())
        rdoc = "\n### "+func.__name__+ "\n" + (16 * " ") + func.__name__ + \
            inspect.formatargspec(*inspect.getargspec(func)) \
            + "\n" + set_doc + "\n\n"
        return rdoc





if __name__ == '__main__':

    api_docs = GPIdocs()
    #print api_docs

    node_docs = NodeDocs()
    #print node_docs

    boiler = '<b>This file was auto-generated via the docs.py script (GPI '+VERSION+', '+RELEASE_DATE+').'+'  Do not edit this file directly.</b>\n\n'

    # NodeAPI
    with open('NodeAPI.md','w') as f:
        print("Writing to NodeAPI.md...")

        preamble = '''# Node API\n'''

        f.write(boiler)
        f.write(preamble)
        f.write(str(api_docs))


    # CoreNodes
    with open('CoreNodes.md','w') as f:
        print("Writing to CoreNodes.md...")

        preamble = '''This is the core node library.
The following node usage information was generated from comments written into
the node-code by the authors.

'''
        f.write(boiler)
        f.write(preamble)
        f.write(str(node_docs))
