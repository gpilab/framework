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


#Author: Sudarshan Ragunathan
#Date: 2013aug05
#Torch tensor support: added following the Math node's pattern, 2026-09-16

import gpi
import sys
import traceback
import numpy as np
from math import fabs, sqrt, exp


# Ops whose ordering (min/max/argmax) is not defined for complex tensors in
# torch (unlike numpy, which orders complex by real-then-imaginary part).
_NO_COMPLEX_OPS_TORCH = {0, 1, 8, 11}


def _is_torch(data):
    if data is None:
        return False
    mod = type(data).__module__
    return mod.split('.')[0] == 'torch'


class ExternalNode(gpi.NodeAPI):
    """Collapse data along selected dimension

        INPUT - input array (NumPy array or PyTorch tensor)

        OUTPUTS:
        Collapse Single Dim - output array, with 1 less dimension than input array (collapsed version)
        Collapse All Dims - single float value from taking operation on entire array, active when "Collapse All" is selected
        Max Val Index - returns the index of the max value when used with collapse all (type : list)

        WIDGETS:
        Status,Info - information boxes
        Operation - selected method of collapse
        Min,Max,Mean,Std. Dev,Sum,Prod,Median - self-evident
        RMS - performs rms over the magnitude of complex input, else performs rms directly on input
        Energy - sum of squares along dimension
        SWA - Energy/Sum
        Max Val Index - index along dimension at which the maximum value occurs
        Geo-Avg - Nth root of Prod, where N is the size of the collapse dimension
        Dimension - dimension along with to collapse
        Compute - compute
        Span Entire Dimension - select whether to collapse along the entire span of specified dimension
        Dimension Start_Index - if Span Entire Dimension is off, lets you pick index of where collapse starts
        Dimension Stop_Index  - if Span Entire Dimension is off, lets you pick index of where collapse ends
        Collapse_All - when off, module collapses along single (specified) dimension, output array at Collapse Dim
                   when on, module collapses entire data set, output value at Collapse All
        Non-Zero - Used with Collapse All to perform collapse on non-zero values of ndarray
        Accepts NumPy arrays and/or PyTorch tensors on 'in'; torch tensors
        are processed on the CPU. Output kind (numpy/torch) always matches
        the input kind. Min/Max/Max Val Index/Median have no complex-tensor
        ordering in torch, so on complex data those ops transparently fall
        back to NumPy for just that operation (a warning is logged). Median
        on torch also differs from NumPy for even-length reductions (picks
        the lower of the two middle values instead of averaging them).
    """

    def initUI(self):

        # Widgets
        self.addWidget('TextBox', 'Status', val='Ready.')
        self.addWidget('TextBox', 'Info', val='Displays single value float results only')
        self.maxdim = 13
        self.ndim = self.maxdim
        self.dim = 0
        self.size = 0
        self.op_buttons = ['Min','Max','Mean','Std. Dev','Sum','RMS','Energy','SWA','Max Val Index','Prod','Geo-Avg','Median']
        self.addWidget('ExclusiveRadioButtons','Operation', buttons=self.op_buttons, val=0)
        dim_buttons = []
        for i in range(-4, 0):
           dim_buttons.append(str(i))
    
        self.addWidget('PushButton', 'Compute', toggle=True, val=True)
        self.addWidget('PushButton', 'Collapse All', toggle=True, val=0)
        self.addWidget('ExclusivePushButtons','Dimension',buttons=dim_buttons, val=0)    
        self.addWidget('PushButton', 'Span Entire Dimension', toggle=True, val=1)
        self.addWidget('Slider', 'Dimension Start_Index', min=0, max=1, val=0)
        self.addWidget('Slider', 'Dimension Stop_Index', min=0, max=1, val=1)
        self.addWidget('PushButton', 'Non-Zero', toggle=True, val=0)
        
            # IO Ports
        self.addInPort('in', 'NPYorTorch', obligation=gpi.REQUIRED)
        self.addOutPort('Collapse Single Dim','NPYorTorch')
        self.addOutPort('Collapse All Dims','FLOAT')
        self.addOutPort('Max Val Index','PASS')
    
    def validate(self):

        data = self.getData('in')
        dim_number = self.getVal('Dimension')
        self.dim = int(dim_number - data.ndim)
        try:
          dlen = data.shape[self.dim]
        except (ValueError, IndexError):
          self.log.warn("Chosen Dimension does not exist. Please make another selection")
          return 1
        dim_buttons = []
        for i in range(-data.ndim, 0):
            dim_buttons.append(str(i))
        self.setAttr('Dimension', buttons=dim_buttons)    
    
        # Change visibility of Start and Stop Index Sliders 
        if self.getVal('Collapse All'):
          self.setAttr('Dimension', visible=False)
          self.setAttr('Span Entire Dimension', visible=False)
          self.setAttr('Dimension Start_Index', visible=False)
          self.setAttr('Dimension Stop_Index', visible=False)
        else:
          self.setAttr('Dimension', visible=True)
          self.setAttr('Span Entire Dimension', visible=True)
          if self.getVal('Span Entire Dimension'):
            self.setAttr('Dimension Start_Index', visible=False,min=0,max=0)
            self.setAttr('Dimension Stop_Index', visible=False,min=0,max=0)
          else:
            self.setAttr('Dimension Start_Index',visible=True,min=0,max=dlen)
            self.setAttr('Dimension Stop_Index',visible=True,min=0,max=dlen)
    
        # Set Collapse all if # dimensions = 1
        if data.ndim == 1:
            self.setAttr('Collapse All', val=1)

        # Check for Start Index to never exceed Stop Index
        I_maxval = self.getVal('Dimension Start_Index')
        F_maxval = self.getVal('Dimension Stop_Index')
        if I_maxval > F_maxval:
            self.setAttr('Dimension Start_Index', val=np.maximum(I_maxval,F_maxval))
            self.setAttr('Dimension Stop_Index', val=np.maximum(I_maxval,F_maxval))    

        if self.getVal('Collapse All'):
            output_shape = ()
        else:
            output_shape = list(data.shape)
            output_shape.pop(self.dim)
        self.setAttr('Info', val=(f'input: {data.shape}\n'
                                  f'output: {output_shape}'))

        # Check for Compute enabled/disabled
        if self.getVal('Compute')==0:
            self.setData('Collapse Single Dim',None)
            self.setData('Collapse All Dims',None)
            self.setData('Max Val Index',None)
            
        self.setAttr('Non-Zero',visible=True)
    

    def compute(self):

        import numpy as np
        data_in = self.getData('in')
        op = self.getVal('Operation')
        nonzero = self.getVal('Non-Zero')
        collapse_all_flag = bool(self.getVal('Collapse All'))

        dim_number = self.getVal('Dimension')
        self.dim = int(dim_number - data_in.ndim)
        try:
          dlen = data_in.shape[self.dim]
        except (ValueError, IndexError):
          self.log.warn("Chosen Dimension does not exist. Please make another selection")
          return 1
        self.setAttr('Dimension Start_Index', min=0, max=dlen)
        self.setAttr('Dimension Stop_Index', min=0, max=dlen)

        if not self.getVal('Compute'):
            return 0

        primary_was_torch = _is_torch(data_in)
        is_torch = primary_was_torch

        try:
            # no GPU support -- torch tensors are always computed on the CPU
            data = data_in.cpu() if is_torch else self._as_numpy(data_in)

            temp1_data = data.swapaxes(self.dim, 0)
            if self.getVal('Span Entire Dimension'):
                temp2_data = temp1_data
            else:
                I_maxval = self.getVal('Dimension Start_Index')
                F_maxval = self.getVal('Dimension Stop_Index')
                temp2_data = temp1_data[I_maxval:F_maxval+1]
            data = temp2_data.swapaxes(self.dim, 0)

            if is_torch:
                collapse_dim, collapse_all = self._collapse_torch(
                    data, op, nonzero, collapse_all_flag, self.dim)
            else:
                collapse_dim, collapse_all = self._collapse_numpy(
                    data, op, nonzero, collapse_all_flag, self.dim)
        except Exception as e:
            self.log.error('Collapse failed: {}'.format(e))
            return 1

        if collapse_all_flag:
            if op == 8:
                idx = [int(i) for i in collapse_all]
                self.setData('Max Val Index', idx)
                self.setData('Collapse All Dims', float(np.prod(idx)))
            else:
                self.setData('Collapse All Dims', float(collapse_all))
                self.setData('Max Val Index', None)
            self.setData('Collapse Single Dim', None)
            self.setAttr('Status', val='Ready')
            out_op = self.op_buttons[op]
            info = out_op+" = "+str(collapse_all)+"\n"
            self.setAttr('Info', val=info)
        else:
            out = self._to_output_kind(collapse_dim, primary_was_torch)
            self.setData('Collapse Single Dim', out)
            self.setData('Collapse All Dims', None)
            self.setData('Max Val Index', None)
            self.setAttr('Status', val='Ready')
            info = "input: "+str(tuple(data.shape)) +"\noutput: "+str(tuple(out.shape))
            self.setAttr('Info', val=info)

        return(0)

    def _collapse_numpy(self, data, op, nonzero, collapse_all_flag, dim):
        '''Original NumPy implementation, unchanged in behavior.
        Returns (collapse_dim, collapse_all) -- exactly one is populated.
        '''
        collapse_dim = None
        collapse_all = None
        if op == 0:    # Min
            if not collapse_all_flag:
                if nonzero:
                    tempData = np.zeros_like(data)
                    np.copyto(tempData,data)
                    np.copyto(tempData,np.nan,where=(tempData == 0))
                    collapse_dim = np.nanmin(tempData, axis=dim)
                    np.nan_to_num(collapse_dim,copy = False)
                else:
                    collapse_dim = np.amin(data, axis=dim)
            else:
                if nonzero:
                    collapse_all = np.amin(data[np.nonzero(data)])
                else:
                    collapse_all = np.amin(data)
        if op == 1:    # Max
            if not collapse_all_flag:
                if nonzero:
                    tempData = np.zeros_like(data)
                    np.copyto(tempData,data)
                    np.copyto(tempData,np.nan,where=(tempData == 0))
                    collapse_dim = np.nanmax(tempData, axis=dim)
                    np.nan_to_num(collapse_dim,copy = False)
                else:
                    collapse_dim = np.amax(data, axis=dim)
            else:
                if nonzero:
                    collapse_all = np.amax(data[np.nonzero(data)])
                else:
                    collapse_all = np.amax(data)
        if op == 2:    # Mean
            if not collapse_all_flag:
                if nonzero:
                    tempData = np.zeros_like(data)
                    np.copyto(tempData,data)
                    np.copyto(tempData,np.nan,where=(tempData == 0))
                    collapse_dim = np.nanmean(tempData, axis=dim)
                    np.nan_to_num(collapse_dim,copy = False)
                else:
                    collapse_dim = np.mean(data, axis=dim)
            else: # collapse all
                if nonzero:
                    collapse_all = np.mean(data[np.nonzero(data)])
                else:
                    collapse_all = np.mean(data)
        if op == 3:    # Standard Deviation
            if not collapse_all_flag:
                if nonzero:
                    tempData = np.zeros_like(data)
                    np.copyto(tempData,data)
                    np.copyto(tempData,np.nan,where=(tempData == 0))
                    collapse_dim = np.nanstd(tempData, axis=dim)
                    np.nan_to_num(collapse_dim,copy = False)
                else:
                    collapse_dim = np.std(data, axis=dim)
            else:
                if nonzero:
                    collapse_all = np.std(data[np.nonzero(data)])
                else:
                    collapse_all = np.std(data)
        if op == 4:    # Sum
            if not collapse_all_flag:
                collapse_dim = np.sum(data, axis=dim)
            else:
                if nonzero:
                    collapse_all = np.sum(data[np.nonzero(data)])
                else:
                    collapse_all = np.sum(data)
        if op == 5:    # RMS
            data_type = str(data.dtype)
            if ('float' in data_type) or ('int' in data_type):
                temp = data
                temp_nz = data[np.nonzero(data)]
            elif 'complex' in data_type:
                data_mag = np.abs(data)
                temp = data_mag
                temp_nz = data_mag[np.nonzero(data_mag)]
            if not collapse_all_flag:
                if nonzero:
                    tempData = np.ones_like(temp)
                    np.copyto(tempData,temp)
                    np.copyto(tempData,np.nan,where=(tempData == 0))
                    temp1_sq = np.square(tempData)
                    temp1_msq = np.nanmean(temp1_sq, axis=dim)
                    np.nan_to_num(temp1_msq,copy = False)
                    collapse_dim = np.sqrt(temp1_msq)
                else:
                    temp1_sq = np.square(temp)
                    temp1_msq = np.mean(temp1_sq, axis=dim)
                    collapse_dim = np.sqrt(temp1_msq)
            else:
                if nonzero:
                    temp2_sq = np.square(temp_nz)
                    temp2_msq = np.mean(temp2_sq)
                    collapse_all = np.sqrt(temp2_msq)
                else:
                    temp2_sq = np.square(temp)
                    temp2_msq = np.mean(temp2_sq)
                    collapse_all = np.sqrt(temp2_msq)
        if op == 6:    # Energy
            temp_sq = np.square(data)
            tempnz_sq = np.square(data[np.nonzero(data)])
            if not collapse_all_flag:
                collapse_dim = np.sum(temp_sq, axis=dim)
            else:
                if nonzero:
                    collapse_all = np.sum(tempnz_sq)
                else:
                    collapse_all = np.sum(temp_sq)
        if op == 7:    # Self Weighted Avg.
            if not collapse_all_flag:
                temp1_sos = np.sum(np.square(data), axis=dim)
                temp1_sum = np.sum(data, axis=dim)
                collapse_dim = np.divide(temp1_sos, temp1_sum)
            else:
                if nonzero:
                    temp2_sos = np.sum(np.square(data[np.nonzero(data)]))
                    temp2_sum = np.sum(data[np.nonzero(data)])
                    collapse_all = np.divide(temp2_sos, temp2_sum)
                else:
                    temp2_sos = np.sum(np.square(data))
                    temp2_sum = np.sum(data)
                    collapse_all = np.divide(temp2_sos, temp2_sum)
        if op == 8:    # Max Value Index
            if not collapse_all_flag:
                if nonzero:
                    stripMin = np.amin(data, axis = dim, keepdims = True)
                    tempData = np.zeros_like(data)
                    np.copyto(tempData,data)
                    tempData = tempData - stripMin
                    np.copyto(tempData,0,where = (data == 0))
                    collapse_dim = np.argmax(tempData, axis=dim)
                    np.nan_to_num(collapse_dim,copy = False)
                else:
                    collapse_dim = np.argmax(data, axis=dim)
            else:
                if nonzero:
                    globalMin = np.amin(data)
                    tempData = np.zeros_like(data)
                    np.copyto(tempData,data)
                    tempData = data - globalMin
                    np.copyto(tempData,0,where = (data == 0))
                    collapse_all = np.unravel_index(tempData.argmax(),data.shape)
                else:
                    collapse_all = np.unravel_index(data.argmax(),data.shape)
        if op == 9:    # Product
            if not collapse_all_flag:
                if nonzero:
                    tempData = np.zeros_like(data)
                    np.copyto(tempData,data)
                    np.copyto(tempData,np.nan,where=(tempData == 0))
                    collapse_dim = np.nanprod(tempData, axis=dim)
                else:
                    collapse_dim = np.prod(data, axis=dim)
            else:
                if nonzero:
                    collapse_all = np.prod(data[np.nonzero(data)])
                else:
                    collapse_all = np.prod(data)
        if op == 10:    # Geometric Avg.
            if not collapse_all_flag:
                if nonzero:
                    tempData = np.zeros_like(data)
                    np.copyto(tempData,data)
                    temp1_size = np.count_nonzero(tempData, axis=dim).astype(float)
                    np.copyto(tempData,np.nan,where=(tempData == 0))
                    temp1_prod = np.nanprod(tempData, axis=dim)
                    # Note - the two lines below would give a complex geo-mean for negative products
                    # But I will leave this out for now so it just throws a warning and gives 0
                    # if(np.amin(temp1_prod) < 0):
                    #     temp1_prod = temp1_prod.astype(complex)
                    temp1_exp = np.divide(1.,temp1_size, out = np.zeros_like(temp1_size), where = (temp1_size != 0))
                    collapse_dim = np.power(temp1_prod, temp1_exp, out = np.zeros_like(temp1_prod),where = (temp1_size != 0))
                    np.nan_to_num(collapse_dim,copy = False)
                else:
                    temp1_prod = np.prod(data, axis=dim)
                    temp1_size = np.size(data, axis=dim)
                    collapse_dim = np.power(temp1_prod, (1/temp1_size))
            else:
                if nonzero:
                    temp2_prod = np.prod(data[np.nonzero(data)])
                    temp2_size = np.size(data[np.nonzero(data)])
                    collapse_all = np.power(temp2_prod, (1/temp2_size))
                else:
                    temp2_prod = np.prod(data)
                    temp2_size = np.size(data)
                    collapse_all = np.power(temp2_prod, (1/temp2_size))
        if op == 11:    # Median
            if not collapse_all_flag:
                if nonzero:
                    tempData = np.zeros_like(data)
                    np.copyto(tempData,data)
                    np.copyto(tempData,np.nan,where=(tempData == 0))
                    collapse_dim = np.nanmedian(tempData, axis=dim)
                    np.nan_to_num(collapse_dim,copy = False)
                else:
                    collapse_dim = np.median(data, axis=dim)
            else:
                if nonzero:
                    collapse_all = np.median(data[np.nonzero(data)])
                else:
                    collapse_all = np.median(data)
        return collapse_dim, collapse_all

    def _collapse_torch(self, data, op, nonzero, collapse_all_flag, dim):
        '''Torch equivalent of _collapse_numpy(). Where torch has no nan*
        reduction (amin/amax/std/prod), masked-out ("Non-Zero") elements are
        substituted with a neutral/sentinel value instead of NaN, then
        corrected back to 0 for slices that end up fully masked out -- this
        reproduces the numpy path's nanX(...) + nan_to_num(...) pattern.
        Returns (collapse_dim, collapse_all) -- exactly one is populated.
        '''
        import torch

        is_cx = torch.is_complex(data)
        if is_cx and op in _NO_COMPLEX_OPS_TORCH:
            # torch has no complex ordering (amin/amax/argmax/nanmedian all
            # reject complex dtypes) -- numpy orders complex lexicographically
            # by (real, imag), so fall back to the numpy path on the CPU
            # rather than failing the node outright.
            self.log.warn(
                "'{}' has no complex-tensor ordering in torch -- falling "
                "back to NumPy/CPU for this operation.".format(self.op_buttons[op]))
            data_np = data.detach().cpu().numpy()
            collapse_dim, collapse_all = self._collapse_numpy(
                data_np, op, nonzero, collapse_all_flag, dim)
            if collapse_dim is not None:
                collapse_dim = torch.from_numpy(np.ascontiguousarray(collapse_dim))
            return collapse_dim, collapse_all

        collapse_dim = None
        collapse_all = None

        if op in (0, 1):    # Min / Max
            want_max = (op == 1)
            if data.is_floating_point():
                sentinel = torch.finfo(data.dtype).min if want_max else torch.finfo(data.dtype).max
            else:
                sentinel = torch.iinfo(data.dtype).min if want_max else torch.iinfo(data.dtype).max
            reduce_fn = torch.amax if want_max else torch.amin
            if not collapse_all_flag:
                if nonzero:
                    mask = data != 0
                    filled = torch.where(mask, data, torch.full_like(data, sentinel))
                    collapse_dim = reduce_fn(filled, dim=dim)
                    all_masked = (~mask).all(dim=dim)
                    collapse_dim = torch.where(all_masked, torch.zeros_like(collapse_dim), collapse_dim)
                else:
                    collapse_dim = reduce_fn(data, dim=dim)
            else:
                sel = data[data != 0] if nonzero else data.reshape(-1)
                collapse_all = reduce_fn(sel) if sel.numel() else torch.zeros((), dtype=data.dtype)

        elif op == 2:    # Mean
            if not collapse_all_flag:
                if nonzero:
                    if is_cx:
                        mask = data != 0
                        count = mask.sum(dim=dim)
                        s = torch.where(mask, data, torch.zeros_like(data)).sum(dim=dim)
                        collapse_dim = torch.where(count == 0, torch.zeros_like(s), s / count.clamp(min=1))
                    else:
                        filled = torch.where(data != 0, data, torch.full_like(data, float('nan')))
                        collapse_dim = torch.nan_to_num(torch.nanmean(filled, dim=dim))
                else:
                    collapse_dim = torch.mean(data, dim=dim)
            else:
                sel = data[data != 0] if nonzero else data.reshape(-1)
                collapse_all = sel.mean() if sel.numel() else torch.zeros((), dtype=data.dtype)

        elif op == 3:    # Standard Deviation (population, ddof=0)
            mask = (data != 0) if nonzero else torch.ones_like(data, dtype=torch.bool)
            if not collapse_all_flag:
                count = mask.sum(dim=dim, keepdim=True)
                count_safe = count.clamp(min=1)
                s = torch.where(mask, data, torch.zeros_like(data)).sum(dim=dim, keepdim=True)
                mean_kd = s / count_safe
                diff = torch.where(mask, data - mean_kd, torch.zeros_like(data))
                sq = diff.abs()**2 if is_cx else diff**2
                var = sq.sum(dim=dim, keepdim=True) / count_safe
                collapse_dim = torch.sqrt(var).squeeze(dim)
                collapse_dim = torch.where(count.squeeze(dim) == 0, torch.zeros_like(collapse_dim), collapse_dim)
            else:
                sel = data[mask]
                collapse_all = sel.std(unbiased=False) if sel.numel() else torch.zeros((), dtype=data.dtype)

        elif op == 4:    # Sum
            if not collapse_all_flag:
                collapse_dim = data.sum(dim=dim)
            else:
                sel = data[data != 0] if nonzero else data.reshape(-1)
                collapse_all = sel.sum() if sel.numel() else torch.zeros((), dtype=data.dtype)

        elif op == 5:    # RMS
            temp = data.abs() if is_cx else data
            if not collapse_all_flag:
                if nonzero:
                    filled = torch.where(temp != 0, temp, torch.full_like(temp, float('nan')))
                    msq = torch.nan_to_num(torch.nanmean(filled**2, dim=dim))
                    collapse_dim = torch.sqrt(msq)
                else:
                    collapse_dim = torch.sqrt(torch.mean(temp**2, dim=dim))
            else:
                sel = temp[temp != 0] if nonzero else temp.reshape(-1)
                collapse_all = torch.sqrt((sel**2).mean()) if sel.numel() else torch.zeros((), dtype=temp.dtype)

        elif op == 6:    # Energy
            sq = data**2
            if not collapse_all_flag:
                collapse_dim = sq.sum(dim=dim)
            else:
                sel = sq[data != 0] if nonzero else sq.reshape(-1)
                collapse_all = sel.sum() if sel.numel() else torch.zeros((), dtype=data.dtype)

        elif op == 7:    # Self Weighted Avg.
            if not collapse_all_flag:
                sos = (data**2).sum(dim=dim)
                s = data.sum(dim=dim)
                collapse_dim = sos / s
            else:
                sel = data[data != 0] if nonzero else data.reshape(-1)
                collapse_all = (sel**2).sum() / sel.sum() if sel.numel() else torch.zeros((), dtype=data.dtype)

        elif op == 8:    # Max Value Index
            if not collapse_all_flag:
                if nonzero:
                    stripMin = data.amin(dim=dim, keepdim=True)
                    tempData = torch.where(data == 0, torch.zeros_like(data), data - stripMin)
                    collapse_dim = torch.argmax(tempData, dim=dim)
                else:
                    collapse_dim = torch.argmax(data, dim=dim)
            else:
                if nonzero:
                    globalMin = data.amin()
                    tempData = torch.where(data == 0, torch.zeros_like(data), data - globalMin)
                    flat_idx = torch.argmax(tempData)
                else:
                    flat_idx = torch.argmax(data)
                collapse_all = torch.unravel_index(flat_idx, data.shape)

        elif op == 9:    # Product
            if not collapse_all_flag:
                if nonzero:
                    mask = data != 0
                    filled = torch.where(mask, data, torch.ones_like(data))
                    collapse_dim = torch.prod(filled, dim=dim)
                    all_masked = (~mask).all(dim=dim)
                    collapse_dim = torch.where(all_masked, torch.zeros_like(collapse_dim), collapse_dim)
                else:
                    collapse_dim = torch.prod(data, dim=dim)
            else:
                sel = data[data != 0] if nonzero else data.reshape(-1)
                collapse_all = torch.prod(sel) if sel.numel() else torch.zeros((), dtype=data.dtype)

        elif op == 10:    # Geometric Avg.
            if not collapse_all_flag:
                if nonzero:
                    mask = data != 0
                    count = mask.sum(dim=dim).to(torch.float64 if data.dtype == torch.float64 else torch.float32)
                    filled = torch.where(mask, data, torch.ones_like(data))
                    prod = torch.prod(filled, dim=dim)
                    have = count != 0
                    exp = torch.where(have, 1.0 / count.clamp(min=1), torch.zeros_like(count))
                    collapse_dim = torch.where(have, torch.pow(prod, exp), torch.zeros_like(prod))
                else:
                    prod = torch.prod(data, dim=dim)
                    n = data.shape[dim]
                    collapse_dim = torch.pow(prod, 1.0 / n)
            else:
                sel = data[data != 0] if nonzero else data.reshape(-1)
                n = sel.numel()
                collapse_all = torch.pow(torch.prod(sel), 1.0 / n) if n else torch.zeros((), dtype=data.dtype)

        elif op == 11:    # Median
            if not collapse_all_flag:
                if nonzero:
                    filled = torch.where(data != 0, data, torch.full_like(data, float('nan')))
                    collapse_dim = torch.nan_to_num(torch.nanmedian(filled, dim=dim).values)
                else:
                    collapse_dim = torch.median(data, dim=dim).values
            else:
                sel = data[data != 0] if nonzero else data.reshape(-1)
                collapse_all = torch.median(sel) if sel.numel() else torch.zeros((), dtype=data.dtype)

        return collapse_dim, collapse_all

    def _as_numpy(self, data):
        if _is_torch(data):
            return data.detach().cpu().numpy()
        return data

    def _to_output_kind(self, out, primary_was_torch):
        '''Match the input kind (torch tensors stay on CPU throughout).'''
        if _is_torch(out) and not primary_was_torch:
            out = out.numpy()
        return out

    def execType(self):
        return gpi.GPI_PROCESS

