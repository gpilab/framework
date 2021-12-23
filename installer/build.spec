# -*- mode: python ; coding: utf-8 -*-


block_cipher = None


a = Analysis(['gpi_launch.py'],
             pathex=[],
             binaries=[],
             datas=[('framework/lib', '.')],
             hiddenimports=['gpi', 'gpi_core', 'framework/lib/', 'scipy.ndimage', 'cProfile', 'pyqtgraph', 'scipy.interpolate', 'scipy.integrate', 'qtpy.QtOpenGL', 'OpenGL', 'OpenGL.GL', 'OpenGL.GLU', 'OpenGL.GLUT', 'qtpy.QtOpenGL.QGLWidget', 'scipy.io', 'scipy.io.wavfile',  'qtpy', 'qtpy.QtCore', 'qtpy.QtGui', 'qtpy.QtWidgets', 'qtpy.QtMultimedia', 'psutil', 'json', 'configparser', 'imp', 'multiprocessing', 'altgraph', 'cached', 'certifi', 'click', 'cx', 'cycler', 'h5py', 'importlib', 'kiwisolver', 'macholib', 'matplotlib', 'numpy', 'Pillow', 'psutil', 'pyinstaller', 'pyinstaller', 'PyOpenGL', 'pyparsing', 'pyqtgraph', 'python', 'python', 'qimage2ndarray', 'qt5', 'qt5', 'QtPy', 'scipy', 'six', 'typing', 'zipp'],
             hookspath=[],
             hooksconfig={},
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)

exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,  
          [],
          name='GPI',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=False,
          disable_windowed_traceback=False,
          target_arch=None,
          codesign_identity=None,
          entitlements_file=None )
app = BUNDLE(exe,
             name='GPI.app',
             icon='framework/lib/gpi/graphics/gpi.icns',
             bundle_identifier=None)

import sys, os, shelve

import plistlib
from pathlib import Path
app_path = Path(app.name)


# make it executable
os.system(app_path  / 'Contents/MacOS/GPI')