# Paper Agent 全链路深度研究开发计划 - 迭代版
**项目**: Paper Agent
**版本**: v0.4 (深度研究迭代版)
**研究指导**: Agent深度研究提示词
**迭代次数**: 20次
**最后更新**: 2026-04-27

---

## 一、深度研究发现的遗漏点概览

基于《Agent深度研究提示词》中的研究问题，对现有系统进行差距分析：

### 1.1 输入处理层遗漏点

| 研究问题 | 当前状态 | 遗漏点 | 优先级 |
|---------|---------|--------|--------|
| 意图识别的置信度校准 | ⚠️ 基础实现 | 缺少基于历史数据的置信度校准机制 | P1 |
| 多意图同时存在的处理 | ❌ 无 | 用户输入可能包含多个意图，需要意图消歧对话 | P0 |
| 输入验证的完整性 | ⚠️ 基础实现 | 缺少安全性和有效性保障的详细验证 | P1 |
| 中英文混合输入处理 | ⚠️ 部分实现 | 跨语言检索和混合输入处理不完善 | P1 |
| 恶意输入防护 | ❌ 无 | 缺少注入攻击检测和防护 | P0 |

### 1.2 检索链路遗漏点

| 研究问题 | 当前状态 | 遗漏点 | 优先级 |
|---------|---------|--------|--------|
| 查询扩展（同义词/相关词） | ⚠️ 基础实现 | 语义级查询扩展不完善 | P1 |
| 查询改写（口语化→检索式） | ⚠️ 基础实现 | 缺少查询理解和改写机制 | P1 |
| 嵌套查询条件处理 | ❌ 无 | 复杂查询条件解析不完整 | P2 |
| 多源结果融合 | ⚠️ 基础实现 | ArXiv/PubMed/SS的融合策略简单 | P1 |
| HyDE检索增强 | ❌ 无 | 假设性文档嵌入增强检索 | P2 |
| 检索结果质量评估指标 | ⚠️ 基础实现 | 缺少系统化的质量评估体系 | P1 |

### 1.3 PDF解析链路遗漏点

| 研究问题 | 当前状态 | 遗漏点 | 优先级 |
|---------|---------|--------|--------|
| 双栏排版正确分栏 | ❌ 无 | PDF双栏布局检测不准确 | P0 |
| 数学公式提取与渲染 | ⚠️ 基础实现 | 公式检测→LaTeX转换→渲染流程不完整 | P1 |
| 参考文献完整性提取 | ⚠️ 基础实现 | 作者、年份、期刊解析准确率不足 | P1 |
| 图表标题与正文关联 | ❌ 无 | 图表引用关系未建立 | P2 |
| 表格的检测→解析→结构化 | ⚠️ 基础实现 | 复杂表格解析准确率低 | P1 |
| 内容理解（核心贡献提取） | ❌ 无 | 缺少论文贡献自动提取机制 | P1 |

### 1.4 生成链路遗漏点

| 研究问题 | 当前状态 | 遗漏点 | 优先级 |
|---------|---------|--------|--------|
| 各章节撰写要点控制 | ⚠️ 基础实现 | 摘要/引言/方法/结果/讨论的生成策略不细分 | P1 |
| 逻辑连贯性保证 | ⚠️ 基础实现 | 长文本生成的一致性机制不完善 | P0 |
| Self-RAG在生成中应用 | ⚠️ 部分实现 | 生成时缺少自我反思和质量控制 | P1 |
| 生成内容的自我评估 | ⚠️ 基础实现 | 缺少生成后的自动质量评估 | P1 |
| 抄袭检测与原创性保证 | ⚠️ 基础实现 | 缺少生成内容的原创性验证 | P1 |
| 不同期刊格式适配 | ⚠️ 部分实现 | 格式转换规则不完善 | P2 |

### 1.5 输出链路遗漏点

| 研究问题 | 当前状态 | 遗漏点 | 优先级 |
|---------|---------|--------|--------|
| 渲染效果预览机制 | ❌ 无 | 预览LaTeX/PDF渲染效果 | P2 |
| 输出内容完整性检查 | ⚠️ 基础实现 | 缺少格式规范的符合性验证 | P1 |
| 用户增量更新支持 | ❌ 无 | 用户修改后的增量更新机制 | P1 |
| 版本管理策略 | ❌ 无 | 论文版本历史管理 | P2 |
| 用户修改反馈支持 | ⚠️ 部分实现 | 反馈→修改的闭环不完整 | P1 |

---

## 二、20次迭代详细开发计划

### 第1次迭代：输入处理层强化（一）

**目标**: 解决意图识别的置信度校准和多意图处理问题

#### 1.1 意图置信度校准器

```python
# src/agents_v2/unified/intent_router.py 新增

class IntentConfidenceCalibrator:
    """
    意图置信度校准器

    基于历史数据校准意图识别的置信度，防止模型过度自信或过度不自信
    """

    def __init__(self):
        # 校准数据：{intent_type: [(raw_confidence, actual_correct), ...]}
        self._calibration_data: Dict[IntentType, List[Tuple[float, bool]]] = defaultdict(list)
        self._temperature = 1.0

    def recordOutcome(self, intent_type: IntentType, raw_confidence: float, actual_correct: bool) -> None:
        """记录识别结果用于后续校准"""
        self._calibration_data[intent_type].append((raw_confidence, actual_correct))
        # 保持最近100条记录
        if len(self._calibration_data[intent_type]) > 100:
            self._calibration_data[intent_type] = self._calibration_data[intent_type][-100:]

    def calibrate(self, intent_type: IntentType, raw_confidence: float) -> float:
        """
        校准置信度

        使用Platt Scaling或Isotonic Regression的简化版
        """
        data = self._calibration_data.get(intent_type, [])
        if len(data) < 10:
            return raw_confidence  # 数据不足，返回原始置信度

        # 计算校准后的置信度
        # 统计不同置信度区间的准确率
        bins = [(0.0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.0)]
        bin_accuracies = []

        for low, high in bins:
            bin_data = [(c, correct) for c, correct in data if low <= c < high]
            if bin_data:
                accuracy = sum(1 for _, correct in bin_data if correct) / len(bin_data)
                bin_accuracies.append((low, high, accuracy))

        # 使用区间准确率校准
        for low, high, accuracy in bin_accuracies:
            if low <= raw_confidence < high:
                # 平滑处理
                return raw_confidence * (1 - self._temperature) + accuracy * self._temperature

        return raw_confidence
```

#### 1.2 多意图检测与消歧器

```python
# src/agents_v2/unified/intent_router.py 新增

class MultiIntentDetector:
    """
    多意图检测与消歧器

    检测用户输入中的多个意图，并在模糊时启动消歧对话
    """

    def __init__(self, llm: Any = None):
        self.llm = llm
        self._disambiguation_prompts = {
            (IntentType.LITERATURE_SEARCH, IntentType.TOPIC_SELECT):
                "您是想搜索论文，还是想让我们帮您选题？这两个是不同的任务。",
            (IntentType.LANGUAGE_POLISH, IntentType.FULL_PAPER):
                "您是想润色现有论文，还是想从头生成一篇新论文？",
            # 更多组合...
        }

    async def detectMultiIntent(self, user_request: str) -> List[IntentCandidate]:
        """检测多意图"""
        prompt = f"""
分析以下用户请求，可能存在多个意图：

用户请求：{user_request}

请识别：
1. 主要意图（置信度最高）
2. 可能存在的次要意图
3. 这些意图之间的关系（并行/顺序/依赖）

返回JSON格式：
{{
    "primary_intent": {{
        "type": "意图类型",
        "confidence": 0.0-1.0,
        "reasoning": "判断理由"
    }},
    "secondary_intents": [
        {{"type": "类型", "confidence": 0.0-1.0, "relation": "并行/顺序"}}
    ],
    "requires_clarification": true/false
}}
"""
        # 调用LLM解析
        # 返回意图候选列表

    async def generateDisambiguationQuestion(
        self,
        intents: List[IntentCandidate]
    ) -> str:
        """生成消歧问题"""
        # 根据意图组合选择预设问题
        key = tuple(sorted([i.intent_type for i in intents]))
        if key in self._disambiguation_prompts:
            return self._disambiguation_prompts[key]

        # 动态生成
        return f"您的请求可能包含多个意图（{', '.join(i.intent_type.value for i in intents)}），请明确您的主要目标。"
```

#### 1.3 输入安全验证器

```python
# src/agents_v2/validators.py 增强

class InputSecurityValidator:
    """
    输入安全验证器

    检测和防护各类注入攻击和恶意输入
    """

    def __init__(self):
        self._injection_patterns = [
            # Prompt注入模式
            r'ignore\s+previous\s+instructions',
            r'ignore\s+all\s+previous',
            r'disregard\s+system\s+prompt',
            # 角色扮演绕过
            r'you\s+are\s+now\s+',
            r'pretend\s+to\s+be',
            # 编码绕过
            r'\\x[0-9a-f]{2}',
            r'\\u[0-9a-f]{4}',
        ]
        self._suspicious_domains = ['example.com', 'test.com']

    def validate(self, text: str) -> ValidationResult:
        """验证输入安全性"""
        issues = []

        # 1. Prompt注入检测
        for pattern in self._injection_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                issues.append(SecurityIssue(
                    type="prompt_injection",
                    severity="high",
                    description=f"检测到可能的prompt注入尝试"
                ))

        # 2. 恶意URL检测
        urls = re.findall(r'https?://[^\s]+', text)
        for url in urls:
            domain = urlparse(url).netloc
            if domain in self._suspicious_domains:
                issues.append(SecurityIssue(
                    type="suspicious_url",
                    severity="medium",
                    description=f"检测到可疑域名: {domain}"
                ))

        # 3. 恶意代码检测
        if self._contains_malicious_code(text):
            issues.append(SecurityIssue(
                type="malicious_code",
                severity="high",
                description="检测到可能的恶意代码"
            ))

        return ValidationResult(
            is_safe=len([i for i in issues if i.severity == "high"]) == 0,
            issues=issues,
            sanitized_text=self._sanitize(text, issues)
        )

    def _sanitize(self, text: str, issues: List[SecurityIssue]) -> str:
        """净化问题输入"""
        sanitized = text
        # 移除检测到的注入模式
        for issue in issues:
            if issue.type == "prompt_injection":
                sanitized = re.sub(r'ignore\s+previous\s+instructions.*', '', sanitized, flags=re.IGNORECASE)
        return sanitized
```

#### 1.4 验收标准

| 验收项 | 标准 | 检查点 |
|--------|------|--------|
| 置信度校准 | 校准后准确率提升15% | 对比100+历史记录 |
| 多意图检测 | 识别准确率>85% | 测试混合意图输入 |
| 意图消歧 | 消歧对话自然流畅 | 用户测试 |
| 安全验证 | 注入检测率>99% | 测试各类攻击 |

---

### 第2次迭代：输入处理层强化（二）

**目标**: 完善多语言处理和跨语言检索

#### 2.1 跨语言查询处理器

