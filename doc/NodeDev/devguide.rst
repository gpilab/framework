##########################
GPI Node Developer's Guide
##########################
.. py:currentmodule:: gpi.nodeAPI

This initial version of the Node Developer's Guide is a reference for widget
and port attributes that can be set in a GPI node and various methods used to
interact with the GPI infrastructure.

Each new node must implement (through inheritance) the :py:class:`NodeAPI`
class. This class provides the necessary methods for interacting with the GPI
framework.

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

    self.addInPort(‘kspacefilter’,‘NPYArray’,ndim=[2,3], dtype=numpy.float32)

:py:meth:`.addOutPort` is used in the initUI section to create an output port.
It defines the unique port name, the data type, and the desired options. For
example, one can specify an output port that will contain a dictionary using::

    self.addOutPort(‘filteredDataDesc’,‘DICT’)

:py:meth:`.getData` is used in the validate and compute sections to retrieve the
data from an input port. It defines the unique port name, and returns the data.
For example, one can assign the data from an input port to a variable kfilt
using::

    kfilt = self.getData(‘kspacefilter’)

The method returns ``None`` if no data are present at the port. This can be
used to check if data are present at input ports set to ``gpi.optional``.

:py:meth:`.setData` is used in the compute section to assign data to an output
port.  It defines the unique port name, and the data. For example, one can
assign the a dictionary contained in oxfordDict to an output port using::

    self.setData(‘filteredDataDesc’, oxfordDict)

Port Data Types & Attributes
----------------------------
For :py:meth:`.addInPort` and :py:meth:`.addOutPort` the 2nd argument is the
type of data associated with the port. The possible types are listed below,
along with the attributes that can be associated with them.

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
menu, provided a widget type and unique identifier. Additional options

:py:meth:`.getVal`

:py:meth:`.setAttr`

:py:meth:`.getAttr`

Additional Utilities
====================
Timing Methods
--------------
Frame code with starttime() and endtime() to measure wall time of computation.  Optional text can be inserted.

