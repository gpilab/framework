# Section 5: Discrete Wavelet Transform

## 5.1 What is Wavelet?

`Wavelet` is a high-performance, thread-safe implementation of the **Discrete Wavelet Transform (DWT)** in 2D and 3D. It supports multi-level decomposition with two orthonormal filter families, automatic memory padding, and denoising via soft-thresholding.

**Key Features:**
- ✅ **2D & 3D Support:** Transform images (2D) or volumetric data (3D)
- ✅ **Multi-Level Decomposition:** Controllable number of wavelet levels
- ✅ **Two Filter Families:** Haar (fast, simple) or Daubechies D4 (smoother, more coefficients)
- ✅ **Thread-Safe Operations:** Per-thread buffers prevent race conditions
- ✅ **Zero-Allocation Execution:** Thread-local buffers pre-allocated in constructor
- ✅ **Soft Thresholding:** Built-in denoising with per-level threshold control
- ✅ **Complex Arithmetic:** Works with `std::complex<float>` and `std::complex<double>`

**Who Should Use It:**
- MRI/CT image denoising and reconstruction
- Wavelet-based signal compression
- Multi-scale image analysis
- Iterative shrinkage/thresholding algorithms (ISTA, FISTA)
- Scientific computing requiring frequency decomposition

---

## 5.2 Filter Options

Voxel Wavelet supports **two orthonormal filter families**:

### 5.2.1 Haar Filter (Fast, Simplicial)

**Constructor Parameter:** `use_haar = true`

**Filter Coefficients:**
- **h (low-pass):** `[1/√2, 1/√2]` — averages adjacent samples
- **g (high-pass):** `[1/√2, -1/√2]` — computes differences

**Characteristics:**
- Filter length = 2 (minimal)
- Fastest computation
- Introduces block artifacts in reconstructed images
- Orthonormal but not smooth

**When to Use:**
- Real-time processing where speed is critical
- Sparse signal analysis (wavelets with compact support)
- Data already contains sharp features (less benefit from smoothing)

### 5.2.2 Daubechies D4 Filter (Smoother, Default)

**Constructor Parameter:** `use_haar = false` (default)

**Filter Coefficients:**
- **h (low-pass):** 4-element filter involving `√3` — smooth averaging
- **g (high-pass):** 4-element filter — smooth detail detection

**Exact Values (normalized for orthonormality):**
```
h = [(1 + √3)/(4√2), (3 + √3)/(4√2), (3 - √3)/(4√2), (1 - √3)/(4√2)]
g = [(1 - √3)/(4√2), -((3 - √3)/(4√2)), (3 + √3)/(4√2), -((1 + √3)/(4√2))]
```

**Characteristics:**
- Filter length = 4
- Slower than Haar (more operations per level)
- Smoother reconstructions
- Better frequency localization
- Orthonormal and smooth

**When to Use:**
- Medical imaging (MRI, CT) requiring smooth reconstructions
- Data with slow-varying features (images, natural photos)
- Denoising applications where artifact-free output is critical
- Compression where visual quality matters

---

## 5.3 Constructor Signatures

### 5.3.1 2D Wavelet Constructor

```cpp
Wavelet(uint64_t image_size1_, uint64_t image_size2_, 
        uint64_t levels_, bool use_d2_not_d4_ = false)
```

**Parameters:**
- `image_size1_`: Height of input images (rows)
- `image_size2_`: Width of input images (columns)
- `levels_`: Number of decomposition levels (min 1)
- `use_haar_`: If `true`, use Haar filter; if `false`, use Daubechies D4 (default)

**Example:**
```cpp
// 2D Daubechies D4 wavelet for 512×512 images, 5 levels
Voxel::Wavelet<double> dwt_d4(512, 512, 5);

// 2D Haar wavelet for 256×256 images, 3 levels
Voxel::Wavelet<float> dwt_haar(256, 256, 3, true);
```

### 5.3.2 3D Wavelet Constructor

```cpp
Wavelet(uint64_t image_size1_, uint64_t image_size2_, uint64_t image_size3_,
        uint64_t levels_, bool use_d2_not_d4_ = false)
```

**Parameters:**
- `image_size1_`: Height (rows)
- `image_size2_`: Width (columns)  
- `image_size3_`: Depth (slices/frames)
- `levels_`: Number of decomposition levels (min 1)
- `use_d2_not_d4_`: Filter family selector