```python
# src/agents_v2/multilingual/processor.py 新增

class CrossLingualQueryProcessor:
    """
    跨语言查询处理器

    处理中英文混合输入，实现跨语言检索
    """

    def __init__(self):
        self._translation_cache = {}
        self._lang_detector = None  # 使用langdetect

    async def detectLanguage(self, text: str) -> str:
        """检测语言"""
        if self._lang_detector is None:
            import langdetect
            self._lang_detector = langdetect

        return self._lang_detector.detect(text)

    async def translateQuery(
        self,
        query: str,
        source_lang: str,
        target_lang: str
    ) -> str:
        """翻译查询"""
        cache_key = f"{source_lang}:{target_lang}:{query}"
        if cache_key in self._translation_cache:
            return self._translation_cache[cache_key]

        # 调用翻译API
        translated = await self._callTranslationAPI(query, source_lang, target_lang)
        self._translation_cache[cache_key] = translated
        return translated

    async def expandCrossLingual(
        self,
        query: str
    ) -> List[QueryExpansion]:
        """
        跨语言查询扩展

        将中文查询扩展为中英文双语查询
        """
        lang = await self.detectLanguage(query)

        expansions = [QueryExpansion(text=query, language=lang)]

        if lang == "zh":
            # 翻译为英文
            en_query = await self.translateQuery(query, "zh", "en")
            expansions.append(QueryExpansion(text=en_query, language="en"))

            # 添加可能的翻译变体
            en_variants = await self._generateTranslationVariants(en_query)
            expansions.extend([
                QueryExpansion(text=v, language="en") for v in en_variants
            ])

        elif lang == "en":
            # 翻译为中文
            zh_query = await self.translateQuery(query, "en", "zh")
            expansions.append(QueryExpansion(text=zh_query, language="zh"))

        return expansions

    async def processMixedLanguageInput(
        self,
        text: str
    ) -> ProcessedInput:
        """
        处理混合语言输入

        识别各语言部分并分别处理
        """
        # 分割中英文部分
        segments = self._splitByLanguage(text)

        processed_segments = []
        for segment in segments:
            if segment.is_english:
                processed_segments.append(ProcessedSegment(
                    text=segment.text,
                    language="en",
                    intent=await self._classifyIntent(segment.text),
                    entities=await self._extractEntities(segment.text, "en")
                ))
            else:
                processed_segments.append(ProcessedSegment(
                    text=segment.text,
                    language="zh",
                    intent=await self._classifyIntent(segment.text),
                    entities=await self._extractEntities(segment.text, "zh")
                ))

        return ProcessedInput(segments=processed_segments)
```

#### 2.2 跨语言检索器

```python
# src/agents_v2/retrieval/cross_lingual_retriever.py 新增

class CrossLingualRetriever:
    """
    跨语言检索器

    支持中英文混合检索和跨语言检索
    """

    def __init__(self):
        self._en_retriever = None  # 英文检索器
        self._zh_retriever = None  # 中文检索器
        self._cross_encoder = None  # 跨语言编码器

    async def retrieve(
        self,
        query: str,
        top_k: int = 10
    ) -> List[CrossLingualResult]:
        """
        跨语言检索

        1. 检测语言
        2. 扩展为双语查询
        3. 分别在对应索引检索
        4. 使用跨语言编码器融合结果
        """
        # 1. 跨语言扩展
        expansions = await self._cross_lingual_expander.expandCrossLingual(query)

        # 2. 分语言检索
        en_results = []
        zh_results = []

        for exp in expansions:
            if exp.language == "en":
                results = await self._en_retriever.retrieve(exp.text, top_k)
                en_results.extend(results)
            else:
                results = await self._zh_retriever.retrieve(exp.text, top_k)
                zh_results.extend(results)

        # 3. 跨语言编码器重排
        fused_results = await self._cross_encode_and_rerank(
            query=query,
            en_results=en_results,
            zh_results=zh_results
        )

        return fused_results[:top_k]

    async def _cross_encode_and_rerank(
        self,
        query: str,
        en_results: List,
        zh_results: List
    ) -> List[CrossLingualResult]:
        """
        使用跨语言编码器融合结果

        e5-mistral、bge-m3 等支持跨语言
        """
        all_docs = [r.content for r in en_results + zh_results]

        # 使用跨语言编码器获取统一空间的向量
        embeddings = await self._cross_encoder.encode(query, all_docs)

        # 计算与查询的相似度
        query_embedding = embeddings[0]
        doc_embeddings = embeddings[1:]

        scores = self._cosine_similarity(query_embedding, doc_embeddings)

        # 组合结果
        results = []
        for i, (doc, score) in enumerate(zip(all_docs, scores)):
            lang = "en" if i < len(en_results) else "zh"
            results.append(CrossLingualResult(
                document=doc,
                score=score,
                language=lang,
                is_translated=lang != await self._detectLanguage(query)
            ))

        results.sort(key=lambda x: x.score, reverse=True)
        return results
```

#### 2.3 验收标准

| 验收项 | 标准 | 检查点 |
|--------|------|--------|
| 语言检测 | 准确率>95% | 测试混合语言文本 |
| 翻译质量 | BLEU>0.8 | 对比参考翻译 |
| 跨语言检索 | 中英混合准确率>80% | 测试混合查询 |
| 结果融合 | 语义相关性提升20% | 对比单语言检索 |

---

### 第3次迭代：检索链路强化（一）

**目标**: 完善查询理解和查询改写机制

#### 3.1 查询理解与分类器

```python
# src/agents_v2/retrieval/query_understanding.py 新增

class QueryUnderstandingPipeline:
    """
    查询理解管道

    完整流程：解析 → 分类 → 扩展 → 改写
    """

    def __init__(self):
        self._parser = QueryParser()
        self._classifier = EnhancedQueryClassifier()
        self._expander = SemanticQueryExpander()
        self._rewriter = QueryRewriter()

    async def understand(
        self,
        query: str,
        context: Optional[Dict] = None
    ) -> QueryUnderstanding:
        """
        完整查询理解

        Returns:
            QueryUnderstanding: 包含所有理解结果
        """
        # 1. 查询解析
        parsed = self._parser.parse(query)
        structured_query = self._parser.toStructuredQuery(parsed)

        # 2. 查询分类
        classification = await self._classifier.classify(parsed, context)

        # 3. 查询意图提取
        intent = await self._extractIntent(parsed)

        # 4. 查询约束提取
        constraints = await self._extractConstraints(parsed)

        # 5. 查询扩展
        if classification.needs_expansion:
            expanded = await self._expander.expand(parsed)
        else:
            expanded = [QueryVariant(text=query, type="original")]

        # 6. 查询改写
        rewritten = await self._rewriter.rewrite(parsed, context)

        return QueryUnderstanding(
            original_query=query,
            structured_query=structured_query,
            classification=classification,
            intent=intent,
            constraints=constraints,
            expanded_queries=expanded,
            rewritten_query=rewritten
        )


@dataclass
class StructuredQuery:
    """结构化查询"""
    main_concept: str                    # 主要概念
    modifiers: List[str]                # 限定词
    operators: List[QueryOperator]       # AND/OR/NOT
    field_specs: List[FieldSpec]       # 字段限定 (title:, author:)
    date_range: Optional[DateRange]    # 时间范围
    exclusions: List[str]               # 排除词


@dataclass
class QueryOperator:
    """查询操作符"""
    operator: str  # AND/OR/NOT
    term: str


@dataclass
class FieldSpec:
    """字段限定"""
    field: str   # title/author/abstract
    value: str
```

#### 3.2 语义查询扩展器

```python
# src/agents_v2/retrieval/semantic_expander.py 新增

class SemanticQueryExpander:
    """
    语义查询扩展器

    基于词向量和知识图谱进行语义级扩展
    """

    def __init__(self):
        self._word_vector_model = None  # e5-mistral 或 bge
        self._knowledge_graph = None
        self._synonym_dict = self._loadSynonymDict()

    async def expand(
        self,
        query: ParsedQuery
    ) -> List[QueryVariant]:
        """语义扩展查询"""
        variants = []

        # 1. 同义词扩展
        synonyms = self._expandSynonyms(query.main_concept)
        for syn in synonyms:
            variants.append(QueryVariant(
                text=self._replaceTerm(query.original, query.main_concept, syn),
                type="synonym",
                confidence=0.9
            ))

        # 2. 上下位词扩展
        hypernyms = await self._getHypernyms(query.main_concept)
        for hyper in hypernyms:
            variants.append(QueryVariant(
                text=f"{hyper} {query.main_concept}",
                type="hypernym",
                confidence=0.8
            ))

        # 3. 相关概念扩展
        related = await self._getRelatedConcepts(query.main_concept)
        for rel in related:
            variants.append(QueryVariant(
                text=f"{query.main_concept} {rel}",
                type="related",
                confidence=0.7
            ))

        # 4. 嵌入向量扩展
        embedding_neighbors = await self._getEmbeddingNeighbors(query.main_concept, top_k=5)
        for neighbor in embedding_neighbors:
            variants.append(QueryVariant(
                text=neighbor,
                type="embedding",
                confidence=0.75
            ))

        return variants[:10]  # 限制扩展数量

    async def _getEmbeddingNeighbors(
        self,
        term: str,
        top_k: int = 5
    ) -> List[str]:
        """获取向量空间中的近邻"""
        if not self._word_vector_model:
            return []

        # 获取词向量
        query_vec = self._word_vector_model.encode(term)

        # 从预计算的索引中搜索近邻
        neighbors = self._vector_index.search(query_vec, top_k)

        return neighbors

    def _loadSynonymDict(self) -> Dict[str, List[str]]:
        """加载同义词词典"""
        # 中文同义词林
        return {
            "深度学习": ["深度神经网络", "deep learning", "DL"],
            "机器学习": ["机器学习方法", "machine learning", "ML"],
            "神经网络": ["neural network", "NN"],
            # 更多同义词...
        }
```

#### 3.3 查询改写器

```python
# src/agents_v2/retrieval/query_rewriter.py 新增

class QueryRewriter:
    """
    查询改写器

    将口语化查询改写为适合检索的格式
    """

    def __init__(self, llm: Any = None):
        self.llm = llm

    async def rewrite(
        self,
        query: ParsedQuery,
        context: Optional[Dict] = None
    ) -> str:
        """
        改写查询

        策略：
        1. 口语化→正式表达
        2. 缩写→全称
        3. 问答→陈述
        4. 添加检索友好的限定词
        """
        prompt = f"""
将以下口语化查询改写为适合学术论文检索的格式：

原始查询：{query.original}

改写要求：
1. 保持核心语义不变
2. 使用正式的学术表达
3. 缩写词扩展为全称
4. 问答形式改为陈述形式
5. 添加必要的限定词（如"论文"、"研究"等）

改写后的查询："""

        try:
            response = await self.llm.agenerate([prompt])
            rewritten = response.generations[0][0].text.strip()
            return rewritten
        except Exception as e:
            logger.error(f"Query rewriting failed: {e}")
            return query.original

    async def rewriteForFormat(
        self,
        query: str,
        target_format: str  # "arxiv" / "pubmed" / "semantic_scholar"
    ) -> str:
        """根据目标格式改写查询"""
        if target_format == "arxiv":
            return self._rewriteForArxiv(query)
        elif target_format == "pubmed":
            return self._rewriteForPubmed(query)
        else:
            return query

    def _rewriteForArxiv(self, query: str) -> str:
        """为ArXiv格式改写"""
        # ArXiv支持简单布尔查询
        # 添加 AND 替换模糊匹配
        rewritten = query.replace(" ", " AND ")
        # 移除复杂标点
        rewritten = re.sub(r'[^\w\sAND]', '', rewritten)
        return rewritten

    def _rewriteForPubmed(self, query: str) -> str:
        """为PubMed格式改写"""
        # PubMed使用 MeSH 词
        # 简化处理，实际应该用MeSH词表映射
        # 添加[Title/Abstract]限定
        return f"({query})[Title/Abstract]"
```

