# Section 4: The FFT Backend (FFTW Wrapper)

The `GPIArray::FFTW` namespace provides a robust, thread-safe wrapper around the FFTW3 library. It handles memory alignment, plan management, and frequency shift logic.

## 4.0 Quick Start

### Forward & Inverse FFT
```cpp
Array<Complex> signal(256, 256);

// Transform to frequency domain
Array<Complex> spectrum = signal.empty_like();
FFTW::fftn(signal, spectrum, FFTW::ImageToKspace);

// Transform back to spatial domain
Array<Complex> recovered = spectrum.empty_like();
FFTW::fftn(spectrum, recovered, FFTW::KspaceToImage);
```

### In-Place Transform
```cpp
Array<Complex> data(512, 512);

// Modifies 'data' directly
FFTW::fftn(data, data, FFTW::ImageToKspace);
```

### 1D FFT on Specific Axis
```cpp
Array<Complex> matrix(100, 256);  // e.g., time x frequency

// Transform only along axis 1 (each row independently)
Array<Complex> result = matrix.empty_like();
FFTW::fftn(matrix, result, FFTW::ImageToKspace, {1});
```

---

## 4.1 Understanding FFT Directions & Normalization

### The Two Directions

| Direction | Formula | Meaning | NumPy |
|-----------|---------|---------|-------|
| **ImageToKspace** | $\hat{X}[k] = \sum_{n=0}^{N-1} x[n] e^{-2\pi i kn/N}$ | Forward FFT → Frequency domain | `np.fft.fft()` |
| **KspaceToImage** | $x[n] = \frac{1}{N}\sum_{k=0}^{N-1} \hat{X}[k] e^{+2\pi i kn/N}$ | Inverse FFT → Spatial domain | `np.fft.ifft()` |

### Choosing Normalization

**Three modes available:**

```cpp
enum Normalization {
    NORM_NONE,      // No scaling
    NORM_BACKWARD,  // (Default) Scale only on inverse
    NORM_ORTHO      // Scale both directions equally
};
```

#### 1. `NORM_BACKWARD` (Default) — Engineering Standard

| Direction | Formula | Scaling |
|-----------|---------|---------|
| ImageToKspace (forward) | $\hat{X}[k] = \sum_{n} x[n] e^{-2\pi i kn/N}$ | ×1 |
| KspaceToImage (inverse) | $x[n] = \frac{1}{N}\sum_{k} \hat{X}[k] e^{+2\pi i kn/N}$ | ×1/N |

**Use when:** Following standard DSP conventions. Energy grows in frequency domain.

```cpp
FFTW::fftn(signal, spectrum, FFTW::ImageToKspace, {}, true, FFTW::NORM_BACKWARD);
// |spectrum| is N times larger than |signal|

FFTW::fftn(spectrum, recovered, FFTW::KspaceToImage, {}, true, FFTW::NORM_BACKWARD);
// recovered ≈ signal ✓ (perfectly reconstructed)
```

#### 2. `NORM_ORTHO` (Orthonormal) — Preserve Energy

| Direction | Formula | Scaling |
|-----------|---------|---------|
| ImageToKspace (forward) | $\hat{X}[k] = \frac{1}{\sqrt{N}}\sum_{n} x[n] e^{-2\pi i kn/N}$ | ×1/√N |
| KspaceToImage (inverse) | $x[n] = \frac{1}{\sqrt{N}}\sum_{k} \hat{X}[k] e^{+2\pi i kn/N}$ | ×1/√N |

**Use when:** You need energy conservation in iterative algorithms (e.g., Conjugate Gradient, regularized reconstruction). Parseval's theorem holds: $\|x\|_2 = \|\hat{X}\|_2$.

```cpp
// Verify energy conservation
double energy_spatial = l2norm(signal);
FFTW::fftn(signal, spectrum, FFTW::ImageToKspace, {}, true, FFTW::NORM_ORTHO);
double energy_freq = l2norm(spectrum);
// energy_spatial ≈ energy_freq ✓
```

#### 3. `NORM_NONE` (No Scaling) — Custom Normalization

| Direction | Formula | Scaling |
|-----------|---------|---------|
| ImageToKspace (forward) | $\hat{X}[k] = \sum_{n} x[n] e^{-2\pi i kn/N}$ | ×1 |
| KspaceToImage (inverse) | $x[n] = \sum_{k} \hat{X}[k] e^{+2\pi i kn/N}$ | ×1 |

**Use when:** You need custom scaling (e.g., handle normalization yourself). Rarely needed.

**Decision Tree:**
```
Do you need energy conservation?
├─ YES (iterative algorithms) → Use ORTHO
│
└─ NO (data analysis, filtering)
   ├─ Forward→Inverse should equal input? → Use BACKWARD (default)
   └─ Need custom scaling? → Use NONE
```

---

## 4.2 Continuous vs. Discrete FFTs

GPIArray always computes **discrete** FFTs. The continuous Fourier transform is its mathematical foundation, but what you get is:

$$X[k] = \sum_{n=0}^{N-1} x[n] e^{-2\pi i kn/N}$$

where indices $n, k \in [0, N-1]$.

**Key Consequence:** To relate frequency-domain values to physical frequencies (Hz), you must scale by the sampling rate:

$$f_k = \frac{k \cdot f_s}{N}$$

where $f_s$ is sampling frequency and $N$ is array size. **The library does NOT do this for you.**

---

## 4.3 One-Off FFT Execution (`fftn`)

For single transforms (not in loops), use `fftn`. It creates a temporary plan with `FFTW_ESTIMATE` (no planning overhead).

