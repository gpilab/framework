[![GPI Framework](http://gpilab.com/images/framewrk_b.jpg)](http://gpilab.com)

GPI stands for **G**raphical **P**rogramming **I**nterface which is a development environment for scientific algorithms that provides a visual workspace for assembling algorithms. Algorithm elements (i.e. nodes) can be linked together to form a flow diagram. Each node is executed according to the hierarchy of the diagram.

[![GPI Framework](http://docs.gpilab.com/en/develop/_images/uilabels.jpg)](http://gpilab.com)

- [Website](https://gpilab.com/)

- [Documentation](http://docs.gpilab.com/en/develop/)

- [Issues](https://github.com/gpilab/framework/issues)

## Installing

### macOS / Linux

Create a new conda environment for gpi:
```shell
conda create -n gpi python=3.9 fftw eigen qt compilers llvm-openmp -c conda-forge
conda activate gpi
```

### Windows

Windows requires the MinGW-w64 GCC 13+ toolchain (for C++17 support in pybind11 nodes):
```shell
conda create -n gpi python=3.9 fftw eigen qt zlib gxx_win-64 distutils-activate-mingw -c conda-forge
conda activate gpi
```

**Package notes:**
- `gxx_win-64` — provides MinGW-w64 GCC 13+ (C++17/C++20), `gendef`, and `dlltool` needed to build C/C++ extensions
- `distutils-activate-mingw` — configures Python's `distutils`/`setuptools` to use the MinGW compiler
- `zlib` — provides `zlib.h` required by some pybind11 nodes (`cnpy.h`)
- `compilers` and `llvm-openmp` are macOS/Linux packages and should **not** be used on Windows
- **pthreads** are provided by the MinGW sysroot (no separate `pthreads-win32` needed)

### All platforms

Install gpi from source:
```shell
git clone https://github.com/gpilab/framework.git gpi_source
cd gpi_source
pip install .
```

Build the core nodes:
```shell
gpi_init
```

You can now run `gpi` from your conda environment:
```shell
gpi
```

To build a node with C dependencies:
```shell
cd /path/to/node
gpi_make --all
```
