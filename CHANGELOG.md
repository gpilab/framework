# TBD Version 1.0

### New Features
* moved to Python 3
* Added JSON network file I/O (net version-3)
* Added updater option to main menu.

### Bugfixes
* Fixed pause from canvas init and canvas locking due to initErrorState.

# TBD Version 0.6

###	New Features
* Conda packaging
* Macro Node closing bug is fixed.
* Create new 'File' menu. Move 'New Tab' and 'Create New Node' into 'File'.
* Add menu item to create new node. Add list window to show libraries.
* Added the BORG binary encapsulation module.
* Added Eigen array library wrappers to PyFI
* mmap node communication
* Added a new detail label for programmatically providing user feedback
    for things like file paths, node operations, or important parameter values

### Bugfixes & Updates
* Updated canvas appearance
* Add a dummy splash screen to get the menu bar to show up.
* Set minimum width for push buttons to prevent losing style on OS X.
* Change the 'about' box to a button which pops up a window instead.
* Added user option to choose starting directory and save filename in save-dialog.
* Stop canvas repositioning when nodes are reloaded.
* Fixed immediate scaling when using spinbox.
* Added 'copy to clipboard' and 'save image' feature to displaybox widgets.
* Turn off keyboard tracking for certain widgets.
* Fixed bug where deleting a node while processing will freeze the canvas.
* Fixed concurrent executions after pause-unpause.
* Create a decorator to profile code and print results to the console.
* Added error msg to ExclusivePushButton set_val method.
* Fixed port hover on edge deletion.
* Fixed floating edge on hovered inport.
* Changed SaveFileBrowser widget not to clear filename when cancelled.
* Fixed file browser widget to mute event trigger on 'Cancel'
* Add placeholder text option for StringBox.
* Fixed spurious SpinBox value change after loosing focus. 

# 2015-02-16 Version 0.5

* First public release
* Moved to Anaconda 2.1
* Moved to Astyle 2.4
* Added support for OSX 10.7
* Splash Screen
 * disable w/ commandline option
* Added 'qimage2ndarray' pip package
* Improved HDF5 Reader
 * provide menu to choose dataset name
* Matlab file Reader (old and new style)
* gpi_make
 * Does force recompile on all .py files
 * Removed R2 stuff
* Moved PyFI from 'core' to the 'framework'
* Added left mouse button for port edge connect
* Node-reload (Ctrl-R)
* Menu options for auto-generating user lib and default node (basic)
 * Reloads mouse menu to include new node if gpirc doesn't exist
* Right click port edge-delete
* Updated math node to default to add 0
* Default LIB_DIRS /opt/gpi/node ~/gpi
 * LIB_DIRS is now searched from parent directory
* Split node libraries and framework into separate projects
* BUGFIXES
 * Fixed file association bug for capitalized extensions.
 * Fixed node updating by forcing recompile
 * Fixed menu ordering of nodes (case insensitive alphabetical)
 * Fixed zlib forking error
 * Fixed the image read and writer to the correct ARGB

# 2014-04-12 Version 0.2

* OSX package (10.7 - 10.9)
 * mpkg file
 * MacPorts Qt, etc...
 * Anaconda python
 * in-house installed PyQT and sip
 * launcher app (spawns new gpi instances, allows OS file associations)
* Linux package (Ubuntu 12.04-13.10)
 * makeself installer script
 * 13.10 gnome desktop puts borders around lib search
  * use XFCE or KDE
* Packaged Software
 * updated numpy and scipy packages (via anaconda)
 * includes pyopencl (OSX)
* GUI updates
 * Status Bar
  * canvas walltime
  * canvas mem
 * Multi-Drag-n-Drop
 * pdone (estimated only)
 * threaded data sharing between processes
  * doesn't lock up GUI (as much)
 * node-menu
  * grip
  * close-all
* Commandline Interface
 * nogui (script-able)
 * string option for configuring network
 * multiple networks, node, and user associated file-types
 * log level
* .gpirc Config File
 * user configurable
 * PATHS (lib, data, net, etc...)
 * file associations
 * make.py
