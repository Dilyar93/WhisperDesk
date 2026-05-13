# -*- mode: python ; coding: utf-8 -*-
"""WhisperDesk PyInstaller spec. One-folder Windows build.

依赖收集交给 pyinstaller-hooks-contrib 的官方 hook（ctranslate2 / tokenizers /
huggingface_hub 等），本 spec 只负责：
  1) 带上 app/resources 的 qss / icon；
  2) 带上 faster_whisper 包内的 silero VAD 资源；
  3) 用 hiddenimports 告知静态分析器跟踪这些包。

根因备忘：`cannot load module more than once per process` 是 numpy 2.x +
PyInstaller < 6.11.1 的已知 bug。处理办法是：
  - requirements.txt 钉 numpy<2；
  - requirements-build.txt 要求 pyinstaller>=6.11.1。
"""
from PyInstaller.utils.hooks import collect_data_files, collect_submodules
import os

block_cipher = None

binaries = []
datas = []

# 资源文件（QSS、图标）
datas += [("app/resources/style.qss", "app/resources")]
if os.path.exists("app/resources/icon.ico"):
    datas += [("app/resources/icon.ico", "app/resources")]

# faster_whisper 自带的 silero VAD 模型等 assets（VAD 启用时必须存在）
datas += collect_data_files("faster_whisper")

# huggingface_hub 会动态 import requests / urllib3 / certifi / charset_normalizer 等，
# PyInstaller 静态分析跟不到，需要整包 submodules + 显式 hiddenimports 兜底。
hiddenimports = [
    "ctranslate2",
    "tokenizers",
    "requests",
    "urllib3",
    "certifi",
    "charset_normalizer",
    "idna",
    "filelock",
    "fsspec",
    "packaging",
    "tqdm",
    "pyyaml",
]
hiddenimports += collect_submodules("huggingface_hub")
hiddenimports += collect_submodules("requests")

# requests / certifi 需要带上 CA 证书等 data files
datas += collect_data_files("certifi")
datas += collect_data_files("huggingface_hub")

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
