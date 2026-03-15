# Section 5: Python Integration (Pybind11)

Call fast C++ algorithms directly from Python with **zero data copying**. NumPy arrays are automatically mapped to `GPIArray::Array<T>` in-place.

## 5.0 Quick Start (30 seconds)

### 1. Write C++ with GPIArray

```cpp
#include "GPIArray/GPIArray.hpp"
using namespace GPIArray;

// Your algorithm takes Array<T>, not Python objects
Array<Complex> my_algorithm(const Array<Complex>& input) {
    Array<Complex> output = input.copy();
    output *= 2.0;  // Any GPIArray operation
    return output;
}

// Bind to Python using one line
PYBIND11_MODULE(MyModule, m) {
    m.def("my_algorithm", &my_algorithm);
}
```

### 2. Build with gpi_make

```bash
cd MyModule
gpi_make .
```

### 3. Call from Python

```python
import numpy as np
import MyModule

# Create NumPy array
data = np.random.rand(256, 256).astype(complex)

# Call C++ directly—array is NOT copied!
result = MyModule.my_algorithm(data)
```

So far, **no Python data structures, no conversion overhead, zero copies**.

---

## 5.1 How It Works: The Type Caster Magic

`GPIArray.hpp` contains a custom Pybind11 `type_caster` that:

1. **Accepts Python objects:** Pybind11 receives `numpy.ndarray` from Python
2. **Maps memory in-place:** No data copying. The NumPy buffer pointer becomes your `Array<T>` data pointer
3. **Returns C++ arrays:** Your returned `Array<T>` automatically wraps back into a NumPy array

Because of this, you write **pure C++** (`Array<T>` everywhere) and the type caster handles Python ↔ C++ conversion silently.

```
┌──────────────────┐
│  NumPy ndarray   │
│  (Python)        │
└────────┬─────────┘
         │ Zero-copy mapping via type_caster
         ▼
┌──────────────────┐
│ Array<T>         │
│ (C++)            │
└──────────────────┘
```

---

## 5.2 What You Can Pass to C++

| Python Type | C++ Receives | Data Copied? | Use Case |
|-------------|-----------|-----------|---|
| `np.ndarray` (any shape) | `Array<T>` | ❌ No | All your algorithms |
| `np.ndarray` | `const Array<T>&` | ❌ No | Read-only inputs |
| Scalar (int/float/complex) | `T` | N/A | Single values |
| `list` of arrays | std::vector<Array<T>> | ❌ No (views) | Batch processing |



