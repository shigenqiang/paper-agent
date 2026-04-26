"""
集成测试 - 端到端测试

测试完整的论文写作流程:
1. TopicAgent -> 选题
2. LiteratureAgent -> 文献搜索
3. ThesisAgent -> Thesis凝练
4. OutlineAgent -> 大纲生成
5. DraftWriterAgent -> 初稿撰写
"""
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch


class TestPipelineIntegration:
    """测试Pipeline集成"""

    @pytest.mark.asyncio
    async def test_topic_agent_produces_valid_output(self):
        """测试TopicAgent生成有效输出"""
        from src.agents_v2.paper_agents import TopicAgent

        agent = TopicAgent()

        # Mock LLM call to avoid real API call
        with patch.object(agent, '_llm_call', side_effect=Exception("Mock LLM")):
            result = await agent.execute({
                "user_request": "深度学习优化"
            })

            # 有fallback，应该返回有效结果
            assert result.success is True
            assert result.result is not None
            assert "selected_topic" in result.result

    @pytest.mark.asyncio
    async def test_literature_agent_produces_valid_output(self):
        """测试LiteratureAgent生成有效输出"""
        from src.agents_v2.paper_agents import LiteratureAgent

        agent = LiteratureAgent()

        # Mock LLM call
        with patch.object(agent, '_llm_call', side_effect=Exception("Mock LLM")):
            result = await agent.execute({
                "topic": "机器学习"
            })

            # 有fallback，应该返回有效结果
            assert result.success is True
            assert result.result is not None
            assert "papers" in result.result

    @pytest.mark.asyncio
    async def test_problem_agent_diagnose_and_fix(self):
        """测试ProblemAgent诊断流程"""
        from src.agents_v2.problem_oriented import DiscussionDeepenerAgent

        agent = DiscussionDeepenerAgent()

        # Provide valid input with results to avoid early validation failure
        diag_result = await agent.diagnose({
            "results": "这是研究结果",
            "discussion": "这是讨论部分",
            "literature": []
        })

        # Should return some result or diagnosed_issues
        assert diag_result.agent_name == "discussion_deepener"
        # LLM may fail, but agent should handle gracefully
        assert diag_result.success is False or diag_result.result is not None


class TestAgentCollaboration:
    """测试Agent协作"""

    @pytest.mark.asyncio
    async def test_topic_to_literature_flow(self):
        """测试Topic到Literature的流程"""
        from src.agents_v2.paper_agents import TopicAgent, LiteratureAgent

        topic_agent = TopicAgent()
        lit_agent = LiteratureAgent()

        with patch.object(topic_agent, '_llm_call', side_effect=Exception("Mock LLM")):
            # 1. 选题
            topic_result = await topic_agent.execute({
                "user_request": "图像分割"
            })

            assert topic_result.success is True
            selected_topic = topic_result.result.get("selected_topic", {})

            with patch.object(lit_agent, '_llm_call', side_effect=Exception("Mock LLM")):
                # 2. 文献搜索
                lit_result = await lit_agent.execute({
                    "topic": selected_topic.get("title", "图像分割")
                }, context={"topic": selected_topic})

                assert lit_result.success is True

    @pytest.mark.asyncio
    async def test_writing_agent_pipeline(self):
        """测试Writing Agent管道"""
        from src.agents_v2.writing import ProposalGeneratorAgent

        agent = ProposalGeneratorAgent()

        with patch.object(agent, '_llm_call', side_effect=Exception("Mock LLM")):
            result = await agent.execute({
                "topic": "测试主题",
                "background": "测试背景"
            })

            # 有fallback处理
            assert result.success is True


class TestErrorRecovery:
    """测试错误恢复"""

    @pytest.mark.asyncio
    async def test_llm_failure_with_fallback(self):
        """测试LLM失败时有fallback"""
        from src.agents_v2.paper_agents import TopicAgent

        agent = TopicAgent()

        # 完全模拟LLM失败
        with patch.object(agent, '_llm_call', side_effect=Exception("API Timeout")):
            result = await agent.execute({
                "user_request": "测试"
            })

            # 应该优雅降级而不是崩溃
            assert result.success is True  # fallback返回success=True
            assert result.result is not None

    @pytest.mark.asyncio
    async def test_multiple_agent_failures_handled(self):
        """测试多个Agent失败都能被处理"""
        from src.agents_v2.paper_agents import TopicAgent, LiteratureAgent, ThesisAgent

        async def mock_llm_call(*args, **kwargs):
            raise Exception("API Error")

        topic_agent = TopicAgent()
        topic_agent._llm_call = mock_llm_call

        lit_agent = LiteratureAgent()
        lit_agent._llm_call = mock_llm_call

        thesis_agent = ThesisAgent()
        thesis_agent._llm_call = mock_llm_call

        # TopicAgent需要user_request
        result = await topic_agent.execute({"user_request": "深度学习"})
        assert result.success is True

        # LiteratureAgent需要topic
        result = await lit_agent.execute({"topic": "机器学习"})
        assert result.success is True

        # ThesisAgent需要topic和literature_result
        result = await thesis_agent.execute({
            "topic": "机器学习",
            "literature_result": {"papers": []}
        })
        assert result.success is True


class TestAgentRegistry:
    """测试Agent注册机制"""

    def test_all_agents_can_be_instantiated(self):
        """测试所有Agent都可以实例化"""
        from src.agents_v2.paper_agents import (
            TopicAgent, LiteratureAgent, ThesisAgent,
            OutlineAgent, DraftWriterAgent, EditorAgent, ReviewerAgent
        )
        from src.agents_v2.problem_oriented import (
            TopicRefinerAgent, LiteratureMapperAgent, MethodologyAdvisorAgent,
            ArgumentBuilderAgent, SectionDifferentiatorAgent, DiscussionDeepenerAgent,
            ChartFormatterAgent, LanguagePolisherAgent, PlagiarismCheckerAgent
        )
        from src.agents_v2.writing import (
            ProposalGeneratorAgent, OutlineGeneratorAgent, DraftGeneratorAgent,
            ReportRefinerAgent, SmartReviserAgent
        )

        # 这些都应该能实例化而不报错
        paper_agents = [
            TopicAgent(), LiteratureAgent(), ThesisAgent(),
            OutlineAgent(), DraftWriterAgent(), EditorAgent(), ReviewerAgent()
        ]

        problem_agents = [
            TopicRefinerAgent(), LiteratureMapperAgent(), MethodologyAdvisorAgent(),
            ArgumentBuilderAgent(), SectionDifferentiatorAgent(), DiscussionDeepenerAgent(),
            ChartFormatterAgent(), LanguagePolisherAgent(), PlagiarismCheckerAgent()
        ]

        writing_agents = [
            ProposalGeneratorAgent(), OutlineGeneratorAgent(), DraftGeneratorAgent(),
            ReportRefinerAgent(), SmartReviserAgent()
        ]

        # 验证实例化成功
        assert len(paper_agents) == 7
        assert len(problem_agents) == 9
        assert len(writing_agents) == 5

    def test_master_supervisor_can_register_all(self):
        """测试MasterSupervisor可以注册所有Agent"""
        from src.agents_v2.unified.master_supervisor import MasterSupervisor

        supervisor = MasterSupervisor()

        # 注册各类Agent
        supervisor.register_problem_agents()
        supervisor.register_pipeline_agents()
        supervisor.register_writing_agents()

        # 验证注册成功
        assert len(supervisor.agents) > 0
        assert "topic" in supervisor.agents
        assert "literature" in supervisor.agents
        assert "topic_refiner" in supervisor.agents


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
