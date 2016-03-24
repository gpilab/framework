##########################
GPI Node Developer's Guide
##########################
.. py:currentmodule:: gpi.nodeAPI

This version of the Node Developer's Guide is a reference for widget and port
attributes that can be set in a GPI node and various methods used to interact
with the GPI infrastructure.

Each new node consists of a Python file containing a main class, which must
implement (through inheritance) the :py:class:`NodeAPI` class. This class
provides the necessary methods for interacting with the GPI framework.
Computation may be performed directly in Python (using e.g. Numpy and SciPy
libraries), or in another language called from Python. The GPI framework
includes :ref:`PyFI <pyfi-devguide>` to help extend nodes with C and C++ code.

For further reference check the :doc:`node_api` documentation page.

“Top Level” Methods
===================
The :py:class:`NodeAPI` class provides three abstract methods, which are
defined by the user and comprise the three major sections of a GPI node.
:py:meth:`.initUI` is required, :py:meth:`.validate` and :py:meth:`compute` are
optional.

:py:meth:`.initUI` (*required*)
This part of the node will run in the constructor at
instantiation (i.e. when the node is placed on the Canvas). It is used to
define widgets and ports, which are displayed in the order they are defined
(widgets top down, ports left to right).

:py:meth:`.validate`
This part of the node will run every time an event is being
processed, always prior to the compute method. It is typically used to
check/enforce compatibility of data and widget values, and set widget
attributes such as min/max and visibility.

:py:meth:`.compute`
This part of the node will run every time an event is being
processed, always after to the validate method. It is where (e.g.) the actual
data computation occurs.

Ports
=====
Input and output ports are used to pass data into and out of nodes,
respectively. They can pass different types of data (e.g. numpy arrays,
dictionaries, etc.) and can limit accepted data types using attributes. Ports
are created :py:meth:`.addInPort` and :py:meth:`addOutPort`. Data are retrieved
from input ports using :py:meth:`.getData` and sent to output ports using
:py:meth:`.setData`.

Port Methods
------------
:py:meth:`.addInPort` is used in the :py:meth:`.initUI` section to create an
input port. It defines the unique port name, the data type, and the desired
options. For example, after importing numpy, one can specify a 4-byte float
numpy array that is either 2 or 3 dimensions using::

    self.addInPort(‘kspacefilter’, ‘NPYArray’, ndim=[2,3], dtype=numpy.float32)

:py:meth:`.addOutPort` is used in the initUI section to create an output port.
It defines the unique port name, the data type, and the desired options. For
example, one can specify an output port that will contain a dictionary using::

    self.addOutPort(‘filteredDataDesc’, ‘DICT’)

For :py:meth:`.addInPort` and :py:meth:`.addOutPort` the 2nd argument is the
type of data associated with the port. The possible types, along with the
attributes that can be associated with them, can be found in
:ref:`port-data-types`.

:py:meth:`.getData` is used in the validate and compute sections to retrieve
the data from an input port. It defines the unique port name, and returns the
data.  For example, one can assign the data from an input port to a variable
``kfilt`` using::

    kfilt = self.getData(‘kspacefilter’)

The method returns ``None`` if no data are present at the port. This can be
used to check if data are present at input ports set to ``gpi.OPTIONAL``.

:py:meth:`.setData` is used in the compute section to assign data to an output
port.  It defines the unique port name, and the data. For example, one can
assign the a dictionary contained in oxfordDict to an output port using::

    self.setData(‘filteredDataDesc’, oxfordDict)

Widgets
=======
The widget methods, types, and attributes described in this section are further
clarified in the example code contained in the core library. This code can be
easily examined by instantiating the ``core→interfaces→Template`` node on the
canvas and using the :ref:`Ctrl/⌘ + Right Click <ui-keyboard>` interaction to
bring up the source code.

