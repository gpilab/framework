
# Section 3: Mathematical Operations & Linear Algebra

`Voxel` provides a high-performance computational engine divided into two distinct paradigms: **element-wise operations** powered by SIMD-oriented kernels in `ArrayMathOps.hpp`, and **matrix-level linear algebra** powered by Eigen mappings in `LINALG_WRAPPER.hpp` (with internal contiguity copies when needed).

## 3.0 Quick Start: Common Workflows

### Element-wise Arithmetic
```cpp
Array<Complex> A(100, 50);
Array<Complex> B(50, 32);

auto C = A + A;
auto D = 2.0 * A;
```

### Point-wise Math
```cpp
Array<Complex> signal(256, 256);

auto magnitude = abs(signal);
auto phase = angle(signal);
```

### Reductions
```cpp
Array<double> image(256, 256);

double total = sum(image);
double mean_val = mean(image);
```

### Linear Algebra
```cpp
Array<Complex> A(100, 50);
Array<Complex> B(50, 32);

Array<Complex> C(A.dimensions(0), B.dimensions(1));
LinAlg::matmul(A, B, C);  // C = A @ B
```

---

## 3.1 Element-wise Arithmetic

The library supports a full suite of element-wise operators with automatic type promotion (e.g., adding an `Array<float>` to an `Array<double>` returns an `Array<double>`).

### Standard Operators

```cpp
using namespace Voxel;

Array<Complex> A(256, 256);
Array<Complex> B(256, 256);

auto C = A + B;       // Hadamard addition
auto D = A * B;       // Element-wise multiplication
auto E = A / 2.0;     // Scalar division
auto F = 5.0 - A;     // Scalar subtraction (Scalar vs Array)

```

### In-place Operators

In-place operators (`+=`, `-=`, `*=`, `/=`) modify the existing memory directly.

> [!CAUTION]
> **In-Place Operations:** In-place operators modify the array's current storage directly. Contiguous arrays get the SIMD fast path, but non-contiguous views can still be updated through the slower stride-aware path.

```cpp
A += B;            // Add B to A in-place
A *= 2.0;          // Scale A by 2.0 in-place
A -= Complex(0,1); // Subtract imaginary unit in-place

```

## 3.2 Broadcasting: Operating on Different Shapes

`Voxel::Array<T>` supports **NumPy-compatible broadcasting** for all arithmetic, comparison, and assignment operators. Broadcasting allows you to perform element-wise operations on arrays with different shapes—as long as they are compatible according to NumPy's broadcasting rules.

### Broadcasting Rules

Broadcasting aligns array dimensions from the **right** and applies the following rules:

1. **Dimension Alignment:** Dimensions are compared from right to left. Missing dimensions are treated as size 1.
2. **Size Compatibility:** For each dimension pair:
   - If sizes are equal, proceed.
   - If one size is 1, broadcast it to match the other.
   - If neither is 1 and they differ, raise an error.
3. **Output Shape:** The result shape is the element-wise maximum of input shapes.

**Example:**
```
Shape A:    (3, 1, 5)
Shape B:    (1, 4, 5)
           ─────────── 
Result:     (3, 4, 5)   ← Broadcast dimension 1 from size 1 to 4
```

### Supported Operators

All element-wise operators support broadcasting:

| Category | Operators |
|----------|-----------|
| **Arithmetic** | `+`, `-`, `*`, `/` (binary and in-place `+=`, `-=`, `*=`, `/=`) |
| **Comparison** | `==`, `!=`, `<`, `<=`, `>`, `>=` (return `Array<bool>`) |
| **Scalar Operations** | All operators work with scalar values on either side |

### Common Broadcasting Examples

**Example 1: Add a vector to matrix columns**
```cpp
Array<double> matrix(3, 4);      // Shape (3, 4)
Array<double> vec(4);            // Shape (4,)
auto result = matrix + vec;      // Broadcasting adds vec to each row
// Result shape: (3, 4)
```

**Example 2: Element-wise multiply with shape (3,1,5) and (1,4,5)**
```cpp
Array<Complex> A(3, 1, 5);       // coils × 1 × freq
Array<Complex> B(1, 4, 5);       // 1 × slices × freq
auto product = A * B;            // Broadcasts to (3, 4, 5)
// Each coil multiplied with each slice at matching frequencies
```

**Example 3: Scalar broadcasting**
```cpp
Array<double> arr(100, 100);
auto scaled = arr * 2.0;         // Every element × 2
auto normalized = arr / sum(arr); // Apply scalar normalization
```

