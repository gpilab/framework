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
#    MAKES NO WARRANTY AND HAS NO LIABILITY ARISING FROM ANY USE OF THE
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

from gpi.config import Config

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
def compile(mod_name, include_dirs=[], libraries=[], library_dirs=[],
            extra_compile_args=[], runtime_library_dirs=[]):

    print(("Making target: " + mod_name))

    # do usual generic module setup
    # NOT: 'mod_name' must have an init<name>
    # function defined in the .cpp code.
    Module1 = Extension(mod_name,
                        # define_macros = [('MAJOR_VERSION',
                        # '1'),('MINOR_VERSION', '0')],
                        include_dirs=list(set(include_dirs)),
                        libraries=list(set(libraries)),
                        library_dirs=list(set(library_dirs)),
                        extra_compile_args=list(set(extra_compile_args)),
                        runtime_library_dirs=list(set(runtime_library_dirs)),
                        sources=[mod_name + '_PyMOD.cpp'])

    # run the setup() function
    try:
        setup(name=mod_name,
              version='0.1-dev',
              description='A kcii library of algorithms and methods.',
              ext_modules=[Module1],
              script_args=["build_ext", "--inplace", "--force"])
    except:
        print((sys.exc_info()))
        print(("FAILED: " + mod_name))
        return 1

    print(("SUCCESS: " + mod_name))
    return 0


def packageArgs(args):
    """Split path and filename info into a dictionary.
    """
    cwd = os.getcwd()
    targets = []
    for arg in args:
        fn = os.path.splitext(os.path.basename(arg))[0]
        ext = os.path.splitext(os.path.basename(arg))[1]
        dn = os.path.dirname(arg)
        targets.append({'pth': cwd + '/' + dn, 'fn': fn, 'ext': ext})
    return targets

def isPythonPackageDir(path):
    return os.path.isfile(str(path)+'/__init__.py')

def findLibraries(basepath):
    # TODO: this searching should be combined with the search in library.py and
    # unified in config.py since they both need to know which libraries are
    # present.

    # if the basepath IS the library directory
    if isPythonPackageDir(basepath):
        return [basepath]

    # check for subdirectories
    libs = []
    for p in os.listdir(basepath):
        subdir = os.path.join(basepath,p)
        if os.path.isdir(subdir):
            if isPythonPackageDir(subdir):
                libs.append(subdir)
    return libs

def targetWalk(recursion_depth=1):
    """Recurse into directories and look for .cpp files to compile.
    TODO: check if the file is a valid python module.
    """
    targets = []
    ipath = os.getcwd()
    ocnt = ipath.count('/')
    for path, dn, fn in os.walk(ipath):
        if path.count('/') - ocnt <= recursion_depth:
            if len(fn):
                for fil in fn:

                    # only attempt _PyMOD.cpp
                    if fil.endswith(".cpp"):
                        if fil.endswith("_PyMOD.cpp"):
                            fn = os.path.splitext(fil)[0]
                            ext = os.path.splitext(fil)[1]
                            targets.append({'pth': path, 'fn': fn, 'ext': ext})

                    # byte-compile all .py files
                    if fil.endswith(".py"):
                        fn = os.path.splitext(fil)[0]
                        ext = os.path.splitext(fil)[1]
                        targets.append({'pth': path, 'fn': fn, 'ext': ext})

    return targets


def makePy(basename, ext, fmt=False, check_fmt=None):

    if check_fmt is None:
        check_fmt = []

    target = [basename, ext]

    # AUTOPEP8
    if fmt:
        try:
            import autopep8
            print(("\nFound: autopep8 " + str(autopep8.__version__) + "..."))
            print(("Reformatting Python script: " + "".join(target)))
            os.system('autopep8 -i --max-line-length 256 ' + "".join(target))
        except:
            print("Failed to perform auto-formatting \
                with \'autopep8\'. Do you have it installed?")

    if 'pep8' in check_fmt:
        # PEP8
        try:
            import pep8
            print(("\nFound: pep8 " + str(pep8.__version__) + "..."))
            print(("Checking Python script: " + "".join(target)))
            print(("pep8 found these problems with your code, START" + Cl.WRN))
            os.system('pep8 --count --statistics --show-source '
                      + "".join(target))
            print((Cl.ESC + "pep8 END"))
        except:
            print("Failed to perform check with \'pep8\'. Do you have it installed?")

    if 'pyflakes' in check_fmt:
        # PYFLAKES
        try:
            import pyflakes
            print(("\nFound: pyflakes " + str(pyflakes.__version__) + "..."))
            print(("Checking Python script: " + "".join(target)))
            print(("pyflakes found these problems with your code, START" + Cl.FAIL))
            os.system('pyflakes ' + "".join(target))
            print((Cl.ESC + "pyflakes END"))
        except:
            print("Failed to perform check with \'pyflakes\'. Do you have it installed?")

    # FORCE COMPILE
    try:
        print('\nAttemping py_compile...')
        py_compile.compile(''.join(target), doraise=True)
        print('py_compile END')
        print(('\nSUCCESS: '+''.join(target)))
        return 0
    except:
        print((Cl.FAIL + str(traceback.format_exc()) + Cl.ESC))
        print('py_compile END')
        print(('\nFAILED: '+''.join(target)))
        return 1


