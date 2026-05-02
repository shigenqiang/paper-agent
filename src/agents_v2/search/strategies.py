"""
Search Strategies - 搜索策略定义

针对不同场景优化搜索配置。
"""
from dataclasses import dataclass
from enum import Enum

from .search_orchestrator import SearchStrategy, SearchConfig, OrchestratorConfig
from .search_result_merger import MergeConfig


class SearchScenario(Enum):
    """搜索场景"""
    LITERATURE_REVIEW = "literature_review"     # 文献综述
    RESEARCH_QUESTION = "research_question"      # 研究问题探索
    PAPER_WRITING = "paper_writing"             # 论文写作引用
    TOPIC_EXPLORATION = "topic_exploration"      # 主题探索
    EXPERT_FINDING = "expert_finding"           # 专家/作者发现
    TREND_ANALYSIS = "trend_analysis"           # 趋势分析
    QUICK_SURVEY = "quick_survey"               # 快速调研


@dataclass
class ScenarioConfig:
    """场景化搜索配置"""
    scenario: SearchScenario
    strategy: SearchStrategy
    max_results: int
    preferred_sources: list
    exclude_sources: list = None
    year_range: tuple = None  # (from_year, to_year)
    include_abstracts: bool = True
    cache_ttl: int = 3600


# 预定义场景配置
SCENARIO_CONFIGS = {
    SearchScenario.LITERATURE_REVIEW: ScenarioConfig(
        scenario=SearchScenario.LITERATURE_REVIEW,
        strategy=SearchStrategy.COMPREHENSIVE,
        max_results=50,
        preferred_sources=["openalex", "semantic_scholar", "crossref", "arxiv"],
        exclude_sources=[],
    ),

    SearchScenario.RESEARCH_QUESTION: ScenarioConfig(
        scenario=SearchScenario.RESEARCH_QUESTION,
        strategy=SearchStrategy.BALANCED,
        max_results=20,
        preferred_sources=["openalex", "arxiv"],
    ),

    SearchScenario.PAPER_WRITING: ScenarioConfig(
        scenario=SearchScenario.PAPER_WRITING,
        strategy=SearchStrategy.BALANCED,
        max_results=15,
        preferred_sources=["semantic_scholar", "openalex", "crossref"],
        include_abstracts=True,
    ),

    SearchScenario.TOPIC_EXPLORATION: ScenarioConfig(
        scenario=SearchScenario.TOPIC_EXPLORATION,
        strategy=SearchStrategy.FAST,
        max_results=10,
        preferred_sources=["openalex", "arxiv"],
        cache_ttl=1800,  # 探索场景缓存更短
    ),

    SearchScenario.EXPERT_FINDING: ScenarioConfig(
        scenario=SearchScenario.EXPERT_FINDING,
        strategy=SearchStrategy.PRECISE,
        max_results=20,
        preferred_sources=["semantic_scholar", "openalex"],
    ),

    SearchScenario.TREND_ANALYSIS: ScenarioConfig(
        scenario=SearchScenario.TREND_ANALYSIS,
        strategy=SearchStrategy.COMPREHENSIVE,
        max_results=100,
        preferred_sources=["openalex", "crossref"],
        year_range=(2020, 2026),
    ),

    SearchScenario.QUICK_SURVEY: ScenarioConfig(
        scenario=SearchScenario.QUICK_SURVEY,
        strategy=SearchStrategy.FAST,
        max_results=5,
        preferred_sources=["openalex"],
        cache_ttl=600,  # 快速调研缓存更短
    ),
}


def get_search_config(scenario: SearchScenario) -> SearchConfig:
    """根据场景获取搜索配置"""
    scenario_config = SCENARIO_CONFIGS.get(scenario)
    if not scenario_config:
        return SearchConfig()

    return SearchConfig(
        strategy=scenario_config.strategy,
        max_total_results=scenario_config.max_results,
        max_results_per_source=scenario_config.max_results // 2,
        enable_cache=True,
        cache_ttl=scenario_config.cache_ttl,
    )


def get_orchestrator_config(scenario: SearchScenario) -> OrchestratorConfig:
    """根据场景获取编排器配置"""
    if scenario == SearchScenario.TOPIC_EXPLORATION:
        return OrchestratorConfig(
            enable_parallel=True,
            max_parallel_sources=5,
            fail_fast=True,
            partial_results_on_error=True,
        )
    elif scenario == SearchScenario.LITERATURE_REVIEW:
        return OrchestratorConfig(
            enable_parallel=True,
            max_parallel_sources=3,
            fail_fast=False,
            partial_results_on_error=True,
        )
    elif scenario == SearchScenario.QUICK_SURVEY:
        return OrchestratorConfig(
            enable_parallel=True,
            max_parallel_sources=2,
            fail_fast=True,
            partial_results_on_error=True,
        )
    return OrchestratorConfig()


def get_sources_for_scenario(scenario: SearchScenario) -> list:
    """获取场景适用的搜索源"""
    config = SCENARIO_CONFIGS.get(scenario)
    if not config:
        return ["openalex", "arxiv"]
    return config.preferred_sources


# 场景化搜索入口
async def search_for_scenario(
    orchestrator,
    query: str,
    scenario: SearchScenario
) -> list:
    """针对场景的搜索

    Args:
        orchestrator: SearchOrchestrator实例
        query: 搜索查询
        scenario: 搜索场景

    Returns:
        搜索结果列表
    """
    scenario_config = SCENARIO_CONFIGS.get(scenario)
    if not scenario_config:
        scenario = SearchScenario.QUICK_SURVEY
        scenario_config = SCENARIO_CONFIGS[scenario]

    search_config = get_search_config(scenario)
    orchestrator_config = get_orchestrator_config(scenario)

    # 更新编排器配置
    orchestrator.config = orchestrator_config

    # 执行搜索
    results = await orchestrator.search(
        query,
        config=search_config,
        sources=scenario_config.preferred_sources
    )

    return results


# 配置验证
def validate_scenario_config(config: ScenarioConfig) -> bool:
    """验证场景配置是否有效"""
    if config.max_results < 1:
        return False
    if not config.preferred_sources:
        return False
    if config.year_range:
        if config.year_range[0] > config.year_range[1]:
            return False
    return True