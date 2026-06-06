# Copyright (c) 2014, Dignity Health
#
#     The GPI core node library is licensed under
# either the BSD 3-clause or the LGPL v. 3.
#
#     Under either license, the following additional term applies:
#
#         NO CLINICAL USE.  THE SOFTWARE IS NOT INTENDED FOR COMMERCIAL
# PURPOSES AND SHOULD BE USED ONLY FOR NON-COMMERCIAL RESEARCH PURPOSES.  THE
# SOFTWARE MAY NOT IN ANY EVENT BE USED FOR ANY CLINICAL OR DIAGNOSTIC
# PURPOSES.  YOU ACKNOWLEDGE AND AGREE THAT THE SOFTWARE IS NOT INTENDED FOR
# USE IN ANY HIGH RISK OR STRICT LIABILITY ACTIVITY, INCLUDING BUT NOT LIMITED
# TO LIFE SUPPORT OR EMERGENCY MEDICAL OPERATIONS OR USES.  LICENSOR MAKES NO
# WARRANTY AND HAS NOR LIABILITY ARISING FROM ANY USE OF THE SOFTWARE IN ANY
# HIGH RISK OR STRICT LIABILITY ACTIVITIES.
#
#     If you elect to license the GPI core node library under the LGPL the
# following applies:
#
#         This file is part of the GPI core node library.
#
#         The GPI core node library is free software: you can redistribute it
# and/or modify it under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation, either version 3 of the License,
# or (at your option) any later version. GPI core node library is distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even
# the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU Lesser General Public License for more details.
#
#         You should have received a copy of the GNU Lesser General Public
# License along with the GPI core node library. If not, see
# <http://www.gnu.org/licenses/>.


# Author: David Smith
# Date: 2013Nov22

import gpi
import numpy as np


class ExternalNode(gpi.NodeAPI):
    """
        Generates a Shepp-Logan phantom of the designated size.
    """
    def execType(self):
        return gpi.GPI_PROCESS

    def initUI(self):

        # Widgets
        self.addWidget('TextBox', 'Info')
        self.addWidget('SpinBox', 'Size', val=128, min=1, max=8192)
        self.addWidget('PushButton','Flip', toggle=True, val=True)
        self.addWidget('PushButton','Compute', toggle=True, val=True)
        self.addWidget('SpinBox', 'Bandlimit iterations', val=0, min=0)

        # IO Ports
        self.addOutPort('out', 'NPYarray')

    def validate(self):

        return 0


    def compute(self):

        #from phantom import phantom
        itr = self.getVal('Bandlimit iterations')

        # visibility
        if self.getVal('Compute'):

            n = self.getVal('Size')
            out = phantom(n)

            out = self.condition(out, itr)
            if self.getVal('Flip'):
                out = out[::-1]

            self.setData('out', out)

        return(0)

    def condition(self, data, iter=0):
        import numpy as np

        # don't condition
        if iter == 0:
            return data

        # recast to fftw reqs.
        orig_type = data.dtype
        data = data.astype(np.complex64, copy=False)

        band = self.window2(data.shape, windowpct=10, widthpct=100)

        # band limit in both domains
        for i in range(iter):
            data *= band # image space
            data = self.fft2(data, dir=0)
            data *= band # k-space
            data = self.fft2(data, dir=1)

        # keep original type
        data = np.abs(data).astype(orig_type, copy=False)

        return data

    def fft2(self, data, dir=0, zp=1, out_shape=[], tx_ON=True):
        # data: np.complex64
        # dir: int (0 or 1)
        # zp: float (>1)

        # simplify the fftw wrapper
        import numpy as np
        import gpi_core.math.fft as corefft

        # generate output dim size array
        # fortran dimension ordering
        outdims = list(data.shape)
        if len(out_shape):
            outdims = out_shape
        else:
            for i in range(len(outdims)):
                outdims[i] = int(outdims[i]*zp)
        outdims.reverse()
        outdims = np.array(outdims, dtype=np.int64)

        # load fft arguments
        kwargs = {}
        kwargs['dir'] = dir

        # transform or just zeropad
        if tx_ON:
            kwargs['dim1'] = 1
            kwargs['dim2'] = 1
        else:
            kwargs['dim1'] = 0
            kwargs['dim2'] = 0

        return corefft.fftw(data, outdims, **kwargs)

    def window2(self, shape, windowpct=100.0, widthpct=100.0, stopVal=0, passVal=1):
        # 2D hanning window just like shapes
        #   OUTPUT: 2D float32 circularly symmetric hanning

        import numpy as np

        # window function width
        bnd = 100.0/widthpct

        # generate coords for each dimension
        x = np.linspace(-bnd, bnd, shape[-1], endpoint=(shape[-1] % 2 != 0))
        y = np.linspace(-bnd, bnd, shape[-2], endpoint=(shape[-2] % 2 != 0))

        # create a 2D grid with coordinates then get radial coords
        xx, yy = np.meshgrid(x,y)
        radius = np.sqrt(xx*xx + yy*yy)

        # calculate hanning
        windIdx = radius <= 1.0
        passIdx = radius <= (1.0 - (windowpct/100.0))
        func = 0.5 * (1.0 - np.cos(np.pi * (1.0 - radius[windIdx]) / (windowpct/100.0)))

        # populate output array
        out = np.zeros(shape, dtype=np.float32)
        out[windIdx] = stopVal + func * (passVal - stopVal)
        out[passIdx] = passVal

        return out