```cpp
/**
 * @file MyModule_PYBIND11.cpp
 * @brief Complete Pybind11 integration example for GPIArray.
 */

// =========================================================================
// REQUIRED INCLUDES
// =========================================================================

#include "GPIArray/GPIArray.hpp"      // Contains: pybind11.h, numpy.h, complex.h, stl.h, FFTW, LinAlg
#include <chrono>                      // Benchmarking only (for EXAMPLE 4)

namespace py = pybind11;
using namespace GPIArray;

// =========================================================================
// EXAMPLE 1: Expose a C++ Struct
// =========================================================================

struct ThresholdConfig {
    double lower_bound = 0.0;
    double upper_bound = 1.0;
};

// In Python: Pass config.lower_bound = 0.5 and read config.upper_bound

// =========================================================================
// EXAMPLE 2: Expose a C++ Class with Methods
// =========================================================================

class SignalProcessor {
public:
    SignalProcessor(double gain) : _gain(gain) {}
    
    // Method that takes Array, returns Array
    Array<double> process(const Array<double>& input) {
        return input * _gain;
    }
private:
    double _gain;
};

// In Python: processor = MyModule.SignalProcessor(2.0); result = processor.process(arr)

// =========================================================================
// EXAMPLE 3: In-Place Array Modification (Zero-Copy)
// =========================================================================

// Modifies the NumPy array directly without copying
void scale_array_inline(Array<double>& arr, double factor) {
    if (arr.ndim() == 1) {
        for (uint64_t i = 0; i < arr.dimensions(0); ++i) {
            arr(i) *= factor;
        }
    } 
    else if (arr.ndim() == 2) {
        for (uint64_t i = 0; i < arr.dimensions(0); ++i) {
            for (uint64_t j = 0; j < arr.dimensions(1); ++j) {
                arr(i, j) *= factor;
            }
        }
    } 
    else if (arr.ndim() == 3) {
        for (uint64_t i = 0; i < arr.dimensions(0); ++i) {
            for (uint64_t j = 0; j < arr.dimensions(1); ++j) {
                for (uint64_t k = 0; k < arr.dimensions(2); ++k) {
                    arr(i, j, k) *= factor;
                }
            }
        }
    } 
    else {
        arr.iterate_nd([&](const std::vector<uint64_t>& idx) {
            arr.get_item(idx) *= factor;
        });
    }
}

// =========================================================================
// EXAMPLE 4: Memory Access Patterns and Cache Behavior
// =========================================================================

// Shows three loop orderings: optimal row-major, cache-thrashing reversed, and SIMD vectorized
void benchmark_loop_orders(Array<double>& arr, double factor) {
    if (arr.ndim() != 3) {
        throw std::invalid_argument("Benchmark requires a 3D array.");
    }
    if (!arr.is_contiguous()) {
        throw std::invalid_argument("Benchmark requires a contiguous array.");
    }

    uint64_t dim0 = arr.dimensions(0);
    uint64_t dim1 = arr.dimensions(1);
    uint64_t dim2 = arr.dimensions(2);
    uint64_t total_size = arr.size();

    std::cout << "\n[C++ Internal Benchmark: " << dim0 << "x" << dim1 << "x" << dim2 << " Elements]" << std::endl;

    // 1. Optimal Row-Major Order (Cache Friendly)
    auto start1 = std::chrono::high_resolution_clock::now();
    for (uint64_t i = 0; i < dim0; ++i) {
        for (uint64_t j = 0; j < dim1; ++j) {
            for (uint64_t k = 0; k < dim2; ++k) {
                arr(i, j, k) *= factor; 
            }
        }
    }
    auto end1 = std::chrono::high_resolution_clock::now();
    std::chrono::duration<double, std::milli> time1 = end1 - start1;
    std::cout << "  -> Optimal Nested Loop (Row-Major): " << time1.count() << " ms" << std::endl;

    // 2. Suboptimal Reversed Order (Cache Thrashing)
    auto start2 = std::chrono::high_resolution_clock::now();
    for (uint64_t k = 0; k < dim2; ++k) {
        for (uint64_t j = 0; j < dim1; ++j) {
            for (uint64_t i = 0; i < dim0; ++i) {
                arr(i, j, k) *= factor;
            }
        }
    }
    auto end2 = std::chrono::high_resolution_clock::now();
    std::chrono::duration<double, std::milli> time2 = end2 - start2;
    std::cout << "  -> Suboptimal Nested Loop (Cache Thrashing): " << time2.count() << " ms" << std::endl;

    // 3. Flat SIMD Vectorized Loop (Maximum Performance)
    auto start3 = std::chrono::high_resolution_clock::now();
    double* data = arr.get_data();
    #pragma omp simd
    for (uint64_t idx = 0; idx < total_size; ++idx) {
        data[idx] *= factor;
    }
    auto end3 = std::chrono::high_resolution_clock::now();
    std::chrono::duration<double, std::milli> time3 = end3 - start3;
    std::cout << "  -> Flat SIMD Vectorized Loop: " << time3.count() << " ms\n" << std::endl;
}

// =========================================================================
// EXAMPLE 5: Function Returning a New Array
// =========================================================================

// Create output array from input; pybind11 smart pointers handle memory
Array<double> add_arrays(const Array<double>& a, const Array<double>& b) {
    return a + b;
}

// =========================================================================
// EXAMPLE 6: Function Returning Multiple Values (Tuple)
// =========================================================================

// Extract real and imaginary parts, return both as a Python tuple
std::tuple<Array<double>, Array<double>> split_real_imag(const Array<std::complex<double>>& arr) {
    return std::make_tuple(real(arr), imag(arr));
}

// =========================================================================
// EXAMPLE 7: Template Function with Type Routing
// =========================================================================

// Generic sum computation; pybind11 automatically dispatches based on NumPy dtype
template<typename T>
T compute_sum(const Array<T>& arr) {
    return sum(arr);
}

// =========================================================================
// EXAMPLE 8: FFTW Wrapper Function
// =========================================================================

// Perform FFT transform on specified axes (e.g., {1, 2} for 3D array)
Array<std::complex<double>> compute_fftn(const Array<std::complex<double>>& input, std::vector<uint64_t> axes) {
    Array<std::complex<double>> output = input.empty_like();
    FFTW::fftn(input, output, FFTW::ImageToKspace, axes);
    return output;
}

// =========================================================================
// EXAMPLE 9: Linear Algebra Operations (Matrix Multiply)
// =========================================================================

// Compute C = A @ B using LinAlg backend; shape inference automatic
Array<std::complex<double>> compute_matmul(const Array<std::complex<double>>& A, const Array<std::complex<double>>& B) {
    Array<std::complex<double>> C(A.dimensions(0), B.dimensions(1));
    LinAlg::matmul(A, B, C);
    return C;
}

// =========================================================================
// EXAMPLE 10: Singular Value Decomposition
// =========================================================================

// Decompose A into U, S, Vh; returns tuple for unpacking in Python
std::tuple<Array<std::complex<double>>, Array<double>, Array<std::complex<double>>> 
compute_svd(const Array<std::complex<double>>& A) {
    uint64_t rows = A.dimensions(0);
    uint64_t cols = A.dimensions(1);
    uint64_t diag_size = std::min(rows, cols);

    Array<std::complex<double>> U(rows, diag_size);
    Array<double> S(diag_size);
    Array<std::complex<double>> Vh(diag_size, cols);

    LinAlg::svd(A, U, S, Vh, LinAlg::Thin);
    return std::make_tuple(U, S, Vh);
}

// =========================================================================
// EXAMPLE 11: Principal Component Analysis
// =========================================================================

// Compute principal components and variances from data matrix
std::tuple<Array<std::complex<double>>, Array<double>> 
compute_pca(const Array<std::complex<double>>& data) {
    uint64_t samples = data.dimensions(0);
    uint64_t features = data.dimensions(1);
    uint64_t diag_size = std::min(samples, features);

    Array<std::complex<double>> principal_components(diag_size, features);
    Array<double> variances(diag_size);

    LinAlg::pca(data, principal_components, variances);
    return std::make_tuple(principal_components, variances);
}

// =========================================================================
// Pybind11 Module Definition
// =========================================================================

PYBIND11_MODULE(MyModule, m) {
    m.doc() = "Pybind11 bindings for MyModule using GPIArray.";

    py::class_<ThresholdConfig>(m, "ThresholdConfig")
        .def(py::init<>()) 
        .def_readwrite("lower_bound", &ThresholdConfig::lower_bound)
        .def_readwrite("upper_bound", &ThresholdConfig::upper_bound);

    py::class_<SignalProcessor>(m, "SignalProcessor")
        .def(py::init<double>())
        .def("process", &SignalProcessor::process);

    m.def("scale_array_inline", &scale_array_inline, "Scales an array in-place.");
    m.def("benchmark_loop_orders", &benchmark_loop_orders, "Benchmarks memory access patterns.");
    m.def("add_arrays", &add_arrays, "Adds two arrays and returns a new array.");
    m.def("split_real_imag", &split_real_imag, "Returns a tuple of (real, imag).");

    // Template routing
    m.def("compute_sum", &compute_sum<double>, "Sum of a float64 array.");
    m.def("compute_sum", &compute_sum<float>, "Sum of a float32 array.");
    m.def("compute_sum", &compute_sum<std::complex<double>>, "Sum of a complex128 array.");

    m.def("compute_fftn", &compute_fftn, "Computes N-Dimensional FFT.");
    m.def("compute_matmul", &compute_matmul, "Computes matrix multiplication C = A * B.");
    m.def("compute_svd", &compute_svd, "Computes Thin SVD, returning (U, S, Vh).");
    m.def("compute_pca", &compute_pca, "Computes PCA, returning (PCs, variances).");
}

```

