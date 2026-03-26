# Section 2: Core Data Structures

The foundation of the library is the `Voxel::Array<T>` container. It mimics NumPy's semantics while enforcing C++ memory safety and optimizing for zero-allocation scientific workflows.

## 2.1 Querying Shape and Size

Understanding the geometry of your data is critical for multi-dimensional processing. `Voxel` provides high-level methods to query both the total volume and specific axis lengths.

* **.shape()**: Returns a `std::vector<uint64_t>` containing the dimensions.
* **.size()**: Returns the total number of elements in the array (the product of all dimensions).
* **.size(i)**: Returns the size of the $i$-th dimension. Passing `0` returns the first dimension.
* **Negative Indexing**: Similar to NumPy, passing `-1` to size methods (e.g., `.size(-1)`) returns the size of the **last** dimension.

**Example:**

```cpp
Array<Complex> A(20, 32, 256, 256);

// shape() returns a std::vector<uint64_t>
auto dims = A.shape();  // {20, 32, 256, 256}

size_t total = A.size();      // Returns 20 * 32 * 256 * 256
size_t coils = A.size(1);     // Returns 32
size_t width = A.size(-1);    // Returns 256 (last dimension)

```

## 2.2 Decision Tree: When to Use What

Before jumping into code, ask yourself: **What do I need to do with this data?**

```
┌─ Do you need a NEW array?
│  ├─ Yes: What should it contain?
│  │  ├─ All zeros? → .zeros_like()
│  │  ├─ All ones?  → .ones_like()
│  │  ├─ Uninitialized, same type? → .empty_like()
│  │  └─ Match shape, different type? → Array<NewType>(original.shape())
│  │
│  └─ No: Do you want to MODIFY the original?
│     ├─ Yes (modifying OK) → Use .slice() or .transpose() directly
│     └─ No (preserve original) → .copy() first, then modify
│
└─ Will you pass it to FFT or Linear Algebra?
   ├─ Yes → Use .contiguous() (automatic: copy only if needed)
   └─ No → Any layout is fine
```

**Quick Reference:**
| I want to... | Use this | Creates copy? |
|--------------|----------|---------------|
| Extract a region | `.slice()` | ❌ No (view) |
| Reshape without moving data | `.reshape()` | ❌ No, if the array is contiguous |
| Rotate dimensions | `.transpose()` | ❌ No (view) |
| Guarantee contiguous only if needed | `.contiguous()` | ✅ Maybe |
| Guarantee contiguous always | `.copy()` | ✅ Yes |
| Create zero array | `.zeros_like()` | ✅ Yes |
| Safe for FFT/Linear Algebra | `.contiguous()` (preferred) | ✅ Maybe |

---

## 2.3 Performance Tip: Indexing Datatypes

> [!IMPORTANT]
> **Always use `size_t` for indexing variables, loop counters, and offset math.** The library's internal address calculation uses unsigned 64-bit integers. Using `size_t` prevents signed/unsigned comparison overhead and ensures optimal register usage for memory offsets during high-speed execution. This can significantly impact performance in tight loops.

## 2.4 Array Instantiation & Examples

`Array<T>` provides several ways to instantiate tensors. To prevent memory fragmentation, factory methods that allocate memory should generally be used during initialization phases rather than inside iterative loops.

### Standard Constructors (Direct Size Overloads)

Convenience constructors for 1D through 10D arrays allow you to pass dimension sizes directly as arguments rather than wrapping them in a vector.

```cpp
using namespace Voxel;

Array<double>  arr1d(100);           // 1D Vector
Array<Complex> arr2d(256, 256);      // 2D Matrix
Array<float>   arr3d(32, 128, 128);  // 3D Volume

```

### Initialization via Shape

You can initialize a new array by passing the shape of an existing array directly into the constructor. This is the preferred way to create workspace buffers or temporary variables that must match your input data.

```cpp
Array<float> A(10, 256, 256);

// Create a new double-precision array matching the exact dimensions of A
Array<double> B(A.shape()); 

```

### Static Initialization Factories



Use the static `zeros`, `ones`, `rand`, or `linspace` methods to create initialized memory from scratch. The `linspace` method defaults to `endpoint=True` to mimic numpy's behavior.


