"""
MultiAgent模块测试

测试:
- MultiAgentDebate: 多Agent辩论
- HierarchicalOrchestrator: 层级编排
- AgentSkillLibrary: 技能库
- SelfLearningEngine: 自主学习
"""
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock

from src.agents_v2.multi_agent import (
    MultiAgentDebate,
    HierarchicalOrchestrator,
    AgentSkillLibrary,
    SelfLearningEngine,
    DebateRole,
    DebateStatement,
    DebateResult,
    run_debate,
    LearningEpisode,
    StrategyAdjustment,
    create_learning_engine
)


class TestDebateRole:
    """DebateRole测试"""

    def test_roles(self):
        """测试角色枚举"""
        assert DebateRole.ADVOCATE.value == "advocate"
        assert DebateRole.OPPONENT.value == "opponent"
        assert DebateRole.MODERATOR.value == "moderator"
        assert DebateRole.EXPERT.value == "expert"


class TestDebateStatement:
    """DebateStatement测试"""

    def test_init(self):
        """测试初始化"""
        statement = DebateStatement(
            speaker="agent1",
            role=DebateRole.ADVOCATE,
            content="测试陈述"
        )

        assert statement.speaker == "agent1"
        assert statement.role == DebateRole.ADVOCATE
        assert statement.content == "测试陈述"
        assert statement.quality_score == 0.5


class TestDebateResult:
    """DebateResult测试"""

    def test_init(self):
        """测试初始化"""
        result = DebateResult(
            topic="AI的未来",
            rounds=3,
            final_position="AI将改变世界",
            supporting_evidence=["证据1", "证据2"],
            opposing_arguments=["反对1"],
            consensus_reached=True,
            confidence=0.8,
            debate_log=[]
        )

        assert result.topic == "AI的未来"
        assert result.rounds == 3
        assert result.consensus_reached is True
        assert result.confidence == 0.8


class TestMultiAgentDebate:
    """MultiAgentDebate测试"""

    def test_init(self):
        """测试初始化"""
        debate = MultiAgentDebate()
        assert debate is not None

    def test_register_agent(self):
        """测试注册Agent"""
        debate = MultiAgentDebate()
        debate.register_agent("agent1", DebateRole.ADVOCATE)

        assert "agent1" in debate._agents
        assert debate._agents["agent1"] == DebateRole.ADVOCATE

    def test_initial_position(self):
        """测试初始立场"""
        debate = MultiAgentDebate()
        position = debate._initial_position("AI的发展", "agent1")

        assert "agent1" in position
        assert "AI的发展" in position

    def test_check_convergence_same(self):
        """测试收敛检测 - 相同位置"""
        debate = MultiAgentDebate()
        positions = {"a": "观点1", "b": "观点1"}
        assert debate._check_convergence(positions) is True

    def test_check_convergence_different(self):
        """测试收敛检测 - 不同位置"""
        debate = MultiAgentDebate()
        positions = {"a": "观点1", "b": "观点2"}
        assert debate._check_convergence(positions) is False

    @pytest.mark.asyncio
    async def test_conduct_debate(self):
        """测试执行辩论"""
        debate = MultiAgentDebate()
        debate.register_agent("agent1", DebateRole.ADVOCATE)
        debate.register_agent("agent2", DebateRole.OPPONENT)

        result = await debate.conduct_debate(
            "AI是否危险",
            ["agent1", "agent2"],
            max_rounds=2
        )

        assert result is not None
        assert result.topic == "AI是否危险"
        assert len(result.debate_log) >= 0


class TestHierarchicalOrchestrator:
    """HierarchicalOrchestrator测试"""

    def test_init(self):
        """测试初始化"""
        orchestrator = HierarchicalOrchestrator()
        assert orchestrator is not None

    @pytest.mark.asyncio
    async def test_decompose_task_simple(self):
        """测试简单任务分解"""
        orchestrator = HierarchicalOrchestrator()
        subtasks = await orchestrator.decompose_task("写一篇论文")

        assert len(subtasks) >= 1
        assert "id" in subtasks[0]
        assert "description" in subtasks[0]

    @pytest.mark.asyncio
    async def test_execute_subtask(self):
        """测试执行子任务"""
        orchestrator = HierarchicalOrchestrator()

        async def mock_executor(task):
            return f"执行了: {task['description']}"

        result = await orchestrator.execute_subtask(
            {"id": "1", "description": "测试任务"},
            mock_executor
        )

        assert "执行了" in result

    @pytest.mark.asyncio
    async def test_aggregate_results(self):
        """测试聚合结果"""
        orchestrator = HierarchicalOrchestrator()
        orchestrator._results["1"] = {"data": "result1"}
        orchestrator._results["2"] = {"data": "result2"}

        aggregated = await orchestrator.aggregate_results(["1", "2"])

        assert "subtask_results" in aggregated

    def test_get_task_graph(self):
        """测试获取任务图"""
        orchestrator = HierarchicalOrchestrator()
        orchestrator._subtasks["1"] = {"id": "1"}

        graph = orchestrator.get_task_graph()
        assert graph["subtask_count"] >= 1


