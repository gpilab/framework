"""Ensure the installed torch build matches the local NVIDIA GPU/driver.

Run automatically by gpi_init (all platforms), or manually via:
    python -m gpi.torch_cuda_setup

A plain `pip install torch` (as pulled in by environment*.yml) gives you
whatever default wheel PyPI serves, which is CPU-only on Windows/Linux.
That silently "works" (import torch succeeds) until a node actually tries
torch.cuda / a 'cuda:0' device, which raises
`AssertionError: Torch not compiled with CUDA enabled` -- confusing because
the machine genuinely has a working NVIDIA GPU.  This module detects that
mismatch and reinstalls torch with the matching CUDA wheel, so the fix
applies on every system running gpi_init rather than needing a manual,
one-off `pip install torch --index-url ...` per machine.
"""

import re
import shutil
import subprocess
import sys

# Keep in sync with setup_conda_env.py's _TORCH_CUDA_URLS/_TORCH_VERSION and
# the pinned `torch==` line in environment*.yml -- all three need to agree
# so a plain `pip install .` and a CUDA reinstall land on the same version.
_TORCH_VERSION = "2.7.1"
_TORCH_CUDA_URLS = {
    "12.6": "https://download.pytorch.org/whl/cu126",
    "12.4": "https://download.pytorch.org/whl/cu124",
    "12.1": "https://download.pytorch.org/whl/cu121",
    "11.8": "https://download.pytorch.org/whl/cu118",
}
_TORCH_CUDA_DEFAULT = "12.4"


def _closest_wheel_version(detected_ver):
    """Highest wheel CUDA version <= the driver's max-supported version."""
    def parts(v):
        return tuple(int(x) for x in v.split("."))
    target = parts(detected_ver)
    candidates = [v for v in _TORCH_CUDA_URLS if parts(v) <= target]
    if candidates:
        return max(candidates, key=parts)
    return min(_TORCH_CUDA_URLS, key=parts)


def _find_nvidia_smi():
    """Locate nvidia-smi even when the driver installer didn't add it to PATH.

    On Windows, the NVIDIA driver installer doesn't always append
    `Program Files\\NVIDIA Corporation\\NVSMI` to the system PATH, so
    shutil.which() alone can miss a perfectly working GPU/driver.
    """
    found = shutil.which("nvidia-smi")
    if found:
        return found
    if sys.platform == 'win32':
        import os
        candidates = [
            os.path.join(os.environ.get('SystemRoot', r'C:\Windows'), 'System32', 'nvidia-smi.exe'),
            os.path.join(os.environ.get('ProgramFiles', r'C:\Program Files'),
                         'NVIDIA Corporation', 'NVSMI', 'nvidia-smi.exe'),
        ]
        for c in candidates:
            if os.path.exists(c):
                return c
    return None


def _detect_driver_cuda_version():
    """Return the max CUDA version the installed NVIDIA driver supports, or None."""
    nvidia_smi = _find_nvidia_smi()
    if not nvidia_smi:
        return None
    try:
        out = subprocess.check_output(
            [nvidia_smi], stderr=subprocess.DEVNULL, text=True
        )
    except Exception:
        return None
    for line in out.splitlines():
        if "CUDA Version:" in line:
            m = re.search(r"CUDA Version:\s*([\d.]+)", line)
            if m:
                return ".".join(m.group(1).split(".")[:2])
    return _TORCH_CUDA_DEFAULT  # GPU present but version unparseable


def _torch_has_working_cuda():
    """True if torch is importable, CUDA-enabled, and a device is usable.

    Runs in a fresh subprocess rather than importing in-process: if this
    process already `import torch`-ed once (e.g. the CPU build), Python
    caches that module in sys.modules, so a later reinstall on disk
    wouldn't be reflected by a plain in-process re-import.
    """
    try:
        result = subprocess.run(
            [sys.executable, "-c",
             "import torch, sys; sys.exit(0 if torch.backends.cuda.is_built() "
             "and torch.cuda.is_available() else 1)"],
            capture_output=True,
        )
        return result.returncode == 0
    except Exception:
        return False


def ensure_cuda_torch():
    """Reinstall torch with a matching CUDA wheel if the GPU/driver need it.

    No-op (besides a print) when there's no NVIDIA GPU, or torch already
    has working CUDA support.
    """
    if sys.platform == 'darwin':
        return True  # macOS never uses CUDA torch

    driver_cuda_ver = _detect_driver_cuda_version()
    if not driver_cuda_ver:
        print("torch_cuda_setup: no NVIDIA GPU detected, leaving torch as-is.")
        return True

    if _torch_has_working_cuda():
        print("torch_cuda_setup: torch already has working CUDA support.")
        return True

    wheel_ver = driver_cuda_ver if driver_cuda_ver in _TORCH_CUDA_URLS else _closest_wheel_version(driver_cuda_ver)
    wheel_url = _TORCH_CUDA_URLS[wheel_ver]
    print(f"torch_cuda_setup: NVIDIA GPU detected (driver supports CUDA {driver_cuda_ver}) "
          f"but installed torch has no working CUDA support.")
    print(f"torch_cuda_setup: reinstalling torch with CUDA {wheel_ver} wheels...")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", f"torch=={_TORCH_VERSION}",
             "--index-url", wheel_url, "--force-reinstall", "--no-cache-dir"],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"WARNING: torch CUDA reinstall failed: {e}")
        return False

    if not _torch_has_working_cuda():
        print("WARNING: torch was reinstalled but CUDA is still not available "
              "-- check that the NVIDIA driver is up to date.")
        return False

    print("torch_cuda_setup: torch now has working CUDA support.")
    return True


def main():
    ok = ensure_cuda_torch()
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
