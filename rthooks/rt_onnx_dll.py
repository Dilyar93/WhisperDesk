"""Runtime hook: 修 onnxruntime 在 PyInstaller 冻结环境下的 DLL 搜索路径。

问题：
  onnxruntime 的 C 扩展 `onnxruntime/capi/onnxruntime_pybind11_state.pyd`
  运行时要加载一堆 sibling DLL（onnxruntime_providers_shared.dll、
  DirectML.dll、可能的 VC++ runtime 等）。PyInstaller 可能把这些 DLL
  扁平化到 `_internal/` 根目录，也可能留在 `_internal/onnxruntime/capi/`。
  Windows 的 DLL 搜索策略不一定两个都覆盖到，于是 `.pyd` 加载失败、
  最终表现为 `ImportError: DLL load failed while importing
  onnxruntime_pybind11_state`，被 faster_whisper 包装成
  `Applying the VAD filter requires the onnxruntime package`。

修复：
  在 onnxruntime 被 import 前，把 `_internal/` 根目录 和
  `_internal/onnxruntime/capi/` 都加进 DLL 搜索路径。
"""
import os
import sys


def _add_dll_dirs() -> None:
    if not sys.platform.startswith("win"):
        return
    add = getattr(os, "add_dll_directory", None)
    if add is None:
        return

    base = getattr(sys, "_MEIPASS", None)
    if not base:
        return

    candidates = [
        base,
        os.path.join(base, "onnxruntime", "capi"),
        os.path.join(base, "ctranslate2"),
    ]
    for p in candidates:
        if os.path.isdir(p):
            try:
                add(p)
            except (OSError, FileNotFoundError):
                pass
    # 同步 PATH，确保老式 LoadLibrary 搜索也能命中
    os.environ["PATH"] = os.pathsep.join(
        [p for p in candidates if os.path.isdir(p)] + [os.environ.get("PATH", "")]
    )


_add_dll_dirs()
