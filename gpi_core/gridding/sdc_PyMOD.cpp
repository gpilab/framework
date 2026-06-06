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


/***************
Author: Jim Pipe
Date 2013 Sep
***************/

#include "PyFI/PyFI.h"
using namespace PyFI;

#include <iostream>
using namespace std;
#include "sdc.cpp"


/**************************/
PYFI_FUNC(oned_sdc)
/**************************/
{
    PYFI_START(); /* This must be the first line */

    /* input */
    PYFI_POSARG(Array<double>, crds);
    PYFI_POSARG(Array<double>, wates);
    PYFI_POSARG(Array<int64_t>, mtxdim);
    PYFI_POSARG(int64_t, numiter);
    PYFI_POSARG(double, taper);

    Array<double> cmtx(mtxdim->size(), mtxdim->as_ULONG());

    PYFI_SETOUTPUT_ALLOC(Array<double>, sdc, wates->dims_object());

    if (onedsdc(*crds,*wates,*sdc,cmtx, *numiter,*taper))
        PYFI_ERROR("onedsdc() has failed");

    PYFI_END(); /* This must be the last line */
} /* oned_sdc */

/**************************/
PYFI_FUNC(twod_sdc)
/**************************/
{
    PYFI_START(); /* This must be the first line */

    /* input */
    PYFI_POSARG(Array<double>, crds);
    PYFI_POSARG(Array<double>, wates);
    PYFI_POSARG(Array<int64_t>, mtxdim);
    PYFI_POSARG(int64_t, numiter);
    PYFI_POSARG(double, taper);

    Array<double> cmtx(mtxdim->size(), mtxdim->as_ULONG());

    PYFI_SETOUTPUT_ALLOC(Array<double>, sdc, wates->dims_object());

    if (twodsdc(*crds,*wates,*sdc,cmtx, *numiter,*taper))
        PYFI_ERROR("twodsdc() has failed");

    PYFI_END(); /* This must be the last line */
} /* twod_sdc */

/**************************/
PYFI_FUNC(threed_sdc)
/**************************/
{
    PYFI_START(); /* This must be the first line */

    /* input */
    PYFI_POSARG(Array<double>, crds);
    PYFI_POSARG(Array<double>, wates);
    PYFI_POSARG(Array<int64_t>, mtxdim);
    PYFI_POSARG(int64_t, numiter);
    PYFI_POSARG(double, taper);
    PYFI_POSARG(double, kradscale);

    Array<double> cmtx(mtxdim->size(), mtxdim->as_ULONG());

    PYFI_SETOUTPUT_ALLOC(Array<double>, sdc, wates->dims_object());

    if (threedsdc(*crds,*wates,*sdc,cmtx, *numiter,*taper, *kradscale))
        PYFI_ERROR("threedsdc() has failed");

    PYFI_END(); /* This must be the last line */
} /* threed_sdc */

/**************************/
PYFI_FUNC(twod_sdcsp)
/**************************/
{
    PYFI_START(); /* This must be the first line */

    /* input */
    PYFI_POSARG(Array<double>, crds);
    PYFI_POSARG(int64_t, numiter);
    PYFI_POSARG(double, taper);
    PYFI_POSARG(double, mtx_xy);

    PYFI_SETOUTPUT_ALLOC(Array<double>, sdc, ArrayDimensions(crds->size(1),crds->size(2)));

    if (twodsdcsp(*crds,*sdc,*numiter,*taper, *mtx_xy))
        PYFI_ERROR("twodsdcsp() has failed");

    PYFI_END(); /* This must be the last line */
} /* twod_sdcsp */

/**************************/
PYFI_FUNC(threed_sdcsp)
/**************************/
{
    PYFI_START(); /* This must be the first line */

    /* input */
    PYFI_POSARG(Array<double>, crds);
    PYFI_POSARG(int64_t, numiter);
    PYFI_POSARG(double, taper);
    PYFI_POSARG(double,mtx_xy);
    PYFI_POSARG(double,mtx_z);

    PYFI_SETOUTPUT_ALLOC(Array<double>, sdc, ArrayDimensions(crds->size(1),crds->size(2)) );

    if (threedsdcsp(*crds,*sdc,*numiter,*taper, *mtx_xy, *mtx_z))
        PYFI_ERROR("threedsdcsp() has failed");

    PYFI_END(); /* This must be the last line */
} /* threed_sdc */

/**************************/
/**************************/

PYFI_LIST_START_
    PYFI_DESC(oned_sdc, "1D SDC calculation")
    PYFI_DESC(twod_sdc, "2D SDC calculation")
    PYFI_DESC(threed_sdc, "3D SDC calculation")
    PYFI_DESC(twod_sdcsp, "2D SDC spiral calculation")
    PYFI_DESC(threed_sdcsp, "3D SDC spiral calculation")
PYFI_LIST_END_
