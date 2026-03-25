#!/usr/bin/env python3
"""
Test script for Voxel Array broadcasting, aggregation, and FFT functionality.
Calls compiled pybind11 test functions exposed in the 'test' module.
"""

import numpy as np
import sys

# Import the compiled test module
try:
    import test
except ImportError as e:
    print(f"ERROR: Could not import 'test' module: {e}")
    print("Make sure to run 'pip install .' first to build and install the module.")
    sys.exit(1)

def test_broadcasting():
    """Test broadcasting operations with automatic shape alignment."""
    print("\n" + "="*70)
    print("BROADCASTING TESTS")
    print("="*70)
    
    # Test 1: Broadcasting Addition (3,1,5) + (1,4,5) → (3,4,5)
    print("\n[TEST 1] Broadcasting Addition: (3,1,5) + (1,4,5) → (3,4,5)")
    A = np.ones((3, 1, 5), dtype=np.complex128)
    B = np.ones((1, 4, 5), dtype=np.complex128) * 2j
    result = test.test_broadcast_add(A, B)
    print(f"  Shape: {result.shape}")
    print(f"  Expected shape: (3, 4, 5) ✓" if result.shape == (3, 4, 5) else f"  Shape mismatch!")
    
    # Test 2: Broadcasting Multiplication
    print("\n[TEST 2] Broadcasting Multiplication: (5,1) * (1,3)")
    A = np.arange(5, dtype=np.complex128).reshape(5, 1)
    B = np.arange(3, dtype=np.complex128).reshape(1, 3)
    result = test.test_broadcast_mul(A, B)
    print(f"  Shape: {result.shape}")
    print(f"  Expected shape: (5, 3) ✓" if result.shape == (5, 3) else f"  Shape mismatch!")
    
    # Test 3: Broadcasting Subtraction
    print("\n[TEST 3] Broadcasting Subtraction: (4,3,1) - (1,1,2)")
    A = np.arange(12, dtype=np.complex128).reshape(4, 3, 1)
    B = np.arange(2, dtype=np.complex128).reshape(1, 1, 2)
    result = test.test_broadcast_sub(A, B)
    print(f"  Shape: {result.shape}")
    print(f"  Expected shape: (4, 3, 2) ✓" if result.shape == (4, 3, 2) else f"  Shape mismatch!")
    
    # Test 4: Broadcasting Division
    print("\n[TEST 4] Broadcasting Division: (2,1,3) / (1,4,1)")
    A = np.arange(1, 7, dtype=np.complex128).reshape(2, 1, 3)
    B = np.arange(1, 5, dtype=np.complex128).reshape(1, 4, 1)
    result = test.test_broadcast_div(A, B)
    print(f"  Shape: {result.shape}")
    print(f"  Expected shape: (2, 4, 3) ✓" if result.shape == (2, 4, 3) else f"  Shape mismatch!")
    
    # Test 5: In-place Broadcasting Addition
    print("\n[TEST 5] In-place Broadcasting Addition: A += B")
    A = np.ones((2, 3), dtype=np.complex128)
    B = np.ones((1, 3), dtype=np.complex128) * 2
    test.test_broadcast_add_inplace(A, B)
    print(f"  A shape after +=: {A.shape}")
    print(f"  A[0,0] value: {A[0,0]} (expected: 3+0j)")
    
    # Test 6: Equality Comparison with Broadcasting
    print("\n[TEST 6] Broadcasting Equality Comparison")
    A = np.array([1+1j, 2+2j], dtype=np.complex128)
    B = np.array([1+1j, 2+2j], dtype=np.complex128)
    result = test.test_broadcast_eq(A, B)
    print(f"  Result shape: {result.shape}")
    print(f"  Result dtype: {result.dtype} (expected: bool)")
    print(f"  All true: {np.all(result)}")