Widgets are visual interfaces associated with nodes to enter and retrieve a
wide variety of values, e.g. floats, integers, strings, lists, images. Widgets
have many attributes associated with them, which affect their behavior in a
variety of ways. They are instantiated using :py:meth:`.addWidget` and modified
using :py:meth:`.setAttr`. Their values and attributes are retrieved using
:py:meth:`.getVal` and :py:meth:`.getAttr`. For reference check the
:doc:`node_api` documentation page.

Widget Methods
--------------
:py:meth:`.addWidget` is used in :py:meth:`.initUI` to add a widget to the node
menu, provided a widget type and unique identifier. Additional options can be
passed to the widget during creation as keyword arguments::

    # create a SpinBox (for integers) named 'foo' with default value of 10 and
    # range of [0,100]
    self.addWidget('SpinBox', 'foo', val=10, min=0, max=100)

    # create a set of ExclusivePushButtons named 'qux' with labels 'Antoine',
    # 'Colby', 'Trotter', and 'Adair' (in that order), and a default value
    # of 1 (corresponding to 'Colby')
    button_labels = ['Antoine', 'Colby', 'Trotter', 'Adair']
    self.addWidget('ExclusivePushButtons', 'qux', buttons=button_labels, val=1)

:py:meth:`.getVal` can be used in any of the top level methods to get the value
of a specific widget::

    foo = self.getVal('foo')

:py:meth:`.setAttr` can be used in any of the top level methods to set the
value of a specific widget attribute::

    # hide 'qux' if 'bar' is less than 10
    if bar > 10:
        self.setAttr('qux', visible=True)
    else:
        self.setAttr('qux', visible=False)

:py:meth:`.getAttr` likewise can be used to get the value of an attribute::

    # scale 'foo' by its maximum value
    foo = foo / self.getAttr('foo', 'max')

Additional Utilities
====================

Event Checking Methods
----------------------
These methods allow the node to perform selective computation based on what
activated the node (e.g. a widget event vs. a port event).

:py:meth:`.getEvents` returns a dictionary with four key:value pairs:
    * ``GPI_WIDGET_EVENT`` : `set(widget_titles (string)`)
    * ``GPI_PORT_EVENT`` : `set(port_titles (string)`)
    * ``GPI_INIT_EVENT`` : ``True`` or ``False``
    * ``GPI_REQUEUE_EVENT`` : ``True`` or ``False``

:py:meth:`.widgetEvents` and :py:meth:`.portEvents` return only the
corresponding ``set`` from the events dictionary.

Example from the ``core→FFTW`` node::

    def validate(self):

        ...

        # only change bounds if the 'direction' widget changed.
        if 'direction' in self.widgetEvents():
            direction = self.getVal('direction')
            if direction:
                self.setAttr('direction', button_title="INVERSE")
            else:
                self.setAttr('direction', button_title="FORWARD")

        ...

Logging Methods
---------------
.. currentmodule:: gpi.logger.PrintLogger

The logger can be used to print messages (e.g. status or error messages) in the
terminal/console window. The GPI main menu (`Debug → Log Level`) controls what
level of log is printed. Text can be inserted as desired using the following
functions:

    * :py:meth:`.debug`
    * :py:meth:`.info`
    * :py:meth:`.node`
    * :py:meth:`.warn`
    * :py:meth:`.error`
    * :py:meth:`.critical`

These functions can be accessed within the top level node methods via
``self.log`` e.g.::

    if np.iscomplex(A):
        self.log.node("A is complex, so we'll take the magnitude...")
        A = np.abs(A)

Timing Methods
--------------
Frame code with :py:meth:`.starttime` and :py:meth:`.endtime` to measure wall
time of computation. Optional text can be passed as an argument to
:py:meth:`.endtime`, which will be written in the log.

