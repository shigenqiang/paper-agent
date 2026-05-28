# Knowledge Graph 知识图谱详解

> 位置: `src/agents_v2/knowledge_graph/`

## 一、架构概览

```
knowledge_graph/
├── __init__.py
├── kg_service.py            # KG服务
├── kg_graphrag.py          # GraphRAG问答
├── kg_embeddings.py        # 向量嵌入
├── kg_community.py         # 社区检测
├── kg_batch_operations.py  # 批量操作
├── kg_extractors.py        # 实体提取
├── kg_hybrid_retriever.py # 混合检索
├── kg_schema.py           # 图谱Schema
├── kg_summarizer.py       # 摘要生成
├── kg_vector_store.py     # 向量存储
└── deprecated/
    └── legacy_generator.py
```

## 二、核心数据结构

### 2.1 实体 (Entity)

```python
@dataclass
class Entity:
    """知识图谱实体"""
    id: str
    type: EntityType  # PAPER, AUTHOR, CONCEPT, METHOD, VENUE
    name: str
    properties: Dict[str, Any]
    embeddings: List[float]

@dataclass
class EntityType(Enum):
    PAPER = "paper"
    AUTHOR = "author"
    CONCEPT = "concept"
    METHOD = "method"
    VENUE = "venue"
```

### 2.2 关系 (Relation)

```python
@dataclass
class Relation:
    """知识图谱关系"""
    id: str
    source_id: str
    target_id: str
    type: RelationType  # CITES, AUTHORED_BY, BELONGS_TO, SIMILAR_TO
    properties: Dict[str, Any]

@dataclass
class RelationType(Enum):
    CITES = "cites"              # 论文引用
    AUTHORED_BY = "authored_by"  # 作者关系
    BELONGS_TO = "belongs_to"    # 归属关系
    SIMILAR_TO = "similar_to"    # 相似关系
    BUILDS_ON = "builds_on"      # 基于关系
```

## 三、核心服务

### 3.1 KGService

```python
class KGService:
    """知识图谱服务"""

    def __init__(self):
        self.vector_store = KGVectorStore()
        self.extractor = KGExtractor()
        self.summarizer = KGSummarizer()

    def add_paper(self, paper: Paper) -> List[Entity]:
        """添加论文到知识图谱"""
        # 1. 提取实体
        entities = self.extractor.extract_entities(paper)

        # 2. 提取关系
        relations = self.extractor.extract_relations(paper)

        # 3. 存储
        for entity in entities:
            self.vector_store.add_entity(entity)
        for relation in relations:
            self.vector_store.add_relation(relation)

        return entities

    def query(self, query: str, depth: int = 2) -> List[dict]:
        """查询知识图谱"""
        # 1. 向量化查询
        query_vec = self.embeddings.encode(query)

        # 2. 查找相关实体
        related = self.vector_store.find_similar(query_vec, top_k=10)

        # 3. 扩展邻居
        return self._expand_subgraph(related, depth=depth)
```

### 3.2 GraphRAG

```python
class KGGraphRAG:
    """基于知识图谱的RAG问答"""

    async def answer(
        self,
        question: str,
        papers: List[Paper],
        top_k: int = 5
    ) -> GraphRAGAnswer:
        """
        1. 从知识图谱检索相关实体
        2. 构建子图
        3. 基于子图生成回答
        """
        # 检索相关论文实体
        entities = self.kg_service.query(question, depth=2)

        # 构建上下文子图
        subgraph = self._build_subgraph(entities)

        # 生成回答
        answer = await self.llm.ainvoke([
            SystemMessage(f"基于以下知识图谱回答问题:\n{subgraph}"),
            HumanMessage(question)
        ])

        return GraphRAGAnswer(
            answer=answer,
            supporting_entities=entities,
            confidence=self._calculate_confidence(entities)
        )
```

### 3.3 社区检测

```python
class KGCommunity:
    """知识图谱社区检测"""

    def detect_communities(self) -> List[Community]:
        """检测知识图谱中的社区"""
        # 使用Louvain算法检测社区
        import networkx as nx
        G = self._build_graph()

        # 社区检测
        from networkx.algorithms.community import louvain_communities
        communities = louvain_communities(G)

        return [
            Community(id=i, nodes=list(nodes))
            for i, nodes in enumerate(communities)
        ]

    def summarize_community(self, community: Community) -> str:
        """生成社区摘要"""
        ...
```

## 四、实体提取

```python
class KGExtractor:
    """知识图谱实体和关系提取"""

    def extract_entities(self, paper: Paper) -> List[Entity]:
        """从论文中提取实体"""
        prompts = [
            # 提取概念
            f"从以下论文摘要中提取关键概念:\n{paper.abstract}",
            # 提取方法
            f"从以下论文中提取研究方法:\n{paper.abstract}",
            # 提取作者
            f"识别以下论文的作者:\n{paper.title}\n{paper.authors}",
        ]

        entities = []
        for prompt in prompts:
            result = await self.llm.ainvoke([
                SystemMessage("你是一个实体提取专家..."),
                HumanMessage(prompt)
            ])
            entities.extend(self._parse_entities(result))

        return entities

    def extract_relations(self, paper: Paper) -> List[Relation]:
        """从论文中提取关系"""
        # 分析引用关系
        # 分析共同作者关系
        # 分析方法继承关系
        ...
```

## 五、混合检索

```python
class KGHybridRetriever:
    """混合检索：向量 + 图结构"""

    def retrieve(
        self,
        query: str,
        top_k: int = 5
    ) -> RetrievalResult:
        """
        1. 向量相似度检索
        2. 图路径扩展
        3. 混合排序
        """
        # 向量检索
        vector_results = self.vector_search(query, top_k * 2)

        # 图扩展
        graph_results = self.graph_expand(vector_results)

        # RRF混合排序
        final_results = self._rrf_merge(vector_results, graph_results)

        return final_results[:top_k]
```

## 六、在工作流中的集成

```python
# langgraph_workflow/nodes/knowledge_graph.py

class KnowledgeGraphNode:
    """知识图谱节点"""

    async def execute(self, state: PaperAgentState) -> PaperAgentState:
        """构建论文知识图谱"""
        papers = state["selected_papers"]

        # 构建图谱
        entities, relations = [], []
        for paper in papers:
            ents, rels = self.kg_service.add_paper(paper)
            entities.extend(ents)
            relations.extend(rels)

        # 检测社区
        communities = self.kg_service.community.detect_communities()

        return {
            "kg_entities": entities,
            "kg_relations": relations,
            "kg_communities": communities
        }
```

---

**更新日期**: 2026-05-02
**基于代码**: `src/agents_v2/knowledge_graph/`
