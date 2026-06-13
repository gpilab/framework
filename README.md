[![GPI Framework](http://gpilab.com/images/framewrk_b.jpg)](http://gpilab.com)

**GPI** (**G**raphical **P**rogramming **I**nterface) is a visual dataflow environment for scientific algorithms. Algorithm elements (nodes) are linked together on a canvas to form a processing pipeline. Each node executes according to the dependency order of the graph.

[![GPI Framework](http://docs.gpilab.com/en/develop/_images/uilabels.jpg)](http://gpilab.com)

- [Website](https://gpilab.com/)
- [Documentation](http://docs.gpilab.com/en/develop/)
- [Issues](https://github.com/gpilab/framework/issues)

---

## Requirements

| Component | Version |
|---|---|
| Python | 3.13 |
| Qt bindings | PyQt6 |
| C++ compiler | GCC 13+ (Linux/Windows) · Apple Clang 15+ (macOS) |
| Build tools | pybind11 ≥ 3.0, Eigen3, FFTW3 |

> **Conda / Miniforge recommended.** All binary dependencies (PyQt6, FFTW, Eigen, compilers) are available from `conda-forge` and install in a single command.

---

## Installation

### Step 1 — Create the conda environment

#### Option A — Auto-detect (recommended)

`setup_conda_env.py` detects your OS, CPU architecture, and whether an NVIDIA GPU is present, then runs the right `conda env create` command and (for Linux/Windows with CUDA) reinstalls `torch` with the matching CUDA wheel.

```shell
python setup_conda_env.py
```

Optional flags:
```shell
python setup_conda_env.py --cuda-version 12.1   # override CUDA detection
python setup_conda_env.py --dry-run             # print commands without running
```

#### Option B — Manual

Pick the environment file for your platform and run `conda env create`. All files create an environment named `gpi`.

| Platform | File |
|---|---|
| macOS | `environment_macos.yml` |
| Linux | `environment_linux.yml` |
| Windows | `environment.yml` |

```shell
# macOS
conda env create -f environment_macos.yml

# Linux
conda env create -f environment_linux.yml

# Windows
conda env create -f environment.yml
```

**Linux / Windows with NVIDIA GPU** — reinstall torch with the CUDA wheel after env creation:
```shell
# Example for CUDA 12.4:
pip install torch --index-url https://download.pytorch.org/whl/cu124
```

> **Compiler package notes**
> - `compilers` + `llvm-openmp` — macOS only (Apple Clang wrapper + OpenMP runtime).
> - `compilers` alone — Linux only (GCC 13+ from conda-forge).
> - `gxx_win-64` + `distutils-activate-mingw` — Windows only (MinGW-w64 + setuptools routing).
> - Never mix compiler packages across platforms.

---

### Step 2 — Activate the environment

```shell
conda activate gpi
```

---

### Step 3 — Install pip dependencies

```shell
pip install dill grpcio grpcio-tools multiprocess pathos pox ppft \
            psutil PyOpenGL qimage2ndarray PyWavelets torch
```

> `torch` is required for the `TORCH_TENSOR` GPU port type. Install the CPU-only build if you don't have a GPU:
> ```shell
> pip install torch --index-url https://download.pytorch.org/whl/cpu
> ```

---

### Step 4 — Install GPI from source

```shell
git clone https://github.com/gpilab/framework.git gpi_source
cd gpi_source
pip install -e .
```

The `-e` flag installs in editable mode so changes to the source take effect immediately without reinstalling.

---

### Step 5 — Build the core nodes

```shell
gpi_init
```

This compiles all C/C++ extensions in `gpi_core` (FFT wrappers, Voxel library, gridding nodes, etc.).

---

### Step 6 — Launch GPI

```shell
gpi
```

On Windows you can also double-click `bin/gpi.cmd` (it activates the conda env automatically).

---

## Building C++ Nodes

GPI supports two styles of C++ extension modules:

| Style | File suffix | Build system | When to use |
|---|---|---|---|
| PyFI (legacy) | `*_PyMOD.cpp` | `make.py` (called by `gpi_make`) | Existing `gpi_core` nodes |
| pybind11 | `*_bind.cpp` | `make_pybind11.py` (also called by `gpi_make`) | New nodes — use this for all new C++ work |

`gpi_make` invokes both build systems automatically so you do not need to call them separately.

**macOS / Linux**
```shell
cd /path/to/node
gpi_make --all          # find and compile all _PyMOD.cpp and _bind.cpp files
gpi_make MyModule       # compile MyModule_bind.cpp only
```

**Windows**
```shell
cd C:\path\to\node
gpi_make --all
gpi_make MyModule
```

The MinGW-w64 toolchain from the conda environment is used automatically on Windows. If you see compiler errors on first run, execute `gpi_init` again to re-run the MinGW environment setup.

### Writing a pybind11 node

Name your binding file `<ModuleName>_bind.cpp` and end it with:

```cpp
PYBIND11_MODULE(ModuleName, m) {
    m.def("my_func", &my_func, "docstring");
}
```

Build it with:
```shell
gpi_make ModuleName
```

Import it from the GPI Python node:
```python
from my_library import ModuleName as mod
result = mod.my_func(data)
```

See `gpi_nodes/voxel_examples/` for complete worked examples.

---

## Updating

Pull the latest changes and reinstall:
```shell
git pull
pip install -e .
gpi_init
```

`gpi_init` only recompiles nodes whose source has changed (incremental build).

---

## Example Nodes (voxel_examples)

The `gpi_nodes/voxel_examples/` library provides beginner-friendly example nodes that demonstrate how to write GPI nodes — from pure Python to calling compiled C++ via pybind11.

| Node | Demonstrates |
|---|---|
| `01_ArrayCreation` | Creating arrays with zeros/ones/linspace/random |
| `02_InlineMath` | Pure Python math on port data (abs, normalize, scale) |
| `03_FFTNumPy` | N-D FFT using NumPy — the pure-Python reference |
| `04_VoxelFFT` | Same FFT via `Voxel::FFT::fftn()` through pybind11 |
| `05_VoxelFilter` | Gaussian k-space filter (FFT → multiply → IFFT) in C++ |
| `06_VoxelLinAlg` | SVD singular values via `Voxel::LinAlg::svd()` |
| `07_VoxelStats` | Array reductions: min/max/mean/stdev/l2norm |

Demo networks in `gpi_nodes/voxel_examples/networks/`:
- `VoxelDemo_FFT.net` — pure Python FFT pipeline (no compilation needed)
- `VoxelDemo_Filter.net` — Gaussian k-space filter (requires compiled C++ module)

To build the C++ examples:
```shell
cd gpi_nodes/voxel_examples
gpi_make VoxelExamples
```

---

## Framework Improvements (GPI 2.0)

| Feature | Description |
|---|---|
| **Compute error channel** | `compute()` can `return "error message"` to signal failure; the string is shown in the node status bar and logged |
| **Port inspection API** | `self.isPortConnected('title')` and `self.getConnectedNodes('title')` available inside `compute()` / `validate()` |
| **Cycle detection fix** | Connection edges are now correctly invalidating the topology cache before cycle detection runs |
| **PyQt6 / Python 3.13** | Full migration from PyQt5; all deprecated Qt4/5 APIs removed |
| **pybind11 3.x node support** | New `*_bind.cpp` naming convention; `gpi_make` handles both PyFI and pybind11 modules |

---

## Development Notes

| File / Directory | Purpose |
|---|---|
| `setup_conda_env.py` | Auto-detects OS/GPU and creates the conda environment |
| `environment.yml` | Windows conda environment (MinGW-w64 toolchain) |
| `environment_macos.yml` | macOS conda environment (Apple Clang + llvm-openmp) |
| `environment_linux.yml` | Linux conda environment (GCC via conda-forge compilers) |
| `bin/gpi` · `bin/gpi.cmd` | Launch GPI (shell / Windows) |
| `bin/gpi_init` · `bin/gpi_init.cmd` | Build all C/C++ node extensions |
| `bin/gpi_make` · `bin/gpi_make.cmd` | Build a single node directory |
| `gpi/make.py` | Build driver for legacy `*_PyMOD.cpp` (PyFI) nodes |
| `gpi/make_pybind11.py` | Build driver for `*_bind.cpp` pybind11 nodes |
| `gpi/win_setup.py` | Windows-specific compiler detection and setup |
| `gpi/include/Voxel/` | C++ N-D array library (pybind11, PocketFFT, Eigen) |
| `gpi_nodes/voxel_examples/` | Beginner example nodes (pure Python → pybind11 C++) |

### Editable install workflow

```shell
# edit source files in gpi/ or gpi_core/
pip install -e .   # only needed if pyproject.toml / setup.py changed
gpi                # picks up changes immediately for Python-only nodes
```

For C++ node changes (pybind11):
```shell
cd gpi_nodes/your_library
gpi_make MyModule      # compiles MyModule_bind.cpp
```

For legacy PyFI nodes in gpi_core:
```shell
cd gpi_core/path/to/node
gpi_make --all
```

### Python version note

GPI 2.0 targets **Python 3.13** (standard CPython, not the free-threaded `cp313t` build). PyQt6 conda-forge wheels exist for `py313`; the free-threaded ABI does not yet have Qt bindings in any major package repository.
