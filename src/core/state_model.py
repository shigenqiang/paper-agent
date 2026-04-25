from pydantic import BaseModel,Field
from typing import Optional,Any,TypedDict,List,Dict


class Paper_Metadata(BaseModel):
    pass



from pydantic import BaseModel, Field
from typing import List


class ExtractedData(BaseModel):
    title: str = Field(
        ...,
        description="论文的标题"
    )

    abstract: str = Field(
        ...,
        description="论文的摘要部分，尽可能突出重点"
    )

    core_problem: str = Field(
        ...,
        description="用“尽管…但…”或“为了…”句式概括论文核心问题"
    )

    key_methodology_name: str = Field(
        ...,
        description="优先取原文给出的模型/算法/框架名"
    )

    key_methodology_principle: str = Field(
        ...,
        description="用1-2句话描述技术路线（可用公式或缩写，但需保留）"
    )

    key_methodology_novelty: str = Field(
        ...,
        description="若原文有“首次”“我们提出”等字样，直接引用；否则概括其创新点"
    )

    datasets_used: List[str] = Field(
        ...,
        description="列出数据集全称及规模，如“SST-2 (67k sentences)”"
    )

    evaluation_metrics: List[str] = Field(
        ...,
        description="仅保留与主实验直接相关的指标，如Accuracy, F1, BLEU"
    )

    main_results: str = Field(
        ...,
        description="必须带数值及对照基线，如“在IMDB上Accuracy达92.5%，优于BERT的89.3%”"
    )

    limitations: str = Field(
        ...,
        description="通常出现在Discussion或Conclusion段首，如“本研究仅考虑英语语料”"
    )

    contributions: List[str] = Field(
        ...,
        description="3-5条bullet式短语，保持原文时态"
    )


class paper_contens(BaseModel):
    extracted_data: List[ExtractedData] = Field(
        ...,
        description="抽取出的论文结构化信息列表"
    )


class SearchAgent(BaseModel):
    query: str
    next_node: Optional[str] = Field(default=None, description="下一步节点")
    structed_query: Optional[dict | str] = Field(default=None, description="结构化查询")
    papers_filter: Optional[dict] = Field(default_factory=dict, description="论文过滤要求")
    papers: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="检索到的论文元数据列表")

    def __init__(self, **data):
        super().__init__(**data)
        if not self.structed_query:
            self.structed_query = self.query


class Paper(BaseModel):
    """论文元数据"""
    paper_id: Optional[str] = Field(default=None, description="论文ID")
    title: str = Field(default="", description="论文标题")
    authors: List[str] = Field(default_factory=list, description="作者列表")
    abstract: str = Field(default="", description="摘要")
    url: Optional[str] = Field(default=None, description="论文链接")
    pdf_url: Optional[str] = Field(default=None, description="PDF链接")
    published_date: Optional[str] = Field(default=None, description="发表日期 YYYY-MM-DD")
    source: str = Field(default="unknown", description="来源: arxiv/semantic_scholar/local")
    categories: List[str] = Field(default_factory=list, description="分类标签")
    doi: Optional[str] = Field(default=None, description="DOI")
    relevance_score: Optional[float] = Field(default=None, description="相关性评分 0-1")
class AnalysisResults(BaseModel):
    """分析模块产生的结构化结果"""
    topic_clusters: Optional[Dict[str, List[str]]] = Field(default=None, description="主题聚类, key: 主题名, value: 相关paper_id列表")
    trend_analysis: Optional[Dict[int, int]] = Field(default=None, description="趋势分析, key: 年份, value: 论文数量")
    method_comparison: Optional[List[Dict[str, Any]]] = Field(default=None, description="方法对比表格数据")
    influential_authors: Optional[List[str]] = Field(default=None, description="高产作者列表")
    influential_institutions: Optional[List[str]] = Field(default=None, description="核心机构列表")



class NodeError(BaseModel):
    search_node_error: Optional[str] = Field(default=None, description="搜索节点错误信息")
    reading_node_error: Optional[str] = Field(default=None, description="阅读节点错误信息")
    analyse_node_error: Optional[str] = Field(default=None, description="分析节点错误信息")
    writing_node_error: Optional[str] = Field(default=None, description="写作节点错误信息")
    report_node_error: Optional[str] = Field(default=None, description="报告生成节点错误信息")
    error: Optional[str] = Field(default=None, description="错误信息")
class paperagentstate(BaseModel):#可以说是agent的短期上下文。
    current_step:str = "init"
    search_state:Optional[SearchAgent]=Field(default=None, description="查询的状态，包含原始查询和结构化查询")#使用query_State的原因是，查看中间值
    papers_content: Optional[paper_contens] = Field(default=None, description="包含论文的元数据和处理过的数据")
    analysis_result:Optional[AnalysisResults]=Field(default=None,description="分析论文的结果")
    outline: Optional[str] = Field(default=None, description="报告大纲")
    writted_sections: Optional[List[str]] = Field(default=None, description="已写章节内容")
    report_markdown: Optional[str] = Field(default=None, description="最终生成的Markdown报告内容")

    # 配置与上下文
    llm_provider: Any = Field(default=None, description="LLM提供者实例", exclude=True)  # 排除序列化

    error: Optional[NodeError] = Field(default=None, description="错误信息")

    def __init__(self, **data):
        super().__init__(**data)
        # 修复 Pydantic default 问题
        if self.writted_sections is None:
            self.writted_sections = []
        if self.error is None:
            self.error = NodeError()




class State(TypedDict):
    state:str
    value:paperagentstate

class ConfigSchema(TypedDict):
    """LangGraph兼容的配置定义"""
    state_queue: str
    value: Dict[str, Any]