```cpp
Array<Complex> input(256, 256);
Array<Complex> output = input.empty_like();

// Transform all dimensions
FFTW::fftn(input, output, FFTW::ImageToKspace);

// Transform specific axes only (must be contiguous innermost dimensions)
FFTW::fftn(input, output, FFTW::ImageToKspace, {1, 2});

// With custom normalization
FFTW::fftn(input, output, FFTW::ImageToKspace, {}, true, FFTW::NORM_ORTHO);

// Disable automatic fftshift (raw frequency order)
FFTW::fftn(input, output, FFTW::ImageToKspace, {}, false);  // perform_shift=false
```

**Key Parameters:**
- **`input`**: Source array
- **`output`**: Destination array (can be same as input for in-place)
- **`direction`**: `ImageToKspace` or `KspaceToImage`
- **`axes`**: Empty = transform all; `{1, 2}` = transform only axes 1 & 2
- **`perform_shift`**: `true` (default) = DC at center; `false` = DC at edge
- **`norm`**: Normalization mode (default: `NORM_BACKWARD`)

---

## 4.4 Persistent Plans (`FFTPlan`) — For Loops & Iterative Algorithms

If you transform the same array shape repeatedly (e.g., iterative reconstruction), persistent plans avoid planning overhead.

```cpp
using namespace GPIArray;

Array<Complex> data(256, 256);

// Create plan once
FFTW::FFTPlan<double> plan(
    {256, 256},           // Array shape
    FFTW_MEASURE,         // Planning rigor (MEASURE is sensible default)
    {},                   // Empty = transform all dims; {1, 2} = specific axes
    FFTW::NORM_ORTHO      // Normalization mode
);

// Use repeatedly (in-place only)
for (int iter = 0; iter < 100; ++iter) {
    plan.ImageToKspace(data);   // Forward
    // ... do something ...
    plan.KspaceToImage(data);   // Backward
}
```

**Planning Options:**
- `FFTW_ESTIMATE` – Fast plan, no measurement (use for one-off transforms)
- `FFTW_MEASURE` – Medium planning, reasonable performance (good default)
- `FFTW_PATIENT` – Slow planning, excellent performance (for loops > 1000 iterations)

---

## 4.5 Frequency Shifting: DC at Center vs. Edge

By default, FFTW places the zero-frequency (DC) component at index 0. Most visualization/analysis tools expect it in the center.

```cpp
Array<Complex> data(256, 256);
Array<Complex> spectrum = data.empty_like();

// With fftshift (DEFAULT, perform_shift=true)
// DC component ends up at index [128, 128]
FFTW::fftn(data, spectrum, FFTW::ImageToKspace, {}, true);

// Without fftshift (perform_shift=false)
// DC component stays at index [0, 0]
FFTW::fftn(data, spectrum, FFTW::ImageToKspace, {}, false);
```

**Performance Note:** For arrays with even dimensions (e.g., 256×256), shifting is automatic and **extremely fast** (mask operation, not memory copy). For odd dimensions, shifting uses `std::rotate` (slower). This is handled transparently.

**NumPy Equivalent:**
```python
np.fft.fftshift(np.fft.fft(x))     # With shift
np.fft.fft(x)                      # Without shift
```

---

## 4.6 Real Transforms (DCT)

```cpp
Array<double> image(256, 256);  // Real-valued only

// Forward DCT-II
Array<double> coeffs = FFTW::dct(image);

// Inverse DCT-III (automatically normalized)
Array<double> recon = FFTW::idct(coeffs);
```

**Restrictions:** 2D, real-valued, contiguous arrays only.

---

## 4.7 Troubleshooting

### Problem: "Array must be contiguous"

**Cause:** You passed a non-contiguous view (e.g., transposed array).

**Solution:**
```cpp
auto bad = original.transpose(1, 0);  // Non-contiguous ❌
FFTW::fftn(bad, output, FFTW::ImageToKspace);  // Fails!

auto good = bad.copy();  // Force contiguous
FFTW::fftn(good, output, FFTW::ImageToKspace);  // ✓ Works
```

### Problem: "Axes must be contiguous innermost dimensions"

**Cause:** You asked to transform non-contiguous axes (e.g., `{0, 2}` in 3D).

**Solution:**
```cpp
Array<Complex> data(32, 256, 256);  // (Coils, Y, X)

// ❌ Can't do this:
FFTW::fftn(data, out, FFTW::ImageToKspace, {0, 2});

// ✓ Do this instead (contiguous innermost):
FFTW::fftn(data, out, FFTW::ImageToKspace, {1, 2});

// Or 1D FFT on arbitrary axis:
for (uint64_t c = 0; c < data.size(0); ++c) {
    auto coil_slice = data.slice(S(c), S::all(), S::all());
    FFTW::fftn(coil_slice, out_slice, FFTW::ImageToKspace, {0});
}
```

### Problem: Forward→Inverse doesn't recover original

**Cause:** Wrong normalization mode or forgetting fftshift.

**Solution:**
```cpp
// ✓ Correct (NORM_BACKWARD is default)
Array<Complex> original(256, 256);
Array<Complex> spectrum = original.empty_like();
Array<Complex> recovered = original.empty_like();

FFTW::fftn(original, spectrum, FFTW::ImageToKspace, {}, true);  // With shift
FFTW::fftn(spectrum, recovered, FFTW::KspaceToImage, {}, true);  // With shift
// recovered ≈ original ✓
```

---

## 4.8 Wisdom (Advanced)

Save expensive planning computations to disk:

```cpp
// Load pre-computed plans at startup
FFTW::load_wisdom<double>("my_plans.wisdom");

// ... do your FFTs ...

// Save new plans before exiting
FFTW::save_wisdom<double>("my_plans.wisdom");
```

Useful for production systems where you run the same transforms repeatedly.