```cpp
auto zeros_vol = Array<double>::zeros(32, 64, 64);
auto noise     = Array<Complex>::rand(64, 64, 64); // Uniform [0, 1]

// Create a 1D array of 100 evenly spaced values from 0.0 to 1.0 (endpoint included by default, like numpy)
auto t = Array<double>::linspace(0.0, 1.0, 100); // endpoint is True by default

// Exclude the endpoint (set endpoint=false)
auto t_closed = Array<double>::linspace(0.0, 1.0, 100, false);
```

### Initializer List Initialization

Create 1D arrays directly using C++ initializer list syntax. This is convenient for small vectors and parameter arrays:

```cpp
// Create a 1D array with initial values
Array<double> t2_water = {60e-3, 80e-3, 100e-3, 120e-3, 150e-3, 250e-3, 500e-3, 1000e-3, 2000e-3};
Array<double> t2_fat = {130e-3, 150e-3};

// Works with different types
Array<Complex> frequencies = {Complex(1.0, 0.0), Complex(2.0, 1.0), Complex(3.0, -1.0)};

// For large arrays, prefer static factories (more efficient)
auto big_array = Array<double>::zeros(1000000); // Better than .fill() for large sizes
```

**Note:** Initializer lists are best for small, compile-time-known arrays. For large or dynamically-sized arrays, use static factories like `.zeros()` or `.rand()` instead.

## 2.5 Clone Factories & Data Duplication

Clone factories allow you to create new arrays based on the properties of an existing instance. This allows for a fluent, readable syntax when preparing auxiliary buffers or workspace arrays.

| Method | Description |
| --- | --- |
| **`.copy()`** | Performs a deep copy, ensuring the new instance is contiguous and owning. |
| **`.empty_like()`** | Returns a new array with matching shape/type but uninitialized memory. |
| **`.zeros_like()`** | Returns a new array with matching shape/type, initialized to zero. |
| **`.ones_like()`** | Returns a new array with matching shape/type, initialized to one. |

**Examples:**

```cpp

// 1. Creates a view (modifying destination modifes source as well)
auto arr_view = original_arr;

// 2. Deep copy an existing array (forces contiguity)
auto arr_copy = original_arr.copy();

// 3. Create a zero-initialized array matching the target data shape and type
auto zero_buffer = target_data.zeros_like();

// 4. Create an array of all ones matching the target shape and type
auto ones_buffer = target_data.ones_like();

```

## 2.6 Memory Properties: Contiguity and Ownership

To safely interface with low-level backends and manage memory lifecycles, `Array<T>` exposes two critical state flags.

### `.is_contiguous()`

Returns `true` if the array elements are laid out sequentially in memory without any gaps.

* **Importance:** High-speed backends (FFTW, Eigen) and SIMD loops require contiguous memory to function correctly.
* **State Change:** Operations like `.transpose()` or inner-dimension `.slice()` will typically render an array non-contiguous.

### `.is_owning()`

Returns `true` if the specific `Array` instance is the primary owner of the memory buffer.

* **Ownership vs. Views:** A primary array created via a constructor or factory is "owning." Views created via operations like `.slice()`, `.transpose()`, or `.reshape()` share existing storage instead of allocating a new buffer.

## 2.7 Array Operations & Manipulation

These operations reorganize data layout. Most return **views** (zero-allocation) unless otherwise noted.

| Method | Description | Example |
| --- | --- | --- |
| **`.fill(val)`** | Fills the entire array with a scalar value in-place. | `A.fill(0.0);` |
| **`.reshape(dims)`** | Changes dimensions without moving data, but only for contiguous arrays. Elements must match. | `A.reshape(32, 65536);` |
| **`.resize(dims)`** | Changes array size. **May reallocate** if total size changes. | `A.resize(10, 128, 128);` |
| **`.transpose(axes)`** | Permutes dimensions. Returns a non-contiguous view. | `A.transpose(0, 2, 1);` |
| **`.flatten()`** | Collapses all dimensions into a single 1D view, but only for contiguous arrays. | `auto vec = A.flatten();` |
| **`.squeeze()`** | Removes all dimensions of size 1. | `B.squeeze();` |
| **`.add_singleton_dimension(i)`** | Inserts a new dimension of size 1 at index $i$. | `A.add_singleton_dimension(0);` |
| **`.contiguous()`** | Returns array as-is if contiguous, otherwise returns a contiguous copy. Zero overhead if already contiguous. | `auto safe = A.transpose(0, 2, 1).contiguous();` |

