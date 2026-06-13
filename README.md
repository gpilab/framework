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
| Build tools | pybind11 ≥ 2.12, Eigen3, FFTW3 |

> **Conda / Miniforge recommended.** All binary dependencies (PyQt6, FFTW, Eigen, compilers) are available from `conda-forge` and install in a single command.

---

## Installation

### Step 1 — Create the conda environment

Pick the command for your platform. All commands create an environment named `gpi`.

**macOS**
```shell
conda create -n gpi -c conda-forge \
    python=3.13 pyqt6 qtpy "numpy>=1.26" "scipy>=1.11" \
    "matplotlib>=3.8" h5py pillow "pydicom>=2.4" "pyqtgraph>=0.13.3" \
    fftw eigen "pybind11>=2.12" compilers llvm-openmp zlib
```

**Linux**
```shell
conda create -n gpi -c conda-forge \
    python=3.13 pyqt6 qtpy "numpy>=1.26" "scipy>=1.11" \
    "matplotlib>=3.8" h5py pillow "pydicom>=2.4" "pyqtgraph>=0.13.3" \
    fftw eigen "pybind11>=2.12" compilers zlib
```

**Windows** — use the provided `environment.yml` (includes the MinGW-w64 toolchain):
```shell
conda env create -f environment.yml
```

Or manually:
```shell
conda create -n gpi -c conda-forge ^
    python=3.13 pyqt6 qtpy "numpy>=1.26" "scipy>=1.11" ^
    "matplotlib>=3.8" h5py pillow "pydicom>=2.4" "pyqtgraph>=0.13.3" ^
    fftw eigen "pybind11>=2.12" gxx_win-64 distutils-activate-mingw zlib
```

> **Windows compiler notes**
> - `gxx_win-64` — MinGW-w64 GCC 13+ with C++17/C++20 support, `gendef`, and `dlltool` for building C/C++ node extensions.
> - `distutils-activate-mingw` — configures setuptools to use the MinGW compiler instead of MSVC.
> - `zlib` — provides `zlib.h` required by `cnpy.h` (used in Voxel/Array nodes).
> - `compilers` and `llvm-openmp` are **macOS/Linux only** — do not use on Windows.

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

On Windows you can also double-click `gpi.cmd` in the repository root (it activates the conda env automatically).

---

## Building C++ Nodes

To compile a node that has C/C++ extensions (e.g. a custom node using Voxel or a FFTW wrapper):

**macOS / Linux**
```shell
cd /path/to/node
gpi_make --all
```

**Windows**
```shell
cd C:\path\to\node
gpi_make
```

`gpi_make` on Windows automatically passes `--all` via the `gpi_make.cmd` wrapper — no extra flags needed. The MinGW-w64 toolchain from the conda environment is used automatically. If you see compiler errors on first run, execute `gpi_init` again to re-run the MinGW environment setup.

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

## Development Notes

| File | Purpose |
|---|---|
| `environment.yml` | Reproducible Windows conda environment |
| `gpi_init` / `gpi_init.cmd` | Builds all C/C++ node extensions |
| `gpi_make` / `gpi_make.cmd` | Builds a single node directory |
| `win_setup.py` | Windows-specific compiler detection and setup |
| `gpi/include/Voxel/` | C++ N-D array library (pybind11, PocketFFT, Eigen) |

### Editable install workflow

```shell
# edit source files in gpi/ or gpi_core/
pip install -e .   # only needed if pyproject.toml / setup.py changed
gpi                # picks up changes immediately for Python-only nodes
```

For C++ node changes:
```shell
cd gpi_core/path/to/node
gpi_make --all
```

### Python version note

GPI 2.0 targets **Python 3.13** (standard CPython, not the free-threaded `cp313t` build). PyQt6 conda-forge wheels exist for `py313`; the free-threaded ABI does not yet have Qt bindings in any major package repository.
