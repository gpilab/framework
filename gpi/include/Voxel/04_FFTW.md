# Section 4: The FFT Backend (PocketFFT)

The `Voxel::FFT` namespace provides a high-performance FFT backend powered by PocketFFT. It handles contiguity, normalization, and frequency-shift logic with automatic internal optimization.

## 4.0 Automatic Contiguity Handling

All FFT functions **automatically ensure contiguity** by calling `.contiguous()` on input arrays. This means:
- ✅ If the array is already contiguous, no copy is made (zero overhead)
- ✅ If the array is non-contiguous (e.g., from `.transpose()` or `.slice()`), a contiguous copy is made automatically

```cpp
// Safe - contiguity handled automatically:
auto transposed = A.transpose(1, 0, 2);  // Non-contiguous view
Array<Complex> output = transposed.empty_like();
FFT::fftn(transposed, output, FFT::Forward);  // ✓ Works correctly!
```

### ⚠️ Important: Non-Contiguous Input Behavior

When a **non-contiguous input array** is passed to FFT functions:
- The operation is performed on an **internal contiguous copy**, NOT the original array
- The original array **remains unchanged**
- If you intended to modify the original, you must manually copy the result back:

```cpp
auto transposed = A.transpose(1, 0, 2);  // Non-contiguous
Array<Complex> output = transposed.empty_like();

FFT::fftn(transposed, output, FFT::Forward);
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

// Direction names
Array<Complex> spectrum = signal.empty_like();
FFT::fftn(signal, spectrum, FFT::Forward);

// Equivalent form:
// FFT::fftn(signal, spectrum, FFT::ImageToKspace);

// Transform back to spatial domain
Array<Complex> recovered = spectrum.empty_like();
FFT::fftn(spectrum, recovered, FFT::Backward);

// Equivalent form:
// FFT::fftn(spectrum, recovered, FFT::KspaceToImage);
```

### In-Place Transform
```cpp
Array<Complex> data(512, 512);

// Modifies 'data' directly
FFT::fftn(data, data, FFT::Forward);
```

### 1D FFT on Specific Axis
```cpp
Array<Complex> matrix(100, 256);  // e.g., time x frequency

// Transform only along axis 1 (each row independently)
Array<Complex> result = matrix.empty_like();
FFT::fftn(matrix, result, FFT::Forward, {1});
```

---

## 4.2 Understanding FFT Directions & Normalization

### The Two Directions

| Direction | Formula | Meaning | NumPy |
|-----------|---------|---------|-------|
| **Forward** (`ImageToKspace`) | $\hat{X}[k] = \sum_{n=0}^{N-1} x[n] e^{-2\pi i kn/N}$ | Forward FFT → Frequency domain | `np.fft.fft()` |
| **Backward** (`KspaceToImage`) | $x[n] = \frac{1}{N}\sum_{k=0}^{N-1} \hat{X}[k] e^{+2\pi i kn/N}$ | Inverse FFT → Spatial domain | `np.fft.ifft()` |

Both naming styles are supported and are equivalent:

```cpp
FFT::Forward == FFT::ImageToKspace;
FFT::Backward == FFT::KspaceToImage;
```

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

For single transforms or any use case, use `fftn`. PocketFFT handles planning internally with optimal default settings (no manual planning flags required).

```cpp
Array<Complex> input(256, 256);
Array<Complex> output = input.empty_like();

// Forward transform
FFT::fftn(input, output, FFT::Forward);

// Backward transform
FFT::fftn(input, output, FFT::Backward);

// Equivalent forms:
// FFT::fftn(input, output, FFT::ImageToKspace);
// FFT::fftn(input, output, FFT::KspaceToImage);

// Transform specific axes only
FFT::fftn(input, output, FFT::Forward, {1, 2});
// FFT::fftn(input, output, FFT::ImageToKspace, {1, 2});

// With custom normalization
FFT::fftn(input, output, FFT::Forward, {}, true, FFT::NORM_ORTHO);
// FFT::fftn(input, output, FFT::ImageToKspace, {}, true, FFT::NORM_ORTHO);

// Disable automatic fftshift (raw frequency order)
FFT::fftn(input, output, FFT::Forward, {}, false);  // perform_shift=false
// FFT::fftn(input, output, FFT::ImageToKspace, {}, false);
```

