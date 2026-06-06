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


/*********************************************
// Spiral Generation code customized for Philips
**********************************************
// Author: Jim Pipe
// Date: May 2011
// Philips-specific Revisions: June 2012
*********************************************/
// A Subset of Relevant Literature
//
// Spiral Invented:
// High-speed spiral-scan echo planar NMR imaging-I.
// Ahn, C.B., Kim, J.H. & Cho, Z.H., IEEE Transactions on Medical Imaging, 5(1) 1986.
//
// Spiral Improved:
// Fast Spiral Coronary Artery Imaging.
// Meyer CH, Hu BS, Nishimura DG, Macovski A, Magnetic Resonance in Medicine, 28(2) 1992.
//
// Variable Density Spiral
// Reduced aliasing artifacts using variable-density k-space sampling trajectories.
// Tsai CM, Nishimura DG, Magnetic Resonance in Medicine, 43(3), 2000
//
// "SLOPPY" SPIRAL
// Faster Imaging with Randomly Perturbed Undersampled Spirals and L_1 Reconstruction
// M. Lustig, J.H. Lee, D.L. Donoho, J.M. Pauly, Proc. of the ISMRM '05
//
// FLORET
// A new design and rationale for 3D orthogonally oversampled k-space trajectories
// Pipe JG, Zwart NR, Aboussouan EA, Robison RK, Devaraj A, Johnson KO, Mag Res Med 66(5) 2011
//
// Distributed Spirals
// Distributed Spirals: A New Class of 3D k-Space Trajectories
// Turley D, Pipe JG, Magnetic Resonance in Medicine, in press (also proc of ISMRM '12)

#ifndef BNISPIRALGEN_C
#define BNISPIRALGEN_C

#include <cmath>

//#define DEBUG_FIELD
#ifndef MAX
#define UNDEFMAX
#define MAX(a,b) (((a)<(b))?(b):(a))
#endif

#ifndef MIN
#define UNDEFMIN
#define MIN(a,b) (((a)>(b))?(b):(a))
#endif

/* return values for error checking */
#define BNISPGEN_SUCCESS 1
#define BNISPGEN_FAILURE 0

#define PHGRAST    0.0064 /* Philips' gradient raster time (ms) */
#define subrast    8      /* number of numerical cycles per gradient raster time */

#define spARRSIZE  25

/* these are used in the pulse sequence, the AVS module and the python reader */
#define spGAMMA     0
#define spGMAX      1
#define spSLEWMAX   2

#define spGTYPE     3

#define spFOVXY     4
#define spFOVZ      5
#define spRESXY     6
#define spRESZ      7
#define spARMS      8
#define spTAPER    19

#define spSTYPE     9
#define spUSTYPE   10
#define spUS0      11
#define spUS1      12
#define spUSR      13

#define spDWELL    14 /* not used by spiralgen(), for resampling after */
#define spREADPTS  15 /* not used by spiralgen(), for recon malloc */

#define spSLOP_PER 16
#define spMGFRQ     17
#define spT2MATCH  18

/* spUSTYPE */
#define spUSTYPE_LINEAR 0
#define spUSTYPE_QUAD   1
#define spUSTYPE_HANN   2

/* spGTYPE */
#define spGTYPE_READOUT  0
#define spGTYPE_RAMPDOWN 1
#define spGTYPE_REWIND   2
#define spGTYPE_M1       3
#define spGTYPE_FSPOIL	 4 /* RKR fast spoiling for FLORET */

/* spSTYPE */
#define spSTYPE_ARCHIM  0
#define spSTYPE_CYL_DST 1
#define spSTYPE_SPH_DST 2
#define spSTYPE_FLORET  3

#include "bnispiralgmn.c"

