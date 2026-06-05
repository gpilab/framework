"""Windows-specific setup for building GPI extensions with MinGW.

Run automatically by gpi_init on Windows, or manually via:
    python -m gpi.win_setup
"""
import os
import sys
import subprocess


def _conda_prefix():
    return sys.prefix


def _find_mingw_tools():
    """Return (bin_dir, tool_prefix, gendef, dlltool) for the active MinGW toolchain.

    Supports two toolchain layouts:
      - gxx_win-64 (GCC 13+): tools live in Library/bin/ with x86_64-w64-mingw32- prefix
      - m2w64-toolchain (GCC 5.3): tools live in Library/mingw-w64/bin/ with no prefix
    """
    prefix = _conda_prefix()

    # New toolchain: gxx_win-64 / conda-forge native GCC
    new_bin = os.path.join(prefix, 'Library', 'bin')
    new_gpp = os.path.join(new_bin, 'x86_64-w64-mingw32-g++.exe')
    if os.path.exists(new_gpp):
        gendef  = os.path.join(new_bin, 'gendef.exe')
        dlltool = os.path.join(new_bin, 'x86_64-w64-mingw32-dlltool.exe')
        # fallback dlltool path used by binutils_win-64
        if not os.path.exists(dlltool):
            dlltool = os.path.join(prefix, 'Library', 'x86_64-w64-mingw32', 'bin', 'dlltool.exe')
        return new_bin, 'x86_64-w64-mingw32-', gendef, dlltool

    # Old toolchain: m2w64-toolchain
    old_bin = os.path.join(prefix, 'Library', 'mingw-w64', 'bin')
    old_gpp = os.path.join(old_bin, 'g++.exe')
    if os.path.exists(old_gpp):
        gendef  = os.path.join(old_bin, 'gendef.exe')
        dlltool = os.path.join(old_bin, 'dlltool.exe')
        return old_bin, '', gendef, dlltool

    return None, None, None, None


def ensure_compiler_wrappers():
    """Create g++.bat / gcc.bat / ar.bat / dlltool.bat so distutils can find them.

    distutils' mingw32 compiler class looks for bare 'g++', 'gcc', 'ar', 'dlltool'
    in PATH.  gxx_win-64 only ships the x86_64-w64-mingw32-prefixed binaries, so we
    create thin .bat wrappers that forward all arguments to the real executables.
    """
    bin_dir, prefix, _, _ = _find_mingw_tools()
    if not bin_dir or not prefix:
        return True  # old toolchain or nothing found — nothing to wrap

    wrappers = {
        'g++.bat':    f'x86_64-w64-mingw32-g++.exe',
        'gcc.bat':    f'x86_64-w64-mingw32-gcc.exe',
        'ar.bat':     f'x86_64-w64-mingw32-gcc-ar.exe',
        'dlltool.bat':f'x86_64-w64-mingw32-dlltool.exe',
    }
    for bat_name, target_name in wrappers.items():
        bat_path    = os.path.join(bin_dir, bat_name)
        target_path = os.path.join(bin_dir, target_name)
        if not os.path.exists(target_path):
            print(f"WARNING: {target_path} not found, skipping {bat_name}")
            continue
        if not os.path.exists(bat_path):
            with open(bat_path, 'w') as f:
                f.write(f'@echo off\n"{target_path}" %*\n')
            print(f"Created wrapper: {bat_path}")
    return True


def ensure_mingw_import_lib():
    """Generate libpythonXY.a for MinGW from the MSVC-built python DLL."""
    pyver = f"python{sys.version_info.major}{sys.version_info.minor}"
    prefix = _conda_prefix()

    lib_a = os.path.join(prefix, 'libs', f'lib{pyver}.a')
    if os.path.exists(lib_a):
        return True

    _, _, gendef, dlltool = _find_mingw_tools()

    if not gendef or not os.path.exists(gendef):
        print(f"WARNING: gendef.exe not found (checked via _find_mingw_tools)")
        print("Install with: conda install -c conda-forge m2w64-toolchain  OR  gxx_win-64")
        return False
    if not dlltool or not os.path.exists(dlltool):
        print(f"WARNING: dlltool not found (checked via _find_mingw_tools)")
        print("Install with: conda install -c conda-forge m2w64-toolchain  OR  gxx_win-64")
        return False

    dll = os.path.join(prefix, f'{pyver}.dll')
    if not os.path.exists(dll):
        print(f"WARNING: {dll} not found")
        return False

    def_file = os.path.join(prefix, f'{pyver}.def')
    print(f"Generating MinGW import library: {lib_a}")
    subprocess.run([gendef, dll], cwd=prefix, check=True)
    subprocess.run([dlltool, '-D', dll, '-d', def_file, '-l', lib_a], check=True)
    print(f"Created: {lib_a}")
    return True


