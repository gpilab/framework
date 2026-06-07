/*
 *   Copyright (C) 2014  Dignity Health
 *
 *   This program is free software: you can redistribute it and/or modify
 *   it under the terms of the GNU Lesser General Public License as published by
 *   the Free Software Foundation, either version 3 of the License, or
 *   (at your option) any later version.
 *
 *   This program is distributed in the hope that it will be useful,
 *   but WITHOUT ANY WARRANTY; without even the implied warranty of
 *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *   GNU Lesser General Public License for more details.
 *
 *   You should have received a copy of the GNU Lesser General Public License
 *   along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 *   NO CLINICAL USE.  THE SOFTWARE IS NOT INTENDED FOR COMMERCIAL PURPOSES
 *   AND SHOULD BE USED ONLY FOR NON-COMMERCIAL RESEARCH PURPOSES.  THE
 *   SOFTWARE MAY NOT IN ANY EVENT BE USED FOR ANY CLINICAL OR DIAGNOSTIC
 *   PURPOSES.  YOU ACKNOWLEDGE AND AGREE THAT THE SOFTWARE IS NOT INTENDED FOR
 *   USE IN ANY HIGH RISK OR STRICT LIABILITY ACTIVITY, INCLUDING BUT NOT
 *   LIMITED TO LIFE SUPPORT OR EMERGENCY MEDICAL OPERATIONS OR USES.  LICENSOR
 *   MAKES NO WARRANTY AND HAS NO LIABILITY ARISING FROM ANY USE OF THE
 *   SOFTWARE IN ANY HIGH RISK OR STRICT LIABILITY ACTIVITIES.
 */

#ifndef _PYFI_H_GUARD
#define _PYFI_H_GUARD
/**
    \brief Include all necessary PyFI functionality.
**/

/******************* 
 * PYTHON REQS
 *******************/

/*
    From http://docs.python.org/3.1/c-api/intro.html#include-files

    Python.h must be included before any standard libs.

        <stdio.h>, <string.h>, <errno.h>, <limits.h>, <assert.h> and <stdlib.h>

    Therefore PyFunctionIF.cpp must be included before.
*/
#ifdef _XOPEN_SOURCE
    #warning "PyFunctionIF must be included before any standard library.  (_XOPEN_SOURCE)"
#endif

#ifdef _POSIX_C_SOURCE
    #warning "PyFunctionIF must be included before any standard library.  (_POSIX_C_SOURCE)"
#endif

/*******************
 * PYTHON & NUMPY
 *******************/

/* On Windows, math.h only defines M_PI when _USE_MATH_DEFINES is set AND it
 * must be defined before the very first inclusion of math.h (Python.h pulls
 * it in on Windows).  Setting it here — before Python.h — is the only
 * reliable location.
 */
#if defined(_WIN32) || defined(__MINGW32__) || defined(__MINGW64__) || defined(MS_WIN64)
    #ifndef _USE_MATH_DEFINES
        #define _USE_MATH_DEFINES
    #endif
#endif

/* Lock to the 1.20 API: avoids PyArrayObject_fields direct struct access
 * (removed in NumPy 2.0) and other pre-1.20 deprecated calls.
 * Using PyArray_DATA() as the proper public accessor macro.
 */
#define NPY_NO_DEPRECATED_API NPY_1_20_API_VERSION
#include <Python.h>            // this must be first
#ifndef PY_ARRAY_UNIQUE_SYMBOL
    #define PY_ARRAY_UNIQUE_SYMBOL MOD_NAME ## ____gpi // this must be defined before arrayobject.h
#endif
#include "numpy/arrayobject.h" // this must be second
/* PyArray_DATA() is the stable public accessor (NumPy 1.x and 2.x).
 * The cast to PyArrayObject* mirrors what the old PyArrayObject_fields
 * cast did; callers have already verified the object is an ndarray. */
#define PYFI_PyArray_BYTES(obj) PyArray_DATA((PyArrayObject*)(obj))

/******************* 
 * PYFI 
 *******************/

/* PyFunction declaration simplifications */
#include "PyFI/PyFIMacros.h"
#include "PyFI/PyFunctionIF.cpp"

#ifdef PYFI_RECON2
    /* subclassed interface for R2 arrays */
    #include "PyFI/PyFunctionIF_R2.cpp"
#endif

#include "PyFI/PyFIArray.cpp"
#include "PyFI/PyFIArray_WrappedNUMPY.cpp"
#include "PyFI/PyFIArray_WrappedFFTW.cpp"
#include "PyFI/PyFIArray_WrappedEigen.cpp"

/* Windows dlgs.h (pulled in via windows.h → winuser.h → dlgs.h through
 * pthread.h) defines rad1–rad16 as dialog-control numeric IDs.  These clash
 * with the common variable names used in scientific C++ code.  Undef them
 * here so that code included after this header can use those identifiers as
 * normal variable names.
 */
#if defined(_WIN32) || defined(MS_WIN64)
    #ifdef rad1
        #undef rad1
    #endif
    #ifdef rad2
        #undef rad2
    #endif
    #ifdef rad3
        #undef rad3
    #endif
    #ifdef rad4
        #undef rad4
    #endif
    #ifdef rad5
        #undef rad5
    #endif
    #ifdef rad6
        #undef rad6
    #endif
    #ifdef rad7
        #undef rad7
    #endif
    #ifdef rad8
        #undef rad8
    #endif
    #ifdef rad9
        #undef rad9
    #endif
    #ifdef rad10
        #undef rad10
    #endif
    #ifdef rad11
        #undef rad11
    #endif
    #ifdef rad12
        #undef rad12
    #endif
    #ifdef rad13
        #undef rad13
    #endif
    #ifdef rad14
        #undef rad14
    #endif
    #ifdef rad15
        #undef rad15
    #endif
    #ifdef rad16
        #undef rad16
    #endif
#endif /* _WIN32 || MS_WIN64 */

#endif // GUARD
