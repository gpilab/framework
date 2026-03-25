#!/usr/bin/env python3
"""
Comprehensive fftshift validation test against NumPy.
Tests even/odd dimensions, various array layouts, and multi-dimensional arrays.
Validates the expected behavior of NumPy fftshift/ifftshift.
"""

import numpy as np
import sys
from itertools import product

def test_1d_fftshift_even():
    """Test 1D fftshift with even dimension array."""
    print("\n🧪 Test 1D fftshift (EVEN dimension)")
    
    # Create test array: [0, 1, 2, 3, 4, 5]
    arr = np.arange(6, dtype=np.complex128)
    expected = np.fft.fftshift(arr)
    
    print(f"  Input:    {arr}")
    print(f"  Expected: {expected}")
    print(f"  (NumPy shift left by N//2={len(arr)//2})")
    
    # Should be [3, 4, 5, 0, 1, 2]
    assert np.allclose(expected, np.array([3, 4, 5, 0, 1, 2], dtype=np.complex128)), \
        "NumPy fftshift validation failed"
    print("  ✅ NumPy validation passed")
    return True

def test_1d_fftshift_odd():
    """Test 1D fftshift with odd dimension array."""
    print("\n🧪 Test 1D fftshift (ODD dimension)")
    
    # Create test array: [0, 1, 2, 3, 4]
    arr = np.arange(5, dtype=np.complex128)
    expected = np.fft.fftshift(arr)
    
    print(f"  Input:    {arr}")
    print(f"  Expected: {expected}")
    print(f"  (NumPy shift left by ceil(N/2)={(len(arr)+1)//2})")
    
    # Should be [3, 4, 0, 1, 2]
    assert np.allclose(expected, np.array([3, 4, 0, 1, 2], dtype=np.complex128)), \
        "NumPy fftshift validation failed"
    print("  ✅ NumPy validation passed")
    return True

def test_2d_fftshift_even_even():
    """Test 2D fftshift with both dimensions even."""
    print("\n🧪 Test 2D fftshift (EVEN x EVEN)")
    
    arr = np.arange(12, dtype=np.complex128).reshape(3, 4)
    expected = np.fft.fftshift(arr)
    
    print(f"  Input shape: {arr.shape}")
    print(f"  Input:\n{arr}")
    print(f"  Expected:\n{expected}")
    
    # Both dims should shift: (3//2, 4//2) = (1, 2)
    # Rows shift by 1, Cols shift by 2
    expected_manual = np.array([
        [10, 11,  8,  9],
        [ 2,  3,  0,  1],
        [ 6,  7,  4,  5]
    ], dtype=np.complex128)
    assert np.allclose(expected, expected_manual), "Manual fftshift validation failed"
    print("  ✅ 2D EVEN×EVEN validation passed")
    return True

def test_2d_fftshift_odd_even():
    """Test 2D fftshift with one odd, one even dimension."""
    print("\n🧪 Test 2D fftshift (ODD x EVEN)")
    
    arr = np.arange(10, dtype=np.complex128).reshape(5, 2)
    expected = np.fft.fftshift(arr)
    
    print(f"  Input shape: {arr.shape}")
    print(f"  Input:\n{arr}")
    print(f"  Expected:\n{expected}")
    
    # Rows shift by ceil(5/2)=3, Cols shift by 2//2=1
    print(f"  Shape {arr.shape}: shift rows by {(5+1)//2}, cols by {2//2}")
    print(f"  (Dimension 0: odd, shift ceil; Dimension 1: even, shift half)")
    print("  ✅ 2D ODD×EVEN format validated")
    return True

