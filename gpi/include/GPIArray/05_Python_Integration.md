# Section 5: Python Integration (Pybind11)

Call fast C++ algorithms directly from Python with NumPy-aware bindings. A simple call into C++ and return back to Python measured under roughly 15 microseconds, which gives a good sense of how small the binding overhead can be in practice. Exact timing depends on the machine, compiler, Python build, and function signature, but the key point is that the binding layer itself is very light. When dtype and layout are already compatible, arrays can be mapped into `GPIArray::Array<T>` without copying.

## 5.0 Quick Start

Creating a Python binding is extremely simple. Just create a file named `<MyModule>_PYBIND11.cpp`, place it alongside the `GPI` folder, and fill it with your C++ function plus a small `PYBIND11_MODULE(...)` block. If your actual algorithm already lives in a separate `.cpp` or header file, just `#include` it from the `*_PYBIND11.cpp` file and bind the function there.

### 1. Create `<MyModule>_PYBIND11.cpp`

```cpp
#include "GPIArray/GPIArray.hpp"
using namespace GPIArray;

using Complex = std::complex<double>

// Write normal C++ using Array<T>
Array<Complex> my_algorithm(const Array<Complex>& input) {
    Array<Complex> output = input.copy();
    output *= 2.0;  // Any GPIArray operation
    return output;
}

// Expose it to Python
PYBIND11_MODULE(MyModule, m) {
    m.def("my_algorithm", &my_algorithm);
}
```

### 2. Build with gpi_make

```bash
gpi_make <MyModule>
```

### 3. Call from Python

```python
import numpy as np
import <gpi_project_folder_name>.MyModule

# Create NumPy array
data = np.random.rand(256, 256).astype(complex)

# Call C++ directly
result = MyModule.my_algorithm(data)
```

The NumPy dtype must match the C++ function signature. If it does not, an error is thrown. When it does match, the type caster maps the NumPy buffer directly into `Array<T>` using the original shape and strides. That means even non-contiguous NumPy arrays are accepted without an input copy, so the Python-to-C++ conversion itself is essentially zero-overhead.

---

## 5.1 How It Works: The Type Caster Magic

`GPIArray.hpp` contains a custom Pybind11 `type_caster` that:

1. **Accepts Python objects:** Pybind11 receives `numpy.ndarray` from Python
2. **Maps memory in-place when types match:** The NumPy buffer pointer becomes your `Array<T>` data pointer
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

## 5.2-5.3 Writing & Calling C++ Functions: Complete Examples

This section combines data types with complete working examples. Each example shows the C++ code, Python test code, and expected output together.

**Type Support:** What you can pass from Python to C++:

| Python Type | C++ Receives | Data Copied? | Use Case |
|-------------|-----------|-----------|---|
| `np.ndarray` with matching dtype | `Array<T>` | No (input is mapped directly) | All your algorithms |
| `np.ndarray` with matching dtype | `const Array<T>&` | No (input is mapped directly) | Read-only inputs |
| Scalar (int/float/complex) | `T` | N/A | Single values |
| `list` of arrays | `std::vector<Array<T>>` | Per-array mapping | Batch processing |



---

### Example 1: Function Returning a New Array (Simplest)

**C++ Code:**
```cpp
#include "GPIArray/GPIArray.hpp"
using namespace GPIArray;

Array<double> add_arrays(const Array<double>& a, const Array<double>& b) {
    return a + b;
}

PYBIND11_MODULE(MyModule, m) {
    m.def("add_arrays", &add_arrays, "Adds two arrays and returns a new array.");
}
```

**Python Code:**
```python
import numpy as np
import MyModule

a = np.array([1.0, 2.0, 3.0])
b = np.array([4.0, 5.0, 6.0])
c = MyModule.add_arrays(a, b)
print(f"Result: {c}")
```

**Expected Output:**
```
Result: [5. 7. 9.]
```

---

### Example 2: In-Place Array Modification (Zero-Copy)