* 2-Level Scope Library
 * configurable library search paths
 * node resolution based on lib-scope
 * fallback resolution based on widget+port footprint
* Network File Upgrade v2
 * backward compatible with v1 and pre-v1
 * saves lib-scope
 * machine specs
 * canvas and node walltime
  * nodes that are copied and pasted will remember their last
   walltime for pdone
* PyFI	
 * updated Numpy API >1.7
 * switched from R2 to PyFI Array (similar to R2 arrays)
  * slightly faster indexing
  * index range checking mode
  * stack traces
  * get() functions for file/line no. decorating
 * FFTW interface
  * PyCallable interface for embedding python
  * pinv()
  * numpy array printing
  * numpy fft1
 * updated error messages
  * type demangling
  * supported types list
 * support for templated functions
 * updated Macros
* NodeAPI
 * new Event API that keeps all events that initiated execution
 * Deprecated IF
  * getEvent (singular getters)
* Nodes
 * ReadPhilips
  * lab/raw/sin reader
  * xml/par/rec bug fixes (specifically for HIFU)
  * noise and phase correction output for raw formats
  * updated display to include labels for dimensions
 * core PyMODs
  * updated to PyFI Arrays
 * Mathematics Library -> Math
 * Elem_Math -> Math
 * ReadImage & WriteImage (.png or .jpg)
 * DataQuery
 * ImageCompare
 * ImageRate
 * DictionQuery
 * ReadCSV & WriteCSV (ascii, comma separated values)
 * ReadHDF5 & WriteHDF5 (still basic, under development)
 * ReadPhysioLog (scanner physiologic sensor recordings)
 * DegridDFT (for trajectory data simulation)
 * Alert (make a noise when a process has finished)
 * AutoNum (in place of IntegerLoop, does float, int, better UI)
 * DiffRMS (find scale RMS diff between two images)
 * Dimensions (updated)
 * ToComplex (updated)
 * T1calculator (for spin sims)

### Bugfixes
 * network loading of widget ports (with in and outports ON)
 * incorrect getWidget() error message (the bug threw exception during the
  error msg creation) -pointed out by David Smith
 * Better Node-Process Stability
  * fixed issue causing zombie processes

# 2013-10-18 Version 0.1

* Virtual Machine distro (VMWare 5)
 * Ubuntu 12.04 x86_64
 * intel composer (OSX), intel mkl-ipp (Linux)
 * Philips Reconstruction Platform Array Library
 * Python 2.7, Qt4 (apt-get)
* PyFI C++ interface to the Recon2.0 array library
 * handles R2 arrays and provides abstract interface for future add-ons
* Status Bar
 * canvas state, tool tips
* Tool Tips
 * node, port, edge
 * node wall time, memory usage
 * port data type
* Port Type Enforcement
 * plugin ready
 * user definable
* Edge Highlighting
 * port-edge highlighting for reverse connections
* External Widget Definitions
* Layouts
 * drag and drop widgets from Node Menu to layout
* MacroNodes
 * w/ configurable layout Node Menu
 * expandable
* Network File Upgrade
 * No longer save Qt-APIv1 components
* PyQT & PySide Compatibility
 * upgraded to Qt-APIv2
* Web Browser Widget
* Multiple Canvas Tabs
 * copy nodes between tabs
* Searchable Node Library in Mouse Menu
* Nodes R2
 * Grid & Rolloff
 * SDC
 * SpiralCoords 
* Nodes Pure Python
 * GLViewer & GLObject generator
 * ReadPhilips
* Node Labels
* Node Menu
 * about widget
 * node state status
* Documentation
 * training course
 * examples (data, networks, pure-python nodes, c++ nodes)
* Website
 * dropbox based
* Significant Improvements in Stability
 * memory collection
 * large array segmentation

# 2013-04-19 Version Pre-Alpha

* PyInstaller & Py2App packaging for Linux and OSX.
 * MacPorts Qt4, Python2.7
 * apt-get Qt4, Python 2.7
* Pure-Python nodes
* Drag-n-Drop 
* Node Library Scan
* Nodes (of interest)
 * Custom Node
 * Matplotlib
 * GLDemo
 * File Reader/Writers
 * Matlabbridge
