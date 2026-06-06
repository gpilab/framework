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


/*********************************************
// Spiral Generation code
**********************************************
// Author: Jim Pipe
// Date: 2020 Oct
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
// This code, revision alpha
// Spiral Trajectory Design: A Flexible Numerical Algorithm and Base Analytical Equations
// Pipe JG, Zwart NR, Magnetic Resonance in Medicine, 71(1), 2014

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

#define SPGRAST    0.005 /* gradient raster time (ms) */
#define subrast    8      /* number of numerical cycles per gradient raster time */

#define spARRSIZE  30     /* array for parameters, adjust as necessary */

/* these are used in the pulse sequence, the GPI node and the python reader */
#define spGAMMA     0
#define spGMAX      1
#define spSLEWMAX   2

#define spTRURES    3

#define spFOV       4
// unused           5
#define spRES       6
// unused           7
#define spARMS      8
#define spINOUT     9

// unused          10
#define spPRECOMP  11
#define spPRECOND  10
#define spUSR0     12
#define spUSR      13
#define spUS0      14
#define spUS1      15

#define spDWELL    16 /* not used by spiralgen(), for resampling after */
#define spREADPTS  17 /* not used by spiralgen(), for recon malloc */

#define spMGFRQ    19
// unused          20
#define spSTWIN    21
#define spENWIN    22
#define spCORWIN   23
#define spGRAD_NA  24
#define spGRAD_NB  25
#define spMAXARRAY 26
#define spGRAD_NT  27
// unused          28
// unused          29

#ifndef M_PI
#define M_PI	3.14159265358979323846	/* MBKO, BNI DHW for M_PI*/
#endif

