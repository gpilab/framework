/*     The GPI core node library is licensed under
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
	\file spiralgencf_PyMOD.cpp
	\author Jim Pipe
	\date 20 oct

	\PyMOD for spiralcoords

 **/

#include "PyFI/PyFI.h"
using namespace PyFI;
#include <iostream>
using namespace std;

#include "spiralgencf_gen.c"
#include "spiralgencf_fill.cpp"

/****
extern "C"
{
    #include "core/spiral/spiralgencf_gen.c"
}
****/

PYFI_FUNC(coords)
{
    PYFI_START(); /* This must be the first line */

    /* input */
    PYFI_POSARG(Array<double>, girf);
    PYFI_POSARG(Array<double>, gtf);
    PYFI_POSARG(double, dwell);
    PYFI_POSARG(double, xdely);
    PYFI_POSARG(double, ydely);

    PYFI_POSARG(double, mslew);
    PYFI_POSARG(double, mgrad);
    PYFI_POSARG(double, gamma);

    PYFI_POSARG(double, fov);
    PYFI_POSARG(double, res);

    PYFI_POSARG(double, narms);

    PYFI_POSARG(double, us_0);
    PYFI_POSARG(double, us_1);
    PYFI_POSARG(double, us_r0);
    PYFI_POSARG(double, us_r);

    PYFI_POSARG(double, mgfrq);
    PYFI_POSARG(int64_t, precomp);
    PYFI_POSARG(int64_t, precond);
    PYFI_POSARG(double, start_win);
    PYFI_POSARG(double, end_win);
    PYFI_POSARG(double, corner_win);

    PYFI_POSARG(int64_t,   spinout);

    PYFI_POSARG(double, trures_acq);

    /* temp vars */
    const int64_t maxarray = 100000; // 100k points is 640msec for 6.4 usec grad raster
    double spparams[spARRSIZE];
    int spgrad_na;
    int spgrad_nb;


    double mx0;
    double my0;
    double mx1;
    double my1;

    /* fill spparams */
    spparams[spARMS] = *narms;

    /* populate table with user input */
    /* units are already kHz, msec, mT, m */
    spparams[spDWELL]    = *dwell;
    spparams[spGAMMA]    = *gamma;
    spparams[spGMAX]     = *mgrad;
    spparams[spSLEWMAX]  = *mslew;

    spparams[spFOV] = *fov;
    spparams[spRES] = (*res) * (*trures_acq);
    spparams[spTRURES] = *trures_acq;

    spparams[spUS0] = *us_0;
    spparams[spUS1] = *us_1;
    spparams[spUSR0] = *us_r0;
    spparams[spUSR] = *us_r;

    spparams[spMGFRQ] = *mgfrq;
    spparams[spPRECOMP] = *precomp;
    spparams[spPRECOND] = *precond;
    spparams[spSTWIN] = *start_win;
    spparams[spENWIN] = *end_win;
    spparams[spCORWIN] = *corner_win;

    spparams[spINOUT] = *spinout;

/*******************************************/
// This is the computational part of the code
// First call spiralgen to get a 1D spiral (only then do we know it's length)
// Next call spiralfill to replicate this 1D spiral for the rest of the 2D or 3D trajectory space
// It is important that spiralfill is the same as methods (i.e. methods and recon rotate trajectory identically)
/*******************************************/

    float  gxarray[maxarray];
    float  gyarray[maxarray];
    float  kxarray[maxarray];
    float  kyarray[maxarray];

    Array<uint64_t> g_dims(3), k_dims(3), t_dims(2);

    t_dims(0) = maxarray;
    t_dims(1) = 20;

    /*******************************************/
    /* Calculate the base 2D spiral trajectory */
    /* This is the main subroutine             */
    /*******************************************/
    if (spiralgen(spparams, maxarray, *girf, *gtf, gxarray, gyarray,
                    kxarray, kyarray, &spgrad_na, &spgrad_nb,
                    &mx0, &my0, &mx1, &my1) == 0) {
      PYFI_ERROR("spiralgen() returned fail code.");
      }

    g_dims(0) = 2; // 2 for x y
    g_dims(1) = spgrad_nb; // includes grad rampdown
    g_dims(2) = spparams[spARMS];

    k_dims(0) = 2; // 2 for x y
    k_dims(1) = spgrad_na; // just for ktmp, reassign this below for karray
    k_dims(2) = g_dims(2);


    /* Create memory for gradients and k-space */
    Array<double> garray(DA(g_dims));
    Array<double>   ktmp(DA(k_dims));

    /* desired dwell after resampling */
    spparams[spREADPTS] = ceil((float)(spgrad_na-1)*SPGRAST/spparams[spDWELL]);
    k_dims(1) = spparams[spREADPTS];
    Array<double> karray(DA(k_dims));

    spiralfill(spparams, maxarray, gxarray, gyarray, kxarray, kyarray,
                 garray, karray, ktmp,
                 *xdely, *ydely);

    PYFI_SETOUTPUT(&garray);
    PYFI_SETOUTPUT(&karray);

    PYFI_END(); /* This must be the last line */
} /* coords */


PYFI_LIST_START_
    PYFI_DESC(coords, "calculate spiral coordinates and gradients")
PYFI_LIST_END_
