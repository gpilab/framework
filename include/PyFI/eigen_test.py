#!/opt/gpi/bin/python
"""A simple test script for the PyFI eigen wrapper.
"""

import numpy as np
import eigen
import timeit

if __name__ == "__main__":
    m = 50 
    n = 50 
    A = 1000*np.random.random((m,n)).astype(np.float32)
    npAinv = np.linalg.pinv(A)
    eigenAinv = eigen.pinv(A)
    if np.allclose(npAinv, eigenAinv, rtol=0.01):
        init = """import eigen, numpy as np
m,n = 50,50
A = 1000*np.random.random((m,n)).astype(np.float32)"""
        a = timeit.timeit('np.linalg.pinv(A)', setup=init, number=1000)
        b = timeit.timeit('eigen.pinv(A)', setup=init, number=1000)
        print "eigen successfully inverted the {}x{} matrix {} times faster than numpy".format(m,n,a/b)

    p = 3
    B = 1000*np.random.random((m,p)).astype(np.float32)
    eigenX = eigen.solve(A,B)
    npX = np.linalg.lstsq(A,B)[0]
    if np.allclose(eigenX, npX, rtol=0.01):
        init = """import eigen as eigen, numpy as np
m,n,p = 50,50,3
A = 1000*np.random.random((m,n)).astype(np.float32)
B = 1000*np.random.random((m,p)).astype(np.float32)"""
        a = timeit.timeit('np.linalg.lstsq(A,B)', setup=init, number=1000)
        b = timeit.timeit('eigen.solve(A,B)', setup=init, number=1000)
        print "eigen successfully solved the equatioon AX=B {} times faster than numpy\n\twhere A was {}x{}, and B was {}x{}".format(a/b,m,n,m,p)