Profiling
---------
GPI provides a simple profiler in `gpi.node_profiler`. This provides a
`decorator` :py:func:`.profiler`, which can be used to profile any function
defined in an external node. Typically this is applied to the
:py:meth:`.compute` top-level method. To use it, import the profiler and
decorate the method you want to profile::

    from gpi.node_profiler import profiler

    class ExternalNode(gpi.NodeAPI):
        """node profiler example"""

        def initUI(self):
            ...

        @profiler
        def compute(self):
            ...

Example output::

   263 function calls in 0.002 seconds

   Ordered by: internal time

   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
       10    0.001    0.000    0.001    0.000 {built-in method posix.read}
        2    0.000    0.000    0.000    0.000 {method 'dump' of '_pickle.Pickler' objects}
        1    0.000    0.000    0.002    0.002 somenewnode_GPI.py:60(compute)
        1    0.000    0.000    0.000    0.000 {method 'random_sample' of 'mtrand.RandomState' objects}
        1    0.000    0.000    0.002    0.002 nodeAPI.py:844(setData)
        1    0.000    0.000    0.000    0.000 nodeAPI.py:893(getData)
        1    0.000    0.000    0.001    0.001 managers.py:695(_connect)
        5    0.000    0.000    0.001    0.000 connection.py:406(_recv_bytes)
        1    0.000    0.000    0.000    0.000 nodeAPI.py:1088(getVal)
       10    0.000    0.000    0.001    0.000 connection.py:374(_recv)
        1    0.000    0.000    0.002    0.002 managers.py:704(_callmethod)

    ...

.. _pyfi-devguide:

PyFI: Extending GPI Nodes with C++
==================================
PyFI is a collection of macros and interface classes that simplify exposing C++
functions to the Python interpreter. The macros also reduce the amount of code
needed to translate Numpy arrays in Python to the PyFI Array class in C++ (and
vice versa).

PyFI can be used both to extend and embed Python. Most of the time PyFI is used
to speed up algorithms by moving them from Python to C/C++, extending Python.
However, the vast Python library can still be leveraged from within C++ code by
embedding Python, allowing the developer to make the occasional Python function
call from C++ when something can be more easily accomplished through Python.
The PyFI interface is separate from GPI and can be used to extend or embed
Python in other C++ applications.

PyFI is located in the `core` GPI library and can be included in a cpp file
with::

    #include “core/PyFI/PyFI.h”

The macros described in this section are demonstrated in the example code::

    <gpi_directory>/core/PyFI/template_PyMOD.cpp

PyFunction Macros
-----------------
These macros are intended to simplify the boilerplate code required to
successfully compile a Python/C++ extension module. The Python documentation
contains much more information on `Extending Python with C or C++
<http://docs.python.org/3.5/extending/extending.html>`_.

PyFunction Declaration
^^^^^^^^^^^^^^^^^^^^^^
:c:macro:`PYFI_FUNC(name)`, :c:macro:`PYFI_START()`, :c:macro:`PYFI_END()`.
These macros are used to declare the function that will be available to the
Python interpreter.  :c:macro:`PYFI_FUNC` takes a function name as its
argument. This is the name used in the :c:macro:`PYFI_FUNCDESC` and will be the
name of the function available in Python.  The :c:macro:`PYFI_START` and
:c:macro:`PYFI_END` handle the Python input and output of the function (e.g.
memory management and exception handling). ::

    PYFI_FUNC(myFunc)
    {
        PYFI_START();

        /* your code goes here */

        PYFI_END();
    }

Input/Output Macros
-------------------
:c:macro:`PYFI_POSARG(type, ptr)`
This macro declares a pointer of the given type and converts the input args
from the Python interface to the corresponding C++ variables. Valid types are
``double``, ``int64_t`` (``long`` depending on the OS), ``std::string``,
``Array<float>``, ``Array<double>``, ``Array<int32_t>``, ``Array<int64_t>``,
``Array<complex<float> >``, ``Array<complex<double> >``. ::

    PYFI_POSARG(double, myInput1);