def make(GPI_PREFIX=None):
    '''Commandline interface to the make utilities.
    '''

    CWD = os.path.realpath('.')

    # LIBRARIES, INCLUDES, ENV-VARS
    include_dirs = []
    libraries = []
    library_dirs = []
    extra_compile_args = []  # ['--version']
    runtime_library_dirs = []

    import pathlib
    GPI_DIR = pathlib.Path(__file__).parent.resolve()
    print("Adding GPI include directory")
    if GPI_PREFIX is not None:
        include_dirs.append(os.path.join(GPI_PREFIX, 'include', 'eigen3'))
        include_dirs.append(os.path.join(GPI_PREFIX, 'include'))
        include_dirs.append(os.path.join(GPI_DIR, 'include'))
        if platform.system() == 'Windows':
            include_dirs.append(os.path.join(GPI_PREFIX, 'Library/include'))

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

    # debug the distutils setup()
    if options.distdebug:
        os.environ['DISTUTILS_DEBUG'] = '1'

    # gather args and their path info
    targets = None
    if len(args):
        targets = packageArgs(args)

    # gather all _PyMOD.cpp and .py files
    # supersedes 'args' if present.
    if options.makeall:
        if options.makeall_rdepth < 0:
            print((Cl.FAIL + "ERROR: recursion depth is set to an invalid number." + Cl.ESC))
            sys.exit(ERROR_INVALID_RECURSION_DEPTH)
        targets = targetWalk(options.makeall_rdepth)

    if targets is None:
        print((Cl.FAIL + "ERROR: no targets specified." + Cl.ESC))
        sys.exit(ERROR_NO_VALID_TARGETS)

    default_cpp = True
    if options.ignore_gpirc:
        print('Ignoring the ~/.gpirc...')
    else:
    # USER MAKE config
        if (len(Config.MAKE_CFLAGS) + len(Config.MAKE_LIBS) + len(Config.MAKE_INC_DIRS) + len(Config.MAKE_LIB_DIRS)) > 0:
            print("Adding USER include dirs")
            # add user libs
            libraries += Config.MAKE_LIBS
            include_dirs += Config.MAKE_INC_DIRS
            library_dirs += Config.MAKE_LIB_DIRS
            extra_compile_args += Config.MAKE_CFLAGS
        if any("c++" in cflag for cflag in Config.MAKE_CFLAGS):
            default_cpp = False

    # Anaconda environment includes
    # includes FFTW and eigen
    print("Adding Anaconda lib and inc dirs...")
    if platform.system() == 'Windows':
        library_dirs += [os.path.join(GPI_PREFIX, 'Library/lib')]
    else:
        library_dirs += [os.path.join(GPI_PREFIX, 'lib')]
    include_dirs += [numpy.get_include()]

    # GPI library dirs
    print("Adding GPI library dirs")
    # add libs from library paths
    found_libs = {}
    search_dirs = []
    if not options.ignore_gpirc:
        print("Adding library paths from .gpirc file")
        search_dirs += Config.GPI_LIBRARY_PATH
    elif options.ignore_sys:
        print("Adding self as a library path. No other node libraries will be used")
        search_dirs += [CWD] # 
    else:
        # resort to searching the CWD for libraries
        # -if the make is being invoked on a PyMOD is reasonable to assume there
        # is a library that contains this file potentially 2 levels up.
        print("Looking two levels up from current working directory for node library files")
        search_dirs = [CWD, os.path.realpath(CWD+'/../../')]

    for flib in search_dirs:
        if os.path.isdir(flib): # skip default config if dirs dont exist
            for usrdir in findLibraries(flib):
                p = os.path.dirname(usrdir)
                b = os.path.basename(usrdir)

                if (b in list(found_libs.keys())) and not (p in list(found_libs.values())):
                    print((Cl.FAIL + "ERROR: \'" + str(b) + "\' libraray conflict:"+Cl.ESC))
                    print(("\t "+os.path.join(found_libs[b],b)))
                    print(("\t "+os.path.join(p,b)))
                    sys.exit(ERROR_LIBRARY_CONFLICT)

                msg = "\tGPI_LIBRARY_PATH \'"+str(p)+"\' for lib \'"+str(b)+"\'"
                include_dirs += [os.path.dirname(usrdir)]
                found_libs[b] = p
                print(msg)

    if len(list(found_libs.keys())) == 0:
        print((Cl.WRN + "WARNING: No GPI libraries found!\n" + Cl.ESC))

    if options.preprocess:
        extra_compile_args.append('-E')

    if options.suppressWarnings:
        extra_compile_args.append('-w')

    # debug pyfi arrays
    if options.debug:
        print("Turning on PyFI Array Debug")
        extra_compile_args += ['-DPYFI_ARRAY_DEBUG']

    # fftw_threads is included in the main lib file on Windows
    if platform.system() == 'Windows':
        libraries += ['fftw3', 'fftw3f']
    else:
        libraries += ['fftw3_threads', 'fftw3', 'fftw3f_threads', 'fftw3f']

    # POSIX THREADS
    # this location is the same for Ubuntu and OSX
    print("Adding POSIX-Threads lib")
    if platform.system() == 'Windows':
        libraries += ['pthreads']
    else:
        libraries += ['pthread']
    if not options.ignore_sys:
        print("Adding POSIX-Threads lib")
        include_dirs += ['/usr/include']
        library_dirs += ['/usr/lib']

    # The intel libs and extra compile flags are different between linux and OSX
    if platform.system() == 'Linux':
        pass

    elif platform.system() == 'Darwin':  # OSX

        os.environ["CC"] = 'clang'
        os.environ["CXX"] = 'clang++'

        # force only x86_64
        os.environ["ARCHFLAGS"] = '-arch x86_64'

        # force 10.9 compatibility unless override is passed
        if options.osx_target_ver is not None:
            os.environ["MACOSX_DEPLOYMENT_TARGET"] = options.osx_target_ver
        else:
            os.environ["MACOSX_DEPLOYMENT_TARGET"] = '10.9'

        # for malloc.h
        if not options.ignore_sys:
            include_dirs += ['/usr/include/malloc']

        # default g++
        extra_compile_args += ['-Wsign-compare']

        # unsupported g++
        #extra_compile_args += ['-Wuninitialized']

        # warn about implicit down casting
        #extra_compile_args += ['-Wshorten-64-to-32']

    # COMPILE
    successes = []
    failures = []
    py_successes = []
    py_failures = []
    for target in targets:

        os.chdir(target['pth'])

        # PYTHON regression, error checking, pep8
        if target['ext'] == '.py':
            retcode = makePy(target['fn'], target['ext'],
                             fmt=options.format,
                             check_fmt=options.check_format)

            if retcode != 0:
                py_failures.append(target['fn'])
            else:
                py_successes.append(target['fn'])

        else:  # CPP compilation

            # ASTYLE
            if options.format:
                try:
                    print("\nAstyle...")
                    print("Reformatting CPP Code: " + target['fn'] + target['ext'])
                    # TODO: astyle might not be in the path even if on the system
                    os.system('astyle -A1 -S -w -c -k3 -b -H -U -C '
                              + target['fn'] + target['ext'])
                    continue  # don't proceed to compile
                except:
                    print("Failed to perform auto-formatting with \'astyle\'. Do you have it installed?")
                    sys.exit(ERROR_EXTERNAL_APP)

            if default_cpp:
                extra_compile_args.append('-std=c++11')

            mod_name = target['fn'].split("_PyMOD")[0]
            extra_compile_args.append('-DMOD_NAME=' + mod_name)

            retcode = compile(
                mod_name, include_dirs, libraries, library_dirs,
                extra_compile_args, runtime_library_dirs)

            extra_compile_args.pop()  # remove MOD_NAME for the next target

            if retcode != 0:
                failures.append(target['fn'])
            else:
                successes.append(target['fn'])

    show_summary = len(py_successes) + len(py_failures) + len(successes) + len(failures)

    # Py Summary
    if show_summary > 1:
        print(('\nSUMMARY (Py Compilations):\n\tSUCCESSES ('+Cl.OKGR+str(len(py_successes))+Cl.ESC+'):'))
        for i in py_successes:
            print(("\t\t" + i))
        print(('\tFAILURES ('+Cl.FAIL+str(len(py_failures))+Cl.ESC+'):'))
        for i in py_failures:
            print(("\t\t" + i))

    # CPP Summary
    if show_summary > 1:
        print(('\nSUMMARY (CPP Compilations):\n\tSUCCESSES ('+Cl.OKGR+str(len(successes))+Cl.ESC+'):'))
        for i in successes:
            print(("\t\t" + i))
        print(('\tFAILURES ('+Cl.FAIL+str(len(failures))+Cl.ESC+'):'))
        for i in failures:
            print(("\t\t" + i))

    # ON FAILURE
    if (len(py_failures) + len(failures)) > 0:
        sys.exit(ERROR_FAILED_COMPILATION)
    # ON SUCCESS
    else:
        sys.exit(SUCCESS)

if __name__ == '__main__':
    make()