**Example:**
```cpp
// 3D volume 256×256×128, 4 levels, Daubechies D4
Voxel::Wavelet<double> dwt_3d(256, 256, 128, 4, false);

// 3D Haar (fast)
Voxel::Wavelet<float> dwt_3d_haar(128, 128, 64, 3, true);
```

**Memory Allocation at Construction:**
During construction, the wavelet object pre-allocates one complex array per OpenMP thread. This enables zero-allocation transformations at runtime.

---

## 5.4 Wavelet Size Computation

The actual working size is larger than the input image to support multi-level decomposition:

```cpp
computed_size = Nq × 2^levels
where Nq = 2 × ceil(image_size / 2^(levels+1))
```

**Example:** For 512×512 input, 5 levels:
- `Nq = 2 × ceil(512 / 64) = 16`
- `wavelet_size = 16 × 32 = 512` ✓ (happens to match input)

**Access Working Sizes:**
```cpp
uint64_t w1 = dwt.get_wavelet_size1();
uint64_t w2 = dwt.get_wavelet_size2();
uint64_t w3 = dwt.get_wavelet_size3();  // 3D only
```

The input is center-padded to this size before transformation and center-cropped after inverse transform.

---

## 5.5 Core Methods

### 5.5.1 Forward Transform (Analysis)

```cpp
Array<ComplexT> forward_transform(const Array<ComplexT>& input) const
```

**Purpose:** Decompose input into wavelet coefficients.

**Parameters:**
- `input`: 2D or 3D array of input data (must match constructor dimensions)

**Returns:** Complex array of wavelet coefficients at `wavelet_size × wavelet_size × ...`

**Example (2D):**
```cpp
Voxel::Array<std::complex<double>> image(512, 512);
// ... populate image ...

const Voxel::Wavelet<double> dwt(512, 512, 5);
auto coeffs = dwt.forward_transform(image);

// coeffs now contains multi-level DWT decomposition
// Top-left quadrant: LL (coarsest low-pass)
// Other quadrants: HL, LH, HH (detail coefficients at each level)
```

**Computational Flow:**
1. Create padded workspace of size `wavelet_size × wavelet_size`
2. Center-copy input into padded array
3. Apply `levels` iterations of 2D/3D DWT filtering
4. Return padded coefficient array

**Time Complexity:** O(n × levels) where n = image_size1 × image_size2

### 5.5.2 Inverse Transform (Synthesis)

```cpp
Array<ComplexT> inverse_transform(Array<ComplexT>& image) const
```

**Purpose:** Reconstruct image from wavelet coefficients (perfect reconstruction if no modification).

**Parameters:**
- `image`: Complex array from `forward_transform()` (modified in-place)

**Returns:** Cropped reconstruction matching original input dimensions

**Example:**
```cpp
auto coeffs = dwt.forward_transform(image);

// Optionally modify coefficients (denoising, compression, etc.)
// ...

auto reconstructed = dwt.inverse_transform(coeffs);
// reconstructed matches original image dimensions
```

**Important Notes:**
- Modifies input array in-place during processing
- Returns center-cropped version to original dimensions
- Perfect reconstruction: `inverse(forward(x)) ≈ x` (numerical precision)

### 5.5.3 Soft Thresholding (Denoising)

```cpp
void soft_threshold(Array<ComplexT>& coeffs, 
                    const std::vector<T>& tau_levels,
                    uint64_t skip_coarsest_levels = 0) const
```

**Purpose:** Apply wavelet shrinkage denoising to coefficients.

**Parameters:**
- `coeffs`: Wavelet coefficients (modified in-place)
- `tau_levels`: Per-level thresholds, size must equal `levels`
- `skip_coarsest_levels`: Skip thresholding on lowest `N` levels (default 0)

**Thresholding Formula (soft shrinkage):**
```
x̂ = sign(x) × max(|x| - τ, 0)
```
For complex: `ẑ = max(|z| - τ, 0) × (z / |z|)`

**Example:**
```cpp
auto coeffs = dwt.forward_transform(noisy_image);

// Create per-level thresholds (higher for coarse, lower for fine)
std::vector<double> tau_levels = {50.0, 40.0, 30.0, 20.0, 10.0}; // 5 levels

// Skip thresholding on 1 coarsest level (preserve LL subband)
dwt.soft_threshold(coeffs, tau_levels, 1);

auto denoised = dwt.inverse_transform(coeffs);
```

**Threshold Selection:**
- **Too high:** Under-thresholding, noise remains
- **Too low:** Over-thresholding, image blurring
- **Typical:** τ ≈ σ × √(2 log N) where σ = noise std deviation, N = array size
- **Per-level:** Coarse levels tolerate higher thresholds; fine levels need lower ones

