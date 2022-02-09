#!/opt/gpi/bin/python

#    Copyright (C) 2014  Dignity Health
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#    NO CLINICAL USE.  THE SOFTWARE IS NOT INTENDED FOR COMMERCIAL PURPOSES
#    AND SHOULD BE USED ONLY FOR NON-COMMERCIAL RESEARCH PURPOSES.  THE
#    SOFTWARE MAY NOT IN ANY EVENT BE USED FOR ANY CLINICAL OR DIAGNOSTIC
#    PURPOSES.  YOU ACKNOWLEDGE AND AGREE THAT THE SOFTWARE IS NOT INTENDED FOR
#    USE IN ANY HIGH RISK OR STRICT LIABILITY ACTIVITY, INCLUDING BUT NOT
#    LIMITED TO LIFE SUPPORT OR EMERGENCY MEDICAL OPERATIONS OR USES.  LICENSOR
#    MAKES NO WARRANTY AND HAS NO LIABILITY ARISING FROM ANY USE OF THE
#    SOFTWARE IN ANY HIGH RISK OR STRICT LIABILITY ACTIVITIES.

"""A simple test script for the PyFI eigen wrapper.
"""
import numpy as np
import eigen
import timeit

if __name__ == "__main__":
    m = 500
    n = 500
    A = 1000*np.random.random((m,n))
    npAinv = np.linalg.pinv(A)
    eigenAinv = eigen.pinv(A)
    if np.allclose(npAinv, eigenAinv, rtol=0.01):
        init = """import eigen, numpy as np
m,n = 50,50
A = 1000*np.random.random((m,n))"""
        a = timeit.timeit('np.linalg.pinv(A)', setup=init, number=1000)
        b = timeit.timeit('eigen.pinv(A)', setup=init, number=1000)
        print("eigen successfully inverted the {}x{} matrix {} times faster than numpy".format(m,n,a/b))

    p = 3
    B = 1000*np.random.random((m,p))
    eigenX = eigen.solve(A,B)
    npX = np.linalg.lstsq(A,B)[0]
    if np.allclose(eigenX, npX, rtol=0.01):
        init = """import eigen as eigen, numpy as np
m,n,p = 50,50,3
A = 1000*np.random.random((m,n))
B = 1000*np.random.random((m,p))"""
        a = timeit.timeit('np.linalg.lstsq(A,B)', setup=init, number=1000)
        b = timeit.timeit('eigen.solve(A,B)', setup=init, number=1000)
        print("eigen successfully solved the equatioon AX=B {} times faster than numpy\n\twhere A was {}x{}, and B was {}x{}".format(a/b,m,n,m,p))


    p = 2000
    B = 1000*np.random.random((n,p))
    eigenC = eigen.dot(A,B)
    npC = np.dot(A,B)
    if np.allclose(eigenC, npC, rtol=0.01):
        init = """import eigen as eigen, numpy as np
m,n,p = 50,50,20
A = 1000*np.random.random((m,n))
B = 1000*np.random.random((n,p))"""
    a = timeit.timeit('np.dot(A,B)', setup=init, number=1000)
    b = timeit.timeit('eigen.dot(A,B)', setup=init, number=1000)
    print("eigen successfully multiplied A*B {} times faster than numpy\n\twhere A was {}x{}, and B was {}x{}".format(a/b,m,n,n,p))

