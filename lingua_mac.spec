# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# Spec file for macOS build
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
    excludes=['tkinter'],
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

app = BUNDLE(
    coll,
    name='Lingua.app',
    icon=os.path.join(lingua_dir, 'resources', 'icon.png'), # macOS usually wants .icns, but will try .png
    bundle_identifier='com.manux.lingua',
    info_plist={
        'NSHighResolutionCapable': 'True',
        'LSBackgroundOnly': 'False',
        'CFBundleShortVersionString': '1.1.0',
    },
)
