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

import gpi
import sys
import traceback
import numpy as np
from math import fabs, sqrt, exp

class ExternalNode(gpi.NodeAPI):
    """Collapse data along selected dimension

        INPUT - input array

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
        for i in range(-1, -5, -1):
           dim_buttons.append(str(i))
    
        self.addWidget('PushButton', 'Compute', toggle=True, val=1)
        self.addWidget('PushButton', 'Collapse All', toggle=True, val=0)
        self.addWidget('ExclusivePushButtons','Dimension',buttons=dim_buttons, val=0)    
        self.addWidget('PushButton', 'Span Entire Dimension', toggle=True, val=1)
        self.addWidget('Slider', 'Dimension Start_Index', min=0, max=1, val=0)
        self.addWidget('Slider', 'Dimension Stop_Index', min=0, max=1, val=1)
        self.addWidget('PushButton', 'Non-Zero', toggle=True, val=0)
        
            # IO Ports
        self.addInPort('in', 'NPYarray', obligation=gpi.REQUIRED)
        self.addOutPort('Collapse Single Dim','NPYarray')
        self.addOutPort('Collapse All Dims','FLOAT')
        self.addOutPort('Max Val Index','PASS')
    
    def validate(self):

        data = self.getData('in')
        dim_number = self.getVal('Dimension')
        self.dim = int(-(dim_number+1))
        try:
          dlen = data.shape[self.dim]
        except (ValueError, IndexError):
          self.log.warn("Chosen Dimension does not exist. Please make another selection")
          return 1
        dim_buttons = []
        for i in range(-1, -(data.ndim+1), -1):
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
            print(str(self.dim)) 

        # Check for Start Index to never exceed Stop Index
        I_maxval = self.getVal('Dimension Start_Index')
        F_maxval = self.getVal('Dimension Stop_Index')
        if I_maxval > F_maxval:
            self.setAttr('Dimension Start_Index', val=np.maximum(I_maxval,F_maxval))
            self.setAttr('Dimension Stop_Index', val=np.maximum(I_maxval,F_maxval))    

        # Check for Compute enabled/disabled
        if self.getVal('Compute')==0:
            self.setData('Collapse Single Dim',None)
            self.setData('Collapse All Dims',None)
            self.setData('Max Val Index',None)
            
        self.setAttr('Non-Zero',visible=True)
    

    def compute(self):

        import sys
        import numpy as np
        import scipy as sp
        data_in = np.dtype(float)
        data_in = self.getData('in')
        op = self.getVal('Operation')
        nonzero = self.getVal('Non-Zero')
    
        dim_number = self.getVal('Dimension')
        self.dim = int(-(dim_number+1))
        try:
          dlen = data_in.shape[self.dim]
        except (ValueError, IndexError):
          self.log.warn("Chosen Dimension does not exist. Please make another selection")
          return 1
        temp1_data = data_in.swapaxes(self.dim,0)
        self.setAttr('Dimension Start_Index', min=0, max=dlen)
        self.setAttr('Dimension Stop_Index', min=0, max=dlen)
        if self.getVal('Span Entire Dimension'):
            temp2_data = temp1_data
        else:
            I_maxval = self.getVal('Dimension Start_Index')
            F_maxval = self.getVal('Dimension Stop_Index')
            temp2_data = temp1_data[I_maxval:F_maxval+1]
        data = temp2_data.swapaxes(self.dim,0)
        if self.getVal('Compute'):
            if op == 0:    # Min
                if self.getVal('Collapse All')==0:
                    if nonzero:
                        tempData = np.zeros_like(data)
                        np.copyto(tempData,data)
                        np.copyto(tempData,np.nan,where=(tempData == 0))
                        collapse_dim = np.nanmin(tempData, axis=self.dim)
                        np.nan_to_num(collapse_dim,copy = False)
                    else:
                        collapse_dim = np.amin(data, axis=self.dim)
                else:
                    if nonzero:
                        collapse_all = np.amin(data[np.nonzero(data)])
                    else:
                        collapse_all = np.amin(data)
            if op == 1:    # Max
                if self.getVal('Collapse All')==0:
                    if nonzero:
                        tempData = np.zeros_like(data)
                        np.copyto(tempData,data)
                        np.copyto(tempData,np.nan,where=(tempData == 0))
                        collapse_dim = np.nanmax(tempData, axis=self.dim)
                        np.nan_to_num(collapse_dim,copy = False)
                    else:
                        collapse_dim = np.amax(data, axis=self.dim)
                else:
                    if nonzero:
                        collapse_all = np.amax(data[np.nonzero(data)])
                    else:
                        collapse_all = np.amax(data)
            if op == 2:    # Mean
                if self.getVal('Collapse All')==0:
                    if nonzero:
                        tempData = np.zeros_like(data)
                        np.copyto(tempData,data)
                        np.copyto(tempData,np.nan,where=(tempData == 0))
                        collapse_dim = np.nanmean(tempData, axis=self.dim)
                        np.nan_to_num(collapse_dim,copy = False)
                    else:
                        collapse_dim = np.mean(data, axis=self.dim)
                else: # collapse all
                    if nonzero:
                        collapse_all = np.mean(data[np.nonzero(data)])
                    else:
                        collapse_all = np.mean(data)
            if op == 3:    # Standard Deviation
                if self.getVal('Collapse All')==0:
                    if nonzero:
                        tempData = np.zeros_like(data)
                        np.copyto(tempData,data)
                        np.copyto(tempData,np.nan,where=(tempData == 0))
                        collapse_dim = np.nanstd(tempData, axis=self.dim)
                        np.nan_to_num(collapse_dim,copy = False)
                    else:
                        collapse_dim = np.std(data, axis=self.dim)
                else:
                    if nonzero:
                        collapse_all = np.std(data[np.nonzero(data)])
                    else:
                        collapse_all = np.std(data)
            if op == 4:    # Sum
                if self.getVal('Collapse All')==0:
                    collapse_dim = np.sum(data, axis=self.dim)
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
                if self.getVal('Collapse All')==0:
                    if nonzero:
                        tempData = np.ones_like(temp)
                        np.copyto(tempData,temp)
                        np.copyto(tempData,np.nan,where=(tempData == 0))
                        temp1_sq = np.square(tempData)
                        temp1_msq = np.nanmean(temp1_sq, axis=self.dim)
                        np.nan_to_num(temp1_msq,copy = False)
                        collapse_dim = np.sqrt(temp1_msq)
                    else:
                        temp1_sq = np.square(temp)
                        temp1_msq = np.mean(temp1_sq, axis=self.dim)
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
                if self.getVal('Collapse All')==0:
                    collapse_dim = np.sum(temp_sq, axis=self.dim)
                else:
                    if nonzero:
                        collapse_all = np.sum(tempnz_sq)
                    else:
                        collapse_all = np.sum(temp_sq)
            if op == 7:    # Self Weighted Avg.
                if self.getVal('Collapse All')==0:
                    temp1_sos = np.sum(np.square(data), axis=self.dim)
                    temp1_sum = np.sum(data, axis=self.dim)
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
                if self.getVal('Collapse All')==0:
                    if nonzero:
                        stripMin = np.amin(data, axis = self.dim, keepdims = True)
                        tempData = np.zeros_like(data)
                        np.copyto(tempData,data)
                        tempData = tempData - stripMin
                        np.copyto(tempData,0,where = (data == 0))
                        collapse_dim = np.argmax(tempData, axis=self.dim)
                        np.nan_to_num(collapse_dim,copy = False)
                    else:
                        collapse_dim = np.argmax(data, axis=self.dim)
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
                if self.getVal('Collapse All')==0:
                    if nonzero:
                        tempData = np.zeros_like(data)
                        np.copyto(tempData,data)
                        np.copyto(tempData,np.nan,where=(tempData == 0))
                        collapse_dim = np.nanprod(tempData, axis=self.dim)
                    else:
                        collapse_dim = np.prod(data, axis=self.dim)
                else:
                    if nonzero:
                        collapse_all = np.prod(data[np.nonzero(data)])
                    else:
                        collapse_all = np.prod(data)
            if op == 10:    # Geometric Avg.
                if self.getVal('Collapse All')==0:
                    if nonzero:
                        tempData = np.zeros_like(data)
                        np.copyto(tempData,data)
                        temp1_size = np.count_nonzero(tempData, axis=self.dim).astype(float)
                        np.copyto(tempData,np.nan,where=(tempData == 0))
                        temp1_prod = np.nanprod(tempData, axis=self.dim)
                        # Note - the two lines below would give a complex geo-mean for negative products
                        # But I will leave this out for now so it just throws a warning and gives 0
                        # if(np.amin(temp1_prod) < 0):
                        #     temp1_prod = temp1_prod.astype(complex)
                        temp1_exp = np.divide(1.,temp1_size, out = np.zeros_like(temp1_size), where = (temp1_size != 0))
                        collapse_dim = np.power(temp1_prod, temp1_exp, out = np.zeros_like(temp1_prod),where = (temp1_size != 0))
                        np.nan_to_num(collapse_dim,copy = False)
                    else:
                        temp1_prod = np.prod(data, axis=self.dim)
                        temp1_size = np.size(data, axis=self.dim)
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
                if self.getVal('Collapse All')==0:
                    if nonzero:
                        tempData = np.zeros_like(data)
                        np.copyto(tempData,data)
                        np.copyto(tempData,np.nan,where=(tempData == 0))
                        collapse_dim = np.nanmedian(tempData, axis=self.dim)
                        np.nan_to_num(collapse_dim,copy = False)
                    else:
                        collapse_dim = np.median(data, axis=self.dim)
                else:
                    if nonzero:
                        collapse_all = np.median(data[np.nonzero(data)])
                    else:
                        collapse_all = np.median(data)


            if self.getVal('Collapse All'):
                if op == 8:
                    maxval_dict = {'index':collapse_all}
                    self.setData('Max Val Index', list(collapse_all))
                    temp_index = np.asarray(collapse_all)
                    self.setData('Collapse All Dims', float(np.prod(temp_index)))
                else:
                    self.setData('Collapse All Dims', float(collapse_all))
                    self.setData('Max Val Index', None)
                self.setData('Collapse Single Dim', None)
                self.setAttr('Status', val='Ready')
                out_op = self.op_buttons[op]
                info = out_op+" = "+str(collapse_all)+"\n"
                self.setAttr('Info', val=info)
            else:
                self.setData('Collapse Single Dim', collapse_dim)
                self.setData('Collapse All Dims', None)
                self.setData('Max Val Index', None)
                self.setAttr('Status', val='Ready')
                info = "input: "+str(data.shape) +"\noutput: "+str(collapse_dim.shape)
                self.setAttr('Info', val=info)

        return(0)


    def execType(self):
#        '''Could be GPI_THREAD, GPI_PROCESS, GPI_APPLOOP'''
         return gpi.GPI_PROCESS
