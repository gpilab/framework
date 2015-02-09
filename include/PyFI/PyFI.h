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
 *   MAKES NO WARRANTY AND HAS NOR LIABILITY ARISING FROM ANY USE OF THE
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

/* Use the following define statement to test for deprecated api.
 *  -The PyArray_BYTES() is said to be replaced with an inline function so the
 *   name will still be usable in the future (but should be the first thing
 *   checked when numpy goes to v2).
 */
#define NPY_NO_DEPRECATED_API NPY_1_7_API_VERSION
#include <Python.h>            // this must be first
#ifndef PY_ARRAY_UNIQUE_SYMBOL
    #define PY_ARRAY_UNIQUE_SYMBOL MOD_NAME ## ____gpi // this must be defined before arrayobject.h
#endif
#include "numpy/arrayobject.h" // this must be second
/* use this for now */
#define PYFI_PyArray_BYTES(obj) (((PyArrayObject_fields *)(obj))->data)

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

#endif // GUARD