#### 3.4 验收标准

| 验收项 | 标准 | 检查点 |
|--------|------|--------|
| 查询解析 | 结构化准确率>90% | 测试各类查询格式 |
| 语义扩展 | 扩展质量评分>4.5/5 | 人工评估 |
| 查询改写 | 检索效果提升20% | A/B测试 |
| 布尔查询 | 支持AND/OR/NOT | 测试复杂查询 |

---

### 第4次迭代：检索链路强化（二）

**目标**: 实现多源检索融合和质量评估

#### 4.1 多源检索协调器

```python
# src/agents_v2/retrieval/multi_source_coordinator.py 新增

class MultiSourceRetriever:
    """
    多源检索协调器

    协调ArXiv/PubMed/Semantic Scholar检索并融合结果
    """

    def __init__(self):
        self._sources = {
            "arxiv": ArxivRetriever(),
            "pubmed": PubmedRetriever(),
            "semantic_scholar": SemanticScholarRetriever()
        }
        self._fusion_strategy = AdaptiveFusion()

    async def retrieve(
        self,
        query: QueryUnderstanding,
        sources: List[str] = None,
        top_k: int = 20
    ) -> List[FusedResult]:
        """
        多源检索并融合

        1. 并行向各源发送检索请求
        2. 获取各源结果
        3. 融合重排
        """
        if sources is None:
            sources = list(self._sources.keys())

        # 并行检索
        tasks = []
        for source in sources:
            if source in self._sources:
                tasks.append(self._retrieveFromSource(source, query, top_k))

        results_by_source = await asyncio.gather(*tasks, return_exceptions=True)

        # 融合结果
        all_results = []
        for source, results in zip(sources, results_by_source):
            if isinstance(results, Exception):
                logger.warning(f"Source {source} failed: {results}")
                continue

            for result in results:
                result.source = source
                all_results.append(result)

        # 融合重排
        fused = await self._fusion_strategy.fuse(all_results, query)

        return fused[:top_k]


class AdaptiveFusionStrategy:
    """
    自适应融合策略

    根据查询类型和源特性动态选择融合方法
    """

    # 不同融合方法
    FUSION_METHODS = {
        "rrf": self._reciprocalRankFusion,      # 倒数排名融合
        "borda": self._bordaCountFusion,        # Borda计数融合
        "weighted": self._weightedScoreFusion,   # 加权分数融合
        "langchan": self._languageModelFusion    # 语言模型融合
    }

    def fuse(
        self,
        results: List[SourceResult],
        query: QueryUnderstanding
    ) -> List[FusedResult]:
        """自适应融合"""
        # 1. 分析查询特性
        query_type = query.classification.type

        # 2. 选择融合方法
        if query_type == QueryType.FACT_LOOKUP:
            method = "rrf"  # 事实查询适合RRF
        elif query_type == QueryType.COMPLEX_REASONING:
            method = "weighted"  # 复杂查询用加权
        else:
            method = "borda"  # 默认用Borda

        # 3. 执行融合
        fusion_func = self.FUSION_METHODS[method]
        fused = fusion_func(results, query)

        # 4. 可选：使用重排模型优化
        if len(fused) > 10:
            fused = await self._cross_encoder_rerank(fused, query)

        return fused

    def _reciprocalRankFusion(
        self,
        results: List[SourceResult],
        k: int = 60
    ) -> List[FusedResult]:
        """倒数排名融合 (RRF)"""
        doc_scores = defaultdict(float)

        for result in results:
            rank = result.rank  # 各源中的排名
            doc_scores[result.doc_id] += 1.0 / (k + rank)

        # 归一化
        max_score = max(doc_scores.values()) if doc_scores else 1
        for doc_id in doc_scores:
            doc_scores[doc_id] /= max_score

        sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)

        return [
            FusedResult(doc_id=doc_id, score=score, method="rrf")
            for doc_id, score in sorted_docs
        ]
```

#### 4.2 检索质量评估器

```python
# src/agents_v2/retrieval/quality_evaluator.py 新增

class RetrievalQualityEvaluator:
    """
    检索质量评估器

    评估检索结果的质量并生成诊断报告
    """

    def __init__(self):
        self._metrics = {
            "relevance": RelevanceMetric(),
            "diversity": DiversityMetric(),
            "coverage": CoverageMetric(),
            "freshness": FreshnessMetric()
        }

    async def evaluate(
        self,
        results: List[RetrievalResult],
        query: QueryUnderstanding,
        ground_truth: Optional[List[str]] = None
    ) -> QualityEvaluation:
        """
        全面评估检索质量
        """
        evaluations = {}

        for metric_name, metric in self._metrics.items():
            evaluations[metric_name] = await metric.compute(
                results=results,
                query=query
            )

        # 综合评分
        weights = {"relevance": 0.4, "diversity": 0.2, "coverage": 0.2, "freshness": 0.2}
        overall_score = sum(
            evaluations[name].score * weights.get(name, 0.25)
            for name in evaluations
        )

        # 生成诊断
        diagnosis = self._generateDiagnosis(evaluations)

        return QualityEvaluation(
            overall_score=overall_score,
            metric_scores=evaluations,
            diagnosis=diagnosis,
            suggestions=self._generateSuggestions(evaluations)
        )

    def _generateDiagnosis(self, evaluations: Dict[str, MetricResult]) -> str:
        """生成质量诊断"""
        issues = []

        if evaluations["relevance"].score < 0.6:
            issues.append("检索结果相关性较低，可能需要扩展查询或更换检索策略")

        if evaluations["diversity"].score < 0.5:
            issues.append("结果多样性不足，可能缺乏不同角度的文献")

        if evaluations["coverage"].score < 0.6:
            issues.append("领域覆盖不全面，建议补充相关子领域的检索")

        if evaluations["freshness"].score < 0.4:
            issues.append("检索结果偏旧，建议添加时间范围限定")

        return "\n".join(issues) if issues else "检索质量良好"


@dataclass
class MetricResult:
    """指标结果"""
    name: str
    score: float  # 0-1
    details: Dict[str, Any]
```

#### 4.3 验收标准

| 验收项 | 标准 | 检查点 |
|--------|------|--------|
| 多源检索 | 3个源正确融合 | 测试各源结果合并 |
| RRF融合 | 排名稳定性测试 | 多次运行一致 |
| 质量评估 | 4个维度评估 | 与人工评估对比 |
| 自适应策略 | 准确选择融合方法 | 测试不同查询类型 |

---

### 第5次迭代：PDF解析链路强化（一）

**目标**: 解决双栏排版检测和公式处理问题

#### 5.1 双栏排版检测器

```python
# src/agents_v2/pdf_layout/detector.py 新增

class LayoutDetector:
    """
    页面布局检测器

    检测PDF的排版方式（单栏/双栏/混排）
    """

    def __init__(self):
        self._column_detector = ColumnDetector()
        self._reading_order = ReadingOrderResolver()

    async def detectLayout(self, page_image) -> LayoutAnalysis:
        """检测页面布局"""
        # 1. 分析文本块分布
        text_blocks = self._extractTextBlocks(page_image)

        # 2. 检测分栏模式
        columns = self._column_detector.detectColumns(text_blocks)

        # 3. 确定阅读顺序
        reading_order = self._reading_order.resolve(columns)

        # 4. 检测特殊元素
        figures = self._detectFigures(page_image)
        tables = self._detectTables(page_image)
        equations = self._detectEquations(page_image)

        return LayoutAnalysis(
            page_number=page_image.page_num,
            layout_type=self._classifyLayout(columns),
            columns=columns,
            reading_order=reading_order,
            figures=figures,
            tables=tables,
            equations=equations
        )


class ColumnDetector:
    """分栏检测器"""

    def detectColumns(self, text_blocks: List[TextBlock]) -> List[Column]:
        """检测分栏"""
        # 1. 计算文本块X坐标分布
        x_coords = [block.x for block in text_blocks]

        # 2. 寻找自然分界点
        gaps = self._findColumnGaps(x_coords)

        # 3. 构建栏
        columns = []
        for i, (start, end) in enumerate(gaps):
            blocks_in_column = [b for b in text_blocks if start <= b.x < end]
            columns.append(Column(
                index=i,
                blocks=blocks_in_column,
                x_range=(start, end)
            ))

        return columns

    def _findColumnGaps(self, x_coords: List[float], min_gap: float = 50) -> List[Tuple[float, float]]:
        """找到栏之间的间隙"""
        if not x_coords:
            return []

        sorted_coords = sorted(x_coords)
        gaps = []

        # 使用DBSCAN或简单阈值检测间隙
        for i in range(len(sorted_coords) - 1):
            gap = sorted_coords[i + 1] - sorted_coords[i]
            if gap > min_gap:
                gaps.append((sorted_coords[i], sorted_coords[i + 1]))

        # 如果没有明显间隙，判断为单栏
        if len(gaps) == 0:
            return [(min(x_coords), max(x_coords) + 1)]

        return gaps


class TwoColumnMerger:
    """双栏内容合并器"""

    def mergeColumns(
        self,
        left_column: List[TextBlock],
        right_column: List[TextBlock]
    ) -> List[TextBlock]:
        """
        合并双栏内容为正确阅读顺序
        """
        merged = []

        # 按Y坐标（从上到下）交替合并
        left_sorted = sorted(left_column, key=lambda b: b.y, reverse=True)
        right_sorted = sorted(right_column, key=lambda b: b.y, reverse=True)

        i, j = 0, 0
        while i < len(left_sorted) or j < len(right_sorted):
            # 添加顶部元素
            if i < len(left_sorted):
                merged.append(left_sorted[i])
                i += 1

            if j < len(right_sorted):
                merged.append(right_sorted[j])
                j += 1

        return merged
```

#### 5.2 数学公式检测与转换器

