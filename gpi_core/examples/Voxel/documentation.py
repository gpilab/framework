# Author: Guru Krishanmoorthy
# Date: Nov 2026

from pathlib import Path
import sysconfig
import webbrowser


def open_documentation(log):
    filename = (Path(sysconfig.get_path('purelib')) / 'gpi' / 'include'
                / 'Voxel' / 'voxel_documentation.html')
    if not filename.is_file():
        log.error(f'Voxel documentation not found: {filename}')
        return False
    if not webbrowser.open(filename.as_uri()):
        log.error(f'Cannot open Voxel documentation in the browser: {filename}')
        return False
    return True
