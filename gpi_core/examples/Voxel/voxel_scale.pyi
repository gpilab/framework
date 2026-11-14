"""
Voxel Scale: copy-based and in-place NumPy scaling through Voxel.
"""
from __future__ import annotations
import typing
__all__: list[str] = ['scale', 'scale_complex', 'scale_complex_inplace', 'scale_float', 'scale_float_inplace', 'scale_inplace', 'scale_int', 'scale_int_inplace']
@typing.overload
def scale(arg0: ..., arg1: typing.SupportsFloat | typing.SupportsIndex) -> ...:
    """
    Scale a float32 array without modifying it.
    """
@typing.overload
def scale(arg0: ..., arg1: typing.SupportsFloat | typing.SupportsIndex) -> ...:
    """
    Scale a float64 array without modifying it.
    """
def scale_complex(arg0: ..., arg1: complex | typing.SupportsComplex | typing.SupportsFloat | typing.SupportsIndex) -> ...:
    """
    Scale a complex64 array without modifying it.
    """
def scale_complex_inplace(arg0: ..., arg1: complex | typing.SupportsComplex | typing.SupportsFloat | typing.SupportsIndex) -> None:
    """
    Scale a writable complex64 array in place.
    """
def scale_float(arg0: ..., arg1: typing.SupportsFloat | typing.SupportsIndex) -> ...:
    """
    Scale a float32 array without modifying it.
    """
def scale_float_inplace(arg0: ..., arg1: typing.SupportsFloat | typing.SupportsIndex) -> None:
    """
    Scale a writable float32 array in place.
    """
@typing.overload
def scale_inplace(arg0: ..., arg1: typing.SupportsFloat | typing.SupportsIndex) -> None:
    """
    Scale a writable float32 array in place.
    """
@typing.overload
def scale_inplace(arg0: ..., arg1: typing.SupportsFloat | typing.SupportsIndex) -> None:
    """
    Scale a writable float64 array in place.
    """
def scale_int(arg0: ..., arg1: typing.SupportsInt | typing.SupportsIndex) -> ...:
    """
    Scale an int32 array without modifying it.
    """
def scale_int_inplace(arg0: ..., arg1: typing.SupportsInt | typing.SupportsIndex) -> None:
    """
    Scale a writable int32 array in place.
    """