```python
# src/agents_v2/pdf_formula/processor.py 新增

class FormulaProcessor:
    """
    数学公式处理器

    检测 → 识别 → LaTeX转换 → 渲染
    """

    def __init__(self):
        self._detector = FormulaDetector()
        self._recognizer = FormulaRecognizer()
        self._latex_converter = LaTeXConverter()

    async def processPage(self, page_image) -> FormulaProcessingResult:
        """处理页面中的公式"""
        # 1. 检测公式
        formulas = await self._detector.detect(page_image)

        results = []
        for formula in formulas:
            # 2. 识别公式类型（行内/显示）
            formula_type = self._classifyFormulaType(formula)

            # 3. 转换为LaTeX
            if formula.is_image:
                latex = await self._recognizer.recognize(formula.image)
            else:
                latex = await self._latex_converter.convert(formula.text)

            # 4. 验证LaTeX
            is_valid, error = self._validateLatex(latex)

            results.append(FormulaResult(
                original=formula,
                latex=latex,
                type=formula_type,
                is_valid=is_valid,
                error=error
            ))

        return FormulaProcessingResult(formulas=results)


class LaTeXConverter:
    """LaTeX转换器"""

    # 常见符号映射
    SYMBOL_MAP = {
        "α": r"\alpha",
        "β": r"\beta",
        "γ": r"\gamma",
        "δ": r"\delta",
        "∞": r"\infty",
        "≤": r"\leq",
        "≥": r"\geq",
        "≠": r"\neq",
        "∈": r"\in",
        "⊂": r"\subset",
        "∪": r"\cup",
        "∩": r"\cap",
        "∑": r"\sum",
        "∏": r"\prod",
        "∫": r"\int",
        "∂": r"\partial",
        # 更多符号...
    }

    def convert(self, formula_text: str) -> str:
        """将文本公式转为LaTeX"""
        latex = formula_text

        # 1. 替换Unicode符号
        for unicode_sym, latex_sym in self.SYMBOL_MAP.items():
            latex = latex.replace(unicode_sym, latex_sym)

        # 2. 处理上下标
        latex = self._processSupSub(latex)

        # 3. 处理分数
        latex = self._processFractions(latex)

        # 4. 处理根号
        latex = self._processRadicals(latex)

        # 5. 处理矩阵
        latex = self._processMatrices(latex)

        return latex

    def _processSupSub(self, text: str) -> str:
        """处理上下标"""
        # 简单实现：x^2, x_1 等
        # 实际需要更复杂的解析
        text = re.sub(r'(\w+)\^(\d+)', r'\1^{\2}', text)
        text = re.sub(r'(\w+)\_(\d+)', r'\1_{\2}', text)
        return text

    def _validateLatex(self, latex: str) -> Tuple[bool, Optional[str]]:
        """验证LaTeX语法"""
        try:
            # 尝试编译
            import subprocess
            result = subprocess.run(
                ['pdflatex', '-interaction=nonstopmode'],
                input=latex,
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0, None
        except Exception as e:
            return False, str(e)
```

#### 5.3 验收标准

| 验收项 | 标准 | 检查点 |
|--------|------|--------|
| 双栏检测 | 准确率>95% | 测试各类型论文 |
| 阅读顺序 | 正确率>90% | 人工对比 |
| 公式识别 | LaTeX准确率>85% | 测试100+公式 |
| 符号转换 | 常见符号全覆盖 | 200+符号测试 |

---

### 第6次迭代：PDF解析链路强化（二）

**目标**: 完善参考文献解析和表格处理

#### 6.1 参考文献深度解析器

```python
# src/agents_v2/pdf_references/deep_parser.py 新增

class DeepReferenceParser:
    """
    参考文献深度解析器

    使用多策略解析参考文献，提升解析准确率
    """

    def __init__(self):
        self._strategies = [
            StructuredReferenceParser(),    # 结构化格式解析
            RegexReferenceParser(),          # 正则表达式解析
            LLMBasedParser(),               # LLM辅助解析
            CFFParser()                    # 引文字段格式解析
        ]
        self._cross_ref_client = CrossRefClient()

    async def parse(
        self,
        reference_text: str
    ) -> ParsedReference:
        """
        多策略解析参考文献

        尝试多种策略，取最优结果
        """
        results = []

        for strategy in self._strategies:
            try:
                result = await strategy.parse(reference_text)
                confidence = self._evaluateParseConfidence(result, reference_text)
                results.append((result, confidence))
            except Exception as e:
                continue

        if not results:
            return ParsedReference(raw_text=reference_text, is_parsed=False)

        # 选择置信度最高的结果
        best_result, best_confidence = max(results, key=lambda x: x[1])

        # 如果置信度低，尝试使用CrossRef API补全
        if best_confidence < 0.7:
            enriched = await self._enrichFromCrossRef(best_result)
            if enriched:
                best_result = enriched
                best_confidence = (best_confidence + 0.9) / 2

        return ParsedReference(
            raw_text=reference_text,
            is_parsed=True,
            confidence=best_confidence,
            **best_result.toDict()
        )

    async def _enrichFromCrossRef(
        self,
        reference: ParsedReference
    ) -> Optional[ParsedReference]:
        """使用CrossRef API补全参考文献信息"""
        if not reference.title:
            return None

        try:
            # 搜索CrossRef
            results = await self._cross_ref_client.search(
                query=reference.title,
                rows=1
            )

            if results:
                cross_ref_data = results[0]
                # 合并数据
                enriched = reference.copy()
                enriched.update({
                    "doi": cross_ref_data.get("DOI"),
                    "authors": cross_ref_data.get("author", []),
                    "year": cross_ref_data.get("published-print", {}).get("date-parts", [[None]])[0][0],
                    "journal": cross_ref_data.get("container-title", [""])[0],
                    "volume": cross_ref_data.get("volume"),
                    "issue": cross_ref_data.get("issue"),
                    "pages": cross_ref_data.get("page")
                })
                return enriched

        except Exception as e:
            logger.warning(f"CrossRef enrichment failed: {e}")

        return None


class LLMBasedParser:
    """基于LLM的参考文献解析器"""

    async def parse(self, reference_text: str) -> Dict[str, Any]:
        """使用LLM解析参考文献"""
        prompt = f"""
解析以下参考文献，提取各字段信息：

参考文献：{reference_text}

支持的格式：
- 作者, A. & 作者, B. (2024). 标题. 期刊, 20(1), 1-20.
- [1] 作者. 标题. 期刊, 2024, 20(1), 1-20.
- 作者等. 标题. 期刊, 2024.

返回JSON格式：
{{
    "authors": ["作者A", "作者B"],
    "title": "论文标题",
    "year": "2024",
    "journal": "期刊名称",
    "volume": "20",
    "issue": "1",
    "pages": "1-20",
    "doi": "10.xxxx/xxxxx"
}}
"""
        # 调用LLM
        # 解析JSON结果
```

#### 6.2 表格检测与结构化解析器

```python
# src/agents_v2/pdf_table/parser.py 新增

class TableParser:
    """
    表格解析器

    检测 → 解析 → 结构化 → 标准化
    """

    def __init__(self):
        self._detector = TableDetector()
        self._structure_parser = TableStructureParser()
        self._normalizer = TableNormalizer()

    async def parseTable(
        self,
        table_image,
        page_context: str = ""
    ) -> ParsedTable:
        """完整解析表格"""
        # 1. 检测表格
        bbox = await self._detector.detect(table_image)
        if not bbox:
            return ParsedTable(is_detected=False)

        # 2. 提取表格内容
        raw_table = await self._extractTableContent(table_image, bbox)

        # 3. 解析表格结构
        structure = await self._structure_parser.parse(raw_table)

        # 4. 识别表头
        headers = await self._identifyHeaders(structure)

        # 5. 检测合并单元格
        merged_cells = await self._detectMergedCells(structure)

        # 6. 标准化
        normalized = await self._normalizer.normalize(
            structure=structure,
            headers=headers,
            merged_cells=merged_cells
        )

        # 7. 描述生成
        description = await self._generateDescription(normalized, page_context)

        return ParsedTable(
            is_detected=True,
            headers=headers,
            rows=normalized.rows,
            merged_cells=merged_cells,
            description=description,
            confidence=self._calculateConfidence(normalized)
        )


class TableStructureParser:
    """表格结构解析器"""

    def parse(self, raw_table: List[List[str]]) -> TableStructure:
        """解析表格结构"""
        # 1. 确定行列数
        num_rows = len(raw_table)
        num_cols = max(len(row) for row in raw_table) if raw_table else 0

        # 2. 识别表头行（通常第一行是表头）
        header_row = raw_table[0] if raw_table else []

        # 3. 确定数据类型
        column_types = self._inferColumnTypes(raw_table[1:] if len(raw_table) > 1 else [])

        # 4. 识别汇总行
        summary_rows = self._detectSummaryRows(raw_table)

        # 5. 识别注释行
        footnote_rows = self._detectFootnoteRows(raw_table)

        return TableStructure(
            raw_data=raw_table,
            num_rows=num_rows,
            num_cols=num_cols,
            header_row=header_row,
            column_types=column_types,
            summary_rows=summary_rows,
            footnote_rows=footnote_rows
        )
```

#### 6.3 验收标准

| 验收项 | 标准 | 检查点 |
|--------|------|--------|
| 参考文献解析 | 准确率>90% | 测试500+参考文献 |
| CrossRef补全 | 补全率>60% | 测试无DOI文献 |
| 表格检测 | 召回率>95% | 测试各类表格 |
| 表格结构化 | 结构准确率>85% | 测试复杂表格 |

---

### 第7次迭代：PDF解析链路强化（三）

**目标**: 实现内容理解（核心贡献提取）和引用关系映射

#### 7.1 论文贡献提取器

```python
# src/agents_v2/pdf_analysis/contribution_extractor.py 新增

class ContributionExtractor:
    """
    论文贡献提取器

    自动识别论文的核心贡献
    """

    def __init__(self, llm: Any = None):
        self.llm = llm

    async def extract(
        self,
        paper_content: Dict[str, Any]
    ) -> PaperContributions:
        """
        提取论文贡献

        分析点：
        1. 摘要中的贡献声明
        2. 引言中的创新点
        3. 结论中的总结
        4. 方法章节的独特设计
        """
        # 1. 从摘要提取
        abstract_contributions = await self._extractFromAbstract(
            paper_content.get("abstract", "")
        )

        # 2. 从引言提取
        intro_contributions = await self._extractFromIntroduction(
            paper_content.get("introduction", "")
        )

        # 3. 从结论提取
        conclusion_contributions = await self._extractFromConclusion(
            paper_content.get("conclusion", "")
        )

        # 4. 从方法提取
        method_contributions = await self._extractFromMethod(
            paper_content.get("method", "")
        )

        # 5. 融合去重
        final_contributions = self._mergeContributions([
            abstract_contributions,
            intro_contributions,
            conclusion_contributions,
            method_contributions
        ])

        # 6. 分类
        categorized = self._categorizeContributions(final_contributions)

        return PaperContributions(
            contributions=categorized,
            novelty_statement=await self._generateNoveltyStatement(final_contributions),
            impact_summary=await self._generateImpactSummary(final_contributions)
        )

    async def _extractFromAbstract(self, abstract: str) -> List[Contribution]:
        """从摘要提取贡献"""
        prompt = f"""
从以下论文摘要中提取核心贡献：

摘要：
{abstract}

贡献通常是：
1. 提出了新方法/模型/算法
2. 解决了什么问题
3. 取得了什么效果

返回JSON格式：
{{
    "contributions": [
        {{"type": "方法/应用/理论", "description": "贡献描述", "evidence": "证据"}}
    ]
}}
"""
        # 调用LLM
        # 解析返回

    async def _generateNoveltyStatement(self, contributions: List[Contribution]) -> str:
        """生成创新性声明"""
        prompt = f"""
基于以下论文贡献，生成一句简洁的创新性声明：

贡献：
{chr(10).join([f"- {c.description}" for c in contributions])}

创新性声明应该：
1. 突出与已有工作的最大区别
2. 使用"首次"、" novel"、"首次提出"等表达
3. 控制在50字以内
"""
        # 调用LLM生成
```

#### 7.2 引用关系映射器