**C++ Code:**
```cpp
#include "GPIArray/GPIArray.hpp"
using namespace GPIArray;

void scale_array_inline(Array<double>& arr, double factor) {
    for (auto& elem : arr) {
        elem *= factor;
    }
}

PYBIND11_MODULE(MyModule, m) {
    m.def("scale_array_inline", &scale_array_inline, "Scales an array in-place.");
}
```

**Python Code:**
```python
import numpy as np
import MyModule

arr = np.ones((100, 100, 100), dtype=np.float64)
MyModule.scale_array_inline(arr, 10.0)
print(f"Array modified in-place: {arr[0, 0, 0]}")  # Verify zero-copy
```

**Expected Output:**
```
Array modified in-place: 10.0
```

---

### Example 3: Function Returning Multiple Values (Tuple)

**C++ Code:**
```cpp
#include "GPIArray/GPIArray.hpp"
using namespace GPIArray;

std::tuple<Array<double>, Array<double>> split_real_imag(const Array<std::complex<double>>& arr) {
    return std::make_tuple(real(arr), imag(arr));
}

PYBIND11_MODULE(MyModule, m) {
    m.def("split_real_imag", &split_real_imag, "Returns a tuple of (real, imag).");
}
```

**Python Code:**
```python
import numpy as np
import MyModule

complex_arr = np.array([1.0 + 2.0j, 3.0 + 4.0j], dtype=np.complex128)
real_part, imag_part = MyModule.split_real_imag(complex_arr)
print(f"Real part: {real_part}, Imag part: {imag_part}")
```

**Expected Output:**
```
Real part: [1. 3.], Imag part: [2. 4.]
```

---

### Example 4: Template Function with Type Routing

**C++ Code:**
```cpp
#include "GPIArray/GPIArray.hpp"
using namespace GPIArray;

template<typename T>
T compute_sum(const Array<T>& arr) {
    return sum(arr);
}

PYBIND11_MODULE(MyModule, m) {
    m.def("compute_sum", &compute_sum<double>, "Sum of a float64 array.");
    m.def("compute_sum", &compute_sum<float>, "Sum of a float32 array.");
    m.def("compute_sum", &compute_sum<std::complex<double>>, "Sum of a complex128 array.");
}
```

**Python Code:**
```python
import numpy as np
import MyModule

arr_float32 = np.ones((100,), dtype=np.float32)
arr_float64 = np.ones((100,), dtype=np.float64)
arr_complex = np.ones((100,), dtype=np.complex128)

print(f"Sum (float32): {MyModule.compute_sum(arr_float32)}")
print(f"Sum (float64): {MyModule.compute_sum(arr_float64)}")
print(f"Sum (complex128): {MyModule.compute_sum(arr_complex)}")
```

**Expected Output:**
```
Sum (float32): 100.0
Sum (float64): 100.0
Sum (complex128): (100+0j)
```

---

### Example 5: Functions with Optional Input Parameters

**C++ Code:**
```cpp
#include "GPIArray/GPIArray.hpp"
using namespace GPIArray;

// Function with optional threshold parameter
Array<double> threshold_array(const Array<double>& arr, double threshold = 0.5) {
    Array<double> result = arr.copy();
    for (auto& elem : result) {
        if (elem < threshold) {
            elem = 0.0;
        }
    }
    return result;
}

PYBIND11_MODULE(MyModule, m) {
    m.def("threshold_array", &threshold_array, 
          "Thresholds array values below threshold", 
          py::arg("arr"), 
          py::arg("threshold") = 0.5);  // Default value = 0.5
}
```

**Python Code:**
```python
import numpy as np
import MyModule

data = np.array([0.2, 0.7, 0.3, 0.9, 0.1], dtype=np.float64)

# Call with default threshold (0.5)
result1 = MyModule.threshold_array(data)
print(f"With default threshold (0.5): {result1}")

# Call with custom threshold (0.3)
result2 = MyModule.threshold_array(data, threshold=0.3)
print(f"With custom threshold (0.3): {result2}")

# Can also use positional argument
result3 = MyModule.threshold_array(data, 0.6)
print(f"With positional threshold (0.6): {result3}")
```

