"""LLM 服务封装 - 增强版"""

from __future__ import annotations

import json
import os
import time
import uuid
from typing import Any

from loguru import logger
from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    provider: str = "openai"
    model_name: str = ""
    temperature: float = 0.2
    max_tokens: int = 4096
    timeout: float = 60.0
    max_retries: int = 2
    retry_backoff_seconds: float = 1.0
    api_key: str | None = None
    base_url: str | None = None
    seed: int | None = None
    extra: dict[str, Any] = Field(default_factory=dict)

    def model_post_init(self, __context: Any) -> None:
        if not self.model_name:
            from dotenv import load_dotenv
            load_dotenv()
            self.model_name = os.environ.get("LLM_MODEL", "mimo-v2.5-pro")


class LLMCallResult(BaseModel):
    success: bool
    content: str = ""
    model: str = ""
    provider: str = ""
    latency_ms: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    retry_count: int = 0
    status: str = "success"
    error_type: str = ""
    error_message: str = ""
    request_id: str = ""
    prompt_name: str = ""
    prompt_version: str = ""
    prompt_hash: str = ""
    response_hash: str = ""


class LLMService:
    def __init__(self, config: LLMConfig | None = None):
        self.config = config or LLMConfig()
        self._llm = None

    @property
    def llm(self):
        if self._llm is None:
            self._llm = self._create_llm()
        return self._llm

    def _create_llm(self):
        from dotenv import load_dotenv
        load_dotenv()

        config = self.config
        api_key = config.api_key or os.environ.get("OPENAI_API_KEY", "")
        base_url = config.base_url or os.environ.get("OPENAI_BASE_URL", "")

        # httpx 默认传输层重试会导致 SSL 握手挂起，需要禁用
        import httpx
        http_client = httpx.Client(
            transport=httpx.HTTPTransport(retries=0),
            timeout=config.timeout,
        )

        if config.provider == "openai":
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model=config.model_name, temperature=config.temperature,
                max_tokens=config.max_tokens, api_key=api_key,
                base_url=base_url if base_url else None,
                timeout=config.timeout, max_retries=config.max_retries,
                http_client=http_client,
            )
        elif config.provider == "anthropic":
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(
                model=config.model_name, temperature=config.temperature,
                max_tokens=config.max_tokens, api_key=api_key,
                timeout=config.timeout, max_retries=config.max_retries,
                http_client=http_client,
            )
        else:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model=config.model_name, temperature=config.temperature,
                max_tokens=config.max_tokens, api_key=api_key,
                base_url=base_url if base_url else None,
                timeout=config.timeout, max_retries=config.max_retries,
                http_client=http_client,
            )

    def invoke(self, system_prompt: str, user_prompt: str) -> str:
        from langchain_core.messages import HumanMessage, SystemMessage
        messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
        try:
            response = self.llm.invoke(messages)
            return response.content
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise

    def invoke_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        from src.agents_v3.research_workspace.llm.json_utils import extract_json
        response = self.invoke(system_prompt, user_prompt)
        try:
            return extract_json(response)
        except Exception as e:
            logger.warning(f"Failed to parse JSON from LLM response: {str(e)}")
            return {"raw_response": response}

    def invoke_structured(
        self, system_prompt: str, user_prompt: str, schema: type,
        prompt_name: str = "", prompt_version: str = "", repair: bool = True,
    ) -> dict[str, Any]:
        from src.agents_v3.research_workspace.llm.json_utils import extract_json, repair_json_with_llm
        from src.agents_v3.research_workspace.llm.logging import hash_text, log_llm_call

        request_id = f"req_{uuid.uuid4().hex[:8]}"
        start_time = time.time()

        try:
            response = self.invoke(system_prompt, user_prompt)
            latency_ms = int((time.time() - start_time) * 1000)

            try:
                parsed = extract_json(response)
            except Exception as e:
                log_llm_call(prompt_name=prompt_name, prompt_version=prompt_version,
                    model=self.config.model_name, success=False, latency_ms=latency_ms,
                    error_type="parse_failed", error_message=str(e))
                return {"success": False, "raw_response": response, "error_type": "parse_failed",
                        "error_message": str(e), "request_id": request_id, "latency_ms": latency_ms}

            try:
                validated = schema(**parsed) if isinstance(parsed, dict) else parsed
                log_llm_call(prompt_name=prompt_name, prompt_version=prompt_version,
                    model=self.config.model_name, success=True, latency_ms=latency_ms,
                    prompt_hash=hash_text(system_prompt + user_prompt), response_hash=hash_text(response))
                try:
                    from src.agents_v3.research_workspace.evaluation.metrics import get_metrics_collector
                    get_metrics_collector().record(
                        "llm_latency_ms", latency_ms, unit="ms", service="llm",
                        operation=prompt_name, tags={"model": self.config.model_name},
                    )
                except Exception:
                    pass
                return {"success": True, "data": validated.model_dump() if hasattr(validated, "model_dump") else validated,
                        "raw_response": response, "request_id": request_id, "latency_ms": latency_ms}
            except Exception as validation_error:
                if repair:
                    repaired = repair_json_with_llm(response, [str(validation_error)], self.invoke)
                    if repaired:
                        try:
                            validated = schema(**repaired)
                            log_llm_call(prompt_name=prompt_name, prompt_version=prompt_version,
                                model=self.config.model_name, success=True, latency_ms=latency_ms)
                            return {"success": True, "data": validated.model_dump() if hasattr(validated, "model_dump") else validated,
                                    "raw_response": response, "repaired": True, "request_id": request_id, "latency_ms": latency_ms}
                        except Exception:
                            pass

                log_llm_call(prompt_name=prompt_name, prompt_version=prompt_version,
                    model=self.config.model_name, success=False, latency_ms=latency_ms,
                    error_type="schema_failed", error_message=str(validation_error))
                return {"success": False, "raw_response": response, "error_type": "schema_failed",
                        "error_message": str(validation_error), "request_id": request_id, "latency_ms": latency_ms}

        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            error_type = "timeout" if "timeout" in str(e).lower() else "provider_error"
            log_llm_call(prompt_name=prompt_name, prompt_version=prompt_version,
                model=self.config.model_name, success=False, latency_ms=latency_ms,
                error_type=error_type, error_message=str(e))
            return {"success": False, "error_type": error_type, "error_message": str(e),
                    "request_id": request_id, "latency_ms": latency_ms}


class FakeLLMService(LLMService):
    def __init__(self, responses: dict[str, Any] | None = None):
        self._responses = responses or {}
        self._default_response = '{"answer": "test answer", "confidence": 0.5}'
        self.call_count = 0
        self.last_system_prompt = ""
        self.last_user_prompt = ""
        self.config = LLMConfig()
        self._llm = None

    @property
    def llm(self):
        return self

    def invoke(self, system_prompt: str, user_prompt: str) -> str:
        self.call_count += 1
        self.last_system_prompt = system_prompt
        self.last_user_prompt = user_prompt
        return self._default_response

    def _create_llm(self):
        return self

    def set_response(self, key: str, response: Any):
        self._responses[key] = response

    def set_default_response(self, response: str):
        self._default_response = response


_llm_service: LLMService | None = None


def get_llm_service(config: LLMConfig | None = None) -> LLMService:
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService(config)
    return _llm_service


def reset_llm_service():
    global _llm_service
    _llm_service = None
