"""
阶段输入输出 Pydantic 模型

预先定义各阶段的输入输出格式，确保类型安全和数据传递一致性
"""
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field
from enum import Enum


class PhaseStatus(str, Enum):
    """阶段状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class QualityLevel(str, Enum):
    """质量等级"""
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"


# ============ Diagnostic 阶段 ============

class DiagnosticInput(BaseModel):
    """诊断阶段输入"""
    user_request: str = Field(..., description="用户的研究请求/主题")
    user_level: str = Field(default="硕士", description="用户研究水平")
    available_time: str = Field(default="6个月", description="可用时间")
    available_resources: str = Field(default="一般", description="可用资源")


class DiagnosticOutput(BaseModel):
    """诊断阶段输出"""
    topic_assessment: Dict[str, Any] = Field(..., description="选题评估结果")
    problems_identified: List[str] = Field(default_factory=list, description="发现的问题列表")
    severity: Dict[str, float] = Field(default_factory=dict, description="问题严重程度")
    recommendations: List[str] = Field(default_factory=list, description="改进建议")
    quality_score: float = Field(..., description="质量评分 0-1")


# ============ Topic 阶段 ============

class TopicInput(BaseModel):
    """选题阶段输入"""
    user_request: str = Field(..., description="用户的研究请求")


class TopicOutput(BaseModel):
    """选题阶段输出"""
    refined_topic: str = Field(..., description="精炼后的选题")
    research_scope: str = Field(..., description="研究范围")
    innovation_points: List[str] = Field(default_factory=list, description="创新点")
    feasibility: float = Field(..., description="可行性评分 0-1")
    quality_score: float = Field(..., description="质量评分 0-1")


# ============ Literature 阶段 ============

class LiteratureInput(BaseModel):
    """文献阶段输入"""
    topic: str = Field(..., description="研究主题")


class PaperInfo(BaseModel):
    """论文信息"""
    title: str
    authors: str
    year: int
    venue: str
    impact: str
    key_contribution: str
    relevance: float = Field(..., description="相关性 0-1")
    limitations: Optional[str] = None


class LiteratureOutput(BaseModel):
    """文献阶段输出"""
    papers: List[PaperInfo] = Field(default_factory=list, description="收集的论文列表")
    paper_analyses: List[Dict[str, Any]] = Field(default_factory=list, description="论文分析结果")
    research_gaps: List[str] = Field(default_factory=list, description="研究空白")
    search_queries: List[str] = Field(default_factory=list, description="搜索查询")
    quality_score: float = Field(..., description="质量评分 0-1")


# ============ Methodology 阶段 ============

class MethodologyInput(BaseModel):
    """方法阶段输入"""
    topic: str = Field(..., description="研究主题")
    literature_result: Dict[str, Any] = Field(default_factory=dict, description="文献阶段结果")


class MethodologyOutput(BaseModel):
    """方法阶段输出"""
    proposed_method: str = Field(..., description="提出的方法")
    method_rationale: str = Field(..., description="方法选择理由")
    expected_contribution: str = Field(..., description="预期贡献")
    methodology_steps: List[str] = Field(default_factory=list, description="方法步骤")
    quality_score: float = Field(..., description="质量评分 0-1")


# ============ Writing 阶段 ============

class WritingInput(BaseModel):
    """写作阶段输入"""
    topic: str = Field(..., description="研究主题")
    literature_result: Dict[str, Any] = Field(default_factory=dict, description="文献阶段结果")
    thesis_statement: str = Field(default="", description="论题陈述")
    outline: Optional[Dict[str, Any]] = Field(default=None, description="论文大纲")


class WritingOutput(BaseModel):
    """写作阶段输出"""
    full_draft: str = Field(..., description="完整草稿")
    outline: Dict[str, Any] = Field(default_factory=dict, description="论文大纲")
    word_count: int = Field(..., description="字数统计")
    sections_completed: List[str] = Field(default_factory=list, description="完成的章节")
    quality_score: float = Field(..., description="质量评分 0-1")


# ============ Polish 阶段 ============

class PolishInput(BaseModel):
    """润色阶段输入"""
    text: str = Field(..., description="待润色的文本")
    language: str = Field(default="zh", description="语言")
    polish_level: str = Field(default="medium", description="润色级别: light/medium/heavy")


class PolishOutput(BaseModel):
    """润色阶段输出"""
    polished_text: str = Field(..., description="润色后的文本")
    changes_made: List[str] = Field(default_factory=list, description="所做的修改")
    grammar_issues_fixed: int = Field(default=0, description="修复的语法问题数")
    style_issues_fixed: int = Field(default=0, description="修复的风格问题数")
    terminology_issues_fixed: int = Field(default=0, description="修复的术语问题数")
    quality_score: float = Field(..., description="质量评分 0-1")


# ============ 阶段结果包装 ============

class PhaseExecutionResult(BaseModel):
    """阶段执行结果（用于跨阶段数据传递）"""
    phase_name: str
    status: PhaseStatus
    input_data: Optional[Dict[str, Any]] = None
    output_data: Optional[Dict[str, Any]] = None
    quality_score: float = 0.0
    execution_time: float = 0.0
    error: Optional[str] = None

    class Config:
        use_enum_values = True