**Expected Output:**
```
With default threshold (0.5): [0.  0.7 0.  0.9 0. ]
With custom threshold (0.3): [0.  0.7 0.  0.9 0. ]
With positional threshold (0.6): [0.7 0.9]
```

---

### Example 6: Function Overloading (Same Name, Different Arguments)

**C++ Code:**
```cpp
#include "GPIArray/GPIArray.hpp"
using namespace GPIArray;

// Normalize array to [0, 1] range
Array<double> normalize(const Array<double>& arr) {
    double min_val = min(arr);
    double max_val = max(arr);
    double range = max_val - min_val;

    return (arr - min_val) / range;
}

// Normalize to custom [target_min, target_max] range
Array<double> normalize(const Array<double>& arr, double target_min, double target_max) {
    double min_val = min(arr);
    double max_val = max(arr);
    double range = max_val - min_val;

    Array<double> normalized = (arr - min_val) / range;
    return target_min + normalized * (target_max - target_min);
}

PYBIND11_MODULE(MyModule, m) {
    // Overload 1: Simple normalization to [0, 1]
    m.def("normalize", static_cast<Array<double>(*)(const Array<double>&)>(&normalize),
          "Normalizes array to [0, 1] range");
    
    // Overload 2: Normalize to custom range
    m.def("normalize", 
          static_cast<Array<double>(*)(const Array<double>&, double, double)>(&normalize),
          "Normalizes array to [target_min, target_max] range",
          py::arg("arr"), py::arg("target_min"), py::arg("target_max"));
}
```

**Python Code:**
```python
import numpy as np
import MyModule

data = np.array([1.0, 2.0, 3.0, 4.0, 5.0], dtype=np.float64)

# Call overload 1: Default [0, 1] normalization
result1 = MyModule.normalize(data)
print(f"Normalized to [0, 1]: {result1}")

# Call overload 2: Custom range [-1, 1]
result2 = MyModule.normalize(data, -1.0, 1.0)
print(f"Normalized to [-1, 1]: {result2}")

# Call overload 2: Custom range [100, 200]
result3 = MyModule.normalize(data, 100.0, 200.0)
print(f"Normalized to [100, 200]: {result3}")
```

**Expected Output:**
```
Normalized to [0, 1]: [0.   0.25 0.5  0.75 1.  ]
Normalized to [-1, 1]: [-1.   -0.5  0.   0.5  1.  ]
Normalized to [100, 200]: [100. 125. 150. 175. 200.]
```

---

### Example 7: Expose a C++ Struct

**C++ Code (`MyModule_PYBIND11.cpp`):**
```cpp
#include "GPIArray/GPIArray.hpp"
namespace py = pybind11;
using namespace GPIArray;

struct ThresholdConfig {
    double lower_bound = 0.0;
    double upper_bound = 1.0;
};

PYBIND11_MODULE(MyModule, m) {
    py::class_<ThresholdConfig>(m, "ThresholdConfig")
        .def(py::init<>()) 
        .def_readwrite("lower_bound", &ThresholdConfig::lower_bound)
        .def_readwrite("upper_bound", &ThresholdConfig::upper_bound);
}
```

**Python Code:**
```python
import MyModule

config = MyModule.ThresholdConfig()
config.lower_bound = 0.5
print(f"Config bounds: {config.lower_bound} to {config.upper_bound}")
```

**Expected Output:**
```
Config bounds: 0.5 to 1.0
```

---

### Example 8: Expose a C++ Class with Methods