int bnispiralgen(double* spparams, int maxarray, float *gxarray, float *gyarray, float *gzarray,
                  int *spgrad_na, int *spgrad_nb, int *spgrad_nc, int *spgrad_nd)
{
/************************************************************
************************************************************

  This function takes parameters passed in spparams array and
  returns a single spiral arm calculated numerically

  The corresponding gradient waveforms are in gxarray and gyarray
  spgrad_na reflects the number of gradient points to reach the end of k-space
  spgrad_nb = spgrad_na + the number of gradient points to ramp G to zero
  spgrad_nc = spgrad_nb + the number of gradient points to rewind k to zero
  spgrad_nd = spgrad_nc + the number of gradient points for first moment compensation

  Assignments below indicate units of input parameters
  All units input using kHz, msec, mT, and m!

  grad = gm exp(i theta) i.e. gm, theta are magnitude and angle of gradient
  kloc = kr exp(i phi)   i.e. kr, phi are magnitude and angle of k-space
  alpha = theta - phi    the angle of the gradient relative to that of k-space
                         (alpha = Pi/2, you go in a circle
                          alpha = 0, you go out radially)

  The variable rad_spacing determines the radial spacing
  in units of the Nyquist distance.
  rad_spacing = 1 gives critical sampling
  rad_spacing > 1 gives undersampling
  rad_spacing can vary throughout spiral generation to create variable density spirals

  KEY EQUATIONS:
  (1) dkr/dphi = rad_spacing*Nyquist/(2 pi)
  (2) dphi/dt = gamma gm Sin(alpha)/kr
  (3) dkr/dt = gamma gm Cos(alpha)

  Solving (1)*(2) = (3) gives
  (4) Tan(alpha) = (2*pi*kr)/(rad_spacing*Nyquist)

*************************************************************/
/* Initializations */
/************************************************************/
  double rast     = PHGRAST / (double)(subrast);   /* calculation "raster time" in msec */

  double gamma    = spparams[spGAMMA];   /* typically 42.577 kHz/mT */
  double gmax     = spparams[spGMAX];    /* max gradient amplitude in mT/m */
  double gfrqmax  = spparams[spMGFRQ];   /* max gradient freq in kHz */
  double slewmax  = spparams[spSLEWMAX]; /* max slew rate, in mT/m/msec*/
  int    gtype    = spparams[spGTYPE];   /* 0 = calculate through readout
                                            1 = include grad ramp-down
                                            2 = include rewinder to end at k=0
                                            3 = include first moment comp */

  double fovxy    = spparams[spFOVXY];   /* enter in m */
  double resxy    = spparams[spRESXY];   /* enter in m : this should be true resolution */
  double fovz     = spparams[spFOVZ];    /* enter in m */
  double resz     = spparams[spRESZ];    /* enter in m : this should be true resolution */
  double arms     = spparams[spARMS];    /* number of spiral interleaves*/
  double taper    = spparams[spTAPER];   /* taper for CDST */
  int   stype     = spparams[spSTYPE];   /* 0 = Archimedean
                                            1 = Cylinder DST
                                            2 = Spherical DST
                                            3 = Hanning DST
                                            4 = Fermat:Floret */

  /* the next 4 variables are for variable density spirals */
  /* they create a transition in the radial spacing as the k-space radius goes from 0 to 1, i.e.*/
  /*    0 < kr < us_0 : spacing = Nyquist distance */
  /* us_0 < kr < us_1 : spacing increases to us_r (affected by ustype)*/
  /* us_1 < kr < 1    : spacing = us_r*/
  int   ustype   = spparams[spUSTYPE]; /* rate of change in undersampling
                                          0 = linear
                                          1 = quadratic
                                          2 = hanning */

  double us_0    = spparams[spUS0];
  double us_1    = spparams[spUS1];
  double us_r    = spparams[spUSR];

  double t2match = spparams[spT2MATCH];

  /* For sloppy spirals, this lets us define periodicity in units of iteration loop time */
  /* set this to zero if you do not want sloppy spirals */
  double slop_per = spparams[spSLOP_PER];

  double nyquist = (double)(arms)/fovxy; /* radial distance per arm to meet the Nyquist limit*/
  double gamrast = gamma*rast; /* gamrast*g = dk*/
  double dgc     = slewmax*rast; /* the most the gradients can change in 1 raster period*/
  double sub_gamrast = (double)(subrast)*gamrast;
  double sub_dgc     = (double)(subrast)*dgc;

  double *kx    = NULL;
  double *ky    = NULL;
  double *kz    = NULL;
  double *gsign    = NULL;

  double kr, kmx, kmy, kmz, kmr, rnorm;
  double rad_spacing=1;
  double alpha, phi, theta;
  double gfrq;
  double ux=0,uy=0,uz=0, umag;
  double gx=0,gy=0,gz=0;
  double us_i;
  double gm=0,term;
  double gsum_ramp, gz_sum_ramp= 0;
  double gsum, gsum0, gradtweak, gxsum, gysum, gzsum;
  double krmax, kzmax, krmax2, kzmax2;
  double kz0,kznorm,rdenom;
  double krnorm;
  double krlim;
  double gm_center;
  int    end_rewinder_flat_top;
  int i, i0, i1, i_end;
  int j;
  int status = 1; /* default set to 1 == SUCCESS */

  kx    = (double*) malloc(subrast*maxarray*sizeof(double));
  ky    = (double*) malloc(subrast*maxarray*sizeof(double));
  kz    = (double*) malloc(subrast*maxarray*sizeof(double));
  gsign = (double*) malloc(subrast*maxarray*sizeof(double));

  if (kx == NULL || ky == NULL || gsign == NULL) printf ("cant allocate memory\n");

  for (i=0;i<subrast*maxarray;i++) gsign[i] = 1.;
  for (i=0;i<subrast*maxarray;i++) kx[i] = 0.;
  for (i=0;i<subrast*maxarray;i++) ky[i] = 0.;
  for (i=0;i<subrast*maxarray;i++) kz[i] = 0.;
  for (i=0;i<maxarray;i++) gxarray[i] = 0.;
  for (i=0;i<maxarray;i++) gyarray[i] = 0.;
  for (i=0;i<maxarray;i++) gzarray[i] = 0.;

  krmax = 0.5/resxy;
  kzmax = 0.5/resz;
  krmax2 = krmax*krmax;
  kzmax2 = kzmax*kzmax;
  krlim = krmax*(1.-(resxy/fovxy));
  theta = 0.;

  if (stype == spSTYPE_CYL_DST) {
    kz0 = (1.-taper)*kzmax;
    kznorm = kzmax-kz0;
  }

  /* Initialization */
  *spgrad_na = 0;
  *spgrad_nb = 0;
  *spgrad_nc = 0;
  *spgrad_nd = 0;

/* start out spiral going radially at max slew-rate for 2 time-points */
  kx[0] = 0.;
  ky[0] = 0.;
  kx[1] = gamrast*dgc;
  ky[1] = 0.;
  kx[2] = 3.*gamrast*dgc;
  ky[2] = 0.;

  if (stype == spSTYPE_SPH_DST) {
    kz[0] = kzmax;
    kz[1] = sqrt(kzmax2*(1.-((kx[1]*kx[1]+ky[1]*ky[1])/krmax2))); // stay on surface of ellipsoid
    kz[2] = sqrt(kzmax2*(1.-((kx[2]*kx[2]+ky[2]*ky[2])/krmax2))); // stay on surface of ellipsoid
    }
  if (stype == spSTYPE_CYL_DST) {
    kz[0] = kzmax;
    krnorm = min(1.,sqrt(kx[1]*kx[1]+ky[1]*ky[1])/krmax); //
    kz[1] = kz0 + kznorm*(2./M_PI)*acos(krnorm);
    krnorm = min(1.,sqrt(kx[2]*kx[2]+ky[2]*ky[2])/krmax); //
    kz[2] = kz0 + kznorm*(2./M_PI)*acos(krnorm);
    }
  else if (stype == spSTYPE_FLORET) { /* RKR FLORET */
    kz[0] = 0.0;
    kz[1] = sqrt(kx[1]*kx[1]+ky[1]*ky[1]);
    kz[2] = sqrt(kx[2]*kx[2]+ky[2]*ky[2]);
    }

  i = 2;
  kr = kx[2];

/******************************/
/* LOOP UNTIL YOU HIT MAX RES */
/******************************/
  while ((kr <= krlim) && (i < subrast*maxarray-1) ) {

/**************************/
/*** STEP 1:  Determine the direction (ux,uy) of the gradient at ~(i+0.5) */
/**************************/
   /* calculate dk/rast = gamma G*/
    kmx = 1.5*kx[i] - 0.5*kx[i-1];
    kmy = 1.5*ky[i] - 0.5*ky[i-1];
    kmr = sqrt(kmx*kmx + kmy*kmy);

/////////////////////////////
// Start rad_spacing logic //
/////////////////////////////
    rnorm = 2.*resxy*kmr; /* the k-space radius, normalized to go from 0 to 1 */

    /* determine the undersample factor */
    if (rnorm <= us_0)
      rad_spacing = 1;
    else if (rnorm < us_1) {
      us_i = (rnorm-us_0)/(us_1 - us_0); /* goes from 0 to 1 as rnorm goes from us_0 to us_1*/
      if (ustype == spUSTYPE_LINEAR) {
/* linearly changing undersampling*/
        rad_spacing = 1. + (us_r - 1.)*us_i;
        }
      else if (ustype == spUSTYPE_QUAD) {
/* quadratically changing undersampling*/
        rad_spacing = 1. + (us_r - 1.)*us_i*us_i;
        }
      else if (ustype == spUSTYPE_HANN) {
/* Hanning-type change in undersampling */
        rad_spacing = 1. + (us_r - 1.)*0.5*(1.-cos(us_i*M_PI));
        }
      } // if (rnorm < us_1)
    else {
      rad_spacing = us_r;
      } // rnorm > us_1

/* Undersample spiral for Spherical-Distributed Spiral */
    if (stype == spSTYPE_SPH_DST) {
      if(rnorm < 1.0)
        rad_spacing = MIN(fovz/resz, rad_spacing/sqrt(1.0 - (rnorm*rnorm)));
      else
        rad_spacing = fovz/resz;
      } // SDST

/* Undersample spiral for Cyl-Distributed Spiral */
    if (stype == spSTYPE_CYL_DST) {
      if(rnorm < 1.0) {
        rdenom = (kz0 + kznorm*((2./M_PI)*acos(rnorm)))/kzmax;
        rad_spacing = MIN(fovz/resz, rad_spacing/rdenom);
        }
      else
        rad_spacing = fovz/resz;
      } // HDST

/* MAKE FERMAT SPIRAL FOR FLORET*/
    if (stype == spSTYPE_FLORET && rnorm > 0.) rad_spacing *= 1./rnorm;

/* Sloppy Spirals - add variability to rad_spacing for reduced aliasing coherence */
// A couple different options here are commented out
// Lots of ways to be sloppy
    if (slop_per > 0) {
//      rad_spacing = MAX(1., (rad_spacing + ((rad_spacing-1.)*sin(2.*M_PI*(double)(i)/slop_per))));
//      rad_spacing += (rad_spacing-1.)*sin(2.*M_PI*slop_per*atan2(ky[i],kx[i]));
      rad_spacing += (rad_spacing-1.)*sin(2.*M_PI*slop_per*rnorm);
      }

// T2 Matching samples more densely together as the signals decays
// SDC will corresponding weight high-signal data more, optimizing SNR while keeping a flat k-space MTF
     if (t2match > 0.)
       rad_spacing = rad_spacing * exp(-(double)(i)*rast/t2match);

///////////////////////////
// End rad_spacing logic //
///////////////////////////

/* See the Key Equation 4 at the beginning of the code*/
    alpha = atan(2.*M_PI*kmr/(rad_spacing*nyquist));
    phi = atan2(kmy,kmx);

/* If gradient frequency = dtheta/dt/2Pi is over maximum, slow down this cycle */
    gfrq = fabs((phi+alpha-theta)/(2.*M_PI))/rast;
    if ((gfrqmax > 0) && (gfrq > gfrqmax))
      gsign[i] = -1;

    theta = phi + alpha;
    ux = cos(theta);
    uy = sin(theta);

// IF SPHERICAL DST
// u dot km is zero if moving on a sphere (km is radial, u is tangential,
// thus km stays on the sphere)
// We are on an ellipsoid, but can normalize u and km by krmax and kzmax to make this work
// The final gradient vector (ux uy uz) will be tangential to the sphere
    if (stype == spSTYPE_SPH_DST) {
      kmz = 1.5*kz[i] - 0.5*kz[i-1];
      uz = -((ux*kmx + uy*kmy)/krmax2)*(kzmax2/kmz);
      umag = sqrt(ux*ux + uy*uy + uz*uz);
      ux = ux/umag;
      uy = uy/umag;
      uz = uz/umag;
      gz = (kz[i] - kz[i-1])/gamrast;
    }

    /* IF CYL DST with hanning taper
    * We need to find uz.
    * 1.  ur = gradient direction radially, which is cos(alpha)
    * 2.  ur/uz = dkr/dkz, or
    * 2.5 uz = ur / (dkr/dkz)
    * 3.  For Hanning, kr = krmax cos[((kz-kz0)/kznorm) (pi/2)], so
    * 4.  dkr/dkz = -(pi/2)(krmax/kznorm)sin[((kz-kz0)/kznorm) (pi/2)]
    *     giving:
    *   uz = -ur*(2./M_PI)*(kznorm/krmax)/sin(((kmz-kz0)/kznorm)*(M_PI/2.));
    */
    if (stype == spSTYPE_CYL_DST && taper > 0) {
      kmz = 1.5*kz[i] - 0.5*kz[i-1];
      if (kmz > kz0 + 0.001*kznorm)
        uz = -cos(alpha)*(2./M_PI)*(kznorm/krmax)/sin(((kmz-kz0)/kznorm)*(M_PI/2.));
      else // getting too close to divide by zero...
        uz = -cos(alpha)*(2./M_PI)*(kznorm/krmax)/sin(0.001*(M_PI/2.));
      umag = sqrt(ux*ux + uy*uy + uz*uz);
      ux = ux/umag;
      uy = uy/umag;
      uz = uz/umag;
      gz = (kz[i] - kz[i-1])/gamrast;
    }

/**************************/
/*** STEP 2: Find largest gradient magnitude with available slew */
/**************************/

/* Current gradient*/
    gx = (kx[i] - kx[i-1])/gamrast;
    gy = (ky[i] - ky[i-1])/gamrast;

/*
// solve for gm using the quadratic equation |gm u - g| = dgc
// which is
//   (gm u - g)(gm u* - g*) = dgc^2
// which gives
//   gm^2 (u u*) - gm (g u* + u g*) + g g* - dgc^2 = 0

// Replacing u u* with 1 (i.e. u is a unit vector) and
// replacing (g u* + u g*) with 2 Real[g u*]
// this is
//   gm^2 + gm (2 b) + c = 0
// giving
//   gm = -b +/- Sqrt(b^2 - c)
// The variable "term" = (b^2 - c) will be positive if we can meet the desired new gradient
*/
    term = dgc*dgc - (gx*gx + gy*gy + gz*gz) + (ux*gx + uy*gy + uz*gz)*(ux*gx + uy*gy + uz*gz);

    if (term >= 0) {
// Slew constraint is met! Now assign next gradient and then next k value
// NOTE gsign is +1 or -1
//   if gsign is positive, we are using slew to speed up (increase gm) as much as possible
//   if gsign is negative, we are using slew to slow down (decrease gm) as much as possible
      gm  = MIN((ux*gx + uy*gy + uz*gz) + gsign[i]*sqrt(term),gmax);
      gx = gm*ux;
      gy = gm*uy;

      kx[i+1] = kx[i] + gx*gamrast;
      ky[i+1] = ky[i] + gy*gamrast;

      if (stype == spSTYPE_SPH_DST)
        kz[i+1] = sqrt(kzmax2*(1.-((kx[i+1]*kx[i+1]+ky[i+1]*ky[i+1])/krmax2))); // stay on surface of ellipsoid
      if (stype == spSTYPE_CYL_DST) {
        krnorm = min(1.,sqrt(kx[i+1]*kx[i+1]+ky[i+1]*ky[i+1])/krmax);
        kz[i+1] = kz0+kznorm*(2./M_PI)*acos(krnorm);
        }
      if (stype == spSTYPE_FLORET) /* RKR FLORET */
        kz[i+1] = sqrt(kx[i+1]*kx[i+1]+ky[i+1]*ky[i+1]);

      i++;
      } // term >= 0
    else {
// We can't go further without violating the slew rate
// This means that we've sped up too fast to turn here at the desired curvature
// We are going to iteratively go back in time and slow down, rather than speed up, at max slew
// Here we'll keep looking back until gsign is positive, then add another negative gsign, just far enough to make the current corner
      while ((i>3) && (gsign[i-1] == -1)) i--;
      gsign[i-1] = -1;
      i = i-2;
      } // term < 0

    kr = sqrt(kx[i]*kx[i] + ky[i]*ky[i]);

    } // MAIN kr loop

  i_end = i;


//********************************************
// DONE LOOPING FOR SAMPLING PORTION
// recast k to g while subsampling by subrast
//********************************************
  gxarray[0] = 0.;
  gyarray[0] = 0.;
  gzarray[0] = 0.;
  gxsum = 0.;
  gysum = 0.;
  gzsum = 0.;
  for (j=1;j<=(i_end/subrast);j++) {
    i1 = j*subrast;
    i0 = (j-1)*subrast;
    gxarray[j] = (kx[i1]-kx[i0])/sub_gamrast;
    gyarray[j] = (ky[i1]-ky[i0])/sub_gamrast;
    gzarray[j] = (kz[i1]-kz[i0])/sub_gamrast;
    gxsum = gxsum + gxarray[j];
    gysum = gysum + gyarray[j];
    gzsum = gzsum + gzarray[j];
    }
  (*spgrad_na) = j;

// recalculate these ending gradient points
  gm = sqrt(gxarray[(*spgrad_na)-1]*gxarray[(*spgrad_na)-1] +
            gyarray[(*spgrad_na)-1]*gyarray[(*spgrad_na)-1] +
            gzarray[(*spgrad_na)-1]*gzarray[(*spgrad_na)-1]);
  ux = gxarray[(*spgrad_na)-1]/gm;
  uy = gyarray[(*spgrad_na)-1]/gm;
  uz = gzarray[(*spgrad_na)-1]/gm;

//**************************************************
// NOW, if requested via gtype, go to g=0 and k=0
// I've tried other ways to be faster, can't find them
//**************************************************

  /* RKR: add plateau before ramp for fast spoiling for FLORET */
    if (gtype == spGTYPE_FSPOIL) {
		gz_sum_ramp = 0;
		gsum = sqrt(gxsum*gxsum + gysum*gysum + gzsum*gzsum);
        double tmp_gsum = gsum;
		gsum_ramp = 0.5*gm*(gm/sub_dgc); /* roughly the area under the ramp */
	    /* spoiler plateau */
        while(tmp_gsum < (2*gsum - gsum_ramp)) /* we want to move out to roughly double the current k-space radius */
        {
		    if (j >= maxarray) /* Check for valid length. ZQL */
		    {
              status = 0;
              free(kx);
              free(ky);
              free(kz);
              free(gsign);
              return status;
		    }
		    gxarray[j] = gm*ux;
		    gyarray[j] = gm*uy;
		    gzarray[j] = gm*uz;
		    gxsum = gxsum + gxarray[j];
		    gysum = gysum + gyarray[j];
		    gzsum = gzsum + gzarray[j];
	        tmp_gsum = sqrt(gxsum*gxsum + gysum*gysum + gzsum*gzsum);
            j++;
	    }
	    /* now ramp down gradients */
        while (gm > 0) {
          if (j >= maxarray) /* Check for valid length. ZQL */
          {
              status = 0;
              free(kx);
              free(ky);
              free(kz);
              free(gsign);
              return status;
          }
          gm = MAX(0,gm - sub_dgc);
          gxarray[j] = gm*ux;
          gyarray[j] = gm*uy;
          gzarray[j] = gm*uz;
          gxsum = gxsum + gxarray[j];
          gysum = gysum + gyarray[j];
          gzsum = gzsum + gzarray[j];
          gz_sum_ramp += gzarray[j];
          j++;
          }
    }
	/* END RKR */

// first we'll ramp gradients to zero
// note {ux,uy} is still pointing in the gradient direction
  else if (gtype > spGTYPE_READOUT) {
    gz_sum_ramp = 0;
    while (gm > 0) {
      if (j >= maxarray) /* Check for valid length. ZQL */
      {
          status = 0;
          free(kx);
          free(ky);
          free(kz);
          free(gsign);
          return status;
      }
      gm = MAX(0,gm - sub_dgc);
      gxarray[j] = gm*ux;
      gyarray[j] = gm*uy;
      gzarray[j] = gm*uz;
      gxsum = gxsum + gxarray[j];
      gysum = gysum + gyarray[j];
      gzsum = gzsum + gzarray[j];
      gz_sum_ramp += gzarray[j];
      j++;
      }
    }
  *spgrad_nb = j;

// now point gradient towards the k-space origin
// {ux,uy} will be a unit vector in that direction
  if (gtype == spGTYPE_REWIND) {

    gsum = sqrt(gxsum*gxsum + gysum*gysum + gzsum*gzsum);
    if (stype == spSTYPE_SPH_DST) gzsum = gzsum + kzmax/sub_gamrast; /* DHW */

    /* JGP just guessing, should check */
    // if (stype == spSTYPE_CYL_DST) gzsum = gzsum + kzmax/sub_gamrast;

    gsum0 = gsum;
    ux = -gxsum/gsum;
    uy = -gysum/gsum;
    uz = -gzsum/gsum;
    gsum_ramp = 0.5*gm*(gm/sub_dgc); /* this is *roughly* how much the area changes if we ramp down the gradient NOW*/
                                     /* this value is zero right now (gm = 0), but it will make sense below */
// increase gm while we can
    while (gsum_ramp < gsum) {
      if (j >= maxarray) /* Check for valid length. ZQL */
      {
          status = 0;
          free(kx);
          free(ky);
          free(kz);
          free(gsign);
          return status;
      }
      gm = MIN(gmax,gm+sub_dgc);
      gxarray[j] = gm*ux;
      gyarray[j] = gm*uy;
      gzarray[j] = gm*uz;
      gsum = gsum - gm;
      j++;
      gsum_ramp = 0.5*gm*(gm/sub_dgc); /* see - now this makes sense; this tells us when to start ramping down */
      }
    /* keep these two parameter for later use */
    gm_center = gm;
    end_rewinder_flat_top = j;


// We've overshot it by a tiny bit, but we'll fix that later
// Ramp down for now
    while (gm > 0) {
      if (j >= maxarray) /* Check for valid length. ZQL */
      {
          status = 0;
          free(kx);
          free(ky);
          free(kz);
          free(gsign);
          return status;
      }
      gm = MAX(0,gm-sub_dgc);
      gxarray[j] = gm*ux;
      gyarray[j] = gm*uy;
      gzarray[j] = gm*uz;
      gsum = gsum - gm;
      j++;
      }
    *spgrad_nc = j;

    /* To avoid increasing amp, and thus slew rate, insert extra point at middle of the rewinder */
    if (gsum > 0)
    {
        int extra_dur = ceil(gsum/gm_center);
        for (j = *spgrad_nc - 1; j >= end_rewinder_flat_top; j--)
        {
            gxarray[j + extra_dur] = gxarray[j];
            gyarray[j + extra_dur] = gyarray[j];
            gzarray[j + extra_dur] = gzarray[j];
        }
        for (j = end_rewinder_flat_top; j < end_rewinder_flat_top + extra_dur; j++)
        {
            gxarray[j] = gm_center*ux;
            gyarray[j] = gm_center*uy;
            gzarray[j] = gm_center*uz;
            gsum = gsum - gm_center;
        }
        *spgrad_nc += extra_dur;
    }

// OK - gm is zero, but gsum is probably not EXACTLY zero. Now scale the rewinder to make the sum exactly zero
    gradtweak = gsum0/(gsum0-gsum);
    for (j=(*spgrad_nb); j<(*spgrad_nc); j++) {
      gxarray[j] = gradtweak*gxarray[j];
      gyarray[j] = gradtweak*gyarray[j];
      gzarray[j] = gradtweak*gzarray[j];
      }
  }

  if (gtype == spGTYPE_M1)
  {
      /* If 1st order moment compensation is desired for z direction
       * in the future, just replace NULL by gzarray.
       */

      if (0 == gradmomentcomp(gxarray, gyarray, NULL /* Off for z axis */, *spgrad_nb, maxarray,
          PHGRAST, gmax, slewmax, 1 /* postscaling */, 0 /* stretching */, spgrad_nc, spgrad_nd))
      {
          *spgrad_nc = 0;
          *spgrad_nd = 0;
          status = 0;
      }
  }

  free (kx);
  free (ky);
  free (kz);
  free (gsign);

  /* check if the number of points reasonable. ZQL */
  switch (gtype)
  {
  case spGTYPE_READOUT: /* spiral only */

      if (*spgrad_na <=0 || *spgrad_na > maxarray)
          status = 0;
      else
          *spgrad_nd = *spgrad_nc = *spgrad_nb = *spgrad_na;
      break;
  case spGTYPE_RAMPDOWN: /* with ramp */
  case spGTYPE_FSPOIL:	/* RKR: fast FLORET spoiling */
      if (*spgrad_na <=0 || *spgrad_nb < *spgrad_na
          || *spgrad_nb > maxarray)
          status = 0;
      else
          *spgrad_nd = *spgrad_nc = *spgrad_nb;
      break;
  case spGTYPE_REWIND: /* with ramp & rewinder */
      if (*spgrad_na <=0 || *spgrad_nb < *spgrad_na
         || *spgrad_nc < *spgrad_nb || *spgrad_nc > maxarray)
          status = 0;
      else
          *spgrad_nd = *spgrad_nc;
      break;
  default:
      if (*spgrad_na <=0 || *spgrad_nb < *spgrad_na
         || *spgrad_nc < *spgrad_nb || *spgrad_nd < *spgrad_nc
         || *spgrad_nd > maxarray)
          status = 0;
      break;
  }
  return status;
}

/* undo common macro names */
#ifdef UNDEFMAX
#undef MAX
#endif

#ifdef UNDEFMIN
#undef MIN
#endif

#endif // BNISPIRALGEN_C -EOF