**SIMD Optimization:** Inner loops use `#pragma omp simd` for vectorization on contiguous arrays.

---

## 5.6 Thread Safety

### 5.6.1 Thread-Local Buffers

The Wavelet class uses per-thread complex arrays to guarantee thread-safe concurrent transforms:

```cpp
mutable std::vector<Array<ComplexT>> thread_buffers;  // One per OpenMP thread
```

**Initialization (in constructor):**
```cpp
int max_threads = omp_get_max_threads();
for(int i = 0; i < max_threads; ++i) {
    thread_buffers.push_back(Array<ComplexT>::zeros(wavelet_size1, 
                                                    wavelet_size2, 
                                                    wavelet_size3));  // 3D
}
```

### 5.6.2 Safe Thread Access

```cpp
Array<ComplexT>& get_thread_buffer() const {
    int thread_id = omp_get_thread_num();
    // Bounds check and access thread_buffers[thread_id]
    return thread_buffers[thread_id];
}
```

### 5.6.3 Multi-threaded Usage Pattern

```cpp
const Voxel::Wavelet<double> dwt(512, 512, 5);  // Single shared instance

#pragma omp parallel for
for (int i = 0; i < num_images; ++i) {
    auto coeffs = dwt.forward_transform(images[i]);
    // Each thread gets its own buffer—no race conditions
}
```

**Guarantees:**
- ✅ Multiple threads can transform different images simultaneously
- ✅ No false sharing or memory contention
- ✅ Bounds checking prevents thread ID overflow
- ⚠️ Initialization assumes thread pool size ≤ `omp_get_max_threads()`

---

## 5.7 Memory Management

### 5.7.1 Pre-Allocated Buffers (Zero-Allocation at Runtime)

All thread buffers are allocated in the constructor, enabling zero-allocation transforms:

```cpp
Voxel::Wavelet<double> dwt(512, 512, 5);  // ~128 MB per thread allocated here
                                           // (512×512 complex<double> per thread)

// Later: transform millions of images with no new allocations
for (int i = 0; i < 1'000'000; ++i) {
    auto coeffs = dwt.forward_transform(images[i]);  // Zero allocation!
}
```

### 5.7.2 Return Value (Copy, Not View)

Both `forward_transform` and `inverse_transform` return new arrays:

```cpp
auto coeffs = dwt.forward_transform(input);    // New Array, not a view
auto output = dwt.inverse_transform(coeffs);   // New Array
```

These use Voxel's shared pointer mechanism, so copying is cheap (shared memory).

### 5.7.3 In-Place Thresholding

`soft_threshold` modifies the coefficient array in-place, reducing memory pressure:

```cpp
auto coeffs = dwt.forward_transform(image);
dwt.soft_threshold(coeffs, tau_levels);  // Modifies coeffs in-place
auto denoised = dwt.inverse_transform(coeffs);
```

---

## 5.8 Decomposition Structure (2D Example)

After `forward_transform` on a 512×512 image with 5 levels, the coefficient array is organized hierarchically. The **coarsest (top) level** contains the LL (low-pass) subband plus all detail subbands (HL, LH, HH) from finer levels:

```
┌──────────────────────────────────────────────────────┐
│                                                      │
│  ┌─────────────┬──────────────────────────────────┐ │
│  │ LL (Level 5)│  HL, LH, HH (Lvl 5)              │ │
│  │ (Coarsest)  │                                  │ │
│  ├─────────────┼───────────────────────────────────┤ │
│  │ LL (Lvl 4)  │  HL, LH, HH (Level 4)            │ │
│  ├─────────────┼───────────────────────────────────┤ │
│  │ LL (Lvl 3)  │  HL, LH, HH (Level 3)            │ │
│  ├─────────────┼───────────────────────────────────┤ │
│  │ LL (Lvl 2)  │  HL, LH, HH (Level 2)            │ │
│  ├─────────────┼───────────────────────────────────┤ │
│  │ LL (Lvl 1)  │  HL, LH, HH (Level 1)            │ │
│  ├─────────────┴───────────────────────────────────┤ │
│  │ HL, LH, HH (Original/Level 0 - Finest Details) │ │
│  └──────────────────────────────────────────────────┘ │
│                                                      │
│  Subbands:                                           │
│  • LL = Low × Low (approximation/trend)              │
│  • HL = High × Low (horizontal edges)                │
│  • LH = Low × High (vertical edges)                  │
│  • HH = High × High (diagonal features)              │
└──────────────────────────────────────────────────────┘
```

