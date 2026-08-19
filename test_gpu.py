"""Tests for gpi/gpu.py and gpi/torch_cuda_setup.py device-detection logic.

Standalone script (no pytest dependency), mirrors the style of test_ttask.py:
assert + print("PASS: ..."). Run with:
    conda run -n gpi python test_gpu.py

Uses a fake 'torch' module injected into sys.modules so these tests exercise
the branching logic (multi-GPU ranking, OOM detection, MPS/CUDA probing)
deterministically, without depending on what hardware happens to be attached
to the machine running the tests.
"""

import sys
import types
import importlib


def _install_fake_torch(cuda_available=False, device_count=0, bad_devices=(),
                         mps_available=False, free_by_index=None,
                         oom_error_cls=None):
    """Install a minimal fake 'torch' module into sys.modules.

    bad_devices: set of cuda indices where torch.empty(...) should raise
                 (simulates a busy/unusable device that still reports
                 available in device_count()).
    free_by_index: {index: free_bytes} for torch.cuda.mem_get_info().
    """
    free_by_index = free_by_index or {}
    calls = {'empty_cache': 0, 'mps_empty_cache': 0}

    fake = types.ModuleType('torch')

    class _FakeTensor:
        def __init__(self, device):
            self.device = types.SimpleNamespace(type=device.split(':')[0])
        def __add__(self, other):
            return self

    def _empty(n, device='cpu'):
        idx = int(device.split(':')[1]) if device.startswith('cuda:') else None
        if device.startswith('cuda:') and idx in bad_devices:
            raise RuntimeError(f'CUDA error: device {idx} busy or unavailable')
        return _FakeTensor(device)
    fake.empty = _empty

    class _CudaOOM(RuntimeError):
        pass

    cuda_ns = types.SimpleNamespace()
    cuda_ns.is_available = lambda: cuda_available
    cuda_ns.device_count = lambda: device_count
    cuda_ns.memory_allocated = lambda idx=0: 1024
    cuda_ns.memory_reserved = lambda idx=0: 2048
    cuda_ns.mem_get_info = lambda idx: (free_by_index.get(idx, 0), 8 * 1024**3)
    cuda_ns.get_device_name = lambda idx: f'FakeGPU{idx}'
    cuda_ns.OutOfMemoryError = oom_error_cls or _CudaOOM
    def _empty_cache():
        calls['empty_cache'] += 1
    cuda_ns.empty_cache = _empty_cache
    fake.cuda = cuda_ns

    mps_ns = types.SimpleNamespace()
    mps_ns.is_available = lambda: mps_available
    def _mps_empty_cache():
        calls['mps_empty_cache'] += 1
    mps_ns.empty_cache = _mps_empty_cache
    mps_ns.current_allocated_memory = lambda: 512
    mps_ns.driver_allocated_memory = lambda: 1024
    fake.mps = mps_ns

    backends_ns = types.SimpleNamespace()
    backends_ns.mps = mps_ns
    fake.backends = backends_ns

    sys.modules['torch'] = fake
    return calls


def _uninstall_fake_torch():
    sys.modules.pop('torch', None)


def _fresh_gpu_module():
    """(Re)import gpi.gpu with a clean module-level cache for each test."""
    sys.modules.pop('gpi.gpu', None)
    import gpi.gpu as gpu
    gpu._devices = None
    gpu._util_cache = None
    gpu._util_cache_time = 0.0
    # Tests assert on the raw probe/ranking logic -- force GPU_ENABLED (in
    # memory only, never touches disk) so a real machine's saved Settings
    # dialog choice (Settings > General > Enable GPU acceleration) can't
    # make these deterministic fake-hardware tests fail.
    from gpi.config import Config
    Config.GPU_ENABLED = True
    Config.GPU_DISABLED_DEVICES = []
    return gpu


# ---------------------------------------------------------------------------
# 1. Probing: CUDA available, all devices usable
# ---------------------------------------------------------------------------
_install_fake_torch(cuda_available=True, device_count=2)
gpu = _fresh_gpu_module()
devices = gpu._probe()
assert devices == ['cpu', 'cuda:0', 'cuda:1'], f"FAIL: {devices}"
print(f"PASS: _probe() lists all usable CUDA devices — {devices}")
_uninstall_fake_torch()

