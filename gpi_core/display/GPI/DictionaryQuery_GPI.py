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


# Author: Jim Pype
# Date: 2013 July
# Brief: Quick readout of dictionary data types

import gpi
import numpy as np
import re
from collections.abc import Mapping
from gpi import QtWidgets
np.set_printoptions(linewidth=256)


# flatten a nested dictionary
def unwrap_dict(din, dout, prefix=''):
    if not isinstance(din, Mapping):
        return dout
    for key, value in din.items():
        path = '{}.{}'.format(prefix, key) if prefix else str(key)
        if isinstance(value, Mapping):
            dout[path] = value
            unwrap_dict(value, dout, path)
        else:
            dout[path] = value
    return dout


# add dictionary item to text output and handle slicing of lists and np arrays
def print_item(item, report, minl, maxl):
    if isinstance(item[1], (list, tuple, np.ndarray)):
        report = report + str(item[0]) + ' = ' + str(item[1][minl:maxl]) + "\n"
    else:
        report = report + str(item[0]) + ' = ' + str(item[1]) + "\n"

    return report


def gen_keys_from_keywords(keys, indict, exactmatch):
    # add regex search results
    if keys != '':
        dflat = dict()
        dflat = unwrap_dict(indict, dflat)
        matching_keys = []
        keys = [key.strip() for key in re.split(r'\s*,\s*', str(keys)) if key.strip()]
        if exactmatch:
            for key in dflat:
                if key in keys:
                    matching_keys.append(key)
        else:
            for pattern in keys:
                try:
                    cpat = re.compile(pattern, re.IGNORECASE)
                except re.error:
                    continue
                for key in dflat:
                    if cpat.search(str(key)):
                        matching_keys.append(key)
    else:
        matching_keys = []

    return(matching_keys)


class ReduceSliders(gpi.GenericWidgetGroup):
    """Combines the BasicCWFCSliders with ExclusivePushButtons
    for a unique widget element useful for reduce dimensions.
    """
    valueChanged = gpi.Signal()

    def __init__(self, title, parent=None):
        super().__init__(title, parent)
        self.sl = gpi.BasicCWFCSliders()
        self.sl.valueChanged.connect(self.valueChanged)
        # at least one button
        self.button_names = ['C/W', 'B/E', 'Slice', 'Pass']
        self.buttons = []
        cnt = 0
        wdgLayout = QtWidgets.QGridLayout()
        for name in self.button_names:
            newbutton = QtWidgets.QPushButton(name)
            newbutton.setCheckable(True)
            newbutton.setAutoExclusive(True)
            self.buttons.append(newbutton)
            newbutton.clicked.connect(self.findValue)
            newbutton.clicked.connect(self.valueChanged)
            wdgLayout.addWidget(newbutton, 0, cnt, 1, 1)
            cnt += 1
        # layout
        wdgLayout.addWidget(self.sl, 1, 0, 1, 4)
        wdgLayout.setVerticalSpacing(0)
        wdgLayout.setSpacing(0)
        self.setLayout(wdgLayout)
        # default
        self.set_min(1)
        self._selection = 3  # pass is default
        self.buttons[self._selection].setChecked(True)
        self.sl.set_allvisible(False)

    # setters
    def set_val(self, val):
        """A python-dict containing keys: center, width, floor, ceiling,
        and selection.
        """
        self.sl.set_center(val['center'])
        self.sl.set_width(val['width'])
        self.sl.set_floor(val['floor'])
        self.sl.set_ceiling(val['ceiling'])
        self._selection = val['selection']
        self.buttons[self._selection].blockSignals(True)
        self.buttons[self._selection].setChecked(True)
        self.buttons[self._selection].blockSignals(False)
        self.findValue(None)

    def set_min(self, val):
        """A min value for center, width, floor and ceiling (int)."""
        self.sl.set_min(val)

    def set_max(self, val):
        """A max value for center, width, floor and ceiling (int)."""
        self.sl.set_max(val)

    # getters
    def get_val(self):
        val = {}
        val['selection'] = self._selection
        val['center'] = self.sl.get_center()
        val['width'] = self.sl.get_width()
        val['floor'] = self.sl.get_floor()
        val['ceiling'] = self.sl.get_ceiling()
        return val

    def get_min(self):
        return self.sl.get_min()

    def get_max(self):
        return self.sl.get_max()
    # support

    def setCropBounds(self):
        self.sl.set_min_width(1)

    def setSliceBounds(self):
        self.sl.set_min_width(0)
        self.sl.set_width(1)

    def setPassBounds(self):
        self.sl.set_min_width(1)
        self.sl.set_width(self.get_max())
        # JGP For Pass, reset cwfc
        self.sl.set_center((self.get_max()+1)/2)
        self.sl.set_width(self.get_max())
        self.sl.set_floor(1)
        self.sl.set_ceiling(self.get_max())

    def findValue(self, value):
        cnt = 0
        for button in self.buttons:
            if button.isChecked():
                self._selection = cnt
            cnt += 1
        # hide appropriate sliders
        if self._selection == 0:  # C/W
            self.sl.set_cwvisible(True)
            self.setCropBounds()
        elif self._selection == 1:  # B/E
            self.sl.set_fcvisible(True)
            self.setCropBounds()
        elif self._selection == 2:  # slice
            self.sl.set_slicevisible(True)
            self.setSliceBounds()
        else:  # pass
            self.sl.set_allvisible(False)
            self.setPassBounds()