//*****************************************************************************************
//*****************************************************************************************
//*****************************************************************************************
int spiralgen(double* spparams, int maxarray,  Array<double> &girf, Array<double> &gtf, float *gxarray, float *gyarray,
              float *kxarray, float *kyarray, int *spgrad_na, int *spgrad_nb,
              double *mx0, double *my0, double *mx1, double *my1) {
//*****************************************************************************************
//*****************************************************************************************
//*****************************************************************************************
// girf = gradient impulse response function with values every SPGRAST ms
//        We have forced girf(0) != 0 and sum[girf] = 1
// gtf = |FFT(girf)| after zero-padding - so it's width corresponds 1/SPGRAST
/*****************************************************************************************
  This function takes parameters passed in spparams array and
  returns a single spiral arm calculated numerically

  The corresponding gradient waveforms are in gxarray and gyarray
  spgrad_na reflects the number of gradient points to reach the end of k-space
  spgrad_nb = spgrad_na + the number of gradient points to ramp G to zero

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

*****************************************************************************************/

/*******************/
/* Initializations */
/*******************/

  double rast     = SPGRAST / (double)(subrast);   /* calculation "raster time" in msec */

  double gamma    = spparams[spGAMMA];    /* typically 42.577 kHz/mT */
  double gmax     = spparams[spGMAX];     /* max gradient amplitude in mT/m */
  double gfrqmax  = spparams[spMGFRQ];    /* max gradient freq in kHz */
  double precomp  = spparams[spPRECOMP];  /* flag to do precompensation */
  double precond  = spparams[spPRECOND];  /* flag to do precompensation */
  double start_win = spparams[spSTWIN];   /* rounding window at start (ms) */
  double end_win   = spparams[spENWIN];   /* rounding window at start (ms) */
  double corner_win = spparams[spCORWIN]; /* rounding window between limits (rads) */
  double slewmax  = spparams[spSLEWMAX];  /* max slew rate, in mT/m/msec*/

  double fov    = spparams[spFOV];   /* enter in m */
  double res    = spparams[spRES];   /* enter in m : this should be true resolution */
  double arms   = spparams[spARMS];  /* number of spiral interleaves*/

  double spinout = spparams[spINOUT]; /* 0,1,2 = out, in, out180 */

  /* the next 4 variables are for variable density spirals */
  /* they create a transition in the radial spacing as the k-space radius goes from 0 to 1, i.e.*/
  /*    0 < kr < us_0 : spacing = Nyquist distance */
  /* us_0 < kr < us_1 : spacing increases to us_r (affected by ustype)*/
  /* us_1 < kr < 1    : spacing = us_r*/

  double us_0    = spparams[spUS0];
  double us_1    = spparams[spUS1];
  double us_r    = spparams[spUSR];
  double us_r0    = spparams[spUSR0];

  double fov_eff = fov/double(arms); /* radial distance per arm to meet the Nyquist limit*/
  double gamrast = gamma*rast; /* gamrast*g = dk*/
  double sub_gamrast = (double)(subrast)*gamrast;

  /* START UPDATE FOR GRADIENT LIMITING */
  /* These paramters are for gradient frequency limiting and limit transitions */
  /* The gradient frequency is obtained through (gamma gm)/radius_of_curvature */
  /* Looking up radius_of_curvature in wikipedia gives a formula for calculating in polar coordinates */
  /* This info is all used to make sure that gm does not exceed what is possible for gfrqmax */
  /* See spiral docs for more info */
  double beta;
  double gcap, g1, scap, sterm;
  double corner_fs, corner_sg, corner_fg;
  double sm_mtf, gm_mtf, fq_mtf;
  double transition_fs, transition_sg, transition_fg;
  double ga1, gb1, gc1, ga2, gb2, gc2;
  double sa1, sb1, sc1, sa2, sb2, sc2;
  double g_1, g_2, dg_1, dg_2;
  double s_1, s_2, ds_1, ds_2;
  double gp1, gp2, sp1, sp2, w1, w2;
  double phi1, phi12, phi2;
  /* END UPDATE FOR GRADIENT LIMITING */

  /* START INFO for target function JGP */
  /* Target gradient |MTF| is 1/sqrt[1+(w*tau)^2] */
  /* Limit gmax and slewmax by this with calculated w, to keep precompensated waveform near limits */
  double dtheta, gfrq,gdot;
  double target_mtf = 1;
  double frq_index;
  int fi1, fi2;
  /* END INFO for target function JGP */

  double delta_g;

  double *kx    = NULL;
  double *ky    = NULL;
  double *gx    = NULL;
  double *gy    = NULL;

  double kr, kmx, kmy, kmr, rnorm;
  double rad_spacing=1;
  double alpha, phi, theta;
  double phi_eff, phi_r_eff, phi_eff2;
  double ux=0,uy=0;
  double us_i;
  double gm=0,term;
  double gxsum, gysum;
  double krmax, krmax2;
  double krlim;
  int i, i0, i1, i_end;
  int j;
  int status = 1; /* default set to 1 == SUCCESS */
  int girf_len = girf.size(0);
  int gtf_len  = gtf.size(0);
  // the gtf array spans 1/SPGRAST, 
  //         so its resolution is that amount / gtf_len
  double gtf_res = 1./(double(gtf_len)*SPGRAST);

// kscale is gamma dt res, to convert gradients to k-space
// kscale will also make the default zeropadded resolution
// 0.8 * prescribed resolution for circle
// This should be easier to deal with to calculate the FOV
  double kscale = spparams[spGAMMA]*SPGRAST*spparams[spRES]*0.8/spparams[spTRURES];

  kx = (double*) malloc(subrast*maxarray*sizeof(double));
  ky = (double*) malloc(subrast*maxarray*sizeof(double));
  gx = (double*) malloc(subrast*maxarray*sizeof(double));
  gy = (double*) malloc(subrast*maxarray*sizeof(double));

  if (kx == NULL || ky == NULL || gx == NULL || gy == NULL) {
    printf ("cant allocate memory\n");
    if (kx != NULL) free(kx);
    if (ky != NULL) free(ky);
    if (gx != NULL) free(gx);
    if (gy != NULL) free(gy);
    status = 0;
    return status;
    }

  double g_max, s_max;
  double max_g, max_s;

  g_max = gmax;
  s_max = slewmax;

  for (i=0;i<subrast*maxarray;i++) kx[i] = 0.;
  for (i=0;i<subrast*maxarray;i++) ky[i] = 0.;
  for (i=0;i<subrast*maxarray;i++) gx[i] = 0.;
  for (i=0;i<subrast*maxarray;i++) gy[i] = 0.;
  for (i=0;i<maxarray;i++) {
    gxarray[i] = 0.;
    gyarray[i] = 0.;
    kxarray[i] = 0.;
    kyarray[i] = 0.;
    }
  krmax = 0.5/res;
  krmax2 = krmax*krmax;
  krlim = krmax*(1.-(res/fov));
  theta = 0.;

  /* Initialization */
  *spgrad_na = 0;
  *spgrad_nb = 0;

/* start out spiral going radially (along x) at max slew-rate for 2 time-points */
/* kx, ky, gx, gy [0] = 0 */

  gx[1] = 0.01*s_max*rast;
  kx[1] = gamrast*gx[1];

  gx[2] = gx[1] + 0.02*s_max*rast;
  kx[2] = kx[1] + gamrast*gx[2];

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

    /* determine the undersample factor */
    rnorm = 2.*res*kmr; /* the k-space radius, normalized to go from 0 to 1 */
    if (rnorm <= us_0)
      rad_spacing = us_r0;
    else if (rnorm < us_1) {
      // This is the transition from us_r0 to us_r, which previously could happen with various functions
      // We now use only a hanning window, wanting to keep everything as smooth as possible everywhere
      // in order to avoid adding unecessary high frequency content.  Besides, it probably didn't matter much.
      us_i = (rnorm-us_0)/(us_1 - us_0); /* goes from 0 to 1 as rnorm goes from us_0 to us_1*/
      rad_spacing = us_r0 + (us_r - us_r0)*0.5*(1.-cos(us_i*M_PI)); // hanning window
      } // if (rnorm < us_1)
    else {
      rad_spacing = us_r;
      } // rnorm > us_1

    phi_eff = 2.*M_PI*kmr*(fov_eff/rad_spacing); // this is phi if rad_spacing is constant
    phi_eff2 = phi_eff*phi_eff;
    phi_r_eff = phi_eff*rad_spacing;

/* See the Key Equation 4 at the beginning of the code*/
    alpha = atan(phi_eff);
    phi = atan2(kmy,kmx);
    theta = phi + alpha;
    ux = cos(theta);
    uy = sin(theta);

/****************************************************************************/
/*** STEP 2: Find largest gradient magnitude with available slew            */
/***         This is the biggest change in code from initial version (2014) */
/***                                    to compact-frequency version (2020) */
/****************************************************************************/

    // TARGET_MTF will reduce g_max and s_max depending on instantaneous frequency (gfrq) */
    // use of this function assumes it will vary slowly (!!)
    // also need to normalize some of the values below to account for this later on
    gdot = (gx[i-1]*gx[i] + gy[i-1]*gy[i])/
           (sqrt(gx[i-1]*gx[i-1] + gy[i-1]*gy[i-1])*sqrt(gx[i]*gx[i]+gy[i]*gy[i]));
    gfrq = acos(gdot)/(2.*M_PI*target_mtf*rast); // current gfrq limit

    // Linearly interpolate the target_mtf from the gtf array, based on gfrq
    frq_index = gfrq/gtf_res;
    fi1 = floor(frq_index);
    fi2 = fi1+1;
    w1 = fi2 - frq_index;
    w2 = frq_index - fi1;
    target_mtf = w1*gtf(fi1) + w2*gtf(fi2);

    if (precond == 0) target_mtf = 1.;

    sm_mtf = target_mtf*s_max;
    gm_mtf = target_mtf*g_max;
    fq_mtf = target_mtf*gfrqmax;
    fq_mtf = gfrqmax;

    // transition values are the product of phi and rad_spacing
    // from frequency to slew limited
    transition_fs = gamma*fov_eff*sm_mtf/(2.*M_PI*fq_mtf*fq_mtf);
    // from slew to gradient limited
    transition_sg = 2.*M_PI*gamma*fov_eff*gm_mtf*gm_mtf/sm_mtf;
    // from frequency to gradient limited
    transition_fg = gamma*fov_eff*gm_mtf/fq_mtf;

    corner_fs = MIN(0.48*(transition_sg-transition_fs),MIN(corner_win,0.75*transition_fs));
    corner_sg = MIN(corner_win,0.95*(transition_sg-transition_fs-corner_fs));
    corner_fg = MIN(corner_win,0.75*transition_fg);

    // Decide if we use freq-slew-grad zones or just freq-grad
    if (transition_fg-corner_fg > transition_fs-corner_fs) {

      if (phi_r_eff < (transition_fs-corner_fs)) { // FREQ LIMITED REGIME
        gcap = ((fq_mtf*rad_spacing)/(gamma*fov_eff))*pow(phi_eff2+1.,1.5)/(phi_eff2+2);
        gcap = min(gcap,gm_mtf);
        sterm = sqrt(1+(phi_eff2*pow((phi_eff2+4),2.)/pow((phi_eff2+2),4.))); // this term stays pretty close to 1
        scap = 2.*M_PI*fq_mtf*sterm*gcap;
        scap = min(scap,sm_mtf);
        }

      else if (phi_r_eff < (transition_fs+corner_fs)) { // TRANSITION #1
        // Do a spline fit, with parabolas y = a + b*phi + c*phi^2:
        //  parabola 1 fit to the LHS value and slope and RHS value,
        //  parabola 2 fit to the RHS value and slope and LHS value,
        //  then perform a linear interpolation between them

        // values and slopes for LHS
        phi1 = (transition_fs-corner_fs)/rad_spacing;
        phi12 = phi1*phi1;
        g_1 = ((fq_mtf*rad_spacing)/(gamma*fov_eff))*pow(phi12+1.,1.5)/(phi12+2);
        g_1 = min(g_1,gm_mtf);
        sterm = sqrt(1+(phi12*pow((phi12+4),2.)/pow((phi12+2),4.))); // this term stays pretty close to 1
        s_1 = 2.*M_PI*fq_mtf*sterm*g_1;
        s_1 = min(s_1,sm_mtf);
        dg_1 = ((fq_mtf*rad_spacing)/(gamma*fov_eff));
        ds_1 = 2.*M_PI*fq_mtf*dg_1;

        // values and slopes for RHS
        phi2 = (transition_fs+corner_fs)/rad_spacing;
        g_2  =     sqrt(sm_mtf*phi2*rad_spacing/(2.*M_PI*gamma*fov_eff));
        g_2 = min(g_2,gm_mtf);
        dg_2 = 0.5*sqrt(sm_mtf*     rad_spacing/(2.*M_PI*gamma*fov_eff*phi2));
        s_2  = sm_mtf;
        s_2 = min(s_2,sm_mtf);
        ds_2 = 0;

        // Parabola 1
        ga1 = g_1;
        gb1 = dg_1;
        gc1 = (g_2 - ga1 - gb1*(phi2 - phi1))/((phi2-phi1)*(phi2-phi1));
        gp1 = ga1 + gb1*(phi_eff-phi1) + gc1*(phi_eff-phi1)*(phi_eff-phi1);

        sa1 = s_1;
        sb1 = ds_1;
        sc1 = (s_2 - sa1 - sb1*(phi2 - phi1))/((phi2-phi1)*(phi2-phi1));
        sp1 = sa1 + sb1*(phi_eff-phi1) + sc1*(phi_eff-phi1)*(phi_eff-phi1);

        // Parabola 2
        ga2 = g_2;
        gb2 = dg_2;
        gc2 = (g_1 - ga2 - gb2*(phi1 - phi2))/((phi1-phi2)*(phi1-phi2));
        gp2 = ga2 + gb2*(phi_eff-phi2) + gc2*(phi_eff-phi2)*(phi_eff-phi2);

        sa2 = s_2;
        sb2 = ds_2;
        sc2 = (s_1 - sa2 - sb2*(phi1 - phi2))/((phi1-phi2)*(phi1-phi2));
        sp2 = sa2 + sb2*(phi_eff-phi2) + sc2*(phi_eff-phi2)*(phi_eff-phi2);

        // Linear Interpolation
        w2 = (phi_eff-phi1)/(2.*corner_fs);
        w1 = 1.-w2;

        gcap = w1*gp1 + w2*gp2;
        gcap = min(gcap, gm_mtf);
        scap = w1*sp1 + w2*sp2;
        scap = min(scap, sm_mtf);
        }

      else if (phi_r_eff < (transition_sg-corner_sg)) { // SLEW LIMITED REGIME
        gcap = sqrt(sm_mtf*phi_r_eff/(2.*M_PI*gamma*fov_eff));
        gcap = min(gcap, gm_mtf);
        scap = sm_mtf;
        }

      else if (phi_r_eff < (transition_sg+corner_sg)) { // TRANSITION #2

        // See TRANSITION #1 comments - here scap remains a constant
        scap = sm_mtf;

        // values and slopes for LHS
        phi1 = (transition_sg-corner_sg)/rad_spacing;
        g_1  =     sqrt(sm_mtf*phi1*rad_spacing/(2.*M_PI*gamma*fov_eff));
        g_1 = min(g_1, gm_mtf);
        dg_1 = 0.5*sqrt(sm_mtf*     rad_spacing/(2.*M_PI*gamma*fov_eff*phi1));

        // values and slopes for LHS
        phi2 = (transition_sg+corner_sg)/rad_spacing;
        g_2 = gm_mtf;
        dg_2 = 0;

        // Parabola 1
        ga1 = g_1;
        gb1 = dg_1;
        gc1 = (g_2 - ga1 - gb1*(phi2 - phi1))/((phi2-phi1)*(phi2-phi1));
        gp1 = ga1 + gb1*(phi_eff-phi1) + gc1*(phi_eff-phi1)*(phi_eff-phi1);

        // Parabola 2
        ga2 = g_2;
        gb2 = dg_2;
        gc2 = (g_1 - ga2 - gb2*(phi1 - phi2))/((phi1-phi2)*(phi1-phi2));
        gp2 = ga2 + gb2*(phi_eff-phi2) + gc2*(phi_eff-phi2)*(phi_eff-phi2);

        // Linear Interpolation
        w2 = (phi_eff-phi1)/(2.*corner_sg);
        w1 = 1.-w2;
        gcap = w1*gp1 + w2*gp2;
        gcap = min(gcap, gm_mtf);
        }

      else { // GRAD LIMITED REGIME
        gcap = gm_mtf;
        scap = sm_mtf;
        }

      } // fmax -> smax -> gmax

    else {
      // transition from freq limited to grad limited, skip slew limited

      if (phi_r_eff < (transition_fg-corner_fg)) { // FREQ LIMITED REGIME
        gcap = ((fq_mtf*rad_spacing)/(gamma*fov_eff))*pow(phi_eff2+1.,1.5)/(phi_eff2+2);
        gcap = min(gcap, gm_mtf);
        sterm = sqrt(1+(phi_eff2*pow((phi_eff2+4),2.)/pow((phi_eff2+2),4.))); // this term stays pretty close to 1
        scap = 2.*M_PI*fq_mtf*sterm*gcap;
        scap = min(scap, sm_mtf);
        }

      else if (phi_r_eff < (transition_fg+corner_fg)) { // TRANSITION #1
        // values and slopes for LHS
        phi1 = (transition_fg-corner_fg)/rad_spacing;
        phi12 = phi1*phi1;
        g_1 = ((fq_mtf*rad_spacing)/(gamma*fov_eff))*pow(phi12+1.,1.5)/(phi12+2);
        g_1 = min(g_1, gm_mtf);
        sterm = sqrt(1+(phi12*pow((phi12+4),2.)/pow((phi12+2),4.))); // this term stays pretty close to 1
        s_1 = 2.*M_PI*fq_mtf*sterm*g_1;
        s_1 = min(s_1, sm_mtf);
        dg_1 = ((fq_mtf*rad_spacing)/(gamma*fov_eff));
        ds_1 = 2.*M_PI*fq_mtf*dg_1;

        // values and slopes for RHS
        phi2 = (transition_fg+corner_fg)/rad_spacing;
        g_2  = gm_mtf;
        dg_2 = 0;
        s_2  = sm_mtf;
        ds_2 = 0;

        // Parabola 1
        ga1 = g_1;
        gb1 = dg_1;
        gc1 = (g_2 - ga1 - gb1*(phi2 - phi1))/((phi2-phi1)*(phi2-phi1));
        gp1 = ga1 + gb1*(phi_eff-phi1) + gc1*(phi_eff-phi1)*(phi_eff-phi1);

        sa1 = s_1;
        sb1 = ds_1;
        sc1 = (s_2 - sa1 - sb1*(phi2 - phi1))/((phi2-phi1)*(phi2-phi1));
        sp1 = sa1 + sb1*(phi_eff-phi1) + sc1*(phi_eff-phi1)*(phi_eff-phi1);

        // Parabola 2
        ga2 = g_2;
        gb2 = dg_2;
        gc2 = (g_1 - ga2 - gb2*(phi1 - phi2))/((phi1-phi2)*(phi1-phi2));
        gp2 = ga2 + gb2*(phi_eff-phi2) + gc2*(phi_eff-phi2)*(phi_eff-phi2);

        sa2 = s_2;
        sb2 = ds_2;
        sc2 = (s_1 - sa2 - sb2*(phi1 - phi2))/((phi1-phi2)*(phi1-phi2));
        sp2 = sa2 + sb2*(phi_eff-phi2) + sc2*(phi_eff-phi2)*(phi_eff-phi2);

        // Linear Interpolation
        w2 = (phi_eff-phi1)/(2.*corner_fg);
        w1 = 1.-w2;

        gcap = w1*gp1 + w2*gp2;
        scap = w1*sp1 + w2*sp2;
        }

      else { // GRAD LIMITED REGIME
        gcap = gm_mtf;
        scap = sm_mtf;
        }

      } // fmax -> gmax

    // No matter when this is, we can slow down the start
    if (double(i)*rast < start_win) { // INITIAL TRANSITION
      // taking sqrt() based on empirical design and assumption that t goes roughly w/ sqrt(phi)
      scap *= sin(0.5*M_PI*double(i)*rast/start_win);
      }


/**************************/
/*** STEP 3: Find largest gradient magnitude with available slew */
/**************************/
// solve for gm using the quadratic equation |gm u - g| = slew*rast, or
//   gm^2 (u u*) - gm (g u* + u g*) + g g* - (slew*rast)^2 = 0

// Replacing u u* with 1 (i.e. u is a unit vector) and (g u* + u g*) with 2 Real[g u*] gives
//   gm^2 + gm (2 b) + c = 0, so
//   gm = -b +/- Sqrt(b^2 - c)
// The variable "term" = (b^2 - c) will be positive if we can meet the desired new gradient

    delta_g = scap*rast;
    term = (delta_g*delta_g) - (gx[i]*gx[i] + gy[i]*gy[i]) + (ux*gx[i] + uy*gy[i])*(ux*gx[i] + uy*gy[i]);

    if (term >= 0) {
// Slew constraint is met! Now assign next gradient and then next k value
// Note we add sqrt(b^2-c) rather than subtract to grow gm

      g1 = ux*gx[i] + uy*gy[i] + sqrt(term);
      gm  = MIN(g1,gcap);

/* END UPDATE FOR GRADIENT FREQ LIMITING */
      gx[i+1] = gm*ux;
      gy[i+1] = gm*uy;

      } // term >= 0

    else {

// We can't go further without violating the slew rate
// This means that we've sped up too fast to turn here at the desired curvature
// We are going to use all our slew to turn, and keep gm constant
// This will mean we move off the desired path, but rather than use previous iterative gsign method
//      we just keep gm and slew constant to keep the smoothest g possible

      printf("Couldn't make corner at i = %d with term = %f\n",i,term);

      // determine dtheta given current slew using slew = (dtheta/dt)*gm
      dtheta = rast*scap/sqrt(gx[i]*gx[i]+gy[i]*gy[i]);

      // dtermine sign of dtheta - same as targeted rotation from (gx,gy) to (ux,uy)
      // use sign of "g cross u" which is proportional to sine(angle)
      if ((gx[i]*uy - gy[i]*ux) < 0)
        dtheta = -dtheta;

      // rotate gx,gy
      gx[i+1] = cos(dtheta)*gx[i] - sin(dtheta)*gy[i];
      gy[i+1] = cos(dtheta)*gy[i] + sin(dtheta)*gx[i];

      } // term < 0

    kx[i+1] = kx[i] + gx[i+1]*gamrast;
    ky[i+1] = ky[i] + gy[i+1]*gamrast;
    i++;

    kr = sqrt(kx[i]*kx[i] + ky[i]*ky[i]);

    } // MAIN kr loop

  i_end = i;

