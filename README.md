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

Choose an environment name. The examples below use `my-gpi`; replace it with your chosen name everywhere, including activation and update commands. The environment files do not set a name.

Choose **one** of the following options. Neither requires the setup script.

#### Option A — Use an environment file (recommended)

Run the command for your platform from the `gpi_source` directory:

**Windows** (in Miniforge Prompt):
```shell
conda env create --name my-gpi -f environment.yml
```

**macOS**:
```shell
conda env create --name my-gpi -f environment_macos.yml
```

**Linux**:
```shell
conda env create --name my-gpi -f environment_linux.yml
```

This downloads and installs Python 3.12 on Windows or Python 3.13 on macOS/Linux, PyQt6, NumPy, SciPy, the C++ build tools, and the remaining dependencies (including PyTorch). It may take a few minutes.

#### Option B — Create the environment manually (no script or YAML file)

Run **one** command below for your platform. These commands create the environment and install the GUI, scientific libraries, and C++ build dependencies from conda-forge. Keep the quotes around package constraints.

**Windows** (in Miniforge Prompt):
```shell
conda create --name my-gpi --override-channels -c conda-forge python=3.12 pyqt6 "qtpy>=2.4.0" "libblas=*=*openblas" "numpy>=1.26" "scipy>=1.11" "matplotlib>=3.8" h5py hdf5=2.1 "pillow>=9.1" "pydicom>=2.4" "nibabel>=5.2.0" "pyqtgraph>=0.13.3" zlib fftw eigen "pybind11>=3.0" gxx_win-64 distutils-activate-mingw pip
```

**macOS**:
```shell
conda create --name my-gpi --override-channels -c conda-forge python=3.13 pyqt6 "qtpy>=2.4.0" "numpy>=1.26" "scipy>=1.11" "matplotlib>=3.8" h5py "pillow>=9.1" "pydicom>=2.4" "nibabel>=5.2.0" "pyqtgraph>=0.13.3" zlib fftw eigen "pybind11>=3.0" compilers llvm-openmp pip
```

**Linux**:
```shell
conda create --name my-gpi --override-channels -c conda-forge python=3.13 pyqt6 "qtpy>=2.4.0" "numpy>=1.26" "scipy>=1.11" "matplotlib>=3.8" h5py "pillow>=9.1" "pydicom>=2.4" "nibabel>=5.2.0" "pyqtgraph>=0.13.3" zlib fftw eigen "pybind11>=3.0" compilers pip
```

