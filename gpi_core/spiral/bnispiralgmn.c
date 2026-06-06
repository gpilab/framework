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
 * spiral waveform post moment compenstation.
**********************************************
 * Author: Zhiqiang Li
 * Date: August 2012
 *********************************************/

#define GRAD_MIDDLE   1
#define GRAD_RIGHT    2
#define TRAP_TRIANGLE 1
#define TRAP_TRAP     2

int solution_analytical(int G_type, double As, double m1s, double maxgrad,
    double gdwell, int N1c, double Ac, int *n1m, int *n2m, int *n1r,
    int *n2r, double *am, double *ar);

int  solution_search(int G_flag, int init_N_bot, int init_N_up,
    double init_m1_bot, double init_m1_up, double As, double m1s,
    double maxgrad, double gdwell, int N1c, double Ac, int *n1m,
    int *n2m, int *n1r, int *n2r, double *am, double *ar);

int solution_pos_neg(double As, double m1s, double maxgrad,
    double gdwell, int N1c, double Ac, int *n1m, int *n2m,
    int *n1r, int *n2r, double *am, double *ar);

void gradtrap(double gdwell, double maxgrad, double area, double Ac,
    int N1c, double *amp, int *nslope, int *nflattop);

void gradmoment_array(int arraysize, double gdwell, int nstart,
    float *garray, double *m0array, double *m1array, double *m0_end,
    double *m1_end);

void gradmoment_trap(int nslope, int nflattop, int nstart, double amp,
    double gdwell, double *m0_end, double *m1_end);

int gradmomentcomp_oneaxis(double As, double m1s, int spgrad_nb, int maxlen, double gdwell,
    double maxgrad, double maxslew, int postscaling, int *n1m, int *n2m, double *am,
    int *n1r, int *n2r, double *ar);

int gradmomentcomp(float *garrayx, float *garrayy, float *garrayz, int spgrad_nb,
    int maxlen, double gdwell, double maxgrad_0, double maxslew_0, int postscaling,
    int stretchingflag, int *spgrad_nc, int *spgrad_nd);

/**********************************************************************
 * Funtion:     gradmomentcom
 * Description: 0th and 1st order gradient moment compensation. The
 *              waveform for compensation will be added to existing
 *              waveform.
 * Parameters:
 *              (I/O) *garrayx: x waveform to be compensated.
 *              (I/O) *garrayy: y waveform to be compensated.
 *              (I/O) *garrayz: z waveform to be compensated.
 *              (I) spgrad_nb: length of original garray
 *              (I) maxlen: max available length of garray
 *              (I) gdwell: gradient dwelling time
 *              (I) maxgrad_0: max gradient strength
 *              (I) maxslew_0: max gradient slew rate
 *              (I) postscaling: flag for scaling gradient
 *              (O) *spgrad_nc: length of array till end of middle gradient
 *              (O) *spgrad_nd: length of array till end of right gradient
 * Return:      0 (Failure) or 1 (Success)
 *********************************************************************/