## 2.8 Changing Datatypes (Casting)

To change the datatype of an existing array (e.g., converting `float` to `double`), use the explicit constructor syntax. This performs a deep copy of the data.

```cpp
Array<float> A_float(256, 256);

// Convert real data to complex (imaginary part becomes 0.0)
Array<Complex> C_complex(A_float);

```

## 2.9 Slicing (`S`)

`Voxel` uses the `S` shorthand for slicing. **All indices and ranges must be wrapped in the `S()` constructor.** Slicing returns a non-owning view.

* **`S(index)`**: Selects a single index.
* **`S(start, stop)`**: Selects a range from start up to stop (exclusive).
* **`S(start, stop, step)`**: Selects a strided range.
* **`S::all()`**: Selects the entire dimension.
* **`S::center()`**: Picks the middle index of the dimension.
* **`S::end`**: A sentinel value representing the end of the dimension. Use in ranges like `S(10, S::end)` to slice from index 10 to the end, or `S(0, S::end-20)` to exclude the last 20 elements.
* **`S(start, stop, -1)`**: Reverse slicing with negative step (start > stop required).

**Contiguity Note:** A slice is only contiguous if it selects a subset of the outermost dimensions while keeping all trailing dimensions intact. Slicing into inner dimensions results in a non-contiguous view.

**Examples:**

```cpp
Array<Complex> volume(32, 256, 256);

// 1. Contiguous View: Extract the 10th slice (Indices must be wrapped in S)
auto slice_view = volume.slice(S(10), S::all(), S::all());

// 2. Strided range: Every 2nd slice from 5 up to 12 (Indices 5, 7, 9, 11)
auto strided_view = volume.slice(S(5, 12, 2), S::all(), S::all());

// 3. Reverse order: Last 10 rows in reverse
auto reversed = volume.slice(S::all(), S(255, 245, -1), S::all());

// 4. Using S::end for flexible range slicing
// Extract from row 50 to the end of dimension
auto to_end = volume.slice(S::all(), S(50, S::end), S::all());
// Extract all but the last 20 rows
auto exclude_tail = volume.slice(S::all(), S(0, S::end - 20), S::all());

// 5. Using .contiguous() for heavy iterative loops
// If unsure about contiguity and planning heavy iterative loops without modifying 
// the source array, use .contiguous(). It returns the array as-is if already contiguous
// (zero overhead), otherwise creates a contiguous copy only when necessary.
auto safe_for_loops = strided_view.contiguous();

```

## 2.10 Iterating Over Arrays

> [!TIP]
> **For optimal performance, always use `size_t` (or `uint64_t`) for loop counters and indexing variables.** The library's internal address calculation uses unsigned 64-bit integers, so `size_t` prevents signed/unsigned comparison overhead and ensures optimal register usage for memory offsets during high-speed execution.

### Simple Iteration (For Most Cases)

Just write natural nested loops. The library handles the rest:

```cpp
Array<double> A(256, 256, 128);

// This works great—write it naturally
for (size_t i = 0; i < A.size(0); ++i) {
    for (size_t j = 0; j < A.size(1); ++j) {
        for (size_t k = 0; k < A.size(2); ++k) {
            A(i, j, k) = i + j + k;
        }
    }
}
```

### Range-Based For Loops (Simplified Iteration)

Use range-based loops for simple element-wise passes when you do not need multi-dimensional indices.

```cpp
Array<double> A(32, 256, 256);

for (auto& elem : A) {
    elem *= 2.0;
}

double sum = 0.0;
for (const auto& elem : A) {
    sum += elem;
}
```

For performance-sensitive or multi-dimensional algorithms, prefer explicit nested loops so you control the access order.

### Bad Loop Ordering (Cache Killer ❌)

Row-major arrays benefit from accessing the **innermost index fastest**. Reversing this causes cache misses:

```cpp
Array<double> A(256, 256);

// ❌ BAD: Accessing the WRONG dimension in the inner loop
// This jumps across 256*8 bytes per iteration (huge cache miss)
for (size_t j = 0; j < A.size(1); ++j) {     // Outermost: columns
    for (size_t i = 0; i < A.size(0); ++i) { // Inner: rows (wrong!)
        A(i, j) = i * j;  // stride jump = 256*8 = 2048 bytes ⚠️
    }
}

// ✅ GOOD: Access the innermost index in the inner loop
// Sequential memory access (cache friendly)
for (size_t i = 0; i < A.size(0); ++i) {     // Outermost: rows
    for (size_t j = 0; j < A.size(1); ++j) { // Inner: columns (correct!)
        A(i, j) = i * j;  // stride jump = 8 bytes ✓
    }
}
```

