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


# Author: Jim Pipe
# Date: 2013 Oct

import gpi
from gpi import QtCore, QtGui, QtWidgets
from gpi.widgets import DisplayBox as _DisplayBox, GPILabel as _GPILabel
import numpy as np

# ---------------------------------------------------------------------------
# ROI helpers — shared shape-to-mask logic (see ImageDisplay_GPI.py for the
# original single-image version this is adapted from)
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


def _format_compare_roi_stats(left_rgba, right_rgba, mask_left, mask_right,
                              label='ROI', paired=True):
    """Compare stats for the same annotation across the left/right images.

    mask_left/mask_right are boolean (H, W) masks into left_rgba/right_rgba
    respectively.  paired=True means the two masks reference the SAME pixel
    positions (true whenever the drawn ROI was cleanly propagated to both
    sides — see compute()'s Side-by-side handling for the one case where it
    can't be, a ROI straddling the midline) — only then is a pixel-wise RMSE
    meaningful.
    """
    def _lum(rgba, mask):
        if mask is None or not mask.any():
            return None
        lum = (0.2126 * rgba[..., 0].astype(float)
               + 0.7152 * rgba[..., 1].astype(float)
               + 0.0722 * rgba[..., 2].astype(float))
        vals = lum[mask]
        return vals if len(vals) else None

    vl = _lum(left_rgba, mask_left)
    vr = _lum(right_rgba, mask_right)
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


_ROI_PALETTE = [
    QtCore.Qt.green, QtCore.Qt.yellow, QtCore.Qt.cyan,
    QtCore.Qt.magenta, QtCore.Qt.white, QtCore.Qt.red,
]

_ROI_PALETTE_RGB = [
    (  0, 255,   0), (255, 255,   0), (  0, 255, 255),
    (255,   0, 255), (255, 255, 255), (255,   0,   0),
]


class _LockedLabel(_GPILabel):
    """GPILabel replacement supporting multiple simultaneous ROIs, used to
    mark a region for LEFT-vs-RIGHT comparison (rather than single-image
    inspection).  Same interaction model as ImageDisplay's ROI tool, minus
    the 3D slice-propagation feature which has no meaning here (ImageCompare
    only ever shows one already-composited 2D frame per side)."""

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
        # Side-by-side mode: a ROI drawn in one half automatically applies to
        # the SAME region in the other image (see compute()) — mirror its
        # outline (dashed) into the other half so that propagation is visible,
        # not just reflected in the stats text.
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
    SAME region across the left/right input images: pixel hover shows both
    sides' values, and each drawn ROI reports mean/std/min/max for both
    sides plus their difference — the ROI toolset itself is the same one
    used in ImageDisplay, but the stats it produces are inherently
    comparative rather than single-image, matching this node's purpose."""

    def __init__(self, title, parent=None):
        super().__init__(title, parent)
        self._rawdata_left     = None
        self._rawdata_right    = None
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
        dl, dr = self._rawdata_left, self._rawdata_right
        if dl is None or dr is None:
            self._hover_lbl.setText(f'[{r}, {c}]')
            return
        h, w0 = dl.shape[:2]
        # modulo the column so hover works identically whether the composite
        # is single-width or the double-width Side-by-side transition
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