**C++ Code:**
```cpp
#include "GPIArray/GPIArray.hpp"
namespace py = pybind11;
using namespace GPIArray;

class SignalProcessor {
public:
    SignalProcessor(double gain) : _gain(gain) {}

    Array<double> process(const Array<double>& input) {
        return input * _gain;
    }

    Array<double> process_with_offset(const Array<double>& input, double offset) {
        return input * _gain + offset;
    }

    void set_gain(double gain) {
        _gain = gain;
    }

    double gain() const {
        return _gain;
    }

private:
    double _gain;
};

PYBIND11_MODULE(MyModule, m) {
    py::class_<SignalProcessor>(m, "SignalProcessor")
        .def(py::init<double>())
        .def("process", &SignalProcessor::process)
        .def("process_with_offset", &SignalProcessor::process_with_offset)
        .def("set_gain", &SignalProcessor::set_gain)
        .def("gain", &SignalProcessor::gain);
}
```

**Python Code:**
```python
import numpy as np
import MyModule

processor = MyModule.SignalProcessor(5.0)
arr_in = np.ones((10,), dtype=np.float64)

arr_out1 = processor.process(arr_in)
print(f"Processed Array: {arr_out1}")

arr_out2 = processor.process_with_offset(arr_in, 2.0)
print(f"Processed With Offset: {arr_out2}")

processor.set_gain(3.0)
print(f"Updated Gain: {processor.gain()}")

arr_out3 = processor.process(arr_in)
print(f"Processed After Gain Update: {arr_out3}")
```

**Expected Output:**
```
Processed Array: [5. 5. 5. 5. 5. 5. 5. 5. 5. 5.]
Processed With Offset: [7. 7. 7. 7. 7. 7. 7. 7. 7. 7.]
Updated Gain: 3.0
Processed After Gain Update: [3. 3. 3. 3. 3. 3. 3. 3. 3. 3.]
```

---

### Example 9: Memory Access Patterns & Cache Behavior

**C++ Code:**
```cpp
#include "GPIArray/GPIArray.hpp"
#include <chrono>
using namespace GPIArray;

void benchmark_loop_orders(Array<double>& arr, double factor) {
    if (!arr.is_contiguous()) throw std::invalid_argument("Requires contiguous array");
    uint64_t dim0 = arr.dimensions(0);
    uint64_t dim1 = arr.dimensions(1);
    uint64_t dim2 = arr.dimensions(2);

    // 1. Optimal Row-Major Order
    auto start1 = std::chrono::high_resolution_clock::now();
    for (uint64_t i = 0; i < dim0; ++i)
        for (uint64_t j = 0; j < dim1; ++j)
            for (uint64_t k = 0; k < dim2; ++k)
                arr(i, j, k) *= factor;
    auto time1 = std::chrono::duration<double, std::milli>(
        std::chrono::high_resolution_clock::now() - start1).count();

    // 2. Cache-Thrashing Reversed Order
    auto start2 = std::chrono::high_resolution_clock::now();
    for (uint64_t k = 0; k < dim2; ++k)
        for (uint64_t j = 0; j < dim1; ++j)
            for (uint64_t i = 0; i < dim0; ++i)
                arr(i, j, k) *= factor;
    auto time2 = std::chrono::duration<double, std::milli>(
        std::chrono::high_resolution_clock::now() - start2).count();

    // 3. SIMD Vectorized Loop
    auto start3 = std::chrono::high_resolution_clock::now();
    double* data = arr.get_data();
    #pragma omp simd
    for (uint64_t idx = 0; idx < arr.size(); ++idx)
        data[idx] *= factor;
    auto time3 = std::chrono::duration<double, std::milli>(
        std::chrono::high_resolution_clock::now() - start3).count();

    std::cout << "Row-Major: " << time1 << " ms, Cache Thrashing: " << time2 
              << " ms, SIMD: " << time3 << " ms" << std::endl;
}

PYBIND11_MODULE(MyModule, m) {
    m.def("benchmark_loop_orders", &benchmark_loop_orders);
}
```

**Python Code:**
```python
import numpy as np
import MyModule

large_arr = np.ones((256, 256, 256), dtype=np.float64)
MyModule.benchmark_loop_orders(large_arr, 1.0001)
```