## 5.4 Calling and Verifying from Python

Once `MyModule_PYBIND11.cpp` is compiled into a shared object (e.g., `MyModule.so`), it can be imported directly into Python. The script below demonstrates how to pass standard `numpy.ndarray` objects to the C++ functions and validates the custom FFT, SVD, and PCA backends against NumPy's native implementations.

```python
"""
test_mymodule.py
Demonstrates calling GPIArray C++ functions from Python and verifying 
the math against NumPy's native implementations.
"""
import numpy as np
import MyModule

def main():
    print("--- 1. Structs and Classes ---")
    config = MyModule.ThresholdConfig()
    config.lower_bound = 0.5
    print(f"Config bounds: {config.lower_bound} to {config.upper_bound}")

    processor = MyModule.SignalProcessor(5.0)
    arr_in = np.ones((10,), dtype=np.float64)
    arr_out = processor.process(arr_in)
    print(f"Processed Array: {arr_out}")


    print("\n--- 2. Inline Array Manipulation (Zero-Copy) ---")
    shape_3d = (100, 100, 100)
    arr_py  = np.ones(shape_3d, dtype=np.float64)
    arr_gpi = np.ones(shape_3d, dtype=np.float64)
    
    # GPIArray C++ SIMD nested loop (Zero-copy modification)
    MyModule.scale_array_inline(arr_gpi, 10.0)
    
    # Python equivalent
    arr_py *= 10.0
    print(f"Verification Match: {np.allclose(arr_py, arr_gpi)}")


    print("\n--- 3. C++ Memory Access Benchmark ---")
    # Creates a massive 3D array to expose cache behavior 
    large_arr = np.ones((256, 256, 256), dtype=np.float64)
    MyModule.benchmark_loop_orders(large_arr, 1.0001)


    print("--- 4. Multiple Returns (std::tuple) ---")
    complex_arr = np.array([1.0 + 2.0j, 3.0 + 4.0j], dtype=np.complex128)
    real_part, imag_part = MyModule.split_real_imag(complex_arr)
    print(f"Real part: {real_part}")
    print(f"Imag part: {imag_part}")


    print("\n--- 5. Template Function Routing ---")
    arr_float32 = np.ones((100,), dtype=np.float32)
    arr_float64 = np.ones((100,), dtype=np.float64)
    arr_complex = np.ones((100,), dtype=np.complex128)

    print(f"Sum (float32):    {MyModule.compute_sum(arr_float32)}")
    print(f"Sum (float64):    {MyModule.compute_sum(arr_float64)}")
    print(f"Sum (complex128): {MyModule.compute_sum(arr_complex)}")


    print("\n--- 6. FFTW Transforms vs NumPy ---")
    img = (np.random.rand(32, 32) + 1j * np.random.rand(32, 32)).astype(np.complex128)
    
    # GPIArray FFT (Automatically handles fftshifts internally)
    kspace_gpi = MyModule.compute_fftn(img, [0, 1])
    
    # NumPy Equivalent (Requires manual shifts to match MRI standards)
    kspace_np = np.fft.fftshift(np.fft.fftn(np.fft.ifftshift(img, axes=(0,1)), axes=(0,1)), axes=(0,1))
    print(f"K-space shape: {kspace_gpi.shape}")
    print(f"FFT Match (GPI vs NumPy): {np.allclose(kspace_gpi, kspace_np)}")


    print("\n--- 7. Linear Algebra (Eigen) vs NumPy ---")
    A = (np.random.rand(5, 3) + 1j * np.random.rand(5, 3)).astype(np.complex128)
    B = (np.random.rand(3, 4) + 1j * np.random.rand(3, 4)).astype(np.complex128)
    
    # A. Matrix Multiplication
    C_gpi = MyModule.compute_matmul(A, B)
    C_np = A @ B
    print(f"MatMul Match: {np.allclose(C_gpi, C_np)}")

    # B. SVD (Singular Value Decomposition)
    U_gpi, S_gpi, Vh_gpi = MyModule.compute_svd(A)
    U_np, S_np, Vh_np = np.linalg.svd(A, full_matrices=False)
    
    # Verify by comparing the singular values and the reconstructed matrix
    recon_gpi = U_gpi @ np.diag(S_gpi) @ Vh_gpi
    print(f"SVD Singular Values Match: {np.allclose(S_gpi, S_np)}")
    print(f"SVD Matrix Reconstruction Match: {np.allclose(recon_gpi, A)}")

    # C. PCA (Principal Component Analysis)
    data = (np.random.rand(100, 10) + 1j * np.random.rand(100, 10)).astype(np.complex128)
    pcs_gpi, variances_gpi = MyModule.compute_pca(data)
    
    # NumPy Equivalent PCA (Mean-center -> SVD -> Variance)
    data_centered = data - np.mean(data, axis=0)
    _, S_pca_np, Vh_pca_np = np.linalg.svd(data_centered, full_matrices=False)
    variances_np = (S_pca_np ** 2) / (data.shape[0] - 1)
    
    print(f"PCA Variances Match: {np.allclose(variances_gpi, variances_np)}")

if __name__ == "__main__":
    main()

"""
EXPECTED CONSOLE OUTPUT:
--- 1. Structs and Classes ---
Config bounds: 0.5 to 1.0
Processed Array: [5. 5. 5. 5. 5. 5. 5. 5. 5. 5.]

--- 2. Inline Array Manipulation (Zero-Copy) ---
Verification Match: True

--- 3. C++ Memory Access Benchmark ---

[C++ Internal Benchmark: 256x256x256 Elements]
  -> Optimal Nested Loop (Row-Major): 4.74154 ms
  -> Suboptimal Nested Loop (Cache Thrashing): 152.75 ms
  -> Flat SIMD Vectorized Loop: 3.55329 ms

--- 4. Multiple Returns (std::tuple) ---
Real part: [1. 3.]
Imag part: [2. 4.]

--- 5. Template Function Routing ---
Sum (float32):    100.0
Sum (float64):    100.0
Sum (complex128): (100+0j)

--- 6. FFTW Transforms vs NumPy ---
K-space shape: (32, 32)
FFT Match (GPI vs NumPy): True

--- 7. Linear Algebra (Eigen) vs NumPy ---
MatMul Match: True
SVD Singular Values Match: True
SVD Matrix Reconstruction Match: True
PCA Variances Match: True
"""

```

