"""LLM 服务模块测试"""

import pytest
import json

from src.agents_v3.research_workspace.llm_service import (
    LLMConfig, LLMCallResult, FakeLLMService,
)
from src.agents_v3.research_workspace.llm_json import extract_json, _try_fix_json
from src.agents_v3.research_workspace.llm_errors import (
    LLMServiceError, JsonExtractionError, StructuredOutputError,
)
from src.agents_v3.research_workspace.llm_logging import redact_text, hash_text
from src.agents_v3.research_workspace.prompt_registry import (
    PromptRegistry, PromptTemplateSpec, get_prompt_registry,
)


# ── LLMConfig ──────────────────────────────────

class TestLLMConfig:
    def test_default_values(self):
        config = LLMConfig()
        assert config.provider == "openai"
        assert config.temperature == 0.2
        assert config.max_tokens == 4096
        assert config.max_retries == 2
        assert config.timeout == 60.0

    def test_custom_values(self):
        config = LLMConfig(model_name="gpt-4", temperature=0.5, max_retries=3)
        assert config.model_name == "gpt-4"
        assert config.temperature == 0.5


# ── LLMCallResult ──────────────────────────────

class TestLLMCallResult:
    def test_success_result(self):
        result = LLMCallResult(success=True, model="gpt-4", latency_ms=500)
        assert result.status == "success"
        assert result.error_type == ""

    def test_error_result(self):
        result = LLMCallResult(success=False, error_type="timeout", error_message="timed out")
        assert result.success is False
        assert result.error_type == "timeout"


# ── JSON 提取 ──────────────────────────────────

class TestJsonExtraction:
    def test_extract_direct_json(self):
        data = extract_json('{"key": "value"}')
        assert data == {"key": "value"}

    def test_extract_from_markdown_block(self):
        text = 'Some text\n```json\n{"key": "value"}\n```\nMore text'
        data = extract_json(text)
        assert data == {"key": "value"}

    def test_extract_from_code_block(self):
        text = '```\n{"key": "value"}\n```'
        data = extract_json(text)
        assert data == {"key": "value"}

    def test_extract_array(self):
        data = extract_json('[1, 2, 3]')
        assert data == [1, 2, 3]

    def test_extract_with_surrounding_text(self):
        text = 'Here is the result: {"answer": "yes"} and more text'
        data = extract_json(text)
        assert data["answer"] == "yes"

    def test_raises_on_empty(self):
        with pytest.raises(JsonExtractionError):
            extract_json("")

    def test_raises_on_no_json(self):
        with pytest.raises(JsonExtractionError):
            extract_json("This is just plain text with no JSON at all.")

    def test_fix_trailing_comma(self):
        fixed = _try_fix_json('{"a": 1, "b": 2,}')
        assert fixed == {"a": 1, "b": 2}


# ── 日志脱敏 ──────────────────────────────────

class TestLogging:
    def test_redact_truncates(self):
        text = "a" * 500
        assert len(redact_text(text, max_length=100)) <= 150  # some tolerance

    def test_redact_removes_api_key(self):
        text = "Here is my api_key: sk-1234567890"
        redacted = redact_text(text)
        assert "REDACTED" in redacted

    def test_hash_deterministic(self):
        assert hash_text("test") == hash_text("test")

    def test_hash_different_inputs(self):
        assert hash_text("a") != hash_text("b")


# ── PromptRegistry ─────────────────────────────

class TestPromptRegistry:
    def test_get_builtin_prompt(self):
        registry = get_prompt_registry()
        prompt = registry.get("paper_card_extraction")
        assert prompt is not None
        assert prompt.module == "paper_card"

    def test_get_specific_version(self):
        registry = get_prompt_registry()
        prompt = registry.get("scope_qa_answer", "v1")
        assert prompt is not None

    def test_list_all(self):
        registry = get_prompt_registry()
        prompts = registry.list()
        assert len(prompts) >= 4

    def test_list_by_module(self):
        registry = get_prompt_registry()
        prompts = registry.list(module="scope_qa")
        assert all(p.module == "scope_qa" for p in prompts)

    def test_register_custom(self):
        registry = PromptRegistry()
        spec = PromptTemplateSpec(
            name="custom_test", version="v1", module="test",
            system_prompt="test prompt",
        )
        registry.register(spec)
        assert registry.get("custom_test") is not None


# ── FakeLLM ────────────────────────────────────

class TestFakeLLM:
    def test_default_response(self):
        fake = FakeLLMService()
        result = fake.invoke("system", "user")
        assert result  # Returns string

    def test_custom_response(self):
        fake = FakeLLMService()
        fake.set_default_response('{"answer": "custom"}')
        result = fake.invoke("system", "user")
        assert "custom" in result

    def test_invoke_json(self):
        fake = FakeLLMService()
        fake.set_default_response('{"key": "value"}')
        result = fake.invoke_json("system", "user")
        assert result["key"] == "value"


# ── 错误类型 ──────────────────────────────────

class TestErrors:
    def test_base_error(self):
        err = LLMServiceError("test", error_type="test_type")
        assert err.error_type == "test_type"
        assert str(err) == "test"

    def test_json_extraction_error(self):
        err = JsonExtractionError("bad json")
        assert err.error_type == "parse_failed"

    def test_structured_output_error(self):
        err = StructuredOutputError("schema fail", validation_errors=["field missing"])
        assert err.validation_errors == ["field missing"]
