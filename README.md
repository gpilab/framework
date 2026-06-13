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
| `setup_conda_env.py` | Auto-detects OS/GPU and creates the conda environment |
| `environment.yml` | Windows conda environment (MinGW-w64 toolchain) |
| `environment_macos.yml` | macOS conda environment (Apple Clang + llvm-openmp) |
| `environment_linux.yml` | Linux conda environment (GCC via conda-forge compilers) |
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