## 5.5 Understanding the Binding Patterns

### Pattern: Modifying Arrays In-Place

Pass by reference to modify the original NumPy array:

```cpp
void scale_array(Array<double>& arr, double factor) {  // Note the &
    arr *= factor;  // Modifies the original array
}
```

In Python, the NumPy array is modified directly (zero-copy):
```python
data = np.ones((100,))
MyModule.scale_array(data, 2.0)
# Now data is all 2.0 ✓
```

### Pattern: Creating New Arrays

Return a new Array that the type caster converts to NumPy:

```cpp
Array<double> process(const Array<double>& input) {  // Pass by const ref (read-only)
    return input * 2.0;  // Return new Array → becomes NumPy array
}
```

In Python:
```python
data = np.ones((100,))
result = MyModule.process(data)  # data unchanged, result is new array ✓
```

### Pattern: Multiple Return Values

Use `std::tuple` for unpacking in Python:

```cpp
std::tuple<Array<double>, Array<double>> 
split_real_imag(const Array<std::complex<double>>& arr) {
    return std::make_tuple(real(arr), imag(arr));
}
```

In Python:
```python
cmplx_arr = np.ones((100,), dtype=np.complex128)
real_part, imag_part = MyModule.split_real_imag(cmplx_arr)  # Auto-unpack ✓
```