**Example 4: In-place addition with broadcasting**
```cpp
Array<Complex> accumulator(32, 256, 256);  // Output accumulator
Array<Complex> coil_data(1, 256, 256);     // Single coil

// Add coil_data (broadcasted) to each coil slot
accumulator += coil_data;
// 'coil_data' is automatically broadcasted from (1,256,256) to (32,256,256)
```

### Checking Broadcastability

Use `is_broadcastable_to()` to check if a broadcast is valid **without throwing an exception:**

```cpp
Array<double> A(3, 1, 5);
Array<double> B(1, 4, 5);

// Check if A can broadcast to B's shape
if (A.is_broadcastable_to(B.shape())) {
    auto result = A * B;  // Safe to perform
}

// Check against explicit target shape
std::vector<uint64_t> target_shape = {3, 4, 5};
if (A.is_broadcastable_to(target_shape)) {
    auto broadcasted = A.broadcast_to(target_shape);  // Zero-copy view
}
```

### Manual Broadcasting (Advanced)

For fine-grained control, explicitly broadcast an array to a target shape:

```cpp
Array<double> A(3, 1, 5);

// Broadcast to (3, 4, 5) without copying data
// Returns a zero-allocation view with adjusted strides
auto A_broadcast = A.broadcast_to({3, 4, 5});

// Now A_broadcast can be used in operations without memory overhead
auto result = A_broadcast * B;
```

**Memory Efficiency:** `broadcast_to()` returns a **view** with adjusted strides—it does not copy data. Dimension(s) with size 1 get stride 0, allowing hardware to repeat the single element efficiently.

### Performance Characteristics

- **Broadcasting itself:** Zero-copy; uses stride manipulation only.
- **Operators:** Element-wise operations are efficient on both contiguous and broadcasted arrays.
- **Optimal case:** Contiguous arrays with `#pragma omp simd` for SIMD vectorization.

```cpp
// Tight loop: multiply with broadcast (efficient)
Array<Complex> A(32, 1, 256, 256);  // Batch × 1 × height × width
Array<Complex> B(1, 4, 256, 256);   // 1 × slices × height × width

// Broadcasts A to (32, 4, 256, 256) internally—no allocation
auto result = A * B;

// If loops are a bottleneck, use raw pointers + simd on contiguous result
if (result.is_contiguous()) {
    Complex* data = result.get_data();
    #pragma omp simd
    for (size_t i = 0; i < result.size(); ++i) {
        data[i] *= factor;  // Vectorized by compiler
    }
}
```

### Error Handling

If arrays cannot broadcast together, an exception is thrown with a clear error message:

```cpp
Array<double> A(3, 4);
Array<double> B(2, 5);

auto result = A + B;  // Throws: "Operands could not be broadcast together"
```

---

## 3.3 Relational & Boolean Operations

Boolean operators (`==`, `!=`, `<`, `<=`, `>`, `>=`) return an `Array<bool>`.
For `std::complex<T>` arrays, inequalities (like `<` or `>=`) are automatically evaluated based on the **magnitude** ($|z|$) of the complex numbers.

```cpp
Array<bool> mask = (A > 0.5);
Array<bool> is_equal = (A == B);

// Aggregate boolean counts using the specialized count() function
uint64_t true_elements = count(mask);

```

## 3.4 Universal Math Functions

These point-wise functions use the library's contiguous fast paths and may benefit from SIMD-oriented compilation.

### Complex Number Operations

For complex arrays:
* **`abs(A)`** → $|z_i|$ (Returns real-valued magnitude array)
* **`angle(A)`** → $\arg(z_i)$ (Returns real-valued phase array in $[-\pi, \pi]$)
* **`real(A)`** → $\text{Re}(z_i)$ (Extracts real component)
* **`imag(A)`** → $\text{Im}(z_i)$ (Extracts imaginary component)
* **`conj(A)`** → $z_i^*$ (Complex conjugate)

### Standard Math Functions

* **Algebraic:** `sqrt`, `cbrt`, `exp`, `log`, `log2`, `log10`, `pow(base, expn)`.
* **Trigonometric:** `sin`, `cos`, `tan`, `asin`, `acos`, `atan`, `sinh`, `cosh`, `tanh`.
* **Rounding & Clamping:** `floor`, `ceil`, `round`, `trunc`, `clamp(A, lo, hi)`.

## 3.5 Reductions & Vector Operations

Reductions collapse an array into a scalar. When arrays are contiguous, different functions take different fast paths: some use `std::accumulate`/`std::min_element`/`std::max_element`, while others use SIMD reductions.

