# test_array.py
"""
Unit tests for Voxel::Array core features (creation, shape, access, reshape, transpose, type conversion)
Author: Guru Krishnamoorthy
Date: 2026-03-25
"""
import importlib
import numpy as np

import test_Array as mod

def test_array_shape():
    shape = mod.test_array_shape()
    assert shape == [3, 4, 5]

def test_array_set_get():
    val = mod.test_array_set_get()
    assert np.isclose(val, 4.0)

def test_array_reshape():
    shape = mod.test_array_reshape()
    assert shape == [3, 4]

def test_array_transpose():
    shape = mod.test_array_transpose()
    assert shape == [4, 2, 3]

def test_array_astype():
    val = mod.test_array_astype()
    assert np.isclose(val, 5.85)

if __name__ == "__main__":
    test_array_shape()
    test_array_set_get()
    test_array_reshape()
    test_array_transpose()
    test_array_astype()
    print("All tests passed!")
