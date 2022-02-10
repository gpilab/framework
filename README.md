[![GPI Framework](http://gpilab.com/images/framewrk_b.jpg)](http://gpilab.com)

GPI stands for **G**raphical **P**rogramming **I**nterface which is a development environment for scientific algorithms that provides a visual workspace for assembling algorithms. Algorithm elements (i.e. nodes) can be linked together to form a flow diagram. Each node is executed according to the hierarchy of the diagram.

[![GPI Framework](http://docs.gpilab.com/en/develop/_images/uilabels.jpg)](http://gpilab.com)

- [Website](https://gpilab.com/)

- [Documentation](http://docs.gpilab.com/en/develop/)

- [Issues](https://github.com/gpilab/framework/issues)

## Installing

### PIP

GPI is available on PyPI:

```shell
$ pip install gpilab
```

GPI officially supports Python 3.7 to 3.9.

### Source

```shell
$ git clone https://github.com/gpilab/framework.git gpi
$ cd gpi
$ pip install -r requirements.txt
```

## Running

If you have installed GPI using `pip` you can run it as follows:

```shell
$ gpi
```

If you have install GPI from source you can run it as follows:

```shell
$ ./bin/gpi
```

## Compiling PyFI files

You will need to have `fftw` and `eigen` to compile PyFI, you can get them by running the following command:

```shell
$ conda install fftw eigen
```

First navigate to the directory with your PyFI files.

If you have installed GPI using `pip` you can make PyFI as follows:

```shell
$ gpi_make --all
```

If you have install GPI from source you can run PyFI as follows:

```shell
$ ./bin/gpi_make --all
```