```python
# src/agents_v2/pdf_citation/relation_mapper.py 新增

class CitationRelationMapper:
    """
    引用关系映射器

    建立图表引用、正文引用、参考文献的关联
    """

    def __init__(self):
        self._figure_refs = {}   # figure_id -> 正文引用位置
        self._table_refs = {}    # table_id -> 正文引用位置
        self._citation_contexts = {}  # citation_marker -> 引用上下文

    def buildRelations(self, paper: ParsedPaper) -> CitationRelations:
        """构建引用关系"""
        # 1. 收集所有引用标记
        citation_markers = self._collectCitationMarkers(paper.full_text)

        # 2. 建立引用上下文
        for marker in citation_markers:
            context = self._extractCitationContext(paper.full_text, marker)
            self._citation_contexts[marker] = context

        # 3. 建立图表关系
        for figure in paper.figures:
            refs = self._findFigureReferences(paper.full_text, figure)
            self._figure_refs[figure.id] = refs

        # 4. 建立参考文献关系
        ref_relations = self._buildReferenceRelations(paper)

        return CitationRelations(
            figure_citations=self._figure_refs,
            table_citations=self._table_refs,
            reference_contexts=self._citation_contexts,
            reference_relations=ref_relations
        )

    def _extractCitationContext(
        self,
        full_text: str,
        citation_marker: str
    ) -> CitationContext:
        """提取引用上下文"""
        # 找到引用在正文中的位置
        position = full_text.find(citation_marker)

        # 提取前后各100字符作为上下文
        start = max(0, position - 100)
        end = min(len(full_text), position + 100)

        preceding = full_text[start:position]
        following = full_text[position + len(citation_marker):end]

        # 判断引用意图
        intent = self._classifyCitationIntent(preceding, following)

        return CitationContext(
            marker=citation_marker,
            preceding_text=preceding,
            following_text=following,
            intent=intent,  # supports/challenges/compares/extends
            position=position
        )

    def _classifyCitationIntent(
        self,
        preceding: str,
        following: str
    ) -> str:
        """分类引用意图"""
        combined = (preceding + following).lower()

        if any(word in combined for word in ["based on", "using", "adopt"]):
            return "supports"
        elif any(word in combined for word in ["however", "contrary", "different"]):
            return "challenges"
        elif any(word in combined for word in ["compare", "similar", "unlike"]):
            return "compares"
        elif any(word in combined for word in ["extend", "build upon", "improve"]):
            return "extends"
        else:
            return "mentions"
```

#### 7.3 验收标准

| 验收项 | 标准 | 检查点 |
|--------|------|--------|
| 贡献提取 | 准确率>80% | 与人工标注对比 |
| 创新性声明 | 人工评分>4/5 | 10人评估 |
| 引用关系 | 映射准确率>90% | 测试100+引用 |
| 引用意图 | 分类准确率>85% | 与人工对比 |

---

### 第8次迭代：生成链路强化（一）

**目标**: 实现分章节撰写策略和质量控制

#### 8.1 章节生成策略控制器

```python
# src/agents_v2/writing/chapter_strategies.py 新增

class ChapterWritingStrategyController:
    """
    章节写作策略控制器

    针对不同章节采用不同生成策略
    """

    STRATEGIES = {
        "abstract": AbstractWritingStrategy(),
        "introduction": IntroductionWritingStrategy(),
        "related_work": RelatedWorkWritingStrategy(),
        "method": MethodWritingStrategy(),
        "experiment": ExperimentWritingStrategy(),
        "discussion": DiscussionWritingStrategy(),
        "conclusion": ConclusionWritingStrategy()
    }

    async def writeChapter(
        self,
        chapter_type: str,
        context: ChapterContext
    ) -> ChapterContent:
        """使用对应策略撰写章节"""
        strategy = self.STRATEGIES.get(chapter_type)
        if not strategy:
            strategy = self.STRATEGIES["conclusion"]  # 默认策略

        return await strategy.write(context)


class AbstractWritingStrategy:
    """摘要撰写策略"""

    async def write(self, context: ChapterContext) -> ChapterContent:
        """撰写结构化摘要"""
        prompt = f"""
撰写论文摘要（四要素结构）：

主题：{context.topic}
研究目标：{context.research_goal}

请按以下结构撰写摘要：
1. 研究背景与目的（1-2句）
2. 研究方法（1-2句）
3. 主要发现/结果（2-3句）
4. 结论与意义（1-2句）

要求：
- 使用第三人称
- 不使用"本文"、"本研究"等第一人称
- 不使用缩写
- 控制在200-300字
- 不引用参考文献

摘要：
"""
        # 调用LLM生成


class IntroductionWritingStrategy:
    """引言撰写策略"""

    async def write(self, context: ChapterContext) -> ChapterContent:
        """撰写引言（漏斗结构）"""
        prompt = f"""
撰写论文引言（漏斗结构）：

主题：{context.topic}
研究背景：{context.background}

引言应包含：
1. 宽泛的研究背景（1段）
2. 领域的具体现状（1段）
3. 现有方法的不足/gap（1段）
4. 本文贡献声明（1段）

Gap示例：
- 方法A在X情况下有效，但无法处理Y
- 现有研究忽视了Z问题
- X和Y的结合尚未被探索

本文贡献应明确说明：
1. 提出了什么方法/理论
2. 解决了什么问题
3. 取得了什么效果

要求：
- 逻辑递进，层层缩小
- gap要具体，不能泛泛而谈
- 贡献要清晰，可验证
"""


class DiscussionWritingStrategy:
    """讨论章节撰写策略"""

    async def write(self, context: ChapterContext) -> ChapterContent:
        """撰写讨论章节"""
        prompt = f"""
撰写论文讨论章节：

研究结果：{context.results_summary}
研究方法：{context.method_summary}

讨论章节应包含：
1. 结果解读：解释发现的含义
2. 与已有工作对比：相同点、不同点
3. 理论意义：结果对理论有什么贡献
4. 实践意义：结果对实践有什么指导
5. 局限性：研究的不足
6. 未来方向：可以如何改进

要求：
- 不要简单重复结果，要深入分析
- 对比要客观，既要承认优势也要指出不足
- 局限性要诚实但不能否定研究价值
"""
```

#### 8.2 生成质量控制器

```python
# src/agents_v2/writing/quality_controller.py 新增

class WritingQualityController:
    """
    写作质量控制器

    在生成过程中进行质量检查和自我修正
    """

    def __init__(self):
        self._checkers = [
            LogicalCoherenceChecker(),
            CitationChecker(),
            TerminologyChecker(),
            StyleChecker()
        ]

    async def controlQuality(
        self,
        draft: str,
        context: GenerationContext
    ) -> QualityReport:
        """控制生成质量"""
        issues = []
        suggestions = []

        # 1. 逻辑连贯性检查
        coherence_result = await self._checkers[0].check(draft, context)
        if not coherence_result.passed:
            issues.extend(coherence_result.issues)
            suggestions.extend(coherence_result.suggestions)

        # 2. 引用检查
        citation_result = await self._checkers[1].check(draft, context)
        if not citation_result.passed:
            issues.extend(citation_result.issues)

        # 3. 术语一致性检查
        terminology_result = await self._checkers[2].check(draft)
        if not terminology_result.passed:
            issues.extend(terminology_result.issues)

        # 4. 风格检查
        style_result = await self._checkers[3].check(draft, context)
        if not style_result.passed:
            suggestions.extend(style_result.suggestions)

        # 计算质量分数
        quality_score = self._calculateQualityScore(
            draft_length=len(draft),
            issues_count=len(issues),
            suggestions_count=len(suggestions)
        )

        return QualityReport(
            draft=draft,
            quality_score=quality_score,
            issues=issues,
            suggestions=suggestions,
            needs_revision=len(issues) > 0
        )


class LogicalCoherenceChecker:
    """逻辑连贯性检查器"""

    async def check(
        self,
        draft: str,
        context: GenerationContext
    ) -> CheckResult:
        """检查逻辑连贯性"""
        issues = []
        suggestions = []

        # 1. 段落衔接检查
        transitions = self._analyzeTransitions(draft)
        if transitions.missing_count > 0:
            issues.append(CoherenceIssue(
                type="transition_missing",
                locations=transitions.missing_locations,
                description=f"缺少{transitions.missing_count}处段落衔接"
            ))
            suggestions.append("在段落之间添加过渡句")

        # 2. 论点支持检查
        unsupported_claims = self._findUnsupportedClaims(draft)
        if unsupported_claims:
            issues.append(CoherenceIssue(
                type="unsupported_claims",
                locations=[c.location for c in unsupported_claims],
                description=f"发现{len(unsupported_claims)}个未经充分论证的论点"
            ))

        # 3. 逻辑矛盾检查
        contradictions = self._findContradictions(draft)
        if contradictions:
            issues.append(CoherenceIssue(
                type="contradictions",
                locations=[c.location for c in contradictions],
                description="发现逻辑矛盾的陈述"
            ))

        return CheckResult(
            passed=len(issues) == 0,
            issues=issues,
            suggestions=suggestions
        )
```

#### 8.3 验收标准

| 验收项 | 标准 | 检查点 |
|--------|------|--------|
| 章节策略 | 7种策略正确应用 | 测试各章节生成 |
| 质量控制 | 问题检测率>90% | 注入问题测试 |
| 自我修正 | 修正有效率>80% | 人工评估修正结果 |
| 连贯性 | 逻辑评分>4/5 | 10人评估 |

---

### 第9次迭代：生成链路强化（二）

**目标**: 实现Self-RAG在生成中的应用和原创性保证

#### 9.1 生成式Self-RAG控制器

```python
# src/agents_v2/writing/self_rag_generator.py 新增

class SelfRAGGenerator:
    """
    自反思RAG生成器

    在生成过程中进行反思和质量控制
    """

    def __init__(self, llm: Any = None):
        self.llm = llm

    async def generate(
        self,
        prompt: str,
        context: Dict[str, Any],
        max_retries: int = 2
    ) -> GenerationResult:
        """
        自反思生成

        流程：
        1. 生成初稿
        2. 反思质量
        3. 如有问题，修正后重新生成
        4. 重复直到质量达标
        """
        for attempt in range(max_retries + 1):
            # 1. 生成
            draft = await self._generateDraft(prompt, context)

            # 2. 反思
            reflection = await self._reflectOnDraft(draft, prompt, context)

            # 3. 检查是否需要修正
            if reflection.quality_score >= 0.8 or attempt >= max_retries:
                return GenerationResult(
                    draft=draft,
                    quality_score=reflection.quality_score,
                    iterations=attempt + 1,
                    issues=reflection.issues
                )

            # 4. 修正问题
            corrected = await self._correctIssues(draft, reflection.issues, context)
            draft = corrected

        return GenerationResult(
            draft=draft,
            quality_score=reflection.quality_score,
            iterations=max_retries + 1,
            issues=reflection.issues,
            warning="Max retries reached"
        )

    async def _reflectOnDraft(
        self,
        draft: str,
        prompt: str,
        context: Dict[str, Any]
    ) -> ReflectionResult:
        """反思初稿质量"""
        reflection_prompt = f"""
作为学术写作评审专家，反思以下论文内容：

原始要求：{prompt}

生成内容：
{draft[:1000]}{'...' if len(draft) > 1000 else ''}

请评估以下方面并给出分数（0-1）：

1. **内容相关性** - 内容是否切题，回应了原始要求？
2. **事实准确性** - 陈述的事实是否有据可查？
3. **逻辑连贯性** - 论证是否严密，逻辑是否通顺？
4. **引用适当性** - 是否恰当地引用了文献？
5. **语言规范性** - 语言是否学术、严谨？

发现的问题：
- 列出需要修正的具体问题

返回JSON格式：
{{
    "quality_scores": {{
        "relevance": 0.0-1.0,
        "accuracy": 0.0-1.0,
        "coherence": 0.0-1.0,
        "citation": 0.0-1.0,
        "language": 0.0-1.0
    }},
    "overall_score": 0.0-1.0,
    "issues": [
        {{"type": "问题类型", "description": "具体描述", "severity": "high/medium/low"}}
    ]
}}
"""
        # 调用LLM获取反思结果
```

