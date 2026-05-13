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
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, collect_all
import os

block_cipher = None

binaries = []
datas = []
hiddenimports = []

# 资源文件（QSS、图标）
datas += [("app/resources/style.qss", "app/resources")]
if os.path.exists("app/resources/icon.ico"):
    datas += [("app/resources/icon.ico", "app/resources")]

# faster_whisper 自带的 silero VAD 模型等 assets（VAD 启用时必须存在）
datas += collect_data_files("faster_whisper")

# 本地 import 探测确认的完整运行时闭包。带原生 DLL / C 扩展的包必须 collect_all。
# 注意：onnxruntime 交给 pyinstaller-hooks-contrib 的官方 hook（会自动生效），
# 我们不再重复 collect_all 避免 DLL 被拷到两个路径触发 DllMain 冲突。
for pkg in (
    "av",              # PyAV：解码音频，带 FFmpeg DLL
    "ctranslate2",     # 推理后端，带 ctranslate2.dll / cublas 等
    "tokenizers",      # Rust 扩展
    "huggingface_hub",
    "requests",
):
    _d, _b, _h = collect_all(pkg)
    datas += _d
    binaries += _b
    hiddenimports += _h

# NVIDIA CUDA 12 runtime DLL（仅 Windows）：ctranslate2 4.4 运行时依赖
# cublas / cublasLt / cudart / cudnn_*_8 等硬编码名的 DLL。这些 DLL 散落在
# 不同的 nvidia-*-cu12 pip 包里，每个包的目录结构都是 site-packages/nvidia/<name>/bin/*.dll。
# 一次性遍历 site-packages/nvidia/ 下所有 bin/ 子目录，把 .dll 扁平到 _internal/。
try:
    import importlib.util
    import glob as _glob
    spec_nvidia = importlib.util.find_spec("nvidia")
    if spec_nvidia and spec_nvidia.submodule_search_locations:
        nvidia_root = spec_nvidia.submodule_search_locations[0]
        for _dll in _glob.glob(os.path.join(nvidia_root, "*", "bin", "*.dll")):
            binaries.append((_dll, "."))
except Exception:
    pass

# 纯 Python 的 HTTP 链路 + hub 常见懒加载依赖
hiddenimports += [
    "certifi",
    "charset_normalizer",
    "idna",
    "urllib3",
    "filelock",
    "fsspec",
    "packaging",
    "tqdm",
    "yaml",
]
# certifi 的 cacert.pem 必须带
datas += collect_data_files("certifi")

a = Analysis(
    ["app/main.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=["rthooks/rt_onnx_dll.py"],
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
    console=True,  # 临时诊断：让 ctranslate2/CUDA 在 abort 前写到 stderr 的错误能显示到控制台。定位完改回 False。
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
