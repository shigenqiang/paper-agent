# Agent输入输出规范与文本处理

> 本文档记录 PaperAgent 项目中各个 Agent 的输入输出规范，以及文本处理的统一方法。
>
> 对应代码版本：v4.0
> 更新时间：2026-05-03

---

## 一、Agent 基类文本处理

### 1.1 BaseAgent 的通用清理方法

所有 Agent 继承自 `PaperAgentBase` 或 `WritingAgentBase`，共享以下文本清理方法：

#### 1.1.1 `_clean_thinking_blocks()` - 移除思考块

```python
def _clean_thinking_blocks(self, text: str) -> str:
    """清理思考块和参考文献，只保留markdown报告内容"""
    # 0. 处理空响应（API错误时返回的HTML/错误页）
    if not text or text.strip().startswith('<!') or text.strip().startswith('<html'):
        return ""

    # 1. 移除<think>...</think>块
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)

    # 2. 移除开头的分隔线或空行
    text = text.lstrip('-\n')

    return text.strip()
```

**处理场景**：
- MiniMax 等模型返回的思考块
- HTML 错误页面（网关错误时返回）
-参考文献残留

#### 1.1.2 `_fix_utf8_escapes()` - UTF-8 转义修复

```python
def _fix_utf8_escapes(self, text: str) -> str:
    """修复MiniMax返回的UTF-8字节转义序列

    MiniMax有时会在JSON字符串中返回UTF-8字节的转义序列，
    如 \\xe4\\xbd\\xa0 而不是实际的中文字符。
    """
    def replace_escape(match):
        full_match = match.group(0)
        try:
            bytes_list = []
            for i in range(0, len(full_match), 4):
                hex_part = full_match[i+2:i+4]
                bytes_list.append(int(hex_part, 16))
            result_bytes = bytes(bytes_list)
            return result_bytes.decode('utf-8')
        except Exception:
            return full_match

    cleaned = re.sub(r'(?:\\x[0-9a-fA-F]{2})+', replace_escape, text)
    return cleaned
```

#### 1.1.3 `_remove_code_fences()` - 移除代码块标记

```python
def _remove_code_fences(self, text: str) -> str:
    """移除代码块标记 (```json ... ``` 或 ``` ... ```)"""
    cleaned = re.sub(r'```json\s*(.*?)\s*```', r'\1', text, flags=re.DOTALL)
    cleaned = re.sub(r'```\s*(.*?)\s*```', r'\1', cleaned, re.DOTALL)
    return cleaned.strip()
```

#### 1.1.4 `_remove_preamble()` - 移除说明性前导文字

```python
def _remove_preamble(self, text: str) -> str:
    """移除输出前的说明性文字，只保留JSON或实际内容"""
    # 如果文本以 ```json 开头，先提取里面的内容
    json_match = re.match(r'^```json\s*(.*?)\s*```', text, re.DOTALL | re.IGNORECASE)
    if json_match:
        return json_match.group(1).strip()

    # 如果包含 JSON 对象，找到第一个 { 开始
    if '{' in text:
        first_brace = text.index('{')
        if first_brace > 0:
            before_brace = text[:first_brace]
            if '\n' in before_brace:
                text = text[first_brace:]

    return text
```

---

### 二、JSON 处理工具

### 2.1 `pydantic_validator.py` - 统一 JSON 解析

```python
def _clean_json_markdown(text: str) -> str:
    """清理JSON markdown格式，移除思考块"""
    if not text:
        return ""

    # 移除思考块
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)

    text = re.sub(r'^```json\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s*```$', '', text, flags=re.IGNORECASE)
    text = re.sub(r'^```\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s*```$', '', text, flags=re.IGNORECASE)
    text = text.strip()

    if not text:
        return ""

    # 如果不是以 { 开头，尝试找到第一个 { 的位置
    if not text.startswith('{'):
        match = re.search(r'\{', text)
        if match:
            text = text[match.start():]

    # 尝试只提取第一个完整的JSON对象
    if text.startswith('{'):
        try:
            json.loads(text)
            return text
        except json.JSONDecodeError:
            # 找到匹配的闭合括号
            start = text.index('{')
            depth = 0
            end_pos = -1
            for i, c in enumerate(text[start:], start):
                if c == '{':
                    depth += 1
                elif c == '}':
                    depth -= 1
                    if depth == 0:
                        end_pos = i + 1
                        break
            if end_pos > 0:
                return text[start:end_pos]

    return text
