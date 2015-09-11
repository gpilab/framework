# Author:
# Date: 

import numpy as np
import gpi

# This is a template node, with stubs for initUI() (input/output ports,
# widgets), validate(), and compute().
# Documentation for the node API can be found online:
# http://docs.gpilab.com/NodeAPI

class ExternalNode(gpi.NodeAPI):
    """This is a GPI node template.

    You should replace this docstring with accurate and thorough documentation.
    INPUT:
        in - a numpy array
    OUTPUT:
        out - a numpy array
    WIDGETS:
        foo - an integer
    """

    # initialize the UI - add widgets and input/output ports
    def initUI(self):
        # Widgets
        self.addWidget('SpinBox', 'foo', val=10, min=0, max=100)
        # self.addWidget('DoubleSpinBox', 'bar', val=10, min=0, max=100)
        # self.addWidget('PushButton', 'baz', toggle=True)
        # self.addWidget('ExclusivePushButtons', 'qux',
        #              buttons=['Antoine', 'Colby', 'Trotter', 'Adair'], val=1)

        # IO Ports
        self.addInPort('in', 'NPYarray', dtype=np.complex64, ndim=3)
        self.addOutPort('out', 'NPYarray', dtype=np.float64, ndim=3)


    # validate the data - runs immediately before compute
    # your last chance to show/hide/edit widgets
    # return 1 if the data is not valid - compute will not run
    # return 0 if the data is valid - compute will run
    def validate(self):
        in_data = self.getData('in')

        # TODO: make sure the input data is valid
        # [your code here]

        return 0

    # process the input data, send it to the output port
    # return 1 if the computation failed
    # return 0 if the computation was successful 
    def compute(self):
        data = self.getData('in')
        foo = self.getVal('foo')

        out = data * foo
        # TODO: process the data
        # [your code here]

        self.setData('out', out)

        return 0
