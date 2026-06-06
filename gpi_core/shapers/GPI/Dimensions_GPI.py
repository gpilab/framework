# Copyright (c) 2014, Dignity Health
# 
#     The GPI core node library is licensed under
# either the BSD 3-clause or the LGPL v. 3.
# 
#     Under either license, the following additional term applies:
# 
#         NO CLINICAL USE.  THE SOFTWARE IS NOT INTENDED FOR COMMERCIAL
# PURPOSES AND SHOULD BE USED ONLY FOR NON-COMMERCIAL RESEARCH PURPOSES.  THE
# SOFTWARE MAY NOT IN ANY EVENT BE USED FOR ANY CLINICAL OR DIAGNOSTIC
# PURPOSES.  YOU ACKNOWLEDGE AND AGREE THAT THE SOFTWARE IS NOT INTENDED FOR
# USE IN ANY HIGH RISK OR STRICT LIABILITY ACTIVITY, INCLUDING BUT NOT LIMITED
# TO LIFE SUPPORT OR EMERGENCY MEDICAL OPERATIONS OR USES.  LICENSOR MAKES NO
# WARRANTY AND HAS NOR LIABILITY ARISING FROM ANY USE OF THE SOFTWARE IN ANY
# HIGH RISK OR STRICT LIABILITY ACTIVITIES.
# 
#     If you elect to license the GPI core node library under the LGPL the
# following applies:
# 
#         This file is part of the GPI core node library.
# 
#         The GPI core node library is free software: you can redistribute it
# and/or modify it under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation, either version 3 of the License,
# or (at your option) any later version. GPI core node library is distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even
# the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU Lesser General Public License for more details.
# 
#         You should have received a copy of the GNU Lesser General Public
# License along with the GPI core node library. If not, see
# <http://www.gnu.org/licenses/>.


# Author: Ryan Robison
# Date: 2013jul02

import numpy as np
import gpi

# define widget bounding limits
DIM_INT_MAX = pow(2, 31) - 1  # max QWidgets can use
DIM_INT_MIN = -pow(2, 31)  # min QWidgets can use

