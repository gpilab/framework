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

# make_pybind11.py
# Author: Guru Krishnamoorthy
# Date: 2025-Jul
#
# Build and setup script for compiling C++ extension modules (_PYBIND11.cpp) for Voxel using setuptools.
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
#   --clean              Remove all build artifacts and cache files.
#   --install            Install compiled modules to site-packages.
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
        $ ./make_pybind11.py <basename>_PYBIND11.cpp
        or
        $ ./make_pybind11.py --all
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
import shutil # For clean operations
import traceback # For detailed error reporting

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
ERROR_CLEAN_FAILED = 7
ERROR_INSTALL_FAILED = 8


# ANSI color support — enable Windows 10+ virtual terminal processing if available.
def _ansi_enabled():
    if sys.platform != 'win32':
        return True
    try:
        import ctypes
        k32 = ctypes.windll.kernel32
        handle = k32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        mode = ctypes.c_ulong()
        if k32.GetConsoleMode(handle, ctypes.byref(mode)):
            k32.SetConsoleMode(handle, mode.value | 0x0004)  # ENABLE_VIRTUAL_TERMINAL_PROCESSING
            return True
    except Exception:
        pass
    return False

_USE_COLOR = _ansi_enabled()

class Cl:
    HDR  = '\033[95m' if _USE_COLOR else ''
    OKBL = '\033[94m' if _USE_COLOR else ''
    OKGR = '\033[92m' if _USE_COLOR else ''
    WRN  = '\033[93m' if _USE_COLOR else ''
    FAIL = '\033[91m' if _USE_COLOR else ''
    ESC  = '\033[0m'  if _USE_COLOR else ''

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
    #print(f"Making target: {mod_name}")

    # Setuptools command-line arguments
    script_args = ["build_ext", "--inplace", "--force"]
    if not verbose:
        script_args.append("--quiet")
    
    # Capture stdout/stderr of the build process for better error reporting
    # setuptools itself will print, but we want to ensure any underlying compiler
    # messages are visible on failure.
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    
    # Use temporary files to capture output
    with tempfile.TemporaryFile(mode='w+') as stdout_capture, \
         tempfile.TemporaryFile(mode='w+') as stderr_capture:
        try:
            sys.stdout = stdout_capture
            sys.stderr = stderr_capture

            # Create the Extension object
            Module1 = Extension(mod_name,
                                include_dirs=include_dirs,
                                libraries=libraries,
                                library_dirs=library_dirs,
                                extra_compile_args=extra_compile_args,
                                runtime_library_dirs=runtime_library_dirs,
                                sources=sources)

            setup(name=mod_name,
                  version='0.1-dev',
                  description='Voxel C++ Extension Module',
                  ext_modules=[Module1],
                  script_args=script_args)
            print(f"{Cl.OKGR}SUCCESS: {mod_name}{Cl.ESC}")
            return SUCCESS
        except Exception as e:
            print(f"{Cl.FAIL}FAILED: {mod_name}{Cl.ESC}")
            print(f"Error details: {e}")
            
            # Print captured stdout and stderr for debugging
            stdout_capture.seek(0)
            stderr_capture.seek(0)
            print(f"\n--- Captured Build Output (stdout) ---\n{stdout_capture.read()}")
            print(f"\n--- Captured Build Output (stderr) ---\n{stderr_capture.read()}")
            traceback.print_exc() # Print Python stack trace
            return ERROR_FAILED_COMPILATION
        finally:
            sys.stdout = original_stdout
            sys.stderr = original_stderr


def packageArgs(args, working_dir=None):
    """Split path and filename info into a dictionary.
    Assumes args are full paths to .cpp files or base module names.
    """
    if working_dir is None:
        working_dir = os.getcwd()
    
    targets = []
    for arg in args:
        full_path_arg = os.path.abspath(arg)
        path_arg = os.path.dirname(full_path_arg)
        filename_arg = os.path.basename(full_path_arg)
        fn_base_arg, ext_arg = os.path.splitext(filename_arg)

        target_module_name = None
        target_pybind_file = None
        current_dir_for_search = working_dir # Use the passed working directory

        # Case 1: Argument is already a full _PYBIND11.cpp filename
        if ext_arg == '.cpp' and fn_base_arg.endswith("_PYBIND11"):
            target_pybind_file = full_path_arg
            target_module_name = fn_base_arg.replace("_PYBIND11", "")
            current_dir_for_search = path_arg # Use the directory of the explicit file
        # Case 2: Argument is a base module name (e.g., 'Grid')
        elif ext_arg == '': # No extension, meaning it might be a module base name
            # Construct the expected _PYBIND11.cpp filename in the current directory
            expected_filename = f"{fn_base_arg}_PYBIND11.cpp"
            search_path = os.path.join(current_dir_for_search, expected_filename)
            if os.path.exists(search_path):
                target_pybind_file = search_path
                target_module_name = fn_base_arg
                print(f"Found {expected_filename} for module '{fn_base_arg}'.")
            else:
                print(f"Skipping '{arg}': Could not find '{expected_filename}' in the current directory or as an explicit _PYBIND11.cpp file.")
                continue # Skip to the next arg

        if target_pybind_file:
            # Use discover_module_sources to find all .cpp files
            # The base directory for search starts from where the _PYBIND11.cpp file is found
            module_sources = discover_module_sources(target_pybind_file, base_search_dir=current_dir_for_search)

            targets.append({
                'pth': current_dir_for_search, # This should be the directory where the source files are located
                'fn': target_module_name,
                'ext': '.cpp',
                'full_filename': target_pybind_file, # Main PYBIND11 source file
                'all_sources': module_sources # List of all .cpp files for this module
            })
        elif ext_arg == '.cpp' and not fn_base_arg.endswith("_PYBIND11"):
            print(f"Skipping non-_PYBIND11.cpp file: {filename_arg}. This script only builds _PYBIND11.cpp modules.")
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

COMPILATION_CACHE_FILE = os.path.join(tempfile.gettempdir(), 'gpi_make_pybind11_cache.pkl')
BUILD_DIR_NAME = 'build' # Standard build directory name for setuptools

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
                return cache.get('compiled_files', {})
    except:
        pass
    return {}