//***********************************************************************
//***********************************************************************
// DONE LOOPING FOR SAMPLING PORTION
// recast k to g while subsampling by subrast
// kxarray, kyarray are coordinates calculated before pecompensation
//***********************************************************************
//***********************************************************************
  gxarray[0] = 0.;
  gyarray[0] = 0.;
  kxarray[0] = 0.;
  kyarray[0] = 0.;
  gxsum = 0.;
  gysum = 0.;
  for (j=1;j<=(i_end/subrast);j++) {
    i1 = j*subrast;
    i0 = (j-1)*subrast;
    gxarray[j] = (kx[i1]-kx[i0])/sub_gamrast;
    gyarray[j] = (ky[i1]-ky[i0])/sub_gamrast;
    kxarray[j] = kxarray[j-1] + kscale*gxarray[j];
    kyarray[j] = kyarray[j-1] + kscale*gyarray[j];
    gxsum = gxsum + gxarray[j];
    gysum = gysum + gyarray[j];
    }
  (*spgrad_na) = j;

//**************************************************
//  Ramp down
//**************************************************
  double beta0, a_hann, b_hann;
  double gm0, dgm0, dgm;
  double theta0,freq0,freqmax,slew0,dtheta0;
  double t_remain, a_down;
  int j0;

// Ramp Gradient magnitude down to zero with Cosine
//  gm0 = a cos[b t]
// dgm0 = -ab sin[b t] = -slew sin[b t]

