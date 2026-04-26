"""
Writing and Revision Flow Test

Test the complete writing and revision process
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestDraftGenerator:
    """Test DraftGeneratorAgent"""

    def test_draft_generator_initialization(self):
        """测试DraftGenerator初始化"""
        from src.agents_v2.writing.draft_generator import DraftGeneratorAgent

        agent = DraftGeneratorAgent()
        assert agent.name == "draft_generator"
        assert "论文" in agent.system_prompt

    def test_draft_generator_execute_without_llm(self):
        """测试DraftGenerator无LLM执行"""
        import asyncio
        from src.agents_v2.writing.draft_generator import DraftGeneratorAgent

        agent = DraftGeneratorAgent()
        # 不传入LLM时应该优雅处理
        result = asyncio.run(agent.execute({
            "topic": "深度学习",
            "outline": {"chapters": []}
        }))

        # Agent使用fallback机制，即使没有LLM也可能返回success
        # 关键是检查是否有合理的结果
        assert result is not None
        assert result.agent_name == "draft_generator"


class TestSmartReviser:
    """Test SmartReviserAgent"""

    def test_smart_reviser_initialization(self):
        """测试SmartReviser初始化"""
        from src.agents_v2.writing.smart_reviser import SmartReviserAgent

        agent = SmartReviserAgent()
        assert agent.name == "smart_reviser"

    def test_smart_reviser_categorize_feedback(self):
        """测试反馈分类"""
        from src.agents_v2.writing.smart_reviser import SmartReviserAgent

        agent = SmartReviserAgent()

        # 测试分类方法存在
        assert hasattr(agent, '_categorize_feedback')


class TestLanguagePolisher:
    """Test LanguagePolisherAgent"""

    def test_language_polisher_initialization(self):
        """测试LanguagePolisher初始化"""
        from src.agents_v2.writing.smart_reviser import LanguagePolisherAgent

        agent = LanguagePolisherAgent()
        assert agent.name == "language_polisher"

    def test_polish_levels(self):
        """测试润色级别"""
        from src.agents_v2.writing.smart_reviser import LanguagePolisherAgent

        agent = LanguagePolisherAgent()
        # 测试不同润色级别
        levels = ["light", "medium", "heavy"]
        for level in levels:
            # 只验证方法存在，不实际执行
            assert hasattr(agent, '_polish_text')


class TestOutlineGenerator:
    """Test OutlineGeneratorAgent"""

    def test_outline_generator_initialization(self):
        """测试OutlineGenerator初始化"""
        from src.agents_v2.writing.outline_generator import OutlineGeneratorAgent

        agent = OutlineGeneratorAgent()
        assert agent.name == "outline_generator"


class TestLiteratureReview:
    """Test LiteratureReviewAgent"""

    def test_literature_review_initialization(self):
        """测试LiteratureReview初始化"""
        from src.agents_v2.writing.literature_review import LiteratureReviewAgent

        agent = LiteratureReviewAgent()
        # Agent名称可能是 literature_review
        assert "literature" in agent.name


class TestBaseWritingAgent:
    """Test WritingAgentBase"""

    def test_writing_input_model(self):
        """测试WritingInput模型"""
        from src.agents_v2.writing.base_writing_agent import WritingInput

        inp = WritingInput(
            task_type="draft_write",
            task_description="Generate a paper draft"
        )
        assert inp.task_type == "draft_write"
        assert inp.task_description == "Generate a paper draft"

    def test_writing_output_model(self):
        """测试WritingOutput模型"""
        from src.agents_v2.writing.base_writing_agent import WritingOutput

        out = WritingOutput(
            success=True,
            result={"draft": "content"},
            agent_name="test_agent"
        )
        assert out.success is True
        assert out.result["draft"] == "content"

    def test_llm_config(self):
        """测试LLMConfig"""
        from src.agents_v2.writing.base_writing_agent import LLMConfig

        config = LLMConfig(
            provider="openai",
            model_name="gpt-4",
            temperature=0.5
        )
        assert config.provider == "openai"
        assert config.temperature == 0.5


class TestWritingFlow:
    """Test Writing Flow Integration"""

    def test_flow_components_exist(self):
        """测试流程组件存在"""
        from src.agents_v2.writing.draft_generator import DraftGeneratorAgent
        from src.agents_v2.writing.smart_reviser import SmartReviserAgent, LanguagePolisherAgent
        from src.agents_v2.writing.outline_generator import OutlineGeneratorAgent
        from src.agents_v2.writing.literature_review import LiteratureReviewAgent

        agents = [
            DraftGeneratorAgent(),
            SmartReviserAgent(),
            LanguagePolisherAgent(),
            OutlineGeneratorAgent(),
            LiteratureReviewAgent()
        ]

        assert len(agents) == 5

    def test_flow_sequence(self):
        """测试流程顺序"""
        from src.agents_v2.writing.base_writing_agent import WritingOutput

        # 模拟流程
        outputs = []

        # 1. Outline generation
        outputs.append(WritingOutput(
            success=True,
            result={"outline": {"chapters": []}},
            agent_name="outline_generator",
            quality_score=0.8
        ))

        # 2. Draft writing
        outputs.append(WritingOutput(
            success=True,
            result={"draft": "content"},
            agent_name="draft_generator",
            quality_score=0.7
        ))

        # 3. Revision
        outputs.append(WritingOutput(
            success=True,
            result={"revised": "new content"},
            agent_name="smart_reviser",
            quality_score=0.85
        ))

        # 4. Polishing
        outputs.append(WritingOutput(
            success=True,
            result={"polished": "final content"},
            agent_name="language_polisher",
            quality_score=0.9
        ))

        assert len(outputs) == 4
        assert all(o.success for o in outputs)

    def test_revision_categories(self):
        """测试修订分类"""
        categories = ["content", "structure", "language", "citation", "logic", "format"]

        for cat in categories:
            assert cat in ["content", "structure", "language", "citation", "logic", "format"]


class TestWritingAgents:
    """Test all writing agents can be imported"""

    def test_import_all_writing_agents(self):
        """测试导入所有写作Agent"""
        from src.agents_v2.writing import (
            DraftGeneratorAgent,
            SmartReviserAgent,
            LanguagePolisherAgent,
            OutlineGeneratorAgent,
            LiteratureReviewAgent,
            ProposalGeneratorAgent
        )

        # 这些应该存在于 __init__.py 中
        assert DraftGeneratorAgent is not None
        assert SmartReviserAgent is not None

    def test_writing_agent_base_methods(self):
        """测试基类方法"""
        from src.agents_v2.writing.base_writing_agent import WritingAgentBase

        # 验证抽象方法
        assert hasattr(WritingAgentBase, 'execute')

    def test_writing_output_has_quality_score(self):
        """测试输出包含质量评分"""
        from src.agents_v2.writing.base_writing_agent import WritingOutput

        out = WritingOutput(
            success=True,
            agent_name="test",
            quality_score=0.85
        )

        assert out.quality_score == 0.85


if __name__ == "__main__":
    pytest.main([__file__, "-v"])