### Pattern: Binding Classes

Expose C++ classes with methods and properties:

```cpp
py::class_<SignalProcessor>(m, "SignalProcessor")
    .def(py::init<double>())          // Constructor
    .def("process", &SignalProcessor::process);  // Method
```

In Python:
```python
processor = MyModule.SignalProcessor(5.0)
result = processor.process(data)
```

### Key Details in the Examples

1. **Struct and Class Binding:** Use `py::init<>()` for constructors, `.def_readwrite()` for public members, `.def()` for methods
2. **Memory Access Optimization:** The benchmark shows row-major access; reversing loop order causes 30-50x slowdown due to cache misses
3. **Inline Array Manipulation:** Direct `arr(i,j,k)` access in tight loops beats the Python interpreter
4. **Template Routing:** Bind the same function name multiple times with different template types; Pybind11 routes automatically based on NumPy dtype
5. **FFTW and LinAlg Wrappers:** Return new arrays by value; caller owns the returned NumPy arrays

## 5.6 Native `.npy` File I/O (`NumpyReadWrite.hpp`)

Save numpy arrays directly to disk from C++ without Python, and load them back. Perfect for:
- **Debug snapshots:** Save intermediate results during long C++ reconstructions
- **Standalone executables:** Process data without invoking Python
- **Data pipelines:** Pure C++ workflows that read/write NumPy-compatible files

