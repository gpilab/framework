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


/*   DFT Gridding Module */

//========================================================================
// DO_DFT
// To Non-Cartesian (Degrid) with off-resonance
//========================================================================

int do_dft(Array<complex<double> > &image, Array<double> &offres, Array<double> &crds, Array<double> &time, Array<complex<double> > &data, int64_t effmtx)
{
  int i,j,k;
  int i2, j2;
  double kx,ky,xx,yy,t;
  complex<double> _I_ = complex<double>(0, -1);
  double mtxnorm;

  i2 = image.size(0)/2;
  j2 = image.size(1)/2;
  mtxnorm = 2.*M_PI*float(effmtx)/float(image.size(0));

  for (k=0;k<data.size();k++) {
    data(k) = 0.;
    kx = crds(0,k)*mtxnorm;
    ky = crds(1,k)*mtxnorm;
    t = time(k)*2.*M_PI;
    for (i=0;i<image.size(0);i++) {
      xx = i-i2;
      for (j=0;j<image.size(1);j++) {
        yy = j-j2;
        // data  = image      FT basis                 off-resonance term
        data(k) += image(i,j)*exp(_I_*(kx*xx + ky*yy + offres(i,j)*t));
    } } } // i j k

  return (0);
}


/* To Cartesian (Grid)
 */
void do_dft_grid(Array<complex<double> > &data, Array<double> &crds, Array<complex<double> > &image, int64_t effmtx, Array<double> &wghts)
{
    int i,j,k;
    int i2, j2;
    double kx,ky,xx,yy;
    complex<double> _I_ = complex<double>(0, 1);
    double mtxnorm;

    i2 = image.size(0)/2;
    j2 = image.size(1)/2;
    mtxnorm = 2.*M_PI*float(effmtx)/float(image.size(0));

    for (i=0;i<image.size(0);i++) 
    {
        xx = i-i2;
        for (j=0;j<image.size(1);j++) 
        {
            yy = j-j2;
            for (k=0;k<data.size();k++) 
            {

                kx = crds(0,k)*mtxnorm;
                ky = crds(1,k)*mtxnorm;

                get2(image,i,j) += get1(data,k)*get1(wghts,k)*exp(_I_*(kx*xx + ky*yy));
            }
        }
    }

    complex<double> scale = 1.0/image.size();
    image *= scale;

}
