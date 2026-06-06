/*
 * Copyright (c) 2014, Dignity Health
 * 
 *     The GPI core node library is licensed under
 * either the BSD 3-clause or the LGPL v. 3.
 * 
 *     Under either license, the following additional term applies:
 * 
 *         NO CLINICAL USE.  THE SOFTWARE IS NOT INTENDED FOR COMMERCIAL
 * PURPOSES AND SHOULD BE USED ONLY FOR NON-COMMERCIAL RESEARCH PURPOSES.  THE
 * SOFTWARE MAY NOT IN ANY EVENT BE USED FOR ANY CLINICAL OR DIAGNOSTIC
 * PURPOSES.  YOU ACKNOWLEDGE AND AGREE THAT THE SOFTWARE IS NOT INTENDED FOR
 * USE IN ANY HIGH RISK OR STRICT LIABILITY ACTIVITY, INCLUDING BUT NOT LIMITED
 * TO LIFE SUPPORT OR EMERGENCY MEDICAL OPERATIONS OR USES.  LICENSOR MAKES NO
 * WARRANTY AND HAS NOR LIABILITY ARISING FROM ANY USE OF THE SOFTWARE IN ANY
 * HIGH RISK OR STRICT LIABILITY ACTIVITIES.
 * 
 *     If you elect to license the GPI core node library under the LGPL the
 * following applies:
 * 
 *         This file is part of the GPI core node library.
 * 
 *         The GPI core node library is free software: you can redistribute it
 * and/or modify it under the terms of the GNU Lesser General Public License as
 * published by the Free Software Foundation, either version 3 of the License,
 * or (at your option) any later version. GPI core node library is distributed
 * in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even
 * the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
 * See the GNU Lesser General Public License for more details.
 * 
 *         You should have received a copy of the GNU Lesser General Public
 * License along with the GPI core node library. If not, see
 * <http://www.gnu.org/licenses/>.
 */


/**
	\file grid_PyMOD.cpp
	\author Jim Pype
	\date 13 Sep

	\PyMOD for GRID

 **/

#include "PyFI/PyFI.h"
using namespace PyFI;

#include <iostream>
using namespace std;
#include "grid_123d.cpp"

PYFI_FUNC(grid)
{
    PYFI_START(); /* This must be the first line */

    /* input */
    PYFI_POSARG(Array<float>, crds);
    PYFI_POSARG(Array<complex<float> >, data);
    PYFI_POSARG(Array<float>, wates);
    PYFI_POSARG(Array<int64_t>, outdim);
    PYFI_POSARG(double, dx);
    PYFI_POSARG(double, dy);
    PYFI_POSARG(double, dz);

    PYFI_SETOUTPUT_ALLOC_DIMS(Array<complex<float> >, outdata, outdim->size(), outdim->as_ULONG());

    if (griddat(*crds,*data,*wates,*outdata,*dx,*dy,*dz))
        PYFI_ERROR("griddat() has failed");

    PYFI_END(); /* This must be the last line */
} /* grid */

PYFI_FUNC(rolloff)
{
    PYFI_START(); /* This must be the first line */

    /* input */
    PYFI_POSARG(Array<complex<float> >, data);
    PYFI_POSARG(Array<int64_t>, outdim);
    PYFI_POSARG(int64_t, isofov);

    PYFI_SETOUTPUT_ALLOC_DIMS(Array<complex<float> >, outdata, outdim->size(), outdim->as_ULONG());

    if (rolloffdat(*data,*outdata,*isofov))
        PYFI_ERROR("rolloff() has failed");

    PYFI_END(); /* This must be the last line */
} /* rolloff */


PYFI_LIST_START_
    PYFI_DESC(grid, "Standard Gridding calculation")
    PYFI_DESC(rolloff, "Rolloff Correction for Standard Gridding calculation")
PYFI_LIST_END_
