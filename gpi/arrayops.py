#    Copyright (C) 2014  Dignity Health
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#    NO CLINICAL USE.  THE SOFTWARE IS NOT INTENDED FOR COMMERCIAL PURPOSES
#    AND SHOULD BE USED ONLY FOR NON-COMMERCIAL RESEARCH PURPOSES.  THE
#    SOFTWARE MAY NOT IN ANY EVENT BE USED FOR ANY CLINICAL OR DIAGNOSTIC
#    PURPOSES.  YOU ACKNOWLEDGE AND AGREE THAT THE SOFTWARE IS NOT INTENDED FOR
#    USE IN ANY HIGH RISK OR STRICT LIABILITY ACTIVITY, INCLUDING BUT NOT
#    LIMITED TO LIFE SUPPORT OR EMERGENCY MEDICAL OPERATIONS OR USES.  LICENSOR
#    MAKES NO WARRANTY AND HAS NO LIABILITY ARISING FROM ANY USE OF THE
#    SOFTWARE IN ANY HIGH RISK OR STRICT LIABILITY ACTIVITIES.

"""Kind-preserving array helpers for shaper-style nodes.

Structural nodes (reshape, transpose, slice, concatenate, flip, ...) do no
arithmetic, so they have no reason to convert between NumPy and PyTorch --
or to move anything to a GPU.  These helpers let such a node accept either
kind and hand back the same kind, on whatever device the input arrived on,
by papering over the handful of places where the two APIs disagree.

Anything NOT listed here (indexing, slicing, .reshape(), .ndim, .shape)
already behaves identically in both libraries and needs no wrapper.
"""

import numpy as np


def is_torch(data):
    """True for a torch.Tensor, without importing torch to find out."""
    return type(data).__module__.split('.')[0] == 'torch'


def size(data):
    """Total number of elements (np .size / torch .numel())."""
    return data.numel() if is_torch(data) else data.size


def dtype_name(data):
    """'float32', 'complex64', ... for either kind."""
    if is_torch(data):
        return str(data.dtype).replace('torch.', '')
    return data.dtype.name


def nbytes(data):
    """Size of the data in bytes, for either kind."""
    if is_torch(data):
        return data.numel() * data.element_size()
    return data.nbytes


def squeeze(data, axes=None):
    """Drop size-1 dimensions; `axes` limits it to those axes."""
    if not is_torch(data):
        return np.squeeze(data, axis=None if axes is None else tuple(axes))
    if axes is None:
        return data.squeeze()
    # one at a time, highest first, so earlier removals don't shift the rest
    for axis in sorted((a if a >= 0 else a + len(data.shape) for a in axes),
                       reverse=True):
        data = data.squeeze(axis)
    return data


def copy(data):
    return data.clone() if is_torch(data) else data.copy()


def astype(data, name):
    """Cast to a dtype given by its NumPy-style name, e.g. 'complex64'."""
    if not is_torch(data):
        return data.astype(name)
    import torch
    dtype = getattr(torch, name, None)
    if not isinstance(dtype, torch.dtype):
        raise TypeError(
            "torch has no '{}' dtype; convert to numpy first "
            "(Torch-Npy node) to cast to it.".format(name))
    return data.to(dtype=dtype)


def expand_dims(data, axis):
    if is_torch(data):
        return data.unsqueeze(axis)
    return np.expand_dims(data, axis)


def concatenate(arrays, axis):
    if is_torch(arrays[0]):
        import torch
        return torch.cat(list(arrays), dim=axis)
    return np.concatenate(list(arrays), axis=axis)


def transpose(data, order):
    """Reorder all dimensions; `order` is a full permutation."""
    if is_torch(data):
        return data.permute(*[int(i) for i in order])
    return data.transpose([int(i) for i in order])


def flip(data, axes):
    """Reverse `data` along each axis in `axes` (an iterable of ints)."""
    axes = [int(a) for a in axes]
    if not axes:
        return data
    if is_torch(data):
        import torch
        # torch has no negative-step slicing, so data[..., ::-1] is out
        return torch.flip(data, dims=axes)
    return np.flip(data, axis=tuple(axes))


def roll(data, shift, axis):
    if is_torch(data):
        import torch
        return torch.roll(data, shifts=int(shift), dims=int(axis))
    return np.roll(data, shift, axis=axis)


def zeros_like(data, shape):
    """A zero-filled array of `shape` matching data's kind/dtype/device."""
    if is_torch(data):
        import torch
        return torch.zeros(tuple(shape), dtype=data.dtype, device=data.device)
    return np.zeros(tuple(shape), dtype=data.dtype)


def shift_pad(data, shift, axis):
    """Non-circular shift along `axis`, backfilling with zeros.

    Positive `shift` moves the data toward higher indices (zeros in front);
    negative moves it toward lower indices (zeros at the end).  Replaces the
    np.insert()/np.delete() pair that has no torch counterpart.
    """
    n = data.shape[axis]
    shift = max(-n, min(n, int(shift)))
    if shift == 0:
        return data

    pad_shape = list(data.shape)
    pad_shape[axis] = abs(shift)
    pad = zeros_like(data, pad_shape)

    index = [slice(None)] * len(data.shape)
    if shift > 0:
        index[axis] = slice(0, n - shift)
        return concatenate([pad, data[tuple(index)]], axis)
    index[axis] = slice(-shift, n)
    return concatenate([data[tuple(index)], pad], axis)
