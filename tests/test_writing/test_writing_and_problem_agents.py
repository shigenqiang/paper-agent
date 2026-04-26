"""
单元测试 - WritingAgent和ProblemAgent
"""
import pytest
import asyncio
from unittest.mock import MagicMock, patch


class TestWritingAgentInputOutput:
    """测试WritingAgent输入输出"""

    def test_writing_agent_base_init(self):
        """测试WritingAgentBase初始化"""
        from src.agents_v2.writing.base_writing_agent import WritingAgentBase

        class TestWritingAgent(WritingAgentBase):
            async def execute(self, input_data, context=None):
                return None

        agent = TestWritingAgent(
            name="test_agent",
            description="Test agent"
        )
        assert agent.name == "test_agent"
        assert agent.description == "Test agent"


class TestProblemAgentInputOutput:
    """测试ProblemAgent输入输出"""

    def test_problem_agent_base_init(self):
        """测试ProblemAgentBase初始化"""
        from src.agents_v2.problem_oriented.base_problem_agent import ProblemAgentBase

        class TestProblemAgent(ProblemAgentBase):
            async def diagnose(self, input_data, context=None):
                return None

            async def fix(self, input_data, context=None):
                return None

        agent = TestProblemAgent(
            name="test_problem_agent",
            description="Test problem agent",
            target_problem="test_problem"
        )
        assert agent.name == "test_problem_agent"


class TestWritingAgents:
    """测试WritingAgent实现"""

    def test_proposal_generator_init(self):
        """测试ProposalGeneratorAgent初始化"""
        from src.agents_v2.writing import ProposalGeneratorAgent

        agent = ProposalGeneratorAgent()
        assert agent.name == "proposal_generator"

    def test_outline_generator_init(self):
        """测试OutlineGeneratorAgent初始化"""
        from src.agents_v2.writing import OutlineGeneratorAgent

        agent = OutlineGeneratorAgent()
        assert agent.name == "outline_generator"

    def test_draft_generator_init(self):
        """测试DraftGeneratorAgent初始化"""
        from src.agents_v2.writing import DraftGeneratorAgent

        agent = DraftGeneratorAgent()
        assert agent.name == "draft_generator"

    def test_report_refiner_init(self):
        """测试ReportRefinerAgent初始化"""
        from src.agents_v2.writing import ReportRefinerAgent

        agent = ReportRefinerAgent()
        assert agent.name == "report_refiner"

    def test_smart_reviser_init(self):
        """测试SmartReviserAgent初始化"""
        from src.agents_v2.writing import SmartReviserAgent

        agent = SmartReviserAgent()
        assert agent.name == "smart_reviser"


class TestProblemAgents:
    """测试ProblemAgent实现"""

    def test_topic_refiner_init(self):
        """测试TopicRefinerAgent初始化"""
        from src.agents_v2.problem_oriented import TopicRefinerAgent

        agent = TopicRefinerAgent()
        assert agent.name == "topic_refiner"

    def test_literature_mapper_init(self):
        """测试LiteratureMapperAgent初始化"""
        from src.agents_v2.problem_oriented import LiteratureMapperAgent

        agent = LiteratureMapperAgent()
        assert agent.name == "literature_mapper"

    def test_methodology_advisor_init(self):
        """测试MethodologyAdvisorAgent初始化"""
        from src.agents_v2.problem_oriented import MethodologyAdvisorAgent

        agent = MethodologyAdvisorAgent()
        assert agent.name == "methodology_advisor"

    def test_argument_builder_init(self):
        """测试ArgumentBuilderAgent初始化"""
        from src.agents_v2.problem_oriented import ArgumentBuilderAgent

        agent = ArgumentBuilderAgent()
        assert agent.name == "argument_builder"

    def test_discussion_deepener_init(self):
        """测试DiscussionDeepenerAgent初始化"""
        from src.agents_v2.problem_oriented import DiscussionDeepenerAgent

        agent = DiscussionDeepenerAgent()
        assert agent.name == "discussion_deepener"

    def test_language_polisher_init(self):
        """测试LanguagePolisherAgent初始化"""
        from src.agents_v2.problem_oriented import LanguagePolisherAgent

        agent = LanguagePolisherAgent()
        assert agent.name == "language_polisher"

    def test_chart_formatter_init(self):
        """测试ChartFormatterAgent初始化"""
        from src.agents_v2.problem_oriented import ChartFormatterAgent

        agent = ChartFormatterAgent()
        assert agent.name == "chart_formatter"

    def test_plagiarism_checker_init(self):
        """测试PlagiarismCheckerAgent初始化"""
        from src.agents_v2.problem_oriented import PlagiarismCheckerAgent

        agent = PlagiarismCheckerAgent()
        assert agent.name == "plagiarism_checker"