int gradmomentcomp(float *garrayx, float *garrayy, float *garrayz, int spgrad_nb,
    int maxlen, double gdwell, double maxgrad_0, double maxslew_0, int postscaling,
    int stretchingflag, int *spgrad_nc, int *spgrad_nd)
{
    int n1m   = 0;
    int n1m_x = 0;
    int n1m_y = 0;
    int n1m_z = 0;
    int n1r   = 0;
    int n1r_x = 0;
    int n1r_y = 0;
    int n1r_z = 0;
    int n2m   = 0;
    int n2m_x = 0;
    int n2m_y = 0;
    int n2m_z = 0;
    int n2r   = 0;
    int n2r_x = 0;
    int n2r_y = 0;
    int n2r_z = 0;
    int axis  = 0;
    int Naxis = 0;
    int i     = 0;
    int idx   = 0;
    int totalm_x = 0;
    int totalm_y = 0;
    int totalm_z = 0;
    int totalr_x = 0;
    int totalr_y = 0;
    int totalr_z = 0;

    double am   = 0.0;
    double am_x = 0.0;
    double am_y = 0.0;
    double am_z = 0.0;
    double ar   = 0.0;
    double ar_x = 0.0;
    double ar_y = 0.0;
    double ar_z = 0.0;
    // AGA - unused 2015-10-13
    // double A    = 0.0;
    // double m1   = 0.0;
    double As_x = 0.0;
    double As_y = 0.0;
    double As_z = 0.0;
    double Am_x = 0.0;
    double Am_y = 0.0;
    double Am_z = 0.0;
    double Ar_x = 0.0;
    double Ar_y = 0.0;
    double Ar_z = 0.0;
    double m1s_x = 0.0;
    double m1s_y = 0.0;
    double m1s_z = 0.0;

    double maxgrad = 0.0;
    double maxslew = 0.0;

    if (garrayz == NULL)
    {
        maxgrad = maxgrad_0/sqrt(2.0);
        maxslew = maxslew_0/sqrt(2.0);
    }
    else
    {
        maxgrad = maxgrad_0/sqrt(3.0);
        maxslew = maxslew_0/sqrt(3.0);
    }
    /* for x axis, calculate 0th/1st order moment, and then perform compensation */
    gradmoment_array(spgrad_nb, gdwell, -spgrad_nb, garrayx, NULL, NULL, &As_x, &m1s_x);
    if (0 == gradmomentcomp_oneaxis(As_x, m1s_x, spgrad_nb, maxlen, gdwell, maxgrad,
        maxslew, postscaling, &n1m_x, &n2m_x, &am_x, &n1r_x, &n2r_x, &ar_x))
    {
        return 0;
    }

    gradmoment_array(spgrad_nb, gdwell, -spgrad_nb, garrayy, NULL, NULL, &As_y, &m1s_y);
    if (0 == gradmomentcomp_oneaxis(As_y, m1s_y, spgrad_nb, maxlen, gdwell, maxgrad,
        maxslew, postscaling, &n1m_y, &n2m_y, &am_y, &n1r_y, &n2r_y, &ar_y))
    {
        return 0;
    }

    if (garrayz != NULL)
    {
        gradmoment_array(spgrad_nb, gdwell, -spgrad_nb, garrayz, NULL, NULL, &As_z, &m1s_z);
        if (0 == gradmomentcomp_oneaxis(As_z, m1s_z, spgrad_nb, maxlen, gdwell, maxgrad,
            maxslew, postscaling, &n1m_z, &n2m_z, &am_z, &n1r_z, &n2r_z, &ar_z))
        {
            return 0;
        }
    }

    /* starting to stretch gradient waveform for x/y/z */
    if (stretchingflag == 1)
    {

        int Nm = 0;
        int Nr = 0;

        double bm_x = 0.0;
        double bm_y = 0.0;
        double bm_z = 0.0;
        double br_x = 0.0;
        double br_y = 0.0;
        double br_z = 0.0;

        /* determine max duration for middle and right gradient */
        if ((2*n1m_x + n2m_x) > (2*n1m_y + n2m_y))
        {
            Nm = 2*n1m_x + n2m_x;
        }
        else
        {
            Nm = 2*n1m_y + n2m_y;
        }

        if (garrayz != NULL && Nm < (2*n1m_z + n2m_z))
        {
            Nm = 2*n1m_z + n2m_z;
        }

        if ((2*n1r_x + n2r_x) > (2*n1r_y + n2r_y))
        {
            Nr = 2*n1r_x + n2r_x;
        }
        else
        {
            Nr = 2*n1r_y + n2r_y;
        }

        if (garrayz != NULL && Nm < (2*n1r_z + n2r_z))
        {
            Nr = 2*n1r_z + n2r_z;
        }

        /* To get Am & Ar, solve
         *    As + Am + Ar = 0
         *    m1s + Am*(Nm-1)/2*gdwell + Ar*(Nm + (Nr-1)/2)*gdwell = 0
         * gives
         *    Ar = (As*(Nm-1)*gdwell - 2.0*m1s)/((Nm+Nr)*gdwell)
         *       = As*(Nm-1)/(Nm+Nr) - 2.0*m1s/gdwell/(Nm+Nr)
         *       = As*ca - m1s*cb
         * where ca = (Nm-1)/(Nm+Nr)
         *       cb = 2.0/gdwell/(Nm+Nr);
         *
         * To get n1 given the area and slew rate, solve
         *    (N-n1-1)*gdwell * (n1*gdwell*maxslew) = A
         * or
         *    (N-1-n1)*n1 = A/(gdwell^2*maxslew)
         * or n1^2 - (N-1)*n1 + A/(gdwell^2*maxslew) = 0
         * let
         *    bm = (N-1)^2 - 4*A/(gdwell^2*maxslew)
         * then
         *    n1 = 0.5*((N-1) - sqrt(bm))
         *
         * let cc = 4.0/(gdwell*gdwell*maxslew)
         *    bm = (N-1)^2 - A*cc
         */

        double ca = (double)(Nm-1)/(double)(Nm+Nr);
        double cb = 2.0/(gdwell*(double)(Nm+Nr));
        double cc = 4.0/(maxslew*gdwell*gdwell);

        Ar_x = As_x*ca - m1s_x*cb;
        br_x = (double)(Nr*Nr) - fabs(Ar_x)*cc;
        Am_x = -(As_x+Ar_x);
        bm_x = (double)(Nm*Nm) - fabs(Am_x)*cc;

        Ar_y = As_y*ca - m1s_y*cb;
        br_y = (double)(Nr*Nr) - fabs(Ar_y)*cc;
        Am_y = -(As_y+Ar_y);
        bm_y = (double)(Nm*Nm) - fabs(Am_y)*cc;
        if (garrayz != NULL)
        {
            Ar_z = As_z*ca - m1s_z*cb;
            br_z = (double)(Nr*Nr) - fabs(Ar_z)*cc;
            Am_z = -(As_z+Ar_z);
            bm_z = (double)(Nm*Nm) - fabs(Am_z)*cc;
        }
        else
        {
          br_z = 0;
          bm_z = 0;
        }

        if (bm_x < 0 || br_x < 0 || bm_y < 0 || br_y < 0 || bm_z < 0 || br_z < 0)
        {
          /* skip stretching */
        }
        else /* try to stretch gradient */
        {
          int tmp_n1m_x = 0;
          int tmp_n2m_x = 0;
          int tmp_n1r_x = 0;
          int tmp_n2r_x = 0;
          int tmp_n1m_y = 0;
          int tmp_n2m_y = 0;
          int tmp_n1r_y = 0;
          int tmp_n2r_y = 0;
          int tmp_n1m_z = 0;
          int tmp_n2m_z = 0;
          int tmp_n1r_z = 0;
          int tmp_n2r_z = 0;
          double tmp_am_x = 0.0;
          double tmp_ar_x = 0.0;
          double tmp_am_y = 0.0;
          double tmp_ar_y = 0.0;
          double tmp_am_z = 0.0;
          double tmp_ar_z = 0.0;

          /* Determine duration and amplitude */
          tmp_n1m_x = ceil(((double)Nm - sqrt(bm_x))/2.0);
          tmp_n2m_x = Nm - 2*tmp_n1m_x;
          tmp_am_x  = Am_x/((double)(Nm -1 - tmp_n1m_x)*gdwell);

          tmp_n1r_x = ceil(((double)Nr - sqrt(br_x))/2.0);
          tmp_n2r_x = Nr - 2*tmp_n1r_x;
          tmp_ar_x  = Ar_x/((double)(Nr -1 - tmp_n1r_x)*gdwell);

          tmp_n1m_y = ceil(((double)Nm - sqrt(bm_y))/2.0);
          tmp_n2m_y = Nm - 2*tmp_n1m_y;
          tmp_am_y  = Am_y/((double)(Nm -1 - tmp_n1m_y)*gdwell);

          tmp_n1r_y = ceil(((double)Nr - sqrt(br_y))/2.0);
          tmp_n2r_y = Nr - 2*tmp_n1r_y;
          tmp_ar_y  = Ar_y/((double)(Nr -1 - tmp_n1r_y)*gdwell);

          if (garrayz != NULL)
          {
            tmp_n1m_z = ceil(((double)Nm - sqrt(bm_z))/2.0);
            tmp_n2m_z = Nm - 2*tmp_n1m_z;
            tmp_am_z  = Am_z/(double)(Nm -1 - tmp_n1m_z);
            tmp_n1r_z = ceil(((double)Nr - sqrt(br_z))/2.0);
            tmp_n2r_z = Nr - 2*tmp_n1r_z;
            tmp_ar_z  = Ar_z/(double)(Nr -1 - tmp_n1r_z);
          }

          if (   fabs(tmp_am_x) > maxgrad || fabs(tmp_am_y) > maxgrad || fabs(tmp_am_z) > maxgrad
              || fabs(tmp_ar_x) > maxgrad || fabs(tmp_ar_y) > maxgrad || fabs(tmp_ar_z) > maxgrad)
          {
            /* solution invalid */
            /* skip stretching */
          }
          else if (tmp_n1m_x < 0 || tmp_n1m_y < 0 || tmp_n1m_z < 0
                || tmp_n2m_x < 0 || tmp_n2m_y < 0 || tmp_n2m_z < 0
                || tmp_n1r_x < 0 || tmp_n1r_y < 0 || tmp_n1r_z < 0
                || tmp_n2r_x < 0 || tmp_n2r_y < 0 || tmp_n2r_z < 0)
          {
            /* solution invalid */
            /* skip stretching */
          }
          else
          {
            /* solution valid */
            n1m_x = tmp_n1m_x;
            n2m_x = tmp_n2m_x;
            am_x = tmp_am_x;
            n1r_x = tmp_n1r_x;
            n2r_x = tmp_n2r_x;
            ar_x = tmp_ar_x;
            n1m_y = tmp_n1m_y;
            n2m_y = tmp_n2m_y;
            am_y = tmp_am_y;
            n1r_y = tmp_n1r_y;
            n2r_y = tmp_n2r_y;
            ar_y = tmp_ar_y;
            if (garrayz != NULL)
            {
                n1m_z = tmp_n1m_z;
                n2m_z = tmp_n2m_z;
                am_z = tmp_am_z;
                n1r_z = tmp_n1r_z;
                n2r_z = tmp_n2r_z;
                ar_z = tmp_ar_z;
            }
          }
        }
    }

    /* set gradient length */
    totalm_x = 2*n1m_x + n2m_x;
    totalr_x = 2*n1r_x + n2r_x;
    totalm_y = 2*n1m_y + n2m_y;
    totalr_y = 2*n1r_y + n2r_y;
    totalm_z = 2*n1m_z + n2m_z;
    totalr_z = 2*n1r_z + n2r_z;

    if (garrayz == NULL)
    {
      if (totalm_x == totalm_y)
      {
        *spgrad_nc = spgrad_nb + totalm_x;
        if (totalr_x >= totalr_y)
        {
          *spgrad_nd = *spgrad_nc + totalr_x;
        }
        else
        {
          *spgrad_nd = *spgrad_nc + totalr_y;
        }
      }
      else
      {
        if ((totalm_x + totalr_x) >= (totalm_y + totalr_y))
        {
          *spgrad_nd = *spgrad_nc = spgrad_nb + totalm_x + totalr_x;
        }
        else
        {
          *spgrad_nd = *spgrad_nc = spgrad_nb + totalm_y + totalr_y;
        }
      }
    }
    else /* 3D case */
    {
      if (totalm_x == totalm_y && totalm_x == totalm_z)
      {
        *spgrad_nc = spgrad_nb + totalm_x;

        if (totalr_x >= totalr_y)
        {
          *spgrad_nd = *spgrad_nc + totalr_x;
        }
        else if (totalr_y >= totalr_z)
        {
          *spgrad_nd = *spgrad_nc + totalr_y;
        }
        else
        {
          *spgrad_nd = *spgrad_nd + totalr_z;
        }
      }
      else
      {
        if ((totalm_x + totalr_x) >= (totalm_y + totalr_y))
        {
          *spgrad_nd = *spgrad_nc = spgrad_nb + totalm_x + totalr_x;
        }
        else if ((totalm_y + totalr_y) >= (totalm_z + totalr_z))
        {
          *spgrad_nd = *spgrad_nc = spgrad_nb + totalm_y + totalr_y;
        }
        else
        {
          *spgrad_nd = *spgrad_nc = spgrad_nb + totalm_z + totalr_z;
        }
      }
    }

    if (*spgrad_nd > maxlen)
    {
        *spgrad_nd = *spgrad_nc = spgrad_nb;
        return 0;
    }

    /* set garray */
    if (garrayz == NULL)
    {
      Naxis = 2;
    }
    else
    {
      Naxis = 3;
    }
    for (axis = 0; axis < Naxis; axis++)
    {
        float *garray = NULL;
        if (axis == 0)
        {
          n1m = n1m_x;
          n2m = n2m_x;
          n1r = n1r_x;
          n2r = n2r_x;
          am  = am_x;
          ar  = ar_x;
          garray = garrayx;
        }
        else if (axis == 1)
        {
          n1m = n1m_y;
          n2m = n2m_y;
          n1r = n1r_y;
          n2r = n2r_y;
          am  = am_y;
          ar  = ar_y;
          garray = garrayy;
        }
        else
        {
          n1m = n1m_z;
          n2m = n2m_z;
          n1r = n1r_z;
          n2r = n2r_z;
          am  = am_z;
          ar  = ar_z;
          garray = garrayz;
        }

        idx = spgrad_nb;
        /* middle gradient */
        /* ramp up */
        for (i = 0; i < n1m; i++)
        {
            garray[idx] = (double)i/(double)n1m*am;
            idx++;
        }
        /* flat top */
        for (i = 0; i < n2m; i++)
        {
            garray[idx] = am;
            idx++;
        }
        /* ramp down */
        for (i = 0; i < n1m; i++)
        {
            garray[idx] = (double)(n1m-1-i)/(double)n1m*am;
            idx++;
        }

        /* right gradient */
        /* ramp up */
        for (i = 0; i < n1r; i++)
        {
            garray[idx] = (double)i/(double)n1r*ar;
            idx++;
        }
        /* flat top */
        for (i = 0; i < n2r; i++)
        {
            garray[idx] = ar;
            idx++;
        }
        /* ramp down */
        for (i = 0; i < n1r; i++)
        {
            garray[idx] = (double)(n1r-1-i)/(double)n1r*ar;
            idx++;
        }
        /* fill 0's at the end */
        while (idx < (*spgrad_nd))
        {
            garray[idx] = 0.0;
            idx++;
        }
        garray = NULL;
    }

    return 1;
}
/**********************************************************************
 * Funtion:     gradmomentcomp_oneaxis
 * Description: 0th and 1st order gradient moment compensation. The
 *              waveform for compensation will be added to existing
 *              waveform.
 * Parameters:
 *              (I) As: 0th order moment to be compensated at t=0
 *              (I) m1s: 1st order moment to be compensated at t= 0
 *              (I) spgrad_nb: length of original garray
 *              (I) maxlen: max available length of garray
 *              (I) gdwell: gradient dwelling time
 *              (I) maxgrad: max gradient strength
 *              (I) maxslew: max gradient slew rate
 *              (I) postscaling: flag for scaling gradient
 *              (O) *spgrad_nc: length of array till end of middle gradient
 *              (O) *spgrad_nd: length of array till end of right gradient
 * Return:      0 (Failure) or 1 (Success)
 *********************************************************************/
