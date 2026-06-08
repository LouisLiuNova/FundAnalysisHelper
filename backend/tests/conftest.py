import os
import pytest


@pytest.fixture(autouse=True)
def set_test_env():
    """测试时设置默认环境变量"""
    os.environ.setdefault("LLM_API_KEY", "sk-test-key")
    os.environ.setdefault("TUSHARE_TOKEN", "test-token")
