# Section 1: Why Voxel? Architecture Overview

## 1.1 The Problem: The "Missing Middle" in Scientific Computing

Scientists and engineers working in computational imaging and non-Cartesian reconstruction face a strict dilemma. Python is productive but too slow for massive data gridding and iterative solvers. C++ is blazingly fast, but bridging it with Python often results in memory-copy bottlenecks.

While excellent general-purpose C++ array libraries already exist—such as **Boost.MultiArray**, **xtensor**, and **NumCpp**—they are often "over-engineered" for abstract mathematics and "under-optimized" for the specific hardware bottlenecks of medical imaging. These generic libraries default to safe, standard memory alignments, rely on heavy template metaprogramming, and usually treat Fourier transforms as external, multi-pass plugins.

`Voxel` was built to fill this missing middle. It acts as a **NumPy-aware bridge between Python and C++**, stripping away generic bloat in favor of aggressive, hardware-level optimizations tuned for massive, multi-coil array processing. Your Python scripts stay simple; your C++ code runs at bare-metal machine speed.

## 1.2 What is Voxel? (And Why Not Just Use other opern-source library?)

Voxel is a lightweight, zero-dependency multi-dimensional array engine. It was developed from the ground up because existing libraries could not provide the compound speedups required by advanced reconstruction frameworks without hitting memory-bandwidth walls. 

Here is exactly why Voxel outperforms general-purpose alternatives in computational imaging:

* 🚀 **Fused Fourier Domain Centering:** Generic libraries require three separate memory passes for a centered FFT (`fftshift` → `FFT` → `ifftshift`). Voxel implements a fused $N$-dimensional parity mask directly into the L1 cache during the FFT execution. This eliminates two full memory-bandwidth passes, resulting in a massive speedup for iterative solvers.
* 🚀 **Strict SIMD Hardware Alignment:** While other libraries use standard 16- or 32-byte alignment, Voxel enforces **strict 64-byte alignment** across the entire engine. This ensures every array is perfectly aligned for AVX-512 (Intel/AMD) and NEON (Apple Silicon) registers, allowing the compiler to use ultra-fast `vmovapd` instructions instead of unaligned equivalents.
* 🚀 **GPL-Free, Header-Only Portability:** High-performance libraries typically rely on FFTW, which suffers from restrictive GPL licensing and notorious compilation issues on modern Apple Silicon Macs. Voxel natively integrates **PocketFFT**, providing a BSD-licensed, thread-safe, and header-only backend that compiles seamlessly anywhere.
* 🚀 **Native "MRI-First" Slicing:** Voxel’s slicing engine natively understands non-contiguous multi-coil data. When extracting strided views (e.g., flipping a phase-encoding axis), Voxel uses a custom OpenMP-vectorized unroller that outperforms the standard `std::copy` logic used by generic wrappers.
* 🚀 **Zero-Copy Python Bridge:** Pass massive NumPy volumes directly into C++ functions. Slicing, reshaping, and transposing return lightweight views that share the exact same `std::shared_ptr` as Python, eliminating conversion overhead.

**Who Should Use It:**
- Computational imaging researchers (MRI, CT, microscopy)
- Developers building iterative reconstruction algorithms requiring extreme speed
- Teams needing a cleanly licensable (GPL-free) compute engine for commercial or academic software
- Anyone hitting memory-bandwidth walls with standard NumPy or generic C++ wrappers

---

## 1.3 Architecture at a Glance

```
┌─────────────────────────────────────┐
│  Your Python Code                   │
│  (NumPy arrays, math, plotting)    │
└──────────────┬──────────────────────┘
               │ Pybind11 (zero-copy bridge)
               ▼
┌─────────────────────────────────────┐
│  Voxel::Array<T>                 │
│  (Your C++ algorithms)              │
└──────────────┬──────────────────────┘
               │
         Efficient Backends:
         - PocketFFT (FFT transforms, BSD-licensed)
         - Eigen (Linear Algebra)
         - Wavelet (DWT)
               │
               ▼
        Optimized Memory Management
        (Automatic, safe, contiguous)
```

**The Key Idea:** One shared memory block, multiple views. Copies are avoided where layout and dtype already match. This design keeps your algorithms fast without sacrificing safety or ease of use.

---

## 1.4 Memory Management: Shared Ownership

All arrays use C++ smart pointers (`std::shared_ptr`) to manage memory:

```cpp
Array<double> original(256, 256);                      // Allocates memory once
auto roi = original.slice(S(0, 100), S(0, 100));      // View—no new memory!
auto copy = original.copy();                           // Actually copies data

// Memory auto-cleans when all arrays go out of scope ✓
```