// (also added an optional smooth ending for last "end_win" ms, see below)

// define beta = b t
// when beta=0, gm' is zero
// when beta = pi, gm is zero

// First calculate gm0, dgm0, theta, dtheta, and slew0 = current slew
// If gm is still rising (we are still in the slew-limited part of spiral), beta is negative

  gm0 = sqrt(gxarray[(*spgrad_na)-1]*gxarray[(*spgrad_na)-1] +
             gyarray[(*spgrad_na)-1]*gyarray[(*spgrad_na)-1]);
  dgm0  = (gm0 - sqrt(gxarray[(*spgrad_na)-2]*gxarray[(*spgrad_na)-2] +
                      gyarray[(*spgrad_na)-2]*gyarray[(*spgrad_na)-2]))/SPGRAST;
  theta0 =          atan2(gyarray[(*spgrad_na)-1],gxarray[(*spgrad_na)-1]);
  dtheta = theta0 - atan2(gyarray[(*spgrad_na)-2],gxarray[(*spgrad_na)-2]);
  if (dtheta < M_PI) dtheta += 2.*M_PI;
  if (dtheta > M_PI) dtheta -= 2.*M_PI;
  dtheta0 = dtheta;
  freq0 = dtheta0/SPGRAST;
  slew0 = sqrt(dgm0*dgm0 + freq0*freq0*gm0*gm0);

