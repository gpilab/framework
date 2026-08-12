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
    """Generates a Shepp-Logan phantom.

    WIDGETS:
    Dimensions          - 2D or 3D output
    Size                - Matrix size (n x n in-plane)
    Slices              - Number of slices, 3D only; output shape is (Slices, Size, Size)
    Flip                - Flip image along the y-axis
    Compute             - Enable output
    Bandlimit iterations - Band-limit conditioning iterations (2D only)
    """

    def execType(self):
        return gpi.GPI_PROCESS

    def initUI(self):
        self.addWidget('TextBox', 'Info')
        self.addWidget('ExclusivePushButtons', 'Dimensions', buttons=['2D', '3D'], val=0)
        self.addWidget('SpinBox', 'Size', val=128, min=1, max=8192)
        self.addWidget('SpinBox', 'Slices', val=128, min=1, max=8192)
        self.addWidget('PushButton', 'Flip', toggle=True, val=True)
        self.addWidget('PushButton', 'Compute', toggle=True, val=True)
        self.addWidget('SpinBox', 'Bandlimit iterations', val=0, min=0)
        self.addOutPort('out', 'NPYarray')

    def validate(self):
        is_3d = self.getVal('Dimensions') == 1
        self.setAttr('Slices', visible=is_3d)
        self.setAttr('Bandlimit iterations', visible=not is_3d)
        return 0

    def compute(self):
        is_3d = self.getVal('Dimensions') == 1

        if self.getVal('Compute'):
            n = self.getVal('Size')

            if is_3d:
                ns = self.getVal('Slices')
                out = phantom3(n, ns)
            else:
                itr = self.getVal('Bandlimit iterations')
                out = phantom(n)
                out = self.condition(out, itr)

            if self.getVal('Flip'):
                out = np.flip(out, axis=-2)

            self.setAttr('Info', val=f'shape: {list(out.shape)}')
            self.setData('out', out)

        return 0

    def condition(self, data, iter=0):
        if iter == 0:
            return data

        orig_type = data.dtype
        data = data.astype(np.complex64, copy=False)
        band = self.window2(data.shape, windowpct=10, widthpct=100)

        for i in range(iter):
            data *= band
            data = self.fft2(data, dir=0)
            data *= band
            data = self.fft2(data, dir=1)

        data = np.abs(data).astype(orig_type, copy=False)
        return data

    def fft2(self, data, dir=0, zp=1, out_shape=[], tx_ON=True):
        import gpi_core.math.fft as corefft

        outdims = list(data.shape)
        if len(out_shape):
            outdims = out_shape
        else:
            for i in range(len(outdims)):
                outdims[i] = int(outdims[i] * zp)
        outdims.reverse()
        outdims = np.array(outdims, dtype=np.int64)

        kwargs = {'dir': dir}
        if tx_ON:
            kwargs['dim1'] = 1
            kwargs['dim2'] = 1
        else:
            kwargs['dim1'] = 0
            kwargs['dim2'] = 0

        return corefft.fftw(data, outdims, **kwargs)

    def window2(self, shape, windowpct=100.0, widthpct=100.0, stopVal=0, passVal=1):
        bnd = 100.0 / widthpct
        x = np.linspace(-bnd, bnd, shape[-1], endpoint=(shape[-1] % 2 != 0))
        y = np.linspace(-bnd, bnd, shape[-2], endpoint=(shape[-2] % 2 != 0))
        xx, yy = np.meshgrid(x, y)
        radius = np.sqrt(xx * xx + yy * yy)

        windIdx = radius <= 1.0
        passIdx = radius <= (1.0 - (windowpct / 100.0))
        func = 0.5 * (1.0 - np.cos(np.pi * (1.0 - radius[windIdx]) / (windowpct / 100.0)))

        out = np.zeros(shape, dtype=np.float32)
        out[windIdx] = stopVal + func * (passVal - stopVal)
        out[passIdx] = passVal
        return out


# ---------------------------------------------------------------------------
# 2D phantom  (original: Copyright (C) 2010 Alex Opie, GPL v3+)
# ---------------------------------------------------------------------------

def phantom(n=256, p_type='Modified Shepp-Logan', ellipses=None):
    """Create a 2D Shepp-Logan phantom of size (n, n)."""
    if ellipses is None:
        ellipses = _select_phantom(p_type)
    elif np.size(ellipses, 1) != 6:
        raise AssertionError("Wrong number of columns in user phantom")

    p = np.zeros((n, n))
    ygrid, xgrid = np.mgrid[-1:1:(1j*n), -1:1:(1j*n)]

    for ellip in ellipses:
        I   = ellip[0]
        a2  = ellip[1]**2
        b2  = ellip[2]**2
        x0  = ellip[3]
        y0  = ellip[4]
        phi = ellip[5] * np.pi / 180

        x = xgrid - x0
        y = ygrid - y0
        cos_p = np.cos(phi)
        sin_p = np.sin(phi)

        locs = (((x * cos_p + y * sin_p)**2) / a2
              + ((y * cos_p - x * sin_p)**2) / b2) <= 1
        p[locs] += I

    return p


def _select_phantom(name):
    if name.lower() == 'shepp-logan':
        return _shepp_logan()
    elif name.lower() == 'modified shepp-logan':
        return _mod_shepp_logan()
    else:
        raise ValueError("Unknown phantom type: %s" % name)


def _shepp_logan():
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


def _mod_shepp_logan():
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


# ---------------------------------------------------------------------------
# 3D phantom
# ---------------------------------------------------------------------------

def phantom3(n=256, ns=256, p_type='Modified Shepp-Logan', ellipses=None):
    """Create a 3D Shepp-Logan phantom of size (ns, n, n).

    Each ellipsoid row: [I, a, b, c, x0, y0, z0, phi_deg]
      I       - additive intensity
      a, b    - semi-axes along x and y
      c       - semi-axis along z
      x0, y0  - centre offset in x/y  (bounding box [-1, 1])
      z0      - centre offset in z     (bounding box [-1, 1])
      phi_deg - rotation about z-axis in degrees
    """
    if ellipses is None:
        ellipses = _select_phantom3(p_type)
    elif np.size(ellipses, 1) != 8:
        raise AssertionError("Wrong number of columns in user 3D phantom")

    p = np.zeros((ns, n, n), dtype=np.float32)
    ygrid, xgrid = np.mgrid[-1:1:(1j*n), -1:1:(1j*n)]
    zgrid = np.linspace(-1, 1, ns, endpoint=(ns % 2 != 0))

    for ellip in ellipses:
        I   = float(ellip[0])
        a2  = ellip[1]**2
        b2  = ellip[2]**2
        c2  = ellip[3]**2
        x0  = ellip[4]
        y0  = ellip[5]
        z0  = ellip[6]
        phi = ellip[7] * np.pi / 180

        x = xgrid - x0
        y = ygrid - y0
        cos_p = np.cos(phi)
        sin_p = np.sin(phi)

        # xy contribution: shape (n, n)
        xy = ((x * cos_p + y * sin_p)**2 / a2
            + (y * cos_p - x * sin_p)**2 / b2)
        # z contribution: shape (ns,)
        z2 = (zgrid - z0)**2 / c2

        # broadcast to (ns, n, n) without allocating a full coordinate grid
        locs = xy[np.newaxis] + z2[:, np.newaxis, np.newaxis] <= 1
        p[locs] += I

    return p


def _select_phantom3(name):
    if name.lower() == 'shepp-logan':
        return _shepp_logan3()
    elif name.lower() == 'modified shepp-logan':
        return _mod_shepp_logan3()
    else:
        raise ValueError("Unknown 3D phantom type: %s" % name)


def _shepp_logan3():
    # [I,    a,      b,      c,      x0,    y0,      z0,  phi_deg]
    return [[   2,  .6900,  .9200,  .9000,    0,      0,    0,   0],
            [-.98,  .6624,  .8740,  .8800,    0, -.0184,    0,   0],
            [-.02,  .1100,  .3100,  .2200,  .22,      0,    0, -18],
            [-.02,  .1600,  .4100,  .2800, -.22,      0,    0,  18],
            [ .01,  .2100,  .2500,  .4100,    0,    .35,    0,   0],
            [ .01,  .0460,  .0460,  .0500,    0,     .1,    0,   0],
            [ .02,  .0460,  .0460,  .0500,    0,    -.1,    0,   0],
            [ .01,  .0460,  .0230,  .0500, -.08,  -.605,    0,   0],
            [ .01,  .0230,  .0230,  .0200,    0,  -.606,    0,   0],
            [ .01,  .0230,  .0460,  .0200,  .06,  -.605,    0,   0]]


def _mod_shepp_logan3():
    # [I,    a,      b,      c,      x0,    y0,      z0,  phi_deg]
    return [[  1.,  .6900,  .9200,  .9000,    0,      0,    0,   0],
            [ -.8,  .6624,  .8740,  .8800,    0, -.0184,    0,   0],
            [ -.2,  .1100,  .3100,  .2200,  .22,      0,    0, -18],
            [ -.2,  .1600,  .4100,  .2800, -.22,      0,    0,  18],
            [  .1,  .2100,  .2500,  .4100,    0,    .35,    0,   0],
            [  .1,  .0460,  .0460,  .0500,    0,    .10,    0,   0],
            [  .1,  .0460,  .0460,  .0500,    0,   -.10,    0,   0],
            [  .1,  .0460,  .0230,  .0500, -.08,  -.605,    0,   0],
            [  .1,  .0230,  .0230,  .0200,    0,  -.606,    0,   0],
            [  .1,  .0230,  .0460,  .0200,  .06,  -.605,    0,   0]]
