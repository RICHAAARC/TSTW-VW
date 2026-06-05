"""
文件用途：为仓库内直接执行的 pytest 命令关闭第三方插件自动加载。
File purpose: Disable third-party pytest plugin autoload for direct test invocations in this repository.
Module type: General module
"""

from __future__ import annotations

import os
import sys


# 中文注释：用户直接执行 `pytest ...` 时，外部环境中的自动加载插件会显著拖慢
# 甚至阻断阶段 1 rebuild 测试；这里在解释器启动期固定关闭自动加载，确保仓库内
# `pytest` 与 `python -m pytest` 口径一致。
os.environ.setdefault("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")

# 中文注释：仓库脚本经常读写 Markdown、JSON、notebook 与审计报告。
# Windows 终端默认代码页可能不是 UTF-8，因此这里为当前解释器和它启动的
# 子进程固定 UTF-8 I/O 口径，避免中文注释在 notebook 或配置文件中被替换成问号。
os.environ.setdefault("PYTHONUTF8", "1")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")
