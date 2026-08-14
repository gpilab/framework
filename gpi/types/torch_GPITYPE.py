#!/usr/bin/env python

# GPI type extension for PyTorch tensors.
# Mirrors NPYarray but adds device enforcement (cpu / cuda / cuda:N / mps).

try:
    import torch
    _TORCH_AVAILABLE = True
except ImportError:
    _TORCH_AVAILABLE = False

from gpi import GPIDefaultType, osuper


class TorchTensor(GPIDefaultType):
    """Port type for PyTorch tensors (torch.Tensor).

    Enforcement parameters (all optional):
        dtype   — torch dtype, e.g. torch.float32, torch.complex64
        ndim    — exact number of dimensions
        drange  — (min_ndim, max_ndim) tuple
        shape   — exact shape tuple
        device  — 'cpu', 'cuda', 'cuda:0', 'mps', etc.  A prefix match is used
                  so 'cuda' matches 'cuda:0', 'cuda:1', etc.
    """

    def __init__(self):
        super(TorchTensor, self).__init__()
        if not _TORCH_AVAILABLE:
            raise ImportError("PyTorch is not installed — TorchTensor port type unavailable.")
        self._type = [torch.Tensor]
        self._dtype = []       # list of torch dtypes
        self._ndim = None
        self._drange = None
        self._shape = None
        self._device = None    # e.g. 'cpu', 'cuda', 'cuda:0'

    # ── tooltip helpers ────────────────────────────────────────────────────

    def edgeTip(self, data):
        if isinstance(data, torch.Tensor):
            return str(tuple(data.shape))
        return osuper(TorchTensor, self).edgeTip(data)

    def toolTip_Data(self, data):
        if isinstance(data, torch.Tensor):
            return f"{data.dtype}\nshape: {tuple(data.shape)}\ndevice: {data.device}"
        return osuper(TorchTensor, self).toolTip_Data(data)

    def toolTip_Port(self):
        msg = ['torch.Tensor']
        if self._dtype:
            msg.append(str(self._dtype))
        if self._ndim is not None:
            msg.append(f"ndim: {self._ndim}")
        elif self._drange is not None:
            msg.append(f"drange: {self._drange}")
        elif self._shape is not None:
            msg.append(f"shape: {self._shape}")
        if self._device is not None:
            msg.append(f"device: {self._device}")
        return '\n'.join(msg)

    # ── data attribute setter (called when data is placed on an OutPort) ───

    def setDataAttr(self, data):
        if isinstance(data, torch.Tensor):
            # Make read-only via requires_grad=False detach — tensors don't
            # have a writeable flag like numpy, but detach() prevents accidental
            # in-place gradient accumulation across nodes.
            return data.detach()
        return osuper(TorchTensor, self).setDataAttr(data)

    # ── type matching (port-to-port compatibility check) ──────────────────

    def matchesType(self, type_cls):
        if self.isFreeType(type_cls):
            return True

        if type(type_cls) != type(self):
            return False

        if self._dtype and type_cls._dtype:
            if not any(t in self._dtype for t in type_cls._dtype):
                return False

        if self._ndim is not None and type_cls._ndim is not None:
            if self._ndim != type_cls._ndim:
                return False
        elif self._drange is not None and type_cls._drange is not None:
            if self._drange != type_cls._drange:
                return False
        elif self._shape is not None and type_cls._shape is not None:
            if self._shape != type_cls._shape:
                return False

        if self._device is not None and type_cls._device is not None:
            if not type_cls._device.startswith(self._device):
                return False

        return True

    # ── data matching (data-vs-port enforcement) ───────────────────────────

    def matchesData(self, data):
        if not isinstance(data, torch.Tensor):
            return False

        if self._dtype and data.dtype not in self._dtype:
            return False

        if self._ndim is not None and data.ndim != self._ndim:
            return False
        elif self._drange is not None:
            if data.ndim < self._drange[0] or data.ndim > self._drange[1]:
                return False
        elif self._shape is not None and tuple(data.shape) != self._shape:
            return False

        if self._device is not None:
            if not str(data.device).startswith(self._device):
                return False

        return True

    # ── setters ────────────────────────────────────────────────────────────

    def set_dtype(self, val):
        """torch.dtype | e.g. torch.float32, torch.complex64"""
        if isinstance(val, list):
            self._dtype = val
        else:
            self._dtype.append(val)

    def set_ndim(self, val):
        """int | Exact number of dimensions."""
        if not isinstance(val, int):
            raise ValueError("'ndim' requires an int")
        self._ndim = val

    def set_drange(self, val):
        """tuple(int, int) | Inclusive (min_ndim, max_ndim) range."""
        if not isinstance(val, tuple) or len(val) != 2:
            raise ValueError("'drange' requires a 2-tuple of ints")
        self._drange = val

    def set_shape(self, val):
        """tuple(int, ...) | Exact shape."""
        if not isinstance(val, tuple):
            raise ValueError("'shape' requires a tuple")
        self._shape = val

    def set_device(self, val):
        """str | 'cpu', 'cuda', 'cuda:0', etc.  Prefix-matched against tensor.device."""
        if not isinstance(val, str):
            raise ValueError("'device' requires a str")
        self._device = val
