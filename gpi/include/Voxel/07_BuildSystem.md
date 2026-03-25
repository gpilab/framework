# Section 7: Build System & Integration

 This section covers the required dependencies, the `gpi_make` tool, automatic dependency discovery, compiler flags, and troubleshooting.

`gpi_make` internally calls `make_pybind11.py`, which contains the build logic for compiling `_PYBIND11.cpp` modules against `Voxel`.

## 7.0 30-Second Quick-Start

**You only need these 3 commands:**

```bash
# 1. Build a single Pybind11 module (e.g., MyModule_PYBIND11.cpp)
gpi_make MyModule

# 2. Build all modules in your project
gpi_make --all

# 3. Debug mode (when developing algorithms)
gpi_make MyModule --debug
```

The build system **automatically**:
- Discovers C++20, OpenMP, FFTW3, Eigen3, Pybind11
- Parses `#include` directives to find all dependencies
- Compiles with maximum performance: `-O3`, `-march=native`, SIMD vectorization
- Maintains MD5-based compilation cache for speed

---

## 6.1 Prerequisites & Dependencies

The `Voxel` build system requires these core components. The good news: if you use **Conda**, everything is pre-configured automatically. **Note:** Since the FFT backend was migrated to PocketFFT (header-only, BSD-licensed), FFTW3 is no longer a required dependency.

### Core Requirements

| Component | Requirement | Purpose |
|-----------|------------|---------|
| **C++ Standard** | C++20 minimum | Required by Voxel API |
| **Compiler** | GCC 10+, Clang 10+, or MSVC 2019+ | C++20 support essential |
| **OpenMP** | Threading library (`libomp`, `libgomp`) | OpenMP-enabled builds and SIMD-oriented pragmas |
| **Eigen3** | Linear algebra library | Matrix operations, SVD, PCA (`LinAlg` namespace) |
| **Pybind11** | Python-C++ binding framework | Python module generation |

### Using Conda (Recommended)

If you're in a **Conda environment**, `gpi_make` automatically detects `$CONDA_PREFIX` and uses its pre-installed toolchain:

```bash
# 1. Create/activate Conda environment with all dependencies
conda create -n gpiarray python=3.11 c-compiler cxx-compiler cmake \
  libomp eigen pybind11 -c conda-forge

conda activate gpiarray

# 2. Install Voxel in development mode
cd /path/to/gpi_source
pip install -e .

# 3. You're ready to build!
gpi_make MyModule
```

No additional configuration needed. The build system automatically:
- Finds compilers from conda
- Uses conda's OpenMP (`libomp` on macOS, `libgomp` on Linux)
- Includes Eigen3 headers
- Detects Pybind11 headers
- **PocketFFT** is header-only, so no external FFT library needed

### Manual Installation (System-Wide)

If not using Conda, install these libraries system-wide:

**macOS (using Homebrew):**
```bash
brew install llvm libomp eigen pybind11
```

**Ubuntu/Debian (using apt):**
```bash
sudo apt install build-essential libopenblas-dev libomp-dev \
  libeigen3-dev pybind11-dev
```

After system-wide installation, create `~/.gpirc` to specify custom paths (if needed):
```ini
MAKE_INC_DIRS=/usr/local/include
MAKE_LIB_DIRS=/usr/local/lib
```

---

## 6.2 The `gpi_make` Build Tool

`gpi_make` is the primary command-line tool for building GPI modules. Under the hood, it executes `make_pybind11.py`, which uses Python's `setuptools` to compile C++ extension modules directly into shared objects (`.so`/`.pyd`).

The build tool intelligently parses arguments, so you don't need to specify the full `_PYBIND11.cpp` filename:

```bash
# Build single module (finds MyModule_PYBIND11.cpp automatically)
gpi_make MyModule

# Build all modules recursively
gpi_make --all

# Remove all build artifacts and cache
gpi_make --clean
```

### Automatic Dependency Discovery

When targeting a module, `gpi_make`:
1. **Parses `#include` directives** in the `_PYBIND11.cpp` file
2. **Finds all `.hpp` files** referenced transitively
3. **Auto-discovers system libraries** (OpenMP, Eigen3, Pybind11)
4. **Detects your environment** (Conda? OS-specific linking?) and links the needed libraries
5. **Maintains MD5-based compilation cache** to skip rebuilding unchanged modules

**Example:** If your code includes `#include "Voxel/Voxel.hpp"`, the build system automatically:
- Links OpenMP libraries used by SIMD pragma kernels
- Adds Eigen3 and Pybind11 include paths
- Applies the project's compile flags
- **Note:** PocketFFT is header-only, so no external FFT library linking required

### Custom Configuration

The build system reads `gpi.config` and `~/.gpirc` to append custom paths:

```ini
# ~/.gpirc
MAKE_INC_DIRS=/usr/local/custom/include
MAKE_LIB_DIRS=/usr/local/custom/lib
```

In Conda environments, `gpi_make` automatically adds `$CONDA_PREFIX/include` and `$CONDA_PREFIX/lib`.

---

## 6.3 Production vs. Debug Mode

Your algorithm's behavior and performance changes based on which build mode you select:

```
┌─────────────────────────────────────────────┐
│      Ready to ship/publish results?         │
│                                             │
│              ✓ YES   ✗ NO                   │
│              │        │                     │
│              ▼        ▼                      │
│         PRODUCTION   DEBUG                  │
│        gpi_make M   gpi_make M --debug     │
└─────────────────────────────────────────────┘
```

### 6.3.1 Production Mode (Default)

```bash
gpi_make MyModule
```

**Compiler Flags Applied:**
- `-O3`: Aggressive compiler optimizations
- `-march=native`: Utilize all SIMD instructions on your CPU (AVX2, AVX-512, etc.)
- `-ffast-math`: Enable aggressive floating-point optimizations
- `-fcx-limited-range`: Remove IEEE 754 NaN/Inf checks for complex multiplication (2-5x faster)
- `-DNDEBUG`: Disable all C++ assertions

**Performance:**
- Typically much faster than debug mode
- Better optimization and vectorization opportunities
- OpenMP support is enabled for user code and library kernels that use OpenMP pragmas

**Use this for:**
- Final clinical/research results
- Benchmarking algorithms
- Production deployments

**Risk:** If your code has unchecked indexing bugs in hot paths, production mode is less likely to catch them early. Many shape checks in the library, including LinAlg argument validation, are still performed in all build modes.

### 6.3.2 Debug Mode

```bash
gpi_make MyModule --debug
```

**Compiler Flags Applied:**
- `-O0`: No optimizations (all code executed as-written)
- `-g`: Debug symbols included
- `GPIARRAY_ENABLE_BOUNDS_CHECKS`: Macro defined globally
- Bounds checking enabled throughout the library

**What Gets Checked:**
- **N-Dimensional Indexing:** Every `arr(i, j, k)` access validated against array bounds
- **Linear Algebra:** Array dimensions validated before MatMul, SVD, PCA operations (these checks are present in all build modes)
- **Assertions:** All C++ assertions enabled

**Performance:**
- 10–50× slower than production mode
- No SIMD vectorization
- Every operation incurs bounds-check overhead

**Use this for:**
- Algorithm development and testing
- Fixing indexing/dimension bugs
- Validating new code before shipping
- Diagnosing unsolved segmentation faults

**Example:** This throws an exception in both debug and production builds because the LinAlg wrapper validates dimensions explicitly:
```cpp
Array<double> A(3, 4);
Array<double> B(5, 5);
Array<double> C(3, 5);
LinAlg::matmul(A, B, C);  // Dimension mismatch → throws before calling Eigen
```

---

## 6.4 Building with Voxel Backends

`Voxel` includes specialized computational backends that are **automatically linked** when you include `Voxel.hpp`. No configuration needed.

### Automatic Backend Integration

When you include `#include "Voxel/Voxel.hpp"`, the build system automatically detects and links:

| Backend | When Used | Linked Automatically |
|---------|-----------|---------------------|
| **FFTW3** | `FFTW::fftn()`, `FFTW::ifftn()`, frequency-domain operations | ✓ Yes |
| **Eigen3** | `LinAlg::matmul()`, `LinAlg::svd()`, `LinAlg::pca()` | ✓ Yes |
| **OpenMP** | OpenMP-enabled compilation and SIMD-oriented pragmas | ✓ Yes |

Just include the header and use the feature—the build system handles the rest.

### SmartContiguity Handling

Voxel's `.contiguous()` method and automatic backend contiguity management are built-in:

```cpp
#include "Voxel/Voxel.hpp"
using namespace Voxel;

void process(const Array<Complex>& input) {
    // Works even if input is non-contiguous (e.g., from transpose)
    // Backends handle contiguity transparently
    Array<Complex> output = input.empty_like();
    
    // FFTW automatically calls .contiguous() if needed
    FFTW::fftn(input, output, FFTW::ImageToKspace);
}
```

No special build flags required—it's automatic.

---

## 6.5 All Build Commands

| Command | Purpose |
|---------|---------|
| `gpi_make MyModule` | Compile `MyModule_PYBIND11.cpp` → `MyModule.so` |
| `gpi_make --all` | Recursively find and compile all `_PYBIND11.cpp` files |
| `gpi_make --clean` | Delete all `build/`, `.so` files, and compilation cache |
| `gpi_make MyModule --debug` | Build with `-O0`, debug symbols, bounds checking |

---

## 6.6 Compiler Flags Reference

### Production Mode Flags

When you run `gpi_make` normally (production mode), these flags are applied:

```
-O3                 # Aggressive optimization
-march=native       # CPU-specific SIMD (AVX2, AVX-512, etc.)
-ffast-math         # Aggressive float math (no NaN/Inf handling)
-fcx-limited-range  # Skip IEEE 754 checks for complex multiplication
-DNDEBUG            # Disable assertions, bounds checking
```

**Result:** Usually much faster, but with fewer debugging guardrails than a debug build.

### Debug Mode Flags

When you run `gpi_make MyModule --debug`, these flags are applied:

```
-O0                 # No optimization (code runs as-written)
-g                  # Debug symbols
-DGPIARRAY_ENABLE_BOUNDS_CHECKS  # Enable all bounds checking
```