### Standard Reductions

| Function | Mathematical Notation | NumPy Equivalent |
|----------|-----|----------|
| `sum(A)` | $\sum_i A_i$ | `np.sum(A)` |
| `mean(A)` | $\frac{1}{N}\sum_i A_i$ | `np.mean(A)` |
| `prod(A)` | $\prod_i A_i$ | `np.prod(A)` |
| `max(A)` | $\max_i A_i$ | `np.max(A)` |
| `min(A)` | $\min_i A_i$ | `np.min(A)` |
| `stdev(A)` | $\sqrt{\frac{1}{N}\sum_i (A_i - \bar{A})^2}$ | `np.std(A)` |

### Norms and Dot Products

```cpp
// 1. Vector Products
auto d_prod = dot(vecA, vecB);                 // $\sum_i A_i B_i^*$
auto o_prod = outer_product(vecA, vecB);       // $AB^H$ (requires 1D arrays)

// 2. Norms
double l1 = l1norm(A);                         // $\|A\|_1 = \sum_i |A_i|$
double l2 = l2norm(A);                         // $\|A\|_2 = \sqrt{\sum_i |A_i|^2}$ (Frobenius)
double linf = linfnorm(A);                     // $\|A\|_\infty = \max_i |A_i|$
double lp = lpnorm(A, 3.0);                    // $\|A\|_p = \left(\sum_i |A_i|^p\right)^{1/p}$

// For complex arrays:
auto c_norm = norm(complex_array);             // $\langle A, A \rangle = \sum_i |A_i|^2$
```

**NumPy Equivalents:**
```python
np.linalg.norm(A, ord=1)        # L1 norm
np.linalg.norm(A, ord=2)        # L2 norm
np.linalg.norm(A, ord=np.inf)   # L-infinity norm
```

---

## 3.6 Linear Algebra Backend (`LinAlg`)

The `Voxel::LinAlg` namespace maps array memory directly to Eigen matrices using `Eigen::Map`.

> [!NOTE]
> **Smart Contiguity Handling:** All LinAlg functions automatically handle non-contiguous input arrays. If an input is non-contiguous, it's transparently copied internally before processing. The original array is never modified.
>
> **Output Requirement:** Output arrays must be pre-allocated and contiguous to avoid hidden allocations. This ensures predictable performance.

- `LinAlg::matmul(A, B, C)`
- `auto C = LinAlg::matmul(A, B)`
- `LinAlg::svd(A, U, S, Vh, LinAlg::Thin)` or `LinAlg::svd(A, U, S, Vh, LinAlg::Full)`
- `auto [U, S, Vh] = LinAlg::svd(A, LinAlg::Thin)` or `LinAlg::svd(A, LinAlg::Full)`
- `LinAlg::pca(data, pc, var)`
- `auto [pc, var] = LinAlg::pca(data)`
- `LinAlg::solve_cholesky(A, b, x)`
- `auto x = LinAlg::solve_cholesky(A, b)`
- `LinAlg::solve_qr(A, b, x)`
- `auto x = LinAlg::solve_qr(A, b)`
- `LinAlg::hermitian(A, A_H)`
- `auto A_H = LinAlg::hermitian(A)`

### Method Summary

| Method | Purpose | In-place Syntax | Overload Syntax |
|-------|---------|-----------------|-----------------|
| `matmul` | Matrix multiplication | `LinAlg::matmul(A, B, C)` | `auto C = LinAlg::matmul(A, B)` |
| `svd` | Singular value decomposition | `LinAlg::svd(A, U, S, Vh, LinAlg::Thin)` | `auto [U, S, Vh] = LinAlg::svd(A, LinAlg::Thin)` |
| `pca` | Principal component analysis | `LinAlg::pca(data, pc, var)` | `auto [pc, var] = LinAlg::pca(data)` |
| `solve_cholesky` | Solve Hermitian positive-definite systems | `LinAlg::solve_cholesky(A, b, x)` | `auto x = LinAlg::solve_cholesky(A, b)` |
| `solve_qr` | Solve general / least-squares systems | `LinAlg::solve_qr(A, b, x)` | `auto x = LinAlg::solve_qr(A, b)` |
| `hermitian` | Conjugate transpose | `LinAlg::hermitian(A, A_H)` | `auto A_H = LinAlg::hermitian(A)` |

### API Style

Most `LinAlg` methods are available in two forms:

1. Pre-allocated output arguments for buffer reuse.
2. Return-value overloads for simpler one-off calls.

### General Matrix Multiplication (GEMM)