:c:macro:`PYFI_KWARG(type, ptr, default)`
This macro declares a pointer of the given type and converts a `keyword arg
<http://docs.python.org/2/tutorial/controlflow.html#keyword-arguments>`_ to the
pointed C++ variable, if it was passed. If the keyword arg is not used, then
the default arg is set. ::

    double myDefault1 = 1.0;
    PYFI_KWARG(double, myInput1, myDefault1);

:c:macro:`PYFI_ERROR(string)`
This macro raises a Python Runtime exception and passes the error message
contained in the string.

:c:macro:`PYFI_SETOUTPUT(ptr)`
The output arguments are set using this macro. If more than one output exists,
then all are packaged in a tuple. This macro will create and copy PyFI arrays
(passed as ptr) to Python Numpy arrays in the Python session.

:c:macro:`PYFI_SETOUTPUT_ALLOC(type, ptr, dims)` If the output array size is
known, before the algorithm code, this macro can be used to generate an output
Numpy array that is accessible within the C++ code as a PyFI array. This is
more time and memory efficient than using :c:macro:`PYFI_SETOUTPUT` with PyFI
arrays. This macro only applies to PyFI arrays.  ‘dims’ can be a
``std::vector<uint64_t>`` or a ``PyFI::ArrayDimensions`` object.

PyFunction List
^^^^^^^^^^^^^^^
:c:macro:`PYFI_LIST_START_`, :c:macro:`PYFI_LIST_END_`,
:c:macro:`PYFI_DESC(name, string)`. These macros define the list of functions
available within the compiled module.  The list is made up of
:c:macro:`PYFI_DESC()` calls placed between the :c:macro:`PYFI_LIST_START_` and
:c:macro:`PYFI_LIST_END_` macros. This group must be the last set of macro
calls in the module file. ::

    PYFI_LIST_START_
        PYFI_DESC(myFunc, “Brief info about myFunc().”)
    PYFI_LIST_END_

Additional Convenience Macros
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
:c:macro:`deb`
This macro can be placed in the code to print out the line number and file name
of the executed code.

:c:macro:`coutv(var)`
This macro prints the name and contents of the variable ‘var’ passed to it.

PyFI Arrays
-----------
.. cpp:namespace:: PyFI

PyFI contains a simple array class that supports multi-dimensional indexing,
overloaded operators (for simple math operations), a few common function
interfaces (e.g. pseudo inverse and fft), index debugging and wrapping Numpy
array objects.

The arrays support up to 10 dimensions. N-dimensional arrays support indexing
as an ND array or as a 1D array. The arrays are initialized by default to a
value of zero. The :cpp:class:`Array` class is a templated class that allows
any type to be a basis element of the array. However, the types supported for
export (by PyFI) between Python and C++ are listed in the
:c:macro:`PYFI_POSARG()` macro above.

Array Methods
-------------
Constructors
^^^^^^^^^^^^
.. cpp:function:: Array(const std::vector<uint64_t> &dims)

Construct an array using a standard vector class containing the dimension
sizes. This is the recommended way for dynamic dimensionality. Array values are
initialized to zero.

.. cpp:function:: Array(uint64_t ndim, uint64_t *dimensions)

Construct an array using a standard C-array containing the desired dimensions.
Array values are initialized to zero.

.. cpp:function:: Array(uint64_t i, uint64_t j, ...)

Construct a new Array (initialized to zero) by specifying the shape (column
major ordering)::

    Array<float> myArray(10);       // a 1D array of length 10
    Array<float> myArray3(10,10,2); // a 3D array with the fastest
                                    // varying dimension of length 2.

.. cpp:function:: Array(uint64_t ndim, uint64_t *dimensions, T *seg_ptr)

Construct a :cpp:class:`PyFI::Array` given an existing memory segment
containing the data.

Array Information
^^^^^^^^^^^^^^^^^
.. cpp:function:: uint64_t PyFI::Array::ndim()

The number of dimensions as a ``uint64_t`` type.

.. cpp:function:: std::vector<uint64_t> PyFI::Array::dimensions_vector()

