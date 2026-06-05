"""枚举类型定义"""

from enum import Enum


class PaperStatus(str, Enum):
    IMPORTED = "imported"
    UPLOADED = "uploaded"
    PARSING = "parsing"
    PARSED = "parsed"
    CARD_READY = "card_ready"
    EVIDENCE_READY = "evidence_ready"
    FAILED = "failed"


class ChunkType(str, Enum):
    TITLE = "title"
    ABSTRACT = "abstract"
    BODY = "body"
    METHOD = "method"
    RESULT = "result"
    DISCUSSION = "discussion"
    LIMITATION = "limitation"
    CONCLUSION = "conclusion"
    REFERENCE = "reference"
    TABLE = "table"
    FIGURE_CAPTION = "figure_caption"
    APPENDIX = "appendix"
    UNKNOWN = "unknown"


class SectionType(str, Enum):
    """论文章节类型（细粒度，比 ChunkType 更精确）"""
    TITLE = "title"
    ABSTRACT = "abstract"
    INTRODUCTION = "introduction"
    RELATED_WORK = "related_work"
    METHOD = "method"
    EXPERIMENT = "experiment"
    RESULT = "result"
    DISCUSSION = "discussion"
    LIMITATION = "limitation"
    CONCLUSION = "conclusion"
    ACKNOWLEDGMENT = "acknowledgment"
    APPENDIX = "appendix"
    REFERENCE = "reference"
    UNKNOWN = "unknown"


class ReportType(str, Enum):
    LITERATURE_REVIEW = "literature_review"
    INNOVATION_REPORT = "innovation_report"


class ScopeType(str, Enum):
    ALL_PROJECT = "all_project"
    SELECTED_PAPERS = "selected_papers"
    TOPIC_GROUP = "topic_group"
    METHOD_GROUP = "method_group"
    GRAPH_SUBGRAPH = "graph_subgraph"
    YEAR_RANGE = "year_range"


class NodeType(str, Enum):
    PAPER = "Paper"
    AUTHOR = "Author"
    TOPIC = "Topic"
    TASK = "Task"
    METHOD = "Method"
    DATASET = "Dataset"
    FINDING = "Finding"
    LIMITATION = "Limitation"
    GAP = "Gap"
    INNOVATION = "InnovationPoint"
    # SciERC 扩展
    METRIC = "Metric"
    OTHER_SCI_TERM = "OtherSciTerm"
    VENUE = "Venue"
    INSTITUTION = "Institution"
    COMMUNITY = "Community"
    GHOST_PAPER = "GhostPaper"


class EdgeType(str, Enum):
    BELONGS_TO_TOPIC = "BELONGS_TO_TOPIC"
    USES_METHOD = "USES_METHOD"
    USES_DATASET = "USES_DATASET"
    REPORTS_FINDING = "REPORTS_FINDING"
    HAS_LIMITATION = "HAS_LIMITATION"
    SUGGESTS_GAP = "SUGGESTS_GAP"
    STUDIES_TASK = "STUDIES_TASK"
    SUPPORTS_INNOVATION = "SUPPORTS_INNOVATION"
    CITES = "CITES"
    # SciERC 核心关系
    USED_FOR = "USED_FOR"           # Method → Task (55.6%)
    CONJUNCTION = "CONJUNCTION"     # Entity ↔ Entity (18.5%)
    HYPONYM_OF = "HYPONYM_OF"      # Entity → Entity (9.8%)
    COMPARE = "COMPARE"             # Method ↔ Method (5%)
    PART_OF = "PART_OF"             # Entity → Entity (5%)
    EVALUATE_FOR = "EVALUATE_FOR"   # Metric → Task (4.4%)
    FEATURE_OF = "FEATURE_OF"       # Property → Entity (1.8%)
    # 扩展关系
    EVALUATED_ON = "EVALUATED_ON"   # Method → Dataset
    EVALUATED_BY = "EVALUATED_BY"   # Method → Metric
    EXTENDS = "EXTENDS"             # Method → Method
    SUBCLASS_OF = "SUBCLASS_OF"
    SUBTASK_OF = "SUBTASK_OF"
    TRAINED_WITH = "TRAINED_WITH"   # Method → Dataset
    ACHIEVES = "ACHIEVES"           # Method → Metric
    AUTHORED_BY = "AUTHORED_BY"
    PUBLISHED_IN = "PUBLISHED_IN"
    BELONGS_TO_COMMUNITY = "BELONGS_TO_COMMUNITY"
    # 立场关系
    SUPPORTS = "SUPPORTS"               # Finding → Finding（支持）
    CONTRADICTS = "CONTRADICTS"         # Finding → Finding（反对）
    # QA 溯源
    RETRIEVES_FROM = "RETRIEVES_FROM"   # Answer → GraphNode（QA 引用图谱节点）
