import pathlib
from setuptools import setup
from setuptools import find_packages

# The directory containing this file
HERE = pathlib.Path(__file__).parent

# The text of the README file
README = (HERE / "README.md").read_text()

setup(
    name="gpilab",
    version="1.4.10",
    description="Graphical Programming Interface",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://github.com/gpilab/framework",
    author="AbdulRahman Alfayad",
    author_email="alfayad.abdulrahman@mayo.edu",
    license="GNU",
    packages=find_packages(),
    install_requires=[
        "setuptools<82", # < needed because v82 removed pkg_resources
        "cycler",
        "dill",
        "fonttools",
        "grpcio",
        "grpcio-tools",
        "h5py",
        "kiwisolver",
        "matplotlib",
        "multiprocess",
        "numpy==1.26.4",
        "packaging",
        "pathos",
        "Pillow",
        "pox",
        "ppft",
        "protobuf<3.20", # < needed because later versions error...
        "psutil",
        "PyOpenGL",
        "pyparsing",
        "PyQt5",
        "PyQt5-Qt5",
        "PyQt5-sip",
        "pyqtgraph",
        "python-dateutil",
        "qimage2ndarray",
        "QtPy",
        "scipy",
        "six",
        "pybind11",
        "PyWavelets",
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
    # NOTE: C/C++ build deps (zlib, fftw, eigen, pthreads-win32) must be installed
    # via conda before running gpi_init. See environment.yml.
    entry_points={
        'console_scripts': [
            'gpi_win_setup=gpi.win_setup:main',
        ],
    },
    include_package_data=True,
    python_requires=">=3.7",
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