def save_compilation_cache(compiled_files):
    """Save compilation cache to disk."""
    try:
        cache = {
            'timestamp': time.time(),
            'compiled_files': compiled_files
        }
        with open(COMPILATION_CACHE_FILE, 'wb') as f:
            pickle.dump(cache, f)
    except Exception as e:
        print(f"Warning: Could not save compilation cache: {e}")


def get_all_dependent_files(start_file, search_dirs):
    """
    Recursively finds all .hpp and .cpp files that are direct or indirect dependencies
    of the start_file, searching within specified search_dirs.
    Returns a set of absolute paths.
    """
    all_dependencies = set()
    files_to_process = [os.path.abspath(start_file)]
    processed_files = set()

    while files_to_process:
        current_file = files_to_process.pop(0)
        if current_file in processed_files:
            continue

        processed_files.add(current_file)
        all_dependencies.add(current_file)

        if not os.path.exists(current_file):
            continue

        try:
            with open(current_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            include_pattern = r'#include\s*[<"]([^>"]+)[>"]'
            includes = re.findall(include_pattern, content)

            current_file_dir = os.path.dirname(current_file)

            for include in includes:
                # Prioritize searching relative to the current file
                potential_paths = []
                # 1. Relative to the current file's directory
                potential_paths.append(os.path.abspath(os.path.join(current_file_dir, include)))
                # 2. Try common subdirectories (e.g., 'cpp/', 'include/') relative to current file's dir
                potential_paths.append(os.path.abspath(os.path.join(current_file_dir, 'cpp', include)))
                potential_paths.append(os.path.abspath(os.path.join(current_file_dir, 'include', include)))
                # 3. Try parent directories (e.g., ../include)
                potential_paths.append(os.path.abspath(os.path.join(current_file_dir, '..', include)))
                potential_paths.append(os.path.abspath(os.path.join(current_file_dir, '..', 'include', include)))


                # Add project-level search directories
                for s_dir in search_dirs:
                    # Only add if the search_dir is a real path (e.g., not from gpi.config if it's broken)
                    if os.path.exists(s_dir) and os.path.isdir(s_dir):
                        potential_paths.append(os.path.abspath(os.path.join(s_dir, include)))
                        potential_paths.append(os.path.abspath(os.path.join(s_dir, 'cpp', include)))
                        potential_paths.append(os.path.abspath(os.path.join(s_dir, 'include', include)))


                found_dependency_path = None
                for p_path in potential_paths:
                    if os.path.exists(p_path):
                        found_dependency_path = p_path
                        break
                
                # Fallback to glob for deeper search if direct path not found
                if not found_dependency_path:
                    # Glob relative to current file's directory
                    glob_pattern = os.path.join(current_file_dir, '**', include)
                    glob_results = glob.glob(glob_pattern, recursive=True)
                    if glob_results:
                        found_dependency_path = os.path.abspath(glob_results[0]) # Take the first match
                
                if found_dependency_path and found_dependency_path not in processed_files:
                    files_to_process.append(found_dependency_path)

        except Exception as e:
            print(f"Warning: Could not parse dependencies for {current_file}: {e}")
            continue
    return all_dependencies


def get_combined_hash_for_module(pybind_file_path, base_search_dirs):
    """
    Calculates a combined hash for a module, considering the _PYBIND11.cpp file,
    all directly or indirectly included .hpp files, and their corresponding .cpp files.
    """
    all_relevant_files = set()

    # Step 1: Get all files included by _PYBIND11.cpp (recursively)
    # The base_search_dirs provided here are critical for dependency resolution
    initial_dependencies = get_all_dependent_files(pybind_file_path, base_search_dirs)
    all_relevant_files.update(initial_dependencies)

    # Step 2: For each .hpp file found, check for a corresponding .cpp file
    # For each .cpp file found (either initial or inferred from .hpp),
    # also get its recursive dependencies.
    # Use a list to allow extending during iteration without issues
    files_to_scan_for_cpp_and_deps = list(all_relevant_files)
    
    # Track files already processed for their dependencies to avoid redundant calls to get_all_dependent_files
    processed_for_full_deps = set()

    # Iteratively find new .cpp files and their dependencies
    i = 0
    while i < len(files_to_scan_for_cpp_and_deps):
        current_file = files_to_scan_for_cpp_and_deps[i]
        i += 1

        if current_file in processed_for_full_deps:
            continue
        processed_for_full_deps.add(current_file)

        if current_file.endswith(('.h', '.hpp')):
            # Infer corresponding .cpp file relative to the header's directory
            base_name, _ = os.path.splitext(current_file)
            cpp_candidate = base_name + '.cpp'
            
            # Check if the .cpp candidate exists and is not already processed
            if os.path.exists(cpp_candidate) and os.path.abspath(cpp_candidate) not in all_relevant_files:
                all_relevant_files.add(os.path.abspath(cpp_candidate))
                files_to_scan_for_cpp_and_deps.append(os.path.abspath(cpp_candidate))
                
        # Also, ensure all dependencies of the current file are included for hashing
        # This will catch deeply nested dependencies that are not .cpp files themselves
        new_deps = get_all_dependent_files(current_file, base_search_dirs)
        for dep in new_deps:
            if dep not in all_relevant_files:
                all_relevant_files.add(dep)
                # Only add if it hasn't been fully processed for its own dependencies yet
                if dep not in processed_for_full_deps:
                    files_to_scan_for_cpp_and_deps.append(dep)

    # Ensure the primary _PYBIND11.cpp file is in the set
    all_relevant_files.add(os.path.abspath(pybind_file_path))


    # Generate a combined hash from the content of all relevant files
    combined_content = []
    for f_path in sorted(list(all_relevant_files)): # Sort for consistent hash
        if os.path.exists(f_path):
            try:
                with open(f_path, 'rb') as f:
                    combined_content.append(f.read())
            except Exception as e:
                # If file cannot be read, use its modification time as a fallback
                print(f"Warning: Could not read {f_path} for hashing, using mtime. Error: {e}")
                combined_content.append(str(os.path.getmtime(f_path)).encode())
        else:
            print(f"Warning: File {f_path} not found during hashing.")

    if not combined_content:
        return None # No content to hash

    return hashlib.md5(b''.join(combined_content)).hexdigest()

def discover_module_sources(pybind_file_path, base_search_dir):
    """
    Discovers all .cpp files that need to be compiled for a given _PYBIND11 module.
    This includes the _PYBIND11.cpp file itself, and any .cpp files that
    correspond to headers it (or its dependencies) include.
    """
    module_sources = set()
    files_to_process = [os.path.abspath(pybind_file_path)]
    processed_files_for_includes = set() # To avoid infinite loops on circular includes

    # These are the local directories where we expect to find module-specific sources and headers
    local_source_search_paths = [
        base_search_dir,
        os.path.join(base_search_dir, 'cpp'),
        os.path.join(base_search_dir, 'include'),
        os.path.join(base_search_dir, 'src') # Common for some project structures
    ]
    # Filter out non-existent directories
    local_source_search_paths = [p for p in local_source_search_paths if os.path.isdir(p)]

    # Add the initial _PYBIND11.cpp file as a source
    module_sources.add(os.path.abspath(pybind_file_path))

    while files_to_process:
        current_file = files_to_process.pop(0)
        
        # Avoid reprocessing files for includes if already done
        if current_file in processed_files_for_includes:
            continue
        processed_files_for_includes.add(current_file)

        if not os.path.exists(current_file):
            continue # File might have been moved/deleted

        try:
            with open(current_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            include_pattern = r'#include\s*[<"]([^>"]+)[>"]'
            includes = re.findall(include_pattern, content)
            
            current_file_dir = os.path.dirname(current_file)

            for include_name in includes:
                if os.path.isabs(include_name) or include_name.startswith('<'):
                    # Skip apparent system includes (e.g., <iostream>)
                    continue

                resolved_path = None
                # Search strategy for local includes:
                # 1. Relative to the current file's directory
                # 2. Within predefined local source search paths (e.g., base, cpp, include, src)
                # 3. Globbing as a fallback for deeper nested structures within those paths

                search_bases = [current_file_dir] + local_source_search_paths
                
                for search_base in search_bases:
                    candidate_path = os.path.abspath(os.path.join(search_base, include_name))
                    if os.path.exists(candidate_path):
                        resolved_path = candidate_path
                        break
                
                # Fallback to glob if direct path not found
                if not resolved_path:
                    for search_base in search_bases:
                        glob_pattern = os.path.join(search_base, '**', include_name)
                        glob_results = glob.glob(glob_pattern, recursive=True)
                        if glob_results:
                            resolved_path = os.path.abspath(glob_results[0])
                            break

                if resolved_path:
                    # If it's a new file (not yet processed for includes or already a module source)
                    if resolved_path not in processed_files_for_includes and resolved_path not in module_sources:
                        # Add to files_to_process if it's a header (to scan its includes)
                        if resolved_path.endswith(('.h', '.hpp')):
                            files_to_process.append(resolved_path)
                            
                        # If it's a .cpp or .c file (either directly included or corresponding to a header)
                        # add it to module sources for compilation
                        if resolved_path.endswith(('.cpp', '.c')):
                            module_sources.add(resolved_path)
                            print(f"    Discovered source file: {os.path.relpath(resolved_path, base_search_dir)}")
                            files_to_process.append(resolved_path) # Also process its includes if it has any

                    # For a header file, always try to find a corresponding .cpp or .c file
                    if resolved_path.endswith(('.h', '.hpp')):
                        base_name, _ = os.path.splitext(resolved_path)
                        # Try .cpp first, then .c
                        for ext in ['.cpp', '.c']:
                            source_candidate = base_name + ext
                            if os.path.exists(source_candidate) and source_candidate not in module_sources:
                                module_sources.add(source_candidate)
                                print(f"    Discovered corresponding C/C++ source: {os.path.relpath(source_candidate, base_search_dir)}")
                                files_to_process.append(source_candidate) # Add the source for its own dependency scan
                                break  # Only add one match

        except Exception as e:
            print(f"Warning: Could not parse includes for {current_file}: {e}")
            continue
    
    # Explicit fallback: ensure pocketfft.c is included if it exists
    # (in case the dependency discovery didn't catch it)
    for search_base in local_source_search_paths:
        pocketfft_c = os.path.join(search_base, 'pocketfft.c')
        if os.path.exists(pocketfft_c) and pocketfft_c not in module_sources:
            module_sources.add(pocketfft_c)
            print(f"    Explicitly added pocketfft.c: {os.path.relpath(pocketfft_c, base_search_dir)}")
            break
    
    # Replace pocketfft.c with pocketfft_wrapper.cpp to avoid C vs C++ compile flag issues
    new_sources = set()
    for src in module_sources:
        if src.endswith('pocketfft.c'):
            # Replace with wrapper
            wrapper_path = src.replace('pocketfft.c', 'pocketfft_wrapper.cpp')
            if os.path.exists(wrapper_path):
                new_sources.add(wrapper_path)
                print(f"    Using pocketfft_wrapper.cpp instead of pocketfft.c for C++ compilation")
            else:
                new_sources.add(src)  # Keep original if wrapper doesn't exist
        else:
            new_sources.add(src)
    
    return list(new_sources) # Return as a list for setuptools


def should_skip_compilation(target_info, cache):
    """Check if module should be skipped based on cache and dependencies of all its sources."""
    pybind_file = target_info['full_filename']
    module_base_dir = target_info['pth'] # Use the directory of the _PYBIND11.cpp as base for hash calculation

    if pybind_file in cache:
        cached_info = cache.get(pybind_file)
        if isinstance(cached_info, dict):
            # Recalculate current hash based on all sources for the module from scratch
            # This ensures any new includes or changes are caught
            current_hash = get_combined_hash_for_module(pybind_file, [module_base_dir])
            cached_hash = cached_info.get('dependency_hash')
            
            if current_hash is not None and current_hash == cached_hash:
                print(f"  Skipping {os.path.basename(pybind_file)} (unchanged with all module dependencies)")
                return True
            else:
                print(f"  Will compile {os.path.basename(pybind_file)} (module sources or dependencies changed)")
                return False
    return False


def targetWalk(recursion_depth=1, project_root=None, ignore_gpirc=False, ignore_sys=False, is_all_flag_active=False, working_dir=None):
    """
    Recurse into directories and look for _PYBIND11.cpp files to compile.
    Then, for each _PYBIND11.cpp, use dependency-based discovery to find all its sources.
    """
    if working_dir is None:
        working_dir = os.getcwd()
        
    targets = []
    # This set will now track UNIQUE absolute paths of _PYBIND11.cpp files found,
    # ensuring each module is added to the 'targets' list only once.
    unique_pybind_files_found_for_targets = set() 

    if project_root is None:
        project_root = os.path.dirname(os.path.abspath(__file__))

    # Get search directories; targetWalk now explicitly passes is_all_flag_active to get_search_directories
    unique_search_dirs = get_search_directories(project_root, ignore_gpirc, ignore_sys, is_all_flag_active, working_dir)

    print(f"Searching for _PYBIND11.cpp files in {len(unique_search_dirs)} directories:")
    for search_dir in unique_search_dirs:
        print(f"  {search_dir}")

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
                        full_pybind_path = os.path.abspath(os.path.join(path, fil))

                        # Check if this specific _PYBIND11.cpp file has already been added to targets
                        if full_pybind_path in unique_pybind_files_found_for_targets:
                            # print(f"  (Skipping duplicate discovery of {os.path.basename(full_pybind_path)})") # Optional: uncomment for verbose debug
                            continue # Skip adding this if already processed

                        unique_pybind_files_found_for_targets.add(full_pybind_path)

                        mod_name_base = os.path.splitext(fil)[0]
                        mod_name = mod_name_base.replace("_PYBIND11", "")

                        # Use the new dependency-driven discovery
                        print(f"  Discovering all sources for module '{mod_name}' (starting from {os.path.basename(full_pybind_path)})")
                        module_sources = discover_module_sources(full_pybind_path, base_search_dir=path)
                        
                        targets.append({
                            'pth': path, # The directory where the main _PYBIND11.cpp file is
                            'fn': mod_name, # Base module name (e.g., 'Test')
                            'ext': '.cpp',
                            'full_filename': full_pybind_path, # Path to the main PYBIND11 source
                            'all_sources': module_sources # List of all .cpp files for this module
                        })

    print(f"\nSUMMARY:")
    print(f"Found {len(unique_pybind_files_found_for_targets)} primary _PYBIND11.cpp files.")
    for t in targets:
        # Print only the base names for brevity in summary
        source_basenames = [os.path.basename(s) for s in t['all_sources']]
        print(f"  Module '{t['fn']}' will be built from {len(source_basenames)} source(s): {', '.join(source_basenames)}")

    return targets

# IMPORTANT FIX: `is_all_flag_active` is back as a parameter.
# This function will now correctly behave differently when `--all` is used.
def get_search_directories(project_root, ignore_gpirc, ignore_sys, is_all_flag_active=False, working_dir=None):
    """
    Collects directories where _PYBIND11.cpp files might reside.
    If is_all_flag_active is True, it restricts the search primarily to project_root and its subdirectories.
    """
    if working_dir is None:
        working_dir = os.getcwd()
        
    search_dirs = []
    # Use project_root (which will be CWD for --all) as the base for search.
    # Do NOT use os.getcwd() here directly for adding to search_dirs outside of `project_root` checks,
    # as project_root is the determined starting point for the recursive walk.

    # If --all is active, explicitly limit the search to the current project root and below.
    # This mimics the desired behavior of the old make.py for 'all' builds.
    if is_all_flag_active:
        # For --all, the primary search target is ONLY the provided project_root (which is CWD for main_make's call)
        # and its immediate relevant subdirs. We explicitly *do not* pull from gpirc/Config here for source discovery.
        search_dirs.append(project_root)
        if os.path.isdir(os.path.join(project_root, 'cpp')):
            search_dirs.append(os.path.join(project_root, 'cpp'))
        if os.path.isdir(os.path.join(project_root, 'include')):
            search_dirs.append(os.path.join(project_root, 'include'))
        if os.path.isdir(os.path.join(project_root, 'src')):
            search_dirs.append(os.path.join(project_root, 'src'))
        
        # Filter out system indicators if the project path itself contains them (unlikely but safe)
        system_indicators_for_filter = [
            '/miniforge3', '/site-packages', '/Library/Frameworks/Python.framework', '.local/lib/python'
        ]
        unique_and_filtered_dirs = []
        for d in search_dirs:
            normalized_d = os.path.abspath(d)
            if os.path.isdir(normalized_d) and \
               normalized_d not in unique_and_filtered_dirs and \
               not any(indicator in normalized_d for indicator in system_indicators_for_filter):
                unique_and_filtered_dirs.append(normalized_d)
        return unique_and_filtered_dirs


    # This block executes if is_all_flag_active is False (e.g., explicit target provided, or for clean/install
    # where broader discovery of existing modules might be needed).
    
    # Always add the current working directory first (for explicit targets)
    search_dirs.append(working_dir) # For explicit arguments, we definitely want to search the working directory.

    system_indicators = [
        '/miniforge3', '/site-packages/gpi_core', '/site-packages/gpi',
        '/Library/Frameworks/Python.framework', '.local/lib/python'
    ]
    
    # 1. From gpi.config (if available and not ignored)
    if not ignore_gpirc and 'Config' in sys.modules:
        try:
            if hasattr(Config, 'GPI_LIBRARY_PATH') and Config.GPI_LIBRARY_PATH:
                for flib_path in Config.GPI_LIBRARY_PATH:
                    if os.path.isdir(flib_path):
                        if not any(excluded in flib_path for excluded in system_indicators):
                            search_dirs.append(flib_path)
                            for usrdir in findLibrariesInPath(flib_path):
                                search_dirs.append(usrdir)
        except Exception as e:
            print(f"Warning: Could not process Config.GPI_LIBRARY_PATH from gpi.config: {e}")

    # 2. From ~/.gpirc (fallback/additional)
    if not ignore_gpirc:
        gpirc_path = os.path.expanduser('~/.gpirc')
        if os.path.exists(gpirc_path):
            try:
                with open(gpirc_path, 'r') as f:
                    for line in f:
                        if line.strip().startswith('LIB_DIRS'):
                            lib_dirs_line = line.strip().split('=', 1)
                            if len(lib_dirs_line) > 1:
                                lib_dirs = lib_dirs_line[1].strip().split(os.pathsep)
                                for lib_dir in lib_dirs:
                                    lib_dir = lib_dir.strip()
                                    excluded_patterns = [
                                        '/miniforge3', '/site-packages', '/Backup',
                                    ]
                                    if (lib_dir and os.path.isdir(lib_dir) and 
                                        not any(excluded in lib_dir for excluded in excluded_patterns)):
                                        search_dirs.append(lib_dir)
            except Exception as e:
                print(f"Warning: Could not parse ~/.gpirc: {e}")
    
    if ignore_sys:
        print("Note: '--ignore-system-libs' is true. General system library locations will be ignored for linking.")
    else:
        print("Including common system locations for library search (for dependency discovery/linking).")
        pass 

    # Remove duplicates and ensure all paths are absolute and exist (general cleanup)
    unique_search_dirs = []
    for d in search_dirs:
        normalized_d = os.path.abspath(d)
        if (os.path.isdir(normalized_d) and
            normalized_d not in unique_search_dirs):
            unique_search_dirs.append(normalized_d)
    
    return unique_search_dirs


# --- BuildConfiguration class definition starts here ---
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
            # Also common subdirectories like 'src/cpp'
            if os.path.isdir(os.path.join(src_dir, 'cpp')):
                self.include_dirs.append(os.path.join(src_dir, 'cpp'))

        # Use the passed gpi_prefix if available, otherwise check environment
        effective_gpi_prefix = self._gpi_prefix if self._gpi_prefix is not None else os.environ.get('GPI_PREFIX')

        if effective_gpi_prefix:
            print(f"Using GPI_PREFIX: {effective_gpi_prefix}")
            self.include_dirs.append(os.path.join(effective_gpi_prefix, 'include', 'eigen3'))
            self.include_dirs.append(os.path.join(effective_gpi_prefix, 'include'))
            # Ensure GPI's own include directory is added if it's separate
            gpi_module_include = os.path.join(gpi_dir, 'include')
            if os.path.isdir(gpi_module_include):
                self.include_dirs.append(gpi_module_include)

            if platform.system() == 'Windows':
                self.include_dirs.append(os.path.join(effective_gpi_prefix, 'Library/include'))
            
            self.library_dirs.append(os.path.join(effective_gpi_prefix, 'lib'))
            if platform.system() == 'Windows':
                self.library_dirs.append(os.path.join(effective_gpi_prefix, 'Library/lib'))
        else:
            print(f"{Cl.WRN}Warning: GPI_PREFIX not explicitly provided or found in environment. This may affect finding core GPI libraries.{Cl.ESC}")


        # Conda environment paths (Updated to support Eigen3)
        if 'CONDA_PREFIX' in os.environ:
            conda_env_path = os.environ['CONDA_PREFIX']
            print(f"CONDA_PREFIX detected: {conda_env_path}")
            
            # Conda paths differ slightly between Windows and Unix
            if platform.system() == 'Windows':
                self.include_dirs.append(os.path.join(conda_env_path, 'Library', 'include'))
                self.include_dirs.append(os.path.join(conda_env_path, 'Library', 'include', 'eigen3')) # Eigen3 headers
                self.library_dirs.append(os.path.join(conda_env_path, 'Library', 'lib'))
                self.runtime_library_dirs.append(os.path.join(conda_env_path, 'Library', 'lib'))
            else:
                self.include_dirs.append(os.path.join(conda_env_path, 'include'))
                self.include_dirs.append(os.path.join(conda_env_path, 'include', 'eigen3')) # Eigen3 headers
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
                        # Add as general search path, specific filtering might be needed
                        self.include_dirs.append(flib_path) # Might contain headers directly
                        self.library_dirs.append(flib_path) # Might contain libs directly
                        for usrdir in findLibrariesInPath(flib_path): # Also search within python packages
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
            
            # Add common system library paths explicitly if not ignored
            if platform.system() != 'Windows': # Unix-like systems
                if '/usr/include' not in self.include_dirs:
                    self.include_dirs.append('/usr/include')
                if '/usr/local/include' not in self.include_dirs:
                    self.include_dirs.append('/usr/local/include')

                if '/usr/lib' not in self.library_dirs:
                    self.library_dirs.append('/usr/lib')
                if '/usr/local/lib' not in self.library_dirs:
                    self.library_dirs.append('/usr/local/lib')

                # macOS specific for malloc.h if needed (from make.py)
                if platform.system() == 'Darwin':
                    if '/usr/include/malloc' not in self.include_dirs:
                        self.include_dirs.append('/usr/include/malloc')


    def _apply_compiler_flags(self):
        """Apply standard, optimization, debug, and OpenMP flags."""
        is_msvc = platform.system() == 'Windows'

        if is_msvc:
            # MSVC flag set (/std:c++20, /EHsc required by pybind11)
            self.extra_compile_args = [a for a in self.extra_compile_args
                                       if not (a.startswith('/std:') or a.startswith('-std='))]
            self.extra_compile_args.extend(['/std:c++20', '/EHsc'])

            # Warning level
            self.extra_compile_args = [a for a in self.extra_compile_args
                                       if not (a in ('/W0','/W1','/W2','/W3','/W4','/Wall') or
                                               a.startswith('-W') or a == '-w')]
            self.extra_compile_args.append('/W2')

            if not self.options.debug:
                self.extra_compile_args.extend(['/O2', '/fp:fast', '/DNDEBUG'])
                self.extra_compile_args = [a for a in self.extra_compile_args
                                           if a != '/DGPIARRAY_ENABLE_BOUNDS_CHECKS']
            else:
                self.extra_compile_args.extend(['/Od', '/Zi', '/DGPIARRAY_ENABLE_BOUNDS_CHECKS'])
                print(f"{Cl.OKBL}Debug mode: GPIARRAY_ENABLE_BOUNDS_CHECKS enabled.{Cl.ESC}")

            # OpenMP on MSVC
            for flag in ['-fopenmp', '-Xpreprocessor', '-openmp', '/openmp']:
                self.extra_compile_args = [a for a in self.extra_compile_args if a != flag]
            self.libraries = [l for l in self.libraries if l not in ('omp', 'gomp', 'iomp5')]
            self.extra_compile_args.append('/openmp')
            print(f"{Cl.OKBL}Using OpenMP for Windows (MSVC: /openmp).{Cl.ESC}")

        else:
            # GCC / Clang flag set
            self.extra_compile_args = [a for a in self.extra_compile_args if not a.startswith('-std=c++')]
            self.extra_compile_args.append('-std=c++20')

            self.extra_compile_args = [a for a in self.extra_compile_args
                                       if not (a == '-w' or a.startswith('-W'))]
            self.extra_compile_args.extend(['-Wall', '-Wextra', '-Wpedantic', '-Wno-unused-result'])
            if platform.system() == 'Darwin':
                self.extra_compile_args.append('-Wsign-compare')

            if not self.options.debug:
                self.extra_compile_args.extend([
                    '-O3', '-march=native', '-DNDEBUG',
                    '-ffast-math', '-fcx-limited-range',
                ])
                self.extra_compile_args = [a for a in self.extra_compile_args
                                           if a != '-DGPIARRAY_ENABLE_BOUNDS_CHECKS']
            else:
                self.extra_compile_args.extend(['-O0', '-g', '-DGPIARRAY_ENABLE_BOUNDS_CHECKS'])
                print(f"{Cl.OKBL}Debug mode: GPIARRAY_ENABLE_BOUNDS_CHECKS enabled, -O0 -g applied.{Cl.ESC}")

            # OpenMP
            for flag in ['-fopenmp', '-Xpreprocessor', '-openmp', '/openmp']:
                self.extra_compile_args = [a for a in self.extra_compile_args if a != flag]
            self.libraries = [l for l in self.libraries if l not in ('omp', 'gomp', 'iomp5')]

            if platform.system() == 'Darwin':
                self.extra_compile_args.extend(['-Xpreprocessor', '-fopenmp'])
                self.libraries.append('omp')
                print(f"{Cl.OKBL}Using OpenMP for macOS (Apple Clang: -Xpreprocessor -fopenmp).{Cl.ESC}")
            elif platform.system() == 'Linux':
                self.extra_compile_args.append('-fopenmp')
                self.libraries.append('gomp')
                print(f"{Cl.OKBL}Using OpenMP for Linux (GCC: -fopenmp).{Cl.ESC}")

            # macOS compiler environment
            if platform.system() == 'Darwin':
                os.environ["CC"] = 'clang'
                os.environ["CXX"] = 'clang++'
                if self.options.osx_target_ver is not None:
                    os.environ["MACOSX_DEPLOYMENT_TARGET"] = self.options.osx_target_ver
                else:
                    os.environ["MACOSX_DEPLOYMENT_TARGET"] = '10.9'


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


def do_clean(current_clean_root):
    """Removes all build artifacts and cache files."""
    print(f"{Cl.HDR}=== Cleaning Build Artifacts ==={Cl.ESC}")
    
    # We want clean to operate within the provided clean root directory.

    # Remove standard setuptools build directories within current_clean_root
    build_dirs_to_remove = [
        os.path.join(current_clean_root, BUILD_DIR_NAME), # 'build/'
        os.path.join(current_clean_root, 'dist'),
    ]
    
    # Clean up .egg-info directories within current_clean_root
    for egg_info_dir in glob.glob(os.path.join(current_clean_root, '*.egg-info')):
        build_dirs_to_remove.append(egg_info_dir)
    
    # Also look for build directories inside python packages within current_clean_root
    for root, dirs, files in os.walk(current_clean_root):
        if '__init__.py' in files: # This is a Python package
            if BUILD_DIR_NAME in dirs:
                build_dirs_to_remove.append(os.path.join(root, BUILD_DIR_NAME))
    
    # Remove compiled .so/.pyd files from source directories (from --inplace builds)
    # This specifically targets files within the current_clean_root's hierarchy.
    
    # Use get_search_directories with is_all_flag_active=True to limit source discovery for clean
    primary_pybind_files_for_clean = set()
    clean_search_paths = get_search_directories(current_clean_root,
                                                ignore_gpirc=False, # Use default config for finding where things *might* be
                                                ignore_sys=False,   # Use default config for finding where things *might* be
                                                is_all_flag_active=True, # THIS IS KEY FOR LOCAL CLEAN SCOPE
                                                working_dir=current_clean_root)

    for base_dir_for_clean_search in clean_search_paths:
        for path, _, fn_list in os.walk(base_dir_for_clean_search):
            for fil in fn_list:
                if fil.endswith("_PYBIND11.cpp"):
                    primary_pybind_files_for_clean.add(os.path.abspath(os.path.join(path, fil)))

    for pybind_file in primary_pybind_files_for_clean:
        module_dir = os.path.dirname(pybind_file)
        mod_name_base = os.path.splitext(os.path.basename(pybind_file))[0]
        mod_name = mod_name_base.replace("_PYBIND11", "")
        
        # Possible compiled file names (e.g., Module.cpython-39-darwin.so)
        glob_pattern = os.path.join(module_dir, f"{mod_name}*.so")
        for so_file in glob.glob(glob_pattern):
            try:
                os.remove(so_file)
                print(f"Removed inplace module: {so_file}")
            except OSError as e:
                print(f"{Cl.WRN}Warning: Could not remove {so_file}: {e}{Cl.ESC}")

        # Also for Windows .pyd
        glob_pattern_pyd = os.path.join(module_dir, f"{mod_name}*.pyd")
        for pyd_file in glob.glob(glob_pattern_pyd):
            try:
                os.remove(pyd_file)
                print(f"Removed inplace module: {pyd_file}")
            except OSError as e:
                print(f"{Cl.WRN}Warning: Could not remove {pyd_file}: {e}{Cl.ESC}")


    for d in set(build_dirs_to_remove): # Use set to remove duplicates
        if os.path.exists(d):
            try:
                if os.path.isdir(d):
                    shutil.rmtree(d)
                    print(f"Removed directory: {d}")
                else: # For *.egg-info glob result might be a file
                    os.remove(d)
                    print(f"Removed file: {d}")
            except OSError as e:
                print(f"{Cl.FAIL}Error removing {d}: {e}{Cl.ESC}")
                return ERROR_CLEAN_FAILED

    # Remove compilation cache file
    if os.path.exists(COMPILATION_CACHE_FILE):
        try:
            os.remove(COMPILATION_CACHE_FILE)
            print(f"Removed cache file: {COMPILATION_CACHE_FILE}")
        except OSError as e:
            print(f"{Cl.FAIL}Error removing cache file {COMPILATION_CACHE_FILE}: {e}{Cl.ESC}")
            return ERROR_CLEAN_FAILED
    
    print(f"{Cl.OKGR}Clean operation complete.{Cl.ESC}")
    return SUCCESS

def do_install():
    """Installs compiled modules to Python's site-packages."""
    print(f"{Cl.HDR}=== Installing Voxel Modules ==={Cl.ESC}")
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # For installation, we generally want to discover ALL modules regardless of CWD,
        # so is_all_flag_active should be False here to allow reading from gpi.config etc.
        all_potential_targets = targetWalk(recursion_depth=2, project_root=script_dir,
                                           ignore_gpirc=False, ignore_sys=False, is_all_flag_active=False) # Pass False here for broad search for install

        if not all_potential_targets:
            print(f"{Cl.WRN}No modules found to install.{Cl.ESC}")
            return SUCCESS

        ext_modules_to_install = []
        for target in all_potential_targets:
            ext_modules_to_install.append(
                Extension(
                    name=target['fn'],
                    sources=target['all_sources']
                )
            )
        
        # Configure build for install (similar to compile, but just names)
        # Use a dummy options object as BuildConfiguration expects it
        dummy_options = optparse.Values()
        dummy_options.debug = False # Assume non-debug install
        dummy_options.osx_target_ver = None # Let it default
        dummy_options.ignore_gpirc = False
        dummy_options.ignore_sys = False
        
        install_build_config = BuildConfiguration(dummy_options, script_dir)
        install_settings = install_build_config.get_config()
        
        print("Running setuptools install command...")
        # Use subprocess to run 'setup.py install' as a separate process
        # This is generally safer than calling setup() directly multiple times
        # in the same script for different commands ('build_ext' vs 'install').
        
        # Prepare the command. We need to locate the actual setup.py relative to this script.
        setup_script_path = os.path.abspath(__file__) # Assume make_pybind11.py IS the setup script for now

        command = [
            sys.executable, # Use the current python interpreter
            setup_script_path,
            "install",
            "--force", # Force reinstall even if already present
            "--record", tempfile.mktemp() # Record installed files for potential uninstall (basic)
        ]
        
        # Add include/lib/compile args to environment for subprocess
        env = os.environ.copy()
        env['CFLAGS'] = ' '.join(install_settings['extra_compile_args'])
        env['LDFLAGS'] = ' '.join([f"-L{d}" for d in install_settings['library_dirs']])
        env['LDFLAGS'] += ' ' + ' '.join([f"-l{l}" for l in install_settings['libraries']])
        env['CPPFLAGS'] = ' '.join([f"-I{d}" for d in install_settings['include_dirs']])

        # For runtime library paths, these are often handled by the linker during build,
        # but could be added to LDFLAGS as well.
        if install_settings['runtime_library_dirs']:
            if platform.system() == 'Darwin':
                rpath_flags = ' '.join([f"-Wl,-rpath,{d}" for d in install_settings['runtime_library_dirs']])
                env['LDFLAGS'] += ' ' + rpath_flags
            elif platform.system() == 'Linux':
                rpath_flags = ' '.join([f"-Wl,-rpath={d}" for d in install_settings['runtime_library_dirs']])
                env['LDFLAGS'] += ' ' + rpath_flags

        print(f"Executing: {' '.join(command)}")
        process = subprocess.run(command, capture_output=True, text=True, env=env)

        if process.returncode == 0:
            print(f"{Cl.OKGR}Installation successful.{Cl.ESC}")
            print("\n--- Installation Output (stdout) ---\n", process.stdout)
            print("\n--- Installation Output (stderr) ---\n", process.stderr)
            return SUCCESS
        else:
            print(f"{Cl.FAIL}Installation FAILED.{Cl.ESC}")
            print("\n--- Installation Output (stdout) ---\n", process.stdout)
            print("\n--- Installation Output (stderr) ---\n", process.stderr)
            return ERROR_INSTALL_FAILED

    except Exception as e:
        print(f"{Cl.FAIL}Installation encountered an exception: {e}{Cl.ESC}")
        traceback.print_exc()
        return ERROR_INSTALL_FAILED


def make(GPI_PREFIX=None):
    '''Commandline interface to the make utilities.
    This script is specifically for building _PYBIND11.cpp C++ extension modules.
    '''
    print(f"{Cl.HDR}=== Starting make_pybind11 ==={Cl.ESC}")
    
    # Capture the current working directory at the start, similar to original make.py
    # This ensures consistent behavior regardless of how many times this script is called
    CWD = os.path.realpath('.')
    
    # Define the project root directory where this script is located.
    # This is typically where make_pybind11.py itself resides.
    SCRIPT_DIR_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
    
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
                      help="Ignore the ~/.gpirc and gpi.config settings.")
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
    parser.add_option('--clean', dest='clean', default=False,
                      action="store_true",
                      help="Remove all build artifacts and cache files.")
    parser.add_option('--install', dest='install', default=False,
                      action="store_true",
                      help="Install compiled modules to Python's site-packages.")
    parser.add_option('--force', dest='force', default=False,
                      action="store_true",
                      help="Force rebuild of all modules, ignoring cache.")


    # Parse arguments
    options, args = parser.parse_args()
    
    # Handle 'clean' command first. It should operate on the CWD.
    if options.clean:
        # Pass the current working directory as the "project_root" for cleaning scope
        return do_clean(CWD)

    # Handle 'install' command
    if options.install:
        # For install, the project root is where the script is, as it affects where things are installed from globally
        return do_install()

    # Set DISTUTILS_DEBUG if requested
    os.environ['DISTUTILS_DEBUG'] = '1' if options.distdebug else os.environ.get('DISTUTILS_DEBUG', '')

    # Load compilation cache
    compiled_cache = load_compilation_cache()

    # Determine targets
    targets = []
    
    # Determine the root for the search based on command-line arguments
    search_root_for_target_discovery = None
    is_all_active_for_target_search = False


    if len(args) > 0:
        print(f"Processing explicit arguments: {args}")
        targets = packageArgs(args, CWD) 
        # For explicit targets, the search_root for dependency hashing is simply the CWD for contextual search.
        search_root_for_target_discovery = CWD 
                                                       
    elif options.makeall:
        if options.makeall_rdepth < 0:
            print((Cl.FAIL + "ERROR: recursion depth is set to an invalid number." + Cl.ESC))
            return ERROR_INVALID_RECURSION_DEPTH
        
        # When --all is specified, the search root is explicitly the current working directory.
        search_root_for_target_discovery = CWD
        is_all_active_for_target_search = True # This flag restricts get_search_directories
        
        print(f"Recursively searching for modules from: {search_root_for_target_discovery}")
        targets = targetWalk(options.makeall_rdepth, search_root_for_target_discovery,
                             options.ignore_gpirc, options.ignore_sys,
                             is_all_flag_active=is_all_active_for_target_search, working_dir=CWD)
    else: # No args and no --all flag, default to --all with depth 2
        print("No arguments provided to make_pybind11, assuming --all with depth 2...")
        
        # Default --all behavior means search from current working directory.
        search_root_for_target_discovery = CWD
        is_all_active_for_target_search = True # This flag restricts get_search_directories
        
        print(f"Recursively searching for modules from: {search_root_for_target_discovery}")
        targets = targetWalk(2, search_root_for_target_discovery,
                             options.ignore_gpirc, options.ignore_sys,
                             is_all_flag_active=is_all_active_for_target_search, working_dir=CWD)


    if not targets:
        print((Cl.WRN + "WARNING: no _PYBIND11.cpp files found to compile." + Cl.ESC))
        return SUCCESS
    
    # # --- DEDUPLICATION LOGIC ---
    # # This ensures that even if targetWalk finds the same module multiple times (e.g., due to symlinks or overlapping paths),
    # # it is only processed once in the compilation loop.
    # deduplicated_targets = []
    # seen_full_filenames = set()
    # for target in targets:
    #     if target['full_filename'] not in seen_full_filenames:
    #         deduplicated_targets.append(target)
    #         seen_full_filenames.add(target['full_filename'])
    # targets = deduplicated_targets
    # print(f"Found {len(targets)} unique modules after deduplication.") # Debug print for final count
    # # --- END DEDUPLICATION LOGIC ---

    # Filter targets based on cache
    original_target_count = len(targets) # This count is now based on unique targets

    # If explicit arguments were provided, force rebuild for those specific targets.
    if len(args) > 0:
        print(f"{Cl.WRN}Explicit targets provided. Forcing rebuild for specified modules.{Cl.ESC}")
        # No filtering by cache when explicit targets are given
    elif options.force:
        print(f"{Cl.WRN}Force rebuild requested. Ignoring cache for all modules.{Cl.ESC}")
        # No filtering by cache when --force is specified
    else:
        # If no explicit arguments and no --force (e.g., --all was used), then filter by cache.
        targets = [t for t in targets if not should_skip_compilation(t, compiled_cache)]

        if len(targets) < original_target_count:
            print(f"{Cl.OKBL}Skipped {original_target_count - len(targets)} modules that are up-to-date.{Cl.ESC}")

        if not targets:
            print(f"{Cl.OKGR}All targets are up to date. Nothing to compile.{Cl.ESC}")
            return SUCCESS

    # Initialize build configuration using SCRIPT_DIR_PROJECT_ROOT for general paths.
    # Note: search_root_for_target_discovery is for *source discovery*,
    # SCRIPT_DIR_PROJECT_ROOT is the base for *compiler paths* (like including GPI's own headers if make_pybind11.py is part of GPI).
    build_config = BuildConfiguration(options, SCRIPT_DIR_PROJECT_ROOT, GPI_PREFIX)
    base_compiler_settings = build_config.get_config()

    # COMPILATION LOOP
    successes = []
    failures = []
    # Store primary _PYBIND11.cpp path and its new hash for caching
    newly_compiled_module_info = {}

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
                    list(target['all_sources']), # Pass the list of all sources
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
                    # Calculate and store the combined hash for the entire module's sources
                    combined_module_hash = get_combined_hash_for_module(target['full_filename'], [target['pth']])
                    newly_compiled_module_info[target['full_filename']] = {
                        'hash': get_file_hash(target['full_filename']),  # Simple hash for main file (for quick checks)
                        'dependency_hash': combined_module_hash,  # Comprehensive hash for the whole module
                        'timestamp': time.time(),
                        'module': target['fn'],
                        'all_sources_compiled': target['all_sources'] # Store all sources that were compiled
                    }

    # Update cache with newly compiled files
    if newly_compiled_module_info:
        # Merge newly compiled info with existing cache
        compiled_cache.update(newly_compiled_module_info)
        save_compilation_cache(compiled_cache)

    # SUMMARY
    print(('\nSUMMARY (PYBIND11 Compilations):\n\tSUCCESSES ('+Cl.OKGR+str(len(successes))+Cl.ESC+'):'))
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