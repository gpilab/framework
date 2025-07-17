#!/usr/bin/env python

# Copyright (C) 2014 Dignity Health
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# NO CLINICAL USE. THE SOFTWARE IS NOT INTENDED FOR COMMERCIAL PURPOSES
# AND SHOULD BE USED ONLY FOR NON-COMMERCIAL RESEARCH PURPOSES. THE
# SOFTWARE MAY NOT IN ANY EVENT BE USED FOR ANY CLINICAL OR DIAGNOSTIC
# PURPOSES. YOU ACKNOWLEDGE AND AGREE THAT THE SOFTWARE IS NOT INTENDED FOR
# USE IN ANY HIGH RISK OR STRICT LIABILITY ACTIVITY, INCLUDING BUT NOT
# LIMITED TO LIFE SUPPORT OR EMERGENCY MEDICAL OPERATIONS OR USES. LICENSOR
# MAKES NO WARRANTY AND HAS NO LIABILITY ARISING FROM ANY USE OF THE
# SOFTWARE IN ANY HIGH RISK OR STRICT LIABILITY ACTIVITIES.

# make_gpiarray.py
# Author: Guru Krishnamoorthy
# Date: 2025-Jul
#
# Build and setup script for compiling C++ extension modules (_PYBIND11.cpp) for GPIArray using setuptools.
# Intended for non-commercial research purposes only; not for clinical or diagnostic use.
#
# Features:
# - Recursively searches for _PYBIND11.cpp files in project and user-specified directories.
# - Builds C++ extension modules using setuptools and pybind11.
# - Supports custom configuration via gpi.config and ~/.gpirc.
# - Handles platform-specific compiler flags and library paths (macOS, Linux, Windows).
# - Implements a compilation cache to skip unchanged files.
# - Provides command-line options for recursion depth, debug mode, ignoring system/user configs, and verbose output.
# - Prints color-coded summaries of compilation successes and failures.
#
# Usage:
#   --all                Recursively build all _PYBIND11.cpp modules.
#   -r, --rdepth         Set recursion depth for --all.
#   --debug              Enable debug flags.
#   --ignore-gpirc       Ignore ~/.gpirc and gpi.config.
#   --ignore-system-libs Ignore system libraries.
#   --osx-ver            Set target macOS version.
#   -v, --verbose        Enable verbose output.
#   -d, --distdebug      Enable distutils debug output.
#
# Returns:
#   SUCCESS (0) on successful compilation,
#   ERROR_FAILED_COMPILATION (1) if any compilation fails,
#   Other error codes for invalid arguments or configuration issues.
#
# Note:
#   This script is not intended for clinical, diagnostic, or commercial use.



'''
Use python distutils to build extension modules. This script can be called
directly from the commandline to build C-extensions.

A C/C++ extension module that implements an alorithm or method.

    This script is specifically designed to build _PYBIND11.cpp files.
    To make, issue the following command:
        $ ./make_gpiarray.py <basename>_PYBIND11.cpp
        or
        $ ./make_gpiarray.py --all
'''
import subprocess
from setuptools import setup, Extension
import os
import sys
import optparse  # get and process user input args
import platform
import numpy
from contextlib import contextmanager # For safer chdir
import tempfile
import pickle
import hashlib
import time
import re
import glob

# Assuming gpi.config exists and is accessible.
# If not, a more robust dummy Config or early exit will be used.
try:
    from gpi.config import Config
except ImportError:
    print("Warning: Could not import gpi.config. Custom user settings from ~/.gpirc might not be applied.")
    class Config: # Dummy Config class if import fails, ensuring all expected attributes exist
        MAKE_CFLAGS = []
        MAKE_LIBS = []
        MAKE_INC_DIRS = []
        MAKE_LIB_DIRS = []
        GPI_LIBRARY_PATH = []
        # Add any other attributes that might be accessed later to prevent AttributeError
        # e.g., GPI_PYTHON_PATH = []

# error codes
SUCCESS = 0
ERROR_FAILED_COMPILATION = 1
ERROR_NO_VALID_TARGETS = 2
ERROR_INVALID_RECURSION_DEPTH = 3
ERROR_LIBRARY_CONFLICT = 4
ERROR_EXTERNAL_APP = 5
ERROR_CONFIG_MISSING = 6