**Benefits:**
- No manual `delete` or `free` calls
- Safe in threaded code
- Automatic cleanup even if exceptions occur
- Python garbage collector stays in sync

---

## 1.5 Understanding Views vs. Copies

This is the most important concept:

| Operation | Result | Copy? | Use Case |
|-----------|--------|-------|----------|
| `.slice()` | Lightweight view | ❌ No | Extract a region |
| `.reshape()` | Reinterpret shape | ❌ No, if input is contiguous | Change layout interpretation |
| `.transpose()` | Swap dimensions | ❌ No | Rotate data |
| `.copy()` | New independent array | ✅ Yes | Preserve original data |
| `Array(shape)` | New allocated array | ✅ Yes | Create workspace |

**Golden Rule:** Operations are views unless you explicitly call `.copy()`. This keeps memory usage low.

---

## 1.6 How Array Indexing Works (Strides)

Instead of complex multi-dimensional index calculation, `Voxel` uses **strides**:

```cpp
Array<double> A(20, 256, 256);  // 3D image with 20 slices

// Stride layout in memory (for row-major, in elements not bytes):
// stride[0] = 256*256  (jump to next slice)
// stride[1] = 256      (jump to next row)
// stride[2] = 1        (one element)

// Element access: A(i,j,k) = memory[i*stride[0] + j*stride[1] + k*stride[2]]
```

**Why This Matters:**
- Slicing and transposing just change strides—no data movement
- Direct element access: `A(5, 100, 200)` is O(1)
- Non-contiguous views possible (but slower for PocketFFT/Eigen)

---

## 1.7 The Three Processing Backends

`Voxel` integrates three key backends:

**PocketFFT (Fast Fourier Transform)** - Multi-dimensional FFT transforms with zero-allocation shifting via alternating sign masks and one-off transform execution.

**Eigen (Linear Algebra)** - Matrix operations: SVD, QR, Cholesky decomposition, matrix multiplication, PCA.

**OpenMP / SIMD pragmas** - Used in parts of the build and in several low-level kernels for vectorization-oriented loops.

These backends work best on contiguous arrays and integrate with Voxel's view/copy semantics.

---

## 1.8 OpenMP Backend & Multi-Threaded Execution

`Voxel` is built with **OpenMP support**, but the current codebase uses it primarily for SIMD pragmas inside library kernels and for user-authored `#pragma omp parallel for` loops.

**What the library does today:**
- Many contiguous hot loops use `#pragma omp simd` for vectorization
- Some reductions and norm-style kernels use SIMD reductions, but not automatic multicore threading
- PocketFFT and Eigen are used as compute backends, with automatic internal optimization

**User Control:**
- Set thread count via environment variable: `OMP_NUM_THREADS=8`
- For user code, `#pragma omp parallel for` on the outermost loop is the intended multicore pattern
- Nested parallel regions are usually a bad idea unless you explicitly know the runtime settings you want

**Why This Choice:**
- Portable across Linux, macOS, Windows
- Lets the project expose SIMD-friendly kernels while still allowing explicit multicore loops in user code
- Keeps the library usable even when callers want to control threading policy themselves

For detailed usage patterns (static vs. dynamic scheduling, batch processing), see Section 2.10 in Data Structures.

---

## 1.9 SIMD Vectorization & CPU Optimization

Modern CPUs use **SIMD (Single Instruction, Multiple Data)** to process 4, 8, or 16 array elements simultaneously:

**Why This Matters:**
- Operations on contiguous arrays are the best candidates for compiler vectorization and SIMD-friendly backend access
- Non-contiguous arrays (e.g., from slicing or striding) usually lose the fast SIMD path
- Backend libraries perform best on contiguous inputs; wrappers may copy non-contiguous inputs internally when needed

**Voxel's SIMD Strategy:**
- Automatic memory alignment is used for the library's main numeric allocation paths
- Contiguity checking: `.contiguous()` ensures data layout supports vectorization
- Transparent to users: You don't manage alignment—just use `.contiguous()` before heavy loops

This is why the Data Structures section emphasizes contiguity: SIMD is performance multiplier.

---

## 1.9 Key Design Choices & Trade-Offs

| Choice | Why | Trade-Off |
|--------|-----|-----------|
| Row-Major layout | Matches NumPy | Column-major libraries must transpose |
| PocketFFT header-only | Zero external dependencies | No linking required |
| In-place operations | Zero allocation | State changes (user must be careful) |
| Smart pointers | Automatic cleanup | Small memory overhead per array |
| Pre-allocated output | Zero allocation | User must know output size |
| OpenMP support | SIMD pragmas in library kernels plus explicit user parallel loops | Multicore speedups are workload-dependent and not automatic everywhere |
| SIMD-ready layout | Better vectorization opportunities on contiguous data | Requires contiguity for the fast path |

