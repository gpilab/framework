#!/opt/gpi/bin/python
import eigen 
import numpy as np

A = np.random.random((5,5)).astype(np.float32)
B = np.zeros(A.shape[::-1]).astype(np.float32)
print A
eigen.pinv(A,B)
print B
print np.linalg.pinv(A)

