# Section 6: Build System & Integration

Because `GPIArray` is optimized for computational scientists, proper compilation is critical for performance. This section covers the two commands you need, when to use debug mode, how dependencies are handled, and how to troubleshoot build failures.

## 6.0 30-Second Quick-Start

**You only need 2 commands:**

```bash
# 1. Build a single module (e.g., MyModule_PYBIND11.cpp)
gpi_make MyModule

# 2. Build all modules in your project
gpi_make --all

# BONUS: Debug mode (when debugging algorithm)
gpi_make MyModule --debug
```

That's it. The build system automatically:
- Finds all `.hpp` dependencies
- Detects your C++ version, OpenMP, FFTW3, Eigen3
- Compiles with maximum performance (`-O3`, `-march=native`, SIMD)
- Caches unchanged builds for speed

## 6.1 Prerequisites

### Using Conda (Recommended)

If you're in a **Conda environment** with all dependencies pre-installed, `gpi_make` automatically detects it and uses:
- CompilerC++ compiler from conda (GCC/Clang with C++20 support)
- OpenMP from Conda (`libomp` on macOS, `libgomp` on Linux)
- FFTW3 (single + double precision, with threading)
- Eigen3 (linear algebra backend)
- Pybind11 

```bash
# You're all set! Just run:
gpi_make MyModule
```

The build system inspects `$CONDA_PREFIX` and automatically adds conda's include/lib paths.

### Manual Installation (if not using Conda)

If installing system-wide, you need these libraries:

| Library | macOS | Ubuntu/Debian |
|---------|-------|---------------|
| **C++20 Compiler** | Xcode 13+ or Clang 10+ | GCC 10+ or Clang 10+ |
| **OpenMP** | `brew install libomp` | Usually pre-installed |
| **FFTW3** | `brew install fftw` | `apt install libfftw3-dev libfftw3-threads-dev` |
| **Eigen3** | `brew install eigen` | `apt install libeigen3-dev` |
| **Pybind11** | `pip install pybind11` | `pip install pybind11` |

## 6.2 Two Build Modes

Your algorithm behavior changes based on which mode you choose:

```
┌─────────────────────────────┐
│   Ready to ship/publish?    │
│                             │
│         ✓ YES   ✗ NO        │
│         │       │           │
│         ▼       ▼           │
│    PRODUCTION  DEBUG        │
│   gpi_make M  gpi_make M    │
│              --debug       │
└─────────────────────────────┘
```

### 6.2.1 Production Mode (Default)

```bash
gpi_make MyModule
```

**What happens:**
- Compiler becomes aggressive: `-O3 -march=native -ffast-math`
- All bounds checking removed (`-DNDEBUG`)
- ~10-50x faster than debug mode
- Math is approximate (not IEEE 754 compliant) to squeeze every instruction

**Use this for:**
- Final clinical/research results
- Benchmarking algorithms
- Production deployments

**Risk:** If your code has an off-by-one indexing error, you'll get silent memory corruption, not a helpful error message.

### 6.2.2 Debug Mode

```bash
gpi_make MyModule --debug
```

**What happens:**
- Compiler is conservative: `-O0` (no optimizations)
- Debug symbols included (`-g`)
- Every array access is validated
- Bounds-checking enabled system-wide

**Use this for:**
- Algorithm development
- Fixing indexing/dimension bugs
- Testing new code before shipping

**Trade-off:** 10-50x slower, but catches mistakes early.

## 6.3 How Dependencies Are Handled

**You don't specify them manually.** The build system:

1. **Scans `#include` statements** in your `_PYBIND11.cpp` file
2. **Finds all `.hpp` files** referenced transitively
3. **Auto-discovers system libraries** (OpenMP, FFTW, Eigen, pybind11)
4. **Detects your environment** (Conda? macOS? Linux?) and links correctly

Example: If your code says `#include "GPIArray/GPIArray.hpp"`, the build system automatically:
- Links FFTW3 (single + double precision, with threading)
- Links Eigen3 and its BLAS backend
- Links OpenMP thread pool
- Includes pybind11

**Custom paths?** Create `~/.gpirc`:

```ini
MAKE_INC_DIRS=/usr/local/custom/include
MAKE_LIB_DIRS=/usr/local/custom/lib
```

## 6.4 All Build Commands

| Command | Effect |
|---------|--------|
| `gpi_make MyModule` | Compile `MyModule_PYBIND11.cpp` → `.so` module |
| `gpi_make --all` | Recursively find and compile all `_PYBIND11.cpp` |
| `gpi_make --clean` | Delete all `build/`, `.so` files, compilation cache |
| `gpi_make MyModule --debug` | Build with `-O0`, bounds checking, debug symbols |

## 6.5 Troubleshooting

### "gpi_make: command not found"

**Problem:** Build tool not in your PATH.

**Solution:**
```bash
cd /path/to/gpi_source
pip install -e .
which gpi_make
```

Should print `/path/to/python/bin/gpi_make`.

### "error: cannot find -lfftw3"

**Problem:** FFTW3 library not installed.

**Solution (macOS):**
```bash
brew install fftw
```

**Solution (Ubuntu/Debian):**
```bash
sudo apt install libfftw3-dev libfftw3-threads-dev
```

### "error: 'omp.h' file not found"

**Problem:** OpenMP not available (common on macOS with default Clang).

**Solution (macOS only):**
```bash
brew install libomp
# Xcode Clang should now find it automatically
```

**Solution (Linux):**
OpenMP comes with GCC/Clang by default. If missing:
```bash
sudo apt install libomp-dev
```

### "Segmentation fault" after `gpi_make --release`

**Problem:** Likely an indexing error. Production mode doesn't catch these.

**Solution:**
```bash
# Rebuild in debug mode to get exact error location
gpi_make MyModule --debug
# Run your code again and it will throw a detailed exception
```

### Build is slow / cache not being used

**Problem:** Files keep recompiling even though source hasn't changed.

**Solution:**
```bash
# Clear the cache
rm -rf build/
# Only `_PYBIND11.cpp` timestamp changes trigger rebuilds
```

## 6.6 Advanced: What "--debug" Actually Does

When you pass `--debug`:

1. **Turns off optimizations:** `-O0` instead of `-O3`
2. **Enables debug symbols:** `-g` added to compiler flags
3. **Activates bounds checking macro:** `GPIARRAY_ENABLE_BOUNDS_CHECKS` is defined
   - Validates every `arr(i, j, k)` indexing operation
   - Checks matrix dimensions before MatMul, SVD, PCA
   - Throws `GPIArray::IndexError` instead of silently corrupting memory

Example: In debug mode, this code throws immediately:
```cpp
Array<double> A(3, 4);
LinAlg::matmul(A, B, C);  // If B.dimensions(0) != 4 → exception
```

In production mode, it silently reads garbage memory.

## 6.7 Performance Notes

| Aspect | Production | Debug |
|--------|-----------|-------|
| Optimization level | `-O3` | `-O0` |
| SIMD vectorization | Full (`-march=native`) | None |
| Bounds checking | None | Full |
| Typical speedup vs debug | 10-50x faster | Baseline |
| Memory safety | None | Complete |
| Use case | Shipping code | Development |