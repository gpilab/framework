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


# Author: Guru Krishnamoorthy, PhD
# Date: September 2026
#
# ImageCompareDisplay fuses ImageDisplay's rendering pipeline (real/complex
# scalar & magnitude x phase colormapping, slice/tile, window/level) with
# ImageCompare's side-by-side/fade/overlay comparison + ROI toolset, so two
# raw numpy arrays (2D/3D, real or complex) can be compared directly without
# two separate upstream ImageDisplay nodes.

import numpy as np
from matplotlib import cm
import gpi
from gpi import QtCore, QtGui, QtWidgets
from gpi.widgets import DisplayBox as _DisplayBox, GPILabel as _GPILabel

# ---------------------------------------------------------------------------
# ROI helpers (module level) — adapted from ImageCompare_GPI.py; duplicated
# per file per this repo's node-file-isolation convention (see
# /memories/repo/gpi_widget_conventions.md).
# ---------------------------------------------------------------------------

def _roi_coords_to_mask(coords, H, W):
    """Build a boolean 2D mask (H x W) from a ROI annotation dict.

    coords: {'type': str, 'p1': (x, y) [, 'p2': (x, y)]}   x=col, y=row
            {'type': 'Polygon', 'pts': [(x, y), ...]}
    """
    mask = np.zeros((H, W), dtype=bool)
    if not coords:
        return mask

    ann = coords.get('type', '')

    if ann == 'Pointer':
        x, y = coords['p1']
        r, c = int(round(y)), int(round(x))
        if 0 <= r < H and 0 <= c < W:
            mask[r, c] = True

    elif ann == 'Line':
        x1, y1 = coords['p1']
        x2, y2 = coords['p2']
        n = max(int(max(abs(x2 - x1), abs(y2 - y1))) * 2 + 1, 2)
        rs = np.round(np.linspace(y1, y2, n)).astype(int)
        cs = np.round(np.linspace(x1, x2, n)).astype(int)
        mask[np.clip(rs, 0, H - 1), np.clip(cs, 0, W - 1)] = True

    elif ann == 'Rectangle':
        x1, y1 = coords['p1']
        x2, y2 = coords['p2']
        r1, r2 = max(0, int(min(y1, y2))), min(H - 1, int(max(y1, y2)))
        c1, c2 = max(0, int(min(x1, x2))), min(W - 1, int(max(x1, x2)))
        if r2 >= r1 and c2 >= c1:
            mask[r1:r2 + 1, c1:c2 + 1] = True

    elif ann == 'Ellipse':
        x1, y1 = coords['p1']
        x2, y2 = coords['p2']
        cr, cc = (y1 + y2) / 2, (x1 + x2) / 2
        ar = max(abs(y2 - y1) / 2, 0.5)
        ac = max(abs(x2 - x1) / 2, 0.5)
        r1, r2 = max(0, int(min(y1, y2))), min(H - 1, int(max(y1, y2)))
        c1, c2 = max(0, int(min(x1, x2))), min(W - 1, int(max(x1, x2)))
        if r2 >= r1 and c2 >= c1:
            rr, cc_g = np.mgrid[r1:r2 + 1, c1:c2 + 1]
            mask[r1:r2 + 1, c1:c2 + 1] = ((rr - cr) / ar) ** 2 + ((cc_g - cc) / ac) ** 2 <= 1

    elif ann == 'Polygon':
        pts = coords.get('pts', [])
        if len(pts) >= 3:
            from matplotlib.path import Path as _MplPath
            smooth = _smooth_polygon(np.asarray(pts, dtype=float), n_per_seg=40)
            verts  = np.vstack([smooth, smooth[:1]])
            codes  = ([_MplPath.MOVETO]
                      + [_MplPath.LINETO] * (len(smooth) - 1)
                      + [_MplPath.CLOSEPOLY])
            poly_path = _MplPath(verts, codes)
            rr, cc_g = np.mgrid[0:H, 0:W]
            grid = np.column_stack([cc_g.ravel().astype(float),
                                    rr.ravel().astype(float)])
            mask = poly_path.contains_points(grid).reshape(H, W)

    return mask


def _roi_x_extent(coord):
    """Return (min_x, max_x) of a ROI annotation dict's data-coordinates, or
    None if it has no points yet (in-progress annotation)."""
    ann = coord.get('type', '')
    if ann == 'Pointer':
        x, _ = coord['p1']
        return (x, x)
    elif ann == 'Polygon':
        pts = coord.get('pts', [])
        if not pts:
            return None
        xs = [p[0] for p in pts]
        return (min(xs), max(xs))
    else:
        x1, _ = coord['p1']
        p2 = coord.get('p2')
        if p2 is None:
            return (x1, x1)
        x2, _ = p2
        return (min(x1, x2), max(x1, x2))


def _shift_roi_x(coord, dx):
    """Copy of a ROI annotation dict with every x-coordinate shifted by dx."""
    c = dict(coord)
    if coord.get('type') == 'Polygon':
        c['pts'] = [(x + dx, y) for x, y in coord.get('pts', [])]
    else:
        c['p1'] = (coord['p1'][0] + dx, coord['p1'][1])
        if coord.get('p2') is not None:
            c['p2'] = (coord['p2'][0] + dx, coord['p2'][1])
    return c


def _smooth_polygon(pts, n_per_seg=20):
    """Closed Catmull-Rom spline through every point in pts (K, 2), K >= 3."""
    pts = np.asarray(pts, dtype=float)
    n   = len(pts)
    if n < 3:
        return pts
    t  = np.linspace(0.0, 1.0, n_per_seg, endpoint=False)
    t2 = t * t
    t3 = t2 * t
    c0 = (-t3 + 2 * t2 - t)
    c1 = (3 * t3 - 5 * t2 + 2)
    c2 = (-3 * t3 + 4 * t2 + t)
    c3 = (t3 - t2)
    segs = []
    for i in range(n):
        p0, p1 = pts[(i - 1) % n], pts[i]
        p2, p3 = pts[(i + 1) % n], pts[(i + 2) % n]
        segs.append(0.5 * (
            c0[:, None] * p0 + c1[:, None] * p1 +
            c2[:, None] * p2 + c3[:, None] * p3
        ))
    return np.concatenate(segs, axis=0)