#### 9.2 原创性检测器

```python
# src/agents_v2/writing/originality_checker.py 新增

class OriginalityChecker:
    """
    原创性检测器

    检测生成内容的原创性，防止抄袭
    """

    def __init__(self):
        self._plagiarism_detector = PlagiarismDetector()
        self._self_plagiarism_checker = SelfPlagiarismChecker()

    async def checkOriginality(
        self,
        draft: str,
        referenced_sources: List[str] = None
    ) -> OriginalityReport:
        """检查原创性"""
        issues = []

        # 1. 与参考文献的相似度检测
        if referenced_sources:
            similarity_result = await self._checkSimilarityToSources(
                draft, referenced_sources
            )
            if similarity_result.similarity > 0.3:
                issues.append(OriginalityIssue(
                    type="high_similarity",
                    severity="high",
                    description=f"与参考文献相似度过高: {similarity_result.similarity:.1%}",
                    suggestions=["改写相关段落", "增加更多原创分析"]
                ))

        # 2. 自我抄袭检测（如果有多版本）
        if referenced_sources:
            self_plagiarism = await self._self_plagiarism_checker.check(
                draft, referenced_sources
            )
            if self_plagiarism.detected:
                issues.append(OriginalityIssue(
                    type="self_plagiarism",
                    severity="medium",
                    description="检测到与作者之前工作的重复",
                    suggestions=["引用自己的之前工作", "换一种表述方式"]
                ))

        # 3. 常用模板检测（避免套话）
        template_issues = self._detectTemplatePhrases(draft)
        if template_issues:
            issues.extend(template_issues)

        # 4. 计算原创性分数
        originality_score = 1.0 - sum(
            issue.severity_weight * 0.2 for issue in issues
        )

        return OriginalityReport(
            originality_score=max(0.0, originality_score),
            issues=issues,
            passed=originality_score >= 0.7 and not any(
                i.severity == "high" for i in issues
            )
        )

    def _detectTemplatePhrases(self, text: str) -> List[OriginalityIssue]:
        """检测模板套话"""
        template_phrases = [
            "近年来，随着...",
            "大量的研究表明...",
            "不言而喻...",
            "众所周知...",
            "本文旨在...",
            "具有重要的理论意义和现实意义"
        ]

        issues = []
        for phrase in template_phrases:
            if phrase in text:
                issues.append(OriginalityIssue(
                    type="template_phrase",
                    severity="low",
                    description=f"使用模板套话: {phrase}",
                    suggestions=["换一种更具体的表达"]
                ))

        return issues
```

#### 9.3 验收标准

| 验收项 | 标准 | 检查点 |
|--------|------|--------|
| Self-RAG生成 | 质量提升15% | 对比无反思生成 |
| 原创性检测 | 检出率>90% | 测试已知重复内容 |
| 自我修正 | 有效修正率>70% | 人工评估修正 |
| 相似度检测 | 准确率>85% | 对比商业查重工具 |

---

### 第10次迭代：输出链路强化（一）

**目标**: 实现格式输出规范和预览机制

#### 10.1 多格式导出器

```python
# src/agents_v2/output/multi_format_exporter.py 新增

class MultiFormatExporter:
    """
    多格式导出器

    支持Markdown/LaTeX/Word/PDF/HTML格式
    """

    def __init__(self):
        self._converters = {
            "markdown": MarkdownConverter(),
            "latex": LaTeXConverter(),
            "word": WordConverter(),
            "pdf": PDFConverter(),
            "html": HTMLConverter()
        }

    async def export(
        self,
        paper: ParsedPaper,
        format: str,
        options: ExportOptions = None
    ) -> ExportedFile:
        """导出为指定格式"""
        converter = self._converters.get(format)
        if not converter:
            raise ValueError(f"Unsupported format: {format}")

        options = options or ExportOptions()

        # 1. 格式特定处理
        content = await converter.convert(paper, options)

        # 2. 添加元数据
        metadata = self._generateMetadata(paper, format)

        # 3. 完整性检查
        validation = await self._validateOutput(content, format, options)

        if not validation.passed:
            raise ExportError(f"Validation failed: {validation.errors}")

        return ExportedFile(
            content=content,
            format=format,
            filename=self._generateFilename(paper, format),
            metadata=metadata
        )


class LaTeXConverter:
    """LaTeX转换器"""

    async def convert(
        self,
        paper: ParsedPaper,
        options: ExportOptions
    ) -> str:
        """转换为LaTeX"""
        template = self._loadTemplate(paper.template or "default")

        # 填充各部分
        content = template.format(
            title=paper.title,
            authors=self._formatAuthors(paper.authors),
            abstract=self._convertAbstract(paper.abstract),
            keywords=self._formatKeywords(paper.keywords),
            sections=self._convertSections(paper.sections),
            references=self._convertReferences(paper.references),
            tables=self._convertTables(paper.tables),
            figures=self._convertFigures(paper.figures)
        )

        return content

    def _loadTemplate(self, template_name: str) -> str:
        """加载LaTeX模板"""
        templates = {
            "default": DEFAULT_LATEX_TEMPLATE,
            "ieee": IEEE_LATEX_TEMPLATE,
            "acm": ACM_LATEX_TEMPLATE,
            "springer": SPRINGER_LATEX_TEMPLATE
        }
        return templates.get(template_name, templates["default"])
```

#### 10.2 渲染预览服务

```python
# src/agents_v2/output/preview_server.py 新增

class RenderingPreviewServer:
    """
    渲染预览服务

    提供LaTeX/PDF实时预览
    """

    def __init__(self):
        self._cache = {}
        self._render_queue = asyncio.Queue()

    async def renderPreview(
        self,
        content: str,
        format: str,
        page: int = 1
    ) -> PreviewResult:
        """
        渲染预览

        支持：
        1. LaTeX源码高亮预览
        2. 编译后的PDF页面预览
        3. HTML渲染预览
        """
        cache_key = f"{hash(content)}:{format}:{page}"

        if cache_key in self._cache:
            return self._cache[cache_key]

        if format == "latex":
            result = await self._renderLatexPreview(content)
        elif format == "pdf":
            result = await self._renderPDFPreview(content, page)
        elif format == "html":
            result = await self._renderHTMLPreview(content)

        self._cache[cache_key] = result
        return result

    async def _renderPDFPreview(
        self,
        latex_content: str,
        page: int
    ) -> PreviewResult:
        """渲染PDF指定页面为图片"""
        # 1. 编译LaTeX
        pdf_path = await self._compileLatex(latex_content)

        # 2. 提取指定页面为图片
        preview_image = await self._extractPageAsImage(pdf_path, page)

        # 3. 生成缩略图
        thumbnail = await self._generateThumbnail(preview_image, max_size=(200, 280))

        return PreviewResult(
            image=preview_image,
            thumbnail=thumbnail,
            page=page,
            total_pages=await self._countPages(pdf_path)
        )
```

#### 10.3 验收标准

| 验收项 | 标准 | 检查点 |
|--------|------|--------|
| 多格式导出 | 支持5+格式 | 测试各格式导出 |
| LaTeX模板 | 支持3+模板 | 测试ieee/acm等 |
| 预览服务 | <2s渲染 | 测量延迟 |
| 格式完整性 | 转换不失真 | 人工检查 |

---

### 第11次迭代：输出链路强化（二）

**目标**: 实现版本管理和增量更新

#### 11.1 论文版本管理器

```python
# src/agents_v2/output/version_manager.py 新增

class PaperVersionManager:
    """
    论文版本管理器

    管理论文的版本历史，支持回滚和对比
    """

    def __init__(self, storage_path: str = ".paper_versions"):
        self.storage_path = storage_path
        self._versions: Dict[str, List[Version]] = {}

    async def saveVersion(
        self,
        paper_id: str,
        content: str,
        metadata: VersionMetadata
    ) -> str:
        """保存版本"""
        version_id = f"{paper_id}_v{len(self._versions.get(paper_id, [])) + 1}"

        version = Version(
            version_id=version_id,
            paper_id=paper_id,
            content=content,
            metadata=metadata,
            created_at=datetime.now()
        )

        if paper_id not in self._versions:
            self._versions[paper_id] = []

        self._versions[paper_id].append(version)

        # 持久化到磁盘
        await self._persistVersion(version)

        return version_id

    async def getVersion(
        self,
        paper_id: str,
        version_id: str
    ) -> Optional[Version]:
        """获取指定版本"""
        versions = self._versions.get(paper_id, [])
        for v in versions:
            if v.version_id == version_id:
                return v
        return None

    async def compareVersions(
        self,
        paper_id: str,
        version_a: str,
        version_b: str
    ) -> VersionDiff:
        """对比两个版本"""
        v_a = await self.getVersion(paper_id, version_a)
        v_b = await self.getVersion(paper_id, version_b)

        if not v_a or not v_b:
            raise ValueError("Version not found")

        # 使用diff算法计算差异
        diff = self._computeDiff(v_a.content, v_b.content)

        return VersionDiff(
            version_a=version_a,
            version_b=version_b,
            diff=diff,
            added_count=diff.added_count,
            removed_count=diff.removed_count,
            modified_count=diff.modified_count
        )

    async def rollbackToVersion(
        self,
        paper_id: str,
        version_id: str
    ) -> str:
        """回滚到指定版本"""
        target_version = await self.getVersion(paper_id, version_id)
        if not target_version:
            raise ValueError(f"Version {version_id} not found")

        # 创建新版本（复制目标版本内容）
        new_version_id = await self.saveVersion(
            paper_id=paper_id,
            content=target_version.content,
            metadata=VersionMetadata(
                change_type="rollback",
                from_version=version_id,
                reason="用户回滚"
            )
        )

        return new_version_id
```

#### 11.2 增量更新处理器