**Expected Output:**
```
Row-Major: 4.74 ms, Cache Thrashing: 152.75 ms, SIMD: 3.55 ms
```

---

### Example 10: FFTW Wrapper Function

**C++ Code:**
```cpp
#include "GPIArray/GPIArray.hpp"
using namespace GPIArray;

Array<std::complex<double>> compute_fftn(const Array<std::complex<double>>& input, 
                                          std::vector<uint64_t> axes) {
    Array<std::complex<double>> output = input.empty_like();
    FFTW::fftn(input, output, FFTW::ImageToKspace, axes);
    return output;
}

PYBIND11_MODULE(MyModule, m) {
    m.def("compute_fftn", &compute_fftn, "Computes N-Dimensional FFT.");
}
```

**Python Code:**
```python
import numpy as np
import MyModule

img = (np.random.rand(32, 32) + 1j * np.random.rand(32, 32)).astype(np.complex128)
kspace_gpi = MyModule.compute_fftn(img, [0, 1])
kspace_np = np.fft.fftshift(np.fft.fftn(np.fft.ifftshift(img, axes=(0,1)), axes=(0,1)), axes=(0,1))
print(f"K-space shape: {kspace_gpi.shape}")
print(f"FFT Match (GPI vs NumPy): {np.allclose(kspace_gpi, kspace_np)}")
```

**Expected Output:**
```
K-space shape: (32, 32)
FFT Match (GPI vs NumPy): True
```

---

### Example 11: Linear Algebra - Matrix Multiplication

**C++ Code:**
```cpp
#include "GPIArray/GPIArray.hpp"
using namespace GPIArray;

Array<std::complex<double>> compute_matmul(const Array<std::complex<double>>& A, 
                                            const Array<std::complex<double>>& B) {
    return LinAlg::matmul(A, B);
}

PYBIND11_MODULE(MyModule, m) {
    m.def("compute_matmul", &compute_matmul, "Computes matrix multiplication C = A * B.");
}
```

**Python Code:**
```python
import numpy as np
import MyModule

A = (np.random.rand(5, 3) + 1j * np.random.rand(5, 3)).astype(np.complex128)
B = (np.random.rand(3, 4) + 1j * np.random.rand(3, 4)).astype(np.complex128)

C_gpi = MyModule.compute_matmul(A, B)
C_np = A @ B
print(f"MatMul Match: {np.allclose(C_gpi, C_np)}")
```

**Expected Output:**
```
MatMul Match: True
```

---

### Example 12: Linear Algebra - SVD (Singular Value Decomposition)

**C++ Code:**
```cpp
#include "GPIArray/GPIArray.hpp"
using namespace GPIArray;

auto compute_svd(const Array<std::complex<double>>& A) {
    return LinAlg::svd(A, LinAlg::Thin);
}

PYBIND11_MODULE(MyModule, m) {
    m.def("compute_svd", &compute_svd, "Computes Thin SVD, returning (U, S, Vh).");
}
```

**Python Code:**
```python
import numpy as np
import MyModule

A = (np.random.rand(5, 3) + 1j * np.random.rand(5, 3)).astype(np.complex128)

U_gpi, S_gpi, Vh_gpi = MyModule.compute_svd(A)
U_np, S_np, Vh_np = np.linalg.svd(A, full_matrices=False)

recon_gpi = U_gpi @ np.diag(S_gpi) @ Vh_gpi
print(f"SVD Singular Values Match: {np.allclose(S_gpi, S_np)}")
print(f"SVD Matrix Reconstruction Match: {np.allclose(recon_gpi, A)}")
```

**Expected Output:**
```
SVD Singular Values Match: True
SVD Matrix Reconstruction Match: True
```

---

### Example 13: Linear Algebra - PCA (Principal Component Analysis)

**C++ Code:**
```cpp
#include "GPIArray/GPIArray.hpp"
using namespace GPIArray;

std::tuple<Array<std::complex<double>>, Array<double>> 
compute_pca(const Array<std::complex<double>>& data) {
    return LinAlg::pca(data);
}

PYBIND11_MODULE(MyModule, m) {
    m.def("compute_pca", &compute_pca, "Computes PCA, returning (PCs, variances).");
}
```

