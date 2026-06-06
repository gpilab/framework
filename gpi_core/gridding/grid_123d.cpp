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


/*   Standard Gridding Module */
#define KERNSIZE 250

//========================================================================
// GRIDDAT
//========================================================================

int griddat(Array<float> &crds, Array<complex<float> > &data, Array<float> &wates, Array<complex<float> > &outdata,
            double dx, double dy, double dz)
{
  int i,j,k,d;
  int mtx0, mtx1, mtx2;
  float fmtx0, fmtx1, fmtx2, fi,fj,fk;
  int di,dj,dk;
  int mini,maxi,minj,maxj,mink,maxk;
  int dj0, dk0;
  float x;
  complex<float> theta;
  complex<float> val0,val1,val2;
  complex<float> eye = sqrt( complex<float>(-1) ) ; // there must be a better way?

  Array<float> kernel(KERNSIZE+1);

////////////
// KERNEL //
////////////
// Create separable kernel, which has a radius-FOV product of 3.33
// With an oversampling factor of 1.5, want the FOV to be 1.33, thus a radius of 2.5
// We will make the kernel 250 points to make this easy calculatin'
// The kernel is a full Hanning window times exp(-6 x^2)
//   which is almost certainly not optimal but a lot easier to generate than a kaiser-bessel function
  for (i=0;i<KERNSIZE;i++) {
    x = (float)(i)/(float)(KERNSIZE); // goes from 0 to 1
    kernel(i) = 0.5*(1.+cos(M_PI*x))*exp(-6.*x*x);
    }

//////////////////
// FLATTEN DATA //
//////////////////
// Convert the incoming data to a 1D series of data, with crds having an extra dimension for kx/ky/(and optionally)kz
  
  //crds.reshape( ArrayBounds( crds.bounds(0) , B(0,data.size()-1) ) );
  //data.reshape(ArrayBounds(B(0,data.size()-1)));
  //wates.reshape(ArrayBounds( B(0,wates.size()-1)));

/////////////
// 1D DATA //
/////////////

  if (crds.size(0) == 1) {
    outdata = complex<float> (0.);

    mtx0 = outdata.size(0);
    fmtx0 = outdata.size(0) & ~1; // round down to nearest even integer
    for (d=0;d<data.size();d++) {
      if ((crds(0,d) >= -0.5) && (crds(0,d) <= 0.5)) { // only grid if crds inbounds
        theta = -2.*M_PI*crds(0,d)*dx;
        if (abs(theta) == 0)
          val0 = data(d)*wates(d);
        else
          val0 = data(d)*wates(d)*exp(eye*theta);
        fi = (0.5+crds(0,d))*fmtx0;
        mini = max(0,int(fi-2.5)+1);
        maxi = min(mtx0-1,int(fi+2.5));
        di = (floor)((100.*((float)(mini) - fi)) + 0.5);
        for (i=mini;i<=maxi;i++) {
          outdata(i) += kernel(abs(di))*val0;
          di += 100;
          } // i
        } // if crds
      } // d
    } // crds.size == 1

/////////////
// 2D DATA //
/////////////

  if (crds.size(0) == 2) {
    outdata = complex<float> (0.);

    mtx0 = outdata.size(0);
    mtx1 = outdata.size(1);
    fmtx0 = outdata.size(0) & ~1; // round down to nearest even integer
    fmtx1 = outdata.size(1) & ~1;
    for (d=0;d<data.size();d++) {
      if ((crds(0,d) >= -0.5) && (crds(0,d) <= 0.5) &&
          (crds(1,d) >= -0.5) && (crds(1,d) <= 0.5)) { // only grid if crds inbounds
        theta = -2.*M_PI*(crds(0,d)*dx + crds(1,d)*dy);
        if (abs(theta) == 0)
          val0 = data(d)*wates(d);
        else
          val0 = data(d)*wates(d)*exp(eye*theta);
        fi = (0.5+crds(0,d))*fmtx0;
        fj = (0.5+crds(1,d))*fmtx1;
        mini = max(0,int(fi-2.5)+1);
        maxi = min(mtx0-1,int(fi+2.5));
        minj = max(0,int(fj-2.5)+1);
        maxj = min(mtx1-1,int(fj+2.5));
        di = (floor)((100.*((float)(mini) - fi)) + 0.5);
        // We are adding 100 to dj each step because the kernel size is 100 times the grid size
        dj0 = (floor)((100.*((float)(minj) - fj)) + 0.5);
        for (i=mini;i<=maxi;i++) {
          val1 = kernel(abs(di))*val0;
          dj = dj0;
          for (j=minj;j<=maxj;j++) {
            outdata(i,j) += kernel(abs(dj))*val1;
            dj += 100;
            } // j
          di += 100;
          } // i
        } // if crds
      } // d
    } // crds.size == 2

/////////////
// 3D DATA //
/////////////
  else if (crds.size(0) == 3) {
    outdata = complex<float> (0.);

    mtx0 = outdata.size(0);
    mtx1 = outdata.size(1);
    mtx2 = outdata.size(2);
    fmtx0 = outdata.size(0) & ~1; // round down to nearest even integer
    fmtx1 = outdata.size(1) & ~1;
    fmtx2 = outdata.size(2) & ~1;
    for (d=0;d<data.size();d++) {
      if ((crds(0,d) >= -0.5) && (crds(0,d) <= 0.5) &&
          (crds(1,d) >= -0.5) && (crds(1,d) <= 0.5) &&
          (crds(2,d) >= -0.5) && (crds(2,d) <= 0.5)) { // only grid if crds inbounds
        theta = -2.*M_PI*(crds(0,d)*dx + crds(1,d)*dy + crds(2,d)*dz);
        if (abs(theta) == 0)
          val0 = data(d)*wates(d);
        else
          val0 = data(d)*wates(d)*exp(eye*theta);
        fi = (0.5+crds(0,d))*fmtx0;
        fj = (0.5+crds(1,d))*fmtx1;
        fk = (0.5+crds(2,d))*fmtx2;
        mini = max(0,int(fi-2.5)+1);
        maxi = min(mtx0-1,int(fi+2.5));
        minj = max(0,int(fj-2.5)+1);
        maxj = min(mtx1-1,int(fj+2.5));
        mink = max(0,int(fk-2.5)+1);
        maxk = min(mtx2-1,int(fk+2.5));
        di = (floor)((100.*((float)(mini) - fi)) + 0.5);
        // We are adding 100 to dj, dk each step because the kernel size is 100 times the grid size
        dj0 = (floor)((100.*((float)(minj) - fj)) + 0.5);
        dk0 = (floor)((100.*((float)(mink) - fk)) + 0.5);
        for (i=mini;i<=maxi;i++) {
          val1 = kernel(abs(di))*val0;
          dj = dj0;
          for (j=minj;j<=maxj;j++) {
            val2 = kernel(abs(dj))*val1;
            dk = dk0;
            for (k=mink;k<=maxk;k++) {
              outdata(i,j,k) += kernel(abs(dk))*val2;
              dk += 100;
              } // k
            dj += 100;
            } // j
          di += 100;
          } // i j
        } // if crds
      } // d
    } // crds.size == 3

   return (0);
}

