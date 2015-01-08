#!/opt/gpi/bin/python
import eigen 
import numpy as np

A = np.random.random((5,5)).astype(np.float32)
print A
eigen.pinv(A)