def _format_compare_stats(data_left, data_right, mask_left, mask_right,
                          label='ROI', paired=True):
    """Physical-value (not RGBA luminance) comparison stats for L/R, since
    this node has direct access to the raw numeric input arrays (unlike
    ImageCompare, which only ever sees already-rendered RGBA from upstream
    ImageDisplay nodes). Complex inputs are reported as magnitude, matching
    ImageDisplay's own ROI-stats convention. mask_left/mask_right may be
    larger than the data footprint (M x P Edge/Black-pixel framing pads the
    displayed image) — center-cropped to match, same as ImageDisplay's
    _format_roi_stats."""
    def _vals(data, mask):
        if mask is None or not mask.any():
            return None
        src = np.abs(data) if np.iscomplexobj(data) else np.asarray(data, dtype=float)
        if src.ndim > 2:
            src = src[..., 0]
        mh, mw = mask.shape[:2]
        dh, dw = src.shape[:2]
        if mh != dh or mw != dw:
            ph = max(0, (mh - dh) // 2)
            pw = max(0, (mw - dw) // 2)
            mask = mask[ph:ph + dh, pw:pw + dw]
            if mask.shape[:2] != (dh, dw):
                return None
        v = src[mask]
        v = v[np.isfinite(v)]
        return v if len(v) else None

    vl = _vals(data_left, mask_left)
    vr = _vals(data_right, mask_right)
    if vl is None and vr is None:
        return ''

    parts = [f'{label}:']
    parts.append(f'L: n={len(vl):,} mean={vl.mean():.4g} std={vl.std():.4g} '
                 f'min={vl.min():.4g} max={vl.max():.4g}' if vl is not None else 'L: empty')
    parts.append(f'R: n={len(vr):,} mean={vr.mean():.4g} std={vr.std():.4g} '
                 f'min={vr.min():.4g} max={vr.max():.4g}' if vr is not None else 'R: empty')
    if vl is not None and vr is not None:
        parts.append(f'\u0394mean(L-R)={vl.mean() - vr.mean():.4g}')
        if paired and vl.shape == vr.shape:
            parts.append(f'RMSE={np.sqrt(np.mean((vl - vr) ** 2)):.4g}')
    return '   '.join(parts)


_ROI_PALETTE = [
    QtCore.Qt.green, QtCore.Qt.yellow, QtCore.Qt.cyan,
    QtCore.Qt.magenta, QtCore.Qt.white, QtCore.Qt.red,
]

_ROI_PALETTE_RGB = [
    (  0, 255,   0), (255, 255,   0), (  0, 255, 255),
    (255,   0, 255), (255, 255, 255), (255,   0,   0),
]


def _phase_cmap(cmap):
    """matplotlib colormap for the phase (hue) channel of the M x P complex
    display, given a complex Color Map index."""
    if cmap == 0:
        return cm.hsv
    elif cmap == 1:
        try:
            import seaborn as sns
            import matplotlib.colors as col
            return col.ListedColormap(sns.color_palette('hls', 256))
        except ImportError:
            return cm.hsv
    elif cmap == 2:
        try:
            import seaborn as sns
            import matplotlib.colors as col
            return col.ListedColormap(sns.color_palette('husl', 256))
        except ImportError:
            return cm.hsv
    else:
        return cm.coolwarm


def _scalar_cmap_rgb(cmap, data):
    """Return (rd, gn, be) in [0, 1] for a real Color Map index, given data
    already scaled to the 0..255 range (float). Mirrors ImageDisplay's
    inline per-pixel colormap math."""
    rd = np.zeros(data.shape)
    gn = np.zeros(data.shape)
    be = np.zeros(data.shape)

    if cmap == 1:  # IceFire
        hue = 4. * (data / 256.)
        h0 = hue < 1.; h1 = (hue >= 1.) & (hue < 2.)
        h2 = (hue >= 2.) & (hue < 3.); h3 = (hue >= 3.) & (hue < 4.)
        be[h0] = hue[h0]
        gn[h1] = (hue - 1.)[h1]; rd[h1] = (hue - 1.)[h1]; be[h1] = 1.
        gn[h2] = 1.;             rd[h2] = 1.;             be[h2] = (3. - hue)[h2]
        rd[h3] = 1.;             gn[h3] = (4. - hue)[h3]

    elif cmap == 2:  # Fire
        hue = 4. * (data / 256.)
        h0 = hue < 1.; h1 = (hue >= 1.) & (hue < 2.)
        h2 = (hue >= 2.) & (hue < 3.); h3 = (hue >= 3.) & (hue < 4.)
        be[h0] = hue[h0]
        be[h1] = (2. - hue)[h1]; rd[h1] = (hue - 1.)[h1]
        rd[h2] = 1.;             gn[h2] = (hue - 2.)[h2]
        rd[h3] = 1.;             gn[h3] = 1.; be[h3] = (hue - 3.)[h3]

    elif cmap == 3:  # Hot
        hue = 3. * (data / 256.)
        h0 = hue < 1.; h1 = (hue >= 1.) & (hue < 2.); h2 = (hue >= 2.) & (hue < 3.)
        rd[h0] = hue[h0]
        rd[h1] = 1.; gn[h1] = (hue - 1.)[h1]
        rd[h2] = 1.; gn[h2] = 1.; be[h2] = (hue - 2.)[h2]

    elif cmap == 4:  # HOT2 (ASIST)
        r0 = data < 20.; r1 = (data >= 20.) & (data <= 100.)
        r3 = (data >= 128.) & (data <= 191.); r4 = data > 191.
        rd[r0] = data[r0] * (4. / 255.)
        rd[r1] = (80. - (data[r1] - 20.)) / 255.
        rd[r3] = (data[r3] - 128.) * (4. / 255.)
        rd[r4] = 1.
        g1 = (data >= 45.) & (data <= 130.); g2 = (data > 130.) & (data < 192.); g3 = data >= 192.
        gn[g1] = (data[g1] - 45.) * (3. / 255.)
        gn[g2] = 1.
        gn[g3] = (252. - (data[g3] - 192.) * 4.) / 255.
        b1 = (data >= 1.) & (data < 86.); b2 = (data >= 86.) & (data <= 137.)
        be[b1] = (data[b1] - 1.) * (3. / 255.)
        be[b2] = (255. - (data[b2] - 86.) * 5.) / 255.

    elif cmap == 5:  # BGR
        hue = 4. * (data / 256.)
        h0 = hue < 1.; h1 = (hue >= 1.) & (hue < 2.)
        h2 = (hue >= 2.) & (hue < 3.); h3 = (hue >= 3.) & (hue < 4.)
        be[h0] = hue[h0]
        gn[h1] = (hue - 1.)[h1]; be[h1] = 1.
        gn[h2] = 1.; rd[h2] = (hue - 2.)[h2]; be[h2] = (3. - hue)[h2]
        rd[h3] = 1.; gn[h3] = (4. - hue)[h3]

    return rd, gn, be


# ---------------------------------------------------------------------------
# _LockedLabel — GPILabel subclass supporting multiple simultaneous ROIs used
# to mark a region for LEFT-vs-RIGHT comparison (adapted from
# ImageCompare_GPI.py, unchanged — this part is orthogonal to whether the
# two sides were rendered upstream or in this node itself).
# ---------------------------------------------------------------------------

class _LockedLabel(_GPILabel):

    def __init__(self, wdgGroup, parent=None):
        super().__init__(wdgGroup, parent)
        self._rois        = []
        self._ext_labels  = []
        self._drawing     = False
        self._cur_p1      = None
        self._cur_p2      = None
        self._poly_pts    = []
        self._poly_cursor = None
        self._edit_roi_idx = None
        self._drag_pt_key  = None
        self._hover_pt_key = None
        self.setFocusPolicy(QtCore.Qt.ClickFocus)

    def _scale(self):
        return getattr(self._wg, '_scaleFact', 1.0)

    def _pix_to_data(self, qpt):
        s = self._scale()
        return (qpt.x() / s, qpt.y() / s)

    def _data_to_pix(self, xy):
        s = self._scale()
        return QtCore.QPoint(int(xy[0] * s), int(xy[1] * s))

    def _cur_color(self):
        return _ROI_PALETTE[len(self._rois) % len(_ROI_PALETTE)]

    def _draw_shape(self, painter, ann, p1, p2):
        if ann == 'Pointer':
            x, y, r = p1.x(), p1.y(), 8
            painter.drawLine(x - r, y, x + r, y)
            painter.drawLine(x, y - r, x, y + r)
        elif p2 is not None:
            if ann == 'Line':
                painter.drawLine(p1, p2)
            elif ann == 'Rectangle':
                painter.drawRect(QtCore.QRect(p1, p2))
            elif ann == 'Ellipse':
                painter.drawEllipse(QtCore.QRect(p1, p2))

    def _label_anchor(self, ann, p1, p2):
        if ann == 'Pointer' or p2 is None:
            return QtCore.QPoint(p1.x() + 10, p1.y() - 4)
        x = min(p1.x(), p2.x())
        y = min(p1.y(), p2.y())
        return QtCore.QPoint(x + 2, y - 4)

    def _ctrl_points(self, roi):
        if roi['type'] == 'Polygon':
            return [(i, self._data_to_pix(pt)) for i, pt in enumerate(roi.get('pts', []))]
        pts = [('p1', self._data_to_pix(roi['p1']))]
        if roi.get('p2') is not None:
            pts.append(('p2', self._data_to_pix(roi['p2'])))
        return pts

    def _hit_ctrl_point(self, qpt, threshold=8):
        idx = self._edit_roi_idx
        if idx is None or not (0 <= idx < len(self._rois)):
            return None
        roi = self._rois[idx]
        best_d, best_key = threshold + 1, None
        for key, px in self._ctrl_points(roi):
            d = (qpt - px).manhattanLength()
            if d < best_d:
                best_d, best_key = d, key
        return best_key

    def paintEvent(self, event):
        QtWidgets.QLabel.paintEvent(self, event)
        painter = QtGui.QPainter(self)
        painter.setBrush(QtCore.Qt.NoBrush)
        font = painter.font()
        font.setPointSize(8)
        font.setBold(True)
        painter.setFont(font)
        for i, roi in enumerate(self._rois):
            color = _ROI_PALETTE[i % len(_ROI_PALETTE)]
            painter.setPen(QtGui.QPen(color, 1))
            lbl_pt = None
            if roi['type'] == 'Polygon':
                pts_data = roi.get('pts', [])
                if len(pts_data) >= 3:
                    s = self._scale()
                    pix_arr = np.array([[x * s, y * s] for x, y in pts_data], dtype=float)
                    smooth  = _smooth_polygon(pix_arr, n_per_seg=20)
                    qpoly   = QtGui.QPolygon([
                        QtCore.QPoint(int(round(p[0])), int(round(p[1])))
                        for p in smooth
                    ])
                    painter.drawPolygon(qpoly)
                    painter.setBrush(QtGui.QBrush(color))
                    painter.setPen(QtCore.Qt.NoPen)
                    for pt in pix_arr:
                        painter.drawEllipse(
                            QtCore.QPoint(int(round(pt[0])), int(round(pt[1]))), 2, 2)
                    painter.setBrush(QtCore.Qt.NoBrush)
                    painter.setPen(QtGui.QPen(color, 1))
                    xs, ys = pix_arr[:, 0], pix_arr[:, 1]
                    lbl_pt = QtCore.QPoint(int(xs.min()) + 2, int(ys.min()) - 4)
            else:
                p1 = self._data_to_pix(roi['p1'])
                p2 = self._data_to_pix(roi['p2']) if roi.get('p2') else None
                self._draw_shape(painter, roi['type'], p1, p2)
                lbl_pt = self._label_anchor(roi['type'], p1, p2)
            if lbl_pt is not None:
                lbl_str = str(i + 1)
                painter.setPen(QtGui.QPen(QtCore.Qt.black, 1))
                painter.drawText(lbl_pt + QtCore.QPoint(1, 1), lbl_str)
                painter.setPen(QtGui.QPen(color, 1))
                painter.drawText(lbl_pt, lbl_str)
        # Side-by-side mode: mirror a ROI drawn in one half into the other's
        # canvas position (dashed outline) so propagation is visible.
        mirror_dx = getattr(self._wg, '_mirror_offset', None)
        if mirror_dx:
            s = self._scale()
            offset_px = mirror_dx * s
            for i, roi in enumerate(self._rois):
                color = _ROI_PALETTE[i % len(_ROI_PALETTE)]
                if roi['type'] == 'Polygon':
                    pts_data = roi.get('pts', [])
                    if len(pts_data) < 3:
                        continue
                    xs = [p[0] for p in pts_data]
                    min_x, max_x = min(xs), max(xs)
                else:
                    p1, p2 = roi['p1'], roi.get('p2')
                    xs = [p1[0]] + ([p2[0]] if p2 else [])
                    min_x, max_x = min(xs), max(xs)
                if max_x < mirror_dx:
                    shift = offset_px
                elif min_x >= mirror_dx:
                    shift = -offset_px
                else:
                    continue   # straddles the midline — no clean mirror
                painter.setPen(QtGui.QPen(color, 1, QtCore.Qt.DashLine))
                if roi['type'] == 'Polygon':
                    pix_arr = np.array([[x * s + shift, y * s] for x, y in pts_data],
                                       dtype=float)
                    smooth = _smooth_polygon(pix_arr, n_per_seg=20)
                    qpoly  = QtGui.QPolygon([
                        QtCore.QPoint(int(round(p[0])), int(round(p[1])))
                        for p in smooth
                    ])
                    painter.drawPolygon(qpoly)
                else:
                    shift_pt = QtCore.QPoint(int(round(shift)), 0)
                    p1px = self._data_to_pix(p1) + shift_pt
                    p2px = (self._data_to_pix(p2) + shift_pt) if p2 else None
                    self._draw_shape(painter, roi['type'], p1px, p2px)
        for lbl_num, dx, dy in self._ext_labels:
            color   = _ROI_PALETTE[(lbl_num - 1) % len(_ROI_PALETTE)]
            base_px = self._data_to_pix((dx, dy))
            lbl_pt  = base_px + QtCore.QPoint(2, -4)
            lbl_str = str(lbl_num)
            painter.setPen(QtGui.QPen(QtCore.Qt.black, 1))
            painter.drawText(lbl_pt + QtCore.QPoint(1, 1), lbl_str)
            painter.setPen(QtGui.QPen(color, 1))
            painter.drawText(lbl_pt, lbl_str)
        ei = self._edit_roi_idx
        if ei is not None and 0 <= ei < len(self._rois):
            color = _ROI_PALETTE[ei % len(_ROI_PALETTE)]
            for key, px in self._ctrl_points(self._rois[ei]):
                active = (key == self._hover_pt_key or key == self._drag_pt_key)
                r = 5 if active else 3
                painter.setPen(QtGui.QPen(QtCore.Qt.white, 1))
                painter.setBrush(QtGui.QBrush(color))
                painter.drawEllipse(px, r, r)
            painter.setBrush(QtCore.Qt.NoBrush)
        if self._poly_pts:
            color   = self._cur_color()
            preview = self._poly_pts[:]
            if self._poly_cursor is not None:
                preview = preview + [self._poly_cursor]
            pix_arr = np.array([[p.x(), p.y()] for p in preview], dtype=float)
            if len(preview) >= 3:
                smooth  = _smooth_polygon(pix_arr, n_per_seg=15)
                qpoly   = QtGui.QPolygon([
                    QtCore.QPoint(int(round(p[0])), int(round(p[1])))
                    for p in smooth
                ])
                painter.setPen(QtGui.QPen(color, 1, QtCore.Qt.DashLine))
                painter.drawPolygon(qpoly)
            elif len(preview) == 2:
                painter.setPen(QtGui.QPen(color, 1, QtCore.Qt.DashLine))
                painter.drawLine(preview[0], preview[1])
            elif len(preview) == 1 and self._poly_cursor is not None:
                painter.setPen(QtGui.QPen(color, 1, QtCore.Qt.DotLine))
                painter.drawLine(preview[0], self._poly_cursor)
            painter.setBrush(QtGui.QBrush(color))
            painter.setPen(QtCore.Qt.NoPen)
            for pt in self._poly_pts:
                painter.drawEllipse(pt, 3, 3)
            painter.setBrush(QtCore.Qt.NoBrush)
        elif self._drawing and self._cur_p1 is not None:
            painter.setPen(QtGui.QPen(self._cur_color(), 1, QtCore.Qt.DashLine))
            self._draw_shape(painter, self._wg.ann_type, self._cur_p1, self._cur_p2)
        painter.end()

    def mousePressEvent(self, event):
        if event.button() != QtCore.Qt.LeftButton:
            return
        if self._edit_roi_idx is not None:
            pt_key = self._hit_ctrl_point(event.pos())
            if pt_key is not None:
                self._drag_pt_key = pt_key
                self.setCursor(QtCore.Qt.SizeAllCursor)
                self.update()
                return
        ann = self._wg.ann_type
        if ann == 'Polygon':
            self._poly_pts.append(event.pos())
            self._poly_cursor = event.pos()
            self.setFocus()
            self.update()
        else:
            self._drawing = True
            self._cur_p1  = event.pos()
            self._cur_p2  = None
            self.update()

    def mouseMoveEvent(self, event):
        if self._drag_pt_key is not None:
            new_data = self._pix_to_data(event.pos())
            roi = self._rois[self._edit_roi_idx]
            if roi['type'] == 'Polygon':
                pts = list(roi['pts'])
                pts[self._drag_pt_key] = new_data
                roi['pts'] = pts
            else:
                roi[self._drag_pt_key] = new_data
            self.update()
            return
        if self._edit_roi_idx is not None:
            pt_key = self._hit_ctrl_point(event.pos())
            if pt_key != self._hover_pt_key:
                self._hover_pt_key = pt_key
                self.setCursor(QtCore.Qt.PointingHandCursor if pt_key is not None
                               else QtCore.Qt.ArrowCursor)
                self.update()
        if self._poly_pts and self._wg.ann_type == 'Polygon':
            self._poly_cursor = event.pos()
            self.update()
            return
        if not self._drawing:
            return
        if self._wg.isPointer():
            self._cur_p1 = event.pos()
        else:
            self._cur_p2 = event.pos()
        self.update()

    def mouseReleaseEvent(self, event):
        if self._drag_pt_key is not None:
            if event.button() == QtCore.Qt.LeftButton:
                self._drag_pt_key = None
                self.unsetCursor()
                self.update()
                self.annotationChanged.emit()
            return
        ann = self._wg.ann_type
        if ann == 'Polygon':
            return
        if event.button() != QtCore.Qt.LeftButton or not self._drawing:
            return
        self._drawing = False
        p2_pix = event.pos()
        if not self._wg.isPointer() and self._cur_p1 == p2_pix:
            self._cur_p1 = None
            self._cur_p2 = None
            self.update()
            return
        roi = {'type': ann, 'p1': self._pix_to_data(self._cur_p1)}
        if ann != 'Pointer':
            roi['p2'] = self._pix_to_data(p2_pix)
        self._rois.append(roi)
        self._cur_p1 = None
        self._cur_p2 = None
        self.update()
        self.annotationChanged.emit()

    def mouseDoubleClickEvent(self, event):
        if event.button() != QtCore.Qt.LeftButton:
            return
        if self._edit_roi_idx is not None:
            self._wg._toggle_edit_roi(self._edit_roi_idx)
            return
        if self._wg.ann_type != 'Polygon':
            return
        if self._poly_pts:
            self._poly_pts.pop()
        if len(self._poly_pts) >= 3:
            roi = {'type': 'Polygon',
                   'pts': [self._pix_to_data(p) for p in self._poly_pts]}
            self._rois.append(roi)
            self.annotationChanged.emit()
        self._poly_pts    = []
        self._poly_cursor = None
        self.update()

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            if self._poly_pts:
                self._poly_pts    = []
                self._poly_cursor = None
                self.update()
            elif self._drawing:
                self._drawing = False
                self._cur_p1  = None
                self._cur_p2  = None
                self.update()
        else:
            super().keyPressEvent(event)

    def contextMenuEvent(self, event):
        menu = QtWidgets.QMenu(self)

        if self._rois:
            for i, roi in enumerate(self._rois):
                editing = (i == self._edit_roi_idx)
                sub     = menu.addMenu(f'ROI {i + 1}  ({roi["type"]})')
                a_send  = sub.addAction('Send to output port')
                a_send.setData(('send', i))
                a_edit  = sub.addAction('Done editing' if editing else 'Edit')
                a_edit.setData(('edit', i))
                a_remove = sub.addAction('Remove')
                a_remove.setData(('clear', i))
            menu.addSeparator()
            a_send_all = menu.addAction('Send all ROIs to output port')
            a_send_all.setData(('send_all', None))
            menu.addSeparator()
            a_save_shapes = menu.addAction('Save ROI shapes (.json)...')
            a_save_shapes.setData(('save_shapes', None))
            save_mask_sub = menu.addMenu('Save pixel mask (.npy)...')
            a_save_labeled = save_mask_sub.addAction('Labeled (ROI index)')
            a_save_labeled.setData(('save_labeled', None))
            a_save_binary  = save_mask_sub.addAction('Binary (all ROIs merged)')
            a_save_binary.setData(('save_binary', None))
            menu.addSeparator()
            a_clear_all = menu.addAction('Clear all ROIs')
            a_clear_all.setData(('clear_all', None))
            menu.addSeparator()

        a_load_shapes = menu.addAction('Load ROI shapes (.json)...')
        a_load_shapes.setData(('load_shapes', None))
        a_load_mask = menu.addAction('Load pixel mask (.npy)...')
        a_load_mask.setData(('load_mask', None))

        action = menu.exec_(self.mapToGlobal(event.pos()))
        if action is None:
            return
        op, idx = action.data()
        if op == 'send':
            self._wg._request_send_roi(idx)
        elif op == 'clear':
            self._rois.pop(idx)
            if self._edit_roi_idx == idx:
                self._edit_roi_idx = None
            elif self._edit_roi_idx is not None and self._edit_roi_idx > idx:
                self._edit_roi_idx -= 1
            self.update()
            self.annotationChanged.emit()
        elif op == 'send_all':
            self._wg._request_send_roi()
        elif op == 'edit':
            self._wg._toggle_edit_roi(idx)
        elif op == 'save_shapes':
            self._wg._save_shapes_to_file()
        elif op == 'save_labeled':
            self._wg._save_mask_to_file(binary=False)
        elif op == 'save_binary':
            self._wg._save_mask_to_file(binary=True)
        elif op == 'load_shapes':
            self._wg._load_shapes_from_file()
        elif op == 'load_mask':
            self._wg._load_mask_from_file()
        elif op == 'clear_all':
            self._rois         = []
            self._edit_roi_idx = None
            self.update()
            self.annotationChanged.emit()


class _HoverFilter(QtCore.QObject):
    def __init__(self, viewport, parent=None):
        super().__init__(parent)
        self._vp = viewport

    def eventFilter(self, obj, event):
        t = event.type()
        if t == QtCore.QEvent.MouseMove:
            s = self._vp._scaleFact
            self._vp._show_hover(int(event.pos().y() / s),
                                 int(event.pos().x() / s))
        elif t == QtCore.QEvent.Leave:
            self._vp._hover_lbl.setText('—')
        return False


class CompareViewBox(_DisplayBox):
    """DisplayBox extended with a multi-ROI annotation tool for comparing the
    SAME region across the left/right rendered images. Unlike
    ImageCompare_GPI.py's version (which only ever sees already-rendered RGBA
    from upstream ImageDisplay nodes), this node renders both sides itself,
    so hover/stats can report actual physical values (magnitude for complex
    data) rather than RGBA luminance whenever available."""

    def __init__(self, title, parent=None):
        super().__init__(title, parent)
        self._rawdata_left     = None   # rendered RGBA uint8, always available
        self._rawdata_right    = None
        self._rawphys_left     = None   # raw numeric (pre-colormap) data; None if unavailable
        self._rawphys_right    = None
        self._pending_roi_mask = None
        self._loaded_mask      = None
        self._mirror_offset    = None   # single-image width in Side-by-side mode, else None

        old_label = self.imageLabel
        try:
            old_label.annotationChanged.disconnect()
        except Exception:
            pass

        self.imageLabel = _LockedLabel(self)
        self.imageLabel.annotationChanged.connect(self.somethingChanged)
        self.imageLabel.setBackgroundRole(QtGui.QPalette.Base)
        self.imageLabel.setSizePolicy(
            QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)
        self.imageLabel.setScaledContents(True)
        self.imageLabel.setMouseTracking(True)
        self.scrollArea.setWidget(self.imageLabel)

        poly_btn = QtWidgets.QCheckBox('Polygon')
        poly_btn.setCheckable(True)
        poly_btn.setAutoExclusive(True)
        poly_btn.setChecked(False)
        poly_btn.stateChanged.connect(self.annotationButton)
        self.ann_box.addWidget(poly_btn)
        self.collapsables.append(poly_btn)
        poly_btn.setVisible(not self._isCollapsed)

        self._hover_filter = _HoverFilter(self)
        self.imageLabel.installEventFilter(self._hover_filter)

        self._hover_lbl = QtWidgets.QLabel('—')
        self._hover_lbl.setStyleSheet(
            'color:#cccccc; font-size:11px; padding:2px 4px;'
            'background:#1e1e1e; border-top:1px solid #3a3a3a;')
        self._hover_lbl.setMinimumHeight(18)

        self._stats_lbl = QtWidgets.QLabel('')
        self._stats_lbl.setStyleSheet(
            'color:#88ff88; font-size:11px; padding:2px 4px;'
            'background:#1a2a1a; border-top:1px solid #3a3a3a;')
        self._stats_lbl.setWordWrap(True)
        self._stats_lbl.hide()

        gl = self.layout()
        nr = gl.rowCount()
        nc = max(gl.columnCount(), 1)
        gl.addWidget(self._hover_lbl, nr,     0, 1, nc)
        gl.addWidget(self._stats_lbl, nr + 1, 0, 1, nc)

    def _show_hover(self, r, c):
        # Prefer physical values (magnitude/phase for complex) when available
        # (no Edge/Black-pixel M x P framing pad active — see compute(),
        # which only publishes rawphys_* when pad == 0 to keep pixel
        # coordinates aligned); otherwise fall back to RGBA luminance.
        pl, pr = self._rawphys_left, self._rawphys_right
        if pl is not None and pr is not None:
            h, w0 = pl.shape[:2]
            c_local = c % w0 if w0 else c
            if not (0 <= r < h and 0 <= c_local < w0):
                self._hover_lbl.setText(f'[{r}, {c}]   (out of bounds)')
                return
            lv, rv = pl[r, c_local], pr[r, c_local]
            if np.iscomplexobj(pl) or np.iscomplexobj(pr):
                lstr = f'{abs(lv):.4g}\u2220{np.angle(lv, deg=True):.1f}\u00b0'
                rstr = f'{abs(rv):.4g}\u2220{np.angle(rv, deg=True):.1f}\u00b0'
                dstr = f'{abs(lv) - abs(rv):.4g}'
            else:
                lstr, rstr = f'{float(lv):.4g}', f'{float(rv):.4g}'
                dstr = f'{float(lv) - float(rv):.4g}'
            self._hover_lbl.setText(
                f'[{r}, {c_local}]   L={lstr}   R={rstr}   \u0394(L-R)={dstr}')
            return

        dl, dr = self._rawdata_left, self._rawdata_right
        if dl is None or dr is None:
            self._hover_lbl.setText(f'[{r}, {c}]')
            return
        h, w0 = dl.shape[:2]
        c_local = c % w0 if w0 else c
        if not (0 <= r < h and 0 <= c_local < w0):
            self._hover_lbl.setText(f'[{r}, {c}]   (out of bounds)')
            return
        lp = dl[r, c_local, :3].astype(float)
        rp = dr[r, c_local, :3].astype(float)
        l_lum = 0.2126 * lp[0] + 0.7152 * lp[1] + 0.0722 * lp[2]
        r_lum = 0.2126 * rp[0] + 0.7152 * rp[1] + 0.0722 * rp[2]
        self._hover_lbl.setText(
            f'[{r}, {c_local}]   L={l_lum:.1f}   R={r_lum:.1f}   '
            f'\u0394(L-R)={l_lum - r_lum:.1f}')

    def _canon_roi(self, roi):
        """Map a ROI's data coords into the canonical single-image (h0, w0)
        space, mirroring compute()'s propagation logic — so Send/Save always
        produce a mask sized to ONE image, even if drawn on the right half
        of a Side-by-side composite."""
        mirror_dx = self._mirror_offset
        if not mirror_dx:
            return roi
        xs = _roi_x_extent(roi)
        if xs is None:
            return roi
        min_x, max_x = xs
        if min_x >= mirror_dx:
            return _shift_roi_x(roi, -mirror_dx)
        return roi   # already left-half, or straddling (best effort)

    def _request_send_roi(self, idx=None):
        rois = self.imageLabel._rois
        if not rois or self._rawdata_left is None:
            return
        H, W = self._rawdata_left.shape[:2]
        targets = [rois[idx]] if (idx is not None and 0 <= idx < len(rois)) else rois
        label_mask = np.zeros((H, W), dtype=np.uint8)
        for k, roi in enumerate(targets, start=1):
            m = _roi_coords_to_mask(self._canon_roi(roi), H, W)
            label_mask[m] = k
        if label_mask.any():
            self._pending_roi_mask = label_mask
            self.somethingChanged()

    def _save_mask_to_file(self, binary=False):
        rois = self.imageLabel._rois
        if not rois or self._rawdata_left is None:
            return
        H, W = self._rawdata_left.shape[:2]
        label_mask = np.zeros((H, W), dtype=np.uint8)
        for k, roi in enumerate(rois, start=1):
            m = _roi_coords_to_mask(self._canon_roi(roi), H, W)
            label_mask[m] = k
        if not label_mask.any():
            return
        save_arr     = (label_mask > 0).astype(np.uint8) if binary else label_mask
        default_name = 'roi_mask_binary.npy' if binary else 'roi_mask_labeled.npy'
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, 'Save ROI mask', default_name,
            'NumPy array (*.npy);;All files (*)',
            options=QtWidgets.QFileDialog.DontUseNativeDialog)
        if path:
            if not path.endswith('.npy'):
                path += '.npy'
            np.save(path, save_arr)

    def _save_shapes_to_file(self):
        import json
        rois = self.imageLabel._rois
        if not rois:
            return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, 'Save ROI shapes', 'roi_shapes.json',
            'ROI shapes (*.json);;All files (*)',
            options=QtWidgets.QFileDialog.DontUseNativeDialog)
        if not path:
            return
        if not path.endswith('.json'):
            path += '.json'
        data = []
        for r in rois:
            if r['type'] == 'Polygon':
                data.append({'type': 'Polygon',
                             'pts': [list(p) for p in r.get('pts', [])]})
            else:
                entry = {'type': r['type'], 'p1': list(r['p1'])}
                if r.get('p2') is not None:
                    entry['p2'] = list(r['p2'])
                data.append(entry)
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

    def _load_shapes_from_file(self):
        import json
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, 'Load ROI shapes', '',
            'ROI shapes (*.json);;All files (*)',
            options=QtWidgets.QFileDialog.DontUseNativeDialog)
        if not path:
            return
        try:
            with open(path) as f:
                data = json.load(f)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, 'Load failed', str(e))
            return
        loaded = []
        for item in data:
            try:
                if item['type'] == 'Polygon':
                    roi = {'type': 'Polygon',
                           'pts': [tuple(p) for p in item.get('pts', [])]}
                else:
                    roi = {'type': item['type'], 'p1': tuple(item['p1'])}
                    if item.get('p2') is not None:
                        roi['p2'] = tuple(item['p2'])
                loaded.append(roi)
            except Exception:
                pass
        if loaded:
            self.imageLabel._rois = loaded
            self.imageLabel._ext_labels = []
            self.imageLabel.update()
            self.somethingChanged()

    def _load_mask_from_file(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, 'Load pixel mask', '',
            'NumPy array (*.npy);;All files (*)',
            options=QtWidgets.QFileDialog.DontUseNativeDialog)
        if not path:
            return
        try:
            mask = np.load(path)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, 'Load failed', str(e))
            return
        if mask.ndim != 2:
            QtWidgets.QMessageBox.warning(
                self, 'Load failed', f'Expected 2D array, got shape {mask.shape}')
            return
        self._loaded_mask = mask.astype(np.uint8)
        self.somethingChanged()

    def get_roi_mask(self):
        mask = self._pending_roi_mask
        self._pending_roi_mask = None
        return mask

    def set_roi_mask(self, val):
        pass   # no-op; required so GPI doesn't complain on network reload

    def set_loaded_mask(self, val):
        pass   # no-op; storage lives in self._loaded_mask

    def get_loaded_mask(self):
        return self._loaded_mask

    def set_val(self, val):
        if isinstance(val, QtGui.QImage):
            super().set_val(val)
        elif isinstance(val, list):
            self.imageLabel._rois = list(val)
            self.imageLabel.update()

    def get_val(self):
        return list(self.imageLabel._rois) if self.imageLabel._rois else None

    def set_rawdata_left(self, data):
        self._rawdata_left = data

    def get_rawdata_left(self):
        return None

    def set_rawdata_right(self, data):
        self._rawdata_right = data

    def get_rawdata_right(self):
        return None

    def set_rawphys_left(self, data):
        self._rawphys_left = data

    def get_rawphys_left(self):
        return None

    def set_rawphys_right(self, data):
        self._rawphys_right = data

    def get_rawphys_right(self):
        return None

    def set_stats_text(self, text):
        if text:
            self._stats_lbl.setText(text)
            self._stats_lbl.show()
        else:
            self._stats_lbl.setText('')
            self._stats_lbl.hide()

    def get_stats_text(self):
        return self._stats_lbl.text()

    def isPolygon(self):
        return self.ann_type == 'Polygon'

    def annotationButton(self, value):
        super().annotationButton(value)
        lbl = self.imageLabel
        if hasattr(lbl, '_poly_pts') and lbl._poly_pts:
            lbl._poly_pts    = []
            lbl._poly_cursor = None
            lbl.update()

    def _toggle_edit_roi(self, idx):
        lbl = self.imageLabel
        lbl._edit_roi_idx = None if lbl._edit_roi_idx == idx else idx
        lbl._drag_pt_key  = None
        lbl._hover_pt_key = None
        lbl.unsetCursor()
        lbl.update()

    def set_ext_labels(self, labels):
        self.imageLabel._ext_labels = list(labels) if labels else []
        self.imageLabel.update()

    def get_ext_labels(self):
        return None

    def set_mirror_offset(self, val):
        self._mirror_offset = val
        self.imageLabel.update()

    def get_mirror_offset(self):
        return self._mirror_offset


