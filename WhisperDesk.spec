# -*- mode: python ; coding: utf-8 -*-
"""WhisperDesk PyInstaller spec. One-folder Windows build.

DLL 收集通过本仓库 `hooks/hook-ctranslate2.py` 覆盖 pyinstaller-hooks-contrib
的默认行为：只收 .dll，过滤掉 .pyd（.pyd 留在 ctranslate2 包目录里，避免
pybind11 因同一扩展被加载到两个路径而报
`cannot load module more than once per process`）。
"""
from PyInstaller.utils.hooks import collect_data_files
import os

block_cipher = None

binaries = []
datas = []

# 资源文件（QSS、图标）
datas += [("app/resources/style.qss", "app/resources")]
if os.path.exists("app/resources/icon.ico"):
    datas += [("app/resources/icon.ico", "app/resources")]

# faster_whisper 自带的 silero VAD 模型等 assets（必须打包，否则 VAD 启用时报错）
datas += collect_data_files("faster_whisper")

# 声明为依赖，让静态分析跟踪到；真正的 DLL 由自定义 hook 处理
hiddenimports = [
    "ctranslate2",
    "tokenizers",
]

a = Analysis(
    ["app/main.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=["hooks"],
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
