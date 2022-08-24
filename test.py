import inspect

def foo(arg1,arg2):
    #do something with args
    a = arg1 + arg2
    return a

fake_gpi_data = {'widgets': {'140642384587360': {'Info': '', 'Size': 128, 'Flip': True, 'Compute': True, 'Bandlimit iterations': 0}, '140642383984240': {'Complex Display': 4, 'Color Map': 0, 'Edge Pixels': 0, 'Black Pixels': 0, 'Viewport:': None, 'Slice': 1, 'Slice/Tile Dimension': 0, 'Extra Dimension': 0, '# Columns': 1, '# Rows': 1, 'L W F C:': {'level': 50, 'window': 100, 'floor': 0, 'ceiling': 100}, 'Scalar Display': 0, 'Gamma': 1.0, 'Zero Ref': 0, 'Fix Range': False, 'Range Min': 0.0, 'Range Max': 0.0}, '140642355349680': {'Mode': 0, 'Units': 1, 'Operation': 0, 'Scalar': 0.0, 'compute': True}}, 'data': {'140642384587360': {'out': None}, '140642383984240': {'out': None, 'binary': None}}}

class FakeGPI:
    def addWidget(self, *kwargs):
        pass

    def addOutPort(self, *kwargs):
        pass

    def getVal(self, id, widget=''):
        if not id.isnumeric(): return None
        try:
            return fake_gpi_data['widgets'][id][widget]
        except:
            return None

    def getData(self, id, name=''):
        if not id.isnumeric(): return None
        try:
            return fake_gpi_data['data'][id][name]
        except:
            return None

    def setData(self, id, name='', data=None):
        if not id.isnumeric(): return None
        try:
            fake_gpi_data['data'][id][name] = data
        except:
            return None



class ExternalNode(FakeGPI):
    """Specify a python boolean for use as node-data or widget-ports-parms.
    OUTPUT - boolean value
    WIDGETS:
      bool - specifies whether boolean is True or False
    """

    def initUI(self):
        # Widgets
        self.addWidget('PushButton', 'bool')

        # IO Ports
        self.addOutPort('out', 'PASS')

    def compute(self):
        self.setData('140642383984240', 'out', [1,2,3])
        data1 = self.getData('140642383984240', 'out')
        data2 = self.getData('inRight')
        print(data1)
        print(data2)

        return 0

    def execType(self):
        return gpi.GPI_THREAD


test = ExternalNode()
print(test.initUI())
print(test.compute())