# ---------------------------------------------------------------------------
# 2. Probing: one CUDA device reports available but fails real allocation
# ---------------------------------------------------------------------------
_install_fake_torch(cuda_available=True, device_count=2, bad_devices={1})
gpu = _fresh_gpu_module()
devices = gpu._probe()
assert devices == ['cpu', 'cuda:0'], f"FAIL: {devices}"
print(f"PASS: _probe() excludes a device that fails real allocation — {devices}")
_uninstall_fake_torch()

# ---------------------------------------------------------------------------
# 3. Probing: no CUDA, MPS available (Apple Silicon)
# ---------------------------------------------------------------------------
_install_fake_torch(cuda_available=False, mps_available=True)
gpu = _fresh_gpu_module()
devices = gpu._probe()
assert devices == ['cpu', 'mps'], f"FAIL: {devices}"
print(f"PASS: _probe() detects MPS when no CUDA is present — {devices}")
_uninstall_fake_torch()

# ---------------------------------------------------------------------------
# 4. Probing: no accelerator at all
# ---------------------------------------------------------------------------
_install_fake_torch(cuda_available=False, mps_available=False)
gpu = _fresh_gpu_module()
devices = gpu._probe()
assert devices == ['cpu'], f"FAIL: {devices}"
print(f"PASS: _probe() falls back to ['cpu'] with no accelerator — {devices}")
_uninstall_fake_torch()

# ---------------------------------------------------------------------------
# 5. best_device(): picks the CUDA device with the most free memory
# ---------------------------------------------------------------------------
_install_fake_torch(cuda_available=True, device_count=3,
                    free_by_index={0: 1_000_000, 1: 5_000_000, 2: 2_000_000})
gpu = _fresh_gpu_module()
gpu._devices = ['cpu', 'cuda:0', 'cuda:1', 'cuda:2']  # skip probing, test ranking only
chosen = gpu.best_device()
assert chosen == 'cuda:1', f"FAIL: {chosen}"
print(f"PASS: best_device() picks the least-loaded CUDA device — {chosen}")
_uninstall_fake_torch()

# ---------------------------------------------------------------------------
# 6. best_device(): 'mps' when it's the only accelerator
# ---------------------------------------------------------------------------
_install_fake_torch(mps_available=True)
gpu = _fresh_gpu_module()
gpu._devices = ['cpu', 'mps']
chosen = gpu.best_device()
assert chosen == 'mps', f"FAIL: {chosen}"
print(f"PASS: best_device() returns 'mps' when it's the only accelerator — {chosen}")
_uninstall_fake_torch()

# ---------------------------------------------------------------------------
# 7. best_device(): 'cpu' when nothing else is usable
# ---------------------------------------------------------------------------
_install_fake_torch()
gpu = _fresh_gpu_module()
gpu._devices = ['cpu']
chosen = gpu.best_device()
assert chosen == 'cpu', f"FAIL: {chosen}"
print(f"PASS: best_device() falls back to 'cpu' — {chosen}")
_uninstall_fake_torch()

# ---------------------------------------------------------------------------
# 8. is_oom_error(): torch.cuda.OutOfMemoryError and message-based fallback
# ---------------------------------------------------------------------------
_install_fake_torch(cuda_available=True, device_count=1)
gpu = _fresh_gpu_module()
assert gpu.is_oom_error(sys.modules['torch'].cuda.OutOfMemoryError(
    "CUDA out of memory. Tried to allocate 2.00 GiB")), \
    "FAIL: should detect torch.cuda.OutOfMemoryError"
assert gpu.is_oom_error(RuntimeError("CUDA out of memory. Tried to allocate 2 GiB")), \
    "FAIL: should detect CUDA OOM RuntimeError by message"
assert gpu.is_oom_error(RuntimeError("MPS backend out of memory")), \
    "FAIL: should detect MPS OOM RuntimeError by message"
assert not gpu.is_oom_error(RuntimeError("some unrelated failure")), \
    "FAIL: should not flag an unrelated RuntimeError"
