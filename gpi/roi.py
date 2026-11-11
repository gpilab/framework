"""Volume ROI coordinates shared by the image display widgets."""

from uuid import uuid4

import numpy as np
from gpi import QtCore, QtGui


def shift_roi(roi, dx, dy):
    result = dict(roi)
    for key in ('p1', 'p2'):
        if roi.get(key) is not None:
            result[key] = (roi[key][0] + dx, roi[key][1] + dy)
    if 'pts' in roi:
        result['pts'] = [(point[0] + dx, point[1] + dy) for point in roi['pts']]
    return result


def brief_mean(data, mask):
    if data is None or not mask.any():
        return ''
    height, width = data.shape[:2]
    if mask.shape != (height, width):
        row = max(0, (mask.shape[0] - height) // 2)
        col = max(0, (mask.shape[1] - width) // 2)
        mask = mask[row:row + height, col:col + width]
        if mask.shape != (height, width):
            return ''
    if data.ndim > 2:
        data = data[..., 0]
    values = data[mask]
    if np.iscomplexobj(values):
        values = np.abs(values)
    values = values[np.isfinite(values)]
    return f'{values.mean():.4g}' if values.size else ''


class VolumeROIMixin:
    def get_roi_layout(self):
        return getattr(self, '_roi_layout', None)

    def _local_roi(self, roi, layout):
        canonicalize = getattr(self, '_canon_roi', None)
        if canonicalize is not None:
            roi = canonicalize(roi)
        if layout is None:
            return dict(roi)
        shape, axis, columns, padding = layout
        height, width = [size for index, size in enumerate(shape) if index != axis]
        points = roi.get('pts') or [roi['p1']]
        if roi.get('p2') is not None:
            points = points + [roi['p2']]
        col = int((min(point[0] for point in points) - padding) // width) if columns else 0
        row = int((min(point[1] for point in points) - padding) // height) if columns else 0
        result = shift_roi(roi, -col * width - padding, -row * height - padding)
        result['_roi_slice'] = row * columns + col if columns else roi.get('_roi_slice', 0)
        return result

    def _layout_rois(self, rois, layout):
        if layout is None:
            return rois
        shape, axis, columns, padding = layout
        height, width = [size for index, size in enumerate(shape) if index != axis]
        result = []
        for roi in rois:
            indices = (range(shape[axis]) if columns and roi.get('_roi_group')
                       else [roi.get('_roi_slice', 0) if columns else 0])
            for index in indices:
                col, row = (index % columns, index // columns) if columns else (0, 0)
                result.append(shift_roi(roi, col * width + padding, row * height + padding))
        return result

    def set_roi_layout(self, val):
        old = self.get_roi_layout()
        if val == old:
            return
        rois = []
        seen = set()
        for roi in self.imageLabel._rois:
            group = roi.get('_roi_group')
            if group and group in seen:
                continue
            if group:
                seen.add(group)
            rois.append(self._local_roi(roi, old))
        if old is not None and val is not None and old[:2] != val[:2]:
            for roi in rois:
                roi.pop('_roi_group', None)
                roi.pop('_roi_slice', None)
        self._roi_layout = val
        self.imageLabel._rois = self._layout_rois(rois, val)
        self.imageLabel._edit_roi_idx = None
        self.imageLabel.update()

    def _request_propagate_roi(self, idx=None):
        layout = self.get_roi_layout()
        rois = self.imageLabel._rois
        if not rois or layout is None:
            return
        shape, axis, columns, padding = layout
        height, width = [size for index, size in enumerate(shape) if index != axis]
        targets = [rois[idx]] if idx is not None else list(rois)
        mask = np.zeros((height, width), dtype=np.uint8)
        replacements = []
        groups = set()
        for roi in targets:
            group = roi.get('_roi_group')
            if group and group in groups:
                continue
            local = self._local_roi(roi, layout)
            if columns and not 0 <= local['_roi_slice'] < shape[axis]:
                continue
            region = self._volume_roi_mask(local, height, width)
            if not region.any():
                continue
            group = group or uuid4().hex
            roi['_roi_group'] = local['_roi_group'] = group
            groups.add(group)
            replacements.append(local)
            mask[region] = len(replacements)
        if not replacements:
            return
        remaining = [roi for roi in rois if roi.get('_roi_group') not in groups]
        self.imageLabel._rois = remaining + self._layout_rois(replacements, layout)
        volume = np.broadcast_to(mask, (shape[axis], height, width))
        self._pending_roi_mask = np.moveaxis(volume, 0, axis).copy()
        self.imageLabel.update()
        self.somethingChanged()

    def _roi_index_label(self, index):
        labels = getattr(self, '_roi_brief_stats', [])
        return labels[index] if index < len(labels) else str(index + 1)

    def _paint_roi_label(self, painter, point, text, color):
        metrics = painter.fontMetrics()
        width = self.imageLabel.width()
        text = metrics.elidedText(text, QtCore.Qt.ElideRight, max(0, width - 4))
        horizontal = max(2, min(point.x(), width - metrics.horizontalAdvance(text) - 2))
        vertical = max(metrics.ascent(), min(point.y(), self.imageLabel.height() - 2))
        anchor = QtCore.QPoint(horizontal, vertical)
        painter.setPen(QtGui.QPen(QtCore.Qt.black, 1))
        painter.drawText(anchor + QtCore.QPoint(1, 1), text)
        painter.setPen(QtGui.QPen(color, 1))
        painter.drawText(anchor, text)

    def set_roi_brief_stats(self, val):
        self._roi_brief_stats = list(val) if val else []
        self.imageLabel.update()

    def get_roi_brief_stats(self):
        return None

    def set_ext_roi_brief_stats(self, val):
        self._ext_roi_brief_stats = dict(val) if val else {}
        self.imageLabel.update()

    def get_ext_roi_brief_stats(self):
        return None

    def _ext_roi_index_label(self, index):
        return getattr(self, '_ext_roi_brief_stats', {}).get(index, str(index))