// Now calculate parameters for hanning window for gm
  // beta0 is where we are now; beta0 < 0 implies gm is still increasing
  beta0 = asin(-dgm0/slew0); 
  a_hann = gm0/cos(beta0);
  b_hann = slew0/a_hann;
    
// get ready to start
  j0 = j-1;
  beta = beta0;
  theta = theta0;

  while (beta < 0.5*M_PI) {
    if (j >= maxarray) { /* Check for valid length. ZQL */
      status = 0;
      free(gx); free(gy);
      free(kx); free(ky);
      return status;
      }

    beta = beta0 + SPGRAST*(j-j0)*b_hann; 
    gm = min(gcap,a_hann*cos(beta));
    dgm = -slew0*sin(beta);

    // Until beta reaches 0, keep dtheta constant, or limit if necessary
    // For beta > 0, it goes down as cos(beta)
    if (beta > 0.)
      dtheta = dtheta0*cos(beta);
    freqmax = sqrt((slew0*slew0) - (dgm*dgm))/gm;
    dtheta = min(dtheta,freqmax*SPGRAST);
    theta += dtheta;

    // Reset dtheta0 if gm still increasing
    if (beta < 0.)
      dtheta0 = dtheta;
     
    gxarray[j] = gm*cos(theta);
    gyarray[j] = gm*sin(theta);
    gxsum = gxsum + gxarray[j];
    gysum = gysum + gyarray[j];

    j++;

    // Enforce a smooth rampdown with duration end_win
    // End with a quadratic term, gm = a t^2
    //                           dgm = 2a t
    // where t is the time from the end of rampdown (t is "backwards" with respect to j)
    // Note gm/dgm = t/2
    // We want to start this at t = end_win
    //    i.e. start with gm / dgm = end_win/2
    if (dgm != 0.) {
      if (abs(gm/dgm) <= end_win/2.) {
        beta = M_PI; // this just stops outer rampdown loop
        t_remain = 2.*abs(gm/dgm);
        a_down = 0.5*abs(dgm)/t_remain;
        t_remain -= SPGRAST;
        while (t_remain > 0.) {
          if (j >= maxarray) { /* Check for valid length. ZQL */
            status = 0;
            free(gx); free(gy);
            free(kx); free(ky);
            return status;
            }
          gm = a_down*t_remain*t_remain;
          dtheta = dtheta0*(gm/a_hann); // (gm/a_hann) -> cos(beta)
          theta += dtheta;

          gxarray[j] = gm*cos(theta);
          gyarray[j] = gm*sin(theta);
          gxsum = gxsum + gxarray[j];
          gysum = gysum + gyarray[j];

          t_remain -= SPGRAST;
          j++;
          }
        }
      }

    }

  *spgrad_nb = j;

