#!/usr/bin/env python3
"""
Comprehensive FFT Validation Script
Compares PocketFFT wrapper results against NumPy's reference FFT implementation
"""

import numpy as np
import sys
try:
    import test
except ImportError:
    print("ERROR: Could not import test module. Run 'gpi_make test' first.")
    sys.exit(1)

def compare_arrays(result, expected, test_name, tolerance=1e-10, verbose=False):
    """Compare two arrays and report results"""
    if result.shape != expected.shape:
        print(f"✗ {test_name}: Shape mismatch! Got {result.shape}, expected {expected.shape}")
        return False
    
    max_error = np.max(np.abs(result - expected))
    mean_error = np.mean(np.abs(result - expected))
    
    passed = max_error < tolerance
    status = "✓" if passed else "✗"
    
    print(f"{status} {test_name}")
    if verbose or not passed:
        print(f"    Max error: {max_error:.2e} (tolerance: {tolerance:.2e})")
        print(f"    Mean error: {mean_error:.2e}")
        if not passed and result.size <= 16:
            print(f"    Got:      {result}")
            print(f"    Expected: {expected}")
    
    return passed


def test_1d_fft():
    """Test 1D FFT forward transform"""
    print("\n" + "="*70)
    print("TEST: 1D FFT Forward Transform")
    print("="*70)
    
    passed = 0
    total = 0
    
    test_cases = [
        ("Simple: [1+0j, 2+0j, 3+0j, 4+0j]", np.array([1+0j, 2+0j, 3+0j, 4+0j])),
        ("8-element", np.array([1, 2, 3, 4, 5, 6, 7, 8], dtype=np.complex128)),
        ("16-element", np.arange(1, 17, dtype=np.complex128)),
        ("Power of 2 (32)", np.arange(1, 33, dtype=np.complex128)),
        ("Complex values", np.array([1+1j, 2+2j, 3+3j, 4+4j], dtype=np.complex128)),
    ]
    
    for test_name, input_arr in test_cases:
        total += 1
        try:
            result = test.test_fft1_forward(input_arr)
            expected = np.fft.fft(input_arr, norm='backward')
            
            if compare_arrays(result, expected, test_name, tolerance=1e-10):
                passed += 1
        except Exception as e:
            print(f"✗ {test_name}: EXCEPTION: {e}")
    
    print(f"\nResult: {passed}/{total} passed")
    return passed, total


def test_1d_ifft():
    """Test 1D FFT inverse transform"""
    print("\n" + "="*70)
    print("TEST: 1D FFT Inverse Transform")
    print("="*70)
    
    passed = 0
    total = 0
    
    test_cases = [
        ("Inverse of [10, -2+2j, -2, -2-2j]", np.array([10, -2+2j, -2, -2-2j], dtype=np.complex128)),
        ("8-element", np.arange(1, 9, dtype=np.complex128)),
        ("Complex energy spectrum", np.array([10+0j, -2+2j, -2+0j, -2-2j], dtype=np.complex128)),
    ]
    
    for test_name, input_arr in test_cases:
        total += 1
        try:
            result = test.test_fft1_inverse(input_arr)
            expected = np.fft.ifft(input_arr, norm='backward')
            
            if compare_arrays(result, expected, test_name, tolerance=1e-10):
                passed += 1
        except Exception as e:
            print(f"✗ {test_name}: EXCEPTION: {e}")
    
    print(f"\nResult: {passed}/{total} passed")
    return passed, total


def test_2d_fft():
    """Test 2D FFT forward transform"""
    print("\n" + "="*70)
    print("TEST: 2D FFT Forward Transform")
    print("="*70)
    
    passed = 0
    total = 0
    
    test_cases = [
        ("4x4 matrix", np.arange(1, 17, dtype=np.complex128).reshape(4, 4)),
        ("8x8 matrix", np.arange(1, 65, dtype=np.complex128).reshape(8, 8)),
        ("3x5 matrix", np.arange(1, 16, dtype=np.complex128).reshape(3, 5)),
        ("2x2 simple", np.array([[1+0j, 2+0j], [3+0j, 4+0j]])),
    ]
    
    for test_name, input_arr in test_cases:
        total += 1
        try:
            result = test.test_fft2_forward(input_arr)
            expected = np.fft.fft2(input_arr, norm='backward')
            
            if compare_arrays(result, expected, test_name, tolerance=1e-9):
                passed += 1
        except Exception as e:
            print(f"✗ {test_name}: EXCEPTION: {e}")
    
    print(f"\nResult: {passed}/{total} passed")
    return passed, total


def test_2d_ifft():
    """Test 2D FFT inverse transform"""
    print("\n" + "="*70)
    print("TEST: 2D FFT Inverse Transform")
    print("="*70)
    
    passed = 0
    total = 0
    
    test_cases = [
        ("4x4 matrix", np.arange(1, 17, dtype=np.complex128).reshape(4, 4)),
        ("8x8 matrix", np.arange(1, 65, dtype=np.complex128).reshape(8, 8)),
    ]
    
    for test_name, input_arr in test_cases:
        total += 1
        try:
            result = test.test_fft2_inverse(input_arr)
            expected = np.fft.ifft2(input_arr, norm='backward')
            
            if compare_arrays(result, expected, test_name, tolerance=1e-9):
                passed += 1
        except Exception as e:
            print(f"✗ {test_name}: EXCEPTION: {e}")
    
    print(f"\nResult: {passed}/{total} passed")
    return passed, total


