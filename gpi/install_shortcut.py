"""
Create desktop / start-menu shortcuts to launch GPI.

CLI (non-interactive — creates all locations):
    gpi_shortcut

CLI (interactive — prompts for location):
    gpi_shortcut --interactive
    python -m gpi.install_shortcut --interactive

GPI menu:
    File → Create Desktop Shortcut
"""

import os
import sys
import subprocess


# ── Helpers ───────────────────────────────────────────────────────────────────

def _pkg_path():
    return os.path.dirname(os.path.realpath(__file__))


def _icon_path():
    """Return the best available icon file for the current platform."""
    graphics = os.path.join(_pkg_path(), 'graphics')
    if sys.platform == 'win32':
        ico = os.path.join(graphics, 'gpi.ico')
        png = os.path.join(graphics, 'iclogo.png')
        if not os.path.exists(ico) and os.path.exists(png):
            try:
                from PIL import Image
                img = Image.open(png).convert('RGBA')
                img.save(ico, format='ICO',
                         sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
            except Exception:
                pass
        return ico if os.path.exists(ico) else png
    elif sys.platform == 'darwin':
        icns = os.path.join(graphics, 'gpi.icns')
        return icns if os.path.exists(icns) else ''
    else:
        return os.path.join(graphics, 'iclogo.png')


def _launcher():
    """Return (executable, arguments) that launch GPI without a console window."""
    if sys.platform == 'win32':
        pythonw = os.path.join(os.path.dirname(sys.executable), 'pythonw.exe')
        exe = pythonw if os.path.exists(pythonw) else sys.executable
        return exe, '-m gpi.launch'
    else:
        gpi_script = os.path.join(os.path.dirname(sys.executable), 'gpi')
        if os.path.exists(gpi_script):
            return gpi_script, ''
        return sys.executable, '-m gpi.launch'


# ── Windows ───────────────────────────────────────────────────────────────────

def _create_lnk(lnk_path, exe, args, workdir, icon):
    """Create a Windows .lnk shortcut. Returns True on success."""
    try:
        import win32com.client
        shell = win32com.client.Dispatch('WScript.Shell')
        sc = shell.CreateShortCut(lnk_path)
        sc.Targetpath = exe
        sc.Arguments = args
        sc.WorkingDirectory = workdir
        sc.Description = 'Graphical Programming Interface (GPI)'
        if icon and os.path.exists(icon):
            sc.IconLocation = icon
        sc.save()
        return True
    except Exception:
        pass

    icon_line = f"$SC.IconLocation = '{icon}'" if (icon and os.path.exists(icon)) else ''
    ps = f"""
$WS = New-Object -ComObject WScript.Shell
$SC = $WS.CreateShortcut('{lnk_path}')
$SC.TargetPath = '{exe}'
$SC.Arguments = '{args}'
$SC.WorkingDirectory = '{workdir}'
$SC.Description = 'Graphical Programming Interface (GPI)'
{icon_line}
$SC.Save()
"""
    try:
        result = subprocess.run(
            ['powershell', '-NoProfile', '-NonInteractive', '-Command', ps],
            capture_output=True, timeout=15
        )
        return result.returncode == 0
    except Exception:
        return False


def _install_windows_desktop():
    exe, args = _launcher()
    icon = _icon_path()
    desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
    if not os.path.isdir(desktop):
        return False, 'Desktop folder not found'
    lnk = os.path.join(desktop, 'GPI.lnk')
    ok = _create_lnk(lnk, exe, args, os.path.expanduser('~'), icon)
    return ok, 'Desktop'


def _install_windows_startmenu():
    exe, args = _launcher()
    icon = _icon_path()
    start_menu = os.path.join(
        os.environ.get('APPDATA', os.path.expanduser('~')),
        'Microsoft', 'Windows', 'Start Menu', 'Programs'
    )
    if not os.path.isdir(start_menu):
        return False, 'Start Menu Programs folder not found'
    lnk = os.path.join(start_menu, 'GPI.lnk')
    ok = _create_lnk(lnk, exe, args, os.path.expanduser('~'), icon)
    return ok, 'Start Menu'


def install_windows(locations=('desktop', 'startmenu')):
    """Create Windows shortcuts. locations: iterable of 'desktop' and/or 'startmenu'."""
    created, failed = [], []
    for loc in locations:
        if loc == 'desktop':
            ok, label = _install_windows_desktop()
        elif loc == 'startmenu':
            ok, label = _install_windows_startmenu()
        else:
            continue
        (created if ok else failed).append(label)
    return created, failed


# ── macOS ─────────────────────────────────────────────────────────────────────

def _make_macos_script():
    exe, args = _launcher()
    return f'#!/bin/bash\n"{exe}" {args}\n'


def _install_macos_desktop():
    path = os.path.join(os.path.expanduser('~'), 'Desktop', 'GPI.command')
    try:
        with open(path, 'w') as f:
            f.write(_make_macos_script())
        os.chmod(path, 0o755)
        return True, 'Desktop'
    except Exception:
        return False, 'Desktop'


def _install_macos_applications():
    path = os.path.join('/Applications', 'GPI.command')
    if not os.path.isdir('/Applications'):
        return False, 'Applications folder not found'
    try:
        with open(path, 'w') as f:
            f.write(_make_macos_script())
        os.chmod(path, 0o755)
        return True, 'Applications'
    except Exception:
        return False, 'Applications'


def install_macos(locations=('desktop', 'applications')):
    """Create macOS shortcuts. locations: iterable of 'desktop' and/or 'applications'."""
    created, failed = [], []
    for loc in locations:
        if loc == 'desktop':
            ok, label = _install_macos_desktop()
        elif loc == 'applications':
            ok, label = _install_macos_applications()
        else:
            continue
        (created if ok else failed).append(label)
    return created, failed


# ── Linux ─────────────────────────────────────────────────────────────────────

def _linux_desktop_entry():
    exe, args = _launcher()
    icon = _icon_path()
    return (
        '[Desktop Entry]\n'
        'Name=GPI\n'
        'Comment=Graphical Programming Interface\n'
        f'Exec={exe} {args}\n'
        f'Icon={icon}\n'
        'Terminal=false\n'
        'Type=Application\n'
        'Categories=Science;Education;\n'
    )


def _install_linux_desktop():
    desktop_dir = os.path.join(os.path.expanduser('~'), 'Desktop')
    os.makedirs(desktop_dir, exist_ok=True)
    path = os.path.join(desktop_dir, 'gpi.desktop')
    try:
        with open(path, 'w') as f:
            f.write(_linux_desktop_entry())
        os.chmod(path, 0o755)
        return True, 'Desktop'
    except Exception:
        return False, 'Desktop'


def _install_linux_appmenu():
    apps_dir = os.path.join(os.path.expanduser('~'), '.local', 'share', 'applications')
    os.makedirs(apps_dir, exist_ok=True)
    path = os.path.join(apps_dir, 'gpi.desktop')
    try:
        with open(path, 'w') as f:
            f.write(_linux_desktop_entry())
        os.chmod(path, 0o755)
        try:
            subprocess.run(['update-desktop-database', apps_dir],
                           capture_output=True, timeout=5)
        except Exception:
            pass
        return True, 'Applications Menu'
    except Exception:
        return False, 'Applications Menu'


def install_linux(locations=('desktop', 'appmenu')):
    """Create Linux shortcuts. locations: iterable of 'desktop' and/or 'appmenu'."""
    created, failed = [], []
    for loc in locations:
        if loc == 'desktop':
            ok, label = _install_linux_desktop()
        elif loc == 'appmenu':
            ok, label = _install_linux_appmenu()
        else:
            continue
        (created if ok else failed).append(label)
    return created, failed


# ── Public API ────────────────────────────────────────────────────────────────

def install(locations=None):
    """Create shortcuts for the current platform. Returns (created, failed) lists.

    locations: list of location keys, or None for all available locations.
    """
    if sys.platform == 'win32':
        locs = locations or ('desktop', 'startmenu')
        return install_windows(locs)
    elif sys.platform == 'darwin':
        locs = locations or ('desktop', 'applications')
        return install_macos(locs)
    else:
        locs = locations or ('desktop', 'appmenu')
        return install_linux(locs)


def _platform_menu():
    """Return (option_list, label_map) for the current platform.

    option_list: list of (key, description) in display order.
    """
    if sys.platform == 'win32':
        opts = [
            ('desktop',   'Desktop'),
            ('startmenu', 'Start Menu (Programs)'),
        ]
        both_label = 'Desktop and Start Menu'
    elif sys.platform == 'darwin':
        opts = [
            ('desktop',      'Desktop'),
            ('applications', 'Applications folder (/Applications)'),
        ]
        both_label = 'Desktop and Applications'
    else:
        opts = [
            ('desktop', 'Desktop (~/Desktop)'),
            ('appmenu', 'Applications Menu (~/.local/share/applications)'),
        ]
        both_label = 'Desktop and Applications Menu'
    return opts, both_label


def interactive():
    """Prompt the user to choose shortcut locations, then create them.

    Returns (created, failed) lists (empty if skipped).
    """
    opts, both_label = _platform_menu()

    print()
    print('=== GPI Shortcut Setup ===')
    print('Where would you like to create a GPI shortcut?\n')
    for i, (_, desc) in enumerate(opts, 1):
        print(f'  {i} - {desc}')
    print(f'  {len(opts) + 1} - Both {both_label}  [recommended]')
    print(f'  {len(opts) + 2} - Skip')
    print()

    both_choice = len(opts) + 1
    skip_choice = len(opts) + 2
    default = str(both_choice)

    while True:
        try:
            raw = input(f'Choice [{default}]: ').strip()
        except (EOFError, KeyboardInterrupt):
            print('\nSkipping shortcut creation.')
            return [], []
        if raw == '':
            raw = default
        if raw.isdigit():
            n = int(raw)
            if 1 <= n <= len(opts):
                chosen = [opts[n - 1][0]]
                break
            elif n == both_choice:
                chosen = [k for k, _ in opts]
                break
            elif n == skip_choice:
                print('Skipping shortcut creation.')
                return [], []
        print(f'  Please enter a number between 1 and {skip_choice}.')

    created, failed = install(chosen)

    if created:
        print(f'GPI shortcut created in: {", ".join(created)}')
        if sys.platform == 'win32':
            print("Tip: right-click the Desktop shortcut → 'Pin to taskbar' to add it there.")
    if failed:
        print(f'Warning: could not create shortcut in: {", ".join(failed)}')
    return created, failed


def main():
    """CLI entry point.

    gpi_shortcut                 — silently create shortcuts in all locations
    gpi_shortcut --interactive   — prompt for location choice
    """
    if '--interactive' in sys.argv:
        interactive()
        return

    created, failed = install()
    if created:
        print(f'GPI shortcut created in: {", ".join(created)}')
        if sys.platform == 'win32':
            print("Tip: right-click the shortcut → 'Pin to taskbar' to add it there.")
    if failed:
        print(f'Warning: could not create shortcut in: {", ".join(failed)}')
    if not created and not failed:
        print('No shortcut locations found.')


if __name__ == '__main__':
    main()