**Key Points:**
- **LL subband** stores the coarsest approximation (top-left)
- **Detail subbands** (HL, LH, HH) from each level populate the rest
- **Hierarchy:** Level 5 (coarsest) → Level 1 (finest before original)
- **Size:** Each level's LL is ½ resolution of the previous level
- **Reconstruction:** Inverse transform processes levels from coarsest → finest

---

## 5.9 3D Decomposition Structure

3D DWT produces 8 subbands per level (instead of 4 in 2D):

```
LLL, LLH (low freq in x,y; varies in z)
LHL, LHH (low freq in x; varies in y,z)
HLL, HLH (low freq in y; varies in x,z)
HHL, HHH (varies in all directions)
```

Coefficient array is structured with these in separate blocks, indexed similarly to 2D.

---

## 5.10 Data Type Support

```cpp
Voxel::Wavelet<float>   // Complex<float> transforms
Voxel::Wavelet<double>  // Complex<double> transforms (recommended for imaging)
```

**Precision Impact:**
- **float:** ~7 decimal digits, smaller memory footprint
- **double:** ~15 decimal digits, better numerical stability (recommended for MRI/medical)

---

## 5.11 Practical Workflow: Denoising

```cpp
#include "Voxel/Wavelet.hpp"
#include "Voxel/Array.hpp"
#include <vector>

using namespace Voxel;

// Denoise a 512×512 image with 5-level Daubechies D4
void denoise_example() {
    // Input: noisy_image (512×512)
    Array<std::complex<double>> noisy_image(512, 512);
    // ... populate noisy_image ...

    // Create wavelet transformer
    const Wavelet<double> dwt(512, 512, 5, false);  // D4, 5 levels

    // Forward transform
    auto coeffs = dwt.forward_transform(noisy_image);

    // Estimate noise std deviation (e.g., from finest detail subband)
    double sigma = estimate_sigma_from_HH(coeffs);

    // Create thresholds: τ = σ × √(2 log N) per level
    std::vector<double> tau_levels(5);
    for (int i = 0; i < 5; ++i) {
        tau_levels[i] = sigma * std::sqrt(2.0 * std::log(512.0 * 512.0)) * (0.8 - 0.1 * i);
    }

    // Soft threshold (skip coarsest level to preserve structure)
    dwt.soft_threshold(coeffs, tau_levels, 1);

    // Inverse transform
    auto denoised = dwt.inverse_transform(coeffs);

    // Use denoised image
}
```

---

## 5.12 Performance Considerations

| Aspect | Haar | Daubechies D4 |
|--------|------|---------------|
| **Speed** | ~2x faster | Baseline |
| **Memory** | Same | Same |
| **Artifacts** | Block effects | Smooth |
| **Filter Operations** | 2 per level | 4 per level |
| **Best For** | Real-time, sparse data | Medical imaging, compression |

**Optimization Tips:**
1. Use contiguous arrays for SIMD vectorization
2. Set `OMP_NUM_THREADS` to match CPU core count
3. For multi-image batching, use `#pragma omp parallel for` on the batch loop
4. Pre-allocate Wavelet object outside loop (construction is expensive)

---

## 5.13 Error Handling

The Wavelet class validates inputs and throws `std::runtime_error` or `std::invalid_argument` for:

- Input dimension mismatch (wrong image size)
- Level count < 1
- Coefficient array size mismatch
- Negative threshold values
- Thread ID out of bounds (dynamic thread pool changes)

**Example:**
```cpp
try {
    auto coeffs = dwt.forward_transform(wrong_size_image);
} catch (const std::invalid_argument& e) {
    std::cerr << "Error: " << e.what() << std::endl;
    // "2D forward_transform: Input must be sized (512, 512)"
}
```

---

## 5.14 Advanced: Custom Denoiser Interface

The header defines an abstract `IWaveletDenoiser` class for building custom denoising algorithms. Subclasses can override threshold selection logic while reusing the wavelet machinery (see `IWaveletDenoiser` in the header for details).

---

## 5.15 References & Further Reading

- **Daubechies D4 Filter:** I. Daubechies, *Ten Lectures on Wavelets* (CBMS-61, 1992)
- **Orthonormal Wavelets:** Mallat's multiresolution framework
- **Soft Thresholding:** Donoho & Johnstone, *Ideal Spatial Adaptation via Wavelet Shrinkage* (JASA, 1994)
- **Fast DWT Algorithm:** Mallat algorithm (O(n) complexity)