class ExternalNode(gpi.NodeAPI):
    """Peform operations on an array that generally change its shape and order, but not so much the actual data
    INPUT - input array
    OUTPUT - output array

    WIDGETS:
    Info: - information on size, etc of input and output array - very useful to pay attention to this
    Operation:
      Reshape - give new dimensions to file (must be same total size), while data stay in same order in memory
      Combine - combine 2 dimensions, output array will have one less dimension
      Split - split a dimension into two dimensions, output array will have one extra dimension
      Extend - add an extra dimension; if length of that dimension > 1, the data will be copied along that dimension
      Transpose - transpose any dimensions
      Flip - mirror the data along any dimension (can flip in multiple dimensions)
      Shift - shift data along any dimension, filling in with zeros
      CircShift - circularly shift data along any dimension, wrapping the data from the outgoing edge back around
      Tile - Separate a dimension so that it is tiled in the other dimensions - may not work in all cases (useful for 3D data)
    """

    def initUI(self):

        # Widgets
        self.dim_base_name = 'Dimension['
        self.maxdim = 13 # set to 13 for now
        self.ndim = self.maxdim
        self.shape = []
        self.size = 0
        self.comp = 1
        self.reset = 0
        self.trans_ind = []
        self.rep_ind = []
        self.flip_string = 'out = data[:]'
        self.info_message = ""
        self.op_buttons = ['Reshape', '   Combine', '   Split', 'Extend',
                           'Transpose', 'Flip', 'Shift', 'CircShift', 'Tile']
        self.addWidget('TextBox', 'Info:')
        self.addWidget('ExclusiveRadioButtons', 'Operation',
                       buttons=self.op_buttons, val = 0)
        self.addWidget('SpinBox', '# Dimensions', val=self.ndim)
        self.addWidget('SpinBox', '# Columns', val=1)
        self.addWidget('SpinBox', '# Rows', val=1)
        for i in range(self.maxdim):
            self.addWidget('SpinBox', self.dim_base_name+str(-i-1)+']', val=0)
        dim_buttons = []
        for i in range(-self.maxdim, 0):
            dim_buttons.append(str(i))
        self.addWidget('NonExclusivePushButtons', 'Selection',
                       buttons=dim_buttons, val=[])
        tile_buttons = []
        for i in range(-3, 0):
            tile_buttons.append(str(i))
        self.addWidget('ExclusivePushButtons', 'Tile Dimension',
                       buttons=tile_buttons, val=0)
                       
        self.addWidget('PushButton', 'Compute', toggle=True, val=0)
        self.addWidget('PushButton', 'Reset', toggle=True, val=0)

        # IO Ports
        self.addInPort('in', 'NPYarray', obligation=gpi.REQUIRED)
        self.addOutPort('out', 'NPYarray')

    def validate(self):
        '''update the widgets based on the input arrays
        '''

        data = self.getData('in')
        op = self.getVal('Operation')
        basic_info = "Input Dimensions: "+str(data.shape)+"\n" \
                     "Input Size: "+str(data.size)+"\n"
        if data.ndim < 3:
            self.op_buttons = ['Reshape', '   Combine', '   Split', 'Extend',
                               'Transpose', 'Flip', 'Shift', 'CircShift']
            if op > 7:
                op = 0
            self.setAttr('Operation', buttons=self.op_buttons, val=op)
        else:
            self.op_buttons = ['Reshape', '   Combine', '   Split', 'Extend',
                               'Transpose', 'Flip', 'Shift', 'CircShift', 'Tile']
            self.setAttr('Operation', buttons=self.op_buttons, val=op)

        # generate list of any Dimension[?] widget events
        dim_events = [s for s in self.widgetEvents() if s.startswith(self.dim_base_name)]

        # set widget visibility and initial values
        if ('in' in self.portEvents() or 'Selection' in self.widgetEvents() or
            set(self.widgetEvents()).intersection(['Operation', 'Selection',
                'Reset', 'Tile Dimension', '# Rows', '# Columns'])):

            # initializations 
            self.flip_string = 'out = data[:]'
            self.info_message = ""

            # check for reset then turn it off
            self.reset = self.getVal('Reset')
            self.setAttr('Reset', val=0)

            # check to make sure the selected dimensions do not exceed the
            # data dimensionality
            if (self.op_buttons[op] in ['   Combine', '   Split',
                                        'Extend', 'Flip']):
                sel = self.getVal('Selection')
                if self.reset == 1:
                    sel = []
                if len(sel) > 0:
                    max_sel = max(sel)
                else:
                    max_sel = -1

            # get and setup data shape and dimensionality
            if op == 0 and self.reset == 0: # Reshape
                self.ndim = self.getVal('# Dimensions')
                self.shape = [1] * self.ndim
                for i in range(self.ndim):
                    self.shape[-i-1] = self.getVal(self.dim_base_name
                                                            +str(-i-1)+']')
                self.size = np.prod(self.shape)
                if self.size != data.size or self.size == 0:
                    self.ndim = data.ndim
                    self.shape = list(data.shape)

            elif op == 1: # Combine
                while max_sel >= len(data.shape)-1:
                    del sel[-1]
                    if len(sel) > 0:
                        max_sel = max(sel)
                    else:
                        break
                self.shape = list(data.shape)
                self.ndim = data.ndim
                for i in sel[::-1]:
                    for j in range(self.ndim - 1):
                        if j < i:
                            self.shape[j] = self.shape[j]
                        elif j == i:
                            self.shape[j] = (self.shape[j] * self.shape[j+1])
                        else:
                            self.shape[j] = self.shape[j+1]
                    del self.shape[-1]
                    self.ndim = len(self.shape)
                self.size = np.prod(self.shape)

            elif op == 2: # Split
                while max_sel >= len(data.shape):
                    del sel[-1]
                    if len(sel) > 0:
                        max_sel = max(sel)
                    else:
                        break
                # calculate indices of editable dimensions based on selection
                j = 0
                k = 0
                data_ind = list(range(len(data.shape) + len(sel)))
                self.shape = [1] * (len(data_ind))
                self.ndim = len(self.shape)
                vis_ind = [1] * (2 * len(sel))
                for i in sel:
                    data_ind.remove(i+k)
                    vis_ind[j] = i+k
                    vis_ind[j+1] = i+k+1
                    j = j+2
                    k = k+1
                # setup the data shape and dimensionality
                if self.portEvents():
                    for i in range(self.ndim):
                        self.shape[-i-1] = (self.getVal(
                                            self.dim_base_name+str(-i-1)+']'))
                    self.size = np.prod(self.shape)
                else:
                    self.reset = 1
                if self.size != data.size or self.reset == 1:
                    self.shape = [1] * self.ndim
                    k = 0
                    for i in range(self.ndim):
                        if i in data_ind:
                            self.shape[i] = data.shape[k]
                            k = k+1
                self.size = np.prod(self.shape)

            elif op == 3: # Extend
                while max_sel > len(data.shape):
                    del sel[-1]
                    if len(sel) > 0:
                        max_sel = max(sel)
                    else:
                        break
                # calculate indices of editable dimensions based on selection
                j = 0
                data_ind = list(range(len(data.shape) + len(sel)))
                self.shape = [1] * (len(data_ind))
                self.ndim = len(self.shape)
                vis_ind = [1] * (len(sel))
                for i in sel:
                    data_ind.remove(i+j)
                    vis_ind[j] = i+j
                    j = j+1
                self.rep_ind = vis_ind
                # setup the data shape and dimensionality
                if self.portEvents():
                    for i in range(self.ndim):
                        self.shape[-i-1] = (self.getVal(
                                            self.dim_base_name+str(-i-1)+']'))
                    self.size = np.prod(self.shape)
                j = 0
                for i in range(self.ndim):
                    if i in data_ind:
                        self.shape[i] = data.shape[j]
                        j = j+1
                self.size = np.prod(self.shape)

            elif self.op_buttons[op] == 'Tile': # Tile
                tile_dim = self.getVal('Tile Dimension')
                row_size = self.getVal('# Rows')
                column_size = self.getVal('# Columns')
                if '# Rows' in self.widgetEvents():
                    column_size = np.ceil(float(data.shape[tile_dim - 3]) // row_size)
                    self.setAttr('# Columns', val=column_size)
                if '# Columns' in self.widgetEvents():
                    row_size = np.ceil(float(data.shape[tile_dim - 3]) // column_size)
                    self.setAttr('# Rows', val=row_size)
                if (row_size * column_size < data.shape[tile_dim - 3] or 
                      self.reset == 1 or
                      'Tile Dimension' in self.widgetEvents()):
                    row_size = int(np.sqrt(data.shape[tile_dim - 3]))
                    column_size = np.ceil(float(data.shape[tile_dim - 3]) // row_size)
                    self.setAttr('# Rows', val=row_size)
                    self.setAttr('# Columns', val=column_size)

                self.ndim = len(data.shape) - 1
                self.shape = [1] * self.ndim
                if tile_dim == 0:
                    self.shape[-1] = data.shape[-1] * column_size
                    self.shape[-2] = data.shape[-2] * row_size
                elif tile_dim == 1:
                    self.shape[-1] = data.shape[-1] * column_size
                    self.shape[-2] = data.shape[-3] * row_size
                else:
                    self.shape[-1] = data.shape[-2] * column_size
                    self.shape[-2] = data.shape[-3] * row_size
                for i in range(3, data.ndim):
                    self.shape[-i] = data.shape[-i-1]

            elif self.op_buttons[op] == 'Transpose': # Transpose
                self.ndim = data.ndim
                self.shape = list(data.shape)
                self.trans_ind = list(range(-data.ndim, 0))
                if self.portEvents():
                    count_trans_ind = list(range(-data.ndim, 0))
                    for i in range(data.ndim):
                        trans_ind = self.getVal(self.dim_base_name
                                                         +str(-i-1)+']')
                        if trans_ind > data.ndim - 1 or trans_ind < -data.ndim:
                            trans_ind = -i-1
                        self.trans_ind[-i-1] = trans_ind
                        self.shape[-i-1] = data.shape[trans_ind]
                        if trans_ind < 0:
                            trans_ind = trans_ind + data.ndim
                        count_trans_ind[-i-1] = trans_ind
                    dup_count = max([count_trans_ind.count(i)
                                for i in count_trans_ind])
                    if dup_count > 1:
                        self.trans_ind = list(range(-data.ndim, 0))

            elif self.op_buttons[op] == 'Flip': # Flip
                self.shape = list(data.shape)
                self.ndim = data.ndim
                self.size = np.prod(data.shape)
                self.flip_string = 'out = data['
                while max_sel >= len(data.shape):
                    del sel[-1]
                    if len(sel) > 0:
                        max_sel = max(sel)
                    else:
                        break
                for i in range(data.ndim):
                    if i in sel:
                        self.flip_string = self.flip_string+'::-1, '
                    else:
                        self.flip_string = self.flip_string+':, '
                self.flip_string = self.flip_string[:-2]+']'

            else: # Shift or CircShift
                if 'Operation' in self.widgetEvents():
                    self.reset = 1
                self.shape = list(data.shape)
                self.ndim = data.ndim
                self.size = np.prod(data.shape)

            # change selection button labels based upon functionality
            dim_buttons = []
            if op == 1:
                for i in range(-data.ndim,-1):
                    dim_buttons.append(str(i)+" AND "+str(i+1))
            if self.op_buttons[op] in ['   Split', 'Flip']:
                for i in range(-data.ndim,0):
                    dim_buttons.append(str(i))
            if op == 3:
                for i in range(-data.ndim-1,0):
                    dim_buttons.append(str(i)+"->")

            # turn on selection button when used
            if (self.op_buttons[op] in ['   Combine', '   Split',
                                        'Extend', 'Flip']):
                self.setAttr('Selection', visible=True,
                                  buttons=dim_buttons, val=sel)
            else:
                self.setAttr('Selection', visible=False)

            # turn on tile widgets when used
            if self.op_buttons[op] == 'Tile':
                self.setAttr('# Rows', visible=True)
                self.setAttr('# Columns', visible=True)
                self.setAttr('Tile Dimension', visible=True)
            else:
                self.setAttr('# Rows', visible=False)
                self.setAttr('# Columns', visible=False)
                self.setAttr('Tile Dimension', visible=False)
                
            # dimensionality is only directly adjustable for reshape
            if op == 0:
                self.setAttr('# Dimensions', visible = True,
                                  val=self.ndim)
            else:
                self.setAttr('# Dimensions', visible = False,
                                  val=self.ndim)

            # set up Dimension widget values, visibility and range
            for i in range(self.maxdim):
                if i < self.ndim and op == 0: # Reshape
                    if self.reset == 1 or self.size == 0:
                        val = data.shape[-i-1]
                        if self.dim_base_name+str(-i-1)+']' not in dim_events:
                            self.setAttr(self.dim_base_name+str(-i-1)+']',
                                            visible=True, val=val,
                                            max=DIM_INT_MAX, min=1)
                        else:
                            self.setAttr(self.dim_base_name+str(-i-1)+']',
                                            visible=True,
                                            max=DIM_INT_MAX, min=1)
                    else:
                        val = self.getVal(self.dim_base_name+str(-i-1)+']')
                        self.shape[-i-1] = val
                        self.setAttr(self.dim_base_name+str(-i-1)+']',
                                          visible=True, val=val,
                                          max=DIM_INT_MAX, min=1)
                elif i < self.ndim and op == 1: # Combine
                    val = self.shape[-i-1]
                    self.setAttr(self.dim_base_name+str(-i-1)+']',
                                      visible=False, val=val,
                                          max=DIM_INT_MAX, min=1)
                elif i < self.ndim and op in [2, 3]: # Split and Extend
                    val = self.shape[-i-1]
                    if (self.ndim - i - 1) in vis_ind:
                        if op == 2 and val == 1:
                            max_val = self.shape[-i]
                        elif op == 2:
                            max_val = val
                        else:
                            self.shape[-i-1] = 1
                            max_val = DIM_INT_MAX
                        self.setAttr(self.dim_base_name+str(-i-1)+']',
                                          visible=True, val=val, min=1,
                                          max=max_val)
                    else:
                        max_val = DIM_INT_MAX
                        self.setAttr(self.dim_base_name+str(-i-1)+']',
                                          visible=False, val=val, min=1,
                                          max=max_val)
                elif (i < data.ndim and
                      self.op_buttons[op] in ['Tile', 'Flip']):
                    val = data.shape[-i-1]
                    self.setAttr(self.dim_base_name+str(-i-1)+']',
                                      visible=False, val=val, min=1, max=DIM_INT_MAX)
                elif i < data.ndim and self.op_buttons[op] == 'Transpose':
                    val = self.trans_ind[-i-1]
                    self.setAttr(self.dim_base_name+str(-i-1)+']',
                                      visible=True, max=data.ndim-1,
                                      min=-data.ndim, val=val)
                elif (i < data.ndim and
                      self.op_buttons[op] in ['Shift', 'CircShift']):
                    if (self.reset == 1):
                        val = 0
                        self.setAttr(self.dim_base_name+str(-i-1)+']',
                                          visible=True, val=val,
                                          max=DIM_INT_MAX, min=DIM_INT_MIN)
                    else:
                        self.setAttr(self.dim_base_name+str(-i-1)+']',
                                          visible=True, max=DIM_INT_MAX,
                                          min=DIM_INT_MIN)
                else:
                    self.setAttr(self.dim_base_name+str(-i-1)+']',
                                      visible=False, max=DIM_INT_MAX,
                                      min=DIM_INT_MIN)


        # adjust data and widget dimensionality when # dimensions is changed
        if ('# Dimensions' in self.widgetEvents() and op == 0):
            self.info_message = ""
            self.ndim = self.getVal('# Dimensions')
            if self.ndim >= len(self.shape):
                for i in range(len(self.shape), self.ndim):
                    self.setAttr(self.dim_base_name+str(-i-1)+']',
                                      visible=True, val=1)
                    self.shape.insert(0, 1)
            else:
                for i in range(len(self.shape), self.ndim, -1):
                    if self.shape[-i] == 1:
                        self.setAttr(self.dim_base_name+str(-i)+']',
                                          visible=False)
                        del self.shape[-i]
                    else:
                        self.ndim = len(self.shape)
                        self.setAttr('# Dimensions', val=self.ndim)
                        self.info_message = "Can't remove non-singleton "+ \
                                             "dimension\n"
                        break
            self.size = np.prod(self.shape)

        # adjust data output size based on user specified sizes
        if (dim_events):
            for event in dim_events:
                self.info_message = ""
                index = int(event[10:12])
                new_val = self.getVal(event)
                self.setAttr(event, val=new_val)
                if op == 0 and (self.ndim + index) >= 0:
                    self.shape[index] = new_val
                    self.size = np.prod(self.shape)
                    if self.size != data.size:
                        self.setAttr('Compute', val=0)
                        self.info_message = "The output and input sizes must "+ \
                                             "match\n"
                    elif self.comp == 1:
                        self.setAttr('Compute', val=1)
                if op == 2:
                    self.size = np.prod(self.shape)
                    sel = self.getVal('Selection')
                    k = 0
                    data_ind = list(range(self.ndim))
                    val = self.getVal(event)
                    for i in sel:
                        data_ind.remove(i+k)
                        k = k+1
                        old_val = self.shape[index]
                    if self.ndim + index in data_ind:
                        linked_index = index - 1
                    else:
                        linked_index = index + 1
                    dim_product = old_val * self.shape[linked_index]
                    val = new_val
                    while(np.mod(dim_product,val) != 0 and val > 1
                                 and val < dim_product):
                        if new_val > old_val:
                            val = val + 1
                        elif new_val < old_val:
                            val = val - 1
                    self.shape[index] = val
                    self.shape[linked_index] = dim_product // val
                    self.setAttr(event, val=val)
                    self.setAttr(self.dim_base_name+str(linked_index)+']',
                                      val=self.shape[linked_index])
                    self.size = np.prod(self.shape)
                if self.op_buttons[op] == 'Transpose':
                    count_trans_ind = list(range(-data.ndim, 0))
                    for i in range(data.ndim):
                        trans_ind = self.getVal(self.dim_base_name+
                                                         str(-i-1)+']')
                        self.trans_ind[-i-1] = trans_ind
                        self.shape[-i-1] = data.shape[trans_ind]
                        if trans_ind < 0:
                            trans_ind = trans_ind + data.ndim
                        count_trans_ind[-i-1] = trans_ind
                    dup_count = max([count_trans_ind.count(i)
                                    for i in count_trans_ind])
                    if dup_count > 1:
                        self.setAttr('Compute', val = 0)
                        self.info_message="Transpose indices must all be unique\n"
                    elif self.comp == 1:
                        self.setAttr('Compute', val=1)
                
        # disable compute when output and input data sizes are not equivalent
        if ('Compute' in self.widgetEvents()):
            self.info_message = ""
            if self.comp == 1:
                self.comp = 0
            else:
                self.comp = 1

        self.size = np.prod(self.shape)
        if self.size != data.size and op == 0:
            self.setAttr('Compute', val=0)
            self.info_message = "The output and input sizes must match\n"
        if self.op_buttons[op] == 'Transpose':
            count_trans_ind = list(range(-data.ndim, 0))
            for i in range(data.ndim):
                trans_ind = self.getVal(self.dim_base_name+
                                                 str(-i-1)+']')
                if trans_ind < 0:
                    trans_ind = trans_ind + data.ndim
                count_trans_ind[-i-1] = trans_ind
            dup_count = max([count_trans_ind.count(i)
                            for i in count_trans_ind])
            if dup_count > 1:
                self.setAttr('Compute', val = 0)
                self.info_message="Transpose indices must all be unique\n"

        self.reset = 0
        # updata info 
        info = basic_info+"Output Dimensions: "+str(self.shape)+"\n" \
               "Output Size: "+str(self.size)+"\n"+self.info_message
        self.setAttr('Info:', val = info)
        if( self.getVal('Compute')):
            self.setDetailLabel(self.op_buttons[op])
        else:
            self.setDetailLabel("{} (idle)".format(self.op_buttons[op]))

        return(0)

    def compute(self):

        import numpy as np

        data = self.getData('in')
        op = self.getVal('Operation')
        basic_info = "Input Dimensions: "+str(data.shape)+"\n" \
                     "Input Size: "+str(data.size)+"\n"

        if self.getVal('Compute'):
            if op in [0, 1, 2]: #Reshape, Combine, or Split
                out = data
                out.shape = self.shape
            if op == 3: # Extend
                temp = data
                temp.shape = self.shape
                for i in self.rep_ind:
                    reps = self.getVal(self.dim_base_name+
                                                str(i-len(self.shape))+']')
                    temp = np.repeat(temp, reps, axis = i)
                out = temp
            if self.op_buttons[op] == 'Tile': # Tile
                tile_dim = self.getVal('Tile Dimension')
                row_size = self.getVal('# Rows')
                column_size = self.getVal('# Columns')
                append_size = row_size * column_size - data.shape[tile_dim-3]
                append_shape = list(data.shape)
                append_shape[tile_dim-3] = append_size
                padded_data = np.append(data, np.zeros(append_shape),
                                        tile_dim-3)
                split_shape = [1] * (data.ndim + 1)
                tile_trans_ind = [1] * (data.ndim + 1)
                if tile_dim == 2:
                    tile_trans_ind[-4:] = [-2, -4, -1, -3]
                elif tile_dim == 1:
                    tile_trans_ind[-4:] = [-3, -4, -2, -1]
                else:
                    tile_trans_ind[-4:] = [-4, -2, -3, -1]

                for i in range(-data.ndim - 1, 0):
                    if i < tile_dim-4:
                        split_shape[i] = data.shape[i+1]
                    elif i == tile_dim-4:
                        split_shape[i] = row_size
                    elif i == tile_dim-3:
                        split_shape[i] = column_size
                    else:
                        split_shape[i] = data.shape[i]
                    if i < -4:
                        tile_trans_ind[i] = i
                padded_data.shape = split_shape
                out = np.ascontiguousarray(padded_data.transpose(
                                           tile_trans_ind))
                out.shape = self.shape
            if self.op_buttons[op] == 'Transpose': # Transpose
                out = data.transpose(self.trans_ind)
            if self.op_buttons[op] == 'Flip': # Flip
                g = globals()
                l = locals()
                exec(self.flip_string,g,l)
                out = l['out']
            if self.op_buttons[op] in ['Shift', 'CircShift']:
                temp = data
                for i in range(data.ndim):
                    shift = self.getVal(self.dim_base_name+
                                                 str(-i-1)+']')
                    if self.op_buttons[op] == 'Shift':
                        if shift <= 0:
                            shift = max(0, -shift)
                            del_range = list(range(shift))
                            insert_vals = [data.shape[-i-1]] * shift
                            temp = np.insert(temp, insert_vals, 0, axis = -i-1)
                            temp = np.delete(temp, del_range, axis = -i-1)
                        else:
                            shift = min(shift, data.shape[-i-1])
                            insert_vals = [0] * shift
                            del_range = list(range(data.shape[-i-1] - shift,
                                              data.shape[-i-1] + 1))
                            temp = np.delete(temp, del_range, axis = -i-1)
                            temp = np.insert(temp, insert_vals, 0, axis = -i-1)

                    if self.op_buttons[op] == 'CircShift':
                        temp = np.roll(temp, shift, axis = -i-1)
                out = temp
            self.shape = out.shape
            self.size = np.prod(self.shape)
            self.setData('out', out)

        # updata info 
        info = basic_info+"Output Dimensions: "+str(self.shape)+"\n" \
               "Output Size: "+str(self.size)+"\n"+self.info_message
        self.setAttr('Info:', val = info)

        return(0)

    def execType(self):
        '''Could be GPI_THREAD, GPI_PROCESS, GPI_APPLOOP'''
        return gpi.GPI_PROCESS
