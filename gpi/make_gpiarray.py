#!/usr/bin/env python

#    Copyright (C) 2014  Dignity Health
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#    NO CLINICAL USE.  THE SOFTWARE IS NOT INTENDED FOR COMMERCIAL PURPOSES
#    AND SHOULD BE USED ONLY FOR NON-COMMERCIAL RESEARCH PURPOSES.  THE
#    SOFTWARE MAY NOT IN ANY EVENT BE USED FOR ANY CLINICAL OR DIAGNOSTIC
#    PURPOSES.  YOU ACKNOWLEDGE AND AGREE THAT THE SOFTWARE IS NOT INTENDED FOR
#    USE IN ANY HIGH RISK OR STRICT LIABILITY ACTIVITY, INCLUDING BUT NOT
#    LIMITED TO LIFE SUPPORT OR EMERGENCY MEDICAL OPERATIONS OR USES.  LICENSOR
#    MAKES NO WARRANTY AND HAS NO LIABILITY ARISING FROM ANY ANY USE OF THE
#    SOFTWARE IN ANY HIGH RISK OR STRICT LIABILITY ACTIVITIES.

# Brief: a make script that can double as a setup script.

'''
Use python distutils to build extension modules.  This script can be called
directly from the commandline to build C-extensions or check pure python
extensions.

A C/C++ extension module that implements an alorithm or method.

    To make, issue the following command:
        $ ./make.py <basename>
        or
        $ ./make.py <basename>.cpp
        or
        $ ./make.py <basename>.py
'''
import subprocess
from setuptools import setup, Extension
import os
import sys
import optparse  # get and process user input args
import platform
import py_compile
import traceback
import numpy

# Assuming gpi.config exists and is accessible. If not, this import might fail.
try:
    from gpi.config import Config
except ImportError:
    print("Warning: Could not import gpi.config. Custom user settings from ~/.gpirc might not be applied.")
    class Config: # Dummy Config class if import fails
        MAKE_CFLAGS = []
        MAKE_LIBS = []
        MAKE_INC_DIRS = []
        MAKE_LIB_DIRS = []
        GPI_LIBRARY_PATH = []


# error codes
SUCCESS = 0
ERROR_FAILED_COMPILATION = 1
ERROR_NO_VALID_TARGETS = 2
ERROR_INVALID_RECURSION_DEPTH = 3
ERROR_LIBRARY_CONFLICT = 4
ERROR_EXTERNAL_APP = 5

print("\n"+str(sys.version)+"\n")

# from:
# http://stackoverflow.com/questions/287871/print-in-terminal-with-colors-using-python
class Cl:
    HDR = '\033[95m'
    OKBL = '\033[94m'
    OKGR = '\033[92m'
    WRN = '\033[93m'
    FAIL = '\033[91m'
    ESC = '\033[0m'

# The basic distutils setup().
def compile_cpp_module(mod_name, sources, include_dirs=[], libraries=[], library_dirs=[],
                       extra_compile_args=[], runtime_library_dirs=[]):
    """
    Compiles a C++ extension module using setuptools.
    `sources` should be a list of all .cpp files to compile into this single module.
    """
    print(f"Making target: {mod_name}")
    print(f"Module sources: {sources}") # Show all sources being passed

    # Create the Extension object - DON'T use set() to preserve order
    Module1 = Extension(mod_name,
                        include_dirs=include_dirs,  # Remove set() to preserve order
                        libraries=libraries,        # Remove set() to preserve order
                        library_dirs=library_dirs,  # Remove set() to preserve order
                        extra_compile_args=extra_compile_args,  # Remove set() to preserve order
                        runtime_library_dirs=runtime_library_dirs,  # Remove set() to preserve order
                        sources=sources)

    # run the setup() function
    try:
        setup(name=mod_name,
              version='0.1-dev',
              description='GPIArray C++ Extension Module',
              ext_modules=[Module1],
              script_args=["build_ext", "--inplace", "--force"])
        print(f"{Cl.OKGR}SUCCESS: {mod_name}{Cl.ESC}")
        return SUCCESS
    except Exception as e:
        print((sys.exc_info()))
        print(f"{Cl.FAIL}FAILED: {mod_name}{Cl.ESC}")
        print(f"Error details: {e}")
        return ERROR_FAILED_COMPILATION