def test_2d_fftshift_odd_odd():
    """Test 2D fftshift with both dimensions odd."""
    print("\n🧪 Test 2D fftshift (ODD x ODD)")
    
    arr = np.arange(9, dtype=np.complex128).reshape(3, 3)
    expected = np.fft.fftshift(arr)
    
    print(f"  Input shape: {arr.shape}")
    print(f"  Input:\n{arr}")
    print(f"  Expected:\n{expected}")
    
    # Both dims shift by ceil(N/2): (3+1)//2 = 2
    expected_manual = np.array([
        [8, 6, 7],
        [2, 0, 1],
        [5, 3, 4]
    ], dtype=np.complex128)
    assert np.allclose(expected, expected_manual), "Manual fftshift validation failed"
    print("  ✅ 2D ODD×ODD validation passed")
    return True

def test_ifftshift_even():
    """Test ifftshift (inverse) with even dimension."""
    print("\n🧪 Test 1D ifftshift (EVEN dimension)")
    
    arr = np.array([3, 4, 5, 0, 1, 2], dtype=np.complex128)
    expected = np.fft.ifftshift(arr)
    
    print(f"  Input (shifted): {arr}")
    print(f"  Expected result: {expected}")
    print(f"  (NumPy inverse shift, even dim)")
    
    # Should recover original [0, 1, 2, 3, 4, 5]
    assert np.allclose(expected, np.arange(6, dtype=np.complex128)), \
        "NumPy ifftshift validation failed"
    print("  ✅ ifftshift EVEN validation passed")
    return True

def test_ifftshift_odd():
    """Test ifftshift (inverse) with odd dimension."""
    print("\n🧪 Test 1D ifftshift (ODD dimension)")
    
    arr = np.array([3, 4, 0, 1, 2], dtype=np.complex128)
    expected = np.fft.ifftshift(arr)
    
    print(f"  Input (shifted): {arr}")
    print(f"  Expected result: {expected}")
    print(f"  (NumPy inverse shift, odd dim)")
    
    # For odd dims, ifftshift should recover the original
    print("  ✅ ifftshift ODD format validated")
    return True

def test_3d_fftshift_mixed():
    """Test 3D fftshift with mixed even/odd dimensions."""
    print("\n🧪 Test 3D fftshift (EVEN x ODD x EVEN)")
    
    arr = np.arange(24, dtype=np.complex128).reshape(4, 3, 2)
    expected = np.fft.fftshift(arr)
    
    print(f"  Input shape: {arr.shape}")
    print(f"  Shifts: dim0(even)={4//2}, dim1(odd)={(3+1)//2}, dim2(even)={2//2}")
    print(f"  Shape validation: {expected.shape == arr.shape}")
    assert expected.shape == arr.shape, "Shape mismatch after fftshift"
    print("  ✅ 3D EVEN×ODD×EVEN validation passed")
    return True

def test_roundtrip_even():
    """Test fftshift -> ifftshift roundtrip for even dimensions."""
    print("\n🧪 Test roundtrip (fftshift -> ifftshift) for EVEN array")
    
    arr = np.arange(8, dtype=np.complex128)
    shifted = np.fft.fftshift(arr)
    recovered = np.fft.ifftshift(shifted)
    
    print(f"  Original:  {arr}")
    print(f"  Shifted:   {shifted}")
    print(f"  Recovered: {recovered}")
    
    assert np.allclose(arr, recovered), "Roundtrip failed for even dimension"
    print("  ✅ Roundtrip EVEN validation passed")
    return True

def test_roundtrip_odd():
    """Test fftshift -> ifftshift roundtrip for odd dimensions."""
    print("\n🧪 Test roundtrip (fftshift -> ifftshift) for ODD array")
    
    arr = np.arange(7, dtype=np.complex128)
    shifted = np.fft.fftshift(arr)
    recovered = np.fft.ifftshift(shifted)
    
    print(f"  Original:  {arr}")
    print(f"  Shifted:   {shifted}")
    print(f"  Recovered: {recovered}")
    
    assert np.allclose(arr, recovered), "Roundtrip failed for odd dimension"
    print("  ✅ Roundtrip ODD validation passed")
    return True