def test_round_trip():
    """Test FFT -> IFFT round-trip consistency"""
    print("\n" + "="*70)
    print("TEST: FFT Round-Trip Consistency (FFT -> IFFT)")
    print("="*70)
    
    passed = 0
    total = 0
    
    test_cases = [
        ("1D simple", np.array([1, 2, 3, 4], dtype=np.complex128)),
        ("1D 8-element", np.arange(1, 9, dtype=np.complex128)),
        ("2D 4x4", np.arange(1, 17, dtype=np.complex128).reshape(4, 4)),
    ]
    
    for test_name, input_arr in test_cases:
        total += 2  # Forward and backward
        
        try:
            # 1D test
            if input_arr.ndim == 1:
                fft_result = test.test_fft1_forward(input_arr)
                recovered = test.test_fft1_inverse(fft_result)
            else:
                fft_result = test.test_fft2_forward(input_arr)
                recovered = test.test_fft2_inverse(fft_result)
            
            if compare_arrays(recovered, input_arr, f"{test_name} (round-trip)", tolerance=1e-9):
                passed += 1
            else:
                total -= 1  # Don't count this check
        except Exception as e:
            print(f"✗ {test_name}: EXCEPTION: {e}")
            total -= 2
    
    print(f"\nResult: {passed}/{total} passed")
    return passed, total


def test_fft_with_shift():
    """Test FFT with fftshift"""
    print("\n" + "="*70)
    print("TEST: FFT with FFTshift")
    print("="*70)
    
    passed = 0
    total = 0
    
    test_cases = [
        ("1D simple", np.array([1+0j, 2+0j, 3+0j, 4+0j])),
        ("1D 8-element", np.arange(1, 9, dtype=np.complex128)),
    ]
    
    for test_name, input_arr in test_cases:
        total += 1
        try:
            # PocketFFT with shift
            result = test.test_fft1_with_shift(input_arr)
            
            # NumPy reference: fft + fftshift
            expected = np.fft.fftshift(np.fft.fft(input_arr, norm='backward'))
            
            if compare_arrays(result, expected, test_name, tolerance=1e-9):
                passed += 1
        except Exception as e:
            print(f"✗ {test_name}: EXCEPTION: {e}")
    
    print(f"\nResult: {passed}/{total} passed")
    return passed, total


def test_orthonormal():
    """Test FFT with orthonormal normalization"""
    print("\n" + "="*70)
    print("TEST: FFT with Orthonormal Normalization (NORM_ORTHO)")
    print("="*70)
    
    passed = 0
    total = 0
    
    test_cases = [
        ("1D simple", np.array([1+0j, 2+0j, 3+0j, 4+0j])),
        ("1D 8-element", np.arange(1, 9, dtype=np.complex128)),
    ]
    
    for test_name, input_arr in test_cases:
        total += 1
        try:
            result = test.test_fft1_ortho(input_arr)
            expected = np.fft.fft(input_arr, norm='ortho')
            
            if compare_arrays(result, expected, test_name, tolerance=1e-9):
                passed += 1
        except Exception as e:
            print(f"✗ {test_name}: EXCEPTION: {e}")
    
    print(f"\nResult: {passed}/{total} passed")
    return passed, total


def test_symmetry():
    """Test FFT symmetry properties for real inputs"""
    print("\n" + "="*70)
    print("TEST: FFT Symmetry Properties (Real Inputs)")
    print("="*70)
    
    passed = 0
    total = 0
    
    # For real inputs, FFT should have Hermitian symmetry: X[N-k] = conj(X[k])
    real_input = np.array([1, 2, 3, 4, 5, 6, 7, 8], dtype=np.complex128)
    
    total += 1
    try:
        result = test.test_fft1_forward(real_input)
        expected = np.fft.fft(real_input)
        
        # Check Hermitian symmetry
        N = len(result)
        symmetric = True
        max_sym_error = 0
        for k in range(1, N // 2):
            error = np.abs(result[N - k] - np.conj(result[k]))
            max_sym_error = max(max_sym_error, error)
            if error > 1e-9:
                symmetric = False
        
        if symmetric and compare_arrays(result, expected, "Hermitian symmetry", tolerance=1e-10):
            passed += 1
            print(f"    Symmetry error: {max_sym_error:.2e} (should be ~0)")
    except Exception as e:
        print(f"✗ Hermitian symmetry: EXCEPTION: {e}")
    
    print(f"\nResult: {passed}/{total} passed")
    return passed, total


def main():
    print("\n" + "="*70)
    print("COMPREHENSIVE FFT VALIDATION AGAINST NUMPY")
    print("="*70)
    
    total_passed = 0
    total_tests = 0
    
    # Run all tests
    p, t = test_1d_fft()
    total_passed += p
    total_tests += t
    
    p, t = test_1d_ifft()
    total_passed += p
    total_tests += t
    
    p, t = test_2d_fft()
    total_passed += p
    total_tests += t
    
    p, t = test_2d_ifft()
    total_passed += p
    total_tests += t
    
    p, t = test_round_trip()
    total_passed += p
    total_tests += t
    
    p, t = test_fft_with_shift()
    total_passed += p
    total_tests += t
    
    p, t = test_orthonormal()
    total_passed += p
    total_tests += t
    
    p, t = test_symmetry()
    total_passed += p
    total_tests += t
    
    # Summary
    print("\n" + "="*70)
    print("VALIDATION SUMMARY")
    print("="*70)
    print(f"Total: {total_passed}/{total_tests} tests passed")
    
    if total_passed == total_tests:
        print("✓ ALL TESTS PASSED - PocketFFT is numerically accurate!")
        return 0
    else:
        print(f"✗ {total_tests - total_passed} tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
