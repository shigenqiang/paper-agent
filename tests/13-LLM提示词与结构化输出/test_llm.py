"""模块13 LLM提示词与结构化输出 — 真实 API 调用

前置条件:
    - ANTHROPIC_AUTH_TOKEN 或 OPENAI_API_KEY 已配置
"""

import os
import pytest
from pydantic import BaseModel

from src.agents_v3.research_workspace.llm.service import LLMService


HAS_LLM_KEY = bool(os.environ.get("ANTHROPIC_AUTH_TOKEN") or os.environ.get("OPENAI_API_KEY"))


class AnswerSchema(BaseModel):
    answer: str


@pytest.mark.skipif(not HAS_LLM_KEY, reason="未配置 LLM API Key")
class TestLLMServiceE2E:
    """LLMService 真实链路测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.service = LLMService()

    def test_invoke_returns_text(self):
        """invoke 应返回文本"""
        result = self.service.invoke("你是一个助手", "说一个字：好")
        assert result
        assert isinstance(result, str)
        print(f"\n[llm] 返回: {result[:50]}...")

    def test_invoke_structured_returns_dict(self):
        """invoke_structured 应返回字典"""
        result = self.service.invoke_structured(
            "你是一个助手，用JSON回答，格式: {\"answer\": \"...\"}",
            "1+1等于几？",
            schema=AnswerSchema,
        )
        assert isinstance(result, dict)
        assert result.get("success") is True or "answer" in result
        print(f"\n[llm] structured: {result}")

    def test_invoke_handles_long_prompt(self):
        """长 prompt 不应超时"""
        long_prompt = "请重复以下内容：" + "测试" * 500
        result = self.service.invoke("你是一个助手", long_prompt)
        assert result
