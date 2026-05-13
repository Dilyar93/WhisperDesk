# -*- mode: python ; coding: utf-8 -*-
"""WhisperDesk PyInstaller spec. One-folder Windows build."""
from PyInstaller.utils.hooks import collect_dynamic_libs, collect_submodules, collect_data_files
import os

block_cipher = None

# ctranslate2 的 CUDA / cuDNN / MKL DLLs 在 wheel 内；显式收集防止 hook 漏
binaries = []
binaries += collect_dynamic_libs("ctranslate2")
# tokenizers 也带 rust 动态库
binaries += collect_dynamic_libs("tokenizers")

# 资源文件（QSS、图标）
datas = []
datas += [("app/resources/style.qss", "app/resources")]
if os.path.exists("app/resources/icon.ico"):
    datas += [("app/resources/icon.ico", "app/resources")]

# faster_whisper 自带的 silero VAD 模型（assets/silero_vad.onnx）必须打包
datas += collect_data_files("faster_whisper")

hiddenimports = []
hiddenimports += collect_submodules("ctranslate2")

a = Analysis(
    ["app/main.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "unittest", "test"],
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
    name="WhisperDesk",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="app/resources/icon.ico" if os.path.exists("app/resources/icon.ico") else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="WhisperDesk",
)