# ---------------------------------------------------------------------------
# WindowLevel widget (from ImageDisplay_GPI.py; node files don't cross-import)
# ---------------------------------------------------------------------------

class WindowLevel(gpi.GenericWidgetGroup):
    """Provides an interface to the BasicCWFCSliders."""
    valueChanged = gpi.Signal()

    def __init__(self, title, parent=None):
        super().__init__(title, parent)
        self.sl = gpi.BasicCWFCSliders()
        self.sl.valueChanged.connect(self.valueChanged)
        self.pb = gpi.BasicPushButton()
        self.pb.set_button_title('reset')
        wdgLayout = QtWidgets.QVBoxLayout()
        wdgLayout.addWidget(self.sl)
        wdgLayout.addWidget(self.pb)
        self.setLayout(wdgLayout)
        self.set_min(0)
        self.set_max(100)
        self.sl.set_allvisible(True)
        self.reset_sliders()
        self.pb.valueChanged.connect(self.reset_sliders)

    def set_val(self, val):
        self.sl.set_center(val['level'])
        self.sl.set_width(val['window'])
        self.sl.set_floor(val['floor'])
        self.sl.set_ceiling(val['ceiling'])

    def set_min(self, val):
        self.sl.set_min(val)

    def set_max(self, val):
        self.sl.set_max(val)

    def get_val(self):
        return {
            'level':   self.sl.get_center(),
            'window':  self.sl.get_width(),
            'floor':   self.sl.get_floor(),
            'ceiling': self.sl.get_ceiling(),
        }

    def get_min(self):
        return self.sl.get_min()

    def get_max(self):
        return self.sl.get_max()

    def reset_sliders(self):
        self.set_val({'window': 100, 'level': 50, 'floor': 0, 'ceiling': 100})