Computes $C = AB$ where $A$ is $(m \times n)$ and $B$ is $(n \times p)$, yielding $C$ as $(m \times p)$.

**Typical use:** Forward models, basis projections, covariance updates, and any dense matrix product.

```cpp
Array<Complex> A(100, 50);
Array<Complex> B(50, 32);
Array<Complex> C(A.dimensions(0), B.dimensions(1));

LinAlg::matmul(A, B, C);
auto C2 = LinAlg::matmul(A, B);
```

| NumPy | Voxel |
|-------|----------|
| `C = A @ B` | `LinAlg::matmul(A, B, C)` |
| `C = A @ B` | `auto C = LinAlg::matmul(A, B)` |

### Singular Value Decomposition (SVD)

Decomposes $A = U \Sigma V^H$, where:
- $U$ is $(m \times k)$ with orthonormal columns
- $\Sigma$ is $(k)$ (diagonal singular values in descending order)
- $V^H$ is $(k \times n)$ (conjugate transpose of $V$)

**Voxel always returns** $V^H$ (not $V$) **to match standard MRI conventions**.

```cpp
Array<Complex> A(256, 128);

uint64_t k = std::min(A.dimensions(0), A.dimensions(1));  // min(256, 128) = 128

Array<Complex> U(256, k);      // Orthonormal left vectors
Array<double> S(k);             // Singular values (always real!)
Array<Complex> Vh(k, 128);      // Conjugate-transpose of right vectors

// Compute full SVD
LinAlg::svd(A, U, S, Vh, LinAlg::Full);

// Thin SVD uses k = min(m, n)
LinAlg::svd(A, U, S, Vh, LinAlg::Thin);
```

**NumPy Equivalents:**
```python
U, S, Vh = np.linalg.svd(A, full_matrices=False)  # Thin SVD
U, S, Vh = np.linalg.svd(A, full_matrices=True)   # Full SVD
```

---

### Principal Component Analysis (PCA)

Designed for coil compression and temporal subspace estimation. Automatically mean-centers features (columns) before computing SVD.

**Input:** $(N \times D)$ array where $N$ = samples, $D$ = features

**Output:** 
- Principal components: $(K \times D)$ (the dominant directions)
- Variances: $(K)$ (explained variance per component, sorted descending)

```cpp
// Example: Compress 32 coils to 10 principal components
Array<Complex> data(1200, 32);         // 1200 timepoints, 32 coils

uint64_t k = std::min(data.dimensions(0), data.dimensions(1));
Array<Complex> pc(k, 32);             // Principal components returned by the current API
Array<double> var(k);                 // Explained variance per component

LinAlg::pca(data, pc, var);

// Check how much variance is retained
double total_var = sum(var);
double variance_explained_pct = 100.0 * total_var / sum(variance all dataset);
```

**NumPy Equivalent (full-rank output):**
```python
from sklearn.decomposition import PCA
pca = PCA(n_components=min(data.shape))
pca.fit(data)
pc = pca.components_
var = pca.explained_variance_
```

---

### Cholesky Solver

```cpp
Array<Complex> A_hpd(128, 128);
Array<Complex> b1(128, 1);
Array<Complex> x1(128, 1);

LinAlg::solve_cholesky(A_hpd, b1, x1);
auto x1_auto = LinAlg::solve_cholesky(A_hpd, b1);
```

Use `solve_cholesky` when $A$ is square, Hermitian, and positive-definite. This is typically the fastest solver in the library for that class of problems.

**Typical use:** Covariance systems, regularized normal equations, and other SPD/Hermitian systems.

### QR Solver

```cpp
Array<Complex> A_ls(256, 50);
Array<Complex> b2(256, 1);
Array<Complex> x2(50, 1);

LinAlg::solve_qr(A_ls, b2, x2);
auto x2_auto = LinAlg::solve_qr(A_ls, b2);
```

Use `solve_qr` for general systems and least-squares problems, especially when the system is rectangular or when Cholesky assumptions do not hold.

**Typical use:** Data fitting, overdetermined systems, and robust general-purpose solves.

### Hermitian Transpose

```cpp
Array<Complex> A(64, 32);
Array<Complex> A_H(32, 64);

LinAlg::hermitian(A, A_H);
auto A_H_auto = LinAlg::hermitian(A);
```

Computes the conjugate transpose $A^H$, which is the standard transpose for complex-valued linear algebra.

**Typical use:** Building Gram matrices, adjoint operators, and expressions like $A^H A$.

---

### Convenience Overloads: Auto-Allocation with Return Values

All linear algebra operations have **dual API**:

