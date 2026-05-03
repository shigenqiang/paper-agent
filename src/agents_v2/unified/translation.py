"""
Translation Wrapper - 翻译封装

解决MiniMax-M2.7模型中文编码问题：
1. 接收中文输入
2. 翻译为英文供LLM处理
3. 英文处理
4. 可选：翻译回中文

使用方法:
    translator = TranslationWrapper()
    result = await translator.process("中文输入", agent)
"""
from src.agents_v2.logging_config import get_logging_logger

import asyncio
from typing import Any, Dict, Optional, Callable

import os

logger = get_logging_logger(__name__)


class TranslationWrapper:
    """
    翻译封装器 - 提供中英互译能力

    用于解决MiniMax等模型的中文编码问题：
    - 中文输入 → 英文 → LLM处理 → 英文输出 → 中文输出（可选）
    """

    def __init__(self, llm_config: Optional[Any] = None):
        self.llm_config = llm_config
        self._translator_llm = None
        self._init_translator()

    def _init_translator(self):
        """初始化翻译用LLM"""
        try:
            # 尝试加载 .env 文件
            try:
                from dotenv import load_dotenv
                load_dotenv()
            except ImportError:
                pass

            from langchain_openai import ChatOpenAI
            # 优先使用 llm_config 中的配置
            if self.llm_config:
                api_key = getattr(self.llm_config, 'api_key', None) or os.getenv("OPENAI_API_KEY")
                base_url = getattr(self.llm_config, 'base_url', None) or os.getenv("OPENAI_BASE_URL", "https://api.minimax.chat/v1")
                model = getattr(self.llm_config, 'model_name', 'minimax-m2.7')
                self._translator_llm = ChatOpenAI(
                    model=model,
                    temperature=0.3,
                    max_tokens=4096,
                    api_key=api_key,
                    base_url=base_url
                )
            else:
                api_key = os.getenv("OPENAI_API_KEY")
                base_url = os.getenv("OPENAI_BASE_URL", "https://api.minimax.chat/v1")
                self._translator_llm = ChatOpenAI(
                    model="minimax-m2.7",
                    temperature=0.3,
                    max_tokens=4096,
                    api_key=api_key,
                    base_url=base_url
                )
        except Exception as e:
            logger.warning(f"Translator LLM init failed: {e}")

    async def to_english(self, text: str) -> str:
        """
        将中文翻译为英文

        Args:
            text: 中文文本

        Returns:
            英文文本
        """
        if not text or not self._translator_llm:
            return text

        # 如果文本已经是纯英文，直接返回
        if all(ord(c) < 128 for c in text):
            return text

        prompt = f"""Translate the following to English. Output ONLY the translation.

Input: {text}

Output:"""

        try:
            from langchain_core.messages import HumanMessage, SystemMessage
            messages = [
                SystemMessage(content="You are a translator. Output ONLY the translated text, no quotes or explanation."),
                HumanMessage(content=prompt)
            ]
            response = await self._translator_llm.ainvoke(messages)
            result = response.content if hasattr(response, 'content') else str(response)
            result = result.strip().replace("<think>", "").replace("", "").strip()
            result = result.strip('"').strip("'")
            return result
        except Exception as e:
            logger.error(f"Translation to English failed: {e}")
            return text

    async def to_chinese(self, text: str) -> str:
        """
        将英文翻译为中文

        Args:
            text: 英文文本

        Returns:
            中文文本
        """
        if not text or not self._translator_llm:
            return text

        prompt = f"""Translate the following English text to Chinese. Only output the Chinese translation, nothing else.

English: {text}

Chinese:"""

        try:
            from langchain_core.messages import HumanMessage, SystemMessage
            messages = [
                SystemMessage(content="You are a translator. Translate English to Chinese accurately."),
                HumanMessage(content=prompt)
            ]
            response = await self._translator_llm.ainvoke(messages)
            result = response.content if hasattr(response, 'content') else str(response)
            return result.strip()
        except Exception as e:
            logger.error(f"Translation to Chinese failed: {e}")
            return text

    async def process_english_first(
        self,
        chinese_input: str,
        agent: Callable,
        translate_output: bool = False
    ) -> Dict[str, Any]:
        """
        英文优先处理流程

        Args:
            chinese_input: 中文输入
            agent: 要使用的Agent（需要支持execute方法）
            translate_output: 是否将输出翻译回中文

        Returns:
            处理结果
        """
        # 1. 中文输入转英文
        english_input = await self.to_english(chinese_input)
        logger.info(f"Translated input to English: {english_input[:50]}...")

        # 2. 英文处理
        try:
            result = await agent.execute({"user_request": english_input})
        except Exception as e:
            logger.error(f"Agent execution failed: {e}")
            raise

        # 3. 可选：输出转中文
        if translate_output and result.result:
            result.result = await self._translate_result_to_chinese(result.result)

        return result

    async def _translate_result_to_chinese(self, result: Any) -> Any:
        """翻译结果中的文本字段为中文"""
        if isinstance(result, dict):
            translated = {}
            for key, value in result.items():
                if key in ["title", "description", "content", "text", "summary", "report"]:
                    if isinstance(value, str):
                        translated[key] = await self.to_chinese(value)
                    else:
                        translated[key] = value
                else:
                    translated[key] = await self._translate_result_to_chinese(value)
            return translated
        elif isinstance(result, list):
            return [await self._translate_result_to_chinese(item) for item in result]
        elif isinstance(result, str):
            return await self.to_chinese(result)
        else:
            return result


class EnglishFirstMixin:
    """
    英文优先Mixin - 为Agent添加英文处理能力

    使用方式:
        class MyEnglishAgent(EnglishFirstMixin, PaperAgentBase):
            pass
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._translator = None
        self._english_mode = True  # 默认启用英文模式

    def _get_translator(self) -> TranslationWrapper:
        """获取翻译器"""
        if self._translator is None:
            self._translator = TranslationWrapper(self.llm_config)
        return self._translator

    async def _process_english_first(
        self,
        chinese_input: str,
        translate_output: bool = False
    ) -> str:
        """
        使用英文优先模式处理输入

        Args:
            chinese_input: 中文输入
            translate_output: 是否翻译输出

        Returns:
            处理后的文本
        """
        translator = self._get_translator()

        if self._english_mode:
            # 翻译为英文
            english_text = await translator.to_english(chinese_input)
            # 处理（由子类实现）
            result = await self._process_text_english(english_text)
            # 可选：翻译回中文
            if translate_output:
                return await translator.to_chinese(result)
            return result
        else:
            return await self._process_text_english(chinese_input)

    async def _process_text_english(self, text: str) -> str:
        """
        子类实现：处理英文文本

        Args:
            text: 英文文本

        Returns:
            处理结果（英文）
        """
        raise NotImplementedError("Subclasses must implement _process_text_english")
