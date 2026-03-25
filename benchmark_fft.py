#!/usr/bin/env python3
"""
FFT Performance Benchmark: NumPy vs Voxel::FFT
Compares execution time on various array sizes and dimensions.
"""

import numpy as np
import time
from typing import Tuple, List
import sys

class FFTBenchmark:
    def __init__(self, num_runs=5, warmup=2):
        self.num_runs = num_runs
        self.warmup = warmup
        self.results = []
    
    def measure(self, func, *args, **kwargs) -> float:
        """Measure execution time in milliseconds."""
        # Warmup
        for _ in range(self.warmup):
            func(*args, **kwargs)
        
        # Timed runs
        times = []
        for _ in range(self.num_runs):
            start = time.perf_counter()
            func(*args, **kwargs)
            elapsed = time.perf_counter() - start
            times.append(elapsed * 1000)  # Convert to ms
        
        return np.mean(times)
    
    def benchmark_1d_fft_even(self):
        """Benchmark 1D FFT with even dimension."""
        print("\n" + "="*70)
        print("1D FFT - EVEN DIMENSION")
        print("="*70)
        
        sizes = [256, 512, 1024, 4096, 8192, 16384]
        print(f"{'Size':<10} {'FFT (ms)':<15} {'FFT+shift (ms)':<20} {'Shift overhead':<15}")
        print("-" * 70)
        
        for size in sizes:
            arr = np.random.rand(size) + 1j*np.random.rand(size)
            
            # Pure FFT
            fft_time = self.measure(np.fft.fft, arr)
            
            # FFT + fftshift
            shift_time = self.measure(lambda: np.fft.fftshift(np.fft.fft(arr)))
            
            overhead = ((shift_time - fft_time) / fft_time * 100)
            print(f"{size:<10} {fft_time:<15.4f} {shift_time:<20.4f} {overhead:>6.2f}%")
    
    def benchmark_1d_fft_odd(self):
        """Benchmark 1D FFT with odd dimension."""
        print("\n" + "="*70)
        print("1D FFT - ODD DIMENSION")
        print("="*70)
        
        sizes = [255, 511, 1023, 4095, 8191, 16383]
        print(f"{'Size':<10} {'FFT (ms)':<15} {'FFT+shift (ms)':<20} {'Shift overhead':<15}")
        print("-" * 70)
        
        for size in sizes:
            arr = np.random.rand(size) + 1j*np.random.rand(size)
            
            # Pure FFT
            fft_time = self.measure(np.fft.fft, arr)
            
            # FFT + fftshift
            shift_time = self.measure(lambda: np.fft.fftshift(np.fft.fft(arr)))
            
            overhead = ((shift_time - fft_time) / fft_time * 100)
            print(f"{size:<10} {fft_time:<15.4f} {shift_time:<20.4f} {overhead:>6.2f}%")
    
    def benchmark_2d_fft_even(self):
        """Benchmark 2D FFT with even dimensions."""
        print("\n" + "="*70)
        print("2D FFT - EVEN DIMENSIONS")
        print("="*70)
        
        shapes = [(64, 64), (128, 128), (256, 256), (512, 512)]
        print(f"{'Shape':<20} {'FFT (ms)':<15} {'FFT+shift (ms)':<20} {'Shift overhead':<15}")
        print("-" * 70)
        
        for shape in shapes:
            arr = np.random.rand(*shape) + 1j*np.random.rand(*shape)
            
            # Pure FFT
            fft_time = self.measure(np.fft.fft2, arr)
            
            # FFT + fftshift
            shift_time = self.measure(lambda: np.fft.fftshift(np.fft.fft2(arr)))
            
            overhead = ((shift_time - fft_time) / fft_time * 100)
            print(f"{str(shape):<20} {fft_time:<15.4f} {shift_time:<20.4f} {overhead:>6.2f}%")
    
    def benchmark_2d_fft_odd(self):
        """Benchmark 2D FFT with odd dimensions."""
        print("\n" + "="*70)
        print("2D FFT - ODD DIMENSIONS")
        print("="*70)
        
        shapes = [(63, 63), (127, 127), (255, 255), (511, 511)]
        print(f"{'Shape':<20} {'FFT (ms)':<15} {'FFT+shift (ms)':<20} {'Shift overhead':<15}")
        print("-" * 70)
        
        for shape in shapes:
            arr = np.random.rand(*shape) + 1j*np.random.rand(*shape)
            
            # Pure FFT
            fft_time = self.measure(np.fft.fft2, arr)
            
            # FFT + fftshift
            shift_time = self.measure(lambda: np.fft.fftshift(np.fft.fft2(arr)))
            
            overhead = ((shift_time - fft_time) / fft_time * 100)
            print(f"{str(shape):<20} {fft_time:<15.4f} {shift_time:<20.4f} {overhead:>6.2f}%")
    
    def benchmark_2d_fft_mixed(self):
        """Benchmark 2D FFT with mixed dimensions."""
        print("\n" + "="*70)
        print("2D FFT - MIXED DIMENSIONS (ODD x EVEN, EVEN x ODD)")
        print("="*70)
        
        shapes = [(63, 64), (64, 63), (127, 128), (128, 127), (255, 256), (256, 255)]
        print(f"{'Shape':<20} {'FFT (ms)':<15} {'FFT+shift (ms)':<20} {'Shift overhead':<15}")
        print("-" * 70)
        
        for shape in shapes:
            arr = np.random.rand(*shape) + 1j*np.random.rand(*shape)
            
            # Pure FFT
            fft_time = self.measure(np.fft.fft2, arr)
            
            # FFT + fftshift
            shift_time = self.measure(lambda: np.fft.fftshift(np.fft.fft2(arr)))
            
            overhead = ((shift_time - fft_time) / fft_time * 100)
            print(f"{str(shape):<20} {fft_time:<15.4f} {shift_time:<20.4f} {overhead:>6.2f}%")
    
    def benchmark_3d_fft(self):
        """Benchmark 3D FFT."""
        print("\n" + "="*70)
        print("3D FFT - EVEN DIMENSIONS")
        print("="*70)
        
        shapes = [(32, 32, 32), (64, 64, 64), (128, 64, 64)]
        print(f"{'Shape':<25} {'FFT (ms)':<15} {'FFT+shift (ms)':<20} {'Shift overhead':<15}")
        print("-" * 75)
        
        for shape in shapes:
            arr = np.random.rand(*shape) + 1j*np.random.rand(*shape)
            
            # Pure FFT
            fft_time = self.measure(np.fft.fftn, arr)
            
            # FFT + fftshift
            shift_time = self.measure(lambda: np.fft.fftshift(np.fft.fftn(arr)))
            
            overhead = ((shift_time - fft_time) / fft_time * 100)
            print(f"{str(shape):<25} {fft_time:<15.4f} {shift_time:<20.4f} {overhead:>6.2f}%")
    
    def benchmark_inverse_fft(self):
        """Benchmark inverse FFT with roundtrip."""
        print("\n" + "="*70)
        print("INVERSE FFT - Roundtrip (FFT + shift + ifftshift + IFFT)")
        print("="*70)
        
        sizes = [256, 512, 1024, 4096]
        print(f"{'Size':<10} {'Forward (ms)':<15} {'Inverse (ms)':<15} {'Total (ms)':<15}")
        print("-" * 55)
        
        for size in sizes:
            arr = np.random.rand(size) + 1j*np.random.rand(size)
            
            # Forward
            fwd_time = self.measure(lambda: np.fft.fftshift(np.fft.fft(arr)))
            
            # Roundtrip
            def roundtrip():
                shifted = np.fft.fftshift(np.fft.fft(arr))
                return np.fft.ifft(np.fft.ifftshift(shifted))
            
            total_time = self.measure(roundtrip)
            inv_time = total_time - fwd_time
            
            print(f"{size:<10} {fwd_time:<15.4f} {inv_time:<15.4f} {total_time:<15.4f}")
    
    def run_all(self):
        """Run all benchmarks."""
        print("\n" + "="*70)
        print("FFT PERFORMANCE BENCHMARK - NumPy")
        print("="*70)
        
        self.benchmark_1d_fft_even()
        self.benchmark_1d_fft_odd()
        self.benchmark_2d_fft_even()
        self.benchmark_2d_fft_odd()
        self.benchmark_2d_fft_mixed()
        self.benchmark_3d_fft()
        self.benchmark_inverse_fft()
        
        print("\n" + "="*70)
        print("BENCHMARK COMPLETE")
        print("="*70)
        print("\nNotes:")
        print("- Shift overhead = (FFT+shift - FFT) / FFT * 100%")
        print("- Even dimensions use sign mask (very fast)")
        print("- Odd dimensions use circular roll (slightly slower)")
        print("- All times in milliseconds (lower is better)")
        print("=" * 70 + "\n")

if __name__ == "__main__":
    benchmark = FFTBenchmark(num_runs=5, warmup=2)
    benchmark.run_all()