Returns a standard vector with the dimension sizes.

.. cpp:function:: uint64_t PyFI::Array::size()

The total number of elements as a ``uint64_t`` type.

.. cpp:function:: T* PyFI::Array::data()

Returns a pointer to the contiguous data segment.

.. cpp:function:: bool PyFI::Array::isWrapper()

Returns a bool indicating whether the array wraps an external data segment
(usually a Numpy data segment).

Operators
^^^^^^^^^
``Array(uint64_t i, uint64_t j, ...)``
The indexing operator calculates multi-dimensional indices given the input
integer arguments and returns the dereferenced pointer to the location in the
data segment. This is the usual way for accessing array memory. All
N-dimensional arrays can also be accessed as 1D arrays.

``=, *=, /=, +=, -=``
The right-hand-side arguments can be a single element of the same type as the
array or another Array of the same type. Arrays must be the same ``size()``.
Operations are on an element-wise basis (not matrix math).

``+, *, -, /``
Math operators that work on both arrays and single elements. All operations are
on an element-wise basis (not matrix math).

``==, !=, <=, >=, <, >``
Inequalities return an Array<bool> object containing a bit-mask evaluated with
the condition for each element. Works with Arrays or single elements (for quick
thresholding).

Builtins
^^^^^^^^
The :cpp:class:`Array` class also contains many builtin methods for basic
arithmetic, statistical, masking, recasting, and reshaping operations. See the
class documentation for more information.

PyFI Array Wrappers
-------------------
For convenience, PyFI Array wrappers to FFTW and Eigen libraries are included
in the :ref:`pyfi-fftw` and :ref:`pyfi-eigen`. There is also a wrapper to some
basic Numpy functions (``pinv`` and ``fft``) in the :ref:`pyfi-numpy` using
:ref:`pyfi-pycallable`. The implementation details can be found in::

    <gpi_directory>/include/PyFI/PyFIArray_WrappedFFTW.cpp
    <gpi_directory>/include/PyFI/PyFIArray_WrappedEigen.cpp
    <gpi_directory>/include/PyFI/PyFIArray_WrappedNUMPY.cpp

Build Setup & Example
---------------------
A PyFI Python extension module can be easily built using the ``gpi_make``
command from a terminal shell. PyFI extensions are compiled into a library
object file (.so for unix based platforms) via :py:mod:`distutils` which is
part of the Python standard library. PyFI modules should be placed in the GPI
node library directory structure under the library specific to the modules
function.  For example a `core` library module, used by the GPI node
`SpiralCoords` would be located in the `spiral` sub-library::

    core/__init__.py                    # python pkg file
    core/spiral                         # sub-library
    core/spiral/__init__.py             # python pkg file
    core/spiral/spiral_PyMOD.cpp        # C++ extension module
    core/spiral/spiral.so               # compiled extension module
    core/spiral/GPI/SpiralCoords_GPI.py # GPI node

The ``gpi_make`` script identifies extension modules by checking for the
`_PyMOD.cpp` extension; other supporting .cpp files will be ignored as make
targets.

A simple Python extension module ‘mymath’ might look like this::

    Example. bni/math/mymath_PyMOD.cpp

    #include “core/PyFI/PyFI.h”
    using namespace PyFI;

    PYFI_FUNC(add_one)
    {
        PYFI_START();
        PYFI_POSARG(Array<float>, arr);

        Array<float> out_arr(*arr);
        out_arr += 1.0;


        PYFI_SETOUTPUT(&out_arr);
        PYFI_END();
    }

    PYFI_LIST_START_
        PYFI_DESC(add_one, “Adds one to each element in the array.”)
    PYFI_LIST_END_

The mymath_PyMOD.cpp module is compiled by invoking the ``gpi_make`` from a
terminal shell::

    $ gpi_make mymath

or::

    $ gpi_make mymath_PyMOD.cpp

