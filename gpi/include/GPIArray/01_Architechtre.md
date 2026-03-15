# Section 1: Why GPIArray? Architecture Overview

## 1.1 What is GPIArray?

`GPIArray` is a **zero-copy bridge between Python and C++** for scientific computing. Write your algorithms in fast C++, call them from Python like normal functions, and pass NumPy arrays without copying or reformatting.

**Key Benefits for Scientists:**
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

**The Key Idea:** One shared memory block, multiple views. No copying needed.

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
| `.reshape()` | Reinterpret shape | ❌ No | Change layout interpretation |
| `.transpose()` | Swap dimensions | ❌ No | Rotate data |
| `.copy()` | New independent array | ✅ Yes | Preserve original data |
| `Array(shape)` | New allocated array | ✅ Yes | Create workspace |

**Golden Rule:** Operations are views unless you explicitly call `.copy()`. This keeps memory usage low.

---

## 1.5 How Array Indexing Works (Strides)

Instead of complex multi-dimensional index calculation, `GPIArray` uses **strides**:

```cpp
Array<double> A(20, 256, 256);  // 3D image with 20 slices

// Stride layout in memory (for row-major):
// stride[0] = 256*256*8 bytes (jump to next slice)
// stride[1] = 256*8 bytes     (jump to next row)  
// stride[2] = 8 bytes         (one element)

// Element access: A(i,j,k) = memory[i*stride[0] + j*stride[1] + k*stride[2]]
```

**Why This Matters:**
- Slicing and transposing just change strides—no data movement
- Direct element access: `A(5, 100, 200)` is O(1)
- Non-contiguous views possible (but slower for FFTW/Eigen)

---

## 1.6 The Three Processing Backends

### FFTW (Fast Fourier Transform)
```cpp
// In-place FFT transform on axes {1, 2}
FFTW::fftn(kspace, kspace, FFTW::KspaceToImage, {1, 2});  

// Out-of-place (preserves input)
Array<Complex> result = kspace.empty_like();
FFTW::fftn(kspace, result, FFTW::KspaceToImage, {1, 2});
```

### Eigen (Linear Algebra)
```cpp
// Matrix multiplication
Array<Complex> C(A.shape()[0], B.shape()[1]);
LinAlg::matmul(A, B, C);  // C = A * B

// SVD decomposition
LinAlg::svd(A, U, S, Vh, LinAlg::Thin);
```

### Wavelet (Discrete Wavelet Transform)
```cpp
// 2D DWT with orthonormal filters
Wavelet<double> dwt(256, 256, levels=3, use_d4=true);
dwt.forward_transform(image);  // In-place decomposition
```

---

## 1.7 Thread Safety & Memory

- **Array construction/destruction:** Safe in multiple threads
- **Reading arrays:** Fully thread-safe (const operations)
- **Modifying arrays:** Not thread-safe (use locks if needed)
- **FFT planning:** Automatically protected by global mutex

---

## 1.8 Key Design Choices & Trade-Offs

| Choice | Why | Trade-Off |
|--------|-----|-----------|
| Row-Major layout | Matches NumPy | Column-major libraries must transpose |
| FFTW alignment | Maximum speed | Slightly more memory used |
| In-place operations | Zero allocation | State changes (user must be careful) |
| Smart pointers | Automatic cleanup | Small memory overhead per array |
| Pre-allocated output | Zero allocation | User must know output size |

---

# Advanced Topics (For Curious Minds)

## A.1 Why FFTW Alignment Matters (Optional Reading)

Modern CPUs have SIMD instruction sets (AVX2, AVX-512) that require data at specific byte boundaries. FFTW's custom allocator ensures this automatically. This isn't something users need to worry about—it just happens.

**Bottom line:** Arrays allocated via `Array(shape)` are already optimally aligned for FFT. You don't need to do anything.

## A.2 Why Row-Major Instead of Column-Major?

NumPy uses C-contiguous (row-major) layout by default. If `GPIArray` used column-major (like Fortran/MATLAB), every Python ↔ C++ transfer would need a transpose. We chose NumPy compatibility over Fortran library ease.

## A.3 Memory Efficiency: Shared Pointers

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