**Why it matters:** The bad loop can be 10-50x slower due to CPU cache misses on large arrays.

### Ultra-Fast Loops (Advanced)

If a loop bottlenecks your entire algorithm, `Voxel` arrays can be flattened to 1D for vectorization:

```cpp
// Ultra-fast SIMD example: Weighted reconstruction (common in imaging)
// result[i] = A[i] * B[i] - C[i] * alpha + D[i]
// With AVX2 (8 doubles per instruction), processes 8 elements simultaneously

if (A.is_contiguous() && B.is_contiguous() && C.is_contiguous() && D.is_contiguous()) {
    const double* A_data = A.get_data();
    const double* B_data = B.get_data();
    const double* C_data = C.get_data();
    const double* D_data = D.get_data();
    double* result = result_array.get_data();
    
    // Compiler/OpenMP auto-vectorizes: processes 8 elements per iteration (AVX2)
    #pragma omp simd
    for (size_t i = 0; i < A.size(); ++i) {
        result[i] = A_data[i] * B_data[i] - C_data[i] * alpha + D_data[i];
    }
    // SIMD improves throughput on contiguous data
}
```

**Why This Example Matters:**
- **Raw pointer access:** Using `result[i]` avoids the stride computation overhead of multi-dimensional indexing like `result(i,j,k)`. Standard indexing requires O(ndims) multiply-add operations per element; raw pointer access is O(1)
- **Multiple operations:** Multiplication, subtraction, addition allow compiler instruction-level parallelism
- **Contiguity requirement:** SIMD only works on contiguous data—this is why `.contiguous()` matters
- **Real-world use:** Image reconstruction, coil combination, inverse transforms all use weighted accumulation like this
- **Compiler auto-vectorization:** Modern compilers (gcc -O3, clang -O3) automatically vectorize clean loops like this to AVX2/AVX-512 instructions

**Performance:** Exact gains depend on compiler, CPU, data type, and memory bandwidth. The important point is qualitative:
- Multi-dimensional indexing has more overhead than a flat contiguous pointer loop
- SIMD-friendly contiguous loops are usually faster than scalar loops
- Explicit OpenMP can add multicore scaling on top of SIMD when the workload is large enough

**Key Takeaway:** For ultra-hot loops, flatten to 1D (`.flatten().contiguous()`) and use raw pointers to eliminate both stride computation and enable SIMD vectorization.


### Multi-threaded Loops: OpenMP Parallelism

For compute-intensive algorithms, OpenMP directives can be used for explicit CPU parallelization in your own loops. However, improper use of nested parallelism can cause significant overhead.

#### ⚠️ CRITICAL: Only Parallelize the Outermost Loop

**Nested parallelism is extremely expensive.** Each thread spawning additional threads incurs thread creation overhead that dominates the actual computation. Always parallelize only the outermost loop.

**❌ BAD: Nested parallelism (avoid!)**
```cpp
Array<double> A(1000, 1000, 1000);

// BAD: Creating threads for ALL three loops!
#pragma omp parallel for
for (size_t i = 0; i < A.size(0); ++i) {
    #pragma omp parallel for  // ❌ Each outer thread spawns more threads—massive overhead!
    for (size_t j = 0; j < A.size(1); ++j) {
        for (size_t k = 0; k < A.size(2); ++k) {
            A(i, j, k) *= 2.0;
        }
    }
}
// Result: often much slower than a single outer parallel loop due to thread-management overhead
```

**✅ GOOD: Parallelize only outermost loop**
```cpp
Array<double> A(1000, 1000, 1000);

// GOOD: Let each thread handle entire slices
#pragma omp parallel for
for (size_t i = 0; i < A.size(0); ++i) {
    for (size_t j = 0; j < A.size(1); ++j) {
        for (size_t k = 0; k < A.size(2); ++k) {
            A(i, j, k) *= 2.0;  // Sequential inner loops per thread
        }
    }
}
```

#### Scheduling Strategies

