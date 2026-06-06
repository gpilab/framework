# Author: Ryan Robison
# Date: 2018 Sept 14

import os
import time
import gpi
from gpi import QtWidgets, QtGui, QtCore
import numpy as np

# WIDGETS
class TextBoxes(gpi.GenericWidgetGroup):
    """A set of non-editable text boxes"""
    valueChanged = gpi.Signal()

    def __init__(self, title, parent=None):
        super(TextBoxes, self).__init__(title, parent)

        # at least one text box
        self.boxes = []
        self.boxes.append(QtWidgets.QLabel())
        self.vbox = QtWidgets.QVBoxLayout()
        self.vbox.setSpacing(0)
        for box in self.boxes:
            self.vbox.addWidget(box)
        self.setLayout(self.vbox)

    # setters
    def set_strings(self, strlist):
        """str | Set the string (str)."""
        ind = 0
        if len(strlist) < len(self.boxes):
            strlendiff = len(self.boxes) - len(strlist)
            strlist.extend(strlendiff*[''])
            self.log.warn("TextBoxes: list of strings shorter than number of "\
                "boxes. Filling rest with empty strings.")

        if len(strlist) > len(self.boxes):
            self.log.warn("TextBoxes: list of strings longer than number of "\
                "boxes. Only using first portion of strings.")

        for box in self.boxes:
            string = strlist[ind]
            box.setText(string)
            ind = ind+1

    def set_length(self, length):
        # add specified number of text boxes
        while length > len(self.boxes):
            newbox = QtWidgets.QLabel()
            self.boxes.append(newbox)
            self.vbox.addWidget(newbox)
        while length < len(self.boxes):
            oldbox = self.boxes.pop()
            oldbox.setParent(None)

        if length != len(self.boxes):
            log.critical("StringBoxes: length not properly set!")


class StringBoxes(gpi.GenericWidgetGroup):
    """A set of editable string boxes"""
    valueChanged = gpi.Signal()

    def __init__(self, title, parent=None):
        super(StringBoxes, self).__init__(title, parent)

        # at least one string box
        self.boxes = []
        self.boxes.append(QtWidgets.QLineEdit())
        self.vbox = QtWidgets.QVBoxLayout()
        self.vbox.setSpacing(0)
        for box in self.boxes:
            self.vbox.addWidget(box)
            box.returnPressed.connect(self.valueChanged)
        self.setLayout(self.vbox)

    # setters
    def set_strings(self, strlist):
        """str | Set the string (str)."""
        ind = 0
        if len(strlist) < len(self.boxes):
            strlendiff = len(self.boxes) - len(strlist)
            strlist.extend(strlendiff*[''])
            log.warn("StringBoxes: list of strings shorter than number of \
                boxes. Filling rest with empty strings.")

        if len(strlist) > len(self.boxes):
            log.warn("StringBoxes: list of strings longer than number of \
                boxes. Only using first portion of strings.")

        for box in self.boxes:
            string = strlist[ind]
            box.setText(string)
            ind = ind+1

    def set_length(self, length):
        # add specified number of string boxes
        while length > len(self.boxes):
            newbox = QtWidgets.QLineEdit()
            self.boxes.append(newbox)
            newbox.returnPressed.connect(self.valueChanged)
            self.vbox.addWidget(newbox)
        while length < len(self.boxes):
            oldbox = self.boxes.pop()
            oldbox.setParent(None)

        if length != len(self.boxes):
            log.critical("StringBoxes: length not properly set!")

    def get_strings(self):
        strings = []
        for box in self.boxes:
            strings.append(box.text())
        return strings


