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
	\file dft_PyMOD.cpp
	\author Jim Pype
	\date 14 Jan

	\PyMOD for DFT

 **/

#include "PyFI/PyFI.h"
using namespace PyFI;

#include "dft_core.cpp"

PYFI_FUNC(dftgrid)
{
    PYFI_START(); /* This must be the first line */

    /* input */
    PYFI_POSARG(Array<complex<double> >, image);
    PYFI_POSARG(Array<double>, offres);
    PYFI_POSARG(Array<double>, crds);
    PYFI_POSARG(Array<double>, time);
    PYFI_POSARG(Array<int64_t>, outdim);
    PYFI_POSARG(int64_t, effmtx);

    PYFI_SETOUTPUT_ALLOC(Array<complex<double> >, outdata, DA(*outdim));

    if (do_dft(*image, *offres, *crds, *time, *outdata, *effmtx))
        PYFI_ERROR("griddat() has failed");

    PYFI_END(); /* This must be the last line */
} /* dftgrid */

PYFI_FUNC(dft_grid)
{
    PYFI_START(); /* This must be the first line */

    /* input */
    PYFI_POSARG(Array<complex<double> >, data);
    PYFI_POSARG(Array<double>, crds);
    PYFI_POSARG(Array<int64_t>, outdim);
    PYFI_POSARG(int64_t, effmtx);
    PYFI_POSARG(Array<double>, wghts);

    PYFI_SETOUTPUT_ALLOC(Array<complex<double> >, outdata, DA(*outdim));

    (*outdata) = complex<double>(0.,0.);
    do_dft_grid(*data, *crds, *outdata, *effmtx, *wghts);

    PYFI_END(); /* This must be the last line */
} /* dftgrid */



PYFI_LIST_START_
    PYFI_DESC(dftgrid, "DFT Gridding calculation")
    PYFI_DESC(dft_grid, "To Cartesian")
PYFI_LIST_END_