int gradmomentcomp_oneaxis(double As, double m1s, int spgrad_nb, int maxlen, double gdwell,
    double maxgrad, double maxslew, int postscaling, int *n1m, int *n2m, double *am,
    int *n1r, int *n2r, double *ar)
{
    int sign_As = 0;
    int sign_Am = 0;
    int N1c     = 0;
    int init_Nr_bot = 0;
    int init_Nr_up  = 0;

    double Am  = 0.0;
    double m1m = 0.0;
    double Ar  = 0.0;
    double m1r = 0.0;
    double Ac  = 0.0;
    double sm  = 0.0;
    double sr  = 0.0;
    double m1_total    = 0.0;
    double init_m1_bot = 0.0;
    double init_m1_up  = 0.0;

    if (As >= 0)
    {
      sign_As = 1;
    }
    else
    {
      sign_As = -1;
      As = -As;
      m1s = -m1s;
    }
    sign_Am = -sign_As;

    if (As == 0 && m1s == 0) /* This may not happen at all */
    {
       /* no need to change garray */
       *n1m = 0;
       *n2m = 0;
       *n1r = 0;
       *n2r = 0;
       *am  = 0.0;
       *ar  = 0.0;
       return 1;
    }

    N1c = ceil(maxgrad/maxslew/gdwell); /* duration of max tramp */
    Ac = maxgrad*(double)N1c*gdwell;

    /* Start with area at (-)(As+Ac) & Ac for middle and right
     * gradients, respectively, such that starting search point
     * will be trap/triangle.
     */
    Am = As + Ac;
    Ar = Ac;
    gradtrap(gdwell, maxgrad, Am, Ac, N1c, am, n1m, n2m);
    gradtrap(gdwell, maxgrad, Ar, Ac, N1c, ar, n1r, n2r);

    /* determine 1st order moment */
    gradmoment_trap(*n1m, *n2m,               0, *am, gdwell, NULL, &m1m);
    gradmoment_trap(*n1r, *n2r, (*n1m)*2+(*n2m), *ar, gdwell, NULL, &m1r);

    m1_total = m1s - m1m + m1r;

    if (m1_total == 0)
    {
      /* Nothing to do */
    }
    else if (m1_total < 0)
    {
      /* Need to increase gradient area/duration.
       * The solution will be trap/trap combination.
       */
      if (0 == solution_analytical(TRAP_TRAP, As, m1s, maxgrad, gdwell, N1c, Ac, n1m, n2m, n1r, n2r, am, ar))
      {
          printf("LINE#%d: Trap/Trap analytical solution failed\n", __LINE__);
          return 0;
      }
    }
    else /* m1_total > 0. Need to decrease gradient */
    {
      if (Ac >= As)
      {
          /* Check if reducing to ciritical triangle/triangle works */
          int Nr_prev = (*n1r)*2 + (*n2r);
          double m1_prev = m1_total;

          Am = Ac;       /* (Ac + As) - As */
          Ar = Ac - As;  /* (Ac     ) - As */
          gradtrap(gdwell, maxgrad, Am, Ac, N1c, am, n1m, n2m);
          gradtrap(gdwell, maxgrad, Ar, Ac, N1c, ar, n1r, n2r);
          gradmoment_trap(*n1m, *n2m,               0, *am, gdwell, NULL, &m1m);
          gradmoment_trap(*n1r, *n2r, (*n1m)*2+(*n2m), *ar, gdwell, NULL, &m1r);
          m1_total = m1s - m1m + m1r;

          if (m1_total == 0)
          {
            /* Nothing to do */
          }
          else if (m1_total < 0)
          {
              /* Solution exists between critical triangle/triangle
               * & trap/critical triangle. It should be a trap/triangle
               * combination.
               */
              if (0 == solution_analytical(TRAP_TRIANGLE, As, m1s, maxgrad, gdwell,
                    N1c, Ac, n1m, n2m, n1r, n2r, am, ar))
              {
                  printf("LINE #%d: Solution_analytical failed\n", __LINE__);
                  return 0;
              }
          }
          else if (m1_total > 0)
          {
            /* need reduce more from Triangle/Triangle(0) */
            /* First check m1_total at As/0 combination.
             */
            Nr_prev = (*n1r)*2 + (*n2r);
            m1_prev = m1_total;

            Am = As;
            Ar = 0;
            gradtrap(gdwell, maxgrad, Am, Ac, N1c, am, n1m, n2m);
            gradtrap(gdwell, maxgrad,  0, Ac, N1c, ar, n1r, n2r);
            gradmoment_trap(*n1m, *n2m, 0, *am, gdwell, NULL, &m1m);
            m1_total = m1s - m1m;

            if (m1_total == 0)
            {
                /* Nothing to do */
            }
            else if (m1_total < 0)
            {
              /* Search between As/0 & Ac/(Ac-As) by right gradient */
              init_Nr_bot = 0;
              init_m1_bot = m1_total;
              init_Nr_up = Nr_prev;
              init_m1_up = m1_prev;

              if (0 == solution_search(GRAD_RIGHT, init_Nr_bot, init_Nr_up, init_m1_bot, init_m1_up,
                  As, m1s, maxgrad, gdwell, N1c, Ac, n1m, n2m, n1r, n2r, am, ar))
              {
                  printf("LINE #%d: Failed to search solution between As/0 & Ac/(Ac-As)\n", __LINE__);
                  return 0;
              }
            }
            else /* m1_total > 0 */
            {
              /* Need to reduce more from As/0.
               * but don't have margin to reduce.
               * Two options:
               * Option A: insert delay before middle gradient.
               * Option B: use pos/neg gradient combination.
               */
              if (0 == solution_pos_neg(As, m1s, maxgrad, gdwell, N1c, Ac,
                  n1m, n2m, n1r, n2r, am, ar))
              {
                  printf("LINE #%d: solution_pos_neg failed\n", __LINE__);
                  return 0;
              }
              sign_Am *= -1.0; /* Since polarity changed */
            }
          }
      }
      else
      {
          /* As > Ac.
           * Check if reducing from (Ac+As)/Ac to trap (As) / 0 works.
          */
          Am = As;
          Ar = 0;

          gradtrap(gdwell, maxgrad, Am, Ac, N1c, am, n1m, n2m);
          gradtrap(gdwell, maxgrad,  0, Ac, N1c, ar, n1r, n2r);
          gradmoment_trap(*n1m, *n2m, 0, *am, gdwell, NULL, &m1m);

          m1_total = m1s - m1m;

          if (m1_total == 0)
          {
            /* Do nothing */
          }
          else if (m1_total < 0)
          {
              /* Solution exists between As/0 & Ac+As/Ac.
               * It is Trap/Triangle combination.
               */
              if (0 == solution_analytical(TRAP_TRIANGLE, As, m1s, maxgrad, gdwell,
                   N1c, Ac, n1m, n2m, n1r, n2r, am, ar))
              {
                  printf("LINE #%d: solution_analytical failed\n", __LINE__);
                  return 0;
              }
          }
          else /* m1_total > 0 */
          {
            /* Need to reduce more, but can't. Two solutions. See comment above. */
            solution_pos_neg(As, m1s, maxgrad, gdwell, N1c, Ac,
                n1m, n2m, n1r, n2r, am, ar);
            sign_Am *= -1.0; /* Since polarity changed */
          }
      }
    }

    /* Now set gradient array */

    /* set actual polarities of middle and right gradient */
    (*am) =  (*am)*(double)sign_Am;
    (*ar) = -(*ar)*(double)sign_Am;

    /* restore sign of As and m1s */
    As *= (double)sign_As;
    m1s *= (double)sign_As;
    if (postscaling == 1)
    {
        /* scale gradient to count for rounding error*/

        gradmoment_trap(*n1m, *n2m,               0, *am, gdwell, &Am, &m1m);
        gradmoment_trap(*n1r, *n2r, (*n1m)*2+(*n2m), *ar, gdwell, &Ar, &m1r);

        /* Solve:
         *       As  + sm*Am  + sr*Ar  = 0
         *       m1s + sm*m1m + sr*m1r = 0
         */
        if (fabs(*am) != 0)
        {
            sr = (m1m*As - m1s*Am)/(m1r*Am - m1m*Ar);
            sm = -(As + sr*Ar)/Am;
        }
        else
        {
            sm = (m1r*As - m1s*Ar)/(m1m*Ar - m1r*Am);
            sr = -(As + sm*Am)/Ar;
        }

        if (sm >= 0 && sr >= 0
            && fabs(sm*(*am)) <= maxgrad
            && fabs(sr*(*ar)) <= maxgrad
            && fabs(sm*(*am)/((double)(*n1m)*gdwell)) <= maxslew
            && fabs(sr*(*ar)/((double)(*n1r)*gdwell)) <= maxslew)
        {
            (*am) = (*am)*sm;
            (*ar) = (*ar)*sr;
        }
        else
        {
            if ((As + Am + Ar) > 0)
            {
                /* reduce gradient with positive amp */
                if (Am > 0)
                {
                   (*am) *= (-As - Ar)/Am;
                }
                else if (Ar > 0)
                {
                    (*ar) *= (-As - Am)/Ar;
                }
            }
            else if ((As + Am + Ar) < 0)
            {
                if (Am < 0)
                {
                    (*am) *= (-As - Ar)/Am;
                }
                else if (Ar < 0)
                {
                    (*ar) *= (-As - Am)/Ar;
                }
            }
        }
        gradmoment_trap(*n1m, *n2m,               0, *am, gdwell, &Am, &m1m);
        gradmoment_trap(*n1r, *n2r, (*n1m)*2+(*n2m), *ar, gdwell, &Ar, &m1r);

    }

    return 1;
}

