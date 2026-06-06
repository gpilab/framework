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


#!/usr/bin/env python
#__author__ = "Mike Schar"
#__date__ = "2013dmar27"

import gpi
from gpi import QtWidgets

# WIDGET
class ComboBox_GROUP(gpi.GenericWidgetGroup):
    """A combination of two comboBoxes for image quality measure of two images next to each other.
        """
    valueChanged = gpi.Signal()

    def __init__(self, title, parent=None):
        super().__init__(title, parent)

        self._val = {}
        self._val['image_quality_left'] = 0
        self._val['image_quality_right'] = 0

        #image_quality_left
        self.iql = gpi.ComboBox('image_quality_left')
        self.iql.set_items(['choose..', 'excellent', 'good', 'diagnostic', 'non-diagnostic'])
        #self.iql.set_val('choose..')
        self.iql.set_index(0)

        #image_quality_right
        self.iqr = gpi.ComboBox('image_quality_right')
        self.iqr.set_items(['choose..', 'excellent', 'good', 'diagnostic', 'non-diagnostic'])
        #self.iqr.set_val('choose..')
        self.iqr.set_index(0)

        self.iql.valueChanged.connect(self.iqlChange)
        self.iqr.valueChanged.connect(self.iqrChange)

        vbox = QtWidgets.QHBoxLayout()
        vbox.addWidget(self.iql)
        vbox.addWidget(self.iqr)
        vbox.setStretch(0, 0)
        vbox.setStretch(1, 0)
        vbox.setContentsMargins(0, 0, 0, 0)  # we don't need margins here
        vbox.setSpacing(0)
        self.setLayout(vbox)

    # setters
    def set_val(self, val):
      """A python-dict containing: image_quality_left and image_quality_right parms. """
      if 'image_quality_left' in val:
        # check if identical so this does not change every time compute is called (according to code in FFTW)
        if self._val['image_quality_left'] != val['image_quality_left']:
          self._val['image_quality_left'] = val['image_quality_left']
          self.iql.blockSignals(True)
          self.iql.set_index(val['image_quality_left'])
          self.iql.blockSignals(False)

      if 'image_quality_right' in val:
        if self._val['image_quality_right'] != val['image_quality_right']:
          self._val['image_quality_right'] = val['image_quality_right']
          self.iqr.blockSignals(True)
          self.iqr.set_index(val['image_quality_right'])
          self.iqr.blockSignals(False)

    # getters
    def get_val(self):
      return self._val

    # support
    def iqlChange(self, val):
      self._val['image_quality_left'] = val
      self.valueChanged.emit()

    def iqrChange(self, val):
      self._val['image_quality_right'] = val
      self.valueChanged.emit()



def toggle_compare(x):
  if x == 0:
    return 5
  elif x == 1:
    return 4
  elif x== 2:
    return 2
  elif x == 3:
    return 3
  elif x == 4:
    return 1
  elif x == 5:
    return 0
  else:
    return -1

class ExternalNode(gpi.NodeAPI):
    """ Module to compare images in a blinded and randomized manner.
        Input Ports:
        Input_List port requires a list of numpy arrays.
           Each numpy array should have the following dimensions:
              [different reconstructions to be compared (2 or 3); number of slices; x resolution; y resolution]
           To combine different numpy arrays to a list copy the following code into a custom module:
              in1 = self.getData('in1')
              in2 = self.getData('in2')
              # if in1 is a list, append in2 to the list, if in1 is not a list, combine them to a list
              if type(in1) is list:
                in1.append(in2)
                out = in1
              else:
                out = [in1, in2]
              self.setData_ofPort('out1', out)
        previous_analysis_array port is an optional port to load a previously stored analysis array (numpy array)
           to continue the interrupted work.

        Widgets:
        image comparison: select whether the image above the button is much better, better, or the same as the other image.
           Use much better for obviously better images.
           Use better if you require the Toggle button to detect small differences.
           Use same if the quality is the same even after using the Toggle button.
           If image quality rating is disabled, then the next slice will be displaced after pressing a button.
        image quality: select the image quality of the image above as either excellent, good, diagnostic, or non-diagnostic.
           This widget may not be visible in case the "Enable image quality rating" button is set to "Off".
        Toggle: Toggle button to switch the image on the left with the image on the right.
        current slice: Shows how many slices have been analyzed so far.
        out of slices: Shows the number of slices to analyze.
        Undo button: Press this button to undo the last selection made.
        Enable image quality rating: The image quality rating widget is only visible if this button is set to On.
           This button is only visible if the current slice is 0 (zero).

        Output Ports:
        image_for_display port is a 2-dimensional numpy array that should be connected to an ImageDisplay module.
        analysis_array: The numpy array with the results of the analsys.
           Use SaveNPY to store the results. Make sure to store every so often as a backup of your work.
              You can load the stored backup by using LoadNPY and connecting to previous_analysis_array input port.
           Data are stored as follows:
              [nr_slices, 4/7]
              per slice up to 4/7 (number of reconstructions 2/3)4/7 (number of reconstructions 2/3)4/7 (number of reconstructions 2/3)4/7 (number of reconstructions 2/3) values are stored.
              0: comparison reconstruction 0 and 1:
                 0: reconstruction 0 is much better than reconstruction 1
                 1: reconstruction 0 is better than reconstruction 1
                 3: reconstruction 0 is the same as reconstruction 1
                 4: reconstruction 1 is better than reconstruction 0
                 5: reconstruction 1 is much better than reconstruction 0
              1: image quality of reconstruction 0 determined when comparing with reconstruction 1
                 1: excellent
                 2: good
                 3: diagnostic
                 4: non-diagnostic
              2: image quality of reconstruction 1 determined when comparing with reconstruction 0
                 1: excellent
                 2: good
                 3: diagnostic
                 4: non-diagnostic
              n.a./3: comparison reconstruction 0 and 2:
                 0: reconstruction 0 is much better than reconstruction 2
                 1: reconstruction 0 is better than reconstruction 2
                 3: reconstruction 0 is the same as reconstruction 2
                 4: reconstruction 2 is better than reconstruction 0
                 5: reconstruction 2 is much better than reconstruction 0
              n.a./4: image quality of reconstruction 0 determined when comparing with reconstruction 2
                 1: excellent
                 2: good
                 3: diagnostic
                 4: non-diagnostic
              n.a./5: image quality of reconstruction 2 determined when comparing with reconstruction 0
                 1: excellent
                 2: good
                 3: diagnostic
                 4: non-diagnostic
              3/6 (last): patient number
    """

    def initUI(self):
        # Widgets
        self.addWidget('ExclusivePushButtons', 'image comparison',
                       buttons=['much better', 'better', 'choose..', 'same', 'better', 'much better'],
                       val=2)
        self.addWidget('ComboBox_GROUP', 'image quality', visible=False)
        self.addWidget('PushButton', 'Toggle', button_title='Toggle', toggle=True)
        self.addWidget('TextBox', 'current slice', val='0')
        self.addWidget('TextBox', 'out of slices', val='n.a.')
        self.addWidget('PushButton', 'undo button', button_title='Undo', toggle=False)
        self.addWidget('PushButton', 'Enable image quality rating', button_title='Off', toggle=True)
        self.addWidget('PushButton', 'Enable RMS Normalization', button_title='RMS Normalize', toggle=True)#YCC

        # global variable
        self.nr_recons = 0


        # IO Ports
        self.addInPort('Input_List', 'LIST', obligation=gpi.REQUIRED)
        self.addInPort('previous_analysis_array', 'NPYarray', obligation=gpi.OPTIONAL)

        self.addOutPort('image_for_display', 'NPYarray', ndim=2)
        self.addOutPort('analysis_array', 'NPYarray')

    def validate(self):
        '''This function runs before compute() as a GPI_APPLOOP exec-type.
        Here, widgets (bounds, limits, etc...) can be modified to ensure they
        are correctly validated before the widget values are used in the
        compute() routine -where widgets are buffered and any modifications are
        applied after compute() runs.
        '''
        self.starttime()  # time your code, NODE level log
        import numpy as np
        import random as random

        # examples of node and warn logger levels.
        self.log.node("Running validation()")
        #self.log.warn("this is a bad code area")

        # the path to the gpi.py main script
        #self.log.node("gpi.py path:"+gpi.defines.GPI_CWD)

        # enable image quality widget
        # disable widget if current slice is larger than 0
        if type(self.getData('Input_List')) != type(None):
          if int(self.getVal('current slice')) > 0:
            self.setAttr('Enable image quality rating', visible=False)
          else:
            self.setAttr('Enable image quality rating', visible=True)
        # Depending on 'Enable image quality rating' widget set image quality widget visible or not.
        if self.widgetEvent() == 'Enable image quality rating':
          if self.getVal('Enable image quality rating'):
            self.setAttr('Enable image quality rating', button_title='On')
            self.setAttr('image quality', visible=True)
          else:
            self.setAttr('Enable image quality rating', button_title='Off')
            self.setAttr('image quality', visible=False)
        enable_iq = self.getVal('Enable image quality rating')

        # check for misc event types, these can also be used in compute
        if self.portEvent() == 'Input_List':
          # GETTING PORT INFO
          data = self.getData('Input_List')

          status = 0

          # check whether a patient dataset is loaded
          nr_patients = len(data)
          if nr_patients < 1:
            status = 1
            return status

          # how many recon per dataset? self.nr_recons. Allow 2 and 3 only for now.
          if status == 0:
            self.nr_recons = (np.shape(data[0]))[0]
            if self.nr_recons < 2 and self.nr_recons > 3:
              self.log.warn("Currently only 2 or 3 different recons to be compared are allowed.")
              status = 1
              return status

          # check if all datasets have self.nr_recons recon types
          if status == 0:
            for patient in range(nr_patients):
              self.log.node(np.shape(data[patient]))
              if (np.shape(data[patient]))[0] != self.nr_recons:
                status = 1
                return status

          # count all the slices
          nr_slices = 0
          if status == 0:
            for patient in range(nr_patients):
              nr_slices += (np.shape(data[patient]))[1]
              self.log.node(" nr_slices = "+str(nr_slices))
              if nr_slices==0:
                status = 1
                return status

          # multiply by 2 if self.nr_recons = 3 since we will compare the first data set with both the second and the third
          nr_slices_in_analysis_array = nr_slices
          if self.nr_recons == 3:
            nr_slices *=2
          self.log.node(" nr_slices = "+str(nr_slices))
          self.setAttr('out of slices', val=str(nr_slices))
          self.setAttr('current slice', val='0')

          # set an empty array to analysis_array OutPort
          # size of second dimension is 4 for 2 reconstructions and 7 for 3 reconstructions
          analysis_dim = ( (self.nr_recons-1) * 3 ) + 1
          analysis_array = np.zeros((nr_slices_in_analysis_array+1, analysis_dim))
          # current slice
          analysis_array[-1,0] = 0
          self.setData('analysis_array', analysis_array)

        # for any new InPort event and both InPorts are connected, first check if previous_analysis_array dimensions agree with Input_List
        #    and then assign the previous_analysis_array to the OutPort analysis_array if that has no value yet.
        if self.portEvent() == 'Input_List' or self.portEvent() == 'previous_analysis_array':
          self.log.node('Either Input_List or previous_analysis_array port event.')
          if type(self.getData('Input_List')) != type(None) and type(self.getData('previous_analysis_array')) != type(None):
            self.log.node('Both Input_List and previous_analysis_array ports are connected.')
            previous_analysis_array = self.getData('previous_analysis_array')
            nr_slices = int(self.getVal('out of slices'))
            if self.nr_recons == 3:
              nr_slices /= 2
            if nr_slices + 1 == (np.shape(previous_analysis_array))[0]:
              self.log.node('Both Input_List and previous_analysis_array ports have same number of slices.')
              analysis_array_does_not_exist_yet = True
              if type(self.getData('analysis_array')) != type(None):
                analysis_array = self.getData('analysis_array')
                if analysis_array[-1,0]>1:
                  analysis_array_does_not_exist_yet = False
                  self.log.warn('The previous analysis array was not loaded as there is existing data in the analysis array. Start with a fresh module to continue with old work.')
                  status = 1
                  return status
              if analysis_array_does_not_exist_yet:
                analysis_array = previous_analysis_array
                self.setData('analysis_array', analysis_array)
                self.log.node("previous_analysis_array asigned to analysis array!")
                self.setAttr('current slice', val=str(int(analysis_array[nr_slices,0])))
            else:
              self.log.node('Input_List and previous_analysis_array ports do NOT have same number of slices.')
              status = 1
              return status

        # If Toggle is pressed, mirror the 3 selection widgets. The display will be swapped in compute.
        if self.widgetEvent() == 'Toggle' and type(self.getData('Input_List')) != type(None):
          # image comparison
          self.setAttr('image comparison', val=toggle_compare(self.getVal('image comparison')) )
          # image quality
          if enable_iq:
            image_quality_left_widget_value = (self.getVal('image quality'))['image_quality_left']
            image_quality_right_widget_value = (self.getVal('image quality'))['image_quality_right']
            self.setAttr('image quality', val={'image_quality_left':image_quality_right_widget_value})
            self.setAttr('image quality', val={'image_quality_right':image_quality_left_widget_value})

        if self.widgetEvent() == 'undo button' and type(self.getData('Input_List')) != type(None):
          # GETTING WIDGET INFO
          nr_slices = int(self.getVal('out of slices'))
          current_slice = int(self.getVal('current slice'))

          # remove values in analysis_array of current slice to be undone, and then reduce current slice by one
          # only if current slice is larger than 0
          if current_slice > 0:
            if current_slice == nr_slices:
              self.setAttr('image comparison', visible=True)
              if enable_iq:
                self.setAttr('image quality', visible=True)

            current_slice -= 1

            # randomize the order how the slices will be presented, use a defined seed point to make the order reproducible.
            random.seed(0)
            slice_order = list(range(nr_slices))
            random.shuffle(slice_order)

            analysis_array = self.getData('analysis_array').copy()
            if self.nr_recons == 3 and slice_order[current_slice] >= nr_slices/2:
              actual_slice = slice_order[current_slice] - (nr_slices/2)
              compare_idx = 3
              iq_left = 4
              iq_right = 5
            else:
              actual_slice = slice_order[current_slice]
              compare_idx = 0
              iq_left = 1
              iq_right = 2

            analysis_array[actual_slice,compare_idx] = 0
            analysis_array[actual_slice,iq_left] = 0
            analysis_array[actual_slice,iq_right] = 0
            self.setAttr('current slice', val=str(current_slice))
            analysis_array[-1, 0] = current_slice
            self.setData('analysis_array', analysis_array)

          # reset the 3 widgets
          self.setAttr('image comparison', val=2)
          if enable_iq:
            self.setAttr('image quality', val={'image_quality_left':0})
            self.setAttr('image quality', val={'image_quality_right':0})


        #print self.getEvent() # super set of events
        #print self.portEvent()
        #print self.widgetEvent()

        self.endtime('validate()')  # endtime w/ message
        self.endtime()  # endtime w/o message

        return 0

    def compute(self):
        '''This is where the main algorithm should be implemented.
        '''
        import numpy as np
        import random as random

        self.log.node("Running compute()")

        # GETTING PORT INFO
        data = self.getData('Input_List')

        # GETTING WIDGET INFO
        nr_slices = int(self.getVal('out of slices'))
        current_slice = int(self.getVal('current slice'))
        toggle = self.getVal('Toggle')
        enable_iq = self.getVal('Enable image quality rating')

        nr_patients = len(data)
        self.log.node("current slice is " + str(current_slice) + " out of " + str(nr_slices) + " slices")

        # randomize the order how the slices will be presented, use a defined seed point to make the order reproducible.
        random.seed(0)
        slice_order = list(range(nr_slices))
        random.shuffle(slice_order)

        # once all 3 options have been selected, store results, move to next slice, and reset the 3 widgets
        if self.widgetEvent() == 'image comparison' or self.widgetEvent() == 'image quality':
          self.log.node('image comparison widget value is ' + str(self.getVal('image comparison')))
          if enable_iq:
            image_quality_left_widget_value = (self.getVal('image quality'))['image_quality_left']
            self.log.node('image quality left widget value is ' + str(image_quality_left_widget_value))
            image_quality_right_widget_value = (self.getVal('image quality'))['image_quality_right']
            self.log.node('image quality right widget value is ' + str(image_quality_right_widget_value))
          else:
            image_quality_left_widget_value = -1
            image_quality_right_widget_value = -1
          if self.getVal('image comparison') != 2 and image_quality_left_widget_value != 0 and image_quality_right_widget_value != 0:
            analysis_array = self.getData('analysis_array').copy()
            # enter the patient number in the last entry only when the first slice is being analyzed
            if current_slice == 0:
              temp_slice = 0
              for patient in range(nr_patients):
                nr_slices_per_current_patient = (np.shape(data[patient]))[1]
                for temp_patient_slice in range(nr_slices_per_current_patient):
                  analysis_array[temp_slice,-1] = patient
                  temp_slice += 1

            # use random generator to determine if first image is shown left or right
            random.seed(current_slice)
            left = random.randint(0,1)
            if self.nr_recons == 3 and slice_order[current_slice] >= nr_slices/2:
              actual_slice = slice_order[current_slice] - (nr_slices/2)
              self.log.node('actual slice is: ' + str(actual_slice))
              compare_idx = 3
              if ( left == 1 ) == toggle:
                compare_value = self.getVal('image comparison')
                iq_left = 4
                iq_right = 5
              else:
                compare_value = toggle_compare(self.getVal('image comparison') )
                iq_left = 5
                iq_right = 4
            else:
              actual_slice = slice_order[current_slice]
              self.log.node('actual slice is: ' + str(actual_slice))
              compare_idx = 0
              if ( left == 1 ) == toggle:
                compare_value = self.getVal('image comparison')
                iq_left = 1
                iq_right = 2
              else:
                compare_value = toggle_compare(self.getVal('image comparison') )
                iq_left = 2
                iq_right = 1

            analysis_array[actual_slice,compare_idx] = compare_value
            if enable_iq:
              analysis_array[actual_slice,iq_left] = image_quality_left_widget_value
              analysis_array[actual_slice,iq_right] = image_quality_right_widget_value
            current_slice += 1
            self.setAttr('current slice', val=str(current_slice))
            analysis_array[-1, 0] = current_slice
            self.setData('analysis_array', analysis_array)
            self.setAttr('image comparison', val=2)
            if enable_iq:
              self.setAttr('image quality', val={'image_quality_left':0})
              self.setAttr('image quality', val={'image_quality_right':0})

        # disable widgets once last slice has been analyzed
        if current_slice >= nr_slices:
          self.setAttr('image comparison', visible=False)
          if enable_iq:
            self.setAttr('image quality', visible=False)
          current_image = np.zeros((2,2))
        else:

          # translate slice order to patient number and slice number of that patient
          slice_counter = 0
          current_recon_comparison = -1
          keep_going = True
          for patient in range(nr_patients):
            if slice_order[current_slice] < slice_counter + (np.shape(data[patient]))[1] and keep_going:
              current_patient = patient
              slice_of_current_patient = slice_order[current_slice] - slice_counter
              current_recon_comparison = 0
              keep_going = False
            slice_counter += (np.shape(data[patient]))[1]
          # run a second time for the comparison between data set one and three. Refer to this comparison as current_recon_comparison = 1
          for patient in range(nr_patients):
            if slice_order[current_slice] < slice_counter + (np.shape(data[patient]))[1] and keep_going:
              current_patient = patient
              slice_of_current_patient = slice_order[current_slice] - slice_counter
              current_recon_comparison = 1
              keep_going = False
            slice_counter += (np.shape(data[patient]))[1]

          # use random generator to determine if first image is shown left or right
          random.seed(current_slice)
          left = random.randint(0,1)

          if current_recon_comparison == 0:
            if ( left == 1 ) == toggle:
              left_image_nr = 0
              right_image_nr = 1
            else:
              left_image_nr = 1
              right_image_nr = 0
          elif current_recon_comparison == 1:
            if ( left == 1 ) == toggle:
              left_image_nr = 0
              right_image_nr = 2
            else:
              left_image_nr = 2
              right_image_nr = 0
          else:
            self.log.warn("current_recon_comparison has not been set to either 0 or 1.")

          self.log.node("Current random slice " + str(slice_order[current_slice]) + ", patient number " + str(current_patient) + ", slice number " + str(slice_of_current_patient) + ", recon comparison " + str(current_recon_comparison) + ", left image is " + str(left_image_nr))

          # assign current image for display
          current_dataset = data[current_patient]
          left_image = current_dataset[left_image_nr, slice_of_current_patient,:,:]
          right_image = current_dataset[right_image_nr, slice_of_current_patient,:,:]
          if (self.getVal('Enable RMS Normalization') == True): #YCC
              left_image = left_image / np.sqrt(np.mean(np.square(left_image)))
              right_image = right_image / np.sqrt(np.mean(np.square(right_image)))

          current_image = np.append(left_image, right_image, 1)


        # SETTING PORT INFO
        self.setData('image_for_display', current_image)

        return 0

    def execType(self):
        '''Could be GPI_THREAD, GPI_PROCESS, GPI_APPLOOP'''
        return gpi.GPI_PROCESS
