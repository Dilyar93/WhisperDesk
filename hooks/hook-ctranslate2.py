"""覆盖 pyinstaller-hooks-contrib 的默认 hook。

问题：contrib 的 hook-ctranslate2 调用 collect_dynamic_libs，会把包里的 .pyd
（如 ctranslate2._ext.cp311-win_amd64.pyd）也一起扁平化到 _internal/ 根目录，
结果同一份 pybind11 扩展模块同时存在两个路径。pybind11 单阶段初始化检测到
PyInit 被调两次，抛 `cannot load module more than once per process`。

修复：只收集 .dll，过滤掉 .pyd（.pyd 留在 ctranslate2/ 包目录里，由
PyInstaller 的 Python 包收集机制正确处理）。
"""
from PyInstaller.utils.hooks import collect_dynamic_libs, copy_metadata

_all = collect_dynamic_libs("ctranslate2")
binaries = [
    (src, dst) for (src, dst) in _all
    if not str(src).lower().endswith(".pyd")
]
datas = copy_metadata("ctranslate2")
