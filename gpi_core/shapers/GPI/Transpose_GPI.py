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
# Date: 2015aug25

import gpi
from gpi import QtWidgets


class GPITabBar(QtWidgets.QTabBar):
    currentChanged = gpi.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._labels_at_press = None

    def clearTabs(self):
        while self.count() > 0:
            self.removeTab(0)

    def addTabsFromList(self, names):
        for i in range(len(names)):
            self.addTab(str(names[i]))

    def labels(self):
        return [str(self.tabText(i)) for i in range(self.count())]

    def mousePressEvent(self, event):
        self._labels_at_press = self.labels()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if self.labels() != self._labels_at_press:
            self.currentChanged.emit()

class OrderButtons(gpi.GenericWidgetGroup):
    """A set of reorderable tabs."""
    valueChanged = gpi.Signal()

    def __init__(self, title, parent=None):
        super().__init__(title, parent)

        # at least one button
        wdgLayout = QtWidgets.QGridLayout()
        self.wdg = GPITabBar()
        self.wdg.addTab('0')
        self.wdg.setMovable(True)
        self.wdg.currentChanged.connect(self.valueChanged.emit)
        # layout
        wdgLayout.addWidget(self.wdg)
        self.setLayout(wdgLayout)

    # setters
    def set_val(self, names):
        """list(str,str,...) | A list of labels (e.g. ['b1', 'b2',...])."""
        self.wdg.clearTabs()
        self.wdg.addTabsFromList(names)

    # getters
    def get_val(self):
        return self.wdg.labels()


class ExternalNode(gpi.NodeAPI):
    """Peform transpose operations on an array.
    INPUT - input array
    OUTPUT - output array

    WIDGETS:
    Info: - information on size, etc of input and output array
    Transpose - transpose any dimensions
    """

    def initUI(self):

        # Widgets
        self.addWidget('TextBox', 'Info:')
        self.addWidget('PushButton', 'Transpose', toggle=True, val=1)
        self.addWidget('OrderButtons', 'Dimension Order')

        # IO Ports
        self.addInPort('in', 'NPYarray', obligation=gpi.REQUIRED)
        self.addOutPort('out', 'NPYarray')

    def validate(self):
        data = self.getData('in')
        order = self.getVal('Dimension Order')

        # the widget doesn't have the same dims as the data then reset the
        # widget with the new length
        if len(order) != data.ndim:
            self.setAttr('Dimension Order', quietval=[str(i) for i in range(data.ndim)])

        # automatically transpose if ndim = 2
        if data.ndim < 3:
            self.setAttr('Dimension Order', visible=False)
        else:
            self.setAttr('Dimension Order', visible=True)

        return 0

    def compute(self):

        data = self.getData('in')
        transpose = self.getVal('Transpose')
        order = self.getVal('Dimension Order')

        # display info
        basic_info = "Input Dimensions: "+str(data.shape)+"\n"

        # setup the transpose indices (automatically transpose if ndim = 2)
        trans_ind = data.ndim*[0]
        if data.ndim > 2:
            for i in range(len(order)):
                trans_ind[i] = int(order[i])
        else:
            trans_ind = [1, 0]

        # compute
        if transpose and data.ndim > 1:
            out = data.transpose(trans_ind)
        else:
            out = data

        # updata info
        info = basic_info+"Output Dimensions: "+str(out.shape)+"\n"
        self.setAttr('Info:', val = info)
        self.setData('out', out)

        return 0