//**************************************************
//  Calculate M0 and M1
//  We do this before precompensation, presuming this is more accurate
//**************************************************
  *mx0 = gxsum * SPGRAST; // 0th moment in (mT/m)*ms;
  *my0 = gysum * SPGRAST; // 0th moment in (mT/m)*ms;

  *mx1 = *my1 = 0;
  // time = 0 at the end of the spiral waveform (ramp)
  for (j = *spgrad_nb - 1; j >= 0; j--) {
    *mx1 = *mx1 + SPGRAST*(double)(j - *spgrad_nb)*gxarray[j]*SPGRAST;
    *my1 = *my1 + SPGRAST*(double)(j - *spgrad_nb)*gyarray[j]*SPGRAST;
    }

//**************************************************
//  FLIP AND NEGATE IF DESIRED
//**************************************************
  if (spinout == 1) { // SPIRAL IN => FLIP
    double gxtemp, gytemp;
    double kxtemp, kytemp;
    for (j = 0; j < ((*spgrad_nb)/2); j++) {
      gxtemp = gxarray[j];
      gytemp = gyarray[j];
      gxarray[j] = gxarray[*spgrad_nb-1-j];
      gxarray[*spgrad_nb-1-j] = gxtemp;
      gyarray[j] = gyarray[*spgrad_nb-1-j];
      gyarray[*spgrad_nb-1-j] = gytemp;
      }
    for (j = 0; j < ((*spgrad_na)/2); j++) {
      kxtemp = kxarray[j];
      kytemp = kyarray[j];
      kxarray[j] = kxarray[*spgrad_na-1-j];
      kxarray[*spgrad_na-1-j] = kxtemp;
      kyarray[j] = kyarray[*spgrad_na-1-j];
      kyarray[*spgrad_na-1-j] = kytemp;
      }
    }

  if (spinout == 2) { // SPIRAL OUT180 => NEGATE
    for (j = 0; j < *spgrad_nb; j++) {
      gxarray[j] *= -1;
      gyarray[j] *= -1;
      }
    for (j = 0; j < *spgrad_na; j++) {
      kxarray[j] *= -1;
      kyarray[j] *= -1;
      }
    *mx0 = -(*mx0);
    *my0 = -(*my0);
    *mx1 = -(*mx1);
    *my1 = -(*my1);
    }

