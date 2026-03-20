# Section 1: Why GPIArray? Architecture Overview

## 1.1 What is GPIArray?

`GPIArray` is a **NumPy-aware bridge between Python and C++** for scientific computing. Write your algorithms in C++, call them from Python like normal functions, and preserve array shape and stride metadata without forcing a row-major copy.

**Key Benefits:**
- ✅ **Seamless Python Integration:** Pass NumPy arrays directly to C++ functions—no conversion overhead
- ✅ **Automatic Memory Management:** No manual allocation/deallocation; memory cleans itself up
- ✅ **Support for N-Dimensional Data:** 0D scalars to 10D tensors (and beyond)
- ✅ **Built-In FFT & Linear Algebra:** FFTW and Eigen backends included
- ✅ **Zero-Copy Views:** Slicing, reshaping, and transposing returns lightweight views, not copies

**Who Should Use It:**
- Computational imaging researchers (MRI, CT, microscopy)
- Iterative reconstruction algorithms
- Signal processing pipelines requiring speed
- Anyone doing NumPy + performance-critical C++

---

## 1.2 Architecture at a Glance

```
┌─────────────────────────────────────┐
│  Your Python Code                   │
│  (NumPy arrays, math, plotting)    │
└──────────────┬──────────────────────┘
               │ Pybind11 (zero-copy bridge)
               ▼
┌─────────────────────────────────────┐
│  GPIArray::Array<T>                 │
│  (Your C++ algorithms)              │
└──────────────┬──────────────────────┘
               │
         Efficient Backends:
         - FFTW (FFT transforms)
         - Eigen (Linear Algebra)
         - Wavelet (DWT)
               │
               ▼
        Optimized Memory Management
        (Automatic, safe, contiguous)
```

**The Key Idea:** One shared memory block, multiple views. Copies are avoided where layout and dtype already match.

---

## 1.3 Memory Management: Shared Ownership

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

## 1.4 Understanding Views vs. Copies

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

## 1.5 How Array Indexing Works (Strides)

Instead of complex multi-dimensional index calculation, `GPIArray` uses **strides**:

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
- Non-contiguous views possible (but slower for FFTW/Eigen)

---

## 1.6 The Three Processing Backends

`GPIArray` integrates three key backends:

**FFTW (Fast Fourier Transform)** - Multi-dimensional FFT transforms with cached plan objects and one-off wrappers.

**Eigen (Linear Algebra)** - Matrix operations: SVD, QR, Cholesky decomposition, matrix multiplication, PCA.

**OpenMP / SIMD pragmas** - Used in parts of the build and in several low-level kernels for vectorization-oriented loops.

These backends work best on contiguous arrays and integrate with GPIArray's view/copy semantics.

---

## 1.7 OpenMP Backend & Multi-Threaded Execution

`GPIArray` is built with **OpenMP support**, but the current codebase uses it primarily for SIMD pragmas inside library kernels and for user-authored `#pragma omp parallel for` loops.

**What the library does today:**
- Many contiguous hot loops use `#pragma omp simd` for vectorization
- Some reductions and norm-style kernels use SIMD reductions, but not automatic multicore threading
- FFTW and Eigen are used as compute backends, but this wrapper does not explicitly enable FFTW threading or configure Eigen thread counts

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

## 1.8 SIMD Vectorization & CPU Optimization

Modern CPUs use **SIMD (Single Instruction, Multiple Data)** to process 4, 8, or 16 array elements simultaneously:

**Why This Matters:**
- Operations on contiguous arrays are the best candidates for compiler vectorization and SIMD-friendly backend access
- Non-contiguous arrays (e.g., from slicing or striding) usually lose the fast SIMD path
- Backend libraries perform best on contiguous inputs; wrappers may copy non-contiguous inputs internally when needed

**GPIArray's SIMD Strategy:**
- Automatic memory alignment is used for the library's main numeric allocation paths
- Contiguity checking: `.contiguous()` ensures data layout supports vectorization
- Transparent to users: You don't manage alignment—just use `.contiguous()` before heavy loops

This is why the Data Structures section emphasizes contiguity: SIMD is performance multiplier.

---

## 1.9 Key Design Choices & Trade-Offs

| Choice | Why | Trade-Off |
|--------|-----|-----------|
| Row-Major layout | Matches NumPy | Column-major libraries must transpose |
| FFTW alignment | Maximum speed | Slightly more memory used |
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
- **FFT plan creation/destruction:** Automatically protected by a global mutex
- **FFT execution:** Safe usage still depends on not racing on the same mutable arrays from multiple threads
- **OpenMP parallelism:** Safe when the user parallelizes independent work correctly; synchronization is still the caller's responsibility

# Advanced Topics (For Curious Minds)

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
- FFTW/Eigen: Work best on contiguous data; wrappers may insert copies for non-contiguous inputs

**GPIArray's Role:** Memory allocator ensures cache-line alignment automatically. Users just need `.contiguous()` before heavy loops on sliced/transposed data.

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

This is why `GPIArray` prioritizes:
1. **Contiguity:** Unlocks SIMD
2. **Multi-core:** Explicit OpenMP loops can spread work across cores
3. **Aligned allocation:** Ensures SIMD-ready data layout

## A.4 Why Row-Major Instead of Column-Major?

NumPy uses C-contiguous (row-major) layout by default. If `GPIArray` used column-major (like Fortran/MATLAB), every Python ↔ C++ transfer would need a transpose. We chose NumPy compatibility over Fortran library ease.

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

---

# Section 2: Core Data Structures (see next chapter)
# Section 3-7: (See subsequent documentation files)