class ComparisonToolbar(gpi.GenericWidgetGroup):
    """Compact controls for the comparison currently shown in the viewport."""

    valueChanged = gpi.Signal()
    _MODES = ['Toggle', 'Fade', 'Horizontal split', 'Vertical split',
              'Color channels', 'Side-by-side']

    def __init__(self, title, parent=None):
        super().__init__(title, parent)
        self._mode = QtWidgets.QComboBox()
        self._mode.addItems(self._MODES)
        self._swap = QtWidgets.QToolButton()
        self._swap.setCheckable(True)
        self._swap.setText('Swap')
        self._swap.setToolTip('Reverse the left and right inputs')
        self._edge_label = QtWidgets.QLabel('Boundary')
        self._edge = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self._edge.setRange(0, 100)
        self._edge.setValue(0)
        self._edge.setToolTip('Adjust the fade, split, or color-channel boundary')

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(6, 2, 6, 2)
        layout.addWidget(QtWidgets.QLabel('View'))
        layout.addWidget(self._mode)
        layout.addWidget(self._swap)
        layout.addWidget(self._edge_label)
        layout.addWidget(self._edge, 1)
        self.setLayout(layout)

        self._mode.currentIndexChanged.connect(self.somethingChanged)
        self._swap.toggled.connect(self.somethingChanged)
        self._edge.valueChanged.connect(self.somethingChanged)
        self.set_edge_visible(False)

    def set_val(self, val):
        if not isinstance(val, dict):
            return
        self._mode.setCurrentIndex(int(val.get('transition', self._mode.currentIndex())))
        self._swap.setChecked(bool(val.get('swap', self._swap.isChecked())))
        self._edge.setValue(int(val.get('edge', self._edge.value())))

    def get_val(self):
        return {
            'transition': self._mode.currentIndex(),
            'swap': self._swap.isChecked(),
            'edge': self._edge.value(),
        }

    def somethingChanged(self):
        self.valueChanged.emit()

    def set_edge_visible(self, visible):
        self._edge_label.setVisible(visible)
        self._edge.setVisible(visible)

    def set_edge_max(self, value):
        self._edge.setMaximum(max(0, int(value)))

    def set_swap_label(self, text):
        self._swap.setText(str(text))