/**********************************************************************
 * Funtion:     solution_analytical
 * Description: analytically find the waveform information (only for
 *              trap/triangle or trap/trap combination)
 * Parameters:  (I) G_type: desired combination (either trap/trap
*               (I) As: gradient area to be compensated
 *              (I) m1s: 1st order moment to be compensated.
 *              (I) maxgrad: max gradient strength
 *              (I) gdwell: gradient dwelling time
 *              (I) N1c: duration of slope of a critical triangle (in
 *                  number of point).
 *              (I) Ac: area of a critical triangle
 *              (O) n1m: duration of slope of the middle gradient
 *              (O) n2m: duration of the flat top of the middle gradient
 *              (O) n1r: duration of slope of the right gradient
 *              (O) n2r: duration of the flat top of the right gradient
 *              (O) am: amplitude of the middle gradient
 *              (O) ar: amplitude of the right gradient
 * Return:      0 (Failure) or 1 (Success)
 *********************************************************************/

int solution_analytical(int G_type, double As, double m1s, double maxgrad,
    double gdwell, int N1c, double Ac, int *n1m, int *n2m,
    int *n1r, int *n2r, double *am, double *ar)
{
    double Ar = 0.0;
    double Am = 0.0;
    double r = 0.0;
    double h = 0.0;

    m1s *= -1; /* due to different definition used in the handbook */
    r = (double)N1c*gdwell;
    h = maxgrad; /* to follow handbook variable */

    if (G_type == TRAP_TRIANGLE)
    {
        /* use solution from handbook p344 */
        Ar = 0.5*(h*r
             +2.0*sqrt(h*r*As + As*As + 2.0*h*m1s)
             -    sqrt(h*h*r*r + 4.0*h*r*sqrt(h*r*As + As*As + 2.0*h*m1s))
             );
    }
    else /*(G_type == TRAP_TRAP)*/
    {
        Ar = 0.5*(-h*r + sqrt(h*h*r*r + 2.0*(h*r*As + As*As + 2.0*h*m1s)));
    }

    Am = As + Ar;
    gradtrap(gdwell, maxgrad, Am, Ac, N1c, am, n1m, n2m);
    gradtrap(gdwell, maxgrad, Ar, Ac, N1c, ar, n1r, n2r);

    if (*am < 0 || *ar < 0 || *n1m < 0 || *n2m < 0 || *n1r < 0 || *n2r < 0)
    {
      printf("LINE #%d: Function solution_analytical failed\n", __LINE__);
      return 0;
    }

    return 1;
}

