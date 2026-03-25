#!/usr/bin/env python3
"""
Simple diagnostic test to understand fftshift bug
"""

import numpy as np
import test

# Simple test case
input_arr = np.array([1+0j, 2+0j, 3+0j, 4+0j], dtype=np.complex128)

print("Input:", input_arr)
print()

# Get raw FFT (no shift)
fft_result = test.test_fft1_forward(input_arr)
print("FFT (no shift):", fft_result)
print()

# Get NumPy's FFT
numpy_fft = np.fft.fft(input_arr)
print("NumPy FFT:", numpy_fft)
print("Match?", np.allclose(fft_result, numpy_fft))
print()

# Now get shifted version
fft_shifted = test.test_fft1_with_shift(input_arr)
print("FFT (with shift):", fft_shifted)
print()

# NumPy's expected shift
numpy_shifted = np.fft.fftshift(np.fft.fft(input_arr))
print("NumPy shifted:   ", numpy_shifted)
print("Match?", np.allclose(fft_shifted, numpy_shifted))
print()

# Manual fftshift on raw PocketFFT result
manual_shift = np.fft.fftshift(fft_result)
print("Manual fftshift of PocketFFT:", manual_shift)
print("Match expected?", np.allclose(manual_shift, numpy_shifted))
print()

# Check the alternating sign issue
print("Debugging alternating signs:")
sign_applied = fft_result * np.array([1 if i % 2 == 0 else -1 for i in range(len(fft_result))], dtype=complex)
print("After alternating sign mask:", sign_applied)
manual_shift2 = np.fft.fftshift(sign_applied)
print("Then shifted:", manual_shift2)
