[![GPI Framework](http://gpilab.com/images/framewrk_b.jpg)](http://gpilab.com)

**GPI** (**G**raphical **P**rogramming **I**nterface) is a visual dataflow environment for scientific algorithms. Connect algorithm nodes on a canvas to build processing pipelines — no boilerplate, just science.

[![GPI Canvas](http://docs.gpilab.com/en/develop/_images/uilabels.jpg)](http://gpilab.com)

- [Website](https://gpilab.com/)
- [Documentation](http://docs.gpilab.com/en/develop/)
- [Issues](https://github.com/gpilab/framework/issues)

---

## Quick Install (all platforms)

> **New to Python?** Follow the steps in order — each one builds on the last.

---

### Step 1 — Install Miniforge

Miniforge is a lightweight conda installer that gives you Python and the `conda` package manager. If you already have Miniforge or Anaconda installed, skip to Step 2.

| Platform | Download |
|---|---|
| Windows | [Miniforge3-Windows-x86_64.exe](https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Windows-x86_64.exe) |
| macOS (Apple Silicon) | [Miniforge3-MacOSX-arm64.sh](https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-MacOSX-arm64.sh) |
| macOS (Intel) | [Miniforge3-MacOSX-x86_64.sh](https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-MacOSX-x86_64.sh) |
| Linux | [Miniforge3-Linux-x86_64.sh](https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh) |

**Windows:** Run the `.exe` installer, accept the defaults, and when it finishes open **Miniforge Prompt** from the Start menu.

**macOS / Linux:** Open a Terminal, then run:
```shell
bash Miniforge3-*.sh
```
Follow the prompts and restart your terminal when done.

---

### Step 2 — Get the GPI source code

In your terminal (or Miniforge Prompt on Windows):

```shell
git clone https://github.com/gpilab/framework.git gpi_source
cd gpi_source
```

> If you don't have `git`, install it from [git-scm.com](https://git-scm.com/downloads) (Windows) or with `conda install git`.

---

### Step 3 — Create the GPI conda environment

This creates an isolated Python environment with all of GPI's dependencies. Run the command for your platform:

**Windows** (in Miniforge Prompt):
```shell
conda env create -f environment.yml
```

**macOS**:
```shell
conda env create -f environment_macos.yml
```

**Linux**:
```shell
conda env create -f environment_linux.yml
```

This downloads and installs Python 3.13, PyQt6, NumPy, SciPy, and all other required packages. It may take a few minutes.

---

### Step 4 — Activate the environment

Every time you open a new terminal to use GPI, run this first:

```shell
conda activate gpi
```

Your prompt will change to show `(gpi)` at the start — this means the environment is active.

---

### Step 5 — Install GPI

```shell
pip install -e .
```

The `-e` flag installs GPI in *editable* mode, meaning any changes you make to the source files take effect immediately.

---

### Step 6 — Build the C++ extensions

```shell
gpi_init
```

This compiles the built-in C++ nodes (FFT, gridding, image processing). It only needs to run once (and again after updating).

---

### Step 7 — Launch GPI

```shell
gpi
```

**Windows shortcut:** Once installed, you can also double-click `bin/gpi.cmd` to launch GPI without opening a terminal first.

---

## Updating GPI

When a new version is available:

```shell
conda activate gpi
cd gpi_source
git pull
pip install -e .
gpi_init
```

`gpi_init` only recompiles nodes whose source has changed — subsequent runs are fast.

---

## Troubleshooting

**`conda: command not found`** — Close and reopen your terminal after installing Miniforge.

**`gpi: command not found`** — Make sure the `gpi` environment is active (`conda activate gpi`) and that `pip install -e .` completed without errors.

**Compiler errors during `gpi_init` on Windows** — Run `gpi_win_setup` once, then retry `gpi_init`. This configures the MinGW compiler that ships with the conda environment.

**macOS security warning on first launch** — Go to System Settings → Privacy & Security and click *Open Anyway*.

---

## GPU Support (optional)

By default, `torch` is not installed. To enable the `TORCH_TENSOR` port type for GPU-accelerated nodes:

**CPU only:**
```shell
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

**NVIDIA GPU (CUDA 12.4):**
```shell
pip install torch --index-url https://download.pytorch.org/whl/cu124
```

Replace `cu124` with your CUDA version (e.g. `cu121` for CUDA 12.1). See [pytorch.org](https://pytorch.org/get-started/locally/) for the full list.
