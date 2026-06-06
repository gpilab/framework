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
# Date: 2013jul12

import gpi


class ExternalNode(gpi.NodeAPI):
    """A module for doing least squares fitting of input data to a user
    defined model.  Fitting is always done along the first dimension.

    INPUTS:
    dataIn - data to fit (i.e. "Y" values, assume "X" values are linear)
    coordsIn - "X" values corresponding to "Y" values of dataIn, if they are not linear

    OUTPUTS:
    fit - the fit curve
    coefficients - coefficients of the fit polynomial
    residual - the input data minus the fit curve

    WIDGETS:
    Mode - choose type of fit
    Info - some instructions for use
    For Mode = Polynomial Fit
      Polynomial order - 0 fits to a constant, 1 fits to a line, 2 fits to a parabola, etc.
    For Mode = Generalized Linear 
      data are fit to a linear sum of functions_which_depend_on_x
      # Model Parameters - number of functions to fit (number of coefficients to calculate)
      fi(x) - the model for the ith function, written as a python function of x.  Examples include:
             1                   (i.e. just a constant)
             np.power(x,3)       (fit to x^3)
             np.sin(x)           (fit to sin of x)
    For Mode = Generalized Non-Linear 
      See Info box (with this Mode selected) for detailed information
    """
    def execType(self):
        return gpi.GPI_PROCESS
        #return gpi.GPI_THREAD

    def initUI(self):
        self.nparms = 9
        self.poly_info_text = "Select the order of the polynomial to which " \
                            + "to fit the data.\n"
        self.lin_info_text = "Define each component of the linear model " \
                           + "using the editable\n text boxes below for " \
                           + "each model parameter.\n\n" \
                           + "The linear model follows the relationship:\n"
        self.lin_model = ''
        self.nl_info_text = "Use the Model Definition box below to enter an " \
                          + "expression\nfor the model to which you would " \
                          + "like to fit your data.\n" \
                          + "Follow the format of the example models " \
                          + "shown below.\n\n" \
                          + "    MODEL EXAMPLES:\n" \
                          + "  1) Second order polynomial (3 model " \
                          + "parameters):\n" \
                          + "    y = a0 + a1 * x + a2 * np.power(x, 2)\n" \
                          + "  2) Exponential Decay (2 model parameters):\n" \
                          + "    y = a0 * np.exp(-x/a1)\n" \
                          + "  3) Sinusoid (4 model parameters):\n" \
                          + "    y = a0 + a1 * np.sin(a2*x + a3)\n" \
                          + "  4) Lorentzian (3 model parameters):\n" \
                          + "    y = (a0 / np.pi) * (a1 / 2) / " \
                          + "(np.power(x - a2, 2) + np.power(a1 / 2, 2))\n" \
                          + "  5) Gaussian (3 model parameters):\n" \
                          + "    y = a0 * np.exp(-np.power(x - a1, 2) / " \
                          + "(2 * np.power(a2, 2)))" 


        # Widgets
        self.addWidget('ExclusivePushButtons', 'Mode', buttons=[
                       'Polynomial Fit', 'Generalized Linear',
                       'Generalized Non-linear'], val=0)
        self.addWidget('TextBox', 'Info:', val="")
        self.addWidget('StringBox', 'Model Definition:', val='y = x')
        self.addWidget('SpinBox', '# Model Parameters', val = 3, min=1, max=self.nparms)
        self.addWidget('DoubleSpinBox', 'Initial a0', decimals = 5,  val = 1.0)
        self.addWidget('StringBox', 'f0(x) =', val='1')
        for i in range(self.nparms):
            if i > 0:
                self.addWidget('DoubleSpinBox', 'Initial a%i'%i, decimals = 5,
                               val = 1.0)
                self.addWidget('StringBox', 'f%i(x) ='%i,
                               val='np.power(x, %i)'%i)
        self.addWidget('SpinBox', 'Polynomial Order', val = 3, min=0)
        self.addWidget('PushButton', 'Compute', toggle=True, val=1)

        # IO Ports
        self.addInPort('dataIn', 'NPYarray', obligation=gpi.REQUIRED, ndim = 2)
        self.addInPort('coordsIn', 'NPYarray', obligation=gpi.OPTIONAL, ndim = 1)
        self.addOutPort('fit', 'NPYarray')
        self.addOutPort('coefficients', 'NPYarray')
        self.addOutPort('residual', 'NPYarray')

    def validate(self):

        self.lin_model = 'y = '

        if (self.portEvents() or
            set(self.widgetEvents()).intersection(set(['Mode', '# Model Parameters']))):
            nParms = self.getVal('# Model Parameters')
            mode = self.getVal('Mode')
            for i in range(self.nparms):
                if i < nParms and mode == 1:
                    self.setAttr('f%i(x) ='%i, visible=True)
                    self.lin_model = self.lin_model +'a%i * f%i(x) + '%(i,i)
                else:
                    self.setAttr('f%i(x) ='%i, visible=False)
                if i < nParms and mode == 2:
                    self.setAttr('Initial a%i'%i, visible=True)
                else:
                    self.setAttr('Initial a%i'%i, visible=False)

            if mode == 0:
                self.setAttr('# Model Parameters', visible=False)
                self.setAttr('Model Definition:', visible=False)
                self.setAttr('Polynomial Order', visible=True)
                self.setAttr('Info:', val=self.poly_info_text)
            elif mode == 1:
                self.setAttr('# Model Parameters', visible=True)
                self.setAttr('Model Definition:', visible=False)
                self.setAttr('Polynomial Order', visible=False)
                self.lin_model = self.lin_model[:-3]+'\n'
                self.setAttr('Info:', val=self.lin_info_text
                                  +self.lin_model)
            else:
                self.setAttr('# Model Parameters', visible=True)
                self.setAttr('Model Definition:', visible=True)
                self.setAttr('Polynomial Order', visible=False)
                self.setAttr('Info:', val=self.nl_info_text)

        return(0)

    def compute(self):

        import numpy as np
        from scipy.optimize import curve_fit

        data = self.getData('dataIn')
        coords = self.getData('coordsIn')
        if coords is None:
            coords = np.array(list(range(data.shape[-1])))

        mode = self.getVal('Mode')
        compute = self.getVal('Compute')

        outer_dim = data.shape[0]

        if compute == 1:
            out = np.zeros(data.shape)
            res = np.zeros(data.shape)
            if mode == 0:
                order = self.getVal('Polynomial Order')
                try:
                    p = np.polyfit(coords, data.T, order)
                except:
                    info = self.poly_info_text \
                         + "\n\nError in the data fitting!"
                    self.setAttr('Info:', val=info)
                    self.setAttr('Compute', val=0)
                else:
                    if outer_dim < 20:
                        info = self.poly_info_text \
                            + "\n\nFit coefficients: "+str(p.T)
                        self.setAttr('Info:', val=info)
                    for i in range(outer_dim):
                        a = p[:,i]
                        out[i,:] = np.polyval(a, coords)
                        res[i,:] = np.subtract(data[i,:], out[i,:])
                    self.setData('fit', out)
                    self.setData('coefficients', np.ascontiguousarray(p))
                    self.setData('residual', res)

            elif mode == 1:
                x = coords
                nParms = self.getVal('# Model Parameters')
                A = np.ones([nParms, coords.shape[-1]])
                for i in range(nParms):
                    func = self.getVal('f%i(x) ='%i)
                    exec('A[%i,:] = '%i+func)
                try:
                    a = np.linalg.lstsq(A.T, data.T)[0]
                except:
                    info = self.lin_info_text + self.lin_model \
                         + "\n\nError in the model or data fitting!"
                    self.setAttr('Info:', val=info)
                    self.setAttr('Compute', val=0)
                else:
                    if outer_dim < 20:
                        info = self.lin_info_text + self.lin_model \
                             + "\n\nFit coefficients: "+str(a.T)
                        self.setAttr('Info:', val=info)
                    for i in range(outer_dim):
                        for j in range(nParms):
                            func = self.getVal('f%i(x) ='%j)
                            exec('out[i,:] = out[i,:] + a[j,i] * '+func)
                        res[i,:] = np.subtract(data[i,:], out[i,:])
                    self.setData('fit', out)
                    self.setData('coefficients', np.ascontiguousarray(a))
                    self.setData('residual', res)

            elif mode == 2:
                mod_expr = 'def Model(x, a0, '
                nParms = self.getVal('# Model Parameters')
                regress_code = self.getVal('Model Definition:')
                a0 = []
                for i in range(0, nParms):
                    val = self.getVal('Initial a%i'%i)
                    a0.append(val)
                p0 = a0
                for i in range(1, nParms):
                    mod_expr = mod_expr+'a%i, '%i
                mod_expr = mod_expr[:-2]+'):\n    import numpy as np\n    ' \
                         +regress_code+'\n    return y\n'
                a = np.zeros([outer_dim, nParms])
                try:
                    exec(mod_expr, locals(), globals())
                    for i in range(outer_dim):
                        p, cov = curve_fit(Model, coords, data[i,:], p0=p0)
                        a[i,:] = p
                except:
                    info = self.nl_info_text \
                         + "\n\nError in the model or data fitting at %i!" %i
                    self.setAttr('Info:', val=info)
                    self.setAttr('Compute', val=0)
                else:
                    if outer_dim < 20:
                        info = self.nl_info_text \
                             + "\n\nFit coefficients: "+str(a)
                        self.setAttr('Info:', val=info)
                    for i in range(outer_dim):
                        out_expr = 'out[i,:] = Model(coords, a[i,0], '
                        for j in range(1, nParms):
                            out_expr = out_expr+'a[i,%i], '%j
                        out_expr = out_expr[:-2]+')'
                        exec(out_expr)
                        res[i,:] = np.subtract(data[i,:], out[i,:])
                    self.setData('fit', out)
                    self.setData('coefficients', np.ascontiguousarray(a))
                    self.setData('residual', res)

        return(0)
