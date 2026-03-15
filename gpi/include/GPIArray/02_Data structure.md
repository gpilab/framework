# Section 2: Core Data Structures

The foundation of the library is the `GPIArray::Array<T>` container. It mimics NumPy's semantics while enforcing C++ memory safety and optimizing for zero-allocation scientific workflows.

## 2.1 Querying Shape and Size

Understanding the geometry of your data is critical for multi-dimensional processing. `GPIArray` provides high-level methods to query both the total volume and specific axis lengths.

* **.shape()**: Returns an `ArrayDimensions` object. It can be printed directly to `std::cout` for debugging.
* **.size()**: Returns the total number of elements in the array (the product of all dimensions).
* **.size(i)**: Returns the size of the $i$-th dimension. Passing `0` returns the first dimension.
* **Negative Indexing**: Similar to NumPy, passing `-1` to size methods (e.g., `.size(-1)`) returns the size of the **last** dimension.

**Example:**

```cpp
Array<Complex> A(20, 32, 256, 256);

// Printing the shape directly to console
std::cout << A.shape() << std::endl; 
// Output: ArrayDimensions 4D (20, 32, 256, 256)

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
│  │  ├─ Match shape of original? → Array(original.shape())
│  │  └─ Uninitialized? → .empty_like()
│  │
│  └─ No: Do you want to MODIFY the original?
│     ├─ Yes (modifying OK) → Use .slice() or .transpose() directly
│     └─ No (preserve original) → .copy() first, then modify
│
└─ Will you pass it to FFT or Linear Algebra?
   ├─ Yes → Call .is_contiguous() first
   │        If false → Use .copy() before passing
   └─ No → Any layout is fine
```

**Quick Reference:**
| I want to... | Use this | Creates copy? |
|--------------|----------|---------------|
| Extract a region | `.slice()` | ❌ No (view) |
| Reshape without moving data | `.reshape()` | ❌ No (view) |
| Rotate dimensions | `.transpose()` | ❌ No (view) |
| Guarantee contiguous + new | `.copy()` | ✅ Yes |
| Create zero array | `.zeros_like()` | ✅ Yes |
| Extract data for FFT | Check `.is_contiguous()`, use `.copy()` if needed | ✅ Maybe |

---

## 2.2 Performance Tip: Indexing Datatypes

For indexing variables, loop counters, and offset math, it is **highly recommended** to use the `size_t` (or `uint64_t`) datatype. Because the library's internal address calculation logic uses unsigned 64-bit integers, using `size_t` prevents signed/unsigned comparison overhead and ensures optimal register usage for memory offsets during high-speed execution.

## 2.3 Array Instantiation & Examples

`Array<T>` provides several ways to instantiate tensors. To prevent memory fragmentation, factory methods that allocate memory should generally be used during initialization phases rather than inside iterative loops.

### Standard Constructors (Direct Size Overloads)

Convenience constructors for 1D through 10D arrays allow you to pass dimension sizes directly as arguments rather than wrapping them in a vector.

```cpp
using namespace GPIArray;

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

Use the static `zeros`, `ones`, or `rand` methods to create initialized memory from scratch.

```cpp
auto zeros_vol = Array<double>::zeros(32, 64, 64);
auto noise     = Array<Complex>::rand(64, 64, 64); // Uniform [0, 1]

```

## 2.4 Clone Factories & Data Duplication

Clone factories allow you to create new arrays based on the properties of an existing instance. This allows for a fluent, readable syntax when preparing auxiliary buffers or workspace arrays.

| Method | Description |
| --- | --- |
| **`.copy()`** | Performs a deep copy, ensuring the new instance is contiguous and owning. |
| **`.empty_like()`** | Returns a new array with matching shape/type but uninitialized memory. |
| **`.zeros_like()`** | Returns a new array with matching shape/type, initialized to zero. |
| **`.ones_like()`** | Returns a new array with matching shape/type, initialized to one. |

**Examples:**

```cpp
// 1. Deep copy an existing array (forces contiguity)
auto arr_copy = original_arr.copy();

// 2. Create a zero-initialized array matching the target data shape and type
auto zero_buffer = target_data.zeros_like();

// 3. Create an array of all ones matching the target shape and type
auto ones_buffer = target_data.ones_like();