### Example: Reading and Writing `.npy` Files from C++

```cpp
#include <iostream>
#include "GPIArray/GPIArray.hpp"      // Contains complex.h, pybind11, FFTW, LinAlg

using namespace GPIArray;

void demo_numpy_io() {
    // 1. Create a 3D array in C++
    Array<std::complex<double>> kspace(32, 256, 256);
    kspace.fill(std::complex<double>(1.0, -0.5));

    // 2. Save the array directly to a NumPy .npy file
    // Python can immediately load this using np.load("kspace_debug.npy")
    std::string filename = "kspace_debug.npy";
    npy_save(filename, kspace);
    std::cout << "Successfully saved to " << filename << std::endl;

    // 3. Load a .npy file from disk back into a C++ GPIArray
    // Note: You must specify the expected template type <T>
    try {
        Array<std::complex<double>> loaded_kspace = npy_load<std::complex<double>>(filename);
        std::cout << "Loaded: " <<  loaded_kspace.shape() << std::endl;
        
        // Verify a specific element
        std::cout << "Element at (0,0,0): " << loaded_kspace(0, 0, 0) << std::endl;
        
    } catch (const std::exception& e) {
        std::cerr << "Failed to load .npy file: " << e.what() << std::endl;
    }
}

```

---

## 5.7 Troubleshooting Python Integration

### Problem: "ImportError: No module named 'MyModule'"

**Cause:** The compiled shared object (.so) is not in Python's path, or compilation failed.

**Solution:**
```bash
# 1. Verify build succeeded
cd MyModule
gpi_make .
ls build/lib/MyModule.*.so  # Check if .so exists

# 2. Add to Python path
export PYTHONPATH=/path/to/MyModule/build/lib:$PYTHONPATH
python -c "import MyModule"  # Try import again

# 3. Or install directly
pip install -e .  # Editable install
```

---

### Problem: "TypeError: unsupported operand type(s)"

**Cause:** You're passing the wrong NumPy dtype (e.g., `float32` when the C++ function expects `float64`).

