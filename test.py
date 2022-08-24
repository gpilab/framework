import inspect

def foo(arg1,arg2):
    #do something with args
    a = arg1 + arg2
    return a
import gpi

class FakeGPI:
    def addWidget(self, *kwargs):
        pass

    def addOutPort(self, *kwargs):
        pass

    def getVal(self, *kwargs):
        pass

    def setData(self, *kwargs):
        pass



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

        out = self.getVal('bool')
        self.setData('out', out)

        return 0

    def execType(self):
        return gpi.GPI_THREAD


test = ExternalNode()
print(test.initUI())
print(test.compute())