```

## 2.5 Memory Properties: Contiguity and Ownership

To safely interface with low-level backends and manage memory lifecycles, `Array<T>` exposes two critical state flags.

### `.is_contiguous()`

Returns `true` if the array elements are laid out sequentially in memory without any gaps.

* **Importance:** High-speed backends (FFTW, Eigen) and SIMD loops require contiguous memory to function correctly.
* **State Change:** Operations like `.transpose()` or inner-dimension `.slice()` will typically render an array non-contiguous.

### `.is_owning()`

Returns `true` if the specific `Array` instance is the primary owner of the memory buffer.

* **Ownership vs. Views:** A primary array created via a constructor or factory is "owning." A view created via `.slice()` or `.reshape()` is "non-owning," meaning it points to the memory of another array.

## 2.6 Array Operations & Manipulation

These operations reorganize data layout. Most return **views** (zero-allocation) unless otherwise noted.

| Method | Description | Example |
| --- | --- | --- |
| **`.fill(val)`** | Fills the entire array with a scalar value in-place. | `A.fill(0.0);` |
| **`.reshape(dims)`** | Changes dimensions without moving data. Elements must match. | `A.reshape(32, 65536);` |
| **`.resize(dims)`** | Changes array size. **May reallocate** if total size changes. | `A.resize(10, 128, 128);` |
| **`.transpose(axes)`** | Permutes dimensions. Returns a non-contiguous view. | `A.transpose(0, 2, 1);` |
| **`.flatten()`** | Collapses all dimensions into a single 1D vector view. | `auto vec = A.flatten();` |
| **`.squeeze()`** | Removes all dimensions of size 1. | `B.squeeze();` |
| **`.add_singleton_dimension(i)`** | Inserts a new dimension of size 1 at index $i$. | `A.add_singleton_dimension(0);` |

## 2.7 Changing Datatypes (Casting)

To change the datatype of an existing array (e.g., converting `float` to `double`), use the explicit constructor syntax. This performs a deep copy of the data.

```cpp
Array<float> A_float(256, 256);

// Convert real data to complex (imaginary part becomes 0.0)
Array<Complex> C_complex(A_float);

```

## 2.8 Slicing (`S`)

`GPIArray` uses the `S` shorthand for slicing. **All indices and ranges must be wrapped in the `S()` constructor.** Slicing returns a non-owning view.

* **`S(index)`**: Selects a single index.
* **`S(start, stop)`**: Selects a range from start up to stop (exclusive).
* **`S(start, stop, step)`**: Selects a strided range.
* **`S::all()`**: Selects the entire dimension.
* **`S::center()`**: Picks the middle index of the dimension.
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

// 4. Slicing with .copy()
// It is highly recommended to create a copy if the resulting view will be used 
// for heavy loops multiple times later.
auto contiguous_block = strided_view.copy();

```

## 2.9 Iterating Over Arrays

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

If a loop bottlenecks your entire algorithm, `GPIArray` arrays can be flattened to 1D for vectorization:

```cpp
// Ultra-fast: For contiguous arrays, use raw pointer + SIMD
if (A.is_contiguous()) {
    double* data = A.get_data();
    #pragma omp simd
    for (size_t i = 0; i < A.size(); ++i) {
        data[i] *= 2.0;
    }
}
```

---

## 2.10 Common Pitfalls & How to Avoid Them

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

**❌ Problem 2: Passing non-contiguous arrays to FFT**

```cpp
auto transposed = A.transpose(1, 0, 2);  // Non-contiguous view
FFTW::fftn(transposed, output, FFTW::ImageToKspace);  // ⚠️ May fail or produce wrong results
```

**✅ Solution:** Check and copy:
```cpp
auto transposed = A.transpose(1, 0, 2);
if (!transposed.is_contiguous()) {
    transposed = transposed.copy();  // Force contiguous
}
FFTW::fftn(transposed, output, FFTW::ImageToKspace);  // ✓ Safe
```

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

## 2.11 Error Handling & Debugging

The library prevents silent crashes and memory corruption by throwing `ArrayException` when dimension mismatches or out-of-bounds slicing occurs.

**Strict Bounds Checking:**
To maintain peak performance in production, **bounds are not checked by default** during coordinate-based indexing or slicing. To enable exhaustive safety checks during development, you must pass the `--debug` flag to the `gpi_make` build tool.

* **`THROW_INVALID_ARGUMENT(msg)`**: Triggered by shape parity or boundary errors when debug mode is enabled. Captures the `__FILE__` and `__LINE__` for rapid debugging.
* **`THROW_RUNTIME_ERROR(msg)`**: Triggered by external backend failures, such as FFTW plan allocation issues or Eigen solver errors.