**Key Parameters:**
- **`input`**: Source array (automatically made contiguous if needed)
- **`output`**: Destination array (can be same as input for in-place)
- **`direction`**: `Forward`, `Backward`, `ImageToKspace`, or `KspaceToImage`
- **`axes`**: Empty = transform all; `{1, 2}` = transform only axes 1 & 2
- **`perform_shift`**: `true` (default) = DC at center; `false` = DC at edge (fast alternating sign mask for even dims)
- **`norm`**: Optional normalization mode. If omitted, the default is `NORM_BACKWARD`.

---

## 4.4 Persistent Plans (`FFTPlan`) — For Loops & Iterative Algorithms

If you transform the same array shape repeatedly (e.g., iterative reconstruction), persistent `FFTPlan` objects provide optimized, reusable transform kernels.

```cpp
using namespace Voxel;

std::vector<Array<Complex>> frames(100, Array<Complex>(256, 256));

// Create plan once (automatically optimized by PocketFFT)
FFT::FFTPlan<double> plan(
    {256, 256},           // Array shape
    {},                   // Empty = transform all dims; {1, 2} = specific axes
    FFT::NORM_ORTHO       // Normalization mode
);

// Execute repeatedly across independent arrays
#pragma omp parallel for
for (int iter = 0; iter < 100; ++iter) {
    plan.ImageToKspace(frames[iter]);
    // Equivalent form:
    // plan.Forward(frames[iter]);
    // ... do something ...
    plan.KspaceToImage(frames[iter]);
    // Equivalent form:
    // plan.Backward(frames[iter]);
}
```

Execution is thread-safe, so a single `FFTPlan` can be reused across parallel iterations when each thread operates on independent arrays.

> [!NOTE]
> During `FFTPlan` creation, the wrapper fixes the transform shape, selected axes, normalization mode, and pre-optimizes internal kernel kernels. PocketFFT automatically selects the best execution strategy for repeated transforms. No manual planning flags are needed—optimization is automatic.

**Why Use `FFTPlan`?**
- **Repeated 2D/3D transforms** on fixed array shapes (iterative reconstruction, multi-frame processing)
- **Thread-safe** transform reuse across parallel regions
- **Automatic optimization** of PocketFFT kernels for the given shape

---

## 4.5 Frequency Shifting: DC at Center vs. Edge

By default, PocketFFT places the zero-frequency (DC) component at index 0. Most visualization/analysis tools expect it in the center.

```cpp
Array<Complex> data(256, 256);
Array<Complex> spectrum = data.empty_like();

// With fftshift (DEFAULT, perform_shift=true)
// DC component ends up at index [128, 128]
FFT::fftn(data, spectrum, FFT::Forward, {}, true);

// Without fftshift (perform_shift=false)
// DC component stays at index [0, 0]
FFT::fftn(data, spectrum, FFT::Forward, {}, false);
```

**Performance Note:** For arrays with **even dimensions** (e.g., 256×256), shifting is **extremely fast** using an alternating sign mask (no memory copy). For odd dimensions, the current implementation throws an error in debug builds. Even-dimension arrays are the recommended use case.

**NumPy Equivalent:**
```python
np.fft.fftshift(np.fft.fft(x))     # With shift
np.fft.fft(x)                      # Without shift
```

---

## 4.6 Troubleshooting

### Problem: FFT works, but a non-contiguous input is slower or not truly in-place

**Cause:** PocketFFT accepts non-contiguous views, but it first creates an internal contiguous copy. The transform runs on that temporary buffer rather than directly on the original view.

**Solution:**
```cpp
auto view = original.transpose(1, 0);  // Non-contiguous view
FFT::fftn(view, output, FFT::Forward);  // ✓ Works, but may copy internally

// If you want the copy to be explicit and predictable:
auto work = view.contiguous();
FFT::fftn(work, output, FFT::Forward);
```

### Problem: Odd-dimension shifting not supported

**Cause:** The current implementation uses alternating sign masks, which only work for even dimensions.

**Solution:**
```cpp
Array<Complex> data(255, 256);  // Odd first dim, even second dim

// ❌ This will throw an error:
// FFT::fftn(data, out, FFT::Forward, {0}, true);  // perform_shift=true

// ✓ Use without shifting, or pad to even dimension:
Array<Complex> data_padded(256, 256);  // Pad to even
FFT::fftn(data_padded, out, FFT::Forward, {}, true);
```