**Result:** Slower, but catches every error with precise location and message.

---

## 7.7 Troubleshooting Build Issues

### "gpi_make: command not found"

**Problem:** Build tool is not in your `PATH`.

**Solution:**
```bash
cd /path/to/gpi_source
pip install -e .
which gpi_make
# Should print: /path/to/python/bin/gpi_make
```

---

### "error: cannot find -lfftw3"

**Problem:** FFTW3 library not installed or not in library path.

**Solution (macOS with Homebrew):**
```bash
brew install fftw
# Verify installation
pkg-config --cflags --libs fftw3
```

**Solution (Ubuntu/Debian):**
```bash
sudo apt install libfftw3-dev libfftw3-threads-dev
pkg-config --cflags --libs fftw3
```

---

### "error: 'omp.h' file not found"

**Problem:** OpenMP headers missing (common on macOS with Apple Clang).

**Solution (macOS):**
```bash
brew install libomp
# Apple Clang should now find it automatically
```

**Solution (Linux):**
```bash
sudo apt install libomp-dev
```

If using GCC, OpenMP usually comes pre-installed. Verify:
```bash
gcc -fopenmp -xc -E - < /dev/null | grep -i omp
```

---

### "error: 'Eigen/Dense' file not found"

**Problem:** Eigen3 headers not installed.

**Solution (macOS):**
```bash
brew install eigen
```

**Solution (Ubuntu/Debian):**
```bash
sudo apt install libeigen3-dev
```

---

### "Segmentation fault" when running production code

**Problem:** Likely an indexing error or dimension mismatch that production mode doesn't catch.

**Solution:**
```bash
# Rebuild in debug mode for detailed error location
gpi_make MyModule --debug

# Run your code again—it will throw an exception with:
# - Exact line number
# - Dimension details
# - Expected vs. actual array bounds
```

Then fix the issue and rebuild with production mode.

---

### Build is slow / "make: cache hit, full rebuild unnecessary" not appearing

**Problem:** Files recompiling even though source is unchanged (cache not working).

**Cause:** The cache keys off a combined hash of the `_PYBIND11.cpp` module plus its discovered dependencies. Rebuilds still happen when any participating source or header changes, but cache misses can occur if dependency discovery changes or outputs were cleaned.

**Solution:**
```bash
# Clear all build artifacts and cache
rm -rf build/
rm -rf *.so

# Rebuild from scratch
gpi_make MyModule
```

---

### "ImportError: cannot import name 'MyModule'"

**Problem:** The compiled `.so` file is not in Python's path.

**Solution:**
```bash
# 1. Verify compilation succeeded
ls -la build/lib/MyModule.*.so

# 2. Add build/lib to PYTHONPATH
export PYTHONPATH=/path/to/gpi_source/build/lib:$PYTHONPATH

# 3. Try importing again
python -c "import MyModule; print('Success!')"
```

Or install in development mode (recommended):
```bash
cd /path/to/gpi_source
pip install -e .
```

---

### "error: redefinition of 'struct MyClass'" or "multiple definition of 'function'"

**Problem:** Header guard missing or circular includes in `.hpp` files.

**Solution:** Ensure every `.hpp` file has proper header guards:
```cpp
#ifndef MY_MODULE_HPP_
#define MY_MODULE_HPP_

// ... declarations ...

#endif  // MY_MODULE_HPP_
```

Alternatively, use `#pragma once` at the top of every header:
```cpp
#pragma once
// ... declarations ...
```

---

## 6.8 Performance Summary

| Aspect | Production Mode | Debug Mode |
|--------|-----------------|-----------|
| **Optimization** | `-O3` | `-O0` |
| **SIMD** | Full (`-march=native`) | None |
| **Bounds Checking** | None | Complete |
| **Speedup vs. Debug** | 10–50× faster | Baseline |
| **Memory Safety** | None | Full |
| **Complex Math** | Fast-math approximation | IEEE 754 compliant |
| **Use Case** | Shipping clinical/production results | Algorithm development & debugging |

---

## 6.9 Best Practices

### Development Workflow

1. **Start in debug mode** while developing algorithms:
   ```bash
   gpi_make MyModule --debug
   ```
   
2. **Fix all errors** until code runs without exceptions.

3. **Benchmark in production mode** when algorithm is working:
   ```bash
   gpi_make MyModule
   # Run same code again to measure actual performance
   ```

4. **Deploy with production mode** for real results.

### Configuration

- **Use Conda** for reproducible builds across platforms
- **Document your environment** in `environment.yml` or `requirements.txt`
- **Document custom include/lib paths** in project notes or reproducible environment files if you rely on them

### Optimization Tips

- Use `.contiguous()` before passing to FFTW/LinAlg if memory layout is uncertain
- Enable `-march=native` (production mode default) to utilize your CPU's specific SIMD capabilities
- Consider parallelizing surrounding batch work with OpenMP after profiling, rather than assuming the FFT wrapper itself is multithreaded
- Profile with debug mode first to identify bottlenecks before production mode

---
| Use case | Shipping code | Development |