```

### 2.2 `parse_json()` - 解析 JSON 返回字典

```python
def parse_json(text: str) -> Optional[Dict[str, Any]]:
    """解析 JSON 文本，返回字典或 None"""
    try:
        cleaned = _clean_json_markdown(text)
        return json.loads(cleaned)
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning(f"JSON parse failed in parse_json: {e}")
        # 尝试正则提取
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return None
```

### 2.3 `parse_with_pydantic()` - 解析并校验 JSON

```python
def parse_with_pydantic(
    text: str,
    model_class: Type[T],
    default_value: Optional[T] = None,
    strict: bool = False
) -> T:
    """使用 Pydantic 模型解析 JSON 文本"""
    try:
        cleaned = _clean_json_markdown(text)
        data = json.loads(cleaned)
        return model_class.model_validate(data)
    except (json.JSONDecodeError, ValidationError) as e:
        logger.warning(f"Pydantic parse failed: {e}")
        # 尝试正则提取
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
                return model_class.model_validate(data)
            except (json.JSONDecodeError, ValidationError):
                pass

        if strict:
            raise

        # 返回默认值
        if default_value is not None:
            return default_value

        return model_class()
```

---

## 三、各 Agent 输入输出规范

### 3.1 TopicAgent - 主题选择

| 项目 | 说明 |
|------|------|
| **输入** | `{ "user_request": "用户的研究兴趣描述" }` |
| **输出** | JSON: `{ title, description, scope, innovation, feasibility, literature_support, key_references, potential_methods, expected_contribution }` |
| **输出字段** | `selected_topic`, `alternative_topics`, `domain_analysis`, `all_candidates` |
| **清理方法** | `_clean_json_markdown()` → `parse_with_pydantic()` |
| **代码位置** | `src/agents_v2/paper_agents/topic_agent.py` |

**典型输入输出示例**：

```
输入: "我想研究人工智能在教育领域的应用"
输出:
{
    "title": "基于大语言模型的个性化自适应学习系统研究",
    "description": "利用LLM技术构建能够根据学生学习行为自动调整难度的智能辅导系统",
    "scope": "聚焦于K-12数学教育场景",
    "innovation": "将生成式AI与知识追踪结合，实现真正的个性化",
    "feasibility": 0.85,
    "literature_support": "深度学习、教育AI、知识追踪相关文献充足",
    "potential_methods": ["大语言模型微调", "知识追踪模型", "强化学习"]
}
```

---

### 3.2 LiteratureAgent - 文献综述

| 项目 | 说明 |
|------|------|
| **输入** | `{ "topic": "研究主题", "research_question": "具体问题" }` |
| **输出** | `{ papers, paper_analyses, research_gaps, search_queries, total_found, total_analyzed }` |
| **清理方法** | `parse_json()` |
| **代码位置** | `src/agents_v2/paper_agents/literature_agent.py` |

**流程**：
1. `_generate_search_queries()` - 生成 8-12 个搜索查询
2. `_multi_engine_search()` - 多引擎并行搜索 + 本地数据库去重
3. `_compute_paper_relevance()` - 嵌入向量计算相关性（ModelScope Qwen3-Embedding）
4. `_deep_read()` - 过滤 embedding_relevance > 0.85，最多 20 篇深度阅读
5. `_identify_gaps()` - 识别研究空白

---

### 3.3 OutlineAgent - 大纲制定

| 项目 | 说明 |
|------|------|
| **输入** | `{ "thesis": "论题", "literature": { paper_analyses } }` |
| **输出** | `{ outline: { structure, chapters, key_arguments } }` |
| **清理方法** | `_clean_json_markdown()` → `parse_with_pydantic()` → `PaperStructure` |
| **代码位置** | `src/agents_v2/paper_agents/outline_agent.py` |

**EnglishFirst 特性**：
- 研究主题先翻译为英文，提升 LLM 理解质量
- 章节信息也进行英文处理
- 通过 `EnglishFirstMixin` 实现

---

### 3.4 DraftWriterAgent - 分节撰写

| 项目 | 说明 |
|------|------|
| **输入** | `{ "outline": {...} }` + context: `{ thesis, literature }` |
| **输出** | `{ chapters: [...], full_draft, chapter_count }` |
| **清理方法** | `_clean_thinking_blocks()` |
| **代码位置** | `src/agents_v2/paper_agents/draft_writer.py` |

**章节类型对应**：
- `introduction` → `_write_introduction()`
- `literature review` → `_write_literature_review()`
- `methodology` → `_write_methodology()`
- `results` → `_write_results()`
- `discussion` → `_write_discussion()`
- `conclusion` → `_write_conclusion()`

---

### 3.5 ReportRefinerAgent - 报告精炼

| 项目 | 说明 |
|------|------|
| **输入** | `{ "draft": "初稿", "focus_areas": [], "max_iterations": 3, "quality_threshold": 0.7 }` |
| **输出** | `{ original_draft, final_draft, improvement_report, iterations_completed, final_quality_score }` |
| **清理方法** | `_clean_text_output()` |
| **代码位置** | `src/agents_v2/writing/report_refiner.py` |

```python
def _clean_text_output(self, text: str) -> str:
    """清理文本输出，移除思考块等无用部分，保留markdown格式"""
    if not text:
        return text
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()
```

---

### 3.6 SmartReviserAgent - 智能改稿

| 项目 | 说明 |
|------|------|
| **输入** | `{ "original_text": "原文", "feedback": "修改意见", "highlight_changes": true }` |
| **输出** | `{ original_text, revised_text, revision_report, feedback_categories, total_revisions }` |
| **清理方法** | `_clean_text_output()` |
| **代码位置** | `src/agents_v2/writing/smart_reviser.py` |

**流程**：
1. `_parse_feedback()` - 解析意见
2. `_categorize_feedback()` - 分类意见（content/structure/language/citation/logic/format）
3. `_apply_revisions()` - 执行修改
4. `_generate_revision_report()` - 生成报告

---

### 3.7 LanguagePolisherAgent - 语言润色

| 项目 | 说明 |
|------|------|
| **输入** | `{ "text": "待润色文本", "language": "zh|en" }` |
| **输出** | `{ diagnosis, overall_quality, polished_text, summary }` |
| **清理方法** | `_clean_text_output()` (复杂版) |
| **代码位置** | `src/agents_v2/writing/smart_reviser.py` |

**诊断维度**：
- `grammar_issues` - 语法错误
- `style_issues` - 风格问题（口语化、主观性）
- `terminology_issues` - 术语不一致

```python
def _clean_text_output(self, text: str) -> str:
    """清理文本输出，移除思考块、代码块标记、诊断信息等无用部分"""
    import re
    # 1. 移除思考块
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    # 2. 移除 markdown 代码块标记
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    text = re.sub(r'```$', '', text)
    # 3. 移除诊断相关字段
    text = re.sub(r'"diagnosis"\s*:.*?(?="[a-z_]+"\s*:|\}\s*$)', '', text, flags=re.DOTALL)
    # ... 更多清理规则
    # 7. 清理多余的空行
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()
```

---

### 3.8 TopicRefinerAgent - 选题精炼

| 项目 | 说明 |
|------|------|
| **输入** | `{ "user_idea": "选题", "user_level": "硕士", "available_time": "6个月" }` |
| **输出** | `{ diagnosis, main_issues, severity, recommendations, suggested_topic, reasoning }` |
| **清理方法** | `_clean_json_markdown()` |
| **代码位置** | `src/agents_v2/problem_oriented/topic_refiner.py` |

**诊断结构**：
```python
{
    "diagnosis": {
        "scope": "too_broad | appropriate | too_narrow",
        "innovation": "high | medium | low",
        "feasibility": 0.0-1.0,
        "value": "high | medium | low"
    },
    "main_issues": ["问题列表"],
    "severity": {"问题名": 0.0-1.0},
    "recommendations": ["建议列表"],
    "suggested_topic": "优化后的选题",
    "reasoning": "分析推理过程"
}
```

---

### 3.9 LiteratureMapperAgent - 文献映射

| 项目 | 说明 |
|------|------|
| **输入** | `{ "topic": "主题", "existing_papers": [], "search_queries": [] }` |
| **输出** | `{ literature_map, categorized_literature, research_gaps, total_papers_found }` |
| **清理方法** | `_clean_json_markdown()` |
| **代码位置** | `src/agents_v2/problem_oriented/literature_mapper.py` |

**文献分类**：
- `methods` - 方法论研究
- `applications` - 应用研究
- `surveys` - 综述文章
- `critiques` - 批评/局限性研究
- `related` - 相关但不直接相关

---

### 3.10 DigestReportAgent - 学术资讯快报

| 项目 | 说明 |
|------|------|
| **输入** | `{ papers, keywords, digest_type, date_range, sources }` |
| **输出** | `{ report, theme_groups, paper_count, themes, report_type }` |
| **报告类型** | daily (500-800字), weekly (1000-1500字), monthly (2000-3000字) |
| **代码位置** | `src/agents_v2/paper_agents/digest_agent.py` |

**生成策略**：
- `daily`: 今日热点 + 代表性论文 5 篇
- `weekly`: 本周概览 + 主题聚类 + 趋势分析
- `monthly`: 月度概览 + 深度分析 + 前沿展望

---

## 四、输入输出模型定义

### 4.1 AgentOutput - 统一输出格式

```python
class AgentOutput(BaseModel):
    """Agent标准输出"""
    success: bool
    result: Any = None
    agent_name: str
    reasoning: Optional[str] = None
    next_actions: List[str] = []
    error: Optional[str] = None
    metadata: Dict[str, Any] = {}
    quality_score: float = 0.0
    # 诊断型Agent额外字段
    diagnosed_issues: List[str] = []
    recommendations: List[str] = []
