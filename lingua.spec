# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# In a spec file, __file__ might not be defined. Use SPECPATH instead.
project_root = SPECPATH
lingua_dir = os.path.join(project_root, 'lingua')

block_cipher = None

a = Analysis(
    [os.path.join(lingua_dir, '__main__.py')],
    pathex=[project_root],
    binaries=[],
    datas=[
        (os.path.join(lingua_dir, 'resources'), 'lingua/resources'),
        (os.path.join(lingua_dir, 'ui/resources'), 'lingua/ui/resources'),
    ] + collect_data_files('PySide6'),
    hiddenimports=collect_submodules('PySide6') + [
        'httpx',
        'ebooklib',
        'lxml',
        'appdirs',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'PySide6.QtWebEngineCore',
        'PySide6.QtWebEngineWidgets',
        'PySide6.QtWebEngine',
        'PySide6.Qt3DCore',
        'PySide6.Qt3DRender',
        'PySide6.Qt3DInput',
        'PySide6.Qt3DLogic',
        'PySide6.Qt3DExtras',
        'PySide6.Qt3DAnimation',
        'PySide6.QtQuick',
        'PySide6.QtQuickWidgets',
        'PySide6.QtQml',
        'PySide6.QtVirtualKeyboard',
        'PySide6.QtSql',
        'PySide6.QtTest',
        'PySide6.QtMultimedia',
        'PySide6.QtMultimediaWidgets',
        'PySide6.QtPositioning',
        'PySide6.QtWebSockets',
        'PySide6.QtWebChannel',
        'PySide6.QtBluetooth',
        'PySide6.QtNfc',
        'PySide6.QtSensors',
        'PySide6.QtLocation',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Lingua',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=[os.path.join(lingua_dir, 'resources', 'icon.ico')],
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Lingua',
)