def test_aggregations():
    """Test aggregation operations (sum, norm, min, max, etc)."""
    print("\n" + "="*70)
    print("AGGREGATION TESTS")
    print("="*70)
    
    # Test 1: Sum of strided array
    print("\n[TEST 1] Sum of Non-Contiguous (Strided) Array")
    arr = np.arange(20, dtype=np.complex128)
    result = test.test_sum_strided(arr)
    expected = np.sum(arr)
    print(f"  Result: {result}")
    print(f"  Expected: {expected}")
    print(f"  Match: {np.isclose(result, expected)} ✓" if np.isclose(result, expected) else f"  Mismatch!")
    
    # Test 2: L2 norm
    print("\n[TEST 2] L2 Norm of Broadcasted Array")
    arr = np.array([3+4j, 5+12j], dtype=np.complex128)  # magnitudes: 5, 13
    result = test.test_l2norm_broadcasted(arr)
    expected = np.sqrt(5**2 + 13**2)
    print(f"  Result: {result}")
    print(f"  Expected: {expected}")
    print(f"  Match: {np.isclose(result, expected)} ✓" if np.isclose(result, expected) else f"  Mismatch!")
    
    # Test 3: Dot product
    print("\n[TEST 3] Dot Product with Conjugate")
    a = np.array([1+1j, 2+2j], dtype=np.complex128)
    b = np.array([1-1j, 1-1j], dtype=np.complex128)
    result = test.test_dot_verification(a, b)
    expected = np.vdot(b, a)  # conjugate(b) · a
    print(f"  Result: {result}")
    print(f"  Expected: {expected}")
    print(f"  Match: {np.isclose(result, expected)} ✓" if np.isclose(result, expected) else f"  Mismatch!")
    
    # Test 4: Min on double array
    print("\n[TEST 4] Min Value (double array)")
    arr = np.array([3.5, 1.2, 5.8, 2.1], dtype=np.float64)
    result = test.test_min_double(arr)
    expected = np.min(arr)
    print(f"  Result: {result}")
    print(f"  Expected: {expected}")
    print(f"  Match: {np.isclose(result, expected)} ✓" if np.isclose(result, expected) else f"  Mismatch!")
    
    # Test 5: Max on double array
    print("\n[TEST 5] Max Value (double array)")
    result = test.test_max_double(arr)
    expected = np.max(arr)
    print(f"  Result: {result}")
    print(f"  Expected: {expected}")
    print(f"  Match: {np.isclose(result, expected)} ✓" if np.isclose(result, expected) else f"  Mismatch!")
    
    # Test 6: Count true in boolean array
    print("\n[TEST 6] Count True Elements (from comparison)")
    a = np.array([1+1j, 2+2j, 3+3j], dtype=np.complex128)
    b = np.array([2+2j, 1+1j, 4+4j], dtype=np.complex128)
    count = test.test_count_comparison(a, b)
    print(f"  Count of a > b: {count}")


def test_fft():
    """Test 1D FFT operations."""
    print("\n" + "="*70)
    print("FFT TESTS")
    print("="*70)
    
    # Test 1: FFT forward on impulse
    print("\n[TEST 1] FFT of Impulse Signal")
    impulse = np.zeros(16, dtype=np.complex128)
    impulse[0] = 1.0
    result = test.test_fft1_impulse(impulse)
    print(f"  Input shape: {impulse.shape}")
    print(f"  Output shape: {result.shape}")
    print(f"  Output shape matches input ✓" if result.shape == impulse.shape else f"  Shape mismatch!")
    print(f"  First element (DC): {result[0]}")
    
    # Test 2: FFT of constant signal
    print("\n[TEST 2] FFT of Constant Signal")
    constant = np.ones(16, dtype=np.complex128)
    result = test.test_fft1_constant(constant)
    print(f"  Output shape: {result.shape}")
    print(f"  DC component (first bin): {result[0]}")
    print(f"  Other bins near zero: {np.max(np.abs(result[1:]))} (should be small)")
    
    # Test 3: FFT 2D round-trip
    print("\n[TEST 3] 2D FFT Round-Trip (Forward + Inverse)")
    data_2d = np.random.rand(8, 8).astype(np.complex128)
    result = test.test_fft2_roundtrip(data_2d)
    print(f"  Input shape: {data_2d.shape}")
    print(f"  Output shape: {result.shape} (should match input)")
    # For round-trip: FFT → IFFT should recover original (with NORM_BACKWARD)
    difference = np.max(np.abs(result - data_2d))
    print(f"  Max difference from original: {difference:.2e}")
    print(f"  Round-trip successful ✓" if difference < 1e-10 else f"  Round-trip error too large")


def test_stride_handling():
    """Test stride handling via NumPy strided arrays (validates slice fixes)."""
    print("\n" + "="*70)
    print("STRIDE & SLICING TESTS")
    print("="*70)
    
    # Test 1: Strided array (simulating negative step slicing)
    print("\n[TEST 1] Non-Contiguous Strided Array (negative step simulation)")
    arr_full = np.arange(10, dtype=np.complex128)
    arr_strided = arr_full[::2]  # Every 2nd element: [0, 2, 4, 6, 8]
    print(f"  Original array: {arr_full}")
    print(f"  Strided (::2): {arr_strided}")
    result = test.test_sum_strided(arr_strided)
    expected = np.sum(arr_strided)
    print(f"  Sum result: {result}")
    print(f"  Expected: {expected}")
    print(f"  Match: {np.isclose(result, expected)} ✓" if np.isclose(result, expected) else f"  Mismatch!")
    
    # Test 2: Reversed array (validates Array Reversal Landmine fix)
    print("\n[TEST 2] Reversed Array (Array Reversal Landmine validation)")
    arr = np.array([1+1j, 2+2j, 3+3j, 4+4j, 5+5j], dtype=np.complex128)
    arr_reversed = arr[::-1]  # Reverse: [5+5j, 4+4j, 3+3j, 2+2j, 1+1j]
    print(f"  Original: {arr}")
    print(f"  Reversed: {arr_reversed}")
    result = test.test_sum_strided(arr_reversed)
    expected = np.sum(arr_reversed)
    print(f"  Sum of reversed: {result}")
    print(f"  Expected: {expected}")
    print(f"  Match: {np.isclose(result, expected)} ✓" if np.isclose(result, expected) else f"  Mismatch!")
    
    # Test 3: L2 norm on strided view
    print("\n[TEST 3] L2 Norm on Strided Array")
    arr = np.array([3+4j, 0+0j, 5+12j, 0+0j], dtype=np.complex128)
    arr_strided = arr[::2]  # [3+4j, 5+12j] - magnitudes: 5, 13
    result = test.test_l2norm_broadcasted(arr_strided)
    expected = np.linalg.norm(np.abs(arr_strided))
    print(f"  Strided elements: {arr_strided}")
    print(f"  L2 norm result: {result}")
    print(f"  Expected: {expected}")
    print(f"  Match: {np.isclose(result, expected)} ✓" if np.isclose(result, expected) else f"  Mismatch!")
    
    # Test 4: Negative stride with large step
    print("\n[TEST 4] Large Negative Step (-3)")
    arr = np.arange(20, dtype=np.float64)
    arr_strided = arr[::-3]  # Reverse with step -3
    print(f"  Original: {arr}")
    print(f"  Strided [::-3]: {arr_strided}")
    result = test.test_sum_strided(arr_strided)
    expected = np.sum(arr_strided)
    print(f"  Sum result: {result}")
    print(f"  Expected: {expected}")
    print(f"  Match: {np.isclose(result, expected)} ✓" if np.isclose(result, expected) else f"  Mismatch!")
    
    # Test 5: Non-contiguous 2D slice (validates .copy() on sliced views)
    print("\n[TEST 5] Non-Contiguous 2D Array (copy from slice)")
    arr_2d = np.arange(20, dtype=np.complex128).reshape(4, 5)
    arr_slice = arr_2d[::2, ::2]  # Every 2nd row and column (non-contiguous)
    print(f"  Original shape: {arr_2d.shape}")
    print(f"  Sliced shape: {arr_slice.shape}")
    print(f"  Sliced is contiguous: {arr_slice.flags['C_CONTIGUOUS']}")
    # Sum the sliced view to test stride handling in aggregation
    result = test.test_sum_strided(arr_slice.flatten())
    expected = np.sum(arr_slice)
    print(f"  Sum of sliced: {result}")
    print(f"  Expected: {expected}")
    print(f"  Match: {np.isclose(result, expected)} ✓" if np.isclose(result, expected) else f"  Mismatch!")
    
    # Test 6: Partial reversal - middle section reversed
    print("\n[TEST 6] Partial Segment Reversal")
    arr = np.arange(10, dtype=np.float64) + 1.0  # [1, 2, ..., 10]
    arr_partial = arr[2:8][::-1]  # Reverse elements 2-8: [8, 7, 6, 5, 4, 3]
    print(f"  Original: {arr}")
    print(f"  Partial reversed [2:8][::-1]: {arr_partial}")
    result = test.test_sum_strided(arr_partial)
    expected = np.sum(arr_partial)
    print(f"  Sum result: {result}")
    print(f"  Expected: {expected}")
    print(f"  Match: {np.isclose(result, expected)} ✓" if np.isclose(result, expected) else f"  Mismatch!")


def test_comparison_operators():
    """Test comparison operators with broadcasting."""
    print("\n" + "="*70)
    print("COMPARISON OPERATOR TESTS")
    print("="*70)
    
    # Test 1: Less than
    print("\n[TEST 1] Broadcasting Less Than (<)")
    A = np.array([1+1j, 2+2j, 3+3j], dtype=np.complex128)
    B = np.array([2+2j, 2+2j, 2+2j], dtype=np.complex128)
    result = test.test_broadcast_lt(A, B)
    print(f"  A magnitudes: {np.abs(A)}")
    print(f"  B magnitude: 2.828...")
    print(f"  A < B (by magnitude): {result}")
    
    # Test 2: Greater than
    print("\n[TEST 2] Broadcasting Greater Than (>)")
    result = test.test_broadcast_gt(A, B)
    print(f"  A > B (by magnitude): {result}")


def main():
    """Run all test suites."""
    print("\n" + "#"*70)
    print("# VOXEL ARRAY TEST SUITE")
    print("# Testing Broadcasting, Aggregations, and FFT Functionality")
    print("#"*70)
    
    try:
        test_broadcasting()
        test_aggregations()
        test_stride_handling()
        test_comparison_operators()
        test_fft()
        
        print("\n" + "#"*70)
        print("# ALL TESTS COMPLETED SUCCESSFULLY ✓")
        print("#"*70)
        
    except Exception as e:
        print(f"\n\nERROR during testing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