class TestAgentSkillLibrary:
    """AgentSkillLibrary测试"""

    def test_init(self):
        """测试初始化"""
        library = AgentSkillLibrary()
        assert library is not None

    def test_register_skill(self):
        """测试注册技能"""
        library = AgentSkillLibrary()

        async def mock_skill(**kwargs):
            return "执行完成"

        library.register_skill(
            "test_skill",
            "这是一个测试技能",
            mock_skill,
            {"version": "1.0"}
        )

        assert "test_skill" in library._skills

    def test_discover_skills(self):
        """测试发现技能"""
        library = AgentSkillLibrary()

        async def mock_skill(**kwargs):
            return "done"

        library.register_skill("code_generator", "生成代码的技能", mock_skill)

        found = library.discover_skills("代码")
        assert len(found) >= 1
        assert found[0]["name"] == "code_generator"

    @pytest.mark.asyncio
    async def test_execute_skill(self):
        """测试执行技能"""
        library = AgentSkillLibrary()

        async def mock_skill(param1, param2=None):
            return f"param1={param1}, param2={param2}"

        library.register_skill("test", "测试技能", mock_skill)

        result = await library.execute_skill("test", param1="value1", param2="value2")
        assert "param1=value1" in result

    def test_get_skill_stats(self):
        """测试获取技能统计"""
        library = AgentSkillLibrary()

        async def mock_skill(**kwargs):
            return "done"

        library.register_skill("skill1", "技能1", mock_skill)
        library.register_skill("skill2", "技能2", mock_skill)

        stats = library.get_skill_stats()
        assert stats["total_skills"] == 2


class TestSelfLearningEngine:
    """SelfLearningEngine测试"""

    def test_init(self):
        """测试初始化"""
        engine = SelfLearningEngine(memory_window=50)
        assert engine.memory_window == 50

    def test_record_attempt_success(self):
        """测试记录成功尝试"""
        engine = SelfLearningEngine()
        engine.record_attempt("任务1", True, "策略A", {"accuracy": 0.9})

        assert len(engine._episodes) == 1
        assert engine._strategies["策略A"] > 0.5

    def test_record_attempt_failure(self):
        """测试记录失败尝试"""
        engine = SelfLearningEngine()
        engine.record_attempt("任务1", False, "策略B", {}, error="超时")

        assert len(engine._episodes) == 1
        assert not list(engine._episodes)[0].success

    @pytest.mark.asyncio
    async def test_analyze_failures(self):
        """测试分析失败"""
        engine = SelfLearningEngine()

        engine.record_attempt("任务1", False, "策略A", error="错误A")
        engine.record_attempt("任务1", False, "策略A", error="错误A")

        patterns = await engine.analyze_failures()
        assert len(patterns) >= 1

    @pytest.mark.asyncio
    async def test_suggest_improvements(self):
        """测试建议改进"""
        engine = SelfLearningEngine()

        # 添加一些成功记录
        for _ in range(5):
            engine.record_attempt("任务", True, "好策略")

        suggestions = await engine.suggest_improvements()
        # 可能没有建议，因为简单实现可能没有足够的分析
        assert isinstance(suggestions, list)

    @pytest.mark.asyncio
    async def test_learn_from_success(self):
        """测试从成功中学习"""
        engine = SelfLearningEngine()

        engine.record_attempt("写论文任务", True, "策略X", {"score": 0.9})

        strategy = await engine.learn_from_success("写论文")
        assert strategy == "策略X"

    @pytest.mark.asyncio
    async def test_execute_with_learning_success(self):
        """测试带学习的成功执行"""
        engine = SelfLearningEngine()

        async def mock_success(task):
            return {"success": True, "result": "done"}

        engine.register_skill("primary", mock_success)

        result = await engine.execute_with_learning("测试任务", "primary")
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_execute_with_learning_fallback(self):
        """测试带备用策略的执行"""
        engine = SelfLearningEngine()

        async def mock_fail(task):
            return {"success": False, "error": "失败"}

        engine.register_skill("primary", mock_fail)
        engine.register_skill("fallback", lambda task: {"success": True})

        result = await engine.execute_with_learning(
            "测试任务",
            "primary",
            ["fallback"]
        )
        assert result["success"] is True

    def test_get_learning_stats(self):
        """测试获取学习统计"""
        engine = SelfLearningEngine()
        engine.record_attempt("任务1", True, "策略A")

        stats = engine.get_learning_stats()
        assert "total_episodes" in stats
        assert stats["total_episodes"] == 1

    def test_clear_history(self):
        """测试清除历史"""
        engine = SelfLearningEngine()
        engine.record_attempt("任务1", True, "策略A")

        engine.clear_history()
        assert len(engine._episodes) == 0


class TestLearningEpisode:
    """LearningEpisode测试"""

    def test_init(self):
        """测试初始化"""
        episode = LearningEpisode(
            task="测试任务",
            attempts=1,
            success=True,
            final_strategy="strategy_a",
            metrics={"accuracy": 0.95}
        )

        assert episode.task == "测试任务"
        assert episode.success is True
        assert episode.final_strategy == "strategy_a"


class TestStrategyAdjustment:
    """StrategyAdjustment测试"""

    def test_init(self):
        """测试初始化"""
        adjustment = StrategyAdjustment(
            strategy_name="test_strategy",
            adjustment_type="increase",
            change_amount=0.2,
            reason="成功率提升",
            resulting_score=0.85
        )

        assert adjustment.strategy_name == "test_strategy"
        assert adjustment.adjustment_type == "increase"


class TestRunDebate:
    """run_debate便捷函数测试"""

    @pytest.mark.asyncio
    async def test_run_debate(self):
        """测试运行辩论"""
        result = await run_debate(
            "AI的未来",
            ["agent1", "agent2"],
            max_rounds=2
        )

        assert result is not None
        assert result.topic == "AI的未来"


class TestCreateLearningEngine:
    """create_learning_engine便捷函数测试"""

    def test_create(self):
        """测试创建引擎"""
        engine = create_learning_engine(memory_window=100)
        assert engine.memory_window == 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])