class DICOM_HDR_GROUP(gpi.GenericWidgetGroup):
    """A combination of Textboxes and StringBoxes to allow for easy display of
    DICOM header info and editing of the values"""
    valueChanged = gpi.Signal()

    def __init__(self, title, parent=None):
        super(DICOM_HDR_GROUP, self).__init__(title, parent)
        self._val = {}
        self._val['tags'] = ''
        self._val['desc'] = ''
        self._val['VRs'] = ''
        self._val['values'] = ''

        self.tb1 = TextBoxes('Tags:')
        self.tb1.set_length(1)
        self.tb2 = TextBoxes('Descriptions:')
        self.tb2.set_length(1)
        self.tb3 = TextBoxes('VRs:')
        self.tb3.set_length(1)

        self.sb = StringBoxes('Values:')
        self.sb.set_length(1)
        self.sb.valueChanged.connect(self.valueChanged)

        vbox = QtWidgets.QHBoxLayout()
        vbox.addWidget(self.tb1)
        vbox.addWidget(self.tb2)
        vbox.addWidget(self.tb3)
        vbox.addWidget(self.sb)
        vbox.setStretch(0, 0)
        vbox.setStretch(1, 0)
        vbox.setStretch(2, 0)
        vbox.setStretch(3, 0)
        vbox.setContentsMargins(0, 0, 0, 0)  # we don't need margins here
        vbox.setSpacing(0)
        self.setLayout(vbox)

    # setters
    def set_info(self, val):
        """A python-dict containing: tags, desc, and VRs parms. """
        if 'tags' in val:
            self._val['tags'] = val['tags']
            self.setTagsQuietly(val['tags'])
        if 'desc' in val:
            self._val['desc'] = val['desc']
            self.setDescriptionsQuietly(val['desc'])
        if 'VRs' in val:
            self._val['VRs'] = val['VRs']
            self.setVRsQuietly(val['VRs'])
        if 'values' in val:
            self._val['values'] = val['values']
            self.setValuesQuietly(val['values'])

    def set_length(self, length):
        self.tb1.set_length(length)
        self.tb2.set_length(length)
        self.tb3.set_length(length)
        self.sb.set_length(length)

    # getters
    def get_val(self):
        return self.sb.get_strings()

    # support
    def setTagsQuietly(self, val):
        self.tb1.blockSignals(True)
        self.tb1.set_strings(val)
        self.tb1.blockSignals(False)

    def setDescriptionsQuietly(self, val):
        self.tb2.blockSignals(True)
        self.tb2.set_strings(val)
        self.tb2.blockSignals(False)

    def setVRsQuietly(self, val):
        self.tb3.blockSignals(True)
        self.tb3.set_strings(val)
        self.tb3.blockSignals(False)

    def setValuesQuietly(self, val):
        self.sb.blockSignals(True)
        self.sb.set_strings(val)
        self.sb.blockSignals(False)


class ExternalNode(gpi.NodeAPI):
    """This node takes in a dictionary of DICOM hdr info from ReadDICOM,
    displays the values for the selected image, and optionally allows for
    editing the header values. An edited DICOM header can be passed as an
    input to WriteDICOM.

    INPUT: GPI DICOM dictionary
    OUTPUT: Modified DICOM dictionary

    WIDGETS:
    Display By - choose whether to display all hdr information for one image or
    a single tag across all images
    Select Image - select image for which the header will be displayed
    Select Tag - select which Tag to display for all images
    Propogate Change to All Images - choose whether to propogate changes to
        DICOM header values to all image headers in the GPI DICOM dictionary.
    Dicom Header - header information for one image (or all images, one tag).
        The header contains the following information for each entry:
        1) Tag - the unique tag for each header entry, hexidecimal in format,
                 comprised of a DICOM group number and DICOM element number.
        2) Description - A short description of each entry
        3) VR - The DICOM value representation describing the format and type
                of each entry.
        4) Value - the current value of the entry. This is the only field that
                   is editable using DICOMheader.
    """

    def execType(self):
        # default executable type
        # return gpi.GPI_THREAD
        return gpi.GPI_PROCESS # this is the safest
        # return gpi.GPI_APPLOOP

    def initUI(self):

        # Widgets
        self.addWidget('ExclusivePushButtons', 'Display By', buttons=['Image','Tag'],val=0)
        self.addWidget('ComboBox', 'Select Image', items=[])
        self.addWidget('ComboBox', 'Select Tag', items=[])
        self.addWidget('PushButton', 'Reset', toggle=False)
        self.addWidget('PushButton', 'Propogate Change to All Images', toggle=False)
        self.addWidget('DICOM_HDR_GROUP', 'Dicom Header')

        # IO Ports
        self.addInPort(title='Dicom Dict In', type='DICT')
        self.addOutPort(title='Dicom Dict Out', type='DICT')

    def validate(self):
        import gpi_core.fileIO.dicomlib as dcm
        import imp
        imp.reload(dcm)

        if (('Display By' in self.widgetEvents()) or
            ('Dicom Dict In' in self.portEvents())):
            hdr = self.getData('Dicom Dict In')
            displayBy = self.getVal('Display By')
            if displayBy == 0:
                keys = list(hdr.keys())
                numvals = len(list(hdr[keys[0]].keys()))
                self.setAttr('Select Image', items=keys, visible=True)
                self.setAttr('Select Tag', visible=False)
                # self.setAttr('Images:', visible=False)
                # self.setAttr('Tags:', visible=True)
            else:
                keys = list(hdr[list(hdr.keys())[0]].keys())
                numvals = len(hdr.keys())
                self.setAttr('Select Image', visible=False)
                self.setAttr('Select Tag', items=keys, visible=True)
                # self.setAttr('Images:', visible=True)
                # self.setAttr('Tags:', visible=False)
            self.setAttr('Dicom Header', length = numvals)


    def compute(self):

        import numpy as np
        import re
        import gpi_core.fileIO.dicomlib as dcm

        hdr = self.getData('Dicom Dict In')
        displayBy = self.getVal('Display By')
        reset = self.getVal('Reset')
        propogate = self.getVal('Propogate Change to All Images')

        if ((reset) or ('Dicom Dict In' in self.portEvents())):
            dicomDict = hdr
        else:
            dicomDict = self.getData('Dicom Dict Out')
            if (dicomDict == None):
                dicomDict = hdr

        if ((reset) or ('Dicom Dict In' in self.portEvents()) or
            ('Display By' in self.widgetEvents()) or
            ('Select Image' in self.widgetEvents()) or
            ('Select Tag' in self.widgetEvents())):
            if displayBy == 0:
                tags = []
                descs = []
                VRs = []
                values = []
                img = self.getVal('Select Image')
                info = dicomDict[img]
                for key in info.keys():
                    desc = info[key][0]
                    VR = info[key][1]
                    val = info[key][2]
                    tags.append(str(key))
                    descs.append(desc)
                    VRs.append(VR)
                    if VR != 'SQ':
                        values.append(val)
                    else:
                        values.append(str(val))
                    # if VR == 'SQ':
                    #     for item in val:
                    #         for key1 in item.keys():
                    #             desc1 = item[key1][0]
                    #             VR1 = item[key1][1]
                    #             val1 = item[key1][2]
                    #             tags.append('  '+str(key1))
                    #             descs.append(desc1)
                    #             VRs.append(VR1)
                    #             values.append(val1)
                val = {'tags': tags, 'desc': descs, 'VRs': VRs, 'values': values}
                self.setAttr('Dicom Header', info=val)

            else:
                imgs = []
                descs = []
                VRs = []
                values = []
                tag = self.getVal('Select Tag')
                for key in dicomDict.keys():
                    desc = dicomDict[key][tag][0]
                    VR = dicomDict[key][tag][1]
                    val = dicomDict[key][tag][2]
                    imgs.append(str(key))
                    descs.append(desc)
                    VRs.append(VR)
                    values.append(val)
                val = {'tags': imgs, 'desc': descs, 'VRs': VRs, 'values': values}
                self.setAttr('Dicom Header', info=val)

        if ('Dicom Header' in self.widgetEvents()):
            newInfo = self.getVal('Dicom Header')
            index = 0
            if displayBy == 0:
                img = self.getVal('Select Image')
                info = hdr[img]
                for key in info.keys():
                    val = info[key][2]
                    newval = newInfo[index]
                    info[key][2] = newval
                    index = index + 1
                dicomDict[img] = info
            else:
                tag = self.getVal('Select Tag')
                for key in hdr.keys():
                    val = hdr[key][tag][2]
                    newval = newInfo[index]
                    dicomDict[key][tag][2] = newval
                    index = index + 1

        if ('Propogate Change to All Images' in self.widgetEvents()):
            if displayBy == 0:
                curimg = self.getVal('Select Image')
                for tag in hdr[curimg].keys():
                    oldval = hdr[curimg][tag][2]
                    newval = dicomDict[curimg][tag][2]
                    if (oldval != newval):
                        for img in hdr.keys():
                            dicomDict[img][tag][2] = newval
            else:
                tag = self.getVal('Select Tag')
                for img in hdr.keys():  # find the first changed value
                    oldval = hdr[img][tag][2]
                    curval = dicomDict[img][tag][2]
                    if (oldval != curval):
                        # update all entries in the header table
                        values = len(hdr.keys())*[curval]
                        val = {'values':values}
                        self.setAttr('Dicom Header', info=val)
                        break
                # now update the dicom header dictionary
                newval = self.getVal('Dicom Header')[0]
                for img in hdr.keys():
                    dicomDict[img][tag][2] = newval

        self.setData('Dicom Dict Out', dicomDict)

        return(0)
