"""全局配置加载 — 从 config.yaml 读取配置"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from loguru import logger

_config: dict[str, Any] | None = None


def load_config() -> dict[str, Any]:
    """加载 config.yaml，单例模式"""
    global _config
    if _config is not None:
        return _config

    config_path = Path("config.yaml")
    if config_path.exists():
        try:
            with open(config_path, encoding="utf-8") as f:
                _config = yaml.safe_load(f) or {}
        except Exception as e:
            logger.warning(f"Failed to load config.yaml: {e}")
            _config = {}
    else:
        _config = {}

    return _config


def get_search_config() -> dict[str, Any]:
    """获取搜索排序配置"""
    config = load_config()
    return config.get("search", {})


def reset_config():
    """重置配置（测试用）"""
    global _config
    _config = None
