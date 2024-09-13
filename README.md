[![GPI Framework](http://gpilab.com/images/framewrk_b.jpg)](http://gpilab.com)

GPI stands for **G**raphical **P**rogramming **I**nterface which is a development environment for scientific algorithms that provides a visual workspace for assembling algorithms. Algorithm elements (i.e. nodes) can be linked together to form a flow diagram. Each node is executed according to the hierarchy of the diagram.

[![GPI Framework](http://docs.gpilab.com/en/develop/_images/uilabels.jpg)](http://gpilab.com)

- [Website](https://gpilab.com/)

- [Documentation](http://docs.gpilab.com/en/develop/)

- [Issues](https://github.com/gpilab/framework/issues)

## Installing

Create a new conda environement for gpi
```shell
$ conda create -n gpi python=3.9 fftw eigen qt
$ conda activate gpi
```

install gpi from source (eventaully we may update PyPy, then this step won't be necessary)
```shell
$ git clone https://github.com/gpilab/framework.git gpi_source
$ cd gpi_source
$ pip install .
```

The core_nodes can be built using the newly installed command
```shell
$ gpi_init
```


You can now run `gpi` from your conda environment.
```shell
$ gpi
```


To build a node with C dependencies:
```shell
$ cd /path/to/node
$ gpi_make --all
```
