# -*- mode: python -*-
"""
PyInstaller build for the Bigraph Cryptography System

Build on each operating system for that system (with requirements-dev.txt
installed):
    pyinstaller packaging/bigraph.spec --distpath dist --workpath build --noconfirm

Produces the folder dist/Bigraph (Windows and Linux, with Bigraph.exe or
Bigraph inside), or dist/Bigraph.app (macOS). The installers in
packaging/windows and packaging/linux are built from the folder.
"""

import os
import sys

from PyInstaller.utils.hooks import collect_submodules, copy_metadata

root = os.path.abspath(os.path.join(SPECPATH, '..'))
sys.path.insert(0, os.path.join(root, 'src'))

# keyring finds its OS key store backends when the program runs, so include
# all of them, with the package metadata it uses to find them
hiddenimports = (collect_submodules('keyring.backends')
                 + collect_submodules('bigraph', filter=lambda name: True)
                 + collect_submodules('gui'))
datas = copy_metadata('keyring')

# Some Python builds (such as the standalone builds uv installs) keep the
# Tcl/Tk libraries next to Python and load them through a relative path that
# PyInstaller's dependency scan does not follow, so add them directly
binaries = []
if sys.platform.startswith('linux'):
    import glob
    lib = os.path.join(sys.base_prefix, 'lib')
    for pattern in ('libtcl*.so*', 'libtk*.so*', 'libtcl*tk*.so*'):
        for path in glob.glob(os.path.join(lib, pattern)):
            if (path, '.') not in binaries:
                binaries.append((path, '.'))

a = Analysis(
    [os.path.join(root, 'main.py')],
    pathex=[os.path.join(root, 'src')],
    binaries=binaries,
    hiddenimports=hiddenimports,
    datas=datas,
    excludes=['pytest', 'numpy', 'PyInstaller'],
    noarchive=False,
)
pyz = PYZ(a.pure)

if sys.platform == 'darwin':
    # A folder-based app bundle, as macOS expects
    exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='Bigraph',
              console=False, argv_emulation=False)
    coll = COLLECT(exe, a.binaries, a.datas, name='Bigraph')
    app = BUNDLE(coll, name='Bigraph.app', bundle_identifier='org.bigraph.app',
                 info_plist={'NSHighResolutionCapable': True})
else:
    # A folder with the executable, as installers expect; it also starts
    # faster than a single file, which unpacks itself on every launch
    icon = os.path.join(SPECPATH, 'icons', 'bigraph.ico') if sys.platform == 'win32' else None
    exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='Bigraph',
              console=False, upx=False, icon=icon)
    coll = COLLECT(exe, a.binaries, a.datas, name='Bigraph', upx=False)