```

### 4.2 WritingOutput - 写作 Agent 输出

```python
class WritingOutput(BaseModel):
    """标准输出"""
    success: bool
    result: Any = None
    agent_name: str
    reasoning: Optional[str] = None
    next_actions: List[str] = []
    error: Optional[str] = None
    metadata: Dict[str, Any] = {}
    quality_score: float = 0.0
    # 诊断型Agent额外字段
    diagnosed_issues: List[str] = []
    recommendations: List[str] = []
```

---

## 五、JSON Schema 规范

### 5.1 Pydantic 模型定义

```python
class DomainAnalysis(BaseModel):
    """领域分析结果模型"""
    main_domain: str = "未知"
    sub_domains: List[str] = []
    keywords: List[str] = []
    related_fields: List[str] = []
    research_level: str = "硕士"

class TopicCandidate(BaseModel):
    """主题候选模型"""
    title: str = ""
    description: str = ""
    scope: str = ""
    innovation: str = ""
    feasibility: float = 0.7
    literature_support: str = ""
    key_references: List[str] = []
    potential_methods: List[str] = []
    expected_contribution: str = ""

class PaperStructure(BaseModel):
    """论文结构"""
    title: str = ""
    paper_type: str = "empirical"
    chapters: List[ChapterOutline] = []
    total_chapters: int = 5
    word_count_estimate: int = 8000

class ChapterOutline(BaseModel):
    """章节大纲"""
    name: str = ""
    purpose: str = ""
    content_guidance: str = ""
    main_points: List[str] = []
    citations_needed: List[str] = []
    order: int = 0
```

---

## 六、质量阈值标准

### 6.1 各阶段阈值

```python
QUALITY_THRESHOLDS = {
    "diagnostic": 6.0,   # 诊断阶段不需要太高
    "topic": 7.0,
    "literature": 7.0,
    "methodology": 7.0,
    "writing": 7.0,
    "polish": 8.0        # 最终润色需要更高
}
```

### 6.2 质量评分维度

| 维度 | 说明 |
|------|------|
| 结构完整性 | 论文结构是否清晰完整 |
| 逻辑连贯性 | 论证逻辑是否严密 |
| 创新性 | 研究贡献是否有创新 |
| 实证充分性 | 实验证据是否充分 |
| 语言表达 | 语言是否准确流畅 |

---

*文档版本: v1.0*
*更新时间: 2026-05-03*