//**************************************************
//  PRECOMPENSATE IF DESIRED
//**************************************************
  if (precomp == 1 && girf_len > 1) {
    double hxsum, hysum;
    double tmp_g, tmp_slew;
    double dxi, dyi;

    max_g = 0;
    max_s = 0;

    // extend duration by 2 time constants to get tail
    *spgrad_nb = MIN(maxarray, *spgrad_nb + girf_len);

    for (i = 0; i < *spgrad_nb; i++) {

      // deconvolution
      hxsum = 0;
      hysum = 0;
      for (j=1; j<= min(i,girf_len-1); j++) {
	hxsum += gxarray[i-j]*girf(j);
	hysum += gyarray[i-j]*girf(j);
	}
      gxarray[i] = (gxarray[i]-hxsum)/girf(0);
      gyarray[i] = (gyarray[i]-hysum)/girf(0);

      // Check for max grad^2, max slew^2
      tmp_g = gxarray[i] * gxarray[i] + gyarray[i] * gyarray[i];
      if (tmp_g > max_g) {
        max_g = tmp_g;
        }

      if (i > 0) {
        dxi = (gxarray[i] - gxarray[i - 1]);
        dyi = (gyarray[i] - gyarray[i - 1]);
        tmp_slew = dxi * dxi + dyi * dyi;
        }

      if (tmp_slew > max_s) {
        max_s = tmp_slew;
        }

      }

    max_g = sqrt(max_g);
    max_s = sqrt(max_s)/SPGRAST;
    printf("after precompensation, max g and s are %f and %f\n",max_g, max_s);

    }

  free(gx);
  free(gy);
  free(kx);
  free(ky);

  return status;
  } // spiralgen

/* undo common macro names */
#ifdef UNDEFMAX
#undef MAX
#endif

#ifdef UNDEFMIN
#undef MIN
#endif
