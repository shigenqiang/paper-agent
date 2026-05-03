"""
配置管理
"""
from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from src.agents_v2.config import LLMConfig


@dataclass
class PhaseConfig:
    """阶段配置"""
    phase_name: str
    llm_config: Optional["LLMConfig"] = None
    quality_threshold: float = 0.7
    max_iterations: int = 3

    def __post_init__(self):
        if self.llm_config is None:
            from src.agents_v2.config import LLMConfig
            import os
            api_key = os.getenv("OPENAI_API_KEY", "")
            base_url = os.getenv("OPENAI_BASE_URL", "https://api.minimax.chat/v1")
            model_name = os.getenv("LLM_MODEL", "MiniMax-M2.7")
            self.llm_config = LLMConfig(
                provider="openai",
                model_name=model_name,
                api_key=api_key,
                base_url=base_url,
                temperature=0.7,
                max_tokens=4096
            )
