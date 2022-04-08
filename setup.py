import pathlib
from setuptools import setup
from setuptools import find_packages

# The directory containing this file
HERE = pathlib.Path(__file__).parent

# The text of the README file
README = (HERE / "README.md").read_text()

setup(
    name='gpilab',
    version='1.4.8',
    description="Graphical Programming Interface",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://github.com/gpilab/framework",
    author="AbdulRahman Alfayad",
    author_email="alfayad.abdulrahman@mayo.edu",
    license="GNU",
    packages=find_packages(),
    install_requires=[
        "cycler==0.11.0",
        "dill==0.3.4",
        "fonttools==4.28.5",
        "grpcio==1.43.0",
        "grpcio-tools==1.43.0",
        "h5py==3.6.0",
        "kiwisolver==1.3.2",
        "matplotlib==3.5.1",
        "multiprocess==0.70.12.2",
        "numpy==1.21.5",
        "packaging==21.3",
        "pathos==0.2.8",
        "Pillow==9.0.1",
        "pox==0.3.0",
        "ppft==1.6.6.4",
        "protobuf==3.19.1",
        "psutil==5.8.0",
        "PyOpenGL==3.1.5",
        "pyparsing==3.0.6",
        "PyQt5==5.15.6",
        "PyQt5-Qt5==5.15.2",
        "PyQt5-sip==12.9.0",
        "pyqtgraph==0.12.3",
        "python-dateutil==2.8.2",
        "qimage2ndarray==1.8.3",
        "QtPy==2.0.0",
        "scipy==1.7.3",
        "six==1.16.0",
        "gpi_core"
    ],
    include_package_data=True,
    python_requires='>=3.7',
    scripts=['bin/gpi', 'bin/gpi_make', 'bin/gpi_update', 'bin/gpi_init', 'bin/gpi.cmd', 'bin/gpi_make.cmd']
)