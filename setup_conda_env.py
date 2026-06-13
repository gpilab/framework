#!/usr/bin/env python3
"""
Auto-detect OS / hardware and create the GPI conda environment.

Usage:
    python setup_conda_env.py [--cuda-version 12.1]

The script:
  1. Detects OS, CPU architecture, and whether an NVIDIA GPU is present.
  2. Selects the matching environment_<platform>.yml file.
  3. Runs `conda env create` (or `conda env update` if 'gpi' already exists).
  4. Prints the next steps (activate, pip install, gpi_init).

For NVIDIA GPUs, torch is reinstalled with the matching CUDA wheel URL.
The --cuda-version flag overrides auto-detection (format: "12.1", "11.8", etc.).
"""

import argparse
import platform
import shutil
import subprocess
import sys
import os


# ── CUDA wheel index URLs (torch 2.x+) ───────────────────────────────────────
_TORCH_CUDA_URLS = {
    "12.6": "https://download.pytorch.org/whl/cu126",
    "12.4": "https://download.pytorch.org/whl/cu124",
    "12.1": "https://download.pytorch.org/whl/cu121",
    "11.8": "https://download.pytorch.org/whl/cu118",
}
_TORCH_CPU_URL  = "https://download.pytorch.org/whl/cpu"
_TORCH_CUDA_DEFAULT = "12.4"   # used when GPU detected but version unknown


def detect_os():
    """Return 'macos', 'linux', or 'windows'."""
    p = sys.platform
    if p == "darwin":
        return "macos"
    if p.startswith("linux"):
        return "linux"
    return "windows"


def detect_arch():
    """Return normalised architecture string: 'x86_64' or 'arm64'."""
    m = platform.machine().lower()
    if m in ("arm64", "aarch64"):
        return "arm64"
    return "x86_64"


def detect_cuda_version():
    """Return CUDA version string (e.g. '12.4') or None if no NVIDIA GPU."""
    # Try nvidia-smi first (works on all platforms with NVIDIA drivers installed)
    nvidia_smi = shutil.which("nvidia-smi")
    if nvidia_smi:
        try:
            out = subprocess.check_output(
                [nvidia_smi, "--query-gpu=driver_version", "--format=csv,noheader"],
                stderr=subprocess.DEVNULL, text=True
            ).strip()
            # nvidia-smi reports driver version, not CUDA version.
            # Use nvcc to get the actual toolkit version if available.
        except Exception:
            pass
        # Fall back: run `nvidia-smi` plain and parse "CUDA Version: X.Y"
        try:
            out = subprocess.check_output(
                [nvidia_smi], stderr=subprocess.DEVNULL, text=True
            )
            for line in out.splitlines():
                if "CUDA Version:" in line:
                    parts = line.split("CUDA Version:")
                    if len(parts) == 2:
                        ver = parts[1].strip().split()[0]
                        # Normalise to "major.minor"
                        v = ".".join(ver.split(".")[:2])
                        return v
        except Exception:
            pass
        # We confirmed an NVIDIA GPU exists even without a version
        return _TORCH_CUDA_DEFAULT

    # Also try nvcc for systems where smi isn't in PATH
    nvcc = shutil.which("nvcc")
    if nvcc:
        try:
            out = subprocess.check_output(
                [nvcc, "--version"], stderr=subprocess.DEVNULL, text=True
            )
            for line in out.splitlines():
                if "release" in line.lower():
                    # "Cuda compilation tools, release 12.4, V12.4.131"
                    import re
                    m = re.search(r"release\s+(\d+\.\d+)", line, re.IGNORECASE)
                    if m:
                        return m.group(1)
        except Exception:
            pass
        return _TORCH_CUDA_DEFAULT

    return None


def pick_yml(os_name):
    mapping = {
        "macos":   "environment_macos.yml",
        "linux":   "environment_linux.yml",
        "windows": "environment.yml",
    }
    return mapping[os_name]


def conda_env_exists(env_name):
    try:
        out = subprocess.check_output(
            ["conda", "env", "list"], stderr=subprocess.DEVNULL, text=True
        )
        for line in out.splitlines():
            if line.startswith(env_name + " ") or line.startswith(env_name + "\t"):
                return True
    except Exception:
        pass
    return False


def run(cmd, **kwargs):
    print(f"\n>>> {' '.join(cmd)}")
    subprocess.run(cmd, check=True, **kwargs)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--cuda-version", metavar="X.Y",
                        help="Override CUDA version detection (e.g. 12.4)")
    parser.add_argument("--env-name", default="gpi",
                        help="Conda environment name (default: gpi)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print commands without executing them")
    args = parser.parse_args()

    os_name  = detect_os()
    arch     = detect_arch()
    cuda_ver = args.cuda_version or detect_cuda_version()

    print(f"Platform : {os_name} / {arch}")
    if cuda_ver:
        print(f"CUDA     : {cuda_ver}  (NVIDIA GPU detected)")
    else:
        print("CUDA     : not detected — using CPU-only torch")

    if os_name == "macos" and arch == "arm64":
        print("Apple Silicon: torch MPS acceleration available (no CUDA needed)")
        cuda_ver = None  # macOS never uses CUDA

    yml = pick_yml(os_name)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    yml_path = os.path.join(script_dir, yml)

    if not os.path.isfile(yml_path):
        print(f"ERROR: environment file not found: {yml_path}")
        sys.exit(1)

    print(f"\nEnvironment file: {yml}")

    if args.dry_run:
        print(f"\n[dry-run] would run: conda env create -f {yml_path} --name {args.env_name}")
        _print_next_steps(args.env_name, cuda_ver, os_name)
        return

    # ── Step 1: create or update the conda environment ───────────────────────
    if conda_env_exists(args.env_name):
        print(f"\nEnvironment '{args.env_name}' already exists — updating.")
        run(["conda", "env", "update", "-f", yml_path, "--name", args.env_name, "--prune"])
    else:
        run(["conda", "env", "create", "-f", yml_path, "--name", args.env_name])

    # ── Step 2: reinstall torch with the right CUDA wheel if needed ──────────
    if cuda_ver and os_name != "macos":
        wheel_url = _TORCH_CUDA_URLS.get(cuda_ver)
        if wheel_url is None:
            # Pick closest supported version
            available = sorted(_TORCH_CUDA_URLS.keys(), reverse=True)
            wheel_url = _TORCH_CUDA_URLS[available[0]]
            print(f"\nNote: CUDA {cuda_ver} not in known wheel list; using {available[0]} wheels.")
        print(f"\nReinstalling torch with CUDA {cuda_ver} wheels...")
        run(["conda", "run", "-n", args.env_name,
             "pip", "install", "torch", "--index-url", wheel_url])

    _print_next_steps(args.env_name, cuda_ver, os_name)


def _print_next_steps(env_name, cuda_ver, os_name):
    activate = (f"conda activate {env_name}"
                if os_name != "windows" else
                f"conda activate {env_name}  (or double-click gpi.cmd)")
    print(f"""
╔══════════════════════════════════════════════════════════╗
║  Environment ready.  Next steps:                         ║
╚══════════════════════════════════════════════════════════╝

  1.  {activate}
  2.  pip install -e .
  3.  gpi_init
  4.  gpi

""")
    if cuda_ver and os_name != "macos":
        url = _TORCH_CUDA_URLS.get(cuda_ver, _TORCH_CUDA_URLS[_TORCH_CUDA_DEFAULT])
        print(f"  torch CUDA wheels used: {url}\n")


if __name__ == "__main__":
    main()
