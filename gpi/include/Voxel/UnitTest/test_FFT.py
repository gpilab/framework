"""
benchmark_fft.py
Comprehensive testing and benchmarking of Voxel::FFT vs NumPy.
Includes Even, Odd, 1D, 2D, 3D, and Batched (Multi-coil) tests.
"""
import numpy as np
import time
import test_FFT as voxel

# Parameter Grid: (Name, Shape, Transform Axes, Iterations)
TEST_CONFIGS = [
    ("1D Even",         (16384,),              [0],       100),
    ("1D Odd",          (16383,),              [0],       100),
    ("2D Even",         (1024, 1024),          [0, 1],    20),
    ("2D Odd",          (1023, 1023),          [0, 1],    20),
    ("3D Even",         (64, 64, 64),          [0, 1, 2], 20),
    ("3D Odd",          (63, 63, 63),          [0, 1, 2], 20),
    ("Batched 3D Even", (8, 64, 64, 64),       [1, 2, 3], 10), # e.g. 8 coils
    ("Batched 3D Odd",  (8, 63, 63, 63),       [1, 2, 3], 10),
]

def numpy_pipeline(arr, axes):
    """NumPy's equivalent shifted forward transform."""
    # NumPy requires 3 distinct memory allocations per iteration
    tmp = np.fft.ifftshift(arr, axes=axes)
    tmp = np.fft.fftn(tmp, axes=axes)
    return np.fft.fftshift(tmp, axes=axes)

def verify_correctness():
    print("===============================================================")
    print("               PHASE 1: CORRECTNESS VALIDATION                 ")
    print("===============================================================")
    
    for name, shape, axes, _ in TEST_CONFIGS:
        # Generate random complex data
        data = np.random.rand(*shape) + 1j * np.random.rand(*shape)
        
        # NumPy Baseline
        n_out = numpy_pipeline(data, axes)
        
        # Voxel One-Off
        v_out = voxel.fftn(data, voxel.TransformDir.Forward, axes, True)
        
        # Voxel FFTPlan (In-Place)
        plan = voxel.FFTPlan(shape, axes)
        v_plan_data = data.copy()
        plan.ImageToKspace(v_plan_data, True)

        # Asserts
        one_off_pass = np.allclose(n_out, v_out)
        plan_pass = np.allclose(n_out, v_plan_data)
        
        status = "✅ PASS" if (one_off_pass and plan_pass) else "❌ FAIL"
        print(f"[{status}] {name:<16} | Shape: {str(shape):<15}")
        
        if not (one_off_pass and plan_pass):
            raise RuntimeError(f"Math validation failed on {name}. Aborting benchmark.")
            
    print("All mathematical validations passed. Proceeding to benchmarks.\n")

def run_benchmarks():
    print("===============================================================")
    print("               PHASE 2: PERFORMANCE BENCHMARK                  ")
    print("===============================================================")
    print(f"{'Test Name':<16} | {'NumPy':<10} | {'One-Off':<10} | {'FFTPlan':<10} | {'Speedup':<10}")
    print("-" * 70)
    
    for name, shape, axes, iters in TEST_CONFIGS:
        data = np.random.rand(*shape) + 1j * np.random.rand(*shape)
        
        # Pre-allocate for Plan
        plan = voxel.FFTPlan(shape, axes)
        v_data_plan = data.copy()
        
        # 1. Benchmark NumPy
        t0 = time.perf_counter()
        for _ in range(iters):
            _ = numpy_pipeline(data, axes)
        t_np = (time.perf_counter() - t0) * 1000 / iters
        
        # 2. Benchmark Voxel One-Off (Simulates wrapper overhead)
        t0 = time.perf_counter()
        for _ in range(iters):
            _ = voxel.fftn(data, voxel.TransformDir.Forward, axes, True)
        t_one = (time.perf_counter() - t0) * 1000 / iters
        
        # 3. Benchmark Voxel FFTPlan (Hot Loop SIMD/Zero-alloc)
        t0 = time.perf_counter()
        for _ in range(iters):
            plan.ImageToKspace(v_data_plan, True)
        t_plan = (time.perf_counter() - t0) * 1000 / iters
        
        speedup = t_np / t_plan
        
        print(f"{name:<16} | {t_np:>7.2f} ms | {t_one:>7.2f} ms | {t_plan:>7.2f} ms | {speedup:>7.2f}x")
        
    print("===============================================================\n")

if __name__ == "__main__":
    verify_correctness()
    run_benchmarks()