# from:
# http://stackoverflow.com/questions/287871/print-in-terminal-with-colors-using-python
class Cl:
    HDR = '\033[95m'
    OKBL = '\033[94m'
    OKGR = '\033[92m'
    WRN = '\033[93m'
    FAIL = '\033[91m'
    ESC = '\033[0m'

@contextmanager
def chdir(newpath):
    """Context manager for changing the current working directory."""
    old_path = os.getcwd()
    os.chdir(newpath)
    try:
        yield
    finally:
        os.chdir(old_path)

def compile_cpp_module(mod_name, sources, include_dirs=[], libraries=[], library_dirs=[],
                       extra_compile_args=[], runtime_library_dirs=[], verbose=False):
    """
    Compiles a C++ extension module using setuptools.
    `sources` should be a list of all .cpp files to compile into this single module.
    """
    print(f"Making target: {mod_name}")

    # Setuptools command-line arguments
    script_args = ["build_ext", "--inplace", "--force"]
    if not verbose:
        script_args.append("--quiet")

    # Create the Extension object
    Module1 = Extension(mod_name,
                        include_dirs=include_dirs,
                        libraries=libraries,
                        library_dirs=library_dirs,
                        extra_compile_args=extra_compile_args,
                        runtime_library_dirs=runtime_library_dirs,
                        sources=sources)

    try:
        setup(name=mod_name,
              version='0.1-dev',
              description='GPIArray C++ Extension Module',
              ext_modules=[Module1],
              script_args=script_args)
        print(f"{Cl.OKGR}SUCCESS: {mod_name}{Cl.ESC}")
        return SUCCESS
    except Exception as e: # Catching broad Exception for now, could be more specific
        print(f"{Cl.FAIL}FAILED: {mod_name}{Cl.ESC}")
        print(f"Error details: {e}")
        # traceback.print_exc() # For more detailed Python stack trace if needed
        return ERROR_FAILED_COMPILATION


def packageArgs(args):
    """Split path and filename info into a dictionary.
    Assumes args are full paths to .cpp files.
    """
    targets = []
    for arg in args:
        full_path = os.path.abspath(arg)
        path = os.path.dirname(full_path)
        filename = os.path.basename(full_path)
        fn_base, ext = os.path.splitext(filename)

        if ext == '.cpp' and fn_base.endswith("_PYBIND11"): # Only target _PYBIND11.cpp
            mod_name = fn_base.replace("_PYBIND11", "")
            targets.append({'pth': path, 'fn': mod_name, 'ext': ext, 'full_filename': full_path})
        elif ext == '.cpp' and not fn_base.endswith("_PYBIND11"):
            print(f"Skipping non-_PYBIND11.cpp file: {filename}. This script only builds _PYBIND11.cpp modules.")
        # Removed .py handling as per user's request for make_gpiarray.py
    return targets

def isPythonPackageDir(path):
    """Checks if a given path is a Python package directory."""
    return os.path.isdir(path) and os.path.isfile(os.path.join(path, '__init__.py'))

def findLibrariesInPath(basepath):
    """
    Finds Python packages (directories with __init__.py) within a basepath.
    """
    libs = []
    if os.path.isdir(basepath):
        if isPythonPackageDir(basepath):
            libs.append(basepath)
        for p in os.listdir(basepath):
            subdir = os.path.join(basepath, p)
            if os.path.isdir(subdir) and isPythonPackageDir(subdir):
                libs.append(subdir)
    return libs

COMPILATION_CACHE_FILE = os.path.join(tempfile.gettempdir(), 'gpi_make_gpiarray_cache.pkl')
CACHE_EXPIRY_MINUTES = 30  # Cache valid for 30 minutes

