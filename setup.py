import pathlib
from setuptools import setup
from setuptools import find_packages

HERE = pathlib.Path(__file__).parent
README = (HERE / "README.md").read_text()

setup(
    name="gpilab",
    version="2.0.0",
    description="Graphical Programming Interface",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://github.com/gpilab/framework",
    author="AbdulRahman Alfayad",
    author_email="alfayad.abdulrahman@mayo.edu",
    license="GNU",
    packages=find_packages(),
    install_requires=[
        "cycler>=0.11.0",
        "dill>=0.3.7",
        "fonttools>=4.40.0",
        "grpcio>=1.81.1",
        "grpcio-tools>=1.81.1",
        "h5py",
        "kiwisolver>=1.4.5",
        "matplotlib>=3.8.0",
        "multiprocess>=0.70.15",
        "numpy>=1.26.0",
        "packaging>=22.0",
        "pathos>=0.3.1",
        "Pillow>=9.1.0",
        "pox>=0.3.2",
        "ppft>=1.7.6",
        "protobuf>=4.25.0",
        "psutil>=5.9.0",
        "PyOpenGL>=3.1.7",
        "pyparsing>=3.1.0",
        "pyqtgraph>=0.13.3",
        "python-dateutil>=2.8.2",
        "qimage2ndarray>=1.10.0",
        "QtPy>=2.4.0",
        "scipy>=1.11.0",
        "six>=1.16.0",
        "pybind11>=3.0.0",
        "PyWavelets>=1.1.1",
        # PyQt6 is installed via conda (not pip) for best binary compatibility.
        # torch is optional — install separately for GPU port support.
    ],
    package_data={
        'gpi_core': [
            '**/*.pyd',
            '**/*.net',
            '**/*.cpp',
            '**/*.c',
            '**/*.md',
        ],
    },
    # NOTE: C/C++ build deps (zlib, fftw, eigen, gxx_win-64) must be installed
    # via conda before running gpi_init. See environment.yml.
    entry_points={
        'console_scripts': [
            'gpi_win_setup=gpi.win_setup:main',
        ],
    },
    include_package_data=True,
    python_requires=">=3.12",
    scripts=[
        "bin/gpi",
        "bin/gpi_make",
        "bin/gpi_update",
        "bin/gpi_init",
        "bin/gpi.cmd",
        "bin/gpi_make.cmd",
        "bin/gpi_init.cmd",
    ],
)
