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


# Author: Nick Zwart
# Date: 2012dec10

import gpi


class ExternalNode(gpi.NodeAPI):
    """A basic module for tutorial purposes.  This module contains all
    stock widgets and types so that the node-developer can preview and read
    auto-doc information about each object.
    """

    def initUI(self):
        # Widgets
        self.addWidget('NonExclusivePushButtons', 'My NonExclusivePushButtons',
                       buttons=['hello', 'world', '!!!'], val=[0, 2])
        self.addWidget('TextBox', 'Data Statistics', val='hello data')
        self.addWidget('ComboBox', 'My Exclusive Options', items=['hello', 'world', '!!!'], val='world')
        self.addWidget(
            'PushButton', 'MyPushButton', button_title='OFF', toggle=True)
        self.addWidget(wdg='TextBox', title='MyTextBox', val='No Info Yet...')
        self.addWidget(
            'OpenFileBrowser', 'MyOpenFileBrowser', button_title='Browse',
            caption='Open Stuff', directory='~/',
            filter='my format (*.my)')
        self.addWidget('SaveFileBrowser', 'MySaveFileBrowser')
        self.addWidget('TextEdit', 'MyTextEdit', val="initial text...")
        self.addWidget('ExclusiveRadioButtons', 'MyExclusiveRadioButtons',
                       buttons=['Thread', 'Process', 'Main Loop'],
                       val=2)
        self.addWidget('ExclusivePushButtons', 'MyExclusivePushButtons',
                       buttons=['Thread', 'Process', 'Main Loop'],
                       val=2)
        self.addWidget('DisplayBox', 'MyDisplayBox', collapsed=True)
        self.addWidget('StringBox', 'MyStringBox', val="True")
        self.addWidget('DoubleSpinBox', 'MyDoubleSpinBox', immediate=True)
        self.addWidget('DoubleSpinBox', 'MyDoubleSpinBox2')
        self.addWidget('SpinBox', 'MySpinBox', immediate=True)
        self.addWidget('SpinBox', 'MySpinBox2')
        self.addWidget('Slider', 'MySlider')
        self.addWidget('WebBox', 'myBrowser', val='www.google.com')

        # IO Ports
        self.addInPort('MyNPYarray', 'NPYarray', obligation=gpi.OPTIONAL)
        self.addInPort(title='MyINT', type='INT', obligation=gpi.OPTIONAL)
        self.addInPort(title='MyFLOAT', type='FLOAT', obligation=gpi.OPTIONAL)
        self.addInPort(title='MyLONG', type='LONG', obligation=gpi.OPTIONAL)
        self.addInPort(title='MyLIST', type='LIST', obligation=gpi.OPTIONAL)

        self.addOutPort('MyTUPLE', 'TUPLE')
        self.addOutPort('MyCOMPLEX', 'COMPLEX')
        self.addOutPort('MySTRING', 'STRING')
        self.addOutPort('MyDICT', 'DICT')

        # example of warn logger level.
        self.log.warn("something didnt initialize.")

    def validate(self):
        '''This function runs before compute() as a GPI_APPLOOP exec-type.
        Here, widgets (bounds, limits, etc...) can be modified to ensure they
        are correctly validated before the widget values are used in the
        compute() routine -where widgets are buffered and any modifications are
        applied after compute() runs.
        '''
        self.starttime()  # time your code, NODE level log

        # examples of node and warn logger levels.
        self.log.node("hello from node level logger, running validation()")
        self.log.warn("this is a bad code area")

        # the path to the gpi.py main script
        self.log.node("gpi.py path:"+gpi.defines.GPI_CWD)

        print("template validation")
        print("DoubleSpinBox: ", self.getVal('MyDoubleSpinBox'))
        print("DoubleSpinBox: ", self.getVal('MyDoubleSpinBox2'))
        print("SpinBox: ", self.getVal('MySpinBox'))
        print("SpinBox2: ", self.getVal('MySpinBox2'))

        # check for misc event types, these can also be used in compute
        print(self.getEvents()) # super set of events
        print(self.portEvents())
        print(self.widgetEvents())

        # validate widget bounds
        data = self.getData('MyNPYarray')
        if data:
            self.setAttr('MyDoubleSpinBox', max=data.shape[0])

        self.endtime('validate()')  # endtime w/ message
        self.endtime()  # endtime w/o message

        return 0

    def compute(self):
        '''This is where the main algorithm should be implemented.
        '''

        self.log.node("hello from node level logger, running compute()")

        print("template compute")

        # GETTING WIDGET INFO
        val = self.getVal('MyPushButton')
        button_title = self.getAttr('MyPushButton', 'button_title')

        # SETTING WIDGET INFO
        if val:
            self.setAttr('MyPushButton', button_title="ON")
        else:
            self.setAttr('MyPushButton', button_title="OFF")

        self.setAttr('MyTextBox', val="The button title was: "+button_title)

        # GETTING PORT INFO
        data = self.getData('MyNPYarray')

        # SETTING PORT INFO
        self.setData('MyTUPLE', ('hello', 'world', 42))
        self.setData('MyCOMPLEX', 3 + 0.14159j)

        # if setData() isn't called, then no downsteam events will trigger
        # and the port data will remain unchanged.
        if self.getData('MySTRING') is None:
            self.log.node('set string')
            self.setData('MySTRING', '/home/bni/data/propellor/lunchtime/meatloaf')
        else:
            pass

        # if the outport is set to None, then no downstream events will trigger
        out = {'hello':1}
        if not self.getData('MyDICT'):
            self.setData('MyDICT', out)
        else:
            self.setData('MyDICT', None)

        return 0

    def execType(self):
        '''Could be GPI_THREAD, GPI_PROCESS, GPI_APPLOOP'''
        return gpi.GPI_PROCESS