OpenMP offers different scheduling models. Choose based on your workload:

**Static Scheduling** (Default)
- Work divided equally before loop starts
- **Use when:** Iterations have similar cost
- **Overhead:** Minimal (no synchronization per iteration)

```cpp
#pragma omp parallel for schedule(static)
for (size_t i = 0; i < 1000000; ++i) {
    process(A[i]);  // Similar work per iteration
}
```

**Dynamic Scheduling**
- Work grabbed by threads as they become idle
- **Use when:** Iteration cost varies significantly
- **Overhead:** Higher (synchronization required)

```cpp
#pragma omp parallel for schedule(dynamic, 128)  // Chunk size 128
for (size_t i = 0; i < 1000000; ++i) {
    if (rand() > 0.5) {
        expensive_operation(A[i]);  // Variable cost—use dynamic!
    } else {
        cheap_operation(A[i]);
    }
}
```

**Guided Scheduling** (Sweet spot)
- Starts with large chunks, decreases over time
- **Use when:** Uncertain about workload distribution
- **Overhead:** Medium

```cpp
#pragma omp parallel for schedule(guided)
for (size_t i = 0; i < 1000000; ++i) {
    process(A[i]);  // Unknown cost pattern
}
```

#### Batch Processing Pattern

For algorithms with variable iteration cost, process in batches rather than scheduling individual iterations:

```cpp
Array<double> A(10000);

// Better than dynamic scheduling: explicitly batch work
size_t batch_size = 100;

#pragma omp parallel for schedule(static)
for (size_t b = 0; b < A.size(0); b += batch_size) {
    size_t end = std::min(b + batch_size, A.size(0));
    
    for (size_t i = b; i < end; ++i) {
        // Variable cost per element
        if (A[i] > threshold) {
            expensive_computation(A[i]);
        }
    }
}
```

#### Real World Example: Coil Sensitivity Multiplication

```cpp
// Multiply each receiver coil by sensitivity map (variable compute per coil)
Array<Complex> image(32, 256, 256);  // 32 coils
Array<Complex> csm(32, 256, 256);    // Sensitivity maps

// Parallelize over coils (each has similar cost)
#pragma omp parallel for schedule(static)
for (size_t c = 0; c < 32; ++c) {
    auto coil_image = image.slice(S(c), S::all(), S::all());
    auto coil_csm = csm.slice(S(c), S::all(), S::all());
    
    // Sequential inner loops—no additional parallelism!
    for (size_t j = 0; j < 256; ++j) {
        for (size_t k = 0; k < 256; ++k) {
            coil_image(j, k) *= coil_csm(j, k);
        }
    }
}
```

#### Performance Tips for Parallelism

| Pattern | Cost per Iteration | Recommended Scheduling |
|---------|-------------------|------------------------|
| Uniform (all similar) | Low | `schedule(static)` |
| Uniform but high | High | `schedule(static)` |
| Variable, medium cost | Medium | `schedule(guided)` |
| Variable, wide range | High | `schedule(dynamic, chunk_size)` |
| Unknown distribution | Unknown | `schedule(guided)` or batches |

#### Checking Optimal Thread Count

Voxel respects the `OMP_NUM_THREADS` environment variable:

```bash
# Use all cores
OMP_NUM_THREADS=0 ./program

# Use specific number
OMP_NUM_THREADS=8 ./program

# Disable parallelism for profiling
OMP_NUM_THREADS=1 ./program
```

Check threads available at runtime:
```cpp
#include <omp.h>

int num_threads = omp_get_max_threads();
std::cout << "Available threads: " << num_threads << std::endl;
```

---

## 2.11 Iteration Optimization: Quick Reference

Choose your iteration strategy based on your needs:

| Scenario | Strategy | Key Consideration |
|----------|----------|-------------------|
| Simple sequential access | Basic nested loops with `size_t` | Easy to read, good CPU cache behavior |
| Cache-sensitive code | Ensure innermost loop accesses innermost dimension | Usually much faster than bad ordering |
| Bottleneck in tight loop | Raw pointer + `#pragma omp simd` on contiguous array | Only after profiling confirms bottleneck |
| Multi-core acceleration | `#pragma omp parallel for` **outermost loop only** | Never nest parallelism—costs outweigh benefits |
| Variable iteration cost | `schedule(dynamic)` or `schedule(guided)` | Prevents thread starvation |
| Unknown workload | Batch processing + `schedule(static)` | More control than pure dynamic scheduling |

