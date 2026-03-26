"""
benchmark_plans.py
Extensive head-to-head performance benchmark: PocketFFT Plan vs. FFTW Plan.
Tests Powers of 2, Primes, Asymmetric shapes, and Multi-Coil workloads.
"""
import numpy as np
import time
import test_FFT as voxel

# Parameter Grid: (Name, Shape, Transform Axes, Iterations)
TEST_CONFIGS = [
    # --- Powers of 2 (The Fast Path) ---
    ("1D Po2",          (2**16,),                 [0],       1000),
    ("2D Po2",          (1024, 1024),             [0, 1],    100),
    ("3D Po2",          (128, 128, 128),          [0, 1, 2], 20),

    # --- Prime Numbers (The Worst Case / Bluestein's Alg) ---
    ("1D Prime",        (65537,),                 [0],       500),
    ("2D Prime",        (1013, 1013),             [0, 1],    20),
    ("3D Prime",        (61, 61, 61),             [0, 1, 2], 10),

    # --- Highly Composite (Multiples of 2, 3, 5) ---
    ("2D Composite",    (1080, 1080),             [0, 1],    50),
    ("3D Composite",    (120, 120, 120),          [0, 1, 2], 20),

    # --- Highly Asymmetric (Extreme Aspect Ratios) ---
    ("2D Skinny",       (16384, 16),              [0, 1],    100),
    ("3D Thick Slice",  (512, 512, 8),            [0, 1, 2], 20),

    # --- Mixed Parity / Boundary Cases ---
    ("3D Mixed Parity", (128, 127, 129),          [0, 1, 2], 20),

    # --- Batched Multi-Coil Workloads ---
    ("2D Batched Coil", (32, 256, 256),           [1, 2],    50),
    ("3D Batched Coil", (16, 128, 128, 64),       [1, 2, 3], 10),
]

def run_plan_benchmarks():
    print("=========================================================================================================")
    print("                             POCKETFFT PLAN vs FFTW PLAN (Extensive Suite)                               ")
    print("=========================================================================================================")
    
    # Updated Header to include Shape and Axes
    header = f"{'Test Name':<18} | {'Grid Shape':<20} | {'Axes':<10} | {'PocketFFT Plan':<16} | {'FFTW Plan':<12} | {'Speedup':<8}"
    print(header)
    print("-" * 105)
    
    for name, shape, axes, iters in TEST_CONFIGS:
        # Generate random complex double precision data
        data = np.random.rand(*shape) + 1j * np.random.rand(*shape)
        
        # Initialize Both Plans
        plan_pkt = voxel.FFTPlan(shape, axes)
        plan_fftw = voxel.FFTWPlan(shape, axes)
        
        # ==========================================
        # 1. Benchmark PocketFFT Plan
        # ==========================================
        v_data_pkt = data.copy()
        plan_pkt.ImageToKspace(v_data_pkt, True) # Warmup
        v_data_pkt[:] = data[:] 
        
        t0 = time.perf_counter()
        for _ in range(iters):
            plan_pkt.ImageToKspace(v_data_pkt, True)
        t_pkt_plan = (time.perf_counter() - t0) * 1000 / iters

        # ==========================================
        # 2. Benchmark FFTW Plan
        # ==========================================
        v_data_fftw = data.copy()
        plan_fftw.ImageToKspace(v_data_fftw, True) # Warmup
        v_data_fftw[:] = data[:] 
        
        t0 = time.perf_counter()
        for _ in range(iters):
            plan_fftw.ImageToKspace(v_data_fftw, True)
        t_fftw_plan = (time.perf_counter() - t0) * 1000 / iters
        
        # Calculate Speedup ( > 1.0 means PocketFFT is faster )
        speedup = t_fftw_plan / t_pkt_plan
        
        # Format shape and axes for clean printing
        shape_str = str(shape).replace(" ", "")
        axes_str = str(axes).replace(" ", "")
        
        print(f"{name:<18} | {shape_str:<20} | {axes_str:<10} | {t_pkt_plan:>13.2f} ms | {t_fftw_plan:>9.2f} ms | {speedup:>7.2f}x")
        
    print("=========================================================================================================\n")

if __name__ == "__main__":
    run_plan_benchmarks()