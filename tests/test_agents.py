"""
单元测试 - 核心Agent模块

测试各个Agent的基本功能:
1. 实例化
2. 注册机制
3. 输入输出格式
"""
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch


class TestAgentInputOutput:
    """测试Agent输入输出格式"""

    def test_agent_input_schema(self):
        """测试AgentInput的schema"""
        from src.agents_v2.paper_agents.base_paper_agent import AgentInput

        agent_input = AgentInput(
            task_type="topic",
            task_description="选择研究主题",
            input_data={"user_request": "机器学习"},
            requirements=["创新性", "可行性"]
        )

        assert agent_input.task_type == "topic"
        assert agent_input.input_data["user_request"] == "机器学习"

    def test_agent_output_schema(self):
        """测试AgentOutput的schema"""
        from src.agents_v2.paper_agents.base_paper_agent import AgentOutput

        agent_output = AgentOutput(
            success=True,
            result={"topic": "深度学习在图像识别中的应用"},
            agent_name="topic_agent",
            reasoning="选择了最相关的topic",
            quality_score=0.8
        )

        assert agent_output.success is True
        assert agent_output.quality_score == 0.8


class TestLLMConfig:
    """测试LLM配置"""

    def test_default_config(self):
        """测试默认配置"""
        from src.agents_v2.paper_agents.base_paper_agent import LLMConfig

        config = LLMConfig()
        assert config.provider == "openai"
        assert config.model_name == "gpt-4"
        assert config.temperature == 0.7

    def test_custom_config(self):
        """测试自定义配置"""
        from src.agents_v2.paper_agents.base_paper_agent import LLMConfig

        config = LLMConfig(
            provider="anthropic",
            model_name="claude-3",
            temperature=0.5,
            api_key="test-key"
        )

        assert config.provider == "anthropic"
        assert config.model_name == "claude-3"
        assert config.api_key == "test-key"


class TestTopicAgent:
    """测试TopicAgent"""

    def test_topic_agent_init(self):
        """测试TopicAgent初始化"""
        from src.agents_v2.paper_agents import TopicAgent

        agent = TopicAgent()
        assert agent.name == "topic_agent"
        assert "主题选择" in agent.description

    @pytest.mark.asyncio
    async def test_topic_agent_empty_input(self):
        """测试空输入处理"""
        from src.agents_v2.paper_agents import TopicAgent

        agent = TopicAgent()
        result = await agent.execute({})

        assert result.success is False
        assert "Empty user request" in result.error

    @pytest.mark.asyncio
    async def test_topic_agent_fallback_on_llm_failure(self):
        """测试LLM失败时使用fallback"""
        from src.agents_v2.paper_agents import TopicAgent

        agent = TopicAgent()

        # Mock _llm_call to raise an exception
        with patch.object(agent, '_llm_call', side_effect=Exception("LLM API Error")):
            result = await agent.execute({"user_request": "深度学习"})

            # 应该返回fallback结果而不是崩溃 - fallback返回success=True但质量较低
            assert result.success is True
            assert result.result is not None
            assert "selected_topic" in result.result


class TestLiteratureAgent:
    """测试LiteratureAgent"""

    def test_literature_agent_init(self):
        """测试LiteratureAgent初始化"""
        from src.agents_v2.paper_agents import LiteratureAgent

        agent = LiteratureAgent()
        assert agent.name == "literature_agent"
        assert agent.search_agent is not None

    @pytest.mark.asyncio
    async def test_literature_agent_empty_topic(self):
        """测试空topic处理"""
        from src.agents_v2.paper_agents import LiteratureAgent

        agent = LiteratureAgent()
        result = await agent.execute({})

        assert result.success is False
        assert "Empty topic" in result.error


class TestIntentRouter:
    """测试IntentRouter"""

    def test_intent_router_init(self):
        """测试IntentRouter初始化"""
        from src.agents_v2.unified.intent_router import IntentRouter

        router = IntentRouter()
        # IntentRouter没有name属性，只是一个协调器
        assert router is not None
        assert hasattr(router, 'route')

    def test_intent_type_enum(self):
        """测试IntentType枚举"""
        from src.agents_v2.unified.intent_router import IntentType

        assert IntentType.LITERATURE_SEARCH.value == "literature_search"
        assert IntentType.TOPIC_SELECT.value == "topic_select"


class TestErrorHandlerIntegration:
    """测试错误处理集成"""

    def test_fallback_handler_phase_fallbacks(self):
        """测试各阶段fallback配置"""
        from src.agents_v2.unified.error_handler import FallbackHandler

        handler = FallbackHandler()

        # topic阶段不可跳过
        topic_fallback = handler.PHASE_FALLBACKS.get("topic", {})
        assert topic_fallback.get("skip_allowed") is False

        # literature阶段可以跳过
        lit_fallback = handler.PHASE_FALLBACKS.get("literature", {})
        assert lit_fallback.get("skip_allowed") is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