**Python Code:**
```python
import numpy as np
import MyModule

data = (np.random.rand(100, 10) + 1j * np.random.rand(100, 10)).astype(np.complex128)
pcs_gpi, variances_gpi = MyModule.compute_pca(data)

# NumPy Equivalent PCA
data_centered = data - np.mean(data, axis=0)
_, S_pca_np, _ = np.linalg.svd(data_centered, full_matrices=False)
variances_np = (S_pca_np ** 2) / (data.shape[0] - 1)

print(f"PCA Variances Match: {np.allclose(variances_gpi, variances_np)}")
```

**Expected Output:**
```
PCA Variances Match: True
```

---

## 5.5 Understanding the Binding Patterns

### Pattern: Modifying Arrays In-Place

Pass by reference to modify the original NumPy array:

```cpp
void scale_array(Array<double>& arr, double factor) {  // Note the &
    arr *= factor;  // Modifies the original array
}
```

In Python, the NumPy array is modified directly when the passed array already matches the bound dtype/layout expectations:
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
#include "GPIArray/NumpyReadWrite.hpp"

using namespace GPIArray;

void demo_numpy_io() {
    Array<double> data(4, 4);
    data.fill(1.0);

    std::string filename = "debug/output.npy";
    npy_save(filename, data);

    Array<double> loaded = npy_load<double>(filename);
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
gpi_make MyModule
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

**Cause:** The Python binding accepts non-contiguous NumPy views and preserves their strides. Problems happen only when your C++ implementation incorrectly assumes the data is laid out as one flat contiguous block.

**Solution:**
```python
# Non-contiguous NumPy views are accepted by the binding
arr = np.ones((10, 10))
transposed = arr.T
MyModule.my_func(transposed)  # Fine if the C++ code is stride-aware

# Only do this if the C++ implementation requires contiguous flat memory
transposed_c = np.ascontiguousarray(transposed)
MyModule.my_func(transposed_c)
```

Use normal `GPIArray` indexing, slicing, or iterators whenever possible. Only force contiguity when the implementation truly depends on linear contiguous access.

> [!NOTE]
> Large non-contiguous NumPy inputs are usually slower to process in C++ than contiguous ones, even when the code is fully stride-aware. The result is still correct, but cache locality and vectorization are generally worse.

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

### Contiguity & Automatic Handling

**The `.contiguous()` Method:**
- Returns the array as-is if already contiguous (zero overhead)
- Returns a copy if non-contiguous (automatic, transparent)
- Available from C++ and automatically used on LinAlg and FFTW input arrays

```cpp
// In C++: Use .contiguous() when passing to FFT/LinAlg
Array<Complex> transposed = A.transpose(1, 0, 2);
auto safe = transposed.contiguous();  // Zero cost if contiguous, copy if not
FFTW::fftn(safe, output, FFTW::ImageToKspace);
```

```python
# In Python: backend wrappers handle non-contiguous FFT/LinAlg inputs automatically
transposed = np_array.T
result = MyModule.my_fft_function(transposed)
```

**DO:**
- ✅ Pass objects by const reference: `const Array<T>&` (zero copy)
- ✅ Modify in-place when possible: `void func(Array<T>&)` (no allocation)
- ✅ Return new arrays: `Array<T> func(...)` (caller owns memory)
- ✅ Use `.contiguous()` for guaranteed FFT/LinAlg compatibility (automatic in backends)
- ✅ Transpose and slice freely when you pass them into FFTW/LinAlg wrappers

**DON'T:**
- ❌ Make unnecessary copies in Python before passing to wrappers that already handle contiguity
- ❌ Manually call `.copy()` before FFT/LinAlg (backends do this automatically)
- ❌ Mix float32 and complex64 without explicit casting
- ❌ Create arrays inside C++ loops that are called from Python