class ExternalNode(gpi.NodeAPI):
    """2D image Compare Module

    INPUTS (must be the same size):
    inleft/inright - 3D uint8 ARGB data (e.g. from ImageDisplay)
    mask - (optional) boolean/uint8 ROI mask, sized to inleft/inright, e.g.
           the 'roi' output of an ImageDisplay node upstream of one of the
           two images. Lets a region picked on one recon/pipeline be reused
           to directly compare both images in that same region.

    OUTPUTS:
    out - 3D data of displayed image, last dimension has length 4 for ARGB byte (uint8) data
    roi - 2D uint8 mask (h x w); 1 inside a drawn ROI, 0 outside. Only sent
          when the user right-clicks a ROI and chooses 'Send to output port'.

    WIDGETS:
    Transition: chooses how to transition between images of left and right ports
    LeftRight: Toggles between left or right images
    edge: slider to demarcate the line, or fading, between two images
    Viewport 'Export GIF': saves an animated GIF that alternates between the
        raw inleft/inright images; 'GIF toggle (sec)' sets the per-frame duration
    Viewport ROI tools (Pointer/Line/Rectangle/Ellipse/Polygon): draw one or
        more regions directly on the comparison viewport. A drawn ROI
        automatically PROPAGATES to both images — that's the point of this
        node — reporting mean/std/min/max for L and R simultaneously (plus
        their difference) in the same stats line, rather than one image at a
        time like ImageDisplay. Hovering the mouse also shows both sides'
        pixel values together. In the Side-by-side transition, a ROI drawn
        within one half is automatically mirrored onto the other half (shown
        as a dashed outline) so the same region is still compared on both
        sides; only a ROI straddling the midline falls back to two
        independent (unpaired) regions.
    """

    def execType(self):
        # GPI_THREAD: compute() only does numpy array ops + builds a QImage
        # (safe off the GUI thread) and updates the Viewport via self.setAttr(),
        # which the framework already marshals to the main thread for
        # GPI_THREAD nodes. GPI_APPLOOP ran this synchronously on the UI
        # thread, freezing the whole app while it composited each frame.
        return gpi.GPI_THREAD

    def initUI(self):

        # Widgets
        self.addWidget('CompareViewBox', 'Viewport:')
        self.addWidget('ExclusivePushButtons','Transition',
                    buttons=['Toggle','Fade','Hor','Vert','Color',
                          'Side-by-side'], val=0)
        self.addWidget('PushButton', 'LeftRight', button_title='Left Port', toggle=True)
        self.addWidget('Slider', 'edge',val=0)

        # IO Ports
        self.addInPort('inleft', 'NPYarray', ndim=3, obligation=gpi.REQUIRED)
        self.addInPort('inright', 'NPYarray', ndim=3, obligation=gpi.REQUIRED)
        self.addInPort('mask', 'NPYarray', obligation=gpi.OPTIONAL,
                       dtype=[np.bool_, np.uint8])
        self.addOutPort('out', 'NPYarray')
        self.addOutPort('roi', 'NPYarray')

    def validate(self):

        # Complex or Scalar?
        inleft = self.getData('inleft')
        inright = self.getData('inright')

        if (inleft.shape[-1] != 4):
            self.log.warn("left port data must have a last dimension of 4")
            return 1
        if (inright.shape[-1] != 4):
            self.log.warn("right port data must have a last dimension of 4")
            return 1
        if (inleft.shape != inright.shape):
            self.log.warn("data must be the same size")
            return 1

        # inleft/inright are stacked top/bottom on the node when the canvas
        # flows left-to-right, and side-by-side left/right when it flows
        # top-to-bottom -- name them to match how they actually appear.
        if self.getLayoutDirection() == 'Horizontal':
          port_l, port_r = "Top Port", "Bottom Port"
        else:
          port_l, port_r = "Left Port", "Right Port"

        if self.getVal('Transition') == 0: # Toggle
          self.setAttr('edge',visible=False)
          if self.getVal('LeftRight'):
            self.setAttr('LeftRight',button_title=port_r)
          else:
            self.setAttr('LeftRight',button_title=port_l)
        elif self.getVal('Transition') == 1: # Fade
          self.setAttr('edge',visible=True,max=100)
          if self.getVal('LeftRight'):
            self.setAttr('LeftRight',button_title=port_r+" at edge=0")
          else:
            self.setAttr('LeftRight',button_title=port_l+" at edge=0")
        elif self.getVal('Transition') == 2: # Horizontal (top/bottom split)
          self.setAttr('edge',visible=True,max=inleft.shape[0])
          if self.getVal('LeftRight'):
            self.setAttr('LeftRight',button_title=port_r+" on top")
          else:
            self.setAttr('LeftRight',button_title=port_l+" on top")
        elif self.getVal('Transition') == 3: # Vertical (left/right split)
          self.setAttr('edge',visible=True,max=inleft.shape[1])
          if self.getVal('LeftRight'):
            self.setAttr('LeftRight',button_title=port_r+" on left")
          else:
            self.setAttr('LeftRight',button_title=port_l+" on left")
        elif self.getVal('Transition') == 4: # Color
          self.setAttr('edge',visible=True,max=5)
          if self.getVal('LeftRight'):
            self.setAttr('LeftRight',button_title=port_l+" RYGCBM")
          else:
            self.setAttr('LeftRight',button_title=port_r+" RYGCBM")
        elif self.getVal('Transition') == 5: # Side-by-side
          self.setAttr('edge',visible=False)
          if self.getVal('LeftRight'):
            self.setAttr('LeftRight',button_title=port_r+" then "+port_l)
          else:
            self.setAttr('LeftRight',button_title=port_l+" then "+port_r)

        return 0

    def compute(self):

        edgeval = self.getVal('edge')

        # make a copy for changes — also needed since the external ROI mask
        # overlay below writes into outleft/outright in place
        if self.getVal('LeftRight'):
          outright = np.array(self.getData('inleft'), copy=True)
          outleft  = np.array(self.getData('inright'), copy=True)
        else:
          outleft  = np.array(self.getData('inleft'), copy=True)
          outright = np.array(self.getData('inright'), copy=True)

        h0, w0 = outleft.shape[:2]
        side_by_side = (self.getVal('Transition') == 5)

        # ---- External ROI mask (in 'mask' port, or loaded via the Viewport's
        # right-click menu): bake a colored overlay into BOTH sides before
        # compositing, so it shows under any Transition and drives the
        # comparison stats below. Reusing a ROI drawn on a single upstream
        # ImageDisplay node lets the exact same region be compared here. ----
        ext_mask = self.getData('mask')
        if ext_mask is None:
            ext_mask = self.getAttr('Viewport:', 'loaded_mask')
        ext_entries         = []   # [(label, bool_mask), ...] one per external label
        ext_label_positions = []   # [(lbl_num, x, y), ...] top-left bbox, data coords
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

        if self.getVal('Transition') == 0: # Toggle
          out = outleft
        elif self.getVal('Transition') == 1: # Fade
          cr = 0.01*float(self.getVal('edge'))
          cl = 1.-cr
          out = cl*outleft.astype(float) + cr*outright.astype(float)
        elif self.getVal('Transition') == 2: # Horizontal (top/bottom split)
          out = np.append(outleft[:edgeval,:,:],outright[edgeval:,:,:],axis=0)
        elif self.getVal('Transition') == 3: # Vertical (left/right split)
          out = np.append(outleft[:,:edgeval,:],outright[:,edgeval:,:],axis=1)
        elif self.getVal('Transition') == 4: # Color
          out = np.copy(outleft)
          if self.getVal('edge') <= 1 or self.getVal('edge') == 5:
            out[:,:,2] = outright[:,:,2] # Red
          if self.getVal('edge') >= 1 and self.getVal('edge') <= 3:
            out[:,:,1] = outright[:,:,1] # Green
          if self.getVal('edge') >= 3:
            out[:,:,0] = outright[:,:,0] # Blue
        elif self.getVal('Transition') == 5: # Side-by-side
          out = np.concatenate((outleft, outright), axis=1)


        image1 = out.astype(np.uint8)

        h, w = out.shape[:2]
        format_ = QtGui.QImage.Format_RGB32

        # .copy() makes Qt own its own buffer; without it the QImage keeps a
        # raw pointer into image1's memory, which can be freed/reused once
        # this function returns, causing an intermittent crash.
        image1 = np.ascontiguousarray(image1)
        image = QtGui.QImage(image1.data, w, h, w * 4, format_).copy()
        if image.isNull():
            self.log.warn("Image Viewer: cannot load image")

        # feed the raw (un-swapped) left/right port images to the Viewport's
        # "Export GIF" button so it can alternate between the two inputs
        # regardless of the LeftRight/Transition display settings above
        left_u8  = np.ascontiguousarray(self.getData('inleft').astype(np.uint8))
        right_u8 = np.ascontiguousarray(self.getData('inright').astype(np.uint8))
        gh, gw = left_u8.shape[:2]   # not w/h above: 'Side-by-side' doubles those
        gif_left  = QtGui.QImage(left_u8.data, gw, gh, gw * 4, format_).copy()
        gif_right = QtGui.QImage(right_u8.data, gw, gh, gw * 4, format_).copy()
        self.getWidget('Viewport:').set_gif_frames([gif_left, gif_right])

        # ROI-comparison rawdata: the (possibly overlaid) L/R images actually
        # shown in the viewport, respecting the LeftRight toggle — so a hover
        # readout of "L"/"R" matches what the user currently sees as left/right.
        outleft_u8  = np.ascontiguousarray(outleft.astype(np.uint8))
        outright_u8 = np.ascontiguousarray(outright.astype(np.uint8))
        self.setAttr('Viewport:', rawdata_left=outleft_u8)
        self.setAttr('Viewport:', rawdata_right=outright_u8)
        self.setAttr('Viewport:', ext_labels=ext_label_positions)
        self.setAttr('Viewport:', mirror_offset=(w0 if side_by_side and w == 2 * w0 else None))

        # ---- ROI: user-drawn annotations automatically PROPAGATE to both
        # images — a ROI drawn anywhere is applied at the same region on
        # BOTH sides, that's the whole point of this node. In every
        # Transition except Side-by-side the two sides already share one
        # coordinate space (h, w0), so the mask applies as-is to both. In
        # Side-by-side (double-width canvas) a ROI drawn entirely within one
        # half is canonicalized back into (h0, w0) space (and mirrored onto
        # the widget's other half — see _LockedLabel.paintEvent) so it still
        # applies identically to both; only a ROI straddling the midline
        # falls back to two independent (unpaired) regions. ----
        roi_coords  = self.getAttr('Viewport:', 'val')   # list of dicts or None
        ann_entries = []   # (label, mask_left, mask_right, paired)
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

        # Stats: one comparison line per external mask label, or per drawn ROI
        stats_lines = []
        if ext_entries:
            for lbl, m in ext_entries:
                stats_lines.append(
                    _format_compare_roi_stats(outleft, outright, m, m, lbl, paired=True))
        else:
            for lbl, ml, mr, paired in ann_entries:
                stats_lines.append(
                    _format_compare_roi_stats(outleft, outright, ml, mr, lbl, paired))
        self.setAttr('Viewport:', stats_text='\n'.join(s for s in stats_lines if s))

        self.setAttr('Viewport:', val=image)

        # ---- ROI OUTPUT ----
        # Only push the roi mask when the user explicitly right-clicked and
        # chose "Send ROI to output port" (one-shot read via get_roi_mask()).
        pending_mask = self.getAttr('Viewport:', 'roi_mask')
        if pending_mask is not None:
            self.setData('roi', pending_mask.astype(np.uint8))
        else:
            self.setData('roi', None)

        self.setData('out',image1)

        return 0
