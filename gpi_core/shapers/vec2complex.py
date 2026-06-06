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


#__author__ = "Nick Zwart"
#__date__ = "2010dec07"
''' For converting between vectorized matrices and complex matrices
    vectorized:
        x[m,n,1]   is a 2D 1-vec array
        x[m,n,o,2] is a 3D 2-vec array
    complex:
        x[0,0] = 1+j2 is a complex element from a 2D array

'''

import numpy as np  # operate on numpy arrays

# newer, better, faster


def c_2_vec(in1, typ):
    '''Convert a complex (or real valued) array to a 2-vec
    '''

    # reshape
    new_shape = list(in1.shape)
    new_shape += [2]  # add vector

    # allocate new 2-vec mem
    out = np.zeros(new_shape, typ)

    out[(Ellipsis, 0)] = in1.real
    out[(Ellipsis, 1)] = in1.imag

    return(out)


def vec_2_c(in1, typ):
    '''Convert a vectorized 1 or 2-vec to complex.
       -Unfortunately this requires a math operation
        instead of just recasting (this should change
        in the future).
    '''

    # get input array shape
    new_shape = list(in1.shape)
    veclen = new_shape[-1]

    # check that last dim is either 1 or 2,
    # if not, then skip reshape
    if(veclen == 1 or veclen == 2):
        new_shape.pop()  # remove vec dim

    # allocate new complex data type
    out = np.zeros(new_shape, typ)

    # make 2-vec complex
    if veclen == 1:
        out[:] = in1[:, 0]
    elif veclen == 2:
        out[:] = in1[(Ellipsis, 0)] + in1[(Ellipsis, 1)]*1j
    else:  # real valued
        out[:] = in1[:]

    return(out)