//========================================================================
// ROLLOFFDAT
//========================================================================

int rolloffdat(Array<complex<float> > &data, Array<complex<float> > &outdata, int64_t isofov)
{
  int i, i0, i1, i2;
  int dmtx0, dmtx1, dmtx2, omtx0, omtx1, omtx2;
  int di0, di1, di2;
  int kernwidth;
  float x;
  float rad0,rad1,rad2,sq1,sq2;
  float den0,den1,den2;
  complex<float> val;
  Array<float> kernel(KERNSIZE+1);

////////////
// KERNEL //
////////////
// Create separable kernel, which has a radius-FOV product of 3.33
// With an oversampling factor of 1.5, want the FOV to be 1.33, thus a radius of 2.5
// We will make the kernel 250 points to make this easy calculatin'
// The kernel is a full Hanning window times exp(-6 x^2)
//   which is almost certainly not optimal but a lot easier to generate than a kaiser-bessel function
  for (i=0;i<KERNSIZE;i++) {
    x = (float)(i)/(float)(KERNSIZE); // goes from 0 to 1
    kernel(i) = 0.5*(1.+cos(M_PI*x))*exp(-6.*x*x);
    }

  kernwidth = KERNSIZE/100;

/////////////
// 1D DATA //
/////////////

  if (data.ndim() == 1) {

/////////////////////////////////
// Calculate correction arrays //
/////////////////////////////////
    Array<complex<float> > ro0(data.size(0));
    Array<complex<float> > cor0(outdata.size(0));
    dmtx0 = data.size(0);
    omtx0 = outdata.size(0);
    den0 = 2./(float)(omtx0);
    di0 = (dmtx0 - omtx0 + 1)/2;

    for (i=0;i<dmtx0;i++)
      ro0(i) = 0.;
    for (i = -kernwidth; i <= kernwidth; i++) {
      i0 = (dmtx0/2) + i;
      if (i0 > 0 && i0 < dmtx0)
        ro0(i0) = kernel(abs(100*i));
      }

    //R2UTILS::Cfft1(ro0,ro0,FFTW_BACKWARD);
    //ro0 = Numpy::fft1(ro0, FFT_NUMPY_BACKWARD);
    FFTW::fft1(ro0, ro0, FFTW_BACKWARD);

    for (i=0;i<omtx0;i++) {
      if (ro0(i+di0).real() > 0)
        cor0(i) = ro0(dmtx0/2).real()/ro0(i+di0).real();
      else
        cor0(i) = 0.;
      }

//////////////////////
// Calculate output //
// Ignore isofov, means nothing here //
//////////////////////

    for (i0=0;i0<omtx0;i0++) {
      outdata(i0) = cor0(i0)*data(i0+di0);
      }

    } // 1D

/////////////
// 2D DATA //
/////////////

  if (data.ndim() == 2) {

/////////////////////////////////
// Calculate correction arrays //
/////////////////////////////////
    Array<complex<float> > ro0(data.size(0));
    Array<complex<float> > ro1(data.size(1));
    Array<complex<float> > cor0(outdata.size(0));
    Array<complex<float> > cor1(outdata.size(1));
    dmtx0 = data.size(0);
    dmtx1 = data.size(1);
    omtx0 = outdata.size(0);
    omtx1 = outdata.size(1);
    den0 = 2./(float)(omtx0);
    den1 = 2./(float)(omtx1);
    di0 = (dmtx0 - omtx0 + 1)/2;
    di1 = (dmtx1 - omtx1 + 1)/2;

    for (i=0;i<dmtx0;i++)
      ro0(i) = 0.;
    for (i=0;i<dmtx1;i++)
      ro1(i) = 0.;
    for (i = -kernwidth; i <= kernwidth; i++) {
      i0 = (dmtx0/2) + i;
      i1 = (dmtx1/2) + i;
      if (i0 > 0 && i0 < dmtx0)
        ro0(i0) = kernel(abs(100*i));
      if (i1 > 0 && i1 < dmtx1)
        ro1(i1) = kernel(abs(100*i));
      }

    //R2UTILS::Cfft1(ro0,ro0,FFTW_BACKWARD);
    //ro0 = Numpy::fft1(ro0, FFT_NUMPY_BACKWARD);
    FFTW::fft1(ro0, ro0, FFTW_BACKWARD);
    //R2UTILS::Cfft1(ro1,ro1,FFTW_BACKWARD);
    //ro1 = Numpy::fft1(ro1, FFT_NUMPY_BACKWARD);
    FFTW::fft1(ro1, ro1, FFTW_BACKWARD);

    for (i=0;i<omtx0;i++) {
      if (ro0(i+di0).real() > 0)
        cor0(i) = ro0(dmtx0/2).real()/ro0(i+di0).real();
      else
        cor0(i) = 0.;
      }
    for (i=0;i<omtx1;i++) {
      if (ro1(i+di1).real() > 0)
        cor1(i) = ro1(dmtx1/2).real()/ro1(i+di1).real();
      else
        cor1(i) = 0.;
      }

//////////////////////
// Calculate output //
//////////////////////

    if (isofov == 1) {
      for (i1=0;i1<omtx1;i1++) {
        rad1 = (float)(i1-omtx1/2)*den1;
        sq1 = rad1*rad1;
        for (i0=0;i0<omtx0;i0++) {
          rad0 = (float)(i0-omtx0/2)*den0;
          if (rad0*rad0 + sq1 <= 1)
            outdata(i0,i1) = cor0(i0)*cor1(i1)*data(i0+di0,i1+di1);
          else
            outdata(i0,i1) = 0;
        } } // i0 i1
      }
    else {
      for (i1=0;i1<omtx1;i1++) {
        for (i0=0;i0<omtx0;i0++) {
          outdata(i0,i1) = cor0(i0)*cor1(i1)*data(i0+di0,i1+di1);
        } }
      }

    } // 2D

/////////////
// 3D DATA //
/////////////

  else if (data.ndim() == 3) {

/////////////////////////////////
// Calculate correction arrays //
/////////////////////////////////
    Array<complex<float> > ro0(data.size(0));
    Array<complex<float> > ro1(data.size(1));
    Array<complex<float> > ro2(data.size(2));
    Array<complex<float> > cor0(outdata.size(0));
    Array<complex<float> > cor1(outdata.size(1));
    Array<complex<float> > cor2(outdata.size(2));
    dmtx0 = data.size(0);
    dmtx1 = data.size(1);
    dmtx2 = data.size(2);
    omtx0 = outdata.size(0);
    omtx1 = outdata.size(1);
    omtx2 = outdata.size(2);
    den0 = 2./(float)(omtx0);
    den1 = 2./(float)(omtx1);
    den2 = 2./(float)(omtx2);
    di0 = (dmtx0 - omtx0 + 1)/2;
    di1 = (dmtx1 - omtx1 + 1)/2;
    di2 = (dmtx2 - omtx2 + 1)/2;

    for (i=0;i<dmtx0;i++)
      ro0(i) = 0.;
    for (i=0;i<dmtx1;i++)
      ro1(i) = 0.;
    for (i=0;i<dmtx2;i++)
      ro2(i) = 0.;
    for (i = -kernwidth; i <= kernwidth; i++) {
      i0 = (dmtx0/2) + i;
      i1 = (dmtx1/2) + i;
      i2 = (dmtx2/2) + i;
      if (i0 > 0 && i0 < dmtx0)
        ro0(i0) = kernel(abs(100*i));
      if (i1 > 0 && i1 < dmtx1)
        ro1(i1) = kernel(abs(100*i));
      if (i2 > 0 && i2 < dmtx2)
        ro2(i2) = kernel(abs(100*i));
      }

    //R2UTILS::Cfft1(ro0,ro0,FFTW_BACKWARD);
    //ro0 = Numpy::fft1(ro0, FFT_NUMPY_BACKWARD);
    FFTW::fft1(ro0, ro0, FFTW_BACKWARD);
    //R2UTILS::Cfft1(ro1,ro1,FFTW_BACKWARD);
    //ro1 = Numpy::fft1(ro1, FFT_NUMPY_BACKWARD);
    FFTW::fft1(ro1, ro1, FFTW_BACKWARD);
    //R2UTILS::Cfft1(ro2,ro2,FFTW_BACKWARD);
    //ro2 = Numpy::fft1(ro2, FFT_NUMPY_BACKWARD);
    FFTW::fft1(ro2, ro2, FFTW_BACKWARD);

    for (i=0;i<omtx0;i++) {
      if (ro0(i+di0).real() > 0)
        cor0(i) = ro0(dmtx0/2).real()/ro0(i+di0).real();
      else
        cor0(i) = 0.;
      }
    for (i=0;i<omtx1;i++) {
      if (ro1(i+di1).real() > 0)
        cor1(i) = ro1(dmtx1/2).real()/ro1(i+di1).real();
      else
        cor1(i) = 0.;
      }
    for (i=0;i<omtx2;i++) {
      if (ro2(i+di2).real() > 0)
        cor2(i) = ro2(dmtx2/2).real()/ro2(i+di2).real();
      else
        cor2(i) = 0.;
      }

//////////////////////
// Calculate output //
//////////////////////

    if (isofov == 1) {
      for (i2=0;i2<omtx2;i2++) {
        rad2 = (float)(i2-omtx2/2)*den2;
        sq2 = rad2*rad2;
        for (i1=0;i1<omtx1;i1++) {
          rad1 = (float)(i1-omtx1/2)*den1;
          sq1 = rad1*rad1;
          for (i0=0;i0<omtx0;i0++) {
            rad0 = (float)(i0-omtx0/2)*den0;
            if (rad0*rad0 + sq1 + sq2 <= 1)
              outdata(i0,i1,i2) = cor0(i0)*cor1(i1)*cor2(i2)*data(i0+di0,i1+di1,i2+di2);
            else
              outdata(i0,i1,i2) = 0;
        } } } // i0 i1 i2
      }
    else {
      for (i2=0;i2<omtx2;i2++) {
        for (i1=0;i1<omtx1;i1++) {
          for (i0=0;i0<omtx0;i0++) {
            outdata(i0,i1,i2) = cor0(i0)*cor1(i1)*cor2(i2)*data(i0+di0,i1+di1,i2+di2);
        } } }
      }

    } // 3D

   return (0);
}
