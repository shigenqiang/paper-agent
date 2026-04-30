"""
ConfigManager - 配置管理

提供配置的集中管理、动态更新和环境变量覆盖支持
"""
from typing import Any, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime
import yaml
import os
import copy


@dataclass
class ConfigChange:
    """配置变更记录"""
    key: str
    old_value: Any
    new_value: Any
    timestamp: datetime
    changed_by: str = "system"


class ConfigManager:
    """配置管理器"""

    # 默认配置
    DEFAULTS = {
        "log_level": "INFO",
        "llm.provider": "openai",
        "llm.model_name": "minimax",
        "llm.temperature": 0.7,
        "llm.max_tokens": 4096,
        "cache.enabled": True,
        "cache.ttl": 3600,
        "cache.max_entries": 1000,
        "rate_limit.enabled": True,
        "rate_limit.max_requests": 100,
        "rate_limit.window_seconds": 60,
        "security.sanitize_input": True,
        "security.allow_html": False,
        "security.max_input_length": 10000,
        "agent.max_concurrent": 10,
        "agent.timeout": 300,
        "agent.retry_attempts": 3
    }

    def __init__(self, config_file: str = "config.yaml"):
        self.config_file = config_file
        self.config: Dict = {}
        self.change_history: list[ConfigChange] = []
        self._load_config()

    def _load_config(self):
        """从文件加载配置"""
        self.config = copy.deepcopy(self.DEFAULTS)

        # 从环境变量覆盖
        self._load_from_env()

        # 从文件加载
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    file_config = yaml.safe_load(f) or {}
                    self._merge_config(self.config, file_config)
            except Exception as e:
                print(f"Warning: Failed to load config from {self.config_file}: {e}")

    def _load_from_env(self):
        """从环境变量加载配置"""
        env_mappings = {
            "OPENAI_API_KEY": ("llm", "api_key"),
            "LOG_LEVEL": ("log_level", None),
            "API_KEY": ("security", "api_key"),
            "CACHE_ENABLED": ("cache", "enabled"),
            "CACHE_TTL": ("cache", "ttl"),
            "MAX_CONCURRENT": ("agent", "max_concurrent"),
            "AGENT_TIMEOUT": ("agent", "timeout"),
        }

        for env_var, config_path in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                if len(config_path) == 1:
                    self.config[config_path[0]] = self._convert_value(value)
                else:
                    section, key = config_path
                    if section not in self.config:
                        self.config[section] = {}
                    self.config[section][key] = self._convert_value(value)

    def _convert_value(self, value: str) -> Any:
        """转换环境变量值为适当类型"""
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        try:
            return int(value)
        except ValueError:
            try:
                return float(value)
            except ValueError:
                return value

    def _merge_config(self, target: Dict, source: Dict):
        """递归合并配置"""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._merge_config(target[key], value)
            else:
                target[key] = value

    async def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值

        支持点号分隔的嵌套键，如 "llm.provider"
        """
        keys = key.split('.')
        value = self.config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    async def set(self, key: str, value: Any, changed_by: str = "api"):
        """设置配置值"""
        old_value = await self.get(key)

        keys = key.split('.')
        config = self.config

        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value

        # 记录变更
        change = ConfigChange(
            key=key,
            old_value=old_value,
            new_value=value,
            timestamp=datetime.now(),
            changed_by=changed_by
        )
        self.change_history.append(change)

    async def get_section(self, section: str) -> Optional[Dict]:
        """获取配置节"""
        return self.config.get(section)

    async def set_section(self, section: str, values: Dict, changed_by: str = "api"):
        """设置配置节"""
        old_values = self.config.get(section, {})
        self.config[section] = values

        # 记录变更
        change = ConfigChange(
            key=f"{section}",
            old_value=old_values,
            new_value=values,
            timestamp=datetime.now(),
            changed_by=changed_by
        )
        self.change_history.append(change)

    async def reload(self):
        """重新加载配置"""
        self.change_history.clear()
        self._load_config()

    async def save(self):
        """保存配置到文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, default_flow_style=False, allow_unicode=True)
            return True
        except Exception as e:
            print(f"Error: Failed to save config to {self.config_file}: {e}")
            return False

    async def export(self) -> Dict:
        """导出当前配置"""
        return copy.deepcopy(self.config)

    async def reset(self, key: Optional[str] = None):
        """重置配置到默认值"""
        if key is None:
            self.config = copy.deepcopy(self.DEFAULTS)
            self.change_history.clear()
        else:
            default_value = self.DEFAULTS.get(key)
            if default_value is not None:
                await self.set(key, default_value, changed_by="reset")

    async def get_change_history(self, limit: int = 50) -> list:
        """获取配置变更历史"""
        return self.change_history[-limit:]

    async def validate(self) -> Dict[str, Any]:
        """验证配置有效性"""
        issues = []

        # 检查必需的配置
        required_keys = ["llm.provider", "llm.model_name"]
        for key in required_keys:
            value = await self.get(key)
            if value is None:
                issues.append(f"Missing required configuration: {key}")

        # 检查值范围
        temperature = await self.get("llm.temperature")
        if temperature is not None and (temperature < 0 or temperature > 2):
            issues.append("llm.temperature should be between 0 and 2")

        max_tokens = await self.get("llm.max_tokens")
        if max_tokens is not None and max_tokens < 100:
            issues.append("llm.max_tokens should be at least 100")

        return {
            "valid": len(issues) == 0,
            "issues": issues
        }

    def get_defaults(self) -> Dict:
        """获取默认配置"""
        return copy.deepcopy(self.DEFAULTS)


# 全局配置管理器实例
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """获取全局配置管理器"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager
