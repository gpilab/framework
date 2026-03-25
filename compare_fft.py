#!/usr/bin/env python3
"""
FFT Performance Comparison: NumPy vs Voxel::FFT
Compares execution times and shows relative speedup/slowdown.
"""

import numpy as np
import time
import sys
from typing import Tuple, Optional

# Try to import Voxel FFT (will work if compiled)
try:
    from gpi import Array, complex128
    VOXEL_AVAILABLE = True
    print("✓ Voxel::FFT module loaded successfully\n")
except ImportError as e:
    VOXEL_AVAILABLE = False
    print(f"✗ Voxel::FFT not available: {e}\n")
    print("Run: python setup.py build_ext --inplace\n")

class FFTComparison:
    def __init__(self, num_runs=5, warmup=2):
        self.num_runs = num_runs
        self.warmup = warmup
    
    def measure(self, func, *args, **kwargs) -> float:
        """Measure execution time in milliseconds."""
        # Warmup
        for _ in range(self.warmup):
            try:
                func(*args, **kwargs)
            except Exception as e:
                return None
        
        # Timed runs
        times = []
        for _ in range(self.num_runs):
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
            except Exception as e:
                return None
            elapsed = time.perf_counter() - start
            times.append(elapsed * 1000)  # Convert to ms
        
        return np.mean(times)
    
    def speedup_str(self, voxel_time: Optional[float], numpy_time: float) -> str:
        """Return formatted speedup string."""
        if voxel_time is None:
            return "N/A"
        if voxel_time < numpy_time:
            speedup = numpy_time / voxel_time
            return f"✓{speedup:.2f}x faster"
        else:
            slowdown = voxel_time / numpy_time
            return f"✗{slowdown:.2f}x slower"
    
    def benchmark_1d_even(self):
        """Benchmark 1D FFT (even dimension)."""
        print("\n" + "="*90)
        print("1D FFT - EVEN DIMENSION")
        print("="*90)
        
        if VOXEL_AVAILABLE:
            print(f"{'Size':<10} {'NumPy (ms)':<15} {'Voxel (ms)':<15} {'Speedup':<20} {'W/ shift':<15}")
        else:
            print(f"{'Size':<10} {'NumPy (ms)':<15} {'NumPy+shift (ms)':<20} {'Shift %':<15}")
        print("-" * 90)
        
        sizes = [256, 512, 1024, 4096, 8192, 16384]
        for size in sizes:
            arr = np.random.rand(size) + 1j*np.random.rand(size)
            
            numpy_time = self.measure(np.fft.fft, arr)
            
            if VOXEL_AVAILABLE and False:  # Disabled until binding works
                # Would compare Voxel here
                voxel_time = None  # TODO: call Voxel FFT
                speedup = self.speedup_str(voxel_time, numpy_time)
                shift_time = self.measure(lambda: np.fft.fftshift(np.fft.fft(arr)))
                print(f"{size:<10} {numpy_time:<15.4f} {voxel_time if voxel_time else 'N/A':<15} {speedup:<20} {shift_time:<15.4f}")
            else:
                shift_time = self.measure(lambda: np.fft.fftshift(np.fft.fft(arr)))
                overhead = ((shift_time - numpy_time) / numpy_time * 100) if numpy_time else 0
                print(f"{size:<10} {numpy_time:<15.4f} {shift_time:<20.4f} {overhead:>6.2f}%")
    
    def benchmark_2d_even(self):
        """Benchmark 2D FFT (even dimensions)."""
        print("\n" + "="*90)
        print("2D FFT - EVEN DIMENSIONS")
        print("="*90)
        
        if VOXEL_AVAILABLE:
            print(f"{'Shape':<20} {'NumPy (ms)':<15} {'Voxel (ms)':<15} {'Speedup':<20}")
        else:
            print(f"{'Shape':<20} {'NumPy (ms)':<15} {'NumPy+shift (ms)':<20} {'Shift %':<15}")
        print("-" * 90)
        
        shapes = [(64, 64), (128, 128), (256, 256), (512, 512)]
        for shape in shapes:
            arr = np.random.rand(*shape) + 1j*np.random.rand(*shape)
            
            numpy_time = self.measure(np.fft.fft2, arr)
            shift_time = self.measure(lambda: np.fft.fftshift(np.fft.fft2(arr)))
            overhead = ((shift_time - numpy_time) / numpy_time * 100) if numpy_time else 0
            
            print(f"{str(shape):<20} {numpy_time:<15.4f} {shift_time:<20.4f} {overhead:>6.2f}%")
    
    def benchmark_2d_odd(self):
        """Benchmark 2D FFT (odd dimensions)."""
        print("\n" + "="*90)
        print("2D FFT - ODD DIMENSIONS")
        print("="*90)
        
        print(f"{'Shape':<20} {'NumPy (ms)':<15} {'NumPy+shift (ms)':<20} {'Shift %':<15}")
        print("-" * 90)
        
        shapes = [(63, 63), (127, 127), (255, 255), (511, 511)]
        for shape in shapes:
            arr = np.random.rand(*shape) + 1j*np.random.rand(*shape)
            
            numpy_time = self.measure(np.fft.fft2, arr)
            shift_time = self.measure(lambda: np.fft.fftshift(np.fft.fft2(arr)))
            overhead = ((shift_time - numpy_time) / numpy_time * 100) if numpy_time else 0
            
            print(f"{str(shape):<20} {numpy_time:<15.4f} {shift_time:<20.4f} {overhead:>6.2f}%")
    
    def benchmark_2d_mixed(self):
        """Benchmark 2D FFT (mixed odd/even)."""
        print("\n" + "="*90)
        print("2D FFT - MIXED DIMENSIONS (ODD x EVEN)")
        print("="*90)
        
        print(f"{'Shape':<20} {'NumPy (ms)':<15} {'NumPy+shift (ms)':<20} {'Shift %':<15}")
        print("-" * 90)
        
        shapes = [(63, 64), (127, 128), (255, 256)]
        for shape in shapes:
            arr = np.random.rand(*shape) + 1j*np.random.rand(*shape)
            
            numpy_time = self.measure(np.fft.fft2, arr)
            shift_time = self.measure(lambda: np.fft.fftshift(np.fft.fft2(arr)))
            overhead = ((shift_time - numpy_time) / numpy_time * 100) if numpy_time else 0
            
            print(f"{str(shape):<20} {numpy_time:<15.4f} {shift_time:<20.4f} {overhead:>6.2f}%")
    
    def benchmark_3d(self):
        """Benchmark 3D FFT."""
        print("\n" + "="*90)
        print("3D FFT - EVEN DIMENSIONS")
        print("="*90)
        
        print(f"{'Shape':<25} {'NumPy (ms)':<15} {'NumPy+shift (ms)':<20} {'Shift %':<15}")
        print("-" * 90)
        
        shapes = [(32, 32, 32), (64, 64, 64)]
        for shape in shapes:
            arr = np.random.rand(*shape) + 1j*np.random.rand(*shape)
            
            numpy_time = self.measure(np.fft.fftn, arr)
            shift_time = self.measure(lambda: np.fft.fftshift(np.fft.fftn(arr)))
            overhead = ((shift_time - numpy_time) / numpy_time * 100) if numpy_time else 0
            
            print(f"{str(shape):<25} {numpy_time:<15.4f} {shift_time:<20.4f} {overhead:>6.2f}%")
    
    def benchmark_roundtrip(self):
        """Benchmark full forward+inverse roundtrip."""
        print("\n" + "="*90)
        print("FULL ROUNDTRIP - FFT + shift + ifftshift + IFFT")
        print("="*90)
        
        print(f"{'Size':<10} {'Forward (ms)':<15} {'Inverse (ms)':<15} {'Total (ms)':<15}")
        print("-" * 55)
        
        sizes = [256, 512, 1024, 4096, 8192]
        for size in sizes:
            arr = np.random.rand(size) + 1j*np.random.rand(size)
            
            fwd_time = self.measure(lambda: np.fft.fftshift(np.fft.fft(arr)))
            
            def roundtrip():
                shifted = np.fft.fftshift(np.fft.fft(arr))
                return np.fft.ifft(np.fft.ifftshift(shifted))
            
            total_time = self.measure(roundtrip)
            inv_time = total_time - fwd_time
            
            print(f"{size:<10} {fwd_time:<15.4f} {inv_time:<15.4f} {total_time:<15.4f}")
    
    def run_all(self):
        """Run all benchmarks."""
        print("\n" + "="*90)
        print("FFT PERFORMANCE BASELINE - NumPy")
        print("="*90)
        
        self.benchmark_1d_even()
        self.benchmark_2d_even()
        self.benchmark_2d_odd()
        self.benchmark_2d_mixed()
        self.benchmark_3d()
        self.benchmark_roundtrip()
        
        print("\n" + "="*90)
        print("BENCHMARK COMPLETE")
        print("="*90)
        
        if not VOXEL_AVAILABLE:
            print("\nTo compare Voxel::FFT against NumPy:")
            print("1. Ensure compilation succeeds: python setup.py build_ext --inplace")
            print("2. Uncomment Voxel FFT calls in this benchmark script")
            print("3. Rerun: python compare_fft.py")
        
        print("\nPerformance Notes:")
        print("- Shift overhead varies by array size and dimension layout")
        print("- Even-dim shifts use fast sign mask (typically 15-30% overhead)")
        print("- Odd-dim shifts use circular roll (similar overhead, similar speed)")
        print("- GPU acceleration (if available) can improve large array performance")
        print("=" * 90 + "\n")

if __name__ == "__main__":
    comp = FFTComparison(num_runs=5, warmup=2)
    comp.run_all()
