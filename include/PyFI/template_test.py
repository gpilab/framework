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


"""A simple test script for the PyFI template module.
"""

import os
import sys
import time
import numpy as np
import numpy.linalg as npl

import template as temp

import math
from math import sqrt




# PYCALLABLE
A = np.array(list(range(4)), dtype=np.float32)
A.shape = [2,2]
print("A:", A)
print("Ainv:", npl.pinv(A))

x = np.array(list(range(24)), dtype=np.float32)
x.shape = [4,3,2]

print(x)

print("matmult (PYTHON)")
print("A: ", A)
print("AdotA: ", np.dot(A,A))

st = time.time()
aarr, c = temp.IFtest2(x)
print("IFtest time: ", time.time()-st)

print(c)

print("aarr:", aarr)


temp.math_double()
temp.math_float()
temp.math_int()




# testing the PyFI interface.
def test(thetest, name):
    if thetest:
        print('\t-'+name+' passed')
        return 1
    else:
        print('\t-'+name+' failed')
        return 0




print("\n\nInterface testing...")
mi = 111
mf = 111.111
ms = 'hello from python'

acf = np.array([1 + 2j, 2, 3], dtype=np.complex64)
ad  = np.array([111.111, 22.22, 3.3], dtype=np.float64)
al  = np.array([7], dtype=np.int64)

# no keywords
# check KW defaults
preout, insize, oi, of, okf, oks, os, nchk, cfa, la, kcfa, kda, kla = temp.IFtest(mi, mf, ms, acf, ad, al)
cnt = 0
tot = 0

# tests
cnt += test((preout == 8.1).all(), 'preout')
tot += 1
cnt += test(oi == (1+111), 'myoutint')
tot += 1
cnt += test(of == mf, 'myfloat')
tot += 1
cnt += test(okf == -0.6, 'mykwfloat')
tot += 1
cnt += test(oks == '<<< your ad here >>>', 'mykwstring')
tot += 1
cnt += test(os == 'c++ generated string', 'myoutstring') 
tot += 1
cnt += test(nchk == 1, 'nullCheckPassed') 
tot += 1
cnt += test((insize == np.multiply(ad,ad)).all(), 'nullCheckPassed') 
tot += 1
cnt += test((cfa == acf).all(), 'mycfarr') 
tot += 1
cnt += test((la == al).all(), 'mylarr') 
tot += 1
cnt += test((kcfa == 1.0+1j).all(), 'mykwcfarr default') 
tot += 1
cnt += test((kda == 0.0).all(), 'mykwdarr default') 
tot += 1
cnt += test((kla == 7).all(), 'mykwlarr default') 
tot += 1

# test keywords
preout, insize, oi, of, okf, oks, os, nchk, cfa, la, kcfa, kda, kla = temp.IFtest(mi, mf, ms, acf, ad, al, mykwcfarr=acf, mykwdarr=ad, mykwlarr=al)

# tests
cnt += test((kcfa == acf).all(), 'mykwcfarr') 
tot += 1
cnt += test((kda == ad).all(), 'mykwdarr') 
tot += 1
cnt += test((kla == al).all(), 'mykwlarr') 
tot += 1

print('\nTest Summary:')
if cnt == tot:
    print('\tSUCCESS: '+str(cnt)+'/'+str(tot))
else:
    print('\tFAILED: '+str(cnt)+'/'+str(tot))