.  self.starttime(. # time your code, NODE level log

.  ...

.  self.endtime('You can put text here if you want'. # endtime w/ message

Logging Methods
---------------
Print messages (e.g. error messages) in the terminal/console window. GPI main menu (Debug -> Log Level) controls what level of log is printed. Text can be inserted as desired.

.  self.log.debug()
.  self.log.info()
.  self.log.node("hello from node level logger, running validation()")
.  self.log.warn("this is a bad code area")
.  self.log.error()
.  self.log.critical()

Event Checking Methods
----------------------
These methods allow the node to perform selective computation based on what activated the node (e.g. a widget event vs. a port event)::
.  ``self.portEvents()``
.  Returns the name of a port that received new data, or Null if no port has received new data since the last node execution.

.  ``self.widgetEvents()``
.  Returns the name of a port that was activated, or Null if no port has received new data since the last node execution.

.  ``self.getEvents() # super set of events``
.  Returns either the name of the last port to receive data or the last widget to have been changed (whichever occurred last)


Note on current behavior: Only the latest event for a node is kept. This means that if the following occurs for a given node (in the specified temporal order):

1. a user changes a widget
2. new data comes to an input port
3. The node executes

At this point,

1. the value of the widget is changed
2. the new data is at the input port
3. self.widgetEvent() is Null
4. self.portEvent() returns the port that received data.

This is because the data came after the widget was set. A future version of GPI will keep a list of all pending events since the last execution.

Profiling
---------

Extending with PyFI (C++)
=========================

PyFI, or “Python Function Interface”, is a collection of macros and interface classes that simplify exposing C++ functions to the Python interpreter. The macros also reduce the amount of code needed to translate Numpy arrays in Python to the PyFI Array class in C++ (and vice versa).

PyFI can be used to extend or embed Python. Most of the time PyFI is used to speed up algorithms by moving them from Python to C/C++, extending Python. However, the vast Python library can still be leveraged from within C++ code by embedding Python, allowing the developer to make the occasional Python function call from C++ when something can be more easily accomplished through Python. The PyFI interface is separate from GPI and can be used to extend or embed Python in other C++ applications.

PyFI is located in the ‘core’ GPI library and can be included in a cpp file via:

.  #include “core/PyFI/PyFI.h”

The macros described in this section are demonstrated in the example code:

.  /opt/gpi/lib/core/PyFI/template_PyMOD.cpp

PyFunction Macros
-----------------

These macros are required to successfully compile a Python/C++ extension module (http://docs.python.org/2/extending/extending.html).

1. ``PYFI_FUNC(name)``, ``PYFI_START()``, ``PYFI_END()``. These macros are used to declare the function that will be available to the Python interpreter. ``PYFI_FUNC`` takes a function name as its argument. This is the name used in the ``PYFI_FUNCDESC`` and will be the name of the function available in Python. The ``PYFI_START`` and ``PYFI_END`` handle the Python input and output of the function (e.g. memory management and exception handling).

. .   Ex::
. . . . PYFI_FUNC(myFunc)
. . . . {
. . . . .  PYFI_START();

. . . . .  /* your code goes here */

. . . . .  PYFI_END();
. . . . }

2. ``PYFI_LIST_START_``, ``PYFI_LIST_END_``, ``PYFI_DESC(name, string)``. These macros define the list of functions available within the compiled module. The list is made up of ``PYFI_DESC()`` calls placed between the ``PYFI_LIST_START_`` and ``PYFI_LIST_END_`` macros. This group must be the last set of macro calls in the module file.

. .   Ex::
. . . . PYFI_LIST_START_
. . . . .  PYFI_DESC(myFunc, “Brief info about myFunc().”)
. . . . PYFI_LIST_END_



Input/Output Macros
-------------------

``PYFI_POSARG(type, ptr)``
This macro declares a pointer of the given type and converts the input args from the Python interface to the corresponding C++ variables. Valid types are double, int64_t (long depending on the OS), ``std::string``, ``Array<float>``, ``Array<double>``, ``Array<int32_t>``, ``Array<int64_t>``, ``Array<complex<float> >``, ``Array<complex<double> >``.

.  Ex:
. .   PYFI_POSARG(double, myInput1);

``PYFI_KWARG(type, ptr, default)``
This macro declares a pointer of the given type and converts the input keyword argument (http://docs.python.org/2/tutorial/controlflow.html#keyword-arguments) to the pointed C++ variable, if it was passed. If the keyword arg is not used, then the default arg is set.

.  Ex:
. .   double myDefault1 = 1.0;
. .   PYFI_KWARG(double, myInput1, myDefault1);

``PYFI_ERROR(string)``
This macro raises a Python Runtime exception and passes the error message contained in the string.

``PYFI_SETOUTPUT(ptr)``
The output arguments are set using this macro. If more than one output exists, then all are packaged in a tuple. This macro will create and copy PyFI arrays (passed as ptr) to Python Numpy arrays in the Python session.

``PYFI_SETOUTPUT_ALLOC(type, ptr, dims)``
If the output array size is known, before the algorithm code, this macro can be used to generate an output Numpy array that is accessible within the C++ code as a PyFI array. This is more time and memory efficient than using ``PYFI_SETOUTPUT`` with PyFI arrays. This macro only applies to PyFI arrays. ‘dims’ can be a ``std::vector<uint64_t>`` or a ``PyFI::ArrayDimensions`` object.

``deb``
This macro can be placed in the code to print out the line number and file name of the executed code.

``coutv(var)``
This macro prints the name and contents of the variable ‘var’ passed to it.

## PyFI Arrays

PyFI contains a simple array class that supports multi-dimensional indexing, overloaded operators (for simple math operations), a few common function interfaces (e.g. pseudo inverse and fft), index debugging and wrapping Numpy array objects.

The arrays support up to 10 dimensions. N-dimensional arrays support indexing as an ND array or as a 1D array. The arrays are initialized by default to a value of zero. The ‘Array’ class is a templated class that allows any type to be a basis element of the array. However, the types supported for export (by PyFI) between Python and C++ are listed in the ``PYFI_POSARG()`` macro above.

An array wrapper to FFTW library is included in the PyFI::FFTW namespace. The implementation details can be found in:

.  core/PyFI/PyFIArray_WrappedFFTW.cpp


Array Methods
-------------

Constructors
^^^^^^^^^^^^
``Array(std::vector<uint64_t> dims)``
Construct an array using a standard vector class containing the dimension sizes. This is the recommended way for dynamic dimensionality.

``Array(uint64_t i, uint64_t j, ....)``
Construct arrays with integer arguments for the size of each dimension. The number of arguments determines the dimensionality.

Array Information
^^^^^^^^^^^^^^^^^
``ndim()``
The number of dimensions as a uint64_t type.

``dimensions_vector()``
Returns a standard vector with the dimension sizes.

``size()``
The total number of elements as a uint64_t type.

``data()``
Returns a pointer to the contiguous data segment.

``isWrapper()``
Returns a bool indicating whether the array wraps an external data segment (usually a Numpy data segment).

Operators
^^^^^^^^^
``Array(uint64_t i, uint64_t j, ...)``
The indexing operator calculates multi-dimensional indices given the input integer arguments and returns the dereferenced pointer to the location in the data segment. This is the usual way for accessing array memory. All N-D arrays can also be accessed as 1-D arrays.

``=, *=, /=, +=, -=``
The right-hand-side arguments can be a single element of the same type as the array or an array of the same type. Arrays must be the same ‘size()’. Operations are on an element-wise basis (not matrix math).

``+, *, -, /``
Math operators that work on both arrays and single elements. All operations are on an element-wise basis (not matrix math).

``==, !=, <=, >=, <, >``
Inequalities return an Array<bool> object containing a bit-mask evaluated with the condition for each element. Works with Arrays or single elements (for quick thresholding).

Builtins
""""""""
``sum()``
The sum of all elements returned as a datum of the base array type.

``prod()``
The product of all elements returned as a datum of the base array type.

``min(), max()``
The min or max of all elements returned as a datum of the base array type.

``abs()``
Calculates the fabs() on an element-wise basis (operates on the array in-place)

``any(T val)``
.  Returns true if any of the elements are equal to val.

``any_infs(), any_nans()``
Checks for infs or nans respectively. Returns a bool.

``clamp_max(T thresh), clamp_min(T thresh)``
Sets arrays > or < thresh equal to thresh. Operates in-place.

``mean(), stddev()``
Calculates sample mean and standard-deviation of the array elements. Returns as a datum of the base array type.

``as_ULONG(), as_FLOAT(), as_CFLOAT(), as_DOUBLE(), as_CDOUBLE(), as_LONG(), as_INT(), as_UCHAR()``
Returns a copy of the array as the selected base type.

``insert(Array<T> arr)``
Insert the elements (centered in each dimension) of ‘arr’ into THIS array. If ‘arr’ is larger then the extra elements are cropped.

``get_resized(std::vector<uint64_t>), get_resized(uint64_t), get_resized(std::vector<double>), get_resized(double)``
Return a copy of THIS array inserted into a new array of a different size. Integer arguments indicate specific dimension sizes (isotropic for single value) and double arguments indicate a scale size of the original array dimensions.

``reshape(std::vector<uint64_t)``
Change the dimensionality of THIS array. The total size must not change.


Build Setup & Example
---------------------
A PyFI Python extension module can be easily built using the ‘gpi_make’ command from a terminal shell. PyFI extensions are compiled into a library object file (.so for unix based platforms) via the ‘distutils’ module which part of the Python standard module library. PyFI modules should be placed in the GPI node library directory structure under the library specific to the modules function. For example a ‘core’ library module, used by the GPI node ‘SpiralCoords’ would be located in the ‘spiral’ sub-library:

.  core/__init__.p. . . . .   # python pkg file
.  core/spira. . . . . . . # sub-library
.  core/spiral/__init__.p. . . .  # python pkg file
.  core/spiral/spiral_PyMOD.cp. . . # C++ extension module
.  core/spiral/spiral.s. . . . .   # compiled extension module
.  core/spiral/GPI/SpiralCoords_GPI.p.   # GPI node

The gpi_make script identifies extension modules by checking for the ‘_PyMOD.cpp’ extension; other supporting .cpp files will be ignored as make targets.

A simple Python extension module ‘mymath’ might look like this::

. .   Example. bni/math/mymath_PyMOD.cpp

. .   #include “core/PyFI/PyFI.h”
. .   using namespace PyFI;

. .   PYFI_FUNC(add_one)
. .   {
. . . . PYFI_START();
. . . . PYFI_POSARG(Array<float>, arr);

. . . . Array<float> out_arr(*arr);
. . . . out_arr += 1.0;


. . . . PYFI_SETOUTPUT(&out_arr);
. . . . PYFI_END();
. .   }

. . . . PYFI_LIST_START_
. . . . .  PYFI_DESC(add_one, “Adds one to each element in the array.”)
. . . . PYFI_LIST_END_

The mymath_PyMOD.cpp module is compiled by invoking the gpi_make from a terminal shell::

.  $ gpi_make mymath

or::

.  $ gpi_make mymath_PyMOD.cpp

A debug flag can be set to compile the PyFI arrays in a debug mode, where all indexing will be checked against the array dimensions::

.  $ gpi_make --debug mymath

The gpi_make is configurable through the ~/.gpirc file (which can be generated from the GPI ‘Config’ menu). Under the ``[PATH]`` section there is a variable ``LIB_DIRS`` that can be configured to point to new GPI libraries. All libraries pointed to by ``LIB_DIRS`` will be included as searchable code and library paths in the gpi_make. NOTE: it is recommended that node developers create their own library for development and leave the ‘core’ library clean. This way new GPI releases won’t overwrite a developer’s development directory.

The Python code that uses this function would then look like this::

.  Example. test.py (placed in the same directory as ‘bni’)

. .   import bni.math.mymath as bm
. .   import numpy as np

. .   x = np.array([1,2,3,4], dtype=np.float32)
. .   y = bm.add_one(x)

. .   print ‘x: ‘, x
. .   print ‘y: ‘, y

.  Output. (run ‘python test.py’)

. .   x: [1. 2. 3. 4.]
. .   y: [2. 3. 4. 5.]

This example can be found in the PyFI library directory within the core library::

.  core/PyFI

Embedding Python (PyCallable)
-----------------------------

PyFI also includes a class called ‘PyCallable’ that simplifies the process of embedding Python. For the purposes of GPI, this allows the PyMOD developer to use Python libraries for functionality that is not yet available as a C++ solution (whether its not available as a library or it is not interfaced with PyFI arrays).

PyFI arrays that are sent to Python via PyCallable are wrapped by Numpy arrays so that the data are accessed directly by the interpreter. The PyCallable interface is threadsafe, however, it will block when executing internal Python calls. The PyCallable class is available in the PyFI namespace. The PyCallable object can be constructed in two ways:

### Module & Function

.  /* use the numpy isnan() function */
.  PyCallable(“numpy”, “isnan”);

or

.  /* use a python script that is loadable from the python path */
.  PyCallable(“myScript”, “myFunc”);

Python code from std::string:

.  std::string myCode = “def func(x, y):\n”
. . . . . .   .   print x, y\n”;
.  PyCallable(code);

In the second case, the function defined in the inline code must define a function called ‘func’. This is what PyCallable looks for in the imported python code. ‘func’ may pass and return any number of arguments.

The PyCallable interface is used to wrap the Numpy implementation of the pseudo inverse ‘pinv()’ and the fft interface for 1D ffts. These examples can be found in:

.  /opt/gpi/lib/core/PyFI/PyFIArray_WrappedNUMPY.cpp

Other simple examples can be found in the template_PyMOD.cpp.

The PyCallable operation is similar to the PyFunction interface in that function arguments are parsed in the order in which they are given, in python its left to right, in PyFI its top to bottom. Regardless of how it is constructed, arguments are passed and returned to and from the Python function by the method functions. The passing functions are:

``PyCallable::SetArg_Array(ptr)``
‘ptr’ is a pointer to a PyFI::Array<T> object.

``PyCallable::SetArg_String(string)``
Takes a std::string.

``PyCallable::SetArg_Long(long)``
Takes a long integer (i.e. int64_t)

``PyCallable::SetArg_Double(double)``
Takes a double precision float.

The return functions are:

``PyCallable::GetReturn_Array(ptr_ptr)``
‘ptr_ptr’ is a reference to a pointer to a PyFI::Array<T> object. This modifies the input pointer given. This is a templated function.

``PyCallable::GetReturn_String()``
Returns a std::string.

``PyCallable::GetReturn_Long()``
Returns a long (int64_t).

``PyCallable::GetReturn_Double()``
Returns a double.

Once all the arguments are set, the Run() method can be called. If any of the GetReturn_ functions are called, then Run() is automatically invoked for the first GetReturn_.

NOTE. PyCallable() currently doesn’t handle exceptions. This means the executed code cannot contain try-except clauses.

