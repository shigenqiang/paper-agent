"""配置加载器"""
import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()


class ConfigLoader:
    """配置加载器"""

    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self._config_cache: Dict[str, Any] = {}

    def load(self, config_name: str) -> Dict[str, Any]:
        """加载配置文件"""
        if config_name in self._config_cache:
            return self._config_cache[config_name]

        config_path = self.config_dir / f"{config_name}.yaml"
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        config = self._substitute_env_vars(config)
        self._config_cache[config_name] = config
        return config

    def _substitute_env_vars(self, config: Any) -> Any:
        """替换配置中的环境变量"""
        if isinstance(config, str):
            if config.startswith("${") and config.endswith("}"):
                env_var = config[2:-1]
                return os.getenv(env_var, config)
            return config
        elif isinstance(config, dict):
            return {k: self._substitute_env_vars(v) for k, v in config.items()}
        elif isinstance(config, list):
            return [self._substitute_env_vars(item) for item in config]
        return config

    def get(self, config_name: str, key: str, default: Any = None) -> Any:
        """获取配置中的特定值"""
        config = self.load(config_name)
        keys = key.split('.')
        value = config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value


# 全局配置加载器实例
config_loader = ConfigLoader()