class ExternalNode(gpi.NodeAPI):
    """Fused image display + compare: render two raw 2D/3D real-or-complex
    numpy arrays (same rendering pipeline as ImageDisplay) and compare them
    directly (same Transition/ROI toolset as ImageCompare) — no upstream
    ImageDisplay nodes required.

    INPUTS:
    inleft/inright - 2D or 3D data, real or complex (need not match dtype,
                     but must match spatial size after slice/tile)
    mask - (optional) boolean/uint8 ROI mask, sized to the rendered images

    OUTPUTS:
    out      - 3D uint8 RGBA composite of the current comparison view
    outleft  - 3D uint8 RGBA rendering of inleft alone
    outright - 3D uint8 RGBA rendering of inright alone
    roi      - 2D uint8 mask (h x w); sent only on right-click "Send to
               output port"

    WIDGETS:
    Complex Display / Color Map / Edge Pixels / Black Pixels / Slice /
    Slice/Tile Dimension / Extra Dimension / # Columns / # Rows / L W F C /
    Scalar Display / Gamma / Zero Ref / Fix Range / Range Min / Range Max:
        same rendering controls as ImageDisplay, applied IDENTICALLY to
        both inputs (shared colormap/window/level for a fair comparison);
        when Fix Range is off, the auto-range is computed over BOTH images
        combined.
    Transition / LeftRight / edge: same comparison controls as ImageCompare.
    Viewport ROI tools: draw ROIs that propagate to both images, reporting
        physical-value (not RGBA) stats for L/R plus their difference.
    """

    def execType(self):
        # Pure numpy + QImage construction, GPI_THREAD-safe (see the
        # execType audit note in /memories/repo/gpi_widget_conventions.md).
        return gpi.GPI_THREAD

    def initUI(self):
        # Compare first: these are the controls used most often while looking
        # at the viewport. Rendering options stay available below it.
        self.addWidget('ComparisonToolbar', 'Comparison')
        self.addWidget('CompareViewBox', 'Viewport:')

        # Rendering widgets (shared by both inputs)
        self.addWidget('TextBox', 'I/O Info:', visible=False)
        self.real_cmaps    = ['Gray', 'IceFire', 'Fire', 'Hot', 'HOT2', 'BGR']
        self.complex_cmaps = ['HSV', 'HSL', 'HUSL', 'CoolWarm']
        self.addWidget('ExclusivePushButtons', 'Complex Display',
                       buttons=['R', 'I', 'M', 'P', 'C'], val=4)
        self.addWidget('ExclusivePushButtons', 'Color Map',
                       buttons=self.real_cmaps, val=0, collapsed=True)
        self.addWidget('SpinBox', 'Edge Pixels', min=0)
        self.addWidget('SpinBox', 'Black Pixels', min=0)
        self.addWidget('Slider', 'Slice', min=1, val=1)
        self.addWidget('ExclusivePushButtons', 'Slice/Tile Dimension',
                       buttons=['0', '1', '2'], val=0)
        self.addWidget('ExclusivePushButtons', 'Extra Dimension',
                       buttons=['Slice', 'Tile', 'RGB(A)'], val=0)
        self.addWidget('SpinBox', '# Columns', val=1)
        self.addWidget('SpinBox', '# Rows', val=1)
        self.addWidget('WindowLevel', 'L W F C:', collapsed=True)
        self.addWidget('ExclusivePushButtons', 'Scalar Display',
                       buttons=['Pass', 'Mag', 'Sign'], val=0)
        self.addWidget('DoubleSpinBox', 'Gamma',
                       min=0.1, max=10, val=1, singlestep=0.05, decimals=3)
        self.addWidget('ExclusivePushButtons', 'Zero Ref',
                       buttons=['---', '0->', '-0-', '<-0'], val=0)
        self.addWidget('PushButton', 'Fix Range',
                       button_title='Auto-Range On', toggle=True)
        self.addWidget('DoubleSpinBox', 'Range Min')
        self.addWidget('DoubleSpinBox', 'Range Max')

        # IO Ports
        self.addInPort('inleft',  'NPYorTorch', kind='numpy', drange=(2, 3))
        self.addInPort('inright', 'NPYorTorch', kind='numpy', drange=(2, 3))
        self.addInPort('mask', 'NPYarray', obligation=gpi.OPTIONAL,
                       dtype=[np.bool_, np.uint8])
        self.addOutPort('out',      'NPYarray')
        self.addOutPort('outleft',  'NPYarray')
        self.addOutPort('outright', 'NPYarray')
        self.addOutPort('roi',      'NPYarray')

        # Cache: (data_ptr, shape, dtype, lo, hi) — avoids re-scanning the
        # full 3D volume on every slice change.
        self._in_range_cache_l = None
        self._in_range_cache_r = None

    def validate(self):

        inleft  = self.getData('inleft')
        inright = self.getData('inright')
        dimfunc = self.getVal('Extra Dimension')

        if inleft.ndim == 3:
            dimval = self.getVal('Slice/Tile Dimension')
            self.setAttr('Extra Dimension', visible=True)
            if inleft.shape[-1] not in [3, 4]:
                if dimfunc > 1:
                    dimfunc = 0
                self.setAttr('Extra Dimension', buttons=['Slice', 'Tile'], val=dimfunc)
            else:
                if inleft.dtype == 'uint8':
                    dimfunc = 2
                self.setAttr('Extra Dimension',
                             buttons=['Slice', 'Tile', 'RGB(A)'], val=dimfunc)

            if dimfunc == 0:
                slval = self.getVal('Slice')
                self.setAttr('Slice/Tile Dimension', visible=True)
                if slval > inleft.shape[dimval]:
                    slval = inleft.shape[dimval]
                self.setAttr('Slice', visible=True, min=1,
                             max=inleft.shape[dimval], val=slval)
                self.setAttr('# Rows',    visible=False)
                self.setAttr('# Columns', visible=False)
            elif dimfunc == 1:
                self.setAttr('Slice/Tile Dimension', visible=True)
                ncol = self.getVal('# Columns')
                nrow = self.getVal('# Rows')
                N    = inleft.shape[dimval]

                if (ncol == 1 and nrow == 1
                        or 'Slice/Tile Dimension' in self.widgetEvents()):
                    ncol = int(np.round(np.sqrt(N)))
                if nrow * ncol < N:
                    nrow = int(np.ceil(N / ncol))
                while nrow * ncol - N >= ncol:
                    nrow -= 1

                self.setAttr('# Columns', visible=True, val=ncol)
                self.setAttr('# Rows',    visible=True, val=nrow)
                self.setAttr('Slice',     visible=False)
            else:
                self.setAttr('Slice/Tile Dimension', visible=False)
                self.setAttr('Slice',     visible=False)
                self.setAttr('# Rows',    visible=False)
                self.setAttr('# Columns', visible=False)

        else:
            if dimfunc > 1:
                dimfunc = 0
                self.setAttr('Extra Dimension', buttons=['Slice', 'Tile'],
                             val=dimfunc)
            self.setAttr('Extra Dimension',      visible=False)
            self.setAttr('Slice/Tile Dimension', visible=False)
            self.setAttr('Slice',     visible=False)
            self.setAttr('# Rows',    visible=False)
            self.setAttr('# Columns', visible=False)

        self.setAttr('L W F C:', visible=(dimfunc != 2))
        self.setAttr('Gamma',    visible=(dimfunc != 2))
        self.setAttr('Fix Range', visible=(dimfunc != 2))

        if dimfunc == 2:
            self.setAttr('Complex Display', visible=False)
            self.setAttr('Color Map',       visible=False)
            self.setAttr('Scalar Display',  visible=False)
            self.setAttr('Edge Pixels',     visible=False)
            self.setAttr('Black Pixels',    visible=False)
            self.setAttr('Zero Ref',        visible=False)
            self.setAttr('Range Min',       visible=False)
            self.setAttr('Range Max',       visible=False)

        else:
            is_complex = np.iscomplexobj(inleft) or np.iscomplexobj(inright)
            self.setAttr('Complex Display', visible=is_complex)
            scalarvis = (not is_complex) or self.getVal('Complex Display') != 4

            if scalarvis:
                self.setAttr('Color Map', buttons=self.real_cmaps,
                             collapsed=self.getAttr('Color Map', 'collapsed'))
            else:
                self.setAttr('Color Map', buttons=self.complex_cmaps,
                             collapsed=self.getAttr('Color Map', 'collapsed'))

            self.setAttr('Scalar Display', visible=scalarvis)
            self.setAttr('Edge Pixels',    visible=not scalarvis)
            self.setAttr('Black Pixels',   visible=not scalarvis)

            if self.getVal('Scalar Display') == 2:
                self.setAttr('Zero Ref', visible=False)
            else:
                self.setAttr('Zero Ref', visible=scalarvis)

            self.setAttr('Range Min', visible=scalarvis)
            self.setAttr('Range Max', visible=scalarvis)

            zval = self.getVal('Zero Ref')
            if zval == 1:
                self.setAttr('Range Min', val=0)
            elif zval == 3:
                self.setAttr('Range Max', val=0)

            if self.getVal('Fix Range'):
                self.setAttr('Fix Range', button_title='Fixed Range On')
            else:
                self.setAttr('Fix Range', button_title='Auto-Range On')

        # ---- ImageCompare-style Transition/edge/LeftRight controls.
        # Edge slider bounds are approximated from inleft's raw spatial
        # dims (pre slice/tile); good enough for the common 2D case, and
        # merely governs UI slider range in the 3D case. ----
        if self.getLayoutDirection() == 'Horizontal':
            port_l, port_r = "Top Port", "Bottom Port"
        else:
            port_l, port_r = "Left Port", "Right Port"

        h0, w0 = inleft.shape[0], inleft.shape[1]
        comparison = self.getVal('Comparison')
        trans = comparison['transition']
        swapped = comparison['swap']
        if trans == 0:  # Toggle
            self.setAttr('Comparison', edge_visible=False,
                         swap_label=(port_r if swapped else port_l))
        elif trans == 1:  # Fade
            self.setAttr('Comparison', edge_visible=True, edge_max=100,
                         swap_label=(port_r if swapped else port_l) + " at edge=0")
        elif trans == 2:  # Horizontal split
            self.setAttr('Comparison', edge_visible=True, edge_max=h0,
                         swap_label=(port_r if swapped else port_l) + " on top")
        elif trans == 3:  # Vertical split
            self.setAttr('Comparison', edge_visible=True, edge_max=w0,
                         swap_label=(port_r if swapped else port_l) + " on left")
        elif trans == 4:  # Color
            self.setAttr('Comparison', edge_visible=True, edge_max=5,
                         swap_label=(port_l if swapped else port_r) + " RYGCBM")
        elif trans == 5:  # Side-by-side
            self.setAttr('Comparison', edge_visible=False,
                         swap_label=(port_r + " then " + port_l if swapped
                                     else port_l + " then " + port_r))

        return 0

    def compute(self):

        def _safe_range(arr):
            mn = float(np.nanmin(arr))
            mx = float(np.nanmax(arr))
            if not np.isfinite(mn):
                mn = 0.0
            if not np.isfinite(mx):
                mx = 1.0
            if mn == mx:
                mx = mn + 1.0
            return mn, mx

        # ---- shared rendering parameters ----
        dimfunc = self.getVal('Extra Dimension')
        dimval  = self.getVal('Slice/Tile Dimension')
        gamma   = self.getVal('Gamma')
        lval    = self.getAttr('L W F C:', 'val')
        cval    = self.getVal('Complex Display')
        cmap    = self.getVal('Color Map')
        sval    = self.getVal('Scalar Display')
        zval    = self.getVal('Zero Ref')
        fval    = self.getVal('Fix Range')
        rmin    = self.getVal('Range Min')
        rmax    = self.getVal('Range Max')
        edgpix  = self.getVal('Edge Pixels')
        blkpix  = self.getVal('Black Pixels')

        flor = 0.01 * lval['floor']
        ceil = 0.01 * lval['ceiling']
        if ceil == flor:
            flor = 0.999 if ceil == 1. else flor
            ceil = ceil  if ceil == 1. else ceil + 0.001

        def _slice_tile(data):
            if data.ndim == 3 and dimfunc < 2:
                if dimfunc == 0:
                    slval = int(np.clip(self.getVal('Slice') - 1, 0, data.shape[dimval] - 1))
                    if dimval == 0:
                        d = data[slval, ...]
                    elif dimval == 1:
                        d = data[:, slval, :]
                    else:
                        d = data[..., slval]
                else:
                    ncol = int(self.getVal('# Columns'))
                    nrow = int(self.getVal('# Rows'))
                    d = np.rollaxis(data, dimval)
                    N, xres, yres = d.shape
                    N_new = ncol * nrow
                    d = np.pad(d, ((0, max(0, N_new - N)), (0, 0), (0, 0)),
                               mode='constant')
                    d = np.reshape(d, (nrow, ncol, xres, yres))
                    d = np.swapaxes(d, 1, 2)
                    d = np.reshape(d, (nrow * xres, ncol * yres))
                return d
            return data

        def _apply_cval_sval(d):
            if cval == 0:
                d = np.real(d)
            elif cval == 1:
                d = np.imag(d)
            elif cval == 2:
                d = np.abs(d)
            elif cval == 3:
                d = np.angle(d, deg=True)
            sign = None
            if sval == 1:
                d = np.abs(d)
            elif sval == 2:
                sign = np.sign(d)
                d = np.abs(d)
            return d, sign

        def _colorize_scalar(data, sign, data_min, data_max):
            data_range = data_max - data_min
            new_min = data_range * flor + data_min
            new_max = data_range * ceil  + data_min
            data = np.clip(data, new_min, new_max)
            if new_max > new_min:
                data = (data - new_min) / (new_max - new_min)
                if gamma != 1:
                    data = np.power(data, gamma)
                data = 255. * data
            else:
                data = 255. * np.ones(data.shape)

            if sval != 2:
                if cmap == 0:
                    luma  = np.uint8(data)
                    red = green = blue = luma
                    alpha = np.full(luma.shape, 255, dtype=np.uint8)
                else:
                    rd, gn, be = _scalar_cmap_rgb(cmap, data)
                    red, green, blue = np.uint8(255. * rd), np.uint8(255. * gn), np.uint8(255. * be)
                    alpha = np.full(red.shape, 255, dtype=np.uint8)
            else:
                rd = np.zeros(data.shape); gn = np.zeros(data.shape); be = np.zeros(data.shape)
                rd[sign <= 0] = data[sign <= 0]; be[sign <= 0] = data[sign <= 0]
                gn[sign >= 0] = data[sign >= 0]
                red, green, blue = rd.astype(np.uint8), gn.astype(np.uint8), be.astype(np.uint8)
                alpha = np.full(red.shape, 255, dtype=np.uint8)

            img = np.zeros(data.shape + (4,), dtype=np.uint8)
            img[..., 0], img[..., 1], img[..., 2], img[..., 3] = red, green, blue, alpha
            return img

        def _colorize_complex(mag, phase, data_min, data_max):
            data_range = data_max - data_min
            new_min = data_range * flor + data_min
            new_max = data_range * ceil  + data_min
            m = np.clip(mag, new_min, new_max)
            if new_max > new_min:
                m = (m - new_min) / (new_max - new_min)
                if gamma != 1:
                    m = np.power(m, gamma)
            else:
                m = np.ones(mag.shape)
            ph = phase
            if edgpix + blkpix > 0:
                h2 = m.shape[0] + 2 * (edgpix + blkpix)
                w2 = m.shape[1] + 2 * (edgpix + blkpix)
                m2  = np.zeros((h2, w2))
                ph2 = np.zeros((h2, w2))
                frame = np.zeros((h2, w2), dtype=bool)
                frame[0:edgpix, :]       = True
                frame[h2 - edgpix:h2, :] = True
                frame[:, 0:edgpix]       = True
                frame[:, w2 - edgpix:w2] = True
                pad = edgpix + blkpix
                oh, ow = m.shape
                m2[pad:pad + oh, pad:pad + ow]  = m
                m2[frame] = 1
                ph2[pad:pad + oh, pad:pad + ow] = ph
                xloc = np.tile(np.linspace(-1., 1., w2), (h2, 1))
                yloc = np.tile(np.linspace(1., -1., h2), (w2, 1)).T
                ph2[frame] = np.degrees(np.arctan2(yloc[frame], xloc[frame]))
                m, ph = m2, ph2
            phase_cmap = _phase_cmap(cmap)
            phase_norm = (ph + 180) / 360
            if cmap != 3:
                phase_norm = (phase_norm - 1 / 3) % 1
            colorized = (255 * cm.gray(m) * phase_cmap(phase_norm)).astype(np.uint8)
            return colorized

        def _rgba_passthrough(data):
            if data.shape[-1] >= 3:
                red   = data[:, :, 0].astype(np.uint8)
                green = data[:, :, 1].astype(np.uint8)
                blue  = data[:, :, 2].astype(np.uint8)
                alpha = (data[:, :, 3].astype(np.uint8) if data.shape[-1] == 4
                         else np.full(red.shape, 255, dtype=np.uint8))
                img = np.zeros(red.shape + (4,), dtype=np.uint8)
                img[..., 0], img[..., 1], img[..., 2], img[..., 3] = red, green, blue, alpha
                return img
            return None

        def _io_info(cache_attr, in_data, in_shape, in_dtype, side_label):
            try:
                _rkey = (in_data.ctypes.data, in_data.shape, in_data.dtype)
                cache = getattr(self, cache_attr)
                if cache is None or cache[:3] != _rkey:
                    if np.iscomplexobj(in_data):
                        lo, hi = _safe_range(np.abs(in_data))
                    else:
                        lo, hi = _safe_range(in_data)
                    setattr(self, cache_attr, (*_rkey, lo, hi))
                else:
                    lo, hi = cache[3], cache[4]
                range_label = (f'|mag| range: [{lo:.4g}, {hi:.4g}]'
                               if np.iscomplexobj(in_data)
                               else f'range: [{lo:.4g}, {hi:.4g}]')
            except Exception:
                range_label = 'range: n/a'
            return f'{side_label}  shape: {in_shape}   dtype: {in_dtype}   {range_label}'

        inleft_raw  = self.getData('inleft')
        inright_raw = self.getData('inright')

        raw_l = _slice_tile(inleft_raw)
        raw_r = _slice_tile(inright_raw)

        io_left  = _io_info('_in_range_cache_l', inleft_raw,  inleft_raw.shape,  inleft_raw.dtype,  'L:')
        io_right = _io_info('_in_range_cache_r', inright_raw, inright_raw.shape, inright_raw.dtype, 'R:')
        self.setAttr('I/O Info:', val=io_left + '\n' + io_right)

        pad = 0  # M x P Edge/Black framing padding, used to gate physical hover below

        # ---- RGB(A) PASSTHROUGH ----
        if dimfunc == 2:
            img_l = _rgba_passthrough(raw_l)
            img_r = _rgba_passthrough(raw_r)
            if img_l is None or img_r is None:
                self.log.warn('ImageCompareDisplay: incompatible RGB(A) input veclen')
                return 1

        # ---- COMPLEX (magnitude x phase colormap), combined range ----
        elif cval == 4:
            mag_l, phase_l = np.abs(raw_l), np.angle(raw_l, deg=True)
            mag_r, phase_r = np.abs(raw_r), np.angle(raw_r, deg=True)
            if fval:
                data_max = rmax
            else:
                data_max = max(_safe_range(mag_l)[1], _safe_range(mag_r)[1])
                self.setAttr('Range Max', val=data_max)
            data_min = 0.
            pad = edgpix + blkpix
            img_l = _colorize_complex(mag_l, phase_l, data_min, data_max)
            img_r = _colorize_complex(mag_r, phase_r, data_min, data_max)

        # ---- SCALAR DISPLAY, combined range ----
        else:
            dl, sign_l = _apply_cval_sval(raw_l)
            dr, sign_r = _apply_cval_sval(raw_r)

            if sval != 2:
                if fval:
                    data_min, data_max = rmin, rmax
                else:
                    mn_l, mx_l = _safe_range(dl)
                    mn_r, mx_r = _safe_range(dr)
                    data_min, data_max = min(mn_l, mn_r), max(mx_l, mx_r)
                if zval == 1:
                    data_min = 0.
                elif zval == 2:
                    data_max = max(abs(data_min), abs(data_max))
                    data_min = -data_max
                elif zval == 3:
                    data_max = 0.
                self.setAttr('Range Min', val=data_min)
                self.setAttr('Range Max', val=data_max)
            else:
                if fval:
                    data_min, data_max = rmin, rmax
                else:
                    mn_l, mx_l = _safe_range(dl)
                    mn_r, mx_r = _safe_range(dr)
                    data_min, data_max = min(mn_l, mn_r), max(mx_l, mx_r)
                data_max   = max(abs(data_min), abs(data_max))
                data_min   = 0.
                data_range = data_max
                self.setAttr('Range Min', val=-data_range)
                self.setAttr('Range Max', val=data_range)

            img_l = _colorize_scalar(dl, sign_l, data_min, data_max)
            img_r = _colorize_scalar(dr, sign_r, data_min, data_max)

        if img_l.shape[:2] != img_r.shape[:2]:
            self.log.warn(f'ImageCompareDisplay: rendered sizes differ — '
                          f'L={img_l.shape[:2]}, R={img_r.shape[:2]}')
            return 1

        self.setData('outleft',  img_l)
        self.setData('outright', img_r)

        # ---- ImageCompare-style comparison (Transition / mask / ROI / stats) ----
        comparison = self.getVal('Comparison')
        transition = comparison['transition']
        edgeval = comparison['edge']

        if comparison['swap']:
            outright = np.array(img_l, copy=True)
            outleft  = np.array(img_r, copy=True)
            phys_left, phys_right = raw_r, raw_l
        else:
            outleft  = np.array(img_l, copy=True)
            outright = np.array(img_r, copy=True)
            phys_left, phys_right = raw_l, raw_r

        h0, w0 = outleft.shape[:2]
        side_by_side = (transition == 5)

        ext_mask = self.getData('mask')
        if ext_mask is None:
            ext_mask = self.getAttr('Viewport:', 'loaded_mask')
        ext_entries         = []
        ext_label_positions = []
        mask_warn           = ''

        if ext_mask is not None:
            if ext_mask.ndim != 2:
                mask_warn = f'mask: wrong shape {ext_mask.shape} (expected 2D)'
            elif ext_mask.shape != (h0, w0):
                mask_warn = (f'mask: size mismatch — mask={ext_mask.shape}, '
                             f'image=({h0}, {w0})')
            else:
                labels = np.unique(ext_mask)
                labels = labels[labels != 0]
                if len(labels) == 0:
                    mask_warn = 'mask: all zeros'
                else:
                    blend = 0.35
                    for lbl in labels:
                        m     = (ext_mask == lbl)
                        lbl_i = int(lbl) - 1
                        r_ov, g_ov, b_ov = _ROI_PALETTE_RGB[lbl_i % len(_ROI_PALETTE_RGB)]
                        for side_img in (outleft, outright):
                            for ch, ov in ((0, r_ov), (1, g_ov), (2, b_ov)):
                                side_img[:, :, ch] = np.where(
                                    m,
                                    np.clip(side_img[:, :, ch].astype(float)
                                            * (1.0 - blend) + ov * blend, 0, 255),
                                    side_img[:, :, ch]).astype(np.uint8)
                        ext_entries.append((f'ROI {int(lbl)}', m))
                        ys, xs = np.where(m)
                        if len(xs):
                            ext_label_positions.append(
                                (int(lbl), float(xs.min()), float(ys.min())))
                if mask_warn:
                    self.log.warn(mask_warn)

        if transition == 0:  # Toggle
            out = outleft
        elif transition == 1:  # Fade
            cr = 0.01 * float(edgeval)
            cl = 1. - cr
            out = cl * outleft.astype(float) + cr * outright.astype(float)
        elif transition == 2:  # Horizontal (top/bottom split)
            out = np.append(outleft[:edgeval, :, :], outright[edgeval:, :, :], axis=0)
        elif transition == 3:  # Vertical (left/right split)
            out = np.append(outleft[:, :edgeval, :], outright[:, edgeval:, :], axis=1)
        elif transition == 4:  # Color
            out = np.copy(outleft)
            if edgeval <= 1 or edgeval == 5:
                out[:, :, 2] = outright[:, :, 2]  # Red
            if edgeval >= 1 and edgeval <= 3:
                out[:, :, 1] = outright[:, :, 1]  # Green
            if edgeval >= 3:
                out[:, :, 0] = outright[:, :, 0]  # Blue
        elif transition == 5:  # Side-by-side
            out = np.concatenate((outleft, outright), axis=1)

        image1 = out.astype(np.uint8)

        h, w = out.shape[:2]
        format_ = QtGui.QImage.Format_RGB32
        image1 = np.ascontiguousarray(image1)
        image = QtGui.QImage(image1.data, w, h, w * 4, format_).copy()
        if image.isNull():
            self.log.warn("ImageCompareDisplay: cannot load image")

        left_u8  = np.ascontiguousarray(img_l.astype(np.uint8))
        right_u8 = np.ascontiguousarray(img_r.astype(np.uint8))
        gh, gw = left_u8.shape[:2]
        gif_left  = QtGui.QImage(left_u8.data, gw, gh, gw * 4, format_).copy()
        gif_right = QtGui.QImage(right_u8.data, gw, gh, gw * 4, format_).copy()
        self.getWidget('Viewport:').set_gif_frames([gif_left, gif_right])

        outleft_u8  = np.ascontiguousarray(outleft.astype(np.uint8))
        outright_u8 = np.ascontiguousarray(outright.astype(np.uint8))
        self.setAttr('Viewport:', rawdata_left=outleft_u8)
        self.setAttr('Viewport:', rawdata_right=outright_u8)
        # Physical hover only when no M x P framing padding is active, so
        # pixel coordinates line up exactly with the (unpadded) raw arrays.
        self.setAttr('Viewport:', rawphys_left=(phys_left if pad == 0 else None))
        self.setAttr('Viewport:', rawphys_right=(phys_right if pad == 0 else None))
        self.setAttr('Viewport:', ext_labels=ext_label_positions)
        self.setAttr('Viewport:', mirror_offset=(w0 if side_by_side and w == 2 * w0 else None))

        roi_coords  = self.getAttr('Viewport:', 'val')
        ann_entries = []
        if roi_coords and isinstance(roi_coords, list):
            for i, coord in enumerate(roi_coords):
                lbl = f'ROI {i + 1} ({coord.get("type", "?")})'
                if side_by_side and w == 2 * w0:
                    xs = _roi_x_extent(coord)
                    if xs is None:
                        continue
                    min_x, max_x = xs
                    if max_x < w0:
                        canon = coord
                    elif min_x >= w0:
                        canon = _shift_roi_x(coord, -w0)
                    else:
                        m = _roi_coords_to_mask(coord, h, w)
                        if m.any():
                            ann_entries.append((lbl, m[:, :w0], m[:, w0:], False))
                        continue
                    m = _roi_coords_to_mask(canon, h0, w0)
                    if m.any():
                        ann_entries.append((lbl, m, m, True))
                else:
                    m = _roi_coords_to_mask(coord, h, w)
                    if m.any():
                        ann_entries.append((lbl, m, m, True))

        stats_lines = []
        if ext_entries:
            for lbl, m in ext_entries:
                stats_lines.append(
                    _format_compare_stats(phys_left, phys_right, m, m, lbl, paired=True))
        else:
            for lbl, ml, mr, paired in ann_entries:
                stats_lines.append(
                    _format_compare_stats(phys_left, phys_right, ml, mr, lbl, paired))
        self.setAttr('Viewport:', stats_text='\n'.join(s for s in stats_lines if s))

        self.setAttr('Viewport:', val=image)

        pending_mask = self.getAttr('Viewport:', 'roi_mask')
        if pending_mask is not None:
            self.setData('roi', pending_mask.astype(np.uint8))
        else:
            self.setData('roi', None)

        self.setData('out', image1)

        return 0
