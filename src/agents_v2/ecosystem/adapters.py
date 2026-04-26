"""
生态适配器 - Ecosystem Adapters

支持:
- LangChain适配器
- AutoGen适配器
- HuggingFace适配器
- OpenAI适配器
"""
import logging
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class LangChainAgent:
    """LangChain兼容Agent"""
    name: str
    tools: List[Any] = None
    memory: Any = None


class LangChainAdapter:
    """LangChain适配器

    提供与LangChain生态的兼容性。
    """

    def __init__(self, agent: Any = None):
        self.agent = agent
        self._tools: Dict[str, Callable] = {}

    def add_tool(self, name: str, func: Callable, description: str = ""):
        """添加工具"""
        self._tools[name] = {
            "func": func,
            "description": description
        }
        logger.info(f"LangChain适配器: 添加工具 {name}")

    async def run(self, prompt: str, tools: List[str] = None) -> str:
        """运行Agent"""
        if self.agent:
            result = await self.agent.arun(prompt)
            return result

        return f"LangChain模拟执行: {prompt}"

    def to_langchain_agent(self) -> LangChainAgent:
        """转换为LangChain Agent"""
        return LangChainAgent(
            name="PaperAgent_LC",
            tools=list(self._tools.values()),
            memory=None
        )


class AutoGenAdapter:
    """AutoGen适配器

    提供与AutoGen生态的兼容性。
    """

    def __init__(self):
        self._agents: Dict[str, Any] = {}

    def register_agent(self, name: str, agent: Any):
        """注册Agent"""
        self._agents[name] = agent
        logger.info(f"AutoGen适配器: 注册Agent {name}")

    async def initiate_chat(self,
                           target_agent: str,
                           message: str,
                           max_turns: int = 10) -> str:
        """发起聊天"""
        agent = self._agents.get(target_agent)
        if agent:
            result = await agent.generate_reply([{"role": "user", "content": message}])
            return result

        return f"AutoGen模拟回复: {message}"

    def create_group_chat(self, agents: List[str]) -> Dict:
        """创建群聊"""
        return {
            "agents": agents,
            "messages": []
        }


class HuggingFaceAdapter:
    """HuggingFace适配器

    支持HF模型和工具。
    """

    def __init__(self, model_name: str = None):
        self.model_name = model_name or "microsoft/phi-2"
        self._model = None
        self._pipeline = None

    def load_model(self):
        """加载模型"""
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline

            self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self._model = AutoModelForCausalLM.from_pretrained(self.model_name)
            self._pipeline = pipeline(
                "text-generation",
                model=self._model,
                tokenizer=self._tokenizer
            )
            logger.info(f"HF模型加载: {self.model_name}")

        except ImportError:
            logger.warning("transformers未安装，使用模拟")
        except Exception as e:
            logger.error(f"HF模型加载失败: {e}")

    async def generate(self, prompt: str, max_length: int = 200) -> str:
        """生成文本"""
        if self._pipeline:
            result = self._pipeline(prompt, max_length=max_length, num_return_sequences=1)
            return result[0]["generated_text"]

        return f"HF模拟生成: {prompt[:50]}..."

    def load_image_model(self, model_name: str = "microsoft/git-base"):
        """加载图像模型"""
        try:
            from transformers import AutoModelForVision2Seq, AutoProcessor

            processor = AutoProcessor.from_pretrained(model_name)
            model = AutoModelForVision2Seq.from_pretrained(model_name)

            return {"processor": processor, "model": model}

        except Exception as e:
            logger.error(f"HF图像模型加载失败: {e}")
            return None


class OpenAIAdapter:
    """OpenAI适配器

    兼容OpenAI GPT生态。
    """

    def __init__(self, api_key: str = None, model: str = "gpt-4"):
        self.api_key = api_key
        self.model = model
        self._client = None

    def connect(self):
        """连接OpenAI API"""
        try:
            from openai import OpenAI
            self._client = OpenAI(api_key=self.api_key)
            logger.info("OpenAI连接成功")
        except ImportError:
            logger.warning("openai未安装，使用模拟")
        except Exception as e:
            logger.error(f"OpenAI连接失败: {e}")

    async def chat(self,
                  messages: List[Dict],
                  temperature: float = 0.7,
                  max_tokens: int = 1000) -> str:
        """聊天"""
        if self._client:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content

        return "OpenAI模拟回复: " + messages[-1].get("content", "")[:50]

    async def embed(self, text: str) -> List[float]:
        """获取文本嵌入"""
        if self._client:
            response = self._client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return response.data[0].embedding

        # 返回模拟嵌入
        import hashlib
        return [float(int(hashlib.md5(text.encode()[i:i+8]).hexdigest(), 16) % 100) / 100
                for i in range(0, min(len(text), 512), 8)]


class EcosystemManager:
    """生态管理器

    统一管理所有生态适配器。
    """

    def __init__(self):
        self.langchain = LangChainAdapter()
        self.autogen = AutoGenAdapter()
        self.huggingface = HuggingFaceAdapter()
        self.openai = OpenAIAdapter()

    def get_adapter(self, ecosystem: str) -> Any:
        """获取适配器"""
        adapters = {
            "langchain": self.langchain,
            "autogen": self.autogen,
            "huggingface": self.huggingface,
            "openai": self.openai
        }
        return adapters.get(ecosystem.lower())

    def get_all_adapters(self) -> Dict[str, Any]:
        """获取所有适配器"""
        return {
            "langchain": self.langchain,
            "autogen": self.autogen,
            "huggingface": self.huggingface,
            "openai": self.openai
        }


# 便捷函数
def create_langchain_adapter(agent: Any = None) -> LangChainAdapter:
    """创建LangChain适配器"""
    return LangChainAdapter(agent=agent)


def create_autogen_adapter() -> AutoGenAdapter:
    """创建AutoGen适配器"""
    return AutoGenAdapter()


def create_huggingface_adapter(model_name: str = None) -> HuggingFaceAdapter:
    """创建HuggingFace适配器"""
    return HuggingFaceAdapter(model_name=model_name)


def create_openai_adapter(api_key: str = None, model: str = "gpt-4") -> OpenAIAdapter:
    """创建OpenAI适配器"""
    return OpenAIAdapter(api_key=api_key, model=model)


def create_ecosystem_manager() -> EcosystemManager:
    """创建生态管理器"""
    return EcosystemManager()