/**********************************************************************
 * Funtion:     solution_search
 * Description: search for gradient waveform that can compensate the
 *              0th/1st order gradient moments. This is used for
 *              triangle/triangle combination
 * Parameters:  (I) G_flag: flag for which gradient (middle or right)
 *                  to be searched
 *              (I) init_N_bot: min duration of the gradient to be
 *                  searched (in number of points)
 *              (I) init_N_up: max duration of the gradient to be searched
 *              (I) init_m1_bot: min 1st order moment of the gradient
 *                  to be searched
 *              (I) init_m1_up: max 1st order moment of the gradient
 *                  to be searched
 *              (I) As: gradient area to be compensated
 *              (I) m1s: 1st order moment to be compensated.
 *              (I) maxgrad: max gradient strength
 *              (I) gdwell: gradient dwelling time
 *              (I) N1c: duration of slope of a critical triangle (in
 *                  number of point).
 *              (I) Ac: area of a critical triangle
 *              (O) n1m: duration of slope of the middle gradient
 *              (O) n2m: duration of the flat top of the middle gradient
 *              (O) n1r: duration of slope of the right gradient
 *              (O) n2r: duration of the flat top of the right gradient
 *              (O) am: amplitude of the middle gradient
 *              (O) ar: amplitude of the right gradient
 * Return:      0 (Failure) or 1 (SUCCESS)
 *********************************************************************/