```python
# src/agents_v2/output/incremental_updater.py 新增

class IncrementalUpdateProcessor:
    """
    增量更新处理器

    处理用户的局部修改请求，只更新变更部分
    """

    def __init__(self):
        self._change_detector = ChangeDetector()

    async def processUpdate(
        self,
        current_paper: ParsedPaper,
        user_changes: UserChanges
    ) -> UpdatedPaper:
        """
        处理增量更新

        策略：
        1. 解析用户修改
        2. 确定影响范围
        3. 只更新受影响部分
        4. 保持其他部分一致性
        """
        # 1. 解析修改类型
        change_type = self._classifyChanges(user_changes)

        if change_type == "sentence_edit":
            # 句子级别的编辑
            updated = await self._processSentenceEdit(
                current_paper, user_changes
            )
        elif change_type == "section_rewrite":
            # 章节重写
            updated = await self._processSectionRewrite(
                current_paper, user_changes
            )
        elif change_type == "content_addition":
            # 内容新增
            updated = await self._processContentAddition(
                current_paper, user_changes
            )
        elif change_type == "content_deletion":
            # 内容删除
            updated = await self._processContentDeletion(
                current_paper, user_changes
            )

        # 2. 更新引用编号（如果增删了参考文献）
        updated = await self._updateCitationNumbers(updated)

        # 3. 更新目录/索引
        updated = await self._updateTOC(updated)

        # 4. 验证完整性
        validation = await self._validateCompleteness(updated)
        if not validation.passed:
            updated = await self._fixCompleteness(updated, validation.issues)

        return updated

    async def _processSentenceEdit(
        self,
        paper: ParsedPaper,
        changes: UserChanges
    ) -> UpdatedPaper:
        """处理句子编辑"""
        new_content = paper.content

        for change in changes.edits:
            # 找到并替换指定句子
            new_content = new_content.replace(
                change.original_sentence,
                change.new_sentence
            )

        return paper.withContent(new_content)
```

#### 11.3 验收标准

| 验收项 | 标准 | 检查点 |
|--------|------|--------|
| 版本保存 | 保存完整内容 | 测试保存/加载 |
| 版本对比 | 差异计算准确 | 对比已知差异 |
| 回滚功能 | 正确恢复 | 测试回滚 |
| 增量更新 | 只更新必要部分 | 测量性能 |
| 引用更新 | 编号正确更新 | 测试引用增删 |

---

### 第12次迭代：系统集成与监控（一）

**目标**: 实现完整的数据流追踪和监控系统

#### 12.1 数据流追踪器

```python
# src/agents_v2/monitoring/data_flow_tracker.py 新增

class DataFlowTracker:
    """
    数据流追踪器

    追踪数据在Agent间的流动和处理
    """

    def __init__(self):
        self._traces: Dict[str, DataFlowTrace] = {}
        self._current_trace_id = None

    async def startTrace(self, operation_id: str, operation_type: str) -> str:
        """开始追踪"""
        trace_id = f"{operation_type}_{operation_id}_{int(time.time()*1000)}"

        self._traces[trace_id] = DataFlowTrace(
            trace_id=trace_id,
            operation_type=operation_type,
            start_time=time.time(),
            nodes=[],
            edges=[]
        )

        self._current_trace_id = trace_id
        return trace_id

    async def recordNode(
        self,
        node_id: str,
        node_type: str,
        input_data: Any,
        output_data: Any,
        metadata: Dict = None
    ) -> None:
        """记录处理节点"""
        if not self._current_trace_id:
            return

        node = DataFlowNode(
            node_id=node_id,
            node_type=node_type,
            input_hash=self._hashData(input_data),
            output_hash=self._hashData(output_data),
            input_size=len(str(input_data)),
            output_size=len(str(output_data)),
            timestamp=time.time(),
            metadata=metadata or {}
        )

        self._traces[self._current_trace_id].nodes.append(node)

    async def recordEdge(
        self,
        from_node: str,
        to_node: str,
        data_flow: str
    ) -> None:
        """记录节点间的数据流动"""
        if not self._current_trace_id:
            return

        edge = DataFlowEdge(
            from_node=from_node,
            to_node=to_node,
            data_flow_type=data_flow,
            timestamp=time.time()
        )

        self._traces[self._current_trace_id].edges.append(edge)

    def getTraceSummary(self, trace_id: str) -> TraceSummary:
        """获取追踪摘要"""
        trace = self._traces.get(trace_id)
        if not trace:
            return None

        # 计算各节点的延迟
        node_delays = {}
        for i, node in enumerate(trace.nodes):
            if i > 0:
                delay = node.timestamp - trace.nodes[i-1].timestamp
                node_delays[node.node_id] = delay

        return TraceSummary(
            trace_id=trace_id,
            total_duration=time.time() - trace.start_time,
            node_count=len(trace.nodes),
            edge_count=len(trace.edges),
            total_input=sum(n.input_size for n in trace.nodes),
            total_output=sum(n.output_size for n in trace.nodes),
            bottleneck_node=max(node_delays.items(), key=lambda x: x[1])[0] if node_delays else None
        )
```

#### 12.2 实时监控仪表板

```python
# src/agents_v2/monitoring/dashboard.py 新增

class MonitoringDashboard:
    """
    实时监控仪表板

    展示系统运行状态和性能指标
    """

    def __init__(self):
        self._metrics_collector = MetricsCollector()
        self._alert_manager = AlertManager()

    async def getDashboardData(self) -> DashboardData:
        """获取仪表板数据"""
        # 1. 收集各指标
        system_metrics = await self._metrics_collector.collectSystemMetrics()
        agent_metrics = await self._metrics_collector.collectAgentMetrics()
        retrieval_metrics = await self._metrics_collector.collectRetrievalMetrics()
        generation_metrics = await self._metrics_collector.collectGenerationMetrics()

        # 2. 检查告警
        alerts = await self._alert_manager.checkAlerts(
            system_metrics, agent_metrics, retrieval_metrics, generation_metrics
        )

        # 3. 生成建议
        suggestions = self._generateSuggestions(alerts, metrics)

        return DashboardData(
            timestamp=datetime.now(),
            system=system_metrics,
            agents=agent_metrics,
            retrieval=retrieval_metrics,
            generation=generation_metrics,
            alerts=alerts,
            suggestions=suggestions
        )


@dataclass
class SystemMetrics:
    """系统指标"""
    cpu_usage: float
    memory_usage: float
    gpu_usage: Optional[float]
    active_requests: int
    queue_depth: int
    uptime_seconds: float


@dataclass
class AgentMetrics:
    """Agent指标"""
    total_agents: int
    active_agents: int
    avg_response_time_ms: float
    success_rate: float
    error_rate: float
    by_agent: Dict[str, AgentPerformance]


@dataclass
class AgentPerformance:
    """单个Agent性能"""
    agent_name: str
    request_count: int
    avg_latency_ms: float
    success_count: int
    error_count: int
```

#### 12.3 验收标准

| 验收项 | 标准 | 检查点 |
|--------|------|--------|
| 数据流追踪 | 完整记录所有节点 | 测试各流程 |
| 监控仪表板 | <1s更新 | 实时性能 |
| 告警触发 | 准确及时 | 测试告警条件 |
| 性能报表 | 包含20+指标 | 人工检查 |

---

### 第13次迭代：系统集成与监控（二）

**目标**: 实现异常检测和自动恢复机制

#### 13.1 异常检测器

```python
# src/agents_v2/monitoring/anomaly_detector.py 新增

class AnomalyDetector:
    """
    异常检测器

    检测系统运行中的异常行为
    """

    def __init__(self):
        self._models = {
            "latency": LatencyAnomalyDetector(),
            "error": ErrorRateAnomalyDetector(),
            "quality": QualityAnomalyDetector()
        }
        self._baselines = {}

    async def detect(
        self,
        metrics: Dict[str, Any]
    ) -> List[AnomalyAlert]:
        """检测异常"""
        alerts = []

        # 1. 延迟异常检测
        if "latency_p95" in metrics:
            latency_alert = await self._models["latency"].detect(
                metrics["latency_p95"]
            )
            if latency_alert:
                alerts.append(latency_alert)

        # 2. 错误率异常检测
        if "error_rate" in metrics:
            error_alert = await self._models["error"].detect(
                metrics["error_rate"]
            )
            if error_alert:
                alerts.append(error_alert)

        # 3. 质量异常检测
        if "quality_score" in metrics:
            quality_alert = await self._models["quality"].detect(
                metrics["quality_score"]
            )
            if quality_alert:
                alerts.append(quality_alert)

        return alerts


class LatencyAnomalyDetector:
    """延迟异常检测器"""

    async def detect(self, latency_ms: float) -> Optional[AnomalyAlert]:
        """检测延迟异常"""
        # 使用简单阈值 + 动态基线
        baseline = self._getBaseline()
        threshold = baseline * 2  # 超过基线2倍视为异常

        if latency_ms > threshold:
            return AnomalyAlert(
                type="latency_anomaly",
                severity=self._calculateSeverity(latency_ms, threshold),
                metric="latency_p95",
                value=latency_ms,
                threshold=threshold,
                baseline=baseline,
                suggestion="检查是否有慢查询或外部服务延迟"
            )

        return None
```

#### 13.2 自动恢复机制

```python
# src/agents_v2/monitoring/auto_recovery.py 新增

class AutoRecoveryManager:
    """
    自动恢复管理器

    根据异常类型自动执行恢复策略
    """

    RECOVERY_STRATEGIES = {
        "latency_anomaly": [
            {"action": "clear_cache", "condition": lambda m: m["cache_hit_rate"] < 0.5},
            {"action": "scale_up", "condition": lambda m: m["queue_depth"] > 50},
            {"action": "restart_agent", "condition": lambda m: m["agent_error_rate"] > 0.1}
        ],
        "error_rate_anomaly": [
            {"action": "rollback_version", "condition": lambda m: True},
            {"action": "enable_fallback", "condition": lambda m: True}
        ],
        "quality_anomaly": [
            {"action": "reduce_batch_size", "condition": lambda m: True},
            {"action": "increase_review_iterations", "condition": lambda m: m["iteration_count"] < 3}
        ]
    }

    async def executeRecovery(
        self,
        anomaly: AnomalyAlert,
        context: Dict[str, Any]
    ) -> RecoveryResult:
        """执行恢复"""
        strategies = self.RECOVERY_STRATEGIES.get(anomaly.type, [])

        for strategy in strategies:
            if strategy["condition"](context):
                action = strategy["action"]
                success = await self._executeAction(action, context)

                if success:
                    return RecoveryResult(
                        action_taken=action,
                        success=True,
                        message=f"Successfully executed {action}"
                    )

        return RecoveryResult(
            action_taken=None,
            success=False,
            message="No applicable recovery strategy found"
        )

    async def _executeAction(
        self,
        action: str,
        context: Dict[str, Any]
    ) -> bool:
        """执行具体恢复动作"""
        actions = {
            "clear_cache": self._clearCache,
            "scale_up": self._scaleUp,
            "restart_agent": self._restartAgent,
            "rollback_version": self._rollbackVersion,
            "reduce_batch_size": self._reduceBatchSize
        }

        action_func = actions.get(action)
        if action_func:
            return await action_func(context)

        return False
```

#### 13.3 验收标准

| 验收项 | 标准 | 检查点 |
|--------|------|--------|
| 异常检测 | 检出率>90% | 注入异常测试 |
| 误报率 | <10% | 运行一周统计 |
| 自动恢复 | 恢复成功率>80% | 测试各类异常 |
| 恢复时间 | <30s | 测量MTTR |

---

### 第14次迭代：用户体验优化（一）

**目标**: 实现个性化推荐和智能提示

#### 14.1 用户行为分析器