## Copyright (C) 2010  Alex Opie  <lx_op@orcon.net.nz>
##
## This program is free software; you can redistribute it and/or modify it
## under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 3 of the License, or (at
## your option) any later version.
##
## This program is distributed in the hope that it will be useful, but
## WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	See the GNU
## General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program; see the file COPYING.  If not, see
## <http://www.gnu.org/licenses/>.

import numpy as np

def phantom (n = 256, p_type = 'Modified Shepp-Logan', ellipses = None):
	"""
	 phantom (n = 256, p_type = 'Modified Shepp-Logan', ellipses = None)

	Create a Shepp-Logan or modified Shepp-Logan phantom.

	A phantom is a known object (either real or purely mathematical)
	that is used for testing image reconstruction algorithms.  The
	Shepp-Logan phantom is a popular mathematical model of a cranial
	slice, made up of a set of ellipses.  This allows rigorous
	testing of computed tomography (CT) algorithms as it can be
	analytically transformed with the radon transform (see the
	function `radon').

	Inputs
	------
	n : The edge length of the square image to be produced.

	p_type : The type of phantom to produce. Either
	  "Modified Shepp-Logan" or "Shepp-Logan".  This is overridden
	  if `ellipses' is also specified.

	ellipses : Custom set of ellipses to use.  These should be in
	  the form
	  	[[I, a, b, x0, y0, phi],
	  	 [I, a, b, x0, y0, phi],
	  	 ...]
	  where each row defines an ellipse.
	  I : Additive intensity of the ellipse.
	  a : Length of the major axis.
	  b : Length of the minor axis.
	  x0 : Horizontal offset of the centre of the ellipse.
	  y0 : Vertical offset of the centre of the ellipse.
	  phi : Counterclockwise rotation of the ellipse in degrees,
	        measured as the angle between the horizontal axis and
	        the ellipse major axis.
	  The image bounding box in the algorithm is [-1, -1], [1, 1],
	  so the values of a, b, x0, y0 should all be specified with
	  respect to this box.

	Output
	------
	P : A phantom image.

	Usage example
	-------------
	  import matplotlib.pyplot as pl
	  P = phantom ()
	  pl.imshow (P)

	References
	----------
	Shepp, L. A.; Logan, B. F.; Reconstructing Interior Head Tissue
	from X-Ray Transmissions, IEEE Transactions on Nuclear Science,
	Feb. 1974, p. 232.

	Toft, P.; "The Radon Transform - Theory and Implementation",
	Ph.D. thesis, Department of Mathematical Modelling, Technical
	University of Denmark, June 1996.

	"""

	if (ellipses is None):
		ellipses = _select_phantom (p_type)
	elif (np.size (ellipses, 1) != 6):
		raise AssertionError ("Wrong number of columns in user phantom")

	# Blank image
	p = np.zeros ((n, n))

	# Create the pixel grid
	ygrid, xgrid = np.mgrid[-1:1:(1j*n), -1:1:(1j*n)]

	for ellip in ellipses:
		I   = ellip [0]
		a2  = ellip [1]**2
		b2  = ellip [2]**2
		x0  = ellip [3]
		y0  = ellip [4]
		phi = ellip [5] * np.pi / 180  # Rotation angle in radians

		# Create the offset x and y values for the grid
		x = xgrid - x0
		y = ygrid - y0

		cos_p = np.cos (phi)
		sin_p = np.sin (phi)

		# Find the pixels within the ellipse
		locs = (((x * cos_p + y * sin_p)**2) / a2
              + ((y * cos_p - x * sin_p)**2) / b2) <= 1

		# Add the ellipse intensity to those pixels
		p [locs] += I

	return p


def _select_phantom (name):
	if (name.lower () == 'shepp-logan'):
		e = _shepp_logan ()
	elif (name.lower () == 'modified shepp-logan'):
		e = _mod_shepp_logan ()
	else:
		raise ValueError ("Unknown phantom type: %s" % name)

	return e


def _shepp_logan ():
	#  Standard head phantom, taken from Shepp & Logan
	return [[   2,   .69,   .92,    0,      0,   0],
	        [-.98, .6624, .8740,    0, -.0184,   0],
	        [-.02, .1100, .3100,  .22,      0, -18],
	        [-.02, .1600, .4100, -.22,      0,  18],
	        [ .01, .2100, .2500,    0,    .35,   0],
	        [ .01, .0460, .0460,    0,     .1,   0],
	        [ .02, .0460, .0460,    0,    -.1,   0],
	        [ .01, .0460, .0230, -.08,  -.605,   0],
	        [ .01, .0230, .0230,    0,  -.606,   0],
	        [ .01, .0230, .0460,  .06,  -.605,   0]]

def _mod_shepp_logan ():
	#  Modified version of Shepp & Logan's head phantom,
	#  adjusted to improve contrast.  Taken from Toft.
	return [[   1,   .69,   .92,    0,      0,   0],
	        [-.80, .6624, .8740,    0, -.0184,   0],
	        [-.20, .1100, .3100,  .22,      0, -18],
	        [-.20, .1600, .4100, -.22,      0,  18],
	        [ .10, .2100, .2500,    0,    .35,   0],
	        [ .10, .0460, .0460,    0,     .1,   0],
	        [ .10, .0460, .0460,    0,    -.1,   0],
	        [ .10, .0460, .0230, -.08,  -.605,   0],
	        [ .10, .0230, .0230,    0,  -.606,   0],
	        [ .10, .0230, .0460,  .06,  -.605,   0]]

#def ?? ():
#	# Add any further phantoms of interest here
#	return np.array (
#	 [[ 0, 0, 0, 0, 0, 0],
#	  [ 0, 0, 0, 0, 0, 0]])

