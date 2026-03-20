# Section 4: The FFT Backend (FFTW Wrapper)

The `GPIArray::FFTW` namespace provides a wrapper around the FFTW3 library. It handles contiguity, plan management, normalization, and frequency-shift logic.

## 4.0 Automatic Contiguity Handling

All FFTW functions **automatically ensure contiguity** by calling `.contiguous()` on input arrays. This means:
- ✅ If the array is already contiguous, no copy is made (zero overhead)
- ✅ If the array is non-contiguous (e.g., from `.transpose()` or `.slice()`), a contiguous copy is made automatically

```cpp
// Safe - contiguity handled automatically:
auto transposed = A.transpose(1, 0, 2);  // Non-contiguous view
Array<Complex> output = transposed.empty_like();
FFTW::fftn(transposed, output, FFTW::ImageToKspace);  // ✓ Works correctly!
```

### ⚠️ Important: Non-Contiguous Input Behavior

When a **non-contiguous input array** is passed to FFTW functions:
- The operation is performed on an **internal contiguous copy**, NOT the original array
- The original array **remains unchanged**
- If you intended to modify the original, you must manually copy the result back:

```cpp
auto transposed = A.transpose(1, 0, 2);  // Non-contiguous
Array<Complex> output = transposed.empty_like();

FFTW::fftn(transposed, output, FFTW::ImageToKspace);
// ⚠️ transposed is NOT modified (it's a view)

// If you need to update the original:
auto result_contiguous = output.contiguous();
transposed = result_contiguous;  // Copy data back to view (if allowed)
// OR use a different approach for your computation
```

**Best Practices:**
- For contiguous arrays: Direct in-place or out-of-place is fine
- For non-contiguous slices/views: Use out-of-place transforms, store results separately
- For maximum clarity: Always use explicit output arrays with non-contiguous inputs

## 4.1 Quick Start

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

## 4.2 Understanding FFT Directions & Normalization

### The Two Directions

| Direction | Formula | Meaning | NumPy |
|-----------|---------|---------|-------|
| **ImageToKspace** | $\hat{X}[k] = \sum_{n=0}^{N-1} x[n] e^{-2\pi i kn/N}$ | Forward FFT → Frequency domain | `np.fft.fft()` |
| **KspaceToImage** | $x[n] = \frac{1}{N}\sum_{k=0}^{N-1} \hat{X}[k] e^{+2\pi i kn/N}$ | Inverse FFT → Spatial domain | `np.fft.ifft()` |

### Choosing Normalization

Three normalization modes are available:

```cpp
enum Normalization {
    NORM_NONE,      // No scaling
    NORM_BACKWARD,  // (Default) Scale only on inverse
    NORM_ORTHO      // Scale both directions equally
};
```

| Mode | Brief Description |
|------|-------------------|
| `NORM_BACKWARD` | Standard default. Forward FFT is unscaled; inverse applies `1/N`. |
| `NORM_ORTHO` | Splits normalization evenly across forward and inverse using `1/sqrt(N)`. |
| `NORM_NONE` | No normalization is applied in either direction. |

---

## 4.3 One-Off FFT Execution (`fftn`)

For single transforms (not in loops), use `fftn`. It creates a temporary plan with `FFTW_ESTIMATE`, which minimizes planning work compared with the more expensive planning modes.

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
- **`norm`**: Optional normalization mode. If omitted, the default is `NORM_BACKWARD`.

---

## 4.4 Persistent Plans (`FFTPlan`) — For Loops & Iterative Algorithms

If you transform the same array shape repeatedly (e.g., iterative reconstruction), persistent plans avoid planning overhead.

```cpp
using namespace GPIArray;

std::vector<Array<Complex>> frames(100, Array<Complex>(256, 256));

// Create plan once
FFTW::FFTPlan<double> plan(
    {256, 256},           // Array shape
    FFTW_MEASURE,         // Planning rigor (MEASURE is sensible default)
    {},                   // Empty = transform all dims; {1, 2} = specific axes
    FFTW::NORM_ORTHO      // Normalization mode
);

// Execute repeatedly across independent arrays
#pragma omp parallel for
for (int iter = 0; iter < 100; ++iter) {
    plan.ImageToKspace(frames[iter]);   // Forward
    // ... do something ...
    plan.KspaceToImage(frames[iter]);   // Backward
}
```

Execution is thread-safe, so a single `FFTPlan` can be reused across parallel iterations when each thread operates on independent arrays.

> [!NOTE]
> During `FFTPlan` creation, the wrapper fixes the transform shape, selected axes, direction-specific FFTW plans, normalization mode, and any internal metadata needed to execute the transform repeatedly. Those prepared plan objects are then stored inside the `FFTPlan` instance and reused on every `ImageToKspace()` / `KspaceToImage()` call, which avoids re-planning overhead.

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

## 4.6 Troubleshooting

### Problem: FFT works, but a non-contiguous input is slower or not truly in-place

**Cause:** FFTW accepts non-contiguous views, but it first creates an internal contiguous copy. The transform runs on that temporary buffer rather than directly on the original view.

**Solution:**
```cpp
auto view = original.transpose(1, 0);  // Non-contiguous view
FFTW::fftn(view, output, FFTW::ImageToKspace);  // ✓ Works, but may copy internally

// If you want the copy to be explicit and predictable:
auto work = view.contiguous();
FFTW::fftn(work, output, FFTW::ImageToKspace);
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

## 4.7 Wisdom (Advanced)

Save expensive planning computations to disk:

```cpp
// Load pre-computed plans at startup
FFTW::load_wisdom<double>("my_plans.wisdom");

// ... do your FFTs ...

// Save new plans before exiting
FFTW::save_wisdom<double>("my_plans.wisdom");
```

Useful for production systems where you run the same transforms repeatedly.
