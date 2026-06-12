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

# Author: Jim Pipe / Nick Zwart
# Date: 2013 Sep 01

import numpy as np
from matplotlib import cm
import gpi
from gpi import QtCore, QtGui, QtWidgets
from gpi.widgets import DisplayBox as _DisplayBox, GPILabel as _GPILabel


# ---------------------------------------------------------------------------
# ROI helper functions (module level — used by compute())
# ---------------------------------------------------------------------------

def _roi_coords_to_mask(coords, H, W):
    """Build a boolean 2D mask (H x W) from ROI annotation dict.

    coords: dict returned by PixelReadoutBox.get_val()
        {'type': str,  'p1': (x, y) [, 'p2': (x, y)]}   x=col, y=row
        {'type': 'Polygon', 'pts': [(x, y), ...]}          x=col, y=row
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
        rr, cc_g = np.mgrid[r1:r2 + 1, c1:c2 + 1]
        mask[r1:r2 + 1, c1:c2 + 1] = ((rr - cr) / ar) ** 2 + ((cc_g - cc) / ac) ** 2 <= 1

    elif ann == 'Polygon':
        pts = coords.get('pts', [])
        if len(pts) >= 3:
            from matplotlib.path import Path as _MplPath
            # Use the smooth spline path so the mask matches what is displayed
            smooth = _smooth_polygon(np.asarray(pts, dtype=float), n_per_seg=40)
            verts  = np.vstack([smooth, smooth[:1]])   # close the ring
            codes  = ([_MplPath.MOVETO]
                      + [_MplPath.LINETO] * (len(smooth) - 1)
                      + [_MplPath.CLOSEPOLY])
            poly_path = _MplPath(verts, codes)
            rr, cc_g = np.mgrid[0:H, 0:W]
            grid = np.column_stack([cc_g.ravel().astype(float),
                                    rr.ravel().astype(float)])
            mask = poly_path.contains_points(grid).reshape(H, W)

    return mask


def _format_roi_stats(data, mask, label='ROI'):
    """Return a formatted stats string for data values within the mask."""
    if mask is None or not mask.any():
        return ''
    src = np.abs(data) if np.iscomplexobj(data) else np.asarray(data, dtype=float)
    if src.ndim > 2:
        src = src[..., 0]  # RGB passthrough: stats on first channel
    # Mask may be larger than data when edge/black pixel border padding is active.
    # Center-crop the mask to the data footprint before indexing.
    mh, mw = mask.shape[:2]
    dh, dw = src.shape[:2]
    if mh != dh or mw != dw:
        ph = max(0, (mh - dh) // 2)
        pw = max(0, (mw - dw) // 2)
        mask = mask[ph:ph + dh, pw:pw + dw]
        if mask.shape[:2] != (dh, dw):
            return f'{label}: size mismatch'
    vals = src[mask]
    vals = vals[np.isfinite(vals)]
    if len(vals) == 0:
        return f'{label}: empty'
    return (f'{label}:  n = {len(vals):,}    '
            f'mean = {vals.mean():.4g}    '
            f'std = {vals.std():.4g}    '
            f'min = {vals.min():.4g}    '
            f'max = {vals.max():.4g}')


# ---------------------------------------------------------------------------
# Smooth polygon spline (Catmull-Rom, closed)
# ---------------------------------------------------------------------------

def _smooth_polygon(pts, n_per_seg=20):
    """Return a dense (N, 2) float array for a smooth closed Catmull-Rom spline
    that passes exactly through every control point in pts.

    pts: array-like of shape (K, 2), K >= 3
    n_per_seg: number of samples per segment (higher → smoother appearance)
    """
    pts = np.asarray(pts, dtype=float)
    n   = len(pts)
    if n < 3:
        return pts
    t  = np.linspace(0.0, 1.0, n_per_seg, endpoint=False)
    t2 = t * t
    t3 = t2 * t
    # Catmull-Rom basis coefficients
    c0 = (-t3 + 2*t2 - t)      # weight for p_{i-1}
    c1 = ( 3*t3 - 5*t2 + 2)    # weight for p_i
    c2 = (-3*t3 + 4*t2 + t)    # weight for p_{i+1}
    c3 = ( t3 - t2)             # weight for p_{i+2}
    segs = []
    for i in range(n):
        p0, p1 = pts[(i - 1) % n], pts[i]
        p2, p3 = pts[(i + 1) % n], pts[(i + 2) % n]
        segs.append(0.5 * (
            c0[:, None] * p0 + c1[:, None] * p1 +
            c2[:, None] * p2 + c3[:, None] * p3
        ))
    return np.concatenate(segs, axis=0)


# ---------------------------------------------------------------------------
# _LockedLabel — GPILabel subclass supporting multiple independent ROIs
# ---------------------------------------------------------------------------

_ROI_PALETTE = [
    QtCore.Qt.green, QtCore.Qt.yellow, QtCore.Qt.cyan,
    QtCore.Qt.magenta, QtCore.Qt.white, QtCore.Qt.red,
]

# Matching RGB triples for numpy-based pixel overlay (same order as _ROI_PALETTE)
_ROI_PALETTE_RGB = [
    (  0, 255,   0),   # green
    (255, 255,   0),   # yellow
    (  0, 255, 255),   # cyan
    (255,   0, 255),   # magenta
    (255, 255, 255),   # white
    (255,   0,   0),   # red
]


class _LockedLabel(_GPILabel):
    """GPILabel replacement supporting multiple simultaneous ROIs.

    Each left-click+drag adds a new ROI shape of the currently selected
    annotation type.  Shapes draw cleanly without coordinate text overlays.
    Right-click for per-ROI or global send/remove options.
    """

    def __init__(self, wdgGroup, parent=None):
        super().__init__(wdgGroup, parent)
        self._rois       = []   # [{'type':str, ...}, ...]  data coords
        self._ext_labels = []   # [(lbl_num, x, y), ...] data coords — from external mask
        self._drawing    = False  # True while LMB is held (non-polygon modes)
        self._cur_p1     = None   # QPoint — pixel coords of in-progress anchor
        self._cur_p2     = None   # QPoint — pixel coords of in-progress end
        self._poly_pts    = []    # [QPoint, ...] pixel coords of in-progress polygon vertices
        self._poly_cursor = None  # QPoint — current cursor pos for polygon preview
        self._edit_roi_idx = None  # which ROI is in edit mode (None = none)
        self._drag_pt_key  = None  # control point key being dragged ('p1'|'p2'|int)
        self._hover_pt_key = None  # control point key under cursor
        self.setFocusPolicy(QtCore.Qt.ClickFocus)

    # ---- coordinate helpers ----

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

    # ---- drawing ----

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
        """Top-left corner offset for the ROI index label."""
        if ann == 'Pointer' or p2 is None:
            return QtCore.QPoint(p1.x() + 10, p1.y() - 4)
        x = min(p1.x(), p2.x())
        y = min(p1.y(), p2.y())
        return QtCore.QPoint(x + 2, y - 4)

    def _ctrl_points(self, roi):
        """Return [(key, QPoint), ...] for all draggable control points of a ROI."""
        if roi['type'] == 'Polygon':
            return [(i, self._data_to_pix(pt)) for i, pt in enumerate(roi.get('pts', []))]
        pts = [('p1', self._data_to_pix(roi['p1']))]
        if roi.get('p2') is not None:
            pts.append(('p2', self._data_to_pix(roi['p2'])))
        return pts

    def _hit_ctrl_point(self, qpt, threshold=8):
        """Return the key of the nearest control point of _edit_roi_idx within
        threshold px, or None if there is no hit (or no ROI in edit mode)."""
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
        # Draw each completed ROI: outline + index label
        for i, roi in enumerate(self._rois):
            color = _ROI_PALETTE[i % len(_ROI_PALETTE)]
            painter.setPen(QtGui.QPen(color, 1))
            lbl_pt = None
            if roi['type'] == 'Polygon':
                pts_data = roi.get('pts', [])
                if len(pts_data) >= 3:
                    s = self._scale()
                    pix_arr = np.array([[x * s, y * s] for x, y in pts_data],
                                       dtype=float)
                    smooth  = _smooth_polygon(pix_arr, n_per_seg=20)
                    qpoly   = QtGui.QPolygon([
                        QtCore.QPoint(int(round(p[0])), int(round(p[1])))
                        for p in smooth
                    ])
                    painter.drawPolygon(qpoly)
                    # Small dots at control points so the user can see them
                    painter.setBrush(QtGui.QBrush(color))
                    painter.setPen(QtCore.Qt.NoPen)
                    for pt in pix_arr:
                        painter.drawEllipse(
                            QtCore.QPoint(int(round(pt[0])), int(round(pt[1]))), 2, 2)
                    painter.setBrush(QtCore.Qt.NoBrush)
                    painter.setPen(QtGui.QPen(color, 1))
                    xs = pix_arr[:, 0]
                    ys = pix_arr[:, 1]
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
        # Draw index labels for externally received mask ROIs (overlay baked into pixels)
        for lbl_num, dx, dy in self._ext_labels:
            color   = _ROI_PALETTE[(lbl_num - 1) % len(_ROI_PALETTE)]
            base_px = self._data_to_pix((dx, dy))
            lbl_pt  = base_px + QtCore.QPoint(2, -4)
            lbl_str = str(lbl_num)
            painter.setPen(QtGui.QPen(QtCore.Qt.black, 1))
            painter.drawText(lbl_pt + QtCore.QPoint(1, 1), lbl_str)
            painter.setPen(QtGui.QPen(color, 1))
            painter.drawText(lbl_pt, lbl_str)
        # Edit mode: show draggable control-point handles on the selected ROI
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
        # Draw in-progress polygon: smooth closed preview incorporating cursor position
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
            # Vertex dots for placed points
            painter.setBrush(QtGui.QBrush(color))
            painter.setPen(QtCore.Qt.NoPen)
            for pt in self._poly_pts:
                painter.drawEllipse(pt, 3, 3)
            painter.setBrush(QtCore.Qt.NoBrush)
        # Draw the in-progress non-polygon ROI with a dashed pen (no label yet)
        elif self._drawing and self._cur_p1 is not None:
            painter.setPen(QtGui.QPen(self._cur_color(), 1, QtCore.Qt.DashLine))
            self._draw_shape(painter, self._wg.ann_type, self._cur_p1, self._cur_p2)
        painter.end()

    # ---- mouse events ----

    def mousePressEvent(self, event):
        if event.button() != QtCore.Qt.LeftButton:
            return
        # If a ROI is in edit mode, check for control-point hit first
        if self._edit_roi_idx is not None:
            pt_key = self._hit_ctrl_point(event.pos())
            if pt_key is not None:
                self._drag_pt_key = pt_key
                self.setCursor(QtCore.Qt.SizeAllCursor)
                self.update()
                return   # consume — don't start a new ROI
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
        # Drag an edit-mode control point
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
        # Hover detection over the edited ROI's control points
        if self._edit_roi_idx is not None:
            pt_key = self._hit_ctrl_point(event.pos())
            if pt_key != self._hover_pt_key:
                self._hover_pt_key = pt_key
                self.setCursor(QtCore.Qt.PointingHandCursor if pt_key is not None
                               else QtCore.Qt.ArrowCursor)
                self.update()
        # Normal in-progress drawing
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
        # Finish dragging an edit-mode control point
        if self._drag_pt_key is not None:
            if event.button() == QtCore.Qt.LeftButton:
                self._drag_pt_key = None
                self.unsetCursor()
                self.update()
                self.annotationChanged.emit()
            return
        ann = self._wg.ann_type
        if ann == 'Polygon':
            return   # polygon finalizes on double-click
        if event.button() != QtCore.Qt.LeftButton or not self._drawing:
            return
        self._drawing = False
        p2_pix = event.pos()
        # Discard accidental zero-size clicks
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
        # Double-click exits edit mode (same as "Done editing" in the context menu)
        if self._edit_roi_idx is not None:
            self._wg._toggle_edit_roi(self._edit_roi_idx)
            return
        if self._wg.ann_type != 'Polygon':
            return
        # Qt fires MousePress then DoubleClick for the second click, so one extra
        # vertex was added by mousePressEvent — remove it before finalizing.
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

    # ---- right-click context menu ----

    def contextMenuEvent(self, event):
        menu = QtWidgets.QMenu(self)

        is_3d_slice = (self._wg._in_data_3d_info is not None)
        if self._rois:
            for i, roi in enumerate(self._rois):
                editing  = (i == self._edit_roi_idx)
                sub      = menu.addMenu(f'ROI {i + 1}  ({roi["type"]})')
                a_send   = sub.addAction('Send to output port')
                a_send.setData(('send',  i))
                if is_3d_slice:
                    a_prop = sub.addAction('Propagate to all slices')
                    a_prop.setData(('propagate', i))
                a_edit   = sub.addAction('Done editing' if editing else 'Edit')
                a_edit.setData(('edit', i))
                a_remove = sub.addAction('Remove')
                a_remove.setData(('clear', i))
            menu.addSeparator()
            a_send_all = menu.addAction('Send all ROIs to output port')
            a_send_all.setData(('send_all', None))
            if is_3d_slice:
                a_prop_all = menu.addAction('Propagate all ROIs to all slices')
                a_prop_all.setData(('propagate_all', None))
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
        elif op == 'propagate':
            self._wg._request_propagate_roi(idx)
        elif op == 'propagate_all':
            self._wg._request_propagate_roi(None)
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


# ---------------------------------------------------------------------------
# _HoverFilter — mouse-move event filter for pixel value readout
# ---------------------------------------------------------------------------

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
        return False  # pass event through


# ---------------------------------------------------------------------------
# PixelReadoutBox — DisplayBox with hover readout and ROI stats
# ---------------------------------------------------------------------------

class PixelReadoutBox(_DisplayBox):
    """DisplayBox extended with:
    - Pixel value readout on mouse hover  (status bar below image)
    - ROI statistics display              (stats bar below status bar)
    - ROI shape draws cleanly without text overlays
    - ROI locks on mouse release (no more accidental dragging)
    - Right-click on a drawn ROI → 'Send ROI to output port' / 'Clear ROI'

    All original DisplayBox functionality is preserved: Scale Factor,
    No Scrollbars, Interpolated Scaling, Copy, Save, annotation mode buttons.
    """

    def __init__(self, title, parent=None):
        super().__init__(title, parent)
        self._rawdata          = None
        self._display_rgba     = None   # RGBA uint8 (H, W, 4) source for scipy bicubic zoom
        self._pending_roi_mask = None   # set by _request_send_roi(), read by compute()
        self._loaded_mask      = None   # set by _load_mask_from_file(), read by compute()
        self._in_data_3d_info  = None   # (in_shape, dimval) when viewing a 3D slice, else None

        # --- Replace GPILabel with _LockedLabel ---
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

        # --- Add Polygon to annotation buttons ---
        poly_btn = QtWidgets.QCheckBox('Polygon')
        poly_btn.setCheckable(True)
        poly_btn.setAutoExclusive(True)
        poly_btn.setChecked(False)
        poly_btn.stateChanged.connect(self.annotationButton)
        self.ann_box.addWidget(poly_btn)
        self.collapsables.append(poly_btn)

        # --- Hover event filter ---
        self._hover_filter = _HoverFilter(self)
        self.imageLabel.installEventFilter(self._hover_filter)

        # --- Pixel hover label ---
        self._hover_lbl = QtWidgets.QLabel('—')
        self._hover_lbl.setStyleSheet(
            'color:#cccccc; font-size:11px; padding:2px 4px;'
            'background:#1e1e1e; border-top:1px solid #3a3a3a;')
        self._hover_lbl.setMinimumHeight(18)

        # --- ROI stats label ---
        self._stats_lbl = QtWidgets.QLabel('')
        self._stats_lbl.setStyleSheet(
            'color:#88ff88; font-size:11px; padding:2px 4px;'
            'background:#1a2a1a; border-top:1px solid #3a3a3a;')
        self._stats_lbl.setWordWrap(True)
        self._stats_lbl.hide()

        # Append both labels to the existing QGridLayout
        gl = self.layout()
        nr = gl.rowCount()
        nc = max(gl.columnCount(), 1)
        gl.addWidget(self._hover_lbl, nr,     0, 1, nc)
        gl.addWidget(self._stats_lbl, nr + 1, 0, 1, nc)

    # ---- pixel hover ----

    def _show_hover(self, r, c):
        data = self._rawdata
        if data is None:
            self._hover_lbl.setText(f'[{r}, {c}]')
            return
        h, w = data.shape[:2]
        if 0 <= r < h and 0 <= c < w:
            v = data[r, c]
            if np.iscomplexobj(data):
                self._hover_lbl.setText(
                    f'[{r}, {c}]   {v:.4g}   '
                    f'|mag| = {abs(v):.4g}   '
                    f'∠ = {np.angle(v, deg=True):.1f}°')
            else:
                self._hover_lbl.setText(f'[{r}, {c}]   =   {v:.6g}')
        else:
            self._hover_lbl.setText(f'[{r}, {c}]   (out of bounds)')

    # ---- ROI send-on-demand ----

    def _request_send_roi(self, idx=None):
        """Build a labeled uint8 mask and schedule it for output.
        Each ROI gets a unique label (1-indexed); 0 = background.
        idx=None sends all ROIs; idx=int sends only that ROI (label=1)."""
        rois = self.imageLabel._rois
        if not rois or self._rawdata is None:
            return
        H, W = self._rawdata.shape[:2]
        targets = [rois[idx]] if (idx is not None and 0 <= idx < len(rois)) else rois
        label_mask = np.zeros((H, W), dtype=np.uint8)
        for k, roi in enumerate(targets, start=1):
            m = _roi_coords_to_mask(roi, H, W)
            label_mask[m] = k
        if label_mask.any():
            self._pending_roi_mask = label_mask
            self.somethingChanged()

    def _save_mask_to_file(self, binary=False):
        """Save current drawn ROIs as a .npy file.

        binary=False: labeled uint8 (pixel value = ROI index, 1-based; 0 = background)
        binary=True:  binary uint8 (1 wherever any ROI covers, 0 elsewhere)
        """
        rois = self.imageLabel._rois
        if not rois or self._rawdata is None:
            return
        H, W = self._rawdata.shape[:2]
        label_mask = np.zeros((H, W), dtype=np.uint8)
        for k, roi in enumerate(rois, start=1):
            m = _roi_coords_to_mask(roi, H, W)
            label_mask[m] = k
        if not label_mask.any():
            return
        save_arr    = (label_mask > 0).astype(np.uint8) if binary else label_mask
        default_name = 'roi_mask_binary.npy' if binary else 'roi_mask_labeled.npy'
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, 'Save ROI mask', default_name,
            'NumPy array (*.npy);;All files (*)')
        if path:
            if not path.endswith('.npy'):
                path += '.npy'
            np.save(path, save_arr)

    def _save_shapes_to_file(self):
        """Save drawn ROI shapes as JSON (type + data coordinates)."""
        import json
        rois = self.imageLabel._rois
        if not rois:
            return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, 'Save ROI shapes', 'roi_shapes.json',
            'ROI shapes (*.json);;All files (*)')
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
        """Load ROI shapes from a JSON file; adds to (or replaces) drawn ROIs."""
        import json
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, 'Load ROI shapes', '',
            'ROI shapes (*.json);;All files (*)')
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
        """Load a pixel mask from a .npy file; used as overlay when no mask port is connected."""
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, 'Load pixel mask', '',
            'NumPy array (*.npy);;All files (*)')
        if not path:
            return
        try:
            mask = np.load(path)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, 'Load failed', str(e))
            return
        if mask.ndim != 2:
            QtWidgets.QMessageBox.warning(
                self, 'Load failed',
                f'Expected 2D array, got shape {mask.shape}')
            return
        self._loaded_mask = mask.astype(np.uint8)
        self.somethingChanged()

    def get_roi_mask(self):
        """One-shot read: return pending mask and clear it so subsequent
        compute() calls don't re-output the same mask."""
        mask = self._pending_roi_mask
        self._pending_roi_mask = None
        return mask

    def set_roi_mask(self, val):
        pass   # no-op; required so GPI doesn't complain on network reload

    def set_loaded_mask(self, val):
        pass   # no-op; storage lives in self._loaded_mask

    def get_loaded_mask(self):
        return self._loaded_mask

    def set_in_data_3d_info(self, val):
        self._in_data_3d_info = val   # (in_shape_tuple, dimval) or None

    def get_in_data_3d_info(self):
        return self._in_data_3d_info

    def _request_propagate_roi(self, idx=None):
        """Build a 3D labeled mask by replicating the drawn ROI(s) across all
        slices along the slice dimension.  idx=None propagates all ROIs."""
        rois = self.imageLabel._rois
        if not rois or self._rawdata is None or self._in_data_3d_info is None:
            return
        in_shape, dimval = self._in_data_3d_info
        H, W = self._rawdata.shape[:2]
        targets = ([rois[idx]] if (idx is not None and 0 <= idx < len(rois))
                   else rois)
        label_mask_2d = np.zeros((H, W), dtype=np.uint8)
        for k, roi in enumerate(targets, start=1):
            m = _roi_coords_to_mask(roi, H, W)
            label_mask_2d[m] = k
        if not label_mask_2d.any():
            return
        D = in_shape[dimval]
        if dimval == 0:
            mask_3d = np.broadcast_to(
                label_mask_2d[np.newaxis, :, :], (D,) + label_mask_2d.shape).copy()
        elif dimval == 1:
            mask_3d = np.broadcast_to(
                label_mask_2d[:, np.newaxis, :],
                (label_mask_2d.shape[0], D, label_mask_2d.shape[1])).copy()
        else:
            mask_3d = np.broadcast_to(
                label_mask_2d[:, :, np.newaxis],
                label_mask_2d.shape + (D,)).copy()
        self._pending_roi_mask = mask_3d
        self.somethingChanged()

    # ---- GPI widget protocol ----

    def set_val(self, val):
        if isinstance(val, QtGui.QImage):
            super().set_val(val)
        elif isinstance(val, list):
            self.imageLabel._rois = list(val)
            self.imageLabel.update()

    def get_val(self):
        """Return current ROI list in data coordinates, or None if empty."""
        return list(self.imageLabel._rois) if self.imageLabel._rois else None

    def set_rawdata(self, data):
        self._rawdata = data

    def get_rawdata(self):
        return None

    def set_display_rgba(self, arr):
        """Store the colormapped RGBA array so applyImageScale() can use scipy."""
        self._display_rgba = arr

    def applyImageScale(self):
        """Bicubic interpolation via scipy when 'Interpolated Scaling' is checked.

        Qt's SmoothTransformation uses bilinear (order=1).  scipy.ndimage.zoom
        with order=3 gives bicubic quality — noticeably sharper at integer scale
        factors (2×, 3×, 4×) with no ringing on smooth scientific images.
        Falls back to Qt bilinear if scipy is not installed.
        """
        s = self._scaleFact
        interp = self.interpCheckBox.isChecked()

        if interp and s != 1 and self._display_rgba is not None:
            try:
                from scipy.ndimage import zoom as _zoom
                # Zoom spatial dims by s; leave the 4-channel axis at 1×.
                scaled = _zoom(self._display_rgba, (s, s, 1),
                               order=3, prefilter=True)
                np.clip(scaled, 0, 255, out=scaled)
                scaled = np.ascontiguousarray(scaled, dtype=np.uint8)
                h2, w2 = scaled.shape[:2]
                qimg = QtGui.QImage(
                    scaled.data, w2, h2, w2 * 4,
                    QtGui.QImage.Format_RGBA8888).copy()
                self.imageLabel.setPixmap(QtGui.QPixmap.fromImage(qimg))
                self.imageLabel.adjustSize()
                return
            except ImportError:
                pass  # scipy not available; fall through to Qt bilinear

        # Qt fallback: bilinear (smooth) or nearest-neighbor (fast)
        if self._pixmap is not None:
            mode = (QtCore.Qt.SmoothTransformation if interp
                    else QtCore.Qt.FastTransformation)
            newpixmap = self._pixmap.scaled(
                self._pixmap.size() * s,
                aspectRatioMode=QtCore.Qt.KeepAspectRatio,
                transformMode=mode)
            self.imageLabel.setPixmap(newpixmap)
            self.imageLabel.adjustSize()

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
        # Cancel any in-progress polygon when switching annotation type
        if hasattr(lbl, '_poly_pts') and lbl._poly_pts:
            lbl._poly_pts    = []
            lbl._poly_cursor = None
            lbl.update()

    def _toggle_edit_roi(self, idx):
        """Enter edit mode for ROI idx, or exit if already editing it."""
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


# ---------------------------------------------------------------------------
# WindowLevel widget (unchanged)
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


# ---------------------------------------------------------------------------
# ExternalNode
# ---------------------------------------------------------------------------

class ExternalNode(gpi.NodeAPI):
    """2D image viewer for real or complex NPYarrays.

    INPUT:
    in   - 2D data, real or complex
           3D uint8 ARGB data (e.g. output of another ImageDisplay node)
    mask - (optional) boolean/uint8 ROI mask from another node; when
           connected, ROI statistics are computed on this mask rather than
           on the drawn annotation.  Useful for comparing the same region
           across different images.

    OUTPUTS:
    out  - 3D uint8 RGBA image array (h x w x 4)
    roi  - 2D uint8 mask array (h x w); 1 inside the drawn ROI, 0 outside.
           None if no annotation is drawn.
    temp - reserved debug output (unused)

    WIDGETS:
    I/O Info:    - input shape, dtype, data range
    Viewport:    - image display (DisplayBox)
        Scale Factor / No Scrollbars / Interpolated Scaling / Copy / Save
        Annotation tools: Pointer, Line, Rectangle, Ellipse
        Hover pixel value: shown in status bar below image
        ROI statistics:   shown in green bar; mean/std/min/max within the
                          drawn annotation (or the mask inport if connected)
    L W F C:     - Level/Window/Floor/Ceiling brightness mapping
    ...          - (all other controls same as original ImageDisplay)
    """

    def execType(self):
        return gpi.GPI_THREAD

    def initUI(self):

        # Widgets
        self.addWidget('TextBox', 'I/O Info:')
        self.addWidget('ExclusivePushButtons', 'Complex Display',
                       buttons=['R', 'I', 'M', 'P', 'C'], val=4)
        self.real_cmaps    = ['Gray', 'IceFire', 'Fire', 'Hot', 'HOT2', 'BGR']
        self.complex_cmaps = ['HSV', 'HSL', 'HUSL', 'CoolWarm']
        self.addWidget('ExclusivePushButtons', 'Color Map',
                       buttons=self.real_cmaps, val=0, collapsed=True)
        self.addWidget('SpinBox', 'Edge Pixels', min=0)
        self.addWidget('SpinBox', 'Black Pixels', min=0)
        self.addWidget('PixelReadoutBox', 'Viewport:')
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
        self.addInPort('in',   'NPYarray', drange=(2, 3))
        self.addInPort('mask', 'NPYarray', obligation=gpi.OPTIONAL)
        self.addOutPort('out',  'NPYarray')
        self.addOutPort('temp', 'NPYarray')
        self.addOutPort('roi',  'NPYarray')

    def validate(self):

        data    = self.getData('in')
        dimfunc = self.getVal('Extra Dimension')

        if data.ndim == 3:
            dimval = self.getVal('Slice/Tile Dimension')
            self.setAttr('Extra Dimension', visible=True)
            if data.shape[-1] not in [3, 4]:
                if dimfunc > 1:
                    dimfunc = 0
                self.setAttr('Extra Dimension', buttons=['Slice', 'Tile'], val=dimfunc)
            else:
                if data.dtype == 'uint8':
                    dimfunc = 2
                self.setAttr('Extra Dimension',
                             buttons=['Slice', 'Tile', 'RGB(A)'], val=dimfunc)

            if dimfunc == 0:
                slval = self.getVal('Slice')
                self.setAttr('Slice/Tile Dimension', visible=True)
                if slval > data.shape[dimval]:
                    slval = data.shape[dimval]
                self.setAttr('Slice', visible=True, min=1,
                             max=data.shape[dimval], val=slval)
                self.setAttr('# Rows',    visible=False)
                self.setAttr('# Columns', visible=False)
            elif dimfunc == 1:
                self.setAttr('Slice/Tile Dimension', visible=True)
                ncol = self.getVal('# Columns')
                nrow = self.getVal('# Rows')
                N    = data.shape[dimval]

                if (ncol == 1 and nrow == 1
                        or 'Slice/Tile Dimension' in self.widgetEvents()):
                    ncol = np.round(np.sqrt(N))
                if nrow * ncol < N:
                    nrow = np.ceil(N / ncol)
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
            if np.iscomplexobj(data):
                self.setAttr('Complex Display', visible=True)
                scalarvis = self.getVal('Complex Display') != 4
            else:
                self.setAttr('Complex Display', visible=False)
                scalarvis = True

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

        # Fetch input — no upfront copy; slice/tile first
        in_data  = self.getData('in')
        in_shape = in_data.shape
        in_dtype = in_data.dtype
        data     = in_data

        # ---- EXTRA DIMENSION: slice or tile BEFORE processing ----
        dimfunc = self.getVal('Extra Dimension')
        dimval  = self.getVal('Slice/Tile Dimension')

        if data.ndim == 3 and dimfunc < 2:
            if dimfunc == 0:  # slice one frame
                slval = self.getVal('Slice') - 1
                if dimval == 0:
                    data = data[slval, ...]
                elif dimval == 1:
                    data = data[:, slval, :]
                else:
                    data = data[..., slval]
            else:  # tile all frames into a mosaic
                ncol = int(self.getVal('# Columns'))
                nrow = int(self.getVal('# Rows'))
                data = np.rollaxis(data, dimval)
                N, xres, yres = data.shape
                N_new = ncol * nrow
                data = np.pad(data, ((0, N_new - N), (0, 0), (0, 0)),
                              mode='constant')
                data = np.reshape(data, (nrow, ncol, xres, yres))
                data = np.swapaxes(data, 1, 2)
                data = np.reshape(data, (nrow * xres, ncol * yres))

        # Save the sliced-but-unprocessed data for pixel-value hover readout.
        # All subsequent operations reassign 'data'; this reference stays stable.
        raw_2d = data

        # ---- DISPLAY PARAMETERS ----
        gamma = self.getVal('Gamma')
        lval  = self.getAttr('L W F C:', 'val')
        cval  = self.getVal('Complex Display')

        if 'Complex Display' in self.widgetEvents():
            if cval == 4:
                self.setAttr('Color Map', buttons=self.complex_cmaps,
                             collapsed=self.getAttr('Color Map', 'collapsed'),
                             val=0)
            else:
                self.setAttr('Color Map', buttons=self.real_cmaps,
                             collapsed=self.getAttr('Color Map', 'collapsed'),
                             val=0)

        cmap = self.getVal('Color Map')
        sval = self.getVal('Scalar Display')
        zval = self.getVal('Zero Ref')
        fval = self.getVal('Fix Range')
        rmin = self.getVal('Range Min')
        rmax = self.getVal('Range Max')

        flor = 0.01 * lval['floor']
        ceil = 0.01 * lval['ceiling']
        if ceil == flor:
            flor = 0.999 if ceil == 1. else flor
            ceil = ceil  if ceil == 1. else ceil + 0.001

        # ---- COMPLEX (magnitude × phase colormap) ----
        if np.iscomplexobj(data) and cval == 4:
            mag   = np.abs(data)
            phase = np.angle(data, deg=True)

            data_min = 0.
            if fval:
                data_max = rmax
            else:
                data_max = float(np.nanmax(mag))
                if not np.isfinite(data_max):
                    data_max = 1.0
                self.setAttr('Range Max', val=data_max)

            data_range = data_max - data_min
            new_min = data_range * flor + data_min
            new_max = data_range * ceil  + data_min
            mag = np.clip(mag, new_min, new_max)

            if new_max > new_min:
                mag = (mag - new_min) / (new_max - new_min)
                if gamma != 1:
                    mag = np.power(mag, gamma)
            else:
                mag = np.ones(mag.shape)

            # Optional phase-color border ring
            edgpix = self.getVal('Edge Pixels')
            blkpix = self.getVal('Black Pixels')
            if edgpix + blkpix > 0:
                h2 = mag.shape[0] + 2 * (edgpix + blkpix)
                w2 = mag.shape[1] + 2 * (edgpix + blkpix)
                mag2   = np.zeros((h2, w2))
                phase2 = np.zeros((h2, w2))
                frame  = np.zeros((h2, w2), dtype=bool)
                frame[0:edgpix, :]       = True
                frame[h2 - edgpix:h2, :] = True
                frame[:, 0:edgpix]       = True
                frame[:, w2 - edgpix:w2] = True
                pad = edgpix + blkpix
                orig_h, orig_w = mag.shape
                mag2[pad:pad + orig_h, pad:pad + orig_w]   = mag
                mag2[frame]                                = 1
                phase2[pad:pad + orig_h, pad:pad + orig_w] = phase
                xloc = np.tile(np.linspace(-1., 1., w2), (h2, 1))
                yloc = np.tile(np.linspace(1., -1., h2), (w2, 1)).T
                phase2[frame] = np.degrees(np.arctan2(yloc[frame], xloc[frame]))
                mag, phase = mag2, phase2

            if cmap == 0:
                phase_cmap = cm.hsv
            elif cmap == 1:
                try:
                    import seaborn as sns
                    import matplotlib.colors as col
                    phase_cmap = col.ListedColormap(sns.color_palette('hls', 256))
                except ImportError:
                    self.log.warn('Seaborn not available; falling back on HSV.')
                    phase_cmap = cm.hsv
            elif cmap == 2:
                try:
                    import seaborn as sns
                    import matplotlib.colors as col
                    phase_cmap = col.ListedColormap(sns.color_palette('husl', 256))
                except ImportError:
                    self.log.warn('Seaborn not available; falling back on HSV.')
                    phase_cmap = cm.hsv
            else:
                phase_cmap = cm.coolwarm

            phase_norm = (phase + 180) / 360
            if cmap != 3:
                phase_norm = (phase_norm - 1 / 3) % 1

            colorized = (255 * cm.gray(mag) * phase_cmap(phase_norm)).astype(np.uint8)
            red   = colorized[..., 0]
            green = colorized[..., 1]
            blue  = colorized[..., 2]
            alpha = colorized[..., 3]

        # ---- SCALAR DISPLAY ----
        elif dimfunc != 2:
            if np.iscomplexobj(data):
                if cval == 0:
                    data = np.real(data)
                elif cval == 1:
                    data = np.imag(data)
                elif cval == 2:
                    data = np.abs(data)
                elif cval == 3:
                    data = np.angle(data, deg=True)

            if sval == 1:
                data = np.abs(data)
            elif sval == 2:
                sign = np.sign(data)
                data = np.abs(data)

            if fval:
                data_min, data_max = rmin, rmax
            else:
                data_min, data_max = _safe_range(data)

            if sval != 2:
                if zval == 1:
                    data_min = 0.
                elif zval == 2:
                    data_max = max(abs(data_min), abs(data_max))
                    data_min = -data_max
                elif zval == 3:
                    data_max = 0.
                data_range = data_max - data_min
                self.setAttr('Range Min', val=data_min)
                self.setAttr('Range Max', val=data_max)
            else:
                data_min   = 0.
                data_max   = max(abs(data_min), abs(data_max))
                data_range = data_max
                self.setAttr('Range Min', val=-data_range)
                self.setAttr('Range Max', val=data_range)

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
                if cmap == 0:  # Grayscale
                    luma  = np.uint8(data)
                    red   = luma
                    green = luma
                    blue  = luma
                    alpha = np.full(luma.shape, 255, dtype=np.uint8)
                else:
                    rd = np.zeros(data.shape)
                    gn = np.zeros(data.shape)
                    be = np.zeros(data.shape)

                    if cmap == 1:  # IceFire
                        hue = 4. * (data / 256.)
                        h0 = hue < 1.
                        h1 = (hue >= 1.) & (hue < 2.)
                        h2 = (hue >= 2.) & (hue < 3.)
                        h3 = (hue >= 3.) & (hue < 4.)
                        be[h0] = hue[h0]
                        gn[h1] = (hue-1.)[h1]; rd[h1] = (hue-1.)[h1]; be[h1] = 1.
                        gn[h2] = 1.;            rd[h2] = 1.;            be[h2] = (3.-hue)[h2]
                        rd[h3] = 1.;            gn[h3] = (4.-hue)[h3]

                    elif cmap == 2:  # Fire
                        hue = 4. * (data / 256.)
                        h0 = hue < 1.
                        h1 = (hue >= 1.) & (hue < 2.)
                        h2 = (hue >= 2.) & (hue < 3.)
                        h3 = (hue >= 3.) & (hue < 4.)
                        be[h0] = hue[h0]
                        be[h1] = (2.-hue)[h1]; rd[h1] = (hue-1.)[h1]
                        rd[h2] = 1.;           gn[h2] = (hue-2.)[h2]
                        rd[h3] = 1.;           gn[h3] = 1.; be[h3] = (hue-3.)[h3]

                    elif cmap == 3:  # Hot
                        hue = 3. * (data / 256.)
                        h0 = hue < 1.
                        h1 = (hue >= 1.) & (hue < 2.)
                        h2 = (hue >= 2.) & (hue < 3.)
                        rd[h0] = hue[h0]
                        rd[h1] = 1.; gn[h1] = (hue-1.)[h1]
                        rd[h2] = 1.; gn[h2] = 1.; be[h2] = (hue-2.)[h2]

                    elif cmap == 4:  # HOT2 (ASIST)
                        r0 = data < 20.
                        r1 = (data >= 20.)  & (data <= 100.)
                        r3 = (data >= 128.) & (data <= 191.)
                        r4 = data > 191.
                        rd[r0] = data[r0] * (4.   / 255.)
                        rd[r1] = (80. - (data[r1] - 20.)) / 255.
                        rd[r3] = (data[r3] - 128.) * (4. / 255.)
                        rd[r4] = 1.
                        g1 = (data >= 45.)  & (data <= 130.)
                        g2 = (data > 130.)  & (data < 192.)
                        g3 = data >= 192.
                        gn[g1] = (data[g1] - 45.) * (3. / 255.)
                        gn[g2] = 1.
                        gn[g3] = (252. - (data[g3] - 192.) * 4.) / 255.
                        b1 = (data >= 1.)  & (data < 86.)
                        b2 = (data >= 86.) & (data <= 137.)
                        be[b1] = (data[b1] - 1.) * (3. / 255.)
                        be[b2] = (255. - (data[b2] - 86.) * 5.) / 255.

                    elif cmap == 5:  # BGR
                        hue = 4. * (data / 256.)
                        h0 = hue < 1.
                        h1 = (hue >= 1.) & (hue < 2.)
                        h2 = (hue >= 2.) & (hue < 3.)
                        h3 = (hue >= 3.) & (hue < 4.)
                        be[h0] = hue[h0]
                        gn[h1] = (hue-1.)[h1]; be[h1] = 1.
                        gn[h2] = 1.; rd[h2] = (hue-2.)[h2]; be[h2] = (3.-hue)[h2]
                        rd[h3] = 1.; gn[h3] = (4.-hue)[h3]

                    red   = np.uint8(255. * rd)
                    green = np.uint8(255. * gn)
                    blue  = np.uint8(255. * be)
                    alpha = np.full(red.shape, 255, dtype=np.uint8)

            else:  # Sign: positive → green, negative → magenta
                rd = np.zeros(data.shape)
                gn = np.zeros(data.shape)
                be = np.zeros(data.shape)
                rd[sign <= 0] = data[sign <= 0]
                be[sign <= 0] = data[sign <= 0]
                gn[sign >= 0] = data[sign >= 0]
                red   = rd.astype(np.uint8)
                green = gn.astype(np.uint8)
                blue  = be.astype(np.uint8)
                alpha = np.full(red.shape, 255, dtype=np.uint8)

        # ---- RGB(A) PASSTHROUGH ----
        else:
            if data.shape[-1] >= 3:
                red   = data[:, :, 0].astype(np.uint8)
                green = data[:, :, 1].astype(np.uint8)
                blue  = data[:, :, 2].astype(np.uint8)
                alpha = (data[:, :, 3].astype(np.uint8)
                         if data.shape[-1] == 4
                         else np.full(red.shape, 255, dtype=np.uint8))
            else:
                self.log.warn(f'ImageDisplay: incompatible input veclen {data.shape[-1]}')
                return 1

        # ---- ASSEMBLE OUTPUT IMAGE ----
        # Format_RGBA8888 maps bytes as R,G,B,A in memory — no endian ambiguity.
        h, w = red.shape[:2]
        image = np.zeros((h, w, 4), dtype=np.uint8)
        image[:, :, 0] = red
        image[:, :, 1] = green
        image[:, :, 2] = blue
        image[:, :, 3] = alpha

        # ---- ROI: annotation masks + external mask validation & overlay ----
        roi_coords = self.getAttr('Viewport:', 'val')   # list of dicts or None
        ann_masks  = []   # [(label_str, bool_mask), ...] one entry per drawn ROI
        if roi_coords and isinstance(roi_coords, list):
            for i, coord in enumerate(roi_coords):
                m = _roi_coords_to_mask(coord, h, w)
                if m.any():
                    ann_masks.append((f'ROI {i + 1} ({coord.get("type", "?")})', m))

        ext_mask = self.getData('mask')
        if ext_mask is None:
            ext_mask = self.getAttr('Viewport:', 'loaded_mask')
        ext_stats_masks     = []   # list of (label_str, bool_mask) — one per ROI label
        ext_label_positions = []   # [(lbl_num, x, y), ...] top-left bbox, data coords
        mask_warn           = ''

        if ext_mask is not None:
            raw_m = ext_mask
            if raw_m.ndim != 2:
                mask_warn = f'mask: wrong shape {ext_mask.shape} (expected 2D)'
            elif raw_m.shape != (h, w):
                mask_warn = (f'mask: size mismatch — '
                             f'mask={raw_m.shape}, image=({h}, {w})')
            else:
                labels = np.unique(raw_m)
                labels = labels[labels != 0]
                if len(labels) == 0:
                    mask_warn = 'mask: all zeros'
                else:
                    # Per-label colored overlay + per-label stats entry + label position
                    blend = 0.35
                    for lbl in labels:
                        m       = (raw_m == lbl)
                        lbl_i   = int(lbl) - 1
                        r_ov, g_ov, b_ov = _ROI_PALETTE_RGB[lbl_i % len(_ROI_PALETTE_RGB)]
                        image[:, :, 0] = np.where(
                            m, np.clip(image[:, :, 0] * (1.0 - blend) + r_ov * blend, 0, 255),
                            image[:, :, 0]).astype(np.uint8)
                        image[:, :, 1] = np.where(
                            m, np.clip(image[:, :, 1] * (1.0 - blend) + g_ov * blend, 0, 255),
                            image[:, :, 1]).astype(np.uint8)
                        image[:, :, 2] = np.where(
                            m, np.clip(image[:, :, 2] * (1.0 - blend) + b_ov * blend, 0, 255),
                            image[:, :, 2]).astype(np.uint8)
                        ext_stats_masks.append((f'ROI {int(lbl)}', m))
                        ys, xs = np.where(m)
                        if len(xs):
                            ext_label_positions.append(
                                (int(lbl), float(xs.min()), float(ys.min())))

        # ---- I/O INFO ----
        try:
            if np.iscomplexobj(in_data):
                lo, hi = _safe_range(np.abs(in_data))
                range_label = f'|mag| range: [{lo:.4g}, {hi:.4g}]'
            else:
                lo, hi = _safe_range(in_data.astype(float))
                range_label = f'range: [{lo:.4g}, {hi:.4g}]'
        except Exception:
            range_label = 'range: n/a'

        io_info = (f'shape: {in_shape}   dtype: {in_dtype}\n'
                   f'display: {(h, w)}   {range_label}')
        if mask_warn:
            io_info += f'\nWARNING: {mask_warn}'
        self.setAttr('I/O Info:', val=io_info)

        # ---- UPDATE VIEWPORT ----
        # Create QImage from RGBA array.  .copy() makes Qt own the data so the
        # numpy buffer can be freed after this thread returns.
        image_c = np.ascontiguousarray(image)
        qimage = QtGui.QImage(
            image_c.data, w, h, w * 4, QtGui.QImage.Format_RGBA8888
        ).copy()
        # Pass the RGBA array before val so applyImageScale() sees it immediately.
        self.setAttr('Viewport:', display_rgba=image_c)
        self.setAttr('Viewport:', val=qimage)
        self.setAttr('Viewport:', rawdata=raw_2d)
        self.setAttr('Viewport:', ext_labels=ext_label_positions)
        if in_data.ndim == 3 and dimfunc == 0:
            self.setAttr('Viewport:', in_data_3d_info=(tuple(in_shape), dimval))
        else:
            self.setAttr('Viewport:', in_data_3d_info=None)
        # Stats: one line per external label, or one line per drawn ROI
        stats_lines = []
        if ext_stats_masks:
            for lbl_str, m in ext_stats_masks:
                stats_lines.append(_format_roi_stats(raw_2d, m, lbl_str))
        else:
            for lbl, m in ann_masks:
                stats_lines.append(_format_roi_stats(raw_2d, m, lbl))
        self.setAttr('Viewport:', stats_text='\n'.join(s for s in stats_lines if s))

        # ---- ROI OUTPUT ----
        # Only push the roi mask when the user explicitly right-clicked and
        # chose "Send ROI to output port".  get_roi_mask() is a one-shot read
        # (clears the pending mask so it isn't re-sent on the next compute).
        pending_mask = self.getAttr('Viewport:', 'roi_mask')
        if pending_mask is not None:
            self.setData('roi', pending_mask.astype(np.uint8))
        else:
            self.setData('roi', None)

        # ---- DATA OUTPUT ----
        self.setData('out', image)

        return 0