int solution_search(int G_flag, int init_N_bot, int init_N_up, double init_m1_bot,
    double init_m1_up, double As, double m1s, double maxgrad, double gdwell,
    int N1c, double Ac, int *n1m, int *n2m, int *n1r, int *n2r, double *am, double *ar)
{
    int N     = 0;
    int N_bot = 0;
    int N_up  = 0;
    int iter  = 0;
    int MAXITER = 200;
    int waveform_found = 0;

    double m1_bot = 0.0;
    double m1_up  = 0.0;
    double Ar  = 0.0;
    double Am  = 0.0;
    double m1  = 0.0;
    double m1m = 0.0;
    double m1r = 0.0;

    N_bot = init_N_bot;
    N_up = init_N_up;
    m1_bot = init_m1_bot;
    m1_up = init_m1_up;

    N = N_bot;
    waveform_found = 0;
    iter = 0;
    while (waveform_found != 1 && iter < MAXITER)
    {
      if (m1_bot * m1_up <= 0 && (N_up - N_bot) <= 2)
      {
        /* Solution found */
        waveform_found = 1; /* set flag to exit */
      }
      else
      {
        N = (N_bot + N_up)/2; /* set new gradient duration */
        if ((N%2) == 0 && (N < (N1c*2+1)))
        {
          N += 1; /* For triangle, want N to be odd */
        }
        if (G_flag == GRAD_MIDDLE)
        {
          /* Searching by middle gradient */
          /* Determine 0th/1st order moment from duration */
          if (N > (N1c*2+1)) /* Trap */
          {
            *n1m = N1c;
            *n2m = N - N1c*2;
            *am = maxgrad;
          }
          else /* Triangle */
          {
            *n1m = (N-1)/2;
            *n2m = 1;
            *am = (double)(*n1m)/(double)N1c*maxgrad;
          }
          gradmoment_trap(*n1m, *n2m, 0, *am, gdwell, &Am, &m1m);

          /* Determine 0th/1st order moment of right gradient */
          Ar = Am + As;
          gradtrap(gdwell, maxgrad, Ar, Ac, N1c, ar, n1r, n2r);
          gradmoment_trap(*n1r, *n2r, N, *ar, gdwell, NULL, &m1r);

          /* total 1st order moment */
          m1 = m1s + m1m - m1r;
          /* update upper/lower boundary */
          if (m1 <= 0)
          {
            N_up = N;
            m1_up = m1;
          }
          else
          {
            N_bot = N;
            m1_bot = m1;
          }
        }
        else
        {
          /* Search by right gradient */
          /* Determine area from duration */
          if (N > (N1c*2+1))
          {
            *ar = maxgrad;
            *n1r = N1c;
            *n2r = N - N1c*2;
          }
          else
          {
            *n1r = (N-1)/2;
            *n2r = 1;
            *ar = (double)(*n1r)/(double)N1c*maxgrad;
          }
          gradmoment_trap(*n1r, *n2r, 0, *ar, gdwell, &Ar, NULL);

          /* Determine area and duration of middle gradient */
          Am = As + Ar;
          gradtrap(gdwell, maxgrad, Am, Ac, N1c, am, n1m, n2m);

          /* Determine 1st order moment of middle/right gradients */
          gradmoment_trap(*n1m, *n2m,             0, *am, gdwell, NULL, &m1m);
          gradmoment_trap(*n1r, *n2r, *n1m*2 + *n2m, *ar, gdwell, NULL, &m1r);

          /* calculate total m1 and update lower/upper boundary */
          m1 = m1s - m1m + m1r;
          if (m1 <= 0)
          {
            m1_bot = m1;
            N_bot = N;
          }
          else
          {
            m1_up = m1;
            N_up = N;
          }
        }

        iter++;
      }
    }
    if (iter >= MAXITER)
    {
        printf("LINE #%d: Max Iteration reached. Solution not found\n", __LINE__);
        return 0;
    }

    return 1;
}