def get_file_hash(filepath):
    """Get hash of file content for cache validation."""
    try:
        with open(filepath, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    except:
        return None

def load_compilation_cache():
    """Load compilation cache from disk."""
    try:
        if os.path.exists(COMPILATION_CACHE_FILE):
            with open(COMPILATION_CACHE_FILE, 'rb') as f:
                cache = pickle.load(f)
                # Check if cache is still valid (not expired)
                if time.time() - cache.get('timestamp', 0) < CACHE_EXPIRY_MINUTES * 60:
                    return cache.get('compiled_files', {})  # Return dict, not set
    except:
        pass
    return {}  # Return empty dict, not set

def save_compilation_cache(compiled_files):
    """Save compilation cache to disk."""
    try:
        cache = {
            'timestamp': time.time(),
            'compiled_files': compiled_files  # This should be a dict
        }
        with open(COMPILATION_CACHE_FILE, 'wb') as f:
            pickle.dump(cache, f)
    except:
        pass

def get_file_dependencies(cpp_filepath):
    """Extract header file dependencies from a C++ file."""
    dependencies = set()
    dependencies.add(cpp_filepath)  # Include the source file itself
    
    try:
        with open(cpp_filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        # Find all #include statements
        include_pattern = r'#include\s*[<"]([^>"]+)[>"]'
        includes = re.findall(include_pattern, content)
        
        cpp_dir = os.path.dirname(cpp_filepath)
        
        for include in includes:
            # Check for local header files (not system headers)
            if not include.startswith('/') and not include.startswith('<'):
                # Try to find the header file in the same directory or subdirectories
                potential_paths = [
                    os.path.join(cpp_dir, include),
                    os.path.join(cpp_dir, '..', include),
                    os.path.join(cpp_dir, '..', '..', include),
                    # Add more search paths as needed
                ]
                
                for path in potential_paths:
                    if os.path.exists(path):
                        dependencies.add(os.path.abspath(path))
                        break
                else:
                    # Try glob pattern for headers in subdirectories
                    search_pattern = os.path.join(cpp_dir, '**', include)
                    found_files = glob.glob(search_pattern, recursive=True)
                    if found_files:
                        dependencies.add(os.path.abspath(found_files[0]))
    
    except Exception as e:
        print(f"Warning: Could not parse dependencies for {cpp_filepath}: {e}")
    
    return dependencies

def get_file_hash_with_dependencies(filepath):
    """Get combined hash of file and its dependencies."""
    try:
        dependencies = get_file_dependencies(filepath)
        all_content = []
        
        for dep_file in sorted(dependencies):  # Sort for consistent hashing
            if os.path.exists(dep_file):
                try:
                    with open(dep_file, 'rb') as f:
                        all_content.append(f.read())
                except:
                    # If we can't read a dependency, include its modification time
                    all_content.append(str(os.path.getmtime(dep_file)).encode())
        
        # Combine all content and hash it
        combined_content = b''.join(all_content)
        return hashlib.md5(combined_content).hexdigest()
    except Exception as e:
        print(f"Warning: Could not compute dependency hash for {filepath}: {e}")
        return get_file_hash(filepath)  # Fallback to simple file hash

def should_skip_compilation(filepath, cache):
    """Check if file should be skipped based on cache and dependencies."""
    if filepath in cache:
        cached_info = cache.get(filepath)
        if isinstance(cached_info, dict):
            # Check dependency-aware hash
            current_hash = get_file_hash_with_dependencies(filepath)
            cached_hash = cached_info.get('dependency_hash') or cached_info.get('hash')
            
            if current_hash == cached_hash:
                print(f"  Skipping {os.path.basename(filepath)} (unchanged with dependencies)")
                return True
            else:
                print(f"  Will compile {os.path.basename(filepath)} (dependencies changed)")
                return False
    return False

def get_search_directories(project_root, ignore_gpirc, ignore_sys):
    """Collects directories where _PYBIND11.cpp files might reside."""
    search_dirs = []
    current_cwd = os.getcwd()
    
    # CRITICAL: Skip if we're in system directories or already processed locations
    system_paths = [
        '/Users/gkrishnamoo3/miniforge3',
        '/site-packages/gpi_core',
        '/site-packages/gpi'
    ]
    
    if any(current_cwd.startswith(path) or path in current_cwd for path in system_paths):
        print(f"{Cl.WRN}Skipping search from system/cached location: {current_cwd}{Cl.ESC}")
        return []

    # Only add current working directory if it's a valid project directory
    if (not current_cwd.startswith('/Users/gkrishnamoo3/miniforge3') and
        not current_cwd.endswith('/site-packages/gpi_core') and
        not current_cwd.endswith('/site-packages/gpi')):
        search_dirs.append(current_cwd)

    # 1. From gpi.config (if available and not ignored)
    if not ignore_gpirc and 'Config' in sys.modules:
        try:
            if hasattr(Config, 'GPI_LIBRARY_PATH') and Config.GPI_LIBRARY_PATH:
                for flib_path in Config.GPI_LIBRARY_PATH:
                    if os.path.isdir(flib_path):
                        # Be more selective about which paths to include
                        if not any(excluded in flib_path for excluded in ['/miniforge3', '/site-packages']):
                            for usrdir in findLibrariesInPath(flib_path):
                                search_dirs.append(usrdir)
        except Exception as e:
            print(f"Warning: Could not process Config.GPI_LIBRARY_PATH from gpi.config: {e}")

    # 2. From ~/.gpirc (fallback/additional) - be much more selective
    if not ignore_gpirc:
        gpirc_path = os.path.expanduser('~/.gpirc')
        if os.path.exists(gpirc_path):
            try:
                with open(gpirc_path, 'r') as f:
                    for line in f:
                        if line.strip().startswith('LIB_DIRS'):
                            lib_dirs_line = line.strip().split('=', 1)
                            if len(lib_dirs_line) > 1:
                                lib_dirs = lib_dirs_line[1].strip().split(':')
                                for lib_dir in lib_dirs:
                                    lib_dir = lib_dir.strip()
                                    # MUCH more restrictive filtering
                                    excluded_patterns = [
                                        '/miniforge3',
                                        '/site-packages',
                                        '/Documents/SW/Backup',  # Exclude backup directories
                                        '/Documents/SW' if not '/Documents/SW/GPI' in lib_dir else None  # Only allow specific GPI projects
                                    ]
                                    excluded_patterns = [p for p in excluded_patterns if p is not None]
                                    
                                    if (lib_dir and os.path.isdir(lib_dir) and 
                                        not any(excluded in lib_dir for excluded in excluded_patterns)):
                                        search_dirs.append(lib_dir)
            except Exception as e:
                print(f"Warning: Could not parse ~/.gpirc: {e}")
    
    # 3. Only add targeted fallback paths
    if ignore_sys:
        print("Adding current working directory as a library path (ignore-system-libs is true).")
        if current_cwd not in search_dirs:
            search_dirs.append(current_cwd)
    else:
        print("Looking for node library files in project-specific locations.")

    # Remove duplicates and filter out problematic paths
    unique_search_dirs = []
    for d in search_dirs:
        normalized_d = os.path.abspath(d)
        excluded_endings = [
            '/Documents',
            '/miniforge3/envs/gpi/lib/python3.9',
            '/site-packages/gpi_core',
            '/site-packages/gpi',
            '/Backup'  # Exclude backup directories
        ]
        
        if (normalized_d not in unique_search_dirs and
            not any(normalized_d.endswith(ending) for ending in excluded_endings)):
            unique_search_dirs.append(normalized_d)
    
    return unique_search_dirs

def targetWalk(recursion_depth=1, project_root=None, ignore_gpirc=False, ignore_sys=False):
    """
    Recurse into directories and look for _PYBIND11.cpp files to compile.
    """
    targets = []
    found_files = set()  # Track files we've already found to avoid duplicates
    
    if project_root is None:
        project_root = os.path.dirname(os.path.abspath(__file__))

    unique_search_dirs = get_search_directories(project_root, ignore_gpirc, ignore_sys)
    
    print(f"Searching for _PYBIND11.cpp files in {len(unique_search_dirs)} directories:")
    for search_dir in unique_search_dirs:
        print(f"  {search_dir}")
    
    found_pybind_files = []
    
    for base_dir in unique_search_dirs:
        if not os.path.exists(base_dir):
            print(f"Warning: Directory does not exist: {base_dir}")
            continue
            
        base_depth = base_dir.count(os.sep)
        
        for path, dn_list, fn_list in os.walk(base_dir):
            current_depth = path.count(os.sep) - base_depth
            if current_depth <= recursion_depth:
                for fil in fn_list:
                    if fil.endswith("_PYBIND11.cpp"):
                        full_path = os.path.abspath(os.path.join(path, fil))  # Use absolute path
                        
                        # Skip if we've already found this file
                        if full_path in found_files:
                            continue
                        
                        found_files.add(full_path)
                        found_pybind_files.append(full_path)
                        mod_name_base = os.path.splitext(fil)[0]
                        mod_name = mod_name_base.replace("_PYBIND11", "")
                        
                        targets.append({
                            'pth': path,
                            'fn': mod_name, # Base module name (e.g., 'Grid')
                            'ext': '.cpp',
                            'full_filename': full_path # Full path to the specific source file
                        })
    
    print(f"\nSUMMARY:")
    print(f"Found {len(found_pybind_files)} _PYBIND11.cpp files:")
    for f in found_pybind_files:
        print(f"  {f}")
    
    return targets


class BuildConfiguration:
    def __init__(self, options, project_root, gpi_prefix=None):
        self.options = options
        self.project_root = project_root
        self._gpi_prefix = gpi_prefix # Store it
        self.include_dirs = []
        self.libraries = []
        self.library_dirs = []
        self.extra_compile_args = []
        self.runtime_library_dirs = []

        self._initialize_paths()
        self._load_gpirc_config()
        self._add_python_includes()
        self._add_system_libraries()
        self._apply_compiler_flags()

    def _initialize_paths(self):
        """Initialize base paths based on project structure and GPI_PREFIX."""
        gpi_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Add project specific include for "PyFI/" (assuming src is PyFI)
        src_dir = os.path.join(self.project_root, 'src')
        if os.path.isdir(src_dir):
            self.include_dirs.append(src_dir)

        # Use the passed gpi_prefix if available, otherwise check environment
        effective_gpi_prefix = self._gpi_prefix if self._gpi_prefix is not None else os.environ.get('GPI_PREFIX')

        if effective_gpi_prefix:
            print(f"Using GPI_PREFIX: {effective_gpi_prefix}")
            self.include_dirs.append(os.path.join(effective_gpi_prefix, 'include', 'eigen3'))
            self.include_dirs.append(os.path.join(effective_gpi_prefix, 'include'))
            self.include_dirs.append(os.path.join(gpi_dir, 'include'))
            if platform.system() == 'Windows':
                self.include_dirs.append(os.path.join(effective_gpi_prefix, 'Library/include'))
            
            self.library_dirs.append(os.path.join(effective_gpi_prefix, 'lib'))
            if platform.system() == 'Windows':
                self.library_dirs.append(os.path.join(effective_gpi_prefix, 'Library/lib'))
        else:
            print(f"{Cl.WRN}Warning: GPI_PREFIX not explicitly provided or found in environment.{Cl.ESC}")


        # Conda environment paths
        if 'CONDA_PREFIX' in os.environ:
            conda_env_path = os.environ['CONDA_PREFIX']
            print(f"CONDA_PREFIX detected: {conda_env_path}")
            self.include_dirs.append(os.path.join(conda_env_path, 'include'))
            self.library_dirs.append(os.path.join(conda_env_path, 'lib'))
            self.runtime_library_dirs.append(os.path.join(conda_env_path, 'lib'))
        else:
            print(f"{Cl.WRN}Warning: CONDA_PREFIX environment variable not set. Please activate your conda environment for optimal build.{Cl.ESC}")

    def _load_gpirc_config(self):
        """Load configuration from gpi.config or ~/.gpirc."""
        if not self.options.ignore_gpirc and 'Config' in sys.modules:
            if hasattr(Config, 'MAKE_LIBS'): self.libraries.extend(Config.MAKE_LIBS)
            if hasattr(Config, 'MAKE_INC_DIRS'): self.include_dirs.extend(Config.MAKE_INC_DIRS)
            if hasattr(Config, 'MAKE_LIB_DIRS'): self.library_dirs.extend(Config.MAKE_LIB_DIRS)
            if hasattr(Config, 'MAKE_CFLAGS'): self.extra_compile_args.extend(Config.MAKE_CFLAGS)
            
            # GPI library paths from .gpirc/Config.GPI_LIBRARY_PATH
            if hasattr(Config, 'GPI_LIBRARY_PATH') and Config.GPI_LIBRARY_PATH:
                for flib_path in Config.GPI_LIBRARY_PATH:
                    if os.path.isdir(flib_path):
                        for usrdir in findLibrariesInPath(flib_path):
                            self.include_dirs.append(os.path.dirname(usrdir))
                            self.library_dirs.append(usrdir)

    def _add_python_includes(self):
        """Add NumPy and Pybind11 includes."""
        self.include_dirs.append(numpy.get_include())
        try:
            import pybind11
            self.include_dirs.append(pybind11.get_include())
            self.include_dirs.append(pybind11.get_include(user=True))
        except ImportError:
            print(f"{Cl.FAIL}Error: pybind11 not found. Please install it (e.g., pip install pybind11).{Cl.ESC}")
            sys.exit(ERROR_EXTERNAL_APP)

    def _add_system_libraries(self):
        """Add common system/external libraries like FFTW and Pthreads."""
        if not self.options.ignore_sys:
            # FFTW Libraries (from CMakeLists.txt)
            if platform.system() == 'Windows':
                self.libraries.extend(['fftw3', 'fftw3f'])
            else: # Linux/macOS
                self.libraries.extend(['fftw3_threads', 'fftw3', 'fftw3f_threads', 'fftw3f'])

            # POSIX THREADS (from CMakeLists.txt)
            if platform.system() == 'Windows':
                self.libraries.append('pthreads')
            else:
                self.libraries.append('pthread')
            
            # Add common system library paths if not ignored (from make.py)
            if platform.system() != 'Windows': # Unix-like systems
                self.include_dirs.append('/usr/include')
                self.library_dirs.append('/usr/lib')
                # macOS specific for malloc.h if needed (from make.py)
                if platform.system() == 'Darwin':
                    self.include_dirs.append('/usr/include/malloc')


    def _apply_compiler_flags(self):
        """Apply standard, optimization, debug, and OpenMP flags."""
        # Ensure C++20
        # Remove any existing -std=c++ flags to enforce C++20
        self.extra_compile_args = [arg for arg in self.extra_compile_args if not arg.startswith('-std=c++')]
        self.extra_compile_args.append('-std=c++20')

        # Suppress warnings by default
        self.extra_compile_args.append('-w')

        # Optimization vs. Debug flags
        if not self.options.debug:
            self.extra_compile_args.extend(['-O3', '-march=native', '-DNDEBUG'])
            # Ensure GPIARRAY_ENABLE_BOUNDS_CHECKS is NOT present
            self.extra_compile_args = [arg for arg in self.extra_compile_args if arg != '-DGPIARRAY_ENABLE_BOUNDS_CHECKS']
        else:
            # Enable GPIARRAY_ENABLE_BOUNDS_CHECKS for debug builds
            self.extra_compile_args.append('-DGPIARRAY_ENABLE_BOUNDS_CHECKS')
            print(f"{Cl.OKBL}Debug mode: GPIARRAY_ENABLE_BOUNDS_CHECKS enabled.{Cl.ESC}")

        # OpenMP - COMPLETELY REWRITTEN to fix macOS issues
        # Remove ALL existing OpenMP-related flags first (more comprehensive)
        openmp_flags_to_remove = ['-fopenmp', '-Xpreprocessor', '-openmp', '/openmp']
        self.extra_compile_args = [arg for arg in self.extra_compile_args if arg not in openmp_flags_to_remove]
        
        # Remove OpenMP libraries to avoid duplicates
        openmp_libs_to_remove = ['omp', 'gomp', 'iomp5']
        self.libraries = [lib for lib in self.libraries if lib not in openmp_libs_to_remove]
        
        if platform.system() == 'Darwin':
            # On macOS with Apple Clang, use -Xpreprocessor followed by -fopenmp
            # These must be separate arguments in the list
            self.extra_compile_args.extend(['-Xpreprocessor', '-fopenmp'])
            self.libraries.append('omp')
            print(f"{Cl.OKBL}Using OpenMP for macOS (Apple Clang: -Xpreprocessor -fopenmp).{Cl.ESC}")
        elif platform.system() == 'Linux':
            # On Linux with GCC, use plain -fopenmp
            self.extra_compile_args.append('-fopenmp')
            self.libraries.append('gomp')
            print(f"{Cl.OKBL}Using OpenMP for Linux (GCC: -fopenmp).{Cl.ESC}")
        
        # macOS specific compiler environment variables and flags from make.py
        if platform.system() == 'Darwin':
            os.environ["CC"] = 'clang'
            os.environ["CXX"] = 'clang++'
            if self.options.osx_target_ver is not None:
                os.environ["MACOSX_DEPLOYMENT_TARGET"] = self.options.osx_target_ver
            else:
                os.environ["MACOSX_DEPLOYMENT_TARGET"] = '10.9'
            # Only add -Wsign-compare if not already present
            if '-Wsign-compare' not in self.extra_compile_args:
                self.extra_compile_args.append('-Wsign-compare')
    
        # Debug: Print the final OpenMP-related flags
        print(f"Final extra_compile_args (OpenMP-related): {[arg for arg in self.extra_compile_args if 'openmp' in arg.lower() or 'Xpreprocessor' in arg]}")
        print(f"Final libraries (OpenMP-related): {[lib for lib in self.libraries if lib in ['omp', 'gomp', 'iomp5']]}")


    def get_config(self):
        # Remove duplicates while preserving order (don't use set() as it reorders)
        def remove_duplicates_preserve_order(lst):
            seen = set()
            result = []
            for item in lst:
                if item not in seen:
                    seen.add(item)
                    result.append(item)
            return result
        
        return {
            'include_dirs': remove_duplicates_preserve_order(self.include_dirs),
            'libraries': remove_duplicates_preserve_order(self.libraries),
            'library_dirs': remove_duplicates_preserve_order(self.library_dirs),
            'extra_compile_args': remove_duplicates_preserve_order(self.extra_compile_args),
            'runtime_library_dirs': remove_duplicates_preserve_order(self.runtime_library_dirs)
        }


def make(GPI_PREFIX=None):
    '''Commandline interface to the make utilities.
    This script is specifically for building _PYBIND11.cpp C++ extension modules.
    '''
    print(f"{Cl.HDR}=== Starting make_gpiarray ==={Cl.ESC}")
    
    # CRITICAL: Early exit for system/redundant calls
    current_cwd = os.getcwd()
    system_indicators = [
        'site-packages/gpi_core',
        'site-packages/gpi',
        'miniforge3/envs/gpi/lib'
    ]
    
    if any(indicator in current_cwd for indicator in system_indicators):
        return SUCCESS
    
    # Load compilation cache
    compiled_cache = load_compilation_cache()
    
    # Define the project root directory where this script is located
    PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
    
    print(f"Python path: {sys.path[:3]}...") # Show first 3 entries

    parser = optparse.OptionParser()
    parser.add_option('--preprocess', dest='preprocess', default=False,
                      action="store_true", help='''Only do preprocessing to \
                              target (the resulting .o file will be \
                              preprocessed code.)''')
    parser.add_option('-w', '--suppressWarnings', dest='suppressWarnings', # This option is now largely superseded by default -w
                      default=False, action="store_true",
                      help='''Tell gcc to only display errors (default behavior now).''')
    parser.add_option('--fmt', dest='format', default=False,
                      action="store_true",
                      help="Auto-format using the astyle scripts.")
    parser.add_option('--all', dest='makeall', default=False,
                      action='store_true',
                      help="Recursively search for _PYBIND11.cpp files and attempt to" +
                      "make them (integer arg sets recursion depth).")
    parser.add_option('-r', '--rdepth', dest='makeall_rdepth', type="int",
                      default=2, # Default recursion depth to 2, similar to make.py's common usage for search
                      help="Integer arg sets recursion depth for makeall.")
    parser.add_option('--debug', dest='debug', default=False,
                      action="store_true",
                      help="Enables debug flags including GPIARRAY_ENABLE_BOUNDS_CHECKS.")
    parser.add_option('--ignore-gpirc', dest='ignore_gpirc', default=False,
                      action="store_true",
                      help="Ignore the ~/.gpirc config and gpi.config settings.")
    parser.add_option('--ignore-system-libs', dest='ignore_sys', default=False,
                      action="store_true",
                      help="Ignore the system libraries (e.g. for conda build).")
    parser.add_option('--osx-ver', dest='osx_target_ver',
                      help="Override tgt. version for OSX builds (must be '10.X').")
    parser.add_option(
        '-v', '--verbose', dest='verbose', default=False, action="store_true",
        help='''Enable verbose output from setuptools.''')
    parser.add_option(
        '-d', '--distdebug', dest='distdebug', default=False, action="store_true",
        help='''Sets DISTUTILS_DEBUG environment variable.''')

    # If no arguments provided, default to --all with depth 2
    if len(sys.argv) == 1:
        print("No arguments provided to make_gpiarray, assuming --all with depth 2...")
        options, args = parser.parse_args(['--all'])
    else:
        options, args = parser.parse_args()
    
    # Set DISTUTILS_DEBUG if requested
    if options.distdebug:
        os.environ['DISTUTILS_DEBUG'] = '1'

    # Determine targets
    targets = []
    if len(args) > 0:
        print(f"Processing explicit arguments: {args}")
        targets = packageArgs(args)
    elif options.makeall:
        if options.makeall_rdepth < 0:
            print((Cl.FAIL + "ERROR: recursion depth is set to an invalid number." + Cl.ESC))
            return ERROR_INVALID_RECURSION_DEPTH
        targets = targetWalk(options.makeall_rdepth, PROJECT_ROOT, options.ignore_gpirc, options.ignore_sys)

    if not targets:
        print((Cl.WRN + "WARNING: no _PYBIND11.cpp files found to compile." + Cl.ESC))
        return SUCCESS

    # Filter targets based on cache
    original_target_count = len(targets)
    targets = [t for t in targets if not should_skip_compilation(t['full_filename'], compiled_cache)]
    
    if len(targets) < original_target_count:
        print(f"{Cl.OKBL}Skipped {original_target_count - len(targets)} files that were recently compiled successfully.{Cl.ESC}")
    
    if not targets:
        print(f"{Cl.OKGR}All targets are up to date. Nothing to compile.{Cl.ESC}")
        return SUCCESS

    # Initialize build configuration
    build_config = BuildConfiguration(options, PROJECT_ROOT, GPI_PREFIX)
    base_compiler_settings = build_config.get_config()

    # COMPILATION LOOP
    successes = []
    failures = []
    newly_compiled = set()

    for target in targets:
        # Use context manager for safer directory changes
        with chdir(target['pth']):
            # C++ compilation (only for _PYBIND11.cpp files as per script's purpose)
            if target['ext'] == '.cpp':
                current_extra_compile_args = list(base_compiler_settings['extra_compile_args'])
                current_extra_compile_args.append('-DMOD_NAME=' + target['fn'])

                print(f"Making target: {target['fn']}")
                retcode = compile_cpp_module(
                    target['fn'],
                    [target['full_filename']],
                    list(base_compiler_settings['include_dirs']),
                    list(base_compiler_settings['libraries']),
                    list(base_compiler_settings['library_dirs']),
                    current_extra_compile_args,
                    list(base_compiler_settings['runtime_library_dirs']),
                    options.verbose
                )

                if retcode != 0:
                    failures.append(target['fn'])
                else:
                    successes.append(target['fn'])
                    # Add to cache with dependency-aware hash
                    dependency_hash = get_file_hash_with_dependencies(target['full_filename'])
                    newly_compiled.add(target['full_filename'])
                    compiled_cache[target['full_filename']] = {
                        'hash': get_file_hash(target['full_filename']),  # Keep simple hash for compatibility
                        'dependency_hash': dependency_hash,  # New dependency-aware hash
                        'timestamp': time.time(),
                        'module': target['fn'],
                        'dependencies': list(get_file_dependencies(target['full_filename']))  # Store dependencies for debugging
                    }

    # Update cache with newly compiled files
    if newly_compiled:
        save_compilation_cache(compiled_cache)

    # SUMMARY
    print(('\nSUMMARY (CPP Compilations):\n\tSUCCESSES ('+Cl.OKGR+str(len(successes))+Cl.ESC+'):'))
    for i in successes:
        print(("\t\t" + i))
    print(('\tFAILURES ('+Cl.FAIL+str(len(failures))+Cl.ESC+'):'))
    for i in failures:
        print(("\t\t" + i))

    if len(failures) > 0:
        return ERROR_FAILED_COMPILATION
    else:
        return SUCCESS

if __name__ == '__main__':
    # When run directly, GPI_PREFIX is not typically passed, so it defaults to None
    retcode = make()
    sys.exit(retcode)