```python
# src/agents_v2/personalization/behavior_analyzer.py 新增

class UserBehaviorAnalyzer:
    """
    用户行为分析器

    分析用户行为模式，提供个性化体验
    """

    def __init__(self):
        self._behavior_history: List[UserAction] = []
        self._pattern_detector = PatternDetector()

    async def analyzeBehavior(
        self,
        user_id: str
    ) -> BehaviorProfile:
        """分析用户行为"""
        # 1. 收集用户行为
        behaviors = await self._collectUserBehaviors(user_id)

        # 2. 检测模式
        patterns = await self._pattern_detector.detect(behaviors)

        # 3. 推断偏好
        preferences = self._inferPreferences(behaviors)

        # 4. 生成画像
        return BehaviorProfile(
            user_id=user_id,
            patterns=patterns,
            preferences=preferences,
            activity_level=self._calculateActivityLevel(behaviors),
            expertise_level=self._estimateExpertiseLevel(behaviors)
        )

    def _inferPreferences(self, behaviors: List[UserAction]) -> UserPreferences:
        """推断用户偏好"""
        # 分析常用操作
        common_actions = self._getMostCommonActions(behaviors)

        # 分析反馈模式
        feedback_patterns = self._analyzeFeedbackPatterns(behaviors)

        # 分析时间模式
        time_patterns = self._analyzeTimePatterns(behaviors)

        return UserPreferences(
            preferred_output_format=common_actions.get("output_format", "markdown"),
            revision_tolerance=feedback_patterns.get("tolerance", "medium"),
            active_hours=time_patterns.get("active_hours", []),
            depth_preference=common_actions.get("depth", "medium")
        )
```

#### 14.2 智能提示生成器

```python
# src/agents_v2/personalization/smart_prompter.py 新增

class SmartPromptGenerator:
    """
    智能提示生成器

    根据上下文和用户偏好生成有帮助的提示
    """

    def __init__(self):
        self._templates = self._loadTemplates()

    async def generateSuggestions(
        self,
        current_state: AgentState,
        user_context: UserContext
    ) -> List[PromptSuggestion]:
        """生成提示建议"""
        suggestions = []

        # 1. 基于当前状态生成建议
        state_based = await self._generateStateBasedSuggestions(current_state)
        suggestions.extend(state_based)

        # 2. 基于用户历史生成建议
        history_based = await self._generateHistoryBasedSuggestions(user_context)
        suggestions.extend(history_based)

        # 3. 基于最佳实践生成建议
        best_practice = await self._generateBestPracticeSuggestions(current_state)
        suggestions.extend(best_practice)

        # 4. 排序和过滤
        suggestions = self._rankAndFilter(suggestions)

        return suggestions[:5]  # 返回Top 5

    async def _generateStateBasedSuggestions(
        self,
        state: AgentState
    ) -> List[PromptSuggestion]:
        """基于当前状态生成建议"""
        suggestions = []

        if state.phase == "writing" and state.revision_count > 2:
            suggestions.append(PromptSuggestion(
                type="encouragement",
                message="已经修订多次，可以考虑先生成大纲或调整研究方向",
                priority="low"
            ))

        if state.quality_score < 0.6:
            suggestions.append(PromptSuggestion(
                type="help",
                message="当前质量分数偏低，建议先完善文献综述部分",
                priority="high"
            ))

        return suggestions
```

#### 14.3 验收标准

| 验收项 | 标准 | 检查点 |
|--------|------|--------|
| 行为分析 | 偏好识别准确率>80% | 用户调查对比 |
| 智能提示 | 用户满意度>4/5 | 问卷调查 |
| 个性化推荐 | 点击率>30% | 统计点击 |
| 提示相关性 | 提示有用率>70% | 用户反馈 |

---

### 第15次迭代：用户体验优化（二）

**目标**: 实现反馈闭环和智能辅助

#### 15.1 反馈闭环处理器

```python
# src/agents_v2/feedback/feedback_loop.py 新增

class FeedbackLoopProcessor:
    """
    反馈闭环处理器

    处理用户反馈，改进系统表现
    """

    def __init__(self):
        self._feedback_store = FeedbackStore()
        self._improvement_engine = ImprovementEngine()

    async def processFeedback(
        self,
        feedback: UserFeedback
    ) -> FeedbackResult:
        """处理用户反馈"""
        # 1. 分类反馈
        category = self._classifyFeedback(feedback)

        # 2. 提取可操作项
        actionable = self._extractActionableItems(feedback)

        # 3. 执行改进（如适用）
        improvements = []
        for item in actionable:
            improvement = await self._improvement_engine.suggestImprovement(item)
            if improvement:
                improvements.append(improvement)

        # 4. 更新用户偏好
        await self._updateUserPreferences(feedback)

        # 5. 记录反馈用于学习
        await self._feedback_store.record(feedback)

        return FeedbackResult(
            category=category,
            actionable_items=actionable,
            improvements=improvements,
            acknowledgment=await self._generateAcknowledgment(feedback)
        )

    async def _improveFromFeedback(
        self,
        feedback: UserFeedback
    ) -> Optional[SystemImprovement]:
        """从反馈中学习并改进"""
        # 分析反馈类型
        if feedback.type == "quality_issue":
            # 质量问题，改进生成策略
            return await self._suggestGenerationImprovement(feedback)
        elif feedback.type == "format_issue":
            # 格式问题，改进导出器
            return await self._suggestFormatImprovement(feedback)
        elif feedback.type == "missing_content":
            # 内容缺失，改进检索策略
            return await self._suggestRetrievalImprovement(feedback)

        return None
```

#### 15.2 智能辅助助手

```python
# src/agents_v2/assistant/smart_assistant.py 新增

class SmartAssistant:
    """
    智能辅助助手

    在写作过程中提供实时辅助
    """

    def __init__(self):
        self._context_analyzer = ContextAnalyzer()
        self._suggestion_engine = SuggestionEngine()

    async def provideAssistance(
        self,
        current_content: str,
        cursor_position: int,
        user_context: UserContext
    ) -> AssistantResponse:
        """提供辅助"""
        # 1. 分析当前上下文
        context = await self._context_analyzer.analyze(
            content=current_content,
            cursor_position=cursor_position
        )

        # 2. 生成建议
        suggestions = await self._suggestion_engine.generate(
            context=context,
            user_preferences=user_context.preferences
        )

        # 3. 生成快捷操作
        quick_actions = await self._generateQuickActions(context)

        return AssistantResponse(
            suggestions=suggestions,
            quick_actions=quick_actions,
            auto_completions=await self._getAutoCompletions(context)
        )

    async def _getAutoCompletions(
        self,
        context: EditingContext
    ) -> List[str]:
        """获取自动补全选项"""
        if context.intent == "writing_reference":
            # 写作引用，提供参考文献格式
            return ["[1]", "[Author, Year]", "[Author et al., Year]"]
        elif context.intent == "writing_section_header":
            # 写章节标题，提供建议标题
            return ["研究背景", "相关工作", "方法", "实验结果", "讨论", "结论"]
        elif context.intent == "writing_citation":
            # 引用格式
            return self._getCitationFormats(context.target_format)

        return []
```

#### 15.3 验收标准

| 验收项 | 标准 | 检查点 |
|--------|------|--------|
| 反馈处理 | <1s响应 | 测量延迟 |
| 改进建议 | 采纳率>30% | 跟踪实施 |
| 智能补全 | 准确率>80% | 统计使用 |
| 辅助满意度 | >4/5 | 用户调查 |

---

### 第16-20次迭代：总结与验收

由于篇幅限制，第16-20次迭代聚焦于系统集成测试、性能优化、文档完善、最终验收等收尾工作。

详细任务包括：

| 迭代 | 主题 | 核心任务 |
|------|------|---------|
| 16 | 测试与验证 | 端到端测试、性能基准、压力测试 |
| 17 | 性能优化 | 缓存优化、并发优化、延迟优化 |
| 18 | 文档完善 | API文档、用户指南、开发者文档 |
| 19 | 安全加固 | 权限验证、数据加密、审计日志 |
| 20 | 最终验收 | 全面测试、评分、发布准备 |

---

## 三、遗漏点优先级与工作量评估

### 3.1 P0级遗漏点（必须实现）

| 遗漏点 | 工作量 | 优先级理由 |
|--------|--------|-----------|
| 多意图处理与消歧 | 中 | 影响核心用户体验 |
| 双栏排版检测 | 高 | PDF解析基础能力 |
| 逻辑连贯性保证 | 高 | 生成质量核心 |
| 恶意输入防护 | 中 | 系统安全基础 |

### 3.2 P1级遗漏点（应该实现）

| 遗漏点 | 工作量 | 优先级理由 |
|--------|--------|-----------|
| 置信度校准 | 低 | 提升准确性 |
| 跨语言检索 | 中 | 扩展适用性 |
| 查询理解增强 | 中 | 检索质量提升 |
| 章节生成策略 | 中 | 生成专业化 |
| Self-RAG生成 | 高 | 质量控制核心 |
| 版本管理 | 中 | 用户体验提升 |

### 3.3 P2级遗漏点（可以优化）

| 遗漏点 | 工作量 | 价值 |
|--------|--------|------|
| HyDE检索 | 高 | 检索增强 |
| 渲染预览 | 中 | 用户体验 |
| 图表关系映射 | 高 | 深度理解 |
| 个性化推荐 | 中 | 用户粘性 |

---

## 四、完整迭代清单

| 迭代 | 主题 | 关键文件 | 遗漏点覆盖 |
|------|------|---------|-----------|
| 1 | 输入处理强化（一） | intent_router.py, validators.py | 多意图处理、安全验证 |
| 2 | 输入处理强化（二） | multilingual/ | 跨语言处理 |
| 3 | 检索链路强化（一） | retrieval/ | 查询理解、查询改写 |
| 4 | 检索链路强化（二） | retrieval/ | 多源融合、质量评估 |
| 5 | PDF解析强化（一） | pdf_layout/ | 双栏检测、公式处理 |
| 6 | PDF解析强化（二） | pdf_references/ | 参考文献解析、表格处理 |
| 7 | PDF解析强化（三） | pdf_analysis/ | 贡献提取、引用映射 |
| 8 | 生成链路强化（一） | writing/ | 章节策略、质量控制 |
| 9 | 生成链路强化（二） | writing/ | Self-RAG、原创性检测 |
| 10 | 输出链路强化（一） | output/ | 多格式导出、预览 |
| 11 | 输出链路强化（二） | output/ | 版本管理、增量更新 |
| 12 | 系统监控（一） | monitoring/ | 数据流追踪、仪表板 |
| 13 | 系统监控（二） | monitoring/ | 异常检测、自动恢复 |
| 14 | 用户体验（一） | personalization/ | 行为分析、智能提示 |
| 15 | 用户体验（二） | feedback/ | 反馈闭环、智能辅助 |
| 16 | 测试验证 | tests/ | E2E测试、性能基准 |
| 17 | 性能优化 | optimization/ | 缓存、并发优化 |
| 18 | 文档完善 | docs/ | API文档、用户指南 |
| 19 | 安全加固 | security/ | 权限、加密、审计 |
| 20 | 最终验收 | - | 全面测试、发布 |

**总计**: 20次迭代，覆盖所有研究提示词中的遗漏点

---

**文档状态**: 完成
**版本**: v0.4
**基于**: Agent深度研究提示词
**最后更新**: 2026-04-27