/**********************************************************************
 * Funtion:     solution_pos_neg
 * Description:
 *              Determine a solution with a postive middle gradient
 *              and a negative right gradient.
 * Parameters:
 *              (I) As: gradient area to be compensated
 *              (I) m1s: 1st order moment to be compensated.
 *              (I) maxgrad: max gradient strength
 *              (I) gdwell: gradient dwelling time
 *              (I) N1c: duration of slope of a critical triangle (in
 *                  number of point).
 *              (I) Ac: area of a critical triangle
 *              (O) n1m: duration of slope of the middle gradient
 *              (O) n2m: duration of the flat top of the middle gradient
 *              (O) n1r: duration of slope of the right gradient
 *              (O) n2r: duration of the flat top of the right gradient
 *              (O) am: amplitude of the middle gradient
 *              (O) ar: amplitude of the right gradient
 * Return:      0 (Failure) or 1 (Success)
 *********************************************************************/

int solution_pos_neg(double As, double m1s, double maxgrad,
    double gdwell, int N1c, double Ac, int *n1m, int *n2m,
    int *n1r, int *n2r, double *am, double *ar)
{
  int N = 0;
  double Am  = 0.0;
  double Ar  = 0.0;
  double m1m = 0.0;
  double m1r = 0.0;
  double r   = 0.0;
  double m1_total = 0.0;

  /* start from max triangle (or min trap) for 1st gradient.  */
  /* the 2nd gradient must be a trapezoid.                    */
  r = (double)N1c*gdwell;
  Am = Ac;
  Ar = Ac + As;
  gradtrap(gdwell, maxgrad, Am, Ac, N1c, am, n1m, n2m);
  gradtrap(gdwell, maxgrad, Ar, Ac, N1c, ar, n1r, n2r);
  gradmoment_trap(*n1m, *n2m,               0, *am, gdwell, NULL, &m1m);
  gradmoment_trap(*n1r, *n2r, (*n1m)*2+(*n2m), *ar, gdwell, NULL, &m1r);

  m1_total = m1s + m1m - m1r;

  if (m1_total >= 0) /* need to iN1crease gradient area, i.e., need two trapezoid */
  {
    /* analytical solution */
    /* this is different from the handbook due to the polarities. */
    double a = 0.0;
    double b = 0.0;
    double c = 0.0;
    a = 2.0;
    b = 4.0*As + 2.0*maxgrad*r;
    c = As*As + 3*maxgrad*r*As - 2.0*maxgrad*m1s;
    Am = (-b + sqrt(b*b - 4.0*a*c))/(2.0*a);
    if (Am <= 0)
    {
      printf("LINE #%d: bipoloar solution 2 failed\n", __LINE__);
      return 0;
    }
    N = ceil((Am/maxgrad + r)/gdwell);
    if (N < (2*N1c+1))
    {
      printf("LINE #%d: bipoloar solution 2 failed\n", __LINE__);
      return 0;
    }
    *n1m = N1c;
    *n2m = N - 2*N1c;
    *am = maxgrad;

    Ar = Am + As;
    N = ceil((Ar/maxgrad + r)/gdwell);
    if (N < (2*N1c+1))
    {
      printf("LINE #%d: bipoloar solution 2 failed\n", __LINE__);
      return 0;
    }
    *n1r = N1c;
    *n2r = N - 2*N1c;
    *ar = maxgrad;
  }
  else /* m1_total < 0, need to decrease gradient area */
  {
    int init_Nm_bot = 0;
    int init_Nm_up  = 0;
    double Nm_prev  = 0.0;
    double m1_prev  = 0.0;
    double init_m1_bot = 0.0;
    double init_m1_up  = 0.0;

    Nm_prev = (*n1m)*2 + (*n2m);
    m1_prev = m1_total;

    /* divide into two situation to reduce possible search time */
    /* We search t of first gradient, instead of the 2nd.       */
    if (Ac >= As)
    {
      /* In this case, check if a triangle + max triangle works */
      /* i.e., (Ac-As)/Ac combination */
      Am = Ac - As;
      Ar = Ac;
      gradtrap(gdwell, maxgrad, Am, Ac, N1c, am, n1m, n2m);
      gradtrap(gdwell, maxgrad, Ar, Ac, N1c, ar, n1r, n2r);
      gradmoment_trap(*n1m, *n2m,               0, *am, gdwell, NULL, &m1m);
      gradmoment_trap(*n1r, *n2r, (*n1m)*2+(*n2m), *ar, gdwell, NULL, &m1r);
      m1_total = m1s + m1m - m1r;

      if (m1_total >= 0)/* need triangle/trapezoid, search it */
      {
        /* need triangle/trapezoid, i.e., the soluiton exists
         * between (Ac-As)/Ac & Ac/(Ac+As), i.e., it is
         * a triangle/trapezoid combination.
         * search the solution instead of using analytical method.
         */
        init_Nm_bot = (*n1m)*2 + (*n2m);
        init_Nm_up = Nm_prev;
        init_m1_bot = m1_total;
        init_m1_up = m1_prev;
      }
      else
      {
        /* need to further reduce area, i.e., solution exists
         * between 0/As & (Ac-As)/Ac. Search it */
        init_Nm_bot = 0;
        init_Nm_up = (*n1m)*2 + (*n2m);
        gradtrap(gdwell, maxgrad, As, Ac, N1c, ar, n1r, n2r);
        gradmoment_trap(*n1r, *n2r, 0, *ar, gdwell, NULL, &m1r);
        init_m1_bot = m1s - m1r;
        init_m1_up = m1_total;
      }
    }
    else /* As > Ac */
    {
      /* search between 0/-As & Ac/-(Ac+As) */
      init_Nm_bot = 0;
      init_Nm_up = Nm_prev;
      gradtrap(gdwell, maxgrad, As, Ac, N1c, ar, n1r, n2r);
      gradmoment_trap(*n1r, *n2r, 0, *ar, gdwell, NULL, &m1r);
      init_m1_bot = m1s - m1r;
      init_m1_up = m1_prev;
    }
    if (0 == solution_search(GRAD_MIDDLE, init_Nm_bot, init_Nm_up,
          init_m1_bot, init_m1_up, As, m1s, maxgrad, gdwell, N1c, Ac,
          n1m, n2m, n1r, n2r, am, ar))
    {
        printf("LINE #%d: Failed to search solution between 0/-As & Ac/-(Ac+As)\n",
            __LINE__);
        return 0;
    }
  }

  return 1;
}