def packageArgs(args):
    """Split path and filename info into a dictionary.
    """
    cwd = os.getcwd()
    targets = []
    for arg in args:
        # Assuming args are full paths to .cpp or .py files
        full_path = os.path.abspath(arg)
        path = os.path.dirname(full_path)
        filename = os.path.basename(full_path)
        fn_base, ext = os.path.splitext(filename)

        if ext == '.cpp':
            # Determine module name for .cpp files
            if fn_base.endswith("_PyMOD"):
                mod_name = fn_base.replace("_PyMOD", "")
            elif fn_base.endswith("_PYBIND11"):
                mod_name = fn_base.replace("_PYBIND11", "")
            else:
                mod_name = fn_base # Fallback, but expect _PyMOD or _PYBIND11
            targets.append({'pth': path, 'fn': mod_name, 'ext': ext, 'full_filename': full_path})
        elif ext == '.py':
            targets.append({'pth': path, 'fn': fn_base, 'ext': ext, 'full_filename': full_path})
    return targets

def isPythonPackageDir(path):
    return os.path.isfile(str(path)+'/__init__.py')

def findLibraries(basepath):
    # This function is likely part of the original GPI setup.
    # It finds Python packages (directories with __init__.py) which are considered libraries.
    libs = []
    if os.path.isdir(basepath): # Check if basepath exists and is a directory
        if isPythonPackageDir(basepath):
            libs.append(basepath)
        for p in os.listdir(basepath):
            subdir = os.path.join(basepath,p)
            if os.path.isdir(subdir):
                if isPythonPackageDir(subdir):
                    libs.append(subdir)
    return libs

def targetWalk(recursion_depth=1):
    """
    Recurse into directories and look for _PyMOD.cpp and _PYBIND11.cpp files to compile.
    """
    targets = []
    ipath = os.getcwd()
    ocnt = ipath.count(os.sep) # Use os.sep for platform independence
    for path, dn_list, fn_list in os.walk(ipath):
        if path.count(os.sep) - ocnt <= recursion_depth:
            for fil in fn_list:
                if fil.endswith(".cpp"):
                    # Detect both _PyMOD.cpp and _PYBIND11.cpp
                    if fil.endswith("_PyMOD.cpp") or fil.endswith("_PYBIND11.cpp"):
                        mod_name_base = os.path.splitext(fil)[0]
                        mod_name = ""
                        if mod_name_base.endswith("_PyMOD"):
                            mod_name = mod_name_base.replace("_PyMOD", "")
                        elif mod_name_base.endswith("_PYBIND11"):
                            mod_name = mod_name_base.replace("_PYBIND11", "")
                        
                        targets.append({
                            'pth': path,
                            'fn': mod_name, # Base module name (e.g., 'FFTW')
                            'ext': '.cpp',
                            'full_filename': os.path.join(path, fil) # Full path to the specific source file
                        })
                elif fil.endswith(".py"):
                    fn_base, ext = os.path.splitext(fil)
                    targets.append({
                        'pth': path,
                        'fn': fn_base,
                        'ext': ext,
                        'full_filename': os.path.join(path, fil)
                    })
    return targets


def makePy(basename, ext, fmt=False, check_fmt=None):
    # This function handles pure Python file formatting and byte-compilation.
    if check_fmt is None:
        check_fmt = []

    target_file = basename + ext

    # AUTOPEP8
    if fmt:
        try:
            import autopep8
            print(("\nFound: autopep8 " + str(autopep8.__version__) + "..."))
            print(f"Reformatting Python script: {target_file}")
            subprocess.run(['autopep8', '-i', '--max-line-length', '256', target_file], check=True)
        except ImportError:
            print("Failed to import \'autopep8\'. Do you have it installed?")
        except subprocess.CalledProcessError as e:
            print(f"autopep8 failed: {e}")

    if 'pep8' in check_fmt:
        try:
            import pep8
            print(("\nFound: pep8 " + str(pep8.__version__) + "..."))
            print(f"Checking Python script: {target_file}")
            print((Cl.WRN + "pep8 found these problems with your code, START" + Cl.ESC))
            subprocess.run(['pep8', '--count', '--statistics', '--show-source', target_file], check=True)
            print((Cl.ESC + "pep8 END"))
        except ImportError:
            print("Failed to import \'pep8\'. Do you have it installed?")
        except subprocess.CalledProcessError as e:
            print(f"pep8 failed: {e}")


    if 'pyflakes' in check_fmt:
        try:
            import pyflakes.api
            print(("\nFound: pyflakes " + str(pyflakes.__version__) + "..."))
            print(f"Checking Python script: {target_file}")
            print((Cl.FAIL + "pyflakes found these problems with your code, START" + Cl.ESC))
            # Pyflakes doesn't have a simple CLI like pep8 or autopep8 for error codes,
            # so using subprocess.run with capture_output to print output directly.
            result = subprocess.run(['pyflakes', target_file], capture_output=True, text=True)
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(result.stderr)
            print((Cl.ESC + "pyflakes END"))
        except ImportError:
            print("Failed to import \'pyflakes\'. Do you have it installed?")
        except subprocess.CalledProcessError as e:
            print(f"pyflakes failed: {e}")

    # FORCE COMPILE
    try:
        print('\nAttemping py_compile...')
        py_compile.compile(target_file, doraise=True)
        print('py_compile END')
        print(f"\n{Cl.OKGR}SUCCESS: {target_file}{Cl.ESC}")
        return SUCCESS
    except Exception:
        print((Cl.FAIL + str(traceback.format_exc()) + Cl.ESC))
        print('py_compile END')
        print(f"\n{Cl.FAIL}FAILED: {target_file}{Cl.ESC}")
        return ERROR_FAILED_COMPILATION