class ExternalNode(gpi.NodeAPI):
    """Display contents of Dictionary-type data

    INPUT
    Data of type DICT

    WIDGETS
    Keys: comma-delimited list of dictionary elements to display
    Range: allows inspection of a subset of large data arrays
    C/W - sliders control center/width of range
    B/E - sliders control begin/end of range
        Slice - slider gives element to inspect
        Pass - shows all elements
    """

    def execType(self):
        return gpi.GPI_THREAD

    def initUI(self):

        # Widgets
        self.addWidget('StringBox', 'Keys:')
        self.addWidget('PushButton', 'Match Exactly', val=0, toggle=True)
        self.addWidget('ReduceSliders', 'Range')
        self.addWidget('TextBox', 'Info:')

        self.addInPort('dq_in', 'DICT')
        self.addOutPort('matches', 'DICT')

    def validate(self):
        '''update the slider bounds based on dictionary
        '''

        indat = self.getData('dq_in')
        if not isinstance(indat, Mapping):
            self.setData('matches', {})
            self.setAttr('Range', max=1)
            self.setAttr('Info:', val='Connect a dictionary input.')
            return 0
        inkeys = self.getVal('Keys:')
        exactmatch = self.getVal('Match Exactly')
        keys = gen_keys_from_keywords(inkeys, indat, exactmatch)

        w = self.getVal('Range')
        maxlen = 1
        if len(keys) > 0:
            dflat = unwrap_dict(indat, {})
            for key in keys:
                if key in dflat:
                    value = dflat[key]
                    if isinstance(value, Mapping):
                        values = value.values()
                    else:
                        values = [value]
                    for value in values:
                        if isinstance(value, (list, tuple, np.ndarray)):
                            maxlen = max(maxlen, len(value))
        else:
            for item in list(indat.items()):
                if isinstance(item[1], (list, tuple, np.ndarray)):
                    maxlen = max(maxlen, len(item[1]))

        if(maxlen > 30):
            maxlen = 30

        self.setAttr('Range', max=maxlen)
        if w['selection'] == 3:  # pass
            w['center'] = (maxlen+1)/2
            w['width'] = maxlen
            w['floor'] = 1
            w['ceiling'] = maxlen
            self.setAttr('Range', quietval=w)

    def compute(self):

        import re

        indat = self.getData('dq_in')
        if not isinstance(indat, Mapping):
            self.setAttr('Info:', val='Connect a dictionary input.')
            self.setData('matches', {})
            return 0
        inkeys = self.getVal('Keys:')
        exactmatch = self.getVal('Match Exactly')
        keys = gen_keys_from_keywords(inkeys, indat, exactmatch)
        dflat = unwrap_dict(indat, {})
        matches = {key: dflat[key] for key in keys if key in dflat}

        w = self.getVal('Range')
        minl = w['floor']-1
        maxl = w['ceiling']

        # Report Back to User
        report = '\n'
        if w['selection'] in [0, 1]:
            report = report + 'Displaying List Elements: ' + str(minl) + ':'\
                + str(maxl - 1) + '\n\n'
        elif w['selection'] == 2:
            report = report + 'Displaying Element: ' + str(minl) + '\n\n'
        if len(keys) > 0:
            for key in keys:
                if key in dflat:
                    if 'dict' in str(type(dflat[key])).lower():
                        report = report + str(key)+':\n'
                    try:
                        for item in list(sorted(dflat[key].items(), key=lambda value: str(value[0]))):
                            report = print_item(item, report,
                                                minl, maxl)
                    except (AttributeError, TypeError):
                        report = print_item((key, dflat[key]), report, minl,
                                            maxl)
        else:
            for item in list(sorted(indat.items(), key=lambda value: str(value[0]))):
                report = print_item(item, report, minl, maxl)

        self.setAttr('Info:', val=report)
        self.setData('matches', matches)

        return(0)