/**********************************************************************
 * Funtion:     gradtrap
 * Description: determine amplitue/duration of a trapezoid/triangle,
 *              given the desired area.
 * Parameters:
 *              (I) gdwell: gradient dwelling time
 *              (I) maxgrad: max gradient strength
 *              (I) area: desired gradient area
 *              (I) Ac: area of a critical triangle (max triangle or min
 *                  trapezoid)
 *              (I) N1c: duration of the slope of a critical triangle (in
 *                  number of points)
 *              (O) *amp: amplitude of the graident
 *              (O) *nslope: number of point in the slope
 *              (O) *nflattop: number of point in the flat top
 * Return:      None
 *********************************************************************/

void gradtrap(double gdwell, double maxgrad, double area, double Ac,
    int N1c, double *amp, int *nslope, int *nflattop)
{
  /* In this code, the assumption is:
   * the leading ramp is: 0, 1, 2, ..., (nslope-1).
   * the ending ramp is : (nslope-1), ..., 2, 1, 0.
   * For trapezoid, the amplitude of the flat top
   * is maxgrad.
   * For triangle, the duration of the flat top is
   * set to 1, with amplitude = maxgrad for critical
   * triangle, or scaled for non-critical triangle.
   */

  double sign_trap = 1.0;

  if (area >= 0)
  {
    sign_trap = 1.0;
  }
  else
  {
    sign_trap = -1.0;
  }

  area *= sign_trap;

  if (area <= Ac) /* Triangle */
  {
    *nflattop = 1;
    *nslope = ceil(sqrt(area*(double)N1c*gdwell/maxgrad)/gdwell);
    if (*nslope > 0)
    {
        *amp = area/(gdwell*(double)(*nslope));
    }
    else
    {
        *amp = 0.0;
    }
  }
  else /* Trapezoid */
  {
    *amp = maxgrad;
    *nslope = N1c;
    *nflattop = ceil(area/(*amp)/gdwell) - (*nslope) + 1;
    /* Note the substraction of 1 */
    *amp = area/(gdwell*(double)((*nslope) + (*nflattop) - 1));
  }

  *amp *= sign_trap;
}

/**********************************************************************
 * Funtion:     gradmoment_array
 * Description: Calculate the 0th/1st order moment arbitrary gradient
 *              waveform stored in an array.
 * Parameters:
 *              (I) arraysize: number of point in the array
 *              (I) gdwell: gradient dwelling time
 *              (I) nstart: start time of the first point (in number of
 *                  point)
 *              (I) *garray: array of the gradient waveform
 *              (O) *m0array: array of the 0th order moment. If NULL,
 *                  this array will not be set
 *              (O) *m1array: array of the 1st order moment. If NULL,
 *                  this array will not be set
 *              (O) *m0_end: 0th order moment at end of the waveform,
 *                  If NULL, this will not be returned
 *              (O) *m1_end: 1st order moment at end of the waveform,
 *                  If NULL, this will not be returned
 * Return:      None
 *********************************************************************/

void gradmoment_array(int arraysize, double gdwell, int nstart, float *garray,
    double *m0array, double *m1array, double *m0_end, double *m1_end)
{
  int i = 0;
  double gdwell2 = gdwell*gdwell;
  double m0 = 0.0;
  double m1 = 0.0;
  double m0_prev = 0.0;
  double m1_prev = 0.0;

  m0 = 0;
  m1 = 0;

  if (arraysize > 0)
  {
      m0 = garray[0]*gdwell;
      m1 = garray[0]*gdwell2*nstart;
      if (m0array != NULL && m1array != NULL)
      {
          m0array[0] = m0;
          m1array[0] = m1;
      }
      for (i = 1; i < arraysize; i++)
      {
          m0_prev = m0;
          m1_prev = m1;
          m0 = m0_prev + garray[i]*gdwell;
          m1 = m1_prev + garray[i]*gdwell2*(i+nstart);

          if (m0array != NULL && m1array != NULL)
          {
              m0array[i] = m0;
              m1array[i] = m1;
          }
      }
  }
  if (m0_end != NULL)
  {
      *m0_end = m0;
  }
  if (m1_end != NULL)
  {
      *m1_end = m1;
  }
}

/**********************************************************************
 * Funtion:     gradmoment_trap
 * Description: Calculate 0th/1st order gradient moment of a trapezoid
 *              (or triangle, which has nflattop = 1)
 * Parameters:
 *              (I) nslope: number of point of the slope
 *              (I) nflattop: number of point of the flattop
 *              (I) nstart: start time of the slope (in number of point)
 *              (I) amp: amplitude of the trapezoid
 *              (I) gdwell: gradient dwelling time
 *              (O) *m0_end: 0th order moment at end of the waveform
 *                  If NULL, the 0th order moment will not be returned
 *              (O) *m1_end: 1st order moment at end of the waveform
 *                  If NULL, the 1st order moment will not be returned
 * Return:      None
 *********************************************************************/

void gradmoment_trap(int nslope, int nflattop, int nstart,
    double amp, double gdwell, double *m0_end, double *m1_end)
{
  /* See comment in gradtrap about the assumption of
   * gradient shape. nstart is the starting point of
   * the ramp.
   */
  double m0 = 0.0;
  double m1 = 0.0;

  m0 = amp*gdwell*(double)(nslope + nflattop - 1);
  m1 = m0*((double)nstart + (double)nslope + (double)(nflattop-1)/2.0)*gdwell;
  if (m0_end != NULL)
  {
    *m0_end = m0;
  }
  if (m1_end != NULL)
  {
    *m1_end = m1;
  }
}
