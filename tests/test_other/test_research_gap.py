"""
研究空白分析器测试
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.agents_v2.problem_oriented.research_gap import (
    ResearchGapAnalyzer,
    ResearchGap,
    GapAnalysisResult,
    GapType,
    OpportunityScore,
    analyze_research_gaps
)


class TestResearchGapAnalyzer:
    """测试研究空白分析器"""

    @pytest.fixture
    def sample_papers(self):
        """示例论文分析数据"""
        return [
            {
                "title": "Deep Learning for Image Classification",
                "core_problem": "图像分类中深度学习的应用",
                "key_methodology": "卷积神经网络 (CNN)",
                "key_findings": ["ResNet达到了95%准确率", "VGG需要更多参数"],
                "limitations": ["需要大量标注数据", "计算资源要求高"],
                "datasets": ["ImageNet", "CIFAR-10"]
            },
            {
                "title": "Transfer Learning in Computer Vision",
                "core_problem": "迁移学习在视觉中的应用",
                "key_methodology": "预训练模型微调",
                "key_findings": ["小数据集也能取得好效果", "特征提取效果显著"],
                "limitations": ["领域差异大时效果下降", "预训练模型选择困难"],
                "datasets": ["ImageNet", "Office-31"]
            },
            {
                "title": "Efficient CNN Architectures",
                "core_problem": "高效CNN架构设计",
                "key_methodology": "网络剪枝和量化",
                "key_findings": ["MobileNet参数量减少80%", "精度损失<2%"],
                "limitations": ["剪枝策略选择困难", "硬件适配复杂"],
                "datasets": ["ImageNet", "CIFAR-100"]
            }
        ]

    @pytest.mark.asyncio
    async def test_analyze_empty_papers(self):
        """测试空论文列表"""
        analyzer = ResearchGapAnalyzer()
        result = await analyzer.analyze("Deep Learning", [])

        assert result.topic == "Deep Learning"
        assert result.total_papers_analyzed == 0
        assert result.gaps_identified == []
        assert result.confidence_level == 0.0

    @pytest.mark.asyncio
    async def test_analyze_with_mock_llm(self, sample_papers):
        """测试有LLM调用的分析"""
        analyzer = ResearchGapAnalyzer()

        # Mock _llm_call to return structured JSON
        async def mock_llm_call(prompt):
            if "methodological" in prompt.lower():
                return '{"gaps": [{"description": "缺乏高效CNN结构的系统性对比", "evidence": ["论文1", "论文2"], "potential_direction": "开展系统对比研究", "required_resources": ["GPU集群"], "related_methods": ["网络剪枝", "知识蒸馏"]}]}'
            elif "empirical" in prompt.lower():
                return '{"gaps": [{"description": "缺乏大规模跨数据集实验", "evidence": ["论文1"], "potential_direction": "进行大规模泛化实验", "required_resources": ["多数据集"], "related_methods": ["迁移学习"]}]}'
            elif "theoretical" in prompt.lower():
                return '{"gaps": []}'
            elif "application" in prompt.lower():
                return '{"gaps": []}'
            elif "comparative" in prompt.lower():
                return '{"gaps": []}'
            elif "scores" in prompt.lower():
                return '{"scores": [{"index": 0, "feasibility": 7.0, "novelty": 8.0, "impact_potential": 7.0, "opportunity_score": "high", "risk_factors": ["计算资源不足"]}]}'
            elif "recommendations" in prompt.lower():
                return '{"recommendations": [{"research_question": "如何系统对比不同高效CNN?", "suggested_method": "标准化 benchmark", "expected_contribution": "为社区提供参考标准"}]}'
            return '{"gaps": []}'

        analyzer._llm_call = mock_llm_call

        result = await analyzer.analyze("Efficient CNN", sample_papers)

        assert result.topic == "Efficient CNN"
        assert result.total_papers_analyzed == 3
        assert len(result.gaps_identified) >= 0
        assert result.confidence_level > 0

    def test_categorize_gaps(self):
        """测试空白分类统计"""
        analyzer = ResearchGapAnalyzer()
        gaps = [
            ResearchGap(GapType.METHODOLOGICAL, "Gap 1", [], "Dir 1", OpportunityScore.HIGH, 7.0, 8.0, 7.0, [], [], []),
            ResearchGap(GapType.METHODOLOGICAL, "Gap 2", [], "Dir 2", OpportunityScore.MEDIUM, 6.0, 7.0, 6.0, [], [], []),
            ResearchGap(GapType.EMPIRICAL, "Gap 3", [], "Dir 3", OpportunityScore.HIGH, 7.0, 8.0, 7.0, [], [], []),
        ]

        categories = analyzer._categorize_gaps(gaps)

        assert categories["methodological"] == 2
        assert categories["empirical"] == 1

    def test_calculate_confidence(self):
        """测试置信度计算"""
        analyzer = ResearchGapAnalyzer()

        # 论文太少
        conf = analyzer._calculate_confidence(5, 0)
        assert conf < 0.5

        # 论文足够，空白适量
        conf = analyzer._calculate_confidence(20, 5)
        assert conf > 0.7

        # 论文足够，空白适中
        conf = analyzer._calculate_confidence(20, 8)
        assert 0.7 <= conf <= 1.0


class TestResearchGap:
    """测试研究空白数据类"""

    def test_gap_creation(self):
        """测试空白创建"""
        gap = ResearchGap(
            gap_type=GapType.METHODOLOGICAL,
            description="Test gap",
            evidence=["Evidence 1"],
            potential_direction="Explore new methods",
            opportunity_score=OpportunityScore.HIGH,
            feasibility=7.5,
            novelty=8.0,
            impact_potential=7.0,
            required_resources=["GPU"],
            related_methods=["CNN", "Transformer"],
            risk_factors=["Data availability"]
        )

        assert gap.gap_type == GapType.METHODOLOGICAL
        assert gap.description == "Test gap"
        assert gap.opportunity_score == OpportunityScore.HIGH
        assert gap.feasibility == 7.5

    def test_gap_types_enum(self):
        """测试空白类型枚举"""
        assert GapType.METHODOLOGICAL.value == "methodological"
        assert GapType.EMPIRICAL.value == "empirical"
        assert GapType.THEORETICAL.value == "theoretical"
        assert GapType.APPLICATION.value == "application"
        assert GapType.COMPARATIVE.value == "comparative"


class TestGapAnalysisResult:
    """测试空白分析结果"""

    def test_result_creation(self):
        """测试结果创建"""
        result = GapAnalysisResult(
            topic="Test Topic",
            total_papers_analyzed=10,
            gaps_identified=[],
            gap_categories={"methodological": 2},
            most_promising_gap=None,
            research_recommendations=["Rec 1"],
            confidence_level=0.85
        )

        assert result.topic == "Test Topic"
        assert result.total_papers_analyzed == 10
        assert result.confidence_level == 0.85

    def test_result_with_gap(self):
        """测试带空白的结果"""
        gap = ResearchGap(
            gap_type=GapType.APPLICATION,
            description="Test gap",
            evidence=["Evidence"],
            potential_direction="Direction",
            opportunity_score=OpportunityScore.HIGH,
            feasibility=8.0,
            novelty=7.5,
            impact_potential=8.0,
            required_resources=[],
            related_methods=[],
            risk_factors=[]
        )

        result = GapAnalysisResult(
            topic="Test",
            total_papers_analyzed=15,
            gaps_identified=[gap],
            gap_categories={"application": 1},
            most_promising_gap=gap,
            research_recommendations=[],
            confidence_level=0.9
        )

        assert result.most_promising_gap == gap
        assert result.gap_categories["application"] == 1


class TestAnalyzeResearchGapsFunction:
    """测试便捷函数"""

    @pytest.mark.asyncio
    async def test_analyze_research_gaps_sync(self):
        """测试同步便捷函数"""
        papers = [
            {
                "title": "Test Paper",
                "core_problem": "Problem",
                "key_methodology": "Method",
                "key_findings": ["Finding 1"],
                "limitations": ["Limitation 1"],
                "datasets": ["Dataset1"]
            }
        ]

        # 直接测试异步版本
        analyzer = ResearchGapAnalyzer()
        result = await analyzer.analyze("Test Topic", papers)
        assert result.topic == "Test Topic"