---

## 1.10 Thread Safety & Memory

- **Array construction/destruction:** Safe in multiple threads
- **Reading arrays:** Fully thread-safe (const operations)
- **Modifying arrays:** Not thread-safe (use locks if needed)
- **FFT transforms:** Automatic optimization with zero manual planning overhead
- **FFT execution:** Safe usage still depends on not racing on the same mutable arrays from multiple threads
- **OpenMP parallelism:** Safe when the user parallelizes independent work correctly; synchronization is still the caller's responsibility

## Advanced Topics (For Curious Minds)

## A.1 SIMD Vectorization & CPU Architecture (Expanded)

Modern CPUs use **SIMD (Single Instruction, Multiple Data)** set extensions to process multiple array elements in parallel hardware instructions.

**SIMD Set Examples:**
- **AVX2:** Process 4 doubles or 8 floats per instruction (Intel/AMD)
- **AVX-512:** Process 8 doubles or 16 floats per instruction (high-end CPUs)
- **ARM NEON:** Process 2 doubles or 4 floats per instruction (ARM processors)

**Why Data Alignment Matters:**
SIMD instructions require contiguous, aligned data:
```cpp
Array<double> A(1000, 1000);  // Allocated with 32-byte alignment
auto B = A.slice(...);         // May lose alignment due to striding
B += 1.0;                       // SIMD disabled—slow!
auto C = B.contiguous();       // Realigned
C += 1.0;                       // SIMD enabled—fast!
```

**Performance Impact:**
- Contiguous arrays: Best chance of hitting the SIMD fast path
- Strided arrays: Often slower because vectorization and cache locality are worse
- PocketFFT/Eigen: Work best on contiguous data; wrappers may insert copies for non-contiguous inputs

**Voxel's Role:** Memory allocator ensures cache-line alignment automatically. Users just need `.contiguous()` before heavy loops on sliced/transposed data.

## A.2 OpenMP Memory & Thread Scaling

OpenMP can distribute loop iterations across CPU cores when you write parallel regions explicitly:

**How It Works:**
```cpp
#pragma omp parallel for
for (int i = 0; i < N; ++i) {
    C[i] = A[i] + B[i];  // Each core runs subset of loop
}
```

**Memory Bandwidth Consideration:**
Modern CPUs can process data faster than RAM provides it. With 16 cores all accessing memory, contention becomes the bottleneck. Contiguous arrays maximize cache efficiency—random-access patterns (from striding) saturate the memory bus quickly.

**Best Practices:**
- Use `.contiguous()` before performance-critical loops that assume linear memory access
- Outermost loop parallelism only unless you intentionally configure nested OpenMP behavior
- OpenMP scheduling: static (predictable), dynamic (load-balanced), guided (hybrid)

See Section 2.10 in Data Structures for detailed scheduling strategies.

## A.3 OpenMP + SIMD Synergy

The combination of OpenMP (multi-core) + SIMD (vector) gives compound speedup:

**Example: Element-wise multiplication**
```cpp
Array<double> A(10000, 10000);
auto B = A * 2.0;  // Internally:
                    // - SIMD can accelerate contiguous elementwise work
                    // - Explicit outer-loop OpenMP can add multicore scaling
                    // - Actual speedup depends on compiler, CPU, memory bandwidth, and workload
```

This is why `Voxel` prioritizes:
1. **Contiguity:** Unlocks SIMD
2. **Multi-core:** Explicit OpenMP loops can spread work across cores
3. **Aligned allocation:** Ensures SIMD-ready data layout

## A.4 Why Row-Major Instead of Column-Major?

NumPy uses C-contiguous (row-major) layout by default. If `Voxel` used column-major (like Fortran/MATLAB), every Python ↔ C++ transfer would need a transpose. We chose NumPy compatibility over Fortran library ease.

**Impact on SIMD:** Row-major also aligns better with modern CPU cache architecture, which prefers sequential memory access.

## A.5 Memory Efficiency: Shared Pointers

When you slice an array, the new array shares the same `std::shared_ptr<T>` with the original. Multiple slices can reference the same memory block. Memory is freed only when the last reference goes out of scope.

**Example:**
```cpp
Array<double> A(1000, 1000);  // 8MB allocated
auto B = A.slice(...);        // B points to same 8MB
auto C = A.slice(...);        // C also points to same 8MB
// Memory freed only when ALL of A, B, C are destroyed ✓
```