**Solution:**
```python
# ❌ Wrong: float32
arr = np.ones((100,), dtype=np.float32)
result = MyModule.my_func(arr)  # Fails!

# ✅ Correct: Explicitly cast
arr = np.ones((100,), dtype=np.float64)
result = MyModule.my_func(arr)

# Or auto-cast in Python
arr = arr.astype(np.float64)
result = MyModule.my_func(arr)
```

---

### Problem: "In-place modification doesn't affect the original NumPy array"

**Cause:** Your C++ function is creating a new Array instead of modifying in-place. The type caster can't automatically map returns back to the input array.

**Solution:** Design your C++ function signature to take a reference:

```cpp
// ❌ Won't modify original Python array
void bad_modify(Array<double> arr) {
    arr.fill(0.0);  // Modifies local copy
}

// ✅ Modifies original Python array
void good_modify(Array<double>& arr) {  // Note the & reference
    arr.fill(0.0);  // Modifies the array that Python owns
}

// Python code
arr = np.ones((100,))
MyModule.good_modify(arr)  # arr is now all zeros ✓
```

---

### Problem: "Segmentation fault when calling C++ function"

**Cause:** Array is non-contiguous, or function expects contiguous data.

**Solution:**
```python
# ❌ Non-contiguous view causes crash
arr = np.ones((10, 10))
transposed = arr.T  # Non-contiguous copy
MyModule.my_func(transposed)  # May crash!

# ✅ Make contiguous first
transposed_c = np.ascontiguousarray(arr.T)
MyModule.my_func(transposed_c)  # Safe ✓
```

---

### Problem: "Type mismatch" or unexpected behavior with complex numbers

**Cause:** NumPy complex is `complex128` (complex<double>), but you defined `complex64` (complex<float>).

**Solution:**
```cpp
// In C++, be explicit about complex type
void process(const Array<std::complex<double>>& arr) {
    // ...
}

// In Python, use complex128
arr = np.ones((100,), dtype=np.complex128)  # Not complex64!
result = MyModule.process(arr)
```

---

## 5.8 NumPy Equivalence Reference

Common GPIArray operations and their NumPy equivalents:

| Operation | GPIArray C++ | NumPy Python |
|-----------|-----------|-----------|
| Element-wise add | `A + B` | `A + B` |
| Element-wise multiply | `A * B` | `A * B` |
| Scalar multiply | `A * 2.0` | `A * 2.0` |
| Sum | `sum(A)` | `np.sum(A)` |
| Mean | `mean(A)` | `np.mean(A)` |
| L2 norm | `l2norm(A)` | `np.linalg.norm(A)` |
| Matrix multiply | `LinAlg::matmul(A, B, C)` | `A @ B` |
| SVD | `LinAlg::svd(A, U, S, Vh, LinAlg::Thin)` | `U, S, Vh = np.linalg.svd(A, full_matrices=False)` |
| FFT | `FFTW::fftn(data, spectrum, ImageToKspace)` | `np.fft.fft(data)` (+ manual shifts) |
| Slice | `arr.slice(S(start, stop), S::all())` | `arr[start:stop, :]` |
| Reshape | `arr.reshape({m, n})` | `arr.reshape((m, n))` |
| Transpose | `arr.transpose({1, 0})` | `arr.T` |
| Real part | `real(arr)` | `np.real(arr)` |
| Conjugate | `conj(arr)` | `np.conj(arr)` |

---

## 5.9 Performance Tips

**DO:**
- ✅ Pass objects by const reference: `const Array<T>&` (zero copy)
- ✅ Modify in-place when possible: `void func(Array<T>&)` (no allocation)
- ✅ Return new arrays: `Array<T> func(...)` (caller owns memory)
- ✅ Use contiguous arrays for FFT/LinAlg

**DON'T:**
- ❌ Make unnecessary copies in Python before passing to C++
- ❌ Expect in-place operations on non-contiguous arrays
- ❌ Mix float32 and complex64 without explicit casting
- ❌ Create arrays inside C++ loops that are called from Python