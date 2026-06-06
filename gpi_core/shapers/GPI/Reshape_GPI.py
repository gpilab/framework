# Author: Ryan Robison
# Date: 2020 March 19

import os
import time
import gpi
from gpi import QtWidgets, QtGui, QtCore

class RESHAPE_GROUP(gpi.GenericWidgetGroup):
    """Widget for entering a new shape via spin boxes"""
    valueChanged = gpi.Signal()

    def __init__(self, title, parent=None):
        super().__init__(title, parent)

        # buttons for adding/removing a box
        self.sub = gpi.BasicPushButton()
        self.sub.set_toggle(False)
        self.sub.set_button_title(u'\u2212')
        self.sub.valueChanged.connect(self.removeBox)
        self.add = gpi.BasicPushButton()
        self.add.set_toggle(False)
        self.add.set_button_title(u'\uFF0B')
        self.add.valueChanged.connect(self.addBox)

        self.hbox = QtWidgets.QHBoxLayout()
        self.hbox.setSpacing(0)
        self.hbox.addWidget(self.sub)
        self.hbox.addWidget(self.add)
        
        # at least one spin box
        self.boxes = []
        self.boxes.append(gpi.BasicSpinBox())
        self.vbox = QtWidgets.QVBoxLayout()
        self.vbox.setSpacing(0)

        self.vbox.addLayout(self.hbox)
        for box in self.boxes:
            self.vbox.addWidget(box)
            box.valueChanged.connect(self.valueChanged)
        self.setLayout(self.vbox)

    # setters
    def set_vals(self, inlist):
        while len(inlist) < len(self.boxes):
            oldbox = self.boxes.pop(0)
            self.vbox.removeWidget(oldbox)
            oldbox.deleteLater()
            oldbox.setParent(None)
            oldbox = None

        while len(inlist) > len(self.boxes):
            newbox = gpi.BasicSpinBox()
            self.boxes.insert(0, newbox) 
            newbox.valueChanged.connect(self.valueChanged)
            newbox.set_min(1)
            newbox.set_val(1)
            newbox.set_max(gpi.GPI_INT_MAX)
            self.vbox.addWidget(newbox)

        if len(inlist) != len(self.boxes):
            self.log.critical("RESHAPE_GROUP: number of boxes not correct!")

        ind = 0 
        for box in self.boxes:
            inval = inlist[ind]
            box.set_val(inval)
            ind = ind + 1

    # support
    def removeBox(self):
        if len(self.boxes) > 1:
            oldbox = self.boxes.pop(0)
            self.vbox.removeWidget(oldbox)
            oldbox.deleteLater()
            oldbox.setParent(None)
            oldbox = None
        self.valueChanged.emit()

    def addBox(self):
        newbox = gpi.BasicSpinBox()
        self.boxes.insert(0, newbox) 
        newbox.valueChanged.connect(self.valueChanged)
        newbox.set_min(1)
        newbox.set_val(1)
        newbox.set_max(gpi.GPI_INT_MAX)
        self.vbox.addWidget(newbox)
        self.valueChanged.emit()

    def get_vals(self):
        vals = []
        for box in self.boxes:
            vals.append(box.get_val())
        return vals


