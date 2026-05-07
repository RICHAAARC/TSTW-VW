"""
文件用途：为仓库内直接执行的 pytest 命令关闭第三方插件自动加载。
File purpose: Disable third-party pytest plugin autoload for direct test invocations in this repository.
Module type: General module
"""

from __future__ import annotations

import os


# 中文注释：用户直接执行 `pytest ...` 时，外部环境中的自动加载插件会显著拖慢
# 甚至阻断阶段 1 rebuild 测试；这里在解释器启动期固定关闭自动加载，确保仓库内
# `pytest` 与 `python -m pytest` 口径一致。
os.environ.setdefault("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")