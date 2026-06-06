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


# Author: Nick Zwart, Jim Pipe
# Date: 2012oct28, 2013Dec


import numpy as np
import gpi

class ExternalNode(gpi.NodeAPI):
    """A visual for-loop that produces floats and integers for a predefined limits and steps.
    Module will output an number, wait for all other modules to run, then output the next integer
    Also allows generation of uniformly distributed random numbers, and manually-entered numbers
    A second "bound" mode is employed when input port is populated for spanning the bounds of a given dim.

    INPUTS:
    in_array: When populated, user specifies dimension, and can automatically or manually change index
              in the range of that dimension

    OUTPUTS:
    int_out - integer output, given as round(float_out)
    dict_for_reduce - passes the widget type necessary to hook IntegerLoop up to Reduce widget InPort
    float_out - floating point output

    WIDGETS:
    Dimension - when in_array populated, lets user pick dimension to for step to span
    Randomize - output value is either RANDOM or LINEAR, the latter = Minimum + step*(Step Size)
    LOOP - when selected, step runs from 0 to "Number of Steps"-1
    Continuous - when selected, step returns to 0 after reaching "Number of Steps" and continues to run
    Minimum - value corresponding to step=0 for LINEAR mode, or minimum range of output for RANDOM mode
    Maximum - value corresponding to last step for LINEAR mode, or maximum range of output for RANDOM mode
    Step Size - change in value per step for LINEAR mode
    Number of Steps - number of iterations between Minimum and Maximum
    step - current index
    Value - current value presented at output, either a random number between Minimum and Maximum for RANDOM mode
            or equal to Minimum + step*(Maximum-Minimum)/("Number of Steps" - 1)
    """

    def execType(self):
        return gpi.GPI_THREAD

    def initUI(self):

        # Widgets
        self.addWidget('Slider', 'Dimension', val=0, visible = False)
        self.addWidget('PushButton', 'Randomize', button_title='LINEAR', toggle=True)
        self.addWidget('PushButton', 'LOOP', button_title='OFF', val=0, toggle=True)
        self.addWidget('PushButton', 'Continuous', button_title='OFF', val=0, toggle=True)
        self.addWidget('DoubleSpinBox', 'Minimum', val=0, decimals=5)
        self.addWidget('DoubleSpinBox', 'Maximum', val=0, decimals=5)
        self.addWidget('DoubleSpinBox', 'Step Size', val=0, decimals=5)
        self.addWidget('SpinBox', 'Number of Steps', val=2, min=2)
        self.addWidget('Slider', 'step', val=0)
        self.addWidget('DoubleSpinBox', 'Value', val=0, decimals=5)

        # IO Ports
        self.addInPort('in_array', 'NPYarray',obligation=gpi.OPTIONAL)
        self.addOutPort('int_out', 'INT')
        self.addOutPort('dict_for_Reduce', 'DICT')
        self.addOutPort('float_out', 'FLOAT')

    def validate(self):

        # change button Titles with toggle
        status = self.getVal('LOOP')
        loop_over = self.getVal('Continuous')

        if status:
          self.setAttr('LOOP', button_title='ON')
        else:
          self.setAttr('LOOP', button_title='OFF')
        
        if loop_over:
          self.setAttr('Continuous', button_title='ON')
        else:
          self.setAttr('Continuous', button_title='OFF')

          # ONLY CHANGE THINGS IF STATUS IS OFF...
          indat = self.getData('in_array')
          if indat is None:
            # NO INPUT
            self.setAttr('Dimension', visible = False)
            self.setAttr('Randomize', visible = True)
            self.setAttr('Minimum', visible = True)
            self.setAttr('Maximum', visible = True)
            self.setAttr('Number of Steps', visible = True)
            self.setAttr('Value', visible = True)
            randomize = self.getVal('Randomize')
            if randomize:
              self.setAttr('Randomize', button_title='RANDOM')
              self.setAttr('Step Size', visible = False)
            else:
              self.setAttr('Randomize', button_title='LINEAR')
              self.setAttr('Step Size', visible = True)

            # Reconcile min,max,nsteps,stepsize
            minval = self.getVal('Minimum')
            maxval = self.getVal('Maximum')
            nsteps = self.getVal('Number of Steps')
            stepsize = self.getVal('Step Size')

            # make sure minval + nsteps*stepsize = maxval
            if 'Step Size' in self.widgetEvents():
              if stepsize != 0:
                nsteps = max(2,round(abs((maxval-minval)/stepsize)) + 1)
              else:
                nsteps = 2
              self.setAttr('Number of Steps',quietval=nsteps)
            self.setAttr('Step Size',quietval=(maxval-minval)/float(nsteps-1))
            self.setAttr('step',max = nsteps-1)
            self.setAttr('Value',min=minval,max=maxval)
          else:
            # INPUT, act in "Bounds" mode
            self.setAttr('Dimension', visible = True,min = -indat.ndim,max=indat.ndim-1)
            self.setAttr('Randomize', visible = False)
            self.setAttr('Minimum', visible = False)
            self.setAttr('Maximum', visible = False)
            self.setAttr('Step Size', visible = False)
            self.setAttr('Value', visible = False)
            self.setAttr('Number of Steps', visible = False)

            ndim = self.getVal('Dimension')
            self.setAttr('step',min=0,max=indat.shape[ndim]-1)

        return 0

    def compute(self):

        import numpy as np

        indat = self.getData('in_array')
        status = self.getVal('LOOP')
        cstep = self.getVal('step')
        loop_over = self.getVal('Continuous')

        # Mode depends on whether input port is populated
        if indat is None:
          minv = self.getVal('Minimum')
          maxv = self.getVal('Maximum')
          random = self.getVal('Randomize')
          nstep = self.getVal('Number of Steps')
          stepsize = (maxv-minv)/float(nstep-1)
        else:
          ndim = self.getVal('Dimension')
          minv = 0
          maxv = indat.shape[ndim]-1
          random = False
          nstep = indat.shape[ndim]
          stepsize = 1.

        if status:
          # if ON, Advance Step unless LOOP just pressed
          if 'LOOP' in self.widgetEvents():
            cstep = 0
            self.setAttr('step',quietval=cstep)
          else:
            if cstep < nstep-1:
              cstep += 1
              self.setAttr('step',quietval=cstep)
            else:
                if loop_over:
                    cstep = 0
                    self.setAttr('step', quietval=cstep)
                else:
                    self.setAttr('LOOP', quietval=False, button_title='OFF')
                    status = False
                    self.setAttr('Continuous', quietval=False, button_title='OFF')
                    loop_over = False

        # If user changed value manually, reflect that
        if 'Value' in self.widgetEvents():
          cvalue = self.getVal('Value')
          if stepsize != 0 and not random:
            cstep = round((cvalue-minv)/stepsize)
            cvalue = minv + cstep*stepsize
            self.setAttr('step',quietval=cstep)
        else:
        # Otherwise update values appropriately
          if random:
            cvalue = minv + (maxv-minv)*np.random.random()
          else:
            cvalue = minv + cstep*stepsize

        self.setAttr('Value',quietval=cvalue)
        self.setData('int_out', int(round(cvalue)))
        self.setData('float_out', cvalue)

        # set dict output to be used for Reduce module
        dict_reduce = {}
        dict_reduce['selection'] = 2
        dict_reduce['width'] = 1
        dict_reduce['ceiling'] = round(cvalue)
        dict_reduce['center'] = round(cvalue)
        dict_reduce['floor'] = round(cvalue)
        self.setData('dict_for_Reduce', dict_reduce)

        # logic for looping
        if status and (cstep <= nstep-1):
          self.setReQueue(True)
        else:
          self.setReQueue(False)
          self.setAttr('LOOP',quietval=False, button_title='OFF')

        return(0)