1. **In-place API**: you allocate outputs and pass them in.
2. **Overload API**: the function allocates outputs and returns them.

### Comparison: In-Place vs Overload

```cpp
// ====== IN-PLACE API (Good for hot loops) ======
Array<Complex> U(256, 128);
Array<double> S(128);
Array<Complex> Vh(128, 128);

for (int iter = 0; iter < 10000; ++iter) {
    Array<Complex> A = generate_matrix();
    // Reuse U, S, Vh across iterations - no new allocations!
    LinAlg::svd(A, U, S, Vh, LinAlg::Thin);
    process_decomposition(U, S, Vh);
}

// ====== OVERLOAD API (Convenient, allocates per call) ======
for (int iter = 0; iter < 10000; ++iter) {
    Array<Complex> A = generate_matrix();
    // Auto-allocates U, S, Vh
    auto [U, S, Vh] = LinAlg::svd(A, LinAlg::Thin);
    process_decomposition(U, S, Vh);
}
```

### Available Overloads

#### Matrix Multiplication

```cpp
// In-place (requires pre-allocation)
Array<Complex> C(m, p);
LinAlg::matmul(A, B, C);

// Overload (auto-allocates)
auto C = LinAlg::matmul(A, B);  // Returns Array<Complex>
```

#### SVD

```cpp
// In-place
Array<Complex> U(m, k);
Array<double> S(k);
Array<Complex> Vh(k, n);
LinAlg::svd(A, U, S, Vh, LinAlg::Thin);

// Overload - Returns tuple<U, S, Vh>
auto [U, S, Vh] = LinAlg::svd(A, LinAlg::Thin);
```

#### PCA

```cpp
// In-place
Array<Complex> pc(k, n);
Array<double> var(k);
LinAlg::pca(data, pc, var);

// Overload - Returns tuple<principal_components, variances>
auto [pc, var] = LinAlg::pca(data);
```

#### Linear Solvers (Cholesky & QR)

```cpp
// In-place
Array<Complex> x(n, rhs_cols);
LinAlg::solve_cholesky(A, b, x);

// Overload - Returns solution directly
auto x = LinAlg::solve_cholesky(A, b);
auto x = LinAlg::solve_qr(A, b);
```

#### Hermitian Transpose

```cpp
// In-place
Array<Complex> A_H(n, m);
LinAlg::hermitian(A, A_H);

// Overload - Returns conjugate transpose
auto A_H = LinAlg::hermitian(A);
```

### When to Use Which API

| Scenario | Use |
|----------|-----|
| **Hot loop** (10k+ iterations) | In-place API - reuse buffers |
| **One-off computation** | Overload API - simpler code |
| **Memory-critical code** | In-place API - avoid allocations |
| **Prototyping / Research** | Overload API - cleaner syntax |
| **GPU acceleration** | In-place API - better scheduling |

---

## 3.7 Troubleshooting Linear Algebra Operations

### Problem: "Output array must be contiguous"

**Cause:** LinAlg wrappers auto-copy non-contiguous inputs, but they expect the output array you provide to already be contiguous.

**Solution:**
```cpp
auto mat = original.transpose(1, 0);  // Non-contiguous input is fine
Array<Complex> C(mat.dimensions(0), B.dimensions(1));  // Newly allocated, contiguous output
LinAlg::matmul(mat, B, C);  // Safe ✓
```

### Problem: "Shapes don't match" in matrix multiplication

**Cause:** Forgetting that matmul(A, B, C) requires C to be pre-allocated with the right dimensions.

**Solution:**
```cpp
// ❌ Wrong: C is not allocated
Array<Complex> C;
LinAlg::matmul(A, B, C);  // Throws: output array C is incorrectly shaped

// ✅ Correct: Pre-allocate C
Array<Complex> C(A.dimensions(0), B.dimensions(1));
LinAlg::matmul(A, B, C);  // OK ✓

// ✅ Or use overload (auto-allocates)
auto C = LinAlg::matmul(A, B);
```

### Problem: Cholesky fails with "matrix is not positive definite"

**Cause:** Your matrix isn't actually positive definite (or is numerically ill-conditioned).

**Solution:**
```cpp
// Try QR instead (slower but more robust)
auto x = LinAlg::solve_qr(A, b);

// Or add a small regularization term
Array<Complex> A_reg = A;
for (uint64_t i = 0; i < A.dimensions(0); ++i) {
    A_reg(i, i) += Complex(1e-6, 0);  // Add small value to diagonal
}
auto x = LinAlg::solve_cholesky(A_reg, b);
```
