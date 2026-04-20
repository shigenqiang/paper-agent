"""配置加载器测试"""
import pytest
from src.core.config import ConfigLoader


def test_config_loader():
    """测试配置加载器"""
    loader = ConfigLoader("config")

    # 测试加载主配置
    config = loader.load("config")
    assert "llm" in config
    assert "storage" in config
    assert "agents" in config

    # 测试获取特定值
    llm_model = loader.get("config", "llm.model")
    assert llm_model is not None


def test_env_substitution():
    """测试环境变量替换"""
    loader = ConfigLoader("config")

    # 测试环境变量替换
    api_key = loader.get("config", "llm.api_key")
    # 如果环境变量未设置，应该返回原始字符串
    assert api_key is not None