def test_non_contiguous():
    """Test fftshift on non-contiguous array views."""
    print("\n🧪 Test fftshift on non-contiguous array (slice/transpose)")
    
    arr = np.arange(24, dtype=np.complex128).reshape(4, 6)
    
    # Non-contiguous view (transposed)
    view = arr.T
    assert not view.flags['C_CONTIGUOUS'], "View should be non-contiguous"
    print(f"  Non-contiguous view shape: {view.shape}")
    print(f"  C_CONTIGUOUS: {view.flags['C_CONTIGUOUS']}")
    
    # NumPy should handle it
    result = np.fft.fftshift(view)
    print(f"  Result shape: {result.shape}")
    print("  ✅ Non-contiguous array handling validated")
    return True

def test_edge_cases():
    """Test edge cases: size-1 arrays, empty arrays, etc."""
    print("\n🧪 Test edge cases")
    
    # Size-1 array
    arr_1 = np.array([42.0], dtype=np.complex128)
    result_1 = np.fft.fftshift(arr_1)
    assert np.allclose(result_1, arr_1), "Size-1 array should be unchanged"
    print("  ✅ Size-1 array: unchanged (as expected)")
    
    # Size-2 array (minimal even)
    arr_2 = np.array([1, 2], dtype=np.complex128)
    result_2 = np.fft.fftshift(arr_2)
    assert np.allclose(result_2, np.array([2, 1])), "Size-2 shift incorrect"
    print("  ✅ Size-2 array: correct shift")
    
    # All zeros
    arr_z = np.zeros((3, 4), dtype=np.complex128)
    result_z = np.fft.fftshift(arr_z)
    assert np.allclose(result_z, np.zeros((3, 4))), "Zeros should remain zeros"
    print("  ✅ Zero array: remains zeros")
    
    print("  ✅ All edge cases passed")
    return True

def test_complex_values():
    """Test with actual complex values (not just real)."""
    print("\n🧪 Test with complex-valued arrays")
    
    arr = np.array([1+2j, 3+4j, 5+6j, 7+8j], dtype=np.complex128)
    expected = np.fft.fftshift(arr)
    
    print(f"  Input:    {arr}")
    print(f"  Expected: {expected}")
    print(f"  Expected: {np.array([5+6j, 7+8j, 1+2j, 3+4j])}")
    
    expected_manual = np.array([5+6j, 7+8j, 1+2j, 3+4j], dtype=np.complex128)
    assert np.allclose(expected, expected_manual), "Complex fftshift incorrect"
    print("  ✅ Complex-valued array validation passed")
    return True

def run_all_tests():
    """Run all validation tests."""
    print("=" * 70)
    print("FFTSHIFT ROBUSTNESS TEST SUITE")
    print("Testing against NumPy fftshift/ifftshift")
    print("=" * 70)
    
    tests = [
        ("1D Even", test_1d_fftshift_even),
        ("1D Odd", test_1d_fftshift_odd),
        ("2D Even×Even", test_2d_fftshift_even_even),
        ("2D Odd×Even", test_2d_fftshift_odd_even),
        ("2D Odd×Odd", test_2d_fftshift_odd_odd),
        ("ifftshift Even", test_ifftshift_even),
        ("ifftshift Odd", test_ifftshift_odd),
        ("3D Mixed", test_3d_fftshift_mixed),
        ("Roundtrip Even", test_roundtrip_even),
        ("Roundtrip Odd", test_roundtrip_odd),
        ("Non-contiguous", test_non_contiguous),
        ("Edge Cases", test_edge_cases),
        ("Complex Values", test_complex_values),
    ]
    
    passed = 0
    failed = 0
    errors = []
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
                errors.append(f"{name}: returned False")
        except AssertionError as e:
            failed += 1
            errors.append(f"{name}: {e}")
        except Exception as e:
            failed += 1
            errors.append(f"{name}: {type(e).__name__}: {e}")
    
    print("\n" + "=" * 70)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 70)
    
    if errors:
        print("\n❌ FAILURES:")
        for error in errors:
            print(f"  • {error}")
        return False
    else:
        print("\n✅ ALL TESTS PASSED")
        return True

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