class COMBINE_SPLIT_GROUP(gpi.GenericWidgetGroup):
    """Dimension specific widget to specify data reshaping"""
    valueChanged = gpi.Signal()

    def __init__(self, title, parent=None):
        super().__init__(title, parent)

        self._val = {}
        self._val['action'] = 0
        self._val['dim_position'] = 1 # 0 - first, 1 - middle, 2 - last
        self._val['combine_dir'] = 0
        self._val['split_prod'] = 1
        self._val['split_val1'] = 1
        self._val['split_val2'] = 1

        # create exclusive push buttons to choose action
        self.action = gpi.ExclusivePushButtons('action')
        self.buttons = ['pass', 'combine', 'split']
        self.action.set_buttons(self.buttons)

        # create exclusive push buttons to choose action
        self.combdir = gpi.ExclusivePushButtons('direction')
        self.buttons = [u'\u2B06', u'\u2B07']
        self.combdir.set_buttons(self.buttons)
        self.combdir.set_visible(False)

        # create integer boxes for splitting a value
        self.sb1 = gpi.BasicSpinBox() 
        self.sb1.set_min(1)
        self.sb1.set_val(1)
        self.sb1.set_max(gpi.GPI_INT_MAX)
        self.sb2 = gpi.BasicSpinBox() 
        self.sb2.set_min(1)
        self.sb2.set_val(1)
        self.sb2.set_max(gpi.GPI_INT_MAX)
        self.set_sb_visible(False)

        self.action.valueChanged.connect(self.actionChange)
        self.combdir.valueChanged.connect(self.combdirChange)
        self.sb1.valueChanged.connect(self.splitChangeLeft)
        self.sb2.valueChanged.connect(self.splitChangeRight)

        hbox = QtWidgets.QHBoxLayout()
        hbox.addWidget(self.action)
        hbox.addWidget(self.combdir)
        hbox.addWidget(self.sb1)
        hbox.addWidget(self.sb2)
        hbox.setSpacing(0)
        self.setLayout(hbox)

    # setters 
    def set_action(self, val):
        self._val['action'] = val
        self.action.set_val(val)
        self.actionChange()

    def set_dimpos(self, val):
        """A marker of the dimension position. 0-first, 1-middle, 2-last"""
        self._val['dim_position'] = val
        pos = self._val['dim_position']
        if pos == 0:
            self.buttons = [u'\u2B07']
        elif pos == 1:
            self.buttons = [u'\u2B06', u'\u2B07']
        elif pos == 2:
            self.buttons = [u'\u2B06']
        else:
            self.log.warn("Not a valid dimension position in widget of type "\
                "COMBINE_SPLIT_GROUP. Must be between 0 and 2.")
        self.combdir.set_buttons(self.buttons)

    def set_split_prod(self, val):
        """set a new product of the split dimension."""
        self._val['split_prod'] = val
        self.splitChangeRight()

    def set_sb_visible(self, val):
        self.sb1.setVisible(val)
        self.sb2.setVisible(val)

    # support
    def actionChange(self):
        self._val['action'] = self.action.get_val()
        if self._val['action'] == 0:
            self.combdir.set_visible(False)
            self.set_sb_visible(False)
        elif self._val['action'] == 1:
            self.combdir.set_visible(True)
            self.set_sb_visible(False)
        else:
            self.combdir.set_visible(False)
            self.set_sb_visible(True)
        self.valueChanged.emit()

    def combdirChange(self):
        self._val['combine_dir'] = self.combdir.get_val()
        self.valueChanged.emit()
            
    def splitChangeLeft(self):
        prod = self._val['split_prod']
        val1 = self.sb1.get_val()
        old_val = self._val['split_val1']
        new_val = val1
        while (prod % val1 != 0 and val1 > 1 and val1 < prod):
            if new_val >= old_val:
                val1 = val1 + 1
            else:
                val1 = val1 - 1
        val2 = prod // val1
        self._val['split_val1'] = val1
        self._val['split_val2'] = val2
        self.setSplitValsQuietly(self._val)
        self.valueChanged.emit()

    def splitChangeRight(self):
        prod = self._val['split_prod']
        val2 = self.sb2.get_val()
        old_val = self._val['split_val2']
        new_val = val2
        while (prod % val2 != 0 and val2 > 1 and val2 < prod):
            if new_val > old_val:
                val2 = val2 + 1
            else:
                val2 = val2 - 1
        val1 = prod // val2
        self._val['split_val1'] = val1
        self._val['split_val2'] = val2
        self.setSplitValsQuietly(self._val)
        self.valueChanged.emit()
        
    def setSplitValsQuietly(self, val):
        self.sb1.blockSignals(True)
        self.sb2.blockSignals(True)
        self.sb1.set_val(self._val['split_val1'])
        self.sb2.set_val(self._val['split_val2'])
        self.sb1.blockSignals(False)
        self.sb2.blockSignals(False)

    # getters
    def get_action(self):
        return self._val['action']
    
    def get_combine_dir(self):
        return self._val['combine_dir']

    def get_split_dims(self):
        """return split dims as a list"""
        dims = []
        dims.append(self._val['split_val1'])
        dims.append(self._val['split_val2'])
        return dims