def ensure_distutils_cfg():
    """Write distutils.cfg to use mingw32 compiler."""
    cfg_path = os.path.join(_conda_prefix(), 'Lib', 'distutils', 'distutils.cfg')
    content = "[build_ext]\ndefine=MS_WIN64\ncompiler=mingw32\n"

    os.makedirs(os.path.dirname(cfg_path), exist_ok=True)
    existing = open(cfg_path).read() if os.path.exists(cfg_path) else ""
    if "compiler=mingw32" not in existing:
        with open(cfg_path, 'w') as f:
            f.write(content)
        print(f"Written: {cfg_path}")
    return True


def ensure_sitecustomize():
    """Install sitecustomize.py that translates MSVC flags to GCC equivalents."""
    site_packages = next(
        p for p in sys.path if 'site-packages' in p and _conda_prefix() in p
    )
    dst = os.path.join(site_packages, 'sitecustomize.py')

    code = '''\
# gpi-mingw-v2: translates MSVC compiler flags to GCC equivalents for MinGW builds
import sys

if sys.platform == 'win32':
    # Flags that map 1-to-1
    _MSVC_TO_GCC_ONE = {
        '/std:c++14': '-std=c++14',
        '/std:c++17': '-std=c++17',
        '/std:c++20': '-std=c++20',
        '/std:c++latest': '-std=c++2b',
        '/O0': '-O0',
        '/O1': '-O1',
        '/O2': '-O2',
        '/Od': '-O0',
        '/fp:fast': '-ffast-math',
        '/DNDEBUG': '-DNDEBUG',
        '/openmp': '-fopenmp',
        '/openmp:experimental': '-fopenmp',
        '/openmp:llvm': '-fopenmp',
        '/W0': '-w',
        '/W1': '-w',
        '/W2': '-Wall',
        '/W3': '-Wall',
        '/W4': '-Wall',
        '/Wall': '-Wall',
    }
    # Flags to silently drop (GCC handles these by default or has no equivalent)
    _MSVC_DROP = {'/EHsc', '/GR', '/GR-', '/MD', '/MDd', '/MT', '/MTd',
                  '/nologo', '/TP', '/Zi', '/Ot', '/GL'}

    def _translate_flags(args):
        if not args:
            return args
        out = []
        for a in args:
            if a in _MSVC_DROP:
                continue
            out.append(_MSVC_TO_GCC_ONE.get(a, a))
        return out

    def _make_patched_compile(original):
        def _patched(self, obj, src, ext, cc_args, extra_postargs, pp_opts):
            return original(self, obj, src, ext, cc_args,
                            _translate_flags(extra_postargs), pp_opts)
        return _patched

    try:
        from setuptools._distutils.compilers.C.cygwin import Compiler
        Compiler._compile = _make_patched_compile(Compiler._compile)
    except Exception:
        pass

    try:
        from distutils.cygwinccompiler import CygwinCCompiler
        CygwinCCompiler._compile = _make_patched_compile(CygwinCCompiler._compile)
    except Exception:
        pass
'''
    existing = open(dst).read() if os.path.exists(dst) else ""
    if "gpi-mingw-v2" not in existing:
        with open(dst, 'w') as f:
            f.write(code)
        print(f"Written: {dst}")
    return True


def main():
    if sys.platform != 'win32':
        return

    print("=== GPI Windows MinGW Setup ===")
    ok = True
    ok &= ensure_distutils_cfg()
    ok &= ensure_compiler_wrappers()
    ok &= ensure_mingw_import_lib()
    ok &= ensure_sitecustomize()
    if ok:
        print("Windows MinGW setup complete.")
    else:
        print("WARNING: Some setup steps failed — see messages above.")
        sys.exit(1)


if __name__ == '__main__':
    main()