def make(GPI_PREFIX=None):
    '''Commandline interface to the make utilities.
    '''
    # Define the project root directory where this script is located
    PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
    # Define the source directory relative to the project root
    SRC_DIR = os.path.join(PROJECT_ROOT, 'src')

    # LIBRARIES, INCLUDES, ENV-VARS (initialized with base paths)
    base_include_dirs = []
    base_libraries = []
    base_library_dirs = []
    base_extra_compile_args = []
    base_runtime_library_dirs = []

    import pathlib
    # GPI_DIR is similar to PROJECT_ROOT here for includes
    GPI_DIR = pathlib.Path(__file__).parent.resolve()
    print("Adding GPI include directory")
    if GPI_PREFIX is not None:
        base_include_dirs.append(os.path.join(GPI_PREFIX, 'include', 'eigen3'))
        base_include_dirs.append(os.path.join(GPI_PREFIX, 'include'))
        base_include_dirs.append(os.path.join(GPI_DIR, 'include'))
        if platform.system() == 'Windows':
            base_include_dirs.append(os.path.join(GPI_PREFIX, 'Library/include'))

    # Add project specific include for "PyFI/"
    base_include_dirs.append(SRC_DIR)

    # Handle CONDA environment and its libraries/includes
    if 'CONDA_PREFIX' in os.environ:
        conda_env_path = os.environ['CONDA_PREFIX']
        print(f"CONDA_PREFIX detected: {conda_env_path}")
        
        # Add Conda include and library directories
        base_include_dirs.append(os.path.join(conda_env_path, 'include'))
        base_library_dirs.append(os.path.join(conda_env_path, 'lib'))
        base_runtime_library_dirs.append(os.path.join(conda_env_path, 'lib')) # For runtime linking
        
        print(f"Configured FFTW3 Include Dir: {os.path.join(conda_env_path, 'include')}")
        print(f"Configured FFTW3 Library Dir: {os.path.join(conda_env_path, 'lib')}")
    else:
        print(f"{Cl.FAIL}CONDA_PREFIX environment variable not set. Please activate your conda environment before configuring CMake.{Cl.ESC}")
        sys.exit(ERROR_EXTERNAL_APP)


    parser = optparse.OptionParser()
    parser.add_option('--preprocess', dest='preprocess', default=False,
                      action="store_true", help='''Only do preprocessing to \
                              target (the resulting .o file will be \
                              preprocessed code.)''')
    parser.add_option('-w', '--suppressWarnings', dest='suppressWarnings',
                      default=False, action="store_true",
                      help='''Tell gcc to only display errors.''')
    parser.add_option('--fmt', dest='format', default=False,
                      action="store_true",
                      help="Auto-format using the autopep8 and astyle scripts.")
    parser.add_option('--pep8', dest='check_format',
                      action="append_const", const="pep8",
                      help="Check Python code format using pep8.")
    parser.add_option('--pyflakes', dest='check_format',
                      action="append_const", const="pyflakes",
                      help="Check Python code format using pyflakes.")
    parser.add_option('--all', dest='makeall', default=False,
                      action='store_true',
                      help="Recursively search for .cpp files and attempt to" +
                      "make them (integer arg sets recursion depth).")
    parser.add_option('-r', '--rdepth', dest='makeall_rdepth', type="int",
                      default=1,
                      help="Integer arg sets recursion depth for makeall.")
    parser.add_option('--debug', dest='debug', default=False,
                      action='store_true',
                      help="Uses range checker for PyFI::Array calls.")
    parser.add_option('--ignore-gpirc', dest='ignore_gpirc', default=False,
                      action='store_true',
                      help="Ignore the ~/.gpirc config.")
    parser.add_option('--ignore-system-libs', dest='ignore_sys', default=False,
                      action='store_true',
                      help="Ignore the system libraries (e.g. for conda build).")
    parser.add_option('--osx-ver', dest='osx_target_ver',
                      help="Override tgt. version for OSX builds (must be '10.X').")

    parser.add_option(
        '-v', '--verbose', dest='verbose', default=False, action="store_true",
        help='''Verbosity.''')

    parser.add_option(
        '-d', '--distdebug', dest='distdebug', default=False, action="store_true",
        help='''Sets DISTUTILS_DEBUG. ''')

    # get user input 'options', and extra 'args' that were unprocessed
    options, args = parser.parse_args()
    opt = vars(options)

    if options.distdebug:
        os.environ['DISTUTILS_DEBUG'] = '1'

    # Determine targets: either explicitly passed args or discovered via targetWalk
    targets = None
    if len(args) > 0:
        targets = packageArgs(args)
    elif options.makeall:
        if options.makeall_rdepth < 0:
            print((Cl.FAIL + "ERROR: recursion depth is set to an invalid number." + Cl.ESC))
            sys.exit(ERROR_INVALID_RECURSION_DEPTH)
        targets = targetWalk(options.makeall_rdepth)

    if targets is None or not targets:
        print((Cl.FAIL + "ERROR: no valid targets specified or found." + Cl.ESC))
        sys.exit(ERROR_NO_VALID_TARGETS)

    # USER MAKE config (assuming gpi.config exists and has these attributes)
    # This block needs to be carefully integrated if `gpi.config` handles custom library paths.
    if not options.ignore_gpirc and 'Config' in sys.modules:
        if hasattr(Config, 'MAKE_LIBS'): base_libraries.extend(Config.MAKE_LIBS)
        if hasattr(Config, 'MAKE_INC_DIRS'): base_include_dirs.extend(Config.MAKE_INC_DIRS)
        if hasattr(Config, 'MAKE_LIB_DIRS'): base_library_dirs.extend(Config.MAKE_LIB_DIRS)
        if hasattr(Config, 'MAKE_CFLAGS'): base_extra_compile_args.extend(Config.MAKE_CFLAGS)
        
        # GPI library paths from .gpirc
        if hasattr(Config, 'GPI_LIBRARY_PATH') and Config.GPI_LIBRARY_PATH:
            print("Adding library paths from .gpirc file")
            for flib_path in Config.GPI_LIBRARY_PATH:
                if os.path.isdir(flib_path):
                    for usrdir in findLibraries(flib_path):
                        p = os.path.dirname(usrdir)
                        b = os.path.basename(usrdir)
                        base_include_dirs.append(os.path.dirname(usrdir)) # Add parent dir of Python package
                        base_library_dirs.append(usrdir) # Add the actual library directory for linking (e.g., where libfoo.so is)
    else:
        # Fallback if GPI.config is not used or ignored, look in project root and parent dirs.
        print("Looking for GPI libraries in current and parent directories (no .gpirc used).")
        search_dirs_fallback = [PROJECT_ROOT, os.path.dirname(PROJECT_ROOT)]
        for flib_path in search_dirs_fallback:
            if os.path.isdir(flib_path):
                for usrdir in findLibraries(flib_path):
                    base_include_dirs.append(os.path.dirname(usrdir))
                    base_library_dirs.append(usrdir) # Add the actual library directory

    # NumPy includes
    base_include_dirs.append(numpy.get_include())

    # Pybind11 includes
    try:
        import pybind11
        base_include_dirs.append(pybind11.get_include())
        base_include_dirs.append(pybind11.get_include(user=True))
    except ImportError:
        print(f"{Cl.FAIL}Error: pybind11 not found. Please install it (e.g., pip install pybind11).{Cl.ESC}")
        sys.exit(ERROR_EXTERNAL_APP)

    # FFTW Libraries (from CMakeLists.txt)
    if platform.system() == 'Windows':
        base_libraries.extend(['fftw3', 'fftw3f'])
    else: # Linux/macOS
        base_libraries.extend(['fftw3_threads', 'fftw3', 'fftw3f_threads', 'fftw3f'])
    print(f"Configured FFTW3 Libraries: {', '.join(base_libraries)}")

    # POSIX THREADS (from CMakeLists.txt)
    if platform.system() == 'Windows':
        base_libraries.append('pthreads')
    else:
        base_libraries.append('pthread')
    print(f"Configured POSIX Threads Libraries: {base_libraries[-1]}")

    # COMPILATION LOOP
    successes = []
    failures = []
    py_successes = []
    py_failures = []

    for target in targets:
        # Change to the directory where the current target's source file is located
        # This helps resolve relative paths in includes within that source file.
        original_cwd = os.getcwd() # Store original CWD
        os.chdir(target['pth'])

        # Create copies of base lists for per-target modifications
        current_extra_compile_args = list(base_extra_compile_args)
        current_libraries = list(base_libraries)
        current_include_dirs = list(base_include_dirs)
        current_library_dirs = list(base_library_dirs)
        current_runtime_library_dirs = list(base_runtime_library_dirs)


        # Handle Python file (formatting/bytecode compilation)
        if target['ext'] == '.py':
            retcode = makePy(target['fn'], target['ext'],
                             fmt=options.format,
                             check_fmt=options.check_format)
            if retcode != 0:
                py_failures.append(target['fn'])
            else:
                py_successes.append(target['fn'])
            os.chdir(original_cwd) # Restore CWD before next target
            continue # Move to next target


        # Handle C++ compilation
        # ASTYLE (if requested)
        if options.format:
            try:
                print("\nAstyle...")
                print(f"Reformatting CPP Code: {target['full_filename']}")
                subprocess.run(['astyle', '-A1', '-S', '-w', '-c', '-k3', '-b', '-H', '-U', '-C', target['full_filename']], check=True)
                # If astyle is the only action, skip compilation
                if not args or (len(args) == 1 and args[0] == target['full_filename']): # Only format this file if it's the only one specified
                    os.chdir(original_cwd) # Restore CWD
                    continue # Skip compilation if only formatting
            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                print(f"Failed to perform auto-formatting with \'astyle\'. Error: {e}. Do you have it installed and in PATH?")
                sys.exit(ERROR_EXTERNAL_APP)
        
        # Apply C++ standard and optimization/debug flags based on _PYBIND11.cpp
        if target['ext'] == '.cpp': # Only apply these flags to C++ files
            current_extra_compile_args = [arg for arg in current_extra_compile_args if not arg.startswith('-std=c++')] # Remove default C++ standard
            current_extra_compile_args.append('-std=c++20') # Enforce C++20 for all C++ files
            
            # Optimization flags (from CMakeLists.txt)
            if not options.debug: # Only for release builds
                current_extra_compile_args.extend(['-O3', '-march=native', '-DNDEBUG']) 
            else: # Debug specific flags
                current_extra_compile_args.append('-DGPIARRAY_ENABLE_BOUNDS_CHECKS') #

            # OpenMP (from CMakeLists.txt)
            if platform.system() == 'Darwin':  # macOS specific OpenMP setup
                # On macOS with Apple Clang, need to use -Xpreprocessor -fopenmp together
                # and link with libomp
                current_extra_compile_args.extend(['-Xpreprocessor', '-fopenmp'])
                current_libraries.append('omp') # Link against libomp.dylib
                print(f"Using OpenMP for module {target['fn']} (macOS specific flags)")
            elif platform.system() == 'Linux': # Linux OpenMP setup (GCC)
                current_extra_compile_args.append('-fopenmp')
                current_libraries.append('gomp') # Common OpenMP library for GCC on Linux
                print(f"Using OpenMP for module {target['fn']} (Linux specific flags)")
            
            # Add MOD_NAME definition
            current_extra_compile_args.append('-DMOD_NAME=' + target['fn'])

            # Sources for compilation: only the main _PYBIND11.cpp (or _PyMOD.cpp) file.
            module_sources_for_compilation = [target['full_filename']]

            # Removed 'cnpy' from current_libraries.append('cnpy')
            # It's now assumed to be a header-only library, so no explicit linking is needed.

            retcode = compile_cpp_module(
                target['fn'], # Module name
                module_sources_for_compilation, # List of source files
                current_include_dirs,
                current_libraries,
                current_library_dirs,
                current_extra_compile_args,
                current_runtime_library_dirs
            )

            if retcode != 0:
                failures.append(target['fn'])
            else:
                successes.append(target['fn'])
        
        os.chdir(original_cwd) # Always restore CWD before next target

    # SUMMARY
    print(('\nSUMMARY (CPP Compilations):\n\tSUCCESSES ('+Cl.OKGR+str(len(successes))+Cl.ESC+'):'))
    for i in successes:
        print(("\t\t" + i))
    print(('\tFAILURES ('+Cl.FAIL+str(len(failures))+Cl.ESC+'):'))
    for i in failures:
        print(("\t\t" + i))

    # ON FAILURE
    if len(py_failures) + len(failures) > 0: # Include pure Python failures
        sys.exit(ERROR_FAILED_COMPILATION)
    # ON SUCCESS
    else:
        sys.exit(SUCCESS)

if __name__ == '__main__':
    make()