class ExternalNode(gpi.NodeAPI):
    """This node can be used to reshape NumPy arrays using user entered 
    values, or by combining and splitting dimensions individually.
    
    The Reshape mode will create a set of editable boxes for users to manually
    enter new dimensions. It also has +/- buttons to add and remove dimensions.
    
    The Combine/Split mode allows users to specify on a dimension by dimension
    basis whether they want to combine with another dimension or split the 
    current dimension into two dimensions.

    INPUT - NumPy array to be reshaped
    OUTPUT - Reshaped NumPy array

    WIDGETS:
    Info: -  Provides info on input and output shape and size.
    Mode - Specify whether to reshape using user entered values or using 
            combine/split operations. 
    Reset - Reset the dimensions and widgets to reflect the input data.
    Apply Shape - Button to tell node to apply the new shape to the data.
    """

    def execType(self):
        # default executable type
        # return gpi.GPI_THREAD
        return gpi.GPI_PROCESS # this is the safest
        # return gpi.GPI_APPLOOP

    def initUI(self):

        # Widgets
        self.addWidget('TextBox', 'Info:')
        self.addWidget('ExclusivePushButtons', 'Mode', buttons=['Reshape', 'Combine/Split'], val = 0)
        self.addWidget('PushButton', 'Reset', toggle=False)
        self.addWidget('RESHAPE_GROUP', 'New Shape')
        self.dim_base_name = 'Dimension['
        self.ndim = 10
        for i in range(self.ndim):
            self.addWidget('COMBINE_SPLIT_GROUP', self.dim_base_name+str(-i-1)+']')
        self.addWidget('PushButton', 'Apply Shape', toggle=True)

        # IO Ports
        self.addInPort('in', 'NPYarray', obligation=gpi.REQUIRED)
        self.addOutPort('out', 'NPYarray')

    def validate(self):
        data = self.getData('in')
        mode = self.getVal('Mode')

        # visibility
        if (self.portEvents() or 'Reset' in self.widgetEvents() 
                or 'Mode' in self.widgetEvents()):
            self.ndim = 10 
            if mode == 0:
                try:
                    cur_dims = self.getAttr('New Shape', 'vals')
                    if cur_dims == [0]:
                        cur_dims = list(data.shape)
                except:
                    cur_dims = list(data.shape)
                if 'Reset' in self.widgetEvents():
                    cur_dims = list(data.shape)
                self.setAttr('New Shape', visible = True, vals = cur_dims)
            else:
                self.setAttr('New Shape', visible = False)
            for i in range(self.ndim):
                dimname = self.dim_base_name+str(-i-1)+']'
                if mode == 0 or i >= data.ndim:
                    self.setAttr(dimname, visible = False)
                else:
                    if 'Reset' in self.widgetEvents():
                        self.setAttr(dimname, action = 0)
                    size = data.shape[-i-1]
                    if i == 0:
                        dimpos = 0
                    elif i == data.ndim - 1:
                        dimpos = 2
                    else:
                        dimpos = 1
                    self.setAttr(dimname, visible = True, dimpos = dimpos, 
                        split_prod = size)

        return(0)

    def compute(self):
        import numpy as np
        data = self.getData('in')
        mode = self.getVal('Mode')
        compute = self.getVal('Apply Shape')
        basic_info = "Input Shape: "+str(data.shape)+"\n" \
                     "Input Size: "+str(data.size)+"\n"
        warn_message = ""
        out_dims = []

        if mode == 0:
            out_dims = self.getAttr('New Shape', 'vals')

        if mode == 1:
            prev_dim = 1
            cur_ind = 0
            for i in range(data.ndim):
                size = data.shape[-i-1]
                dimname = self.dim_base_name+str(-i-1)+']'
                action = self.getAttr(dimname, 'action')
                if action == 0:  # pass
                    out_dims.append(size * prev_dim)
                    prev_dim = 1
                    cur_ind = cur_ind + 1
                elif action == 1:  # combine
                    combdir = self.getAttr(dimname, 'combine_dir')
                    if combdir == 0 and i != 0:
                        if prev_dim == 1:
                            size = size * out_dims.pop(cur_ind-1)
                            out_dims.insert(cur_ind-1, size)
                            prev_dim = 1
                        else:
                            size = size * prev_dim
                            out_dims.append(size)
                            prev_dim = 1
                            cur_ind = cur_ind + 1
                    else:
                        prev_dim = prev_dim * size
                else:  # split
                    split_dims = self.getAttr(dimname, 'split_dims')
                    out_dims.append(split_dims[0] * prev_dim)
                    out_dims.append(split_dims[1])
                    cur_ind = cur_ind + 2
                    prev_dim = 1
            out_dims.reverse()

        if data.size != np.prod(out_dims):
            warn_message = "The total data size must match between the input " \
                "and output shapes.\n"
        info = basic_info+"Output Shape: "+str(out_dims)+"\n" \
                "Output Size: "+str(np.prod(out_dims))+"\n"+warn_message

        self.setAttr('Info:', val=info)

        if compute:
            if data.size == np.prod(out_dims):
                data.shape = out_dims
                self.setData('out', data)
            else:
                self.setAttr('Apply Shape', val = 0)
                self.log.warn("reshape size does not match input size. "\
                    "Defaulting to input size.")


        return(0)