**Golden Rule:** Start with simple sequential loops. Profile first. Optimize only where measurements show bottlenecks.

---

## 2.12 Common Pitfalls & How to Avoid Them

**❌ Problem 1: Modifying a slice changes the original**

```cpp
Array<double> original(256, 256);
auto roi = original.slice(S(50, 100), S::all());

roi.fill(0.0);  // ⚠️ This also zeros the original!
```

**✅ Solution:** Use `.copy()` if you need independence:
```cpp
auto roi_copy = original.slice(S(50, 100), S::all()).copy();
roi_copy.fill(0.0);  // ✓ Original untouched
```

---

**❌ Problem 2: Expecting in-place backend processing on a non-contiguous view**

```cpp
auto transposed = A.transpose(1, 0, 2);  // Non-contiguous view
FFTW::fftn(transposed, transposed, FFTW::ImageToKspace);  // ⚠️ Not truly in-place on the original view
```

**What actually happens:** FFTW and LinAlg wrappers accept non-contiguous inputs by calling `.contiguous()` internally when needed. That means the operation still works, but the backend runs on a temporary contiguous copy, not directly on the original view. For FFTW specifically, a non-contiguous input prevents true in-place processing.

**✅ Solution 1 (Preferred):** Make contiguity explicit before calling the backend:
```cpp
auto transposed = A.transpose(1, 0, 2);
auto work = transposed.contiguous();
FFTW::fftn(work, work, FFTW::ImageToKspace);  // ✓ True in-place processing on contiguous storage
```

**✅ Solution 2:** Let the wrapper handle the copy when you do not need in-place behavior:
```cpp
auto transposed = A.transpose(1, 0, 2);
FFTW::fftn(transposed, output, FFTW::ImageToKspace);  // ✓ Safe, but may allocate/copy internally
```

**Key Insight:** Non-contiguous arrays are supported, but they may force an internal copy. Use `.contiguous()` yourself when you want predictable memory behavior or true in-place FFT processing.

---

**❌ Problem 3: Forgetting bounds checking during development**

```cpp
// Compiles and runs but accesses garbage data
Array<double> A(100, 100);
A(200, 50) = 5.0;  // ⚠️ Out of bounds! Silent corruption.
```

**✅ Solution:** Use `gpi_make --debug`:
```bash
$ gpi_make MyModule --debug
# Now out-of-bounds access throws clear error ✓
```

---

**❌ Problem 4: Creating arrays inside loops**

```cpp
for (int iter = 0; iter < 1000; ++iter) {
    Array<double> temp(256, 256);  // ⚠️ Allocates 1000 times!
    // ... use temp ...
}
```

**✅ Solution:** Create once, reuse:
```cpp
Array<double> temp(256, 256);  // Allocate once
for (int iter = 0; iter < 1000; ++iter) {
    temp.fill(0.0);  // Reset
    // ... use temp ...
}
```

---

**❌ Problem 5: Comparing views from different sources**

```cpp
auto roi1 = A.slice(S(0, 10), S::all());
auto roi2 = B.slice(S(0, 10), S::all());

if (roi1 == roi2) { }  // ⚠️ Compares memory addresses, not values!
```

**✅ Solution:** Explicitly compare values:
```cpp
auto roi1 = A.slice(S(0, 10), S::all());
auto roi2 = B.slice(S(0, 10), S::all());

bool same_values = (sum(abs(roi1 - roi2)) < 1e-10);  // ✓ Value comparison
```

---

## 2.13 Error Handling & Debugging

The library prevents silent crashes and memory corruption by throwing `ArrayException` when dimension mismatches or out-of-bounds slicing occurs.

**Strict Bounds Checking:**
To maintain peak performance in production, **bounds are not checked by default** during coordinate-based indexing or slicing. To enable exhaustive safety checks during development, you must pass the `--debug` flag to the `gpi_make` build tool.

* **`THROW_INVALID_ARGUMENT(msg)`**: Triggered by shape parity or boundary errors when debug mode is enabled. Captures the `__FILE__` and `__LINE__` for rapid debugging.
* **`THROW_RUNTIME_ERROR(msg)`**: Triggered by external backend failures, such as FFTW plan allocation issues or Eigen solver errors.