class TestPaperAgents:
    """测试PaperAgent实现"""

    def test_topic_agent_has_execute(self):
        """测试TopicAgent有execute方法"""
        from src.agents_v2.paper_agents import TopicAgent

        agent = TopicAgent()
        assert hasattr(agent, 'execute')
        assert callable(agent.execute)

    def test_literature_agent_has_execute(self):
        """测试LiteratureAgent有execute方法"""
        from src.agents_v2.paper_agents import LiteratureAgent

        agent = LiteratureAgent()
        assert hasattr(agent, 'execute')
        assert callable(agent.execute)

    def test_thesis_agent_has_execute(self):
        """测试ThesisAgent有execute方法"""
        from src.agents_v2.paper_agents import ThesisAgent

        agent = ThesisAgent()
        assert hasattr(agent, 'execute')
        assert callable(agent.execute)

    def test_outline_agent_has_execute(self):
        """测试OutlineAgent有execute方法"""
        from src.agents_v2.paper_agents import OutlineAgent

        agent = OutlineAgent()
        assert hasattr(agent, 'execute')
        assert callable(agent.execute)

    def test_draft_writer_has_execute(self):
        """测试DraftWriterAgent有execute方法"""
        from src.agents_v2.paper_agents import DraftWriterAgent

        agent = DraftWriterAgent()
        assert hasattr(agent, 'execute')
        assert callable(agent.execute)


class TestMasterSupervisor:
    """测试MasterSupervisor"""

    def test_master_supervisor_init(self):
        """测试MasterSupervisor初始化"""
        from src.agents_v2.unified.master_supervisor import MasterSupervisor

        supervisor = MasterSupervisor()
        assert supervisor is not None
        assert hasattr(supervisor, 'run')
        assert hasattr(supervisor, 'register_agent')

    def test_phase_names(self):
        """测试定义的阶段名称"""
        from src.agents_v2.unified.master_supervisor import MasterSupervisor

        supervisor = MasterSupervisor()
        expected_phases = ["diagnostic", "topic", "literature", "methodology", "writing", "polish"]
        assert supervisor.PHASES == expected_phases

    def test_quality_thresholds(self):
        """测试质量阈值配置"""
        from src.agents_v2.unified.master_supervisor import MasterSupervisor

        supervisor = MasterSupervisor()
        assert "topic" in supervisor.QUALITY_THRESHOLDS
        assert "writing" in supervisor.QUALITY_THRESHOLDS
        assert supervisor.QUALITY_THRESHOLDS["polish"] == 8.0


class TestIntentRouter:
    """测试IntentRouter"""

    def test_intent_type_values(self):
        """测试IntentType枚举值"""
        from src.agents_v2.unified.intent_router import IntentType

        assert IntentType.TOPIC_SELECT.value == "topic_select"
        assert IntentType.LITERATURE_SEARCH.value == "literature_search"
        assert IntentType.DRAFT_WRITE.value == "draft_write"
        assert IntentType.FULL_PAPER.value == "full_paper"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
