from setuptools import setup
from setuptools import find_packages

setup(
    name='gpi',
    version='1.0.0',
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
        "Pillow==8.4.0",
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
        "six==1.16.0"
    ],
    include_package_data=True,
    python_requires='>=3.7',
)