Continue with Steps 4–7 below. Step 5 installs GPI and its remaining required Python packages. PyTorch is optional for this manual path; see [GPU Support](#gpu-support-optional) if you need it.

> **Optional setup helper:** If you prefer automatic platform and NVIDIA GPU detection, run `python setup_conda_env.py --env-name my-gpi` instead of either option above, then continue with Step 4. The helper updates an existing environment with that name, so choose a new name for a separate installation.

---

### Step 4 — Activate the environment

Every time you open a new terminal to use GPI, run this first:

```shell
conda activate my-gpi
```

Your prompt will change to show `(my-gpi)` (or your chosen name) at the start — this means the environment is active.

---

### Step 5 — Install GPI

```shell
pip install .
```

Run this from the `gpi_source` directory with your chosen environment active.

---

### Step 6 — Build the C++ extensions

```shell
gpi_init
```

This compiles the built-in C++ nodes (FFT, gridding, image processing). It only needs to run once (and again after updating).

At the end of `gpi_init` you will be prompted to create a desktop shortcut:

```
=== GPI Shortcut Setup ===
Where would you like to create a GPI shortcut?

  1 - Desktop
  2 - Start Menu (Programs)
  3 - Both Desktop and Start Menu  [recommended]
  4 - Skip

Choice [3]:
```

Press **Enter** to accept the recommended option, or type a number to choose. You can also create or recreate shortcuts at any time via **File → Create Desktop Shortcut** inside GPI.

---

### Step 7 — Launch GPI

```shell
gpi
```

Or double-click the **GPI** shortcut on your Desktop / Start Menu if you created one in the previous step.

---

## Using GPI

### The Canvas

The canvas is where you build pipelines by placing and connecting nodes. Right-click anywhere on the canvas to open the node library and add a node. Drag from an output port to an input port to connect two nodes — GPI automatically re-runs the downstream computation.

---

### Menus

| Menu | Key actions |
|---|---|
| **File** | New Tab, Load / Save Network, Open Terminal, Create Desktop Shortcut, Show Log Output, Settings |
| **Edit** | Undo / Redo, Copy / Paste / Paste with Connections, Delete, Select All, Find Node, Reload Node, Organize Nodes, Pause / Unpause, Close All Node Menus/Console, Zoom In / Out |
| **Library** | Create New Library, Create New Node, Scan For New Nodes |
| **Debug** | Logger Level, Print sys.paths / sys.modules |
| **Help** | About, Documentation, Examples, Check For Updates |

---

### Keyboard Shortcuts

All canvas shortcuts are configurable via **File → Settings → Shortcuts**. The defaults are:

| Action | Default Shortcut |
|---|---|
| Undo | `Ctrl+Z` |
| Redo | `Ctrl+Y` |
| Copy | `Ctrl+C` |
| Paste | `Ctrl+V` |
| Paste with Connections | `Ctrl+Shift+V` |
| Delete Selected | `Del` |
| Select All | `Ctrl+A` |
| Find Node | `Ctrl+F` |
| Load Network | `Ctrl+L` |
| Save Network | `Ctrl+S` |
| Reload Node | `Ctrl+R` |
| Organize Nodes | `Ctrl+O` |
| Pause / Unpause | `Ctrl+P` |
| Close All Node Menus/Console | `Ctrl+X` |
| Zoom In | `+` |
| Zoom Out | `-` |

To change a shortcut, go to **File → Settings → Shortcuts**, click the field next to the action, and press the new key combination.

---

### Settings

Open **File → Settings** (`Ctrl+,`) to configure:

- **Appearance** — switch between Dark and Classic themes; choose Horizontal or Vertical connector layout
- **Paths** — set the Node Library directory, default network save location, and data directory
- **Associations** — map file extensions to nodes (e.g. `.png` → ReadImage) for drag-and-drop onto the canvas
- **Shortcuts** — remap any canvas shortcut and configure node deploy shortcuts
- **Make** — advanced C++ build settings for custom nodes

Click **Restore Defaults** at the bottom of the Settings dialog to reset everything to factory defaults.

---

### Log Output

GPI captures all runtime messages (node errors, warnings, debug output) in a floating **GPI Log Output** window. To open it:

- **File → Show Log Output**
- When GPI is launched via a desktop shortcut, the log window opens automatically at startup.

---

### Open Terminal

**File → Open Terminal** opens a terminal pre-activated with the GPI conda environment. This works whether GPI was launched from the command line or a desktop shortcut.

---

### File Associations

Drag a file from the file browser node onto the canvas to automatically place the appropriate reader node. Default associations include:

`.bmp`, `.csv`, `.dcm`, `.gif`, `.h5`, `.hdf5`, `.jpeg`, `.jpg`, `.mat`, `.mridata`, `.npy`, `.pickle`, `.pkl`, `.png`, `.raw`, `.tif`, `.tiff`, `.webp`

Custom associations can be added in **File → Settings → Associations**.

---

## Updating GPI

When a new version is available:

```shell
conda activate my-gpi
cd gpi_source
git pull
pip install -e .
gpi_init
```

`gpi_init` only recompiles nodes whose source has changed — subsequent runs are fast.

Replace `my-gpi` with the environment name you chose during installation.

---

## Troubleshooting

**`conda: command not found`** — Close and reopen your terminal after installing Miniforge.

**`gpi: command not found`** — Make sure your chosen environment is active (for example, `conda activate my-gpi`) and that `pip install .` completed without errors.

**Compiler errors during `gpi_init` on Windows** — Run `gpi_win_setup` once, then retry `gpi_init`. This configures the MinGW compiler that ships with the conda environment.

**macOS security warning on first launch** — Go to System Settings → Privacy & Security and click *Open Anyway*.

**Node errors not visible** — Open **File → Show Log Output** to see the full error trace. When launched via desktop shortcut the log window opens automatically.

---

## GPU Support (optional)

The environment-file and setup-helper options install `torch`; the manual option leaves it optional. With your chosen environment active, use the commands below to add PyTorch or select a CPU/CUDA build for the `TORCH_TENSOR` port type:

**CPU only:**
```shell
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

**NVIDIA GPU (CUDA 12.4):**
```shell
pip install torch --index-url https://download.pytorch.org/whl/cu124
```

Replace `cu124` with your CUDA version (e.g. `cu121` for CUDA 12.1). See [pytorch.org](https://pytorch.org/get-started/locally/) for the full list.
