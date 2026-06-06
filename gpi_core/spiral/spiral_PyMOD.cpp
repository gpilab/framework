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
	\file spiral_PyMOD.cpp
	\author Jim Pipe
	\date 13 Sep

	\PyMOD for spiralcoords

 **/

#include "PyFI/PyFI.h"
using namespace PyFI;
#include <iostream>
using namespace std;

#include "bnispiralfill.cpp"

extern "C"
{
    #include "bnispiralgen.c"
}

/* find the correct answer through brute force recon
 * inputs: solnk, solnV, vm, u, invu, nwraps, VENC
 */
PYFI_FUNC(coords)
{
    PYFI_START(); /* This must be the first line */

    /* input */
    PYFI_POSARG(double, dwell);
    PYFI_POSARG(double, xdely);
    PYFI_POSARG(double, ydely);
    PYFI_POSARG(double, zdely);

    PYFI_POSARG(double, mslew);
    PYFI_POSARG(double, mgrad);
    PYFI_POSARG(double, gamma);

    PYFI_POSARG(double, fovxy);
    PYFI_POSARG(double, fovz);
    PYFI_POSARG(double, resxy);
    PYFI_POSARG(double, resz);

    PYFI_POSARG(int64_t,   stype);
    PYFI_POSARG(double, narms);
    PYFI_POSARG(double, taper);
  
    PYFI_POSARG(int64_t, hubs);
    PYFI_POSARG(double, alpha0);
    PYFI_POSARG(int64_t, rebin);

    PYFI_POSARG(double, us_0);
    PYFI_POSARG(double, us_1);
    PYFI_POSARG(double, us_r);
    PYFI_POSARG(int64_t,   utype);

    PYFI_POSARG(double, mgfrq);
    PYFI_POSARG(double, t2mch);

    PYFI_POSARG(double, slper);
    PYFI_POSARG(int64_t,   gtype);
    PYFI_POSARG(int64_t,   spinout);
    PYFI_POSARG(int64_t,   numCalPnts);

    /* temp vars */
    const int64_t maxarray = 100000;
    double spparams[spARRSIZE];
    int spgrad_na;
    int spgrad_nb;
    int spgrad_nc;
    int spgrad_nd;

    /* fill spparams */
    if(*stype == spSTYPE_ARCHIM)
    {
          spparams[spARMS] = floor(*narms); /* truncate UI float */
          spparams[spSTYPE] = 0; 
    }
    else if(*stype == spSTYPE_CYL_DST)
    {
          spparams[spARMS] = *narms;
          spparams[spSTYPE] = 1; 
    }
    else if(*stype == spSTYPE_SPH_DST)
    {
          spparams[spARMS] = *narms;
          spparams[spSTYPE] = 2; 
    }
    else if(*stype == spSTYPE_FLORET)
    {
          spparams[spARMS] = *narms;
          spparams[spSTYPE] = 3; 
    }

    /* populate table with user input */
    /* units are already kHz, msec, mT, m */
    spparams[spDWELL]    = *dwell;
    spparams[spGAMMA]    = *gamma;
    spparams[spGMAX]     = *mgrad;
    spparams[spSLEWMAX]  = *mslew;

    /* Get spiralgen() options from user 
    *      0: calc through readout, 
    *      1: include grad rampdown, 
    *      2: include rewinder to k=0
    */
    spparams[spGTYPE] = *gtype;

    spparams[spFOVXY] = *fovxy;
    spparams[spFOVZ]  = *fovz;
    spparams[spRESXY] = *resxy;
    spparams[spRESZ]  = *resz;

    spparams[spTAPER]  = *taper;

    /* Get variable density spiral type from user:
    *      0 = linear, 
    *      1 = quadratic, 
    *      2 = hanning undersampling change
    */
    spparams[spUSTYPE] = *utype; 
    spparams[spUS0] = *us_0;
    spparams[spUS1] = *us_1;
    spparams[spUSR] = *us_r;

    spparams[spMGFRQ] = *mgfrq;
    spparams[spT2MATCH] = *t2mch;
    spparams[spSLOP_PER] = *slper;

/*******************************************/
// This is the computational part of the code
// Step 1: true_resolution  and array dimension calcs
// Step 2: Call bnispiralgen to get a 1D spiral (only then do we know it's length)
//         NOTE bnispiralgen SHOULD NOT BE ALTERED FOR RECON2, 
//              as it must be *identical* to the code used for the methods code
// Step 3: Next call bnispiralfill to replicate this 1D spiral for the rest of the 2D or 3D trajectory space
/*******************************************/

    float  gxarray[maxarray];
    float  gyarray[maxarray];
    float  gzarray[maxarray];
    double res_circle = sqrt(M_PI)/2.;
    double res_sphere = pow(M_PI/6.,(1./3.));
    // alpha0 is for FLORET, and the angle through which each hub is filled
    // hardcode this now for +/- 45 degrees
    // double alpha0 = 0.25*M_PI;

    Array<uint64_t> g_dims(3), k_dims(4);

//********
// STEP 1
//********
    /* alter resolution for circles and spheres to account for filter effect */
    /* then set output data dimensions */
    if(spparams[spSTYPE] == spSTYPE_ARCHIM)
    {
        spparams[spRESXY] *= res_circle;
        k_dims(2) = spparams[spARMS];
        k_dims(3) = 1; // Only generate 2D data
    }
    if(spparams[spSTYPE] == spSTYPE_CYL_DST)
    {
        spparams[spRESXY] *= res_circle;
        k_dims(2) = round(spparams[spARMS]*spparams[spFOVZ]/spparams[spRESZ]); /* DHW was floor */
        k_dims(3) = 1;
    }
    if(spparams[spSTYPE] == spSTYPE_SPH_DST)
    {
        spparams[spRESXY] *= res_sphere;
        spparams[spRESZ]  *= res_sphere;
        k_dims(2) = round(spparams[spARMS]*spparams[spFOVZ]/spparams[spRESZ]); /* DHW was floor */
        k_dims(3) = 1;
    }
    if(spparams[spSTYPE] == spSTYPE_FLORET)
    {
        spparams[spRESXY] *= res_sphere;
        spparams[spRESZ]  *= res_sphere;
        k_dims(2) = round(spparams[spARMS]*(*alpha0)*spparams[spFOVZ]/spparams[spRESZ]);
        if(*rebin)
        {
            int bin_fact = round(k_dims(2) / 34.0);
            k_dims(2) = bin_fact * 34.0;
        }
        k_dims(3) = *hubs;
    }

//********
// STEP 2
//********
    /* Calculate the base 2D spiral trajectory */
    if (bnispiralgen(spparams, maxarray, gxarray, gyarray, gzarray,
                 &spgrad_na, &spgrad_nb, &spgrad_nc, &spgrad_nd) == BNISPGEN_FAILURE)
    {
        PYFI_ERROR("bnispiralgen() returned fail code."); 
    }

    /* DHW change gxarray gyarray and gzarray for spiral in and spiral inout options */
    int64_t i;
    if (*spinout > 0) {
      /* insert addtional calbration points */
      if ((*spinout > 1) && (*numCalPnts > 0))
      {
          for (i = spgrad_nd-1; i >=0; i--)
          {
              gxarray[i+(*numCalPnts)] = gxarray[i];
              gyarray[i+(*numCalPnts)] = gyarray[i];
              gzarray[i+(*numCalPnts)] = gzarray[i];
          }
          for (i = 0; i < (*numCalPnts); i++)
          {
              gxarray[i] = 0.0;
              gyarray[i] = 0.0;
              gzarray[i] = 0.0;
          }
          spgrad_na = spgrad_na + (*numCalPnts);
          spgrad_nb = spgrad_nb + (*numCalPnts);
          spgrad_nc = spgrad_nc + (*numCalPnts);
          spgrad_nd = spgrad_nd + (*numCalPnts);
      }
      /* end of inserting calibraton points */

      /* first move the spiral out waveform spgrad_nd points forward */
      for(i=0; i<spgrad_nd; i++) {
        gxarray[i+spgrad_nd] = gxarray[i];
        gyarray[i+spgrad_nd] = gyarray[i];
        gzarray[i+spgrad_nd] = gzarray[i]; 
        }
      /* second reverse the first half */
      for(i=0; i<spgrad_nd; i++) {
        gxarray[i] = gxarray[2*spgrad_nd-1-i];
        gyarray[i] = gyarray[2*spgrad_nd-1-i];
        gzarray[i] = -gzarray[2*spgrad_nd-1-i];
        }
       
      if (*spinout ==3 || *spinout == 5) // same traj for spiral inout 
        for(i=0; i<spgrad_nd; i++) {
          gxarray[i+spgrad_nd] = -gxarray[i+spgrad_nd];
          gyarray[i+spgrad_nd] = -gyarray[i+spgrad_nd];
          }
      if (*spinout >= 4) // rot2 or same2
      {
          for(i=0; i<2*spgrad_nd; i++)
          {
              gxarray[i] = -gxarray[i];
              gyarray[i] = -gyarray[i];
          }
      }
      }
   
//********
// STEP 3
//********

    /* bnispiralgen tells us how many gradient points per TR */
    if (spparams[spGTYPE] == spGTYPE_READOUT)  g_dims(1) = spgrad_na; // edge of k-space
    if (spparams[spGTYPE] == spGTYPE_RAMPDOWN) g_dims(1) = spgrad_nb; // grad rampdown
    if (spparams[spGTYPE] == spGTYPE_REWIND)   g_dims(1) = spgrad_nc; // k-space rewinder
    if (spparams[spGTYPE] == spGTYPE_M1)       g_dims(1) = spgrad_nd; // k-space rewinder
    if (spparams[spGTYPE] == spGTYPE_FSPOIL)       g_dims(1) = spgrad_nb; // FLORET fast spoiling

    g_dims(0) = 3; // 3 for x y z
    k_dims(0) = 3; // 3 for x y z
    k_dims(1) = g_dims(1); // just for ktmp, reassign this below for karray
    g_dims(2) = k_dims(2);

    /* RKR make larger to account for other hubs */
    if(spparams[spSTYPE] == spSTYPE_FLORET)
    {
        g_dims(2) *= *hubs;
    }

    // DHW spiral_inout options
    if (*spinout > 1)
    {
        k_dims(1) *=2;
        g_dims(1) *=2;
    }

    /* desired dwell after resampling */
    spparams[spREADPTS] = floor((float)(spgrad_na)*PHGRAST/spparams[spDWELL]);
    double tread0 = 0; // DHW the time for prewinder(fliped rewinder) for spiral in and spiral inout
    if(*spinout > 0)
        tread0=(spgrad_nd - spgrad_na)*PHGRAST;

    /* Create memory for gradients and k-space */
    Array<double> garray(DA(g_dims));
    Array<double>   ktmp(DA(k_dims));
    k_dims(1) = spparams[spREADPTS];
    // DHW spiral_inout options
    if (*spinout >1)
        k_dims(1) *=2;

    Array<double> karray(DA(k_dims));

    bnispiralfill(spparams, maxarray, gxarray,gyarray, gzarray,
                  garray,karray,ktmp,*alpha0,*rebin, *xdely,*ydely,*zdely,tread0,*spinout);

    

    PYFI_SETOUTPUT(&garray);
    PYFI_SETOUTPUT(&karray);

    PYFI_END(); /* This must be the last line */
} /* coords */

PYFI_LIST_START_
    PYFI_DESC(coords, "calculate spiral coordinates and gradients")
PYFI_LIST_END_