A debug flag can be set to compile the PyFI arrays in a debug mode, where all
indexing will be checked against the array dimensions. This also adds some
debug printing to stdout::

    $ gpi_make --debug mymath

The ``gpi_make`` is configurable through the `~/.gpirc` file (see
:doc:`../config`).  Under the ``[PATH]`` section there is a variable ``LIB_DIRS``
that can be configured to point to new GPI libraries. All libraries pointed to
by ``LIB_DIRS`` will be included as searchable code and library paths in the
``gpi_make``. NOTE: it is recommended that node developers create their own
library for development and leave the ‘core’ library clean.  This way new GPI
releases won’t overwrite a developer’s development directory.

Example python code (`test.py` placed in the same directory as `bni`)::

    import bni.math.mymath as bnimath
    import numpy as np

    x = np.array([1,2,3,4], dtype=np.float32)
    y = bnimath.add_one(x)

    print(‘x: ‘, x)
    print(‘y: ‘, y)

Output of ``python test.py``::

    x: [1. 2. 3. 4.]
    y: [2. 3. 4. 5.]

Embedding Python (PyCallable)
-----------------------------
PyFI also includes a class called :ref:`PyCallable <pyfi-pycallable>` that
simplifies the process of embedding Python in C++ code. For the purposes of
GPI, this allows the PyMOD developer to use Python libraries for functionality
that is not yet available as a C++ solution (whether its not available as a
library or it is not interfaced with PyFI arrays).

PyFI arrays that are sent to Python via PyCallable are wrapped by Numpy arrays
so that the data are accessed directly by the interpreter. The PyCallable
interface is threadsafe, however, it will block when executing internal Python
calls. The PyCallable class is available in the PyFI namespace. The PyCallable
object can be constructed in two ways:

Module & Function Examples
^^^^^^^^^^^^^^^^^^^^^^^^^^
Use the numpy ``isnan()`` function::

    PyCallable(“numpy”, “isnan”);

Use a python script that is loadable from the python path::

    PyCallable(“myScript”, “myFunc”);

Python code from ``std::string``::

    std::string myCode = “def func(x, y):\n\tprint(x, y)\n”;
    PyCallable(code);

In the second case, the function defined in the inline code must define a
function called ``func``. This is what PyCallable looks for in the imported
python code. ``func`` may pass and return any number of arguments.

Other simple examples can be found in ``template_PyMOD.cpp``.

The PyCallable operation is similar to the PyFunction interface in that
function arguments are parsed in the order in which they are given, in python
its left to right, in PyFI its top to bottom. Regardless of how it is
constructed, arguments are passed and returned to and from the Python function
by the method functions.

.. cpp:function:: PyCallable::SetArg_Array(ptr)

``ptr`` is a pointer to a ``PyFI::Array<T>`` object.

.. cpp:function:: PyCallable::SetArg_String(string)

Takes a ``std::string``.

.. cpp:function:: PyCallable::SetArg_Long(long)

Takes a long integer (i.e. int64_t)

.. cpp:function:: PyCallable::SetArg_Double(double)

Takes a double precision float.

The return functions are:

.. cpp:function:: PyCallable::GetReturn_Array(ptr_ptr)

``ptr_ptr`` is a reference to a pointer to a ``PyFI::Array<T>`` object. This
modifies the input pointer given. This is a templated function.

.. cpp:function:: PyCallable::GetReturn_String()

Returns a ``std::string``.

.. cpp:function:: PyCallable::GetReturn_Long()

Returns a ``long`` (``int64_t``).

.. cpp:function:: PyCallable::GetReturn_Double()

Returns a ``double``.

Once all the arguments are set, the ``Run()`` method can be called. If any of
the ``GetReturn_`` functions are called, then ``Run()`` is automatically
invoked for the first ``GetReturn_``.

`NOTE:` ``PyCallable()`` currently doesn’t handle exceptions. This means the
executed code cannot contain try-except clauses.

