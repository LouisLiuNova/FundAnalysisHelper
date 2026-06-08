import pytest
from app.core.config import load_config


def test_load_config_从yaml读取配置():
    """验证从 config.yaml 正确加载 LLM、MongoDB、Redis、Tushare 配置"""
    config = load_config()

    assert config.llm.base_url == "https://api.deepseek.com/v1"
    assert config.llm.api_key == "sk-test-key"
    assert config.llm.analyst_model == "deepseek-v4-pro[1m]"
    assert config.tushare.token == "test-token"
