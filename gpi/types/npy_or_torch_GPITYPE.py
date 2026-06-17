"""Union port type that accepts either a NumPy array or a PyTorch tensor.

Usage in a node:
    self.addInPort('in', 'NPYorTorch', obligation=gpi.REQUIRED)

A port typed NPYorTorch will accept connections from:
    - NPYarray   output ports
    - TorchTensor output ports
    - PASS (free-type) output ports

It rejects connections from unrelated types (DICT, LIST, etc.).
"""

import numpy as np

from gpi import GPIDefaultType, osuper


class NPYorTorch(GPIDefaultType):
    """Port type that accepts either a NumPy ndarray or a PyTorch Tensor."""

    def __init__(self):
        super().__init__()

    def edgeTip(self, data):
        if isinstance(data, np.ndarray):
            return str(data.shape)
        try:
            import torch
            if isinstance(data, torch.Tensor):
                return str(tuple(data.shape))
        except ImportError:
            pass
        return osuper(NPYorTorch, self).edgeTip(data)

    def toolTip_Data(self, data):
        if isinstance(data, np.ndarray):
            return f'numpy.ndarray\ndtype: {data.dtype}\nshape: {data.shape}'
        try:
            import torch
            if isinstance(data, torch.Tensor):
                return f'torch.Tensor\ndtype: {data.dtype}\nshape: {tuple(data.shape)}\ndevice: {data.device}'
        except ImportError:
            pass
        return osuper(NPYorTorch, self).toolTip_Data(data)

    def toolTip_Port(self):
        return 'NPYarray | TorchTensor'

    def matchesType(self, type_cls):
        """Accept PASS, NPYarray, or TorchTensor upstream ports."""
        if self.isFreeType(type_cls):
            return True
        type_name = type(type_cls).__name__
        return type_name in ('NPYarray', 'TorchTensor', 'NPYorTorch')

    def matchesData(self, data):
        """Accept numpy arrays and torch tensors."""
        if isinstance(data, np.ndarray):
            return True
        try:
            import torch
            if isinstance(data, torch.Tensor):
                return True
        except ImportError:
            pass
        return False
