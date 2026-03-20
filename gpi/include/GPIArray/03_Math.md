
# Section 3: Mathematical Operations & Linear Algebra

`GPIArray` provides a high-performance computational engine divided into two distinct paradigms: **element-wise operations** powered by SIMD-oriented kernels in `ArrayMathOps.hpp`, and **matrix-level linear algebra** powered by Eigen mappings in `LINALG_WRAPPER.hpp` (with internal contiguity copies when needed).

## 3.0 Quick Start: Common Workflows

### Matrix Multiplication
```cpp
Array<Complex> A(100, 50);
Array<Complex> B(50, 32);

Array<Complex> C(A.dimensions(0), B.dimensions(1));
LinAlg::matmul(A, B, C);  // C = A @ B
```

### Singular Value Decomposition
```cpp
Array<Complex> A(256, 128);

uint64_t k = std::min(A.dimensions(0), A.dimensions(1));
Array<Complex> U(256, k);
Array<double> S(k);
Array<Complex> Vh(k, 128);

LinAlg::svd(A, U, S, Vh, LinAlg::Thin);  // A = U @ diag(S) @ Vh
```

### Principal Component Analysis
```cpp
Array<Complex> data(1000, 50);  // 1000 samples, 50 features

uint64_t k = std::min(data.dimensions(0), data.dimensions(1));
Array<Complex> pc(k, 50);       // Principal components returned by the current API
Array<double> var(k);           // Explained variances

LinAlg::pca(data, pc, var);
```

### Solving Linear Systems
```cpp
Array<Complex> A_matrix(128, 128);  // Hermitian positive-definite
Array<Complex> b_vector(128, 1);
Array<Complex> solution(128, 1);

LinAlg::solve_cholesky(A_matrix, b_vector, solution);
```

---

## 3.1 Element-wise Arithmetic

The library supports a full suite of element-wise operators with automatic type promotion (e.g., adding an `Array<float>` to an `Array<double>` returns an `Array<double>`).

### Standard Operators

```cpp
using namespace GPIArray;

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

## 3.2 Relational & Boolean Operations

Boolean operators (`==`, `!=`, `<`, `<=`, `>`, `>=`) return an `Array<bool>`.
For `std::complex<T>` arrays, inequalities (like `<` or `>=`) are automatically evaluated based on the **magnitude** ($|z|$) of the complex numbers.

```cpp
Array<bool> mask = (A > 0.5);
Array<bool> is_equal = (A == B);

// Aggregate boolean counts using the specialized count() function
uint64_t true_elements = count(mask);

```

## 3.3 Universal Math Functions

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

## 3.4 Reductions & Vector Operations

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

## 3.5 When to Use Which Solver?

Choose the right solver based on your matrix properties:

```
Is A square?
├─ NO → Use QR factorization (LinAlg::solve_qr) for least squares
│
└─ YES → Is A symmetric/Hermitian positive-definite?
   ├─ YES → Use Cholesky (LinAlg::solve_cholesky) - FASTEST ✓
   │
   └─ NO → Use QR factorization (LinAlg::solve_qr) - numerically stable
```

---

## 3.6 Linear Algebra Backend (`LinAlg`)

The `GPIArray::LinAlg` namespace maps array memory directly to Eigen matrices using `Eigen::Map`.

> [!NOTE]
> **Smart Contiguity Handling:** All LinAlg functions automatically handle non-contiguous input arrays. If an input is non-contiguous, it's transparently copied internally before processing. The original array is never modified.
>
> **Output Requirement:** Output arrays must be **pre-allocated and contiguous** to avoid hidden allocations. This ensures predictable performance.

### General Matrix Multiplication (GEMM)

Computes $C = AB$ where $A$ is $(m \times n)$ and $B$ is $(n \times p)$, yielding $C$ as $(m \times p)$.

**Example with non-contiguous input (handled automatically):**

```cpp
Array<Complex> A(100, 50);
Array<Complex> B(100, 32);

// Non-contiguous inputs work automatically!
auto A_transposed = A.transpose(1, 0);  // Non-contiguous view
Array<Complex> C(A_transposed.dimensions(0), B.dimensions(1));  // Output: contiguous

LinAlg::matmul(A_transposed, B, C);  // ✓ Automatically handles A_transposed
```

| NumPy | GPIArray |
|-------|----------|
| `C = A @ B` | `LinAlg::matmul(A, B, C)` |
| `C = A.T @ B` | `LinAlg::matmul(A.transpose(), B, C)` (auto-handled) |

### Linear Solvers: When to Use What

#### 1. Cholesky (Fastest - Use if you can!)

**Requirements:** $A$ must be **square, Hermitian, and positive-definite**.

**When to use:** Covariance matrices, normal equations from least squares, symmetric weight matrices.

```cpp
// Example: Solve A x = b where A is Hermitian positive-definite
Array<Complex> A(128, 128);      // Hermitian
Array<Complex> b(128, 1);         // RHS
Array<Complex> x(128, 1);         // Solution

LinAlg::solve_cholesky(A, b, x);
```

#### 2. QR (General-purpose fallback)

**Requirements:** $A$ can be rectangular or square, but the current implementation throws on rank-deficient systems.

**When to use:** Non-square systems, ill-conditioned matrices, least-squares fitting.

```cpp
// Example: Solve A x = b in least-squares sense (A is 256 x 50)
Array<Complex> A(256, 50);       // Overdetermined
Array<Complex> b(256, 1);         // RHS
Array<Complex> x(50, 1);          // Solution

LinAlg::solve_qr(A, b, x);  // Finds a least-squares solution when the system is not rank-deficient
```

---

### Singular Value Decomposition (SVD)

Decomposes $A = U \Sigma V^H$, where:
- $U$ is $(m \times k)$ with orthonormal columns
- $\Sigma$ is $(k)$ (diagonal singular values in descending order)
- $V^H$ is $(k \times n)$ (conjugate transpose of $V$)

**GPIArray always returns** $V^H$ (not $V$) **to match standard MRI conventions**.

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

## 3.7 Convenience Overloads: Auto-Allocation with Return Values

All linear algebra operations have **dual API**:

1. **In-place API** (Returns nothing, modifies pre-allocated output arrays)
   - Useful in **hot loops** where you reuse the same output buffers
   - Saves memory by avoiding heap allocations
   - Full control over memory layout

2. **Overload API** (Returns results via tuple, auto-allocates internally)
   - Convenient for one-off computations
   - Automatic, safe memory management
   - More Pythonic style

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

## 3.8 Troubleshooting Linear Algebra Operations

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