print("PASS: is_oom_error() distinguishes GPU OOM from other errors")
_uninstall_fake_torch()

# is_oom_error() must short-circuit on an unrelated error WITHOUT importing
# torch -- this runs on every node failure (functor.py/spawn_worker.py), and
# an unconditional `import torch` there would add noticeable latency to
# every non-GPU error too (regression caught by test_ttask.py timing out).
_uninstall_fake_torch()
gpu = _fresh_gpu_module()
assert 'torch' not in sys.modules, "test setup error: torch should not be loaded yet"
assert not gpu.is_oom_error(ValueError("intentional error")), \
    "FAIL: unrelated error should not be flagged as OOM"
assert 'torch' not in sys.modules, \
    "FAIL: is_oom_error() imported torch for an unrelated error -- would slow down every node failure"
print("PASS: is_oom_error() skips the torch import entirely for unrelated errors")

# ---------------------------------------------------------------------------
# 9. recover_from_oom(): clears the cache only for devices actually present
# ---------------------------------------------------------------------------
calls = _install_fake_torch(cuda_available=True, device_count=1)
gpu = _fresh_gpu_module()
gpu._devices = ['cpu', 'cuda:0']
gpu.recover_from_oom()
assert calls['empty_cache'] == 1 and calls['mps_empty_cache'] == 0, f"FAIL: {calls}"
print("PASS: recover_from_oom() clears CUDA cache when a CUDA device is present")
_uninstall_fake_torch()

calls = _install_fake_torch(mps_available=True)
gpu = _fresh_gpu_module()
gpu._devices = ['cpu', 'mps']
gpu.recover_from_oom()
assert calls['empty_cache'] == 0 and calls['mps_empty_cache'] == 1, f"FAIL: {calls}"
print("PASS: recover_from_oom() clears MPS cache when only MPS is present")
_uninstall_fake_torch()

# ---------------------------------------------------------------------------
# 10. device_names(): human-readable names for display/tooltips
# ---------------------------------------------------------------------------
_install_fake_torch(cuda_available=True, device_count=2)
gpu = _fresh_gpu_module()
gpu._devices = ['cpu', 'cuda:0', 'cuda:1']
names = gpu.device_names()
assert names == {'cuda:0': 'FakeGPU0', 'cuda:1': 'FakeGPU1'}, f"FAIL: {names}"
print(f"PASS: device_names() reports per-device names — {names}")
_uninstall_fake_torch()

# ---------------------------------------------------------------------------
# 11. torch_cuda_setup._closest_wheel_version(): round down, never up
# ---------------------------------------------------------------------------
import gpi.torch_cuda_setup as tcs
assert tcs._closest_wheel_version("12.5") == "12.4", "FAIL: should round down from 12.5"
assert tcs._closest_wheel_version("12.6") == "12.6", "FAIL: exact match should stay 12.6"
assert tcs._closest_wheel_version("9.0") == "11.8", "FAIL: below every known build should pick the lowest"
print("PASS: _closest_wheel_version() rounds down to the nearest known build")

# ---------------------------------------------------------------------------
# 12. torch_cuda_setup._find_nvidia_smi(): falls back to known install paths
# ---------------------------------------------------------------------------
import shutil as _shutil
import os as _os
_orig_which = _shutil.which
_orig_exists = _os.path.exists
_orig_platform = sys.platform
try:
    _shutil.which = lambda name: None  # not on PATH
    sys.platform = 'win32'
    _os.environ['SystemRoot'] = _os.environ.get('SystemRoot', r'C:\Windows')
    expected = _os.path.join(_os.environ['SystemRoot'], 'System32', 'nvidia-smi.exe')
    _os.path.exists = lambda p: p == expected
    found = tcs._find_nvidia_smi()
    assert found == expected, f"FAIL: {found}"
    print(f"PASS: _find_nvidia_smi() falls back to System32 when not on PATH — {found}")
finally:
    _shutil.which = _orig_which
    _os.path.exists = _orig_exists
    sys.platform = _orig_platform

print("\nAll gpu.py / torch_cuda_setup.py tests passed.")
