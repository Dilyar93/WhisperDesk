# -*- mode: python ; coding: utf-8 -*-
"""WhisperDesk PyInstaller spec. One-folder Windows build."""
from PyInstaller.utils.hooks import collect_all, collect_data_files
import os

block_cipher = None

# 用 collect_all 统一收集 ctranslate2（DLL + Python 模块 + 数据）到同一位置，
# 避免因 collect_dynamic_libs + collect_submodules 组合导致 DLL 被复制到多处，
# 从而触发 ctranslate2 启动时 "cannot load module more than once per process"。
ct2_datas, ct2_binaries, ct2_hiddenimports = collect_all("ctranslate2")
# tokenizers 同样带 rust 动态库，一起用 collect_all 处理
tok_datas, tok_binaries, tok_hiddenimports = collect_all("tokenizers")

binaries = ct2_binaries + tok_binaries

# 资源文件（QSS、图标）
datas = ct2_datas + tok_datas
datas += [("app/resources/style.qss", "app/resources")]
if os.path.exists("app/resources/icon.ico"):
    datas += [("app/resources/icon.ico", "app/resources")]

# faster_whisper 自带的 silero VAD 模型等 assets
datas += collect_data_files("faster_whisper")

hiddenimports = ct2_hiddenimports + tok_hiddenimports

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
