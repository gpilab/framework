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

"""gpu.py -- framework-level torch/CUDA/MPS device detection.

torch.cuda.is_available() and device_count() only ask the driver whether
CUDA exists; they don't acquire a context.  A device can pass both checks
and still raise 'CUDA error: CUDA-capable device(s) is/are busy or
unavailable' (cudaErrorDevicesUnavailable) the first time something is
actually allocated on it -- e.g. another process is holding it exclusively.
So detection here does a real allocation + op on each device and only
reports the ones that survive it.  On Apple Silicon (no CUDA), the same
probe is done against the single unified 'mps' device instead.

Probing initializes the CUDA driver/context, which is slow enough to notice,
so the result is cached for the lifetime of the process.  Call prewarm()
once at startup (off the GUI thread) so the first node doesn't pay that
cost; nodes call torch_devices() to get the vetted list.
"""

import sys
import threading
import time

_lock = threading.Lock()
_devices = None       # cached ['cpu', 'cuda:0', ...] once probing has run
_prewarm_thread = None
_util_cache = None
_util_cache_time = 0.0
_UTIL_CACHE_SECONDS = 1.0  # nvidia-smi fallback spawns a process; don't do it on every status update


def _probe_device(device):
    """True if a tensor can actually be allocated and used on `device`."""
    import torch
    t = torch.empty(1, device=device)
    t += 1
    return True


def _probe():
    devices = ['cpu']
    try:
        import torch
        if torch.cuda.is_available():
            for i in range(torch.cuda.device_count()):
                try:
                    _probe_device(f'cuda:{i}')
                    devices.append(f'cuda:{i}')
                except Exception:
                    pass
        elif getattr(torch.backends, 'mps', None) is not None and torch.backends.mps.is_available():
            # Apple Silicon: a single unified 'mps' device, no index/count like CUDA.
            try:
                _probe_device('mps')
                devices.append('mps')
            except Exception:
                pass
    except Exception:
        pass
    return devices


def torch_devices(wait=True):
    """Return ['cpu'] plus each 'cuda:N' (or 'mps' on Apple Silicon) that
    passed a real usability test.

    Detection runs once per process (on first call, or earlier if prewarm()
    was called) and is cached afterward.

    wait=False returns whatever is cached so far without blocking -- ['cpu']
    if probing hasn't completed yet -- for callers that can't stall (e.g. UI
    code); wait=True (default) blocks until the result is known.
    """
    global _devices
    if _devices is not None:
        return _devices
    if not wait:
        return ['cpu']
    # Lock held for the whole probe so concurrent callers wait for the one
    # result instead of each racing to allocate on the same devices.
    with _lock:
        if _devices is None:
            _devices = _probe()
        return _devices


def prewarm():
    """Kick off device probing on a background thread so the first call to
    torch_devices() doesn't pay the CUDA-context-init cost.  Safe to call
    more than once; only the first call spawns a thread.
    """
    global _prewarm_thread
    with _lock:
        if _devices is not None or _prewarm_thread is not None:
            return
        _prewarm_thread = threading.Thread(target=torch_devices, daemon=True)
        _prewarm_thread.start()


def memory_usage():
    """Return (allocated_bytes, reserved_bytes): this process's own CUDA
    memory footprint, summed over every vetted device.  Non-blocking (uses
    torch_devices(wait=False)) so it's safe to poll from the GUI thread;
    returns (0, 0) before probing has completed or if no GPU is usable.
    """
    allocated = reserved = 0
    devices = torch_devices(wait=False)
    if len(devices) <= 1:  # just 'cpu', or not probed yet
        return 0, 0
    try:
        import torch
        for dev in devices:
            if dev == 'cpu':
                continue
            if dev == 'mps':
                allocated += torch.mps.current_allocated_memory()
                reserved += torch.mps.driver_allocated_memory()
                continue
            idx = int(dev.split(':')[1])
            allocated += torch.cuda.memory_allocated(idx)
            reserved += torch.cuda.memory_reserved(idx)
    except Exception:
        return 0, 0
    return allocated, reserved


def utilization():
    """Best-effort GPU compute utilization percent (0-100), or None if it
    can't be determined.  This reflects the whole GPU, not just this
    process -- CUDA doesn't expose per-process compute usage.

    Cached for _UTIL_CACHE_SECONDS since the nvidia-smi fallback spawns a
    subprocess and this gets polled on every status bar update.
    """
    global _util_cache, _util_cache_time
    devices = torch_devices(wait=False)
    if len(devices) <= 1:
        return None
    if 'mps' in devices:
        return None  # no equivalent of nvidia-smi/pynvml utilization query on Apple Silicon

    now = time.time()
    if _util_cache is not None and (now - _util_cache_time) < _UTIL_CACHE_SECONDS:
        return _util_cache

    try:
        import torch
        _util_cache = torch.cuda.utilization()
        _util_cache_time = now
        return _util_cache
    except Exception:
        pass
    # torch.cuda.utilization() needs pynvml, which may not be installed;
    # fall back to parsing nvidia-smi directly.
    try:
        import subprocess
        kwargs = {}
        if sys.platform == 'win32':
            # avoid a flashing console window when launched from the GUI
            kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
        out = subprocess.check_output(
            ['nvidia-smi', '--query-gpu=utilization.gpu',
             '--format=csv,noheader,nounits'],
            timeout=2, **kwargs
        )
        _util_cache = float(out.decode().splitlines()[0].strip())
        _util_cache_time = now
        return _util_cache
    except Exception:
        _util_cache = None
        _util_cache_time = now
        return None
