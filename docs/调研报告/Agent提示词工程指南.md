# Agent提示词工程指南

> 论文Agent系统的提示词工程完整指南，涵盖规范写法与深度研究方法
>
> **项目参考**: 所有Agent的提示词写法需参考本文档
>
> - 规范写法: 第一部分（第一章～第十章）
> - 深度研究: 第二部分（第十一章～第十四章）

**文档版本**: v2.0（融合版）
**更新日期**: 2026-04-28

---

## 第一部分：提示词规范写法

### 一、Agent提示词结构

#### 1.1 标准提示词模板

每个Agent的提示词应包含以下五个部分：

```
┌─────────────────────────────────────────────────────────────┐
│                    SYSTEM PROMPT 结构                        │
├─────────────────────────────────────────────────────────────┤
│  1. 角色定义 (Role Definition)                              │
│     - Agent身份、专业背景                                   │
│     - 核心职责说明                                          │
│                                                             │
│  2. 能力边界 (Capabilities)                                 │
│     - 能做什么                                               │
│     - 具备哪些专业知识                                       │
│                                                             │
│  3. 行为准则 (Guidelines)                                  │
│     - 应该如何处理任务                                       │
│     - 质量标准                                               │
│                                                             │
│  4. 约束限制 (Constraints)                                 │
│     - 不能做什么                                             │
│     - 限制条件                                               │
│                                                             │
│  5. 输出格式 (Output Format)                               │
│     - JSON Schema定义                                        │
│     - 示例输出                                               │
└─────────────────────────────────────────────────────────────┘
```

#### 1.2 实际代码示例

**QueryRouter Agent (问题路由)**

```python
# 代码位置: src/agents_v2/qa/query_router.py
self.system_prompt = """你是一个专业的问题分类专家，擅长判断用户问题的类型并决定最佳处理策略。

问题类型定义：
1. BASIC_QUERY（基础查询）：简单的事实性问题，可以直接回答
   - 例如：什么是贝叶斯定理？正态分布的定义是什么？
   - 处理方式：直接回答，不需要搜索论文

2. PROFESSIONAL（专业问题）：需要深入解释的方法论或理论问题
   - 例如：分层模型的MCMC估计方法有哪些？
   - 处理方式：搜索论文后给出专业回答

3. FRONTIER（前沿探索）：关于最新研究进展的问题
   - 例如：2024年统计学习有什么新突破？
   - 处理方式：搜索arXiv最新论文

4. APPLICATION（应用咨询）：关于在实际场景中应用的问题
   - 例如：如何在医学研究中应用倾向性评分？
   - 处理方式：搜索PubMed案例

输出格式（JSON）：
{
    "question_type": "professional",
    "confidence": 0.85,
    "reasoning": "这是一个关于统计方法的问题，需要搜索论文获得更详细的专业解释",
    "suggested_path": "paper_search",
    "filters": {
        "domain": "statistics",
        "sort_by": "relevance"
    }
}
"""
```

**TopicRefiner Agent (选题精炼)**

```python
# 代码位置: src/agents_v2/problem_oriented/topic_refiner.py
system_prompt = """你是一个学术研究选题专家。
你的职责是帮助用户优化研究选题，确保：
1. 选题具体、可执行
2. 具有创新性
3. 在用户能力范围内
4. 有研究价值

请分析用户输入，诊断问题，并提供具体改进建议。"""
```

---

### 二、不同类型Agent的提示词规范

#### 2.1 路由类Agent (Intent Router / Query Router)

**职责**: 识别用户意图，分类问题类型，决定处理路径

**提示词要点**:
1. 清晰定义各类问题的特征
2. 给出每类问题的典型示例
3. 明确处理路径映射
4. 指定置信度阈值

**模板**:
```
## 角色
你是一个[领域]问题分类专家。

## 问题类型定义
1. TYPE_A（类型A）：
   - 特征：[识别特征]
   - 示例：[典型问题]
   - 处理：[处理方式]

2. TYPE_B（类型B）：
   - ...

## 输出格式
{
    "question_type": "类型",
    "confidence": 0.0-1.0,
    "reasoning": "判断理由",
    "suggested_path": "处理路径",
    "filters": {}
}
```

#### 2.2 搜索类Agent (Paper Search)

**职责**: 多源检索、查询优化、结果排序

**提示词要点**:
1. 多平台特点说明 (arXiv/PubMed/SS)
2. 查询扩展和改写策略
3. 结果质量评估标准
4. 去重和排序规则

**模板**:
```
## 角色
你是一个学术论文搜索专家。

## 搜索策略
- 核心查询：[主体概念]
- 扩展查询：[同义词/相关词]
- 限定条件：[时间/来源/类型]

## 结果评估
1. 相关性评分标准
2. 质量评估维度
3. 排序优先级

## 输出格式
{
    "papers": [...],
    "total": 数量,
    "sources": ["来源列表"]
}
```

#### 2.3 诊断类Agent (Problem Diagnosis)

**职责**: 问题识别、根因分析、严重程度评估

**提示词要点**:
1. 问题分类体系
2. 诊断维度清单
3. 严重程度判定标准
4. 修复优先级建议

**模板**:
```
## 角色
你是一个专业的[领域]问题诊断专家。

## 诊断维度
1. [维度1]：评估标准
2. [维度2]：评估标准

## 问题分类
- ISSUE_A：问题描述
- ISSUE_B：问题描述

## 严重程度
- HIGH：影响大，需优先修复
- MEDIUM：中等影响
- LOW：轻微问题

## 输出格式
{
    "problems_found": [...],
    "severity": {"问题": 0.0-1.0},
    "recommendations": [...]
}
```

#### 2.4 生成类Agent (Report/Literature Generation)

**职责**: 内容生成、结构化输出、引用规范

**提示词要点**:
1. 报告结构定义
2. 内容质量标准
3. 引用格式规范
4. 长度限制要求

**模板**:
```
## 角色
你是一个专业的学术[报告/文献]生成专家。

## 职责
1. [职责1]
2. [职责2]

## 生成要求
- 结构：[章节要求]
- 长度：[字数限制]
- 格式：[格式规范]
- 引用：[引用要求]

## 输出格式
{
    "section_1": {...},
    "section_2": {...},
    "references": [...]
}
```

#### 2.5 精炼类Agent (Refinement)

**职责**: 多轮迭代、质量提升、问题修复

**提示词要点**:
1. 评审维度定义
2. 质量评分标准
3. 迭代终止条件
4. 改进建议生成

**模板**:
```
## 角色
你是一个专业的学术论文评审和精炼专家。

## 评审维度
1. 结构完整性
2. 逻辑连贯性
3. 论证充分性
4. 引用准确性
5. 语言表达

## 质量标准
- 优秀 (≥0.9)：满足所有维度
- 良好 (≥0.7)：满足大部分维度
- 一般 (≥0.5)：满足基本要求
- 需改进 (<0.5)：存在重大问题

## 输出格式
{
    "quality_score": 0.0-1.0,
    "issues": [...],
    "suggestions": [...]
}
```

#### 2.6 Pipeline类Agent

**职责**: 流水线执行、阶段输出、流程协调

**提示词要点**:
1. 阶段目标定义
2. 输入输出规范
3. 质量阈值要求
4. 后续Agent建议

**模板**:
```
## 角色
你是一个[阶段名]Agent。

## 阶段目标
- 主要目标：[目标描述]
- 质量要求：[标准]

## 输入规范
{
    "required_fields": [...],
    "optional_fields": [...]
}

## 输出规范
{
    "result": {...},
    "quality_score": 0.0-1.0,
    "next_agents": ["建议的后续Agent"]
}
```

---

### 三、Few-Shot Examples 写法

#### 3.1 为什么需要Few-Shot

Few-Shot Examples帮助LLM理解期望的输入-输出映射关系，提高输出格式的一致性。

#### 3.2 正确写法

```python
FEW_SHOT_EXAMPLES = """
## 输出格式示例

【示例1：主题选择】
输入：我想研究人工智能在教育领域的应用
输出：
{
    "title": "基于大语言模型的个性化自适应学习系统研究",
    "description": "利用LLM技术构建能够根据学生学习行为自动调整难度的智能辅导系统",
    "scope": "聚焦于K-12数学教育场景",
    "innovation": "将生成式AI与知识追踪结合，实现真正的个性化",
    "feasibility": 0.85,
    "literature_support": "深度学习、教育AI、知识追踪相关文献充足"
}

【示例2：聚焦具体问题】
输入：我想做机器学习方面的研究
输出：
{
    "title": "联邦学习中的隐私保护梯度压缩方法研究",
    "description": "在保证差分隐私前提下，通过梯度压缩减少通信开销",
    "scope": "聚焦于图像分类任务的联邦学习场景",
    "innovation": "提出一种新的压缩比自适应策略，平衡隐私和效率",
    "feasibility": 0.78,
    "literature_support": "联邦学习、差分隐私相关文献丰富"
}

【示例3：跨学科研究】
输入：我想研究AI和生物学的交叉方向
输出：
{
    "title": "基于深度学习的蛋白质结构预测优化方法",
    "description": "改进AlphaFold2的预测精度和推理速度",
    "scope": "聚焦于单域蛋白质的结构预测",
    "innovation": "提出轻量化网络结构，降低计算资源需求",
    "feasibility": 0.72,
    "literature_support": "AlphaFold相关文献较多，但应用优化方向较少"
}
"""

# 在system_prompt中使用
system_prompt = """你是一个学术研究主题选择专家。
...
请确保选择的主题具有研究价值和创新性。""" + FEW_SHOT_EXAMPLES
```

#### 3.3 注意事项

1. **示例数量**: 2-3个典型示例即可，过多会增加token消耗
2. **覆盖边界**: 示例应覆盖主要场景和边界情况
3. **格式一致**: 示例输出格式必须与正式输出格式一致
4. **避免偏见**: 示例应多样化，避免模型过度拟合特定风格

---

### 四、Chain-of-Thought (CoT) 提示

#### 4.1 何时使用

当任务复杂、需要多步推理时，使用CoT引导模型逐步思考。

#### 4.2 写法示例

```python
async def _analyze_topic_issues(self, topic: str, user_level: str) -> List[str]:
    """分析选题问题"""
    prompt = f"""
分析以下研究选题的问题：

选题：{topic}
研究者水平：{user_level}

请按以下步骤逐步分析：

步骤1：范围评估
- 判断选题是过于宽泛还是过于狭窄
- 记录判断依据

步骤2：创新性评估
- 分析是否有新颖的研究角度
- 识别潜在创新点

步骤3：可行性评估
- 评估技术可行性
- 评估资源可行性

步骤4：综合诊断
- 汇总上述分析
- 识别主要问题

输出JSON格式：
{{
    "issues": ["问题1", "问题2", ...],
    "scope_assessment": {{
        "too_broad": true/false,
        "too_narrow": true/false,
        "main_issue": "主要问题描述"
    }},
    "reasoning": "分析推理过程"
}}
"""
```

---

### 五、多语言处理提示

#### 5.1 中英文混合输入

```python
prompt = f"""
分析以下研究选题（可能包含中英文混合）：

{user_request}

处理要求：
1. 识别并保留关键英文术语
2. 理解中文表达的研究意图
3. 统一技术术语的使用
4. 生成双语输出（可选）

请用中文输出分析结果。
"""
```

#### 5.2 跨语言检索

```python
prompt = f"""
为以下研究主题生成中英文搜索查询：

主题：{topic}

请生成：
1. 中文查询关键词
2. 英文查询关键词
3. 对应的同义词扩展

输出格式：
{{
    "chinese_queries": [...],
    "english_queries": [...],
    "combined_query": "组合查询"
}}
"""
```

---

### 六、JSON输出处理

#### 6.1 严格的Schema定义

```python
OUTPUT_SCHEMA = """
输出JSON格式：
{
    "required_field": "类型/说明",
    "optional_field": "类型/说明 (可选)",
    "array_field": ["元素类型"],
    "nested_field": {
        "sub_field": "说明"
    }
}
"""
```

#### 6.2 解析与降级

```python
def _parse_report(self, llm_output: str, papers: List[Dict]) -> Dict[str, Any]:
    """解析LLM输出的报告"""
    import json

    try:
        # 尝试解析JSON
        report = json.loads(llm_output)
        return report

    except json.JSONError:
        # 降级处理：手动构建报告
        self.logger.warning("JSON解析失败，使用降级处理")
        return {
            "summary": llm_output[:500],
            "paper_details": [...],
            "references": self._generate_references(papers)
        }
```

#### 6.3 降级策略

```python
async def _llm_call_with_fallback(
    self,
    prompt: str,
    primary_schema: str,
    fallback_schema: str = None
) -> Dict:
    """带降级的LLM调用"""
    try:
        # 尝试严格Schema输出
        response = await self._llm_call(prompt + f"\n\n请严格按以下JSON格式输出：\n{primary_schema}")
        return json.loads(response)
    except json.JSONDecodeError:
        if fallback_schema:
            # 尝试宽松Schema
            try:
                response = await self._llm_call(prompt + f"\n\n请按以下格式输出：\n{fallback_schema}")
                return json.loads(response)
            except:
                pass
        # 最终降级：返回原始文本
        return {"raw_output": response, "parse_error": True}
```

---

### 七、质量评分提示

#### 7.1 多维度评分

```python
prompt = f"""
评审论文质量，从以下维度评分（每项1-10）：

1. 结构完整性：论文结构是否清晰完整
2. 逻辑连贯性：论证逻辑是否严密
3. 创新性：研究贡献是否有创新
4. 实证充分性：实验证据是否充分
5. 语言表达：语言是否准确流畅

论文内容：
{draft[:2000]}...

输出JSON格式：
{{
    "dimension_scores": {{
        "structure": 分数,
        "logic": 分数,
        "novelty": 分数,
        "evidence": 分数,
        "language": 分数
    }},
    "overall_score": 加权平均分,
    "main_strengths": ["主要优点"],
    "main_weaknesses": ["主要缺点"]
}}
"""
```

#### 7.2 阈值判定

```python
QUALITY_THRESHOLDS = {
    "diagnostic": 6.0,   # 诊断阶段不需要太高
    "topic": 7.0,
    "literature": 7.0,
    "methodology": 7.0,
    "writing": 7.0,
    "polish": 8.0        # 最终润色需要更高
}

# 判定逻辑
if quality_score >= QUALITY_THRESHOLDS[phase]:
    # 达标，继续下一阶段
    pass
else:
    # 未达标，迭代修复
    await self._iterate_phase(phase, result)
```

---

### 八、迭代优化提示

#### 8.1 迭代循环结构

```python
async def execute(self, input_data, max_iterations=3, quality_threshold=0.7):
    """多轮迭代执行"""
    current_content = input_data.get("content")
    iteration_history = []

    for iteration in range(max_iterations):
        # 1. 评审当前版本
        review = await self._review(current_content, iteration + 1)

        # 2. 评估质量
        if review["quality_score"] >= quality_threshold:
            break  # 达标，停止迭代

        # 3. 修复问题
        current_content = await self._refine(current_content, review)
        iteration_history.append(review)

    return {
        "final_content": current_content,
        "iterations": len(iteration_history),
        "final_quality": review["quality_score"]
    }
```

#### 8.2 迭代终止条件

```python
TERMINATION_CONDITIONS = {
    "quality_reached": "质量评分达到阈值",
    "max_iterations": "达到最大迭代次数",
    "no_improvement": "连续2轮无明显改进",
    "time_limit": "达到时间限制"
}
```

---

### 九、最佳实践清单

#### 9.1 提示词设计

- [ ] 角色定义清晰，避免模糊身份
- [ ] 职责边界明确，防止任务混乱
- [ ] 示例覆盖主要场景
- [ ] 输出格式严格定义
- [ ] 包含错误处理和降级策略

#### 9.2 JSON输出

- [ ] 使用严格的Schema定义
- [ ] 提供解析失败的降级处理
- [ ] 验证必要字段存在
- [ ] 处理类型转换错误

#### 9.3 迭代优化

- [ ] 设置合理的质量阈值
- [ ] 定义明确的终止条件
- [ ] 记录迭代历史
- [ ] 控制最大迭代次数

#### 9.4 多语言

- [ ] 明确输入语言
- [ ] 统一术语使用
- [ ] 处理混合语言输入
- [ ] 提供双语输出选项

---

### 十、反面示例

#### 10.1 过于简略

```python
# ❌ 不推荐：缺少必要信息
system_prompt = "你是论文助手，帮我写论文。"

# ✅ 推荐：完整定义
system_prompt = """你是一个专业的学术论文写作助手。
你的职责是：
1. 帮助用户撰写学术论文各章节
2. 确保内容符合学术规范
3. 提供专业的语言润色

质量标准：
- 结构清晰，逻辑连贯
- 语言专业，表达准确
- 引用规范，有据可查"""
```

#### 10.2 缺少输出格式

```python
# ❌ 不推荐：输出格式不明确
prompt = "分析这篇论文的创新点。"

# ✅ 推荐：明确输出格式
prompt = """分析这篇论文的创新点。

输出JSON格式：
{
    "innovation_type": "方法创新/应用创新/理论创新",
    "core_contribution": "核心贡献描述",
    "novelty_score": 1-10,
    "comparison_with_existing": "与现有工作的对比"
}
"""
```

#### 10.3 缺少示例

```python
# ❌ 不推荐：没有示例
prompt = "为研究主题生成搜索查询。"

# ✅ 推荐：包含Few-Shot示例
prompt = """为研究主题生成多个搜索查询。

【示例】
输入：深度学习优化方法
输出：
{
    "queries": [
        {"query": "深度学习 优化 方法", "angle": "核心概念"},
        {"query": "神经网络 训练 加速", "angle": "相关技术"}
    ]
}

现在请为以下主题生成查询：
输入：{topic}
输出："""
```

---

## 第二部分：Agent深度研究方法

### 十一、框架搜索提示词

#### 11.1 通用Agent框架搜索

```
你是一名AI Agent研究专家。请帮我系统搜索以下内容：

## 搜索目标

### 1. 主流Agent框架
- LangChain / LangGraph 框架设计
- AutoGPT / BabyAGI 任务拆解机制
- MetaGPT / ChatDev 多Agent协作
- CrewAI 角色扮演框架
- Microsoft AutoGen 对话式Agent框架
- CrewAI / Swarms 多Agent编排

### 2. 论文Agent专用框架
- 学术论文撰写Agent的系统设计
- 论文搜索→理解→写作的Pipeline架构
- 如何构建文献综述Agent
- 论文审稿Agent的框架设计

### 3. RAG Agent架构
- 检索增强生成Agent的标准架构
- Self-RAG / Corrective-RAG 实现方式
- 迭代式检索Agent的设计模式
- 多跳推理Agent框架

### 4. 工具使用框架
- Toolformer / ToolTuning 方法
- ReAct / Plan-and-Execute 范式
- Agent的工具选择与调用机制

## 搜索来源
- ArXiv: cs.AI, cs.CL, cs.LG
- Semantic Scholar
- GitHub (trending repositories)
- 技术博客 / Medium

## 输出格式
1. 每个框架的核心架构图描述
2. 关键技术点清单
3. 论文/代码链接
4. 对现有系统的启发点
```

#### 11.2 GitHub论文Agent搜索

```
请在GitHub上搜索高质量的论文Agent相关项目：

## 搜索关键词
- "paper agent"
- "academic writing agent"
- "literature review agent"
- "research paper generation"
- "arxiv assistant"
- "paper summarizer"

## 评估维度
对于每个找到的仓库，请评估：

### 架构设计
- [ ] 整体架构是Pipeline还是多Agent？
- [ ] Agent之间的通信方式是什么？
- [ ] 状态管理如何实现？
- [ ] 错误处理和容错机制？

### 技术实现
- [ ] 使用了哪些LLM框架？
- [ ] 工具调用如何实现？
- [ ] RAG是如何集成的？
- [ ] 是否有记忆系统？

### 代码质量
- [ ] 代码结构是否清晰？
- [ ] 是否有测试覆盖？
- [ ] 是否模块化设计？
- [ ] 可扩展性如何？

### 功能完整性
- [ ] 支持哪些论文任务？
- [ ] PDF解析能力如何？
- [ ] 引用处理是否完善？
- [ ] 输出格式支持哪些？

## 输出要求
1. Star数排名前10的项目列表
2. 每个项目的架构分析
3. 可借鉴的技术点总结
4. 发现的问题或改进机会
```

---

### 十二、链路深化研究提示词

#### 12.1 输入处理层研究

```
深度研究论文Agent的输入处理层：

## 研究问题

### 意图识别
1. 如何准确识别用户的真实意图？
   - 基于关键词的方法有哪些局限性？
   - LLM-based意图分类的最佳实践？
   - 多意图同时存在的处理策略？

2. 意图的粒度如何设计？
   - 粗粒度：搜索/写作/分析
   - 细粒度：具体任务类型
   - 如何支持意图的组合？

### 输入验证
1. 需要验证哪些输入要素？
   - 文本长度 / 编码格式
   - 敏感信息检测
   - 恶意输入防护

2. 验证失败时的处理策略？
   - 自动修复 vs 拒绝请求
   - 如何给出有意义的错误提示？

### 多语言处理
1. 中英文混合输入如何处理？
2. 跨语言检索如何实现？
3. 多语言输出的质量保证？

## 现有方案分析
请对比分析3-5个主流系统的输入处理方案，指出各自优缺点。
```

#### 12.2 检索链路研究

```
深度研究论文Agent的检索链路：

## 研究问题

### 查询理解
1. 查询解析的完整流程
   - 查询分类（主题/作者/DOI/关键词）
   - 查询扩展（同义词/相关词）
   - 查询改写（口语化→检索式）

2. 如何处理复杂查询？
   - 嵌套查询条件
   - 时间范围限制
   - 排除词/必含词

### 多源检索
1. ArXiv / PubMed / Semantic Scholar 各有什么特点？
   - 数据覆盖范围
   - API限制和速率控制
   - 结果格式差异

2. 如何实现多源结果的融合？
   - 置信度加权
   - 去重策略
   - 排序算法

### 检索优化
1. 迭代式检索何时触发？终止条件？
2. 查询失败时的回退策略？
3. 检索结果的质量评估指标？

## 高级检索策略
1. HyDE (Hypothetical Document Embeddings)
2. Query Decomposition
3. Step-back Prompting
4. Sub-Query Planning

## 输出要求
1. 检索链路的完整流程图
2. 每个环节的关键技术点
3. 现有系统的不足与改进机会
4. 推荐的最优方案
```

#### 12.3 PDF解析链路研究

```
深度研究论文Agent的PDF解析链路：

## 研究问题

### 文本提取
1. 表格类论文的特殊处理？
2. 双栏排版的正确分栏？
3. 脚注/尾注的识别？
4. 数学公式的提取与渲染？

### 结构解析
1. 章节标题的层级识别
2. 摘要/引言/方法/结果/讨论的边界判定
3. 参考文献的完整性提取
4. 图表标题与正文的关联

### 内容理解
1. 如何理解论文的核心贡献？
2. 方法部分的细节提取
3. 实验结果的结构化
4. 引用关系的映射

### 复杂元素
1. 表格：检测→解析→结构化→标准化
2. 图表：分类→标题提取→描述生成
3. 公式：检测→LaTeX转换→渲染

## 技术方案对比
| 方案 | 准确性 | 速度 | 成本 | 适用场景 |
|------|--------|------|------|----------|
| PyPDF2 | | | | |
| pdfplumber | | | | |
| LlamaParse | | | | |
| Marker | | | | |
| GROBID | | | | |

## 输出要求
1. PDF解析的完整pipeline
2. 每个环节的算法选型
3. 准确率/速度的优化建议
4. 开源工具vs自研的权衡
```

#### 12.4 生成链路研究

```
深度研究论文Agent的生成链路：

## 研究问题

### 论文撰写
1. 各章节的撰写要点
   - 摘要：结构化摘要 vs 非结构化
   - 引言：研究背景→研究gap→本文贡献
   - 方法：技术细节的可复现性
   - 结果：数据呈现的逻辑性
   - 讨论：与已有工作的对比

2. 如何保证论文的逻辑连贯性？
3. 长文本生成的一致性如何保证？
4. 引用生成与插入的时机？

### 质量控制
1. Self-RAG在生成中的应用
2. 生成内容的自我评估机制
3. 反思与修订的触发条件
4. 抄袭检测与原创性保证

### 格式规范
1. 不同期刊格式的适配
2. 参考文献格式的自动转换
3. 图表编号与引用的一致性

## 生成策略
1. Retrieval-Augmented Writing
2. Outline-Driven Generation
3. Section-by-Section Writing
4. Multi-Pass Refinement

## 输出要求
1. 生成链路的完整流程
2. 各阶段的质量控制点
3. 现有方案的优缺点分析
4. 提升生成质量的建议
```

#### 12.5 输出链路研究

```
深度研究论文Agent的输出链路：

## 研究问题

### 格式输出
1. 支持哪些输出格式？
   - Markdown / LaTeX / Word
   - PDF / HTML
   - 结构化JSON

2. 格式转换的完整性保证？
3. 渲染效果的预览机制？

### 结果验证
1. 输出内容的完整性检查
2. 格式规范的符合性验证
3. 引用准确性的验证机制

### 用户交互
1. 如何支持用户的修改反馈？
2. 增量更新的实现方式？
3. 版本管理的策略？

## 输出要求
1. 输出链路的完整流程
2. 质量保障机制的设计
3. 用户体验优化建议
```

---

### 十三、综合研究提示词

```
## 论文Agent全链路深度研究

你是一家AI研究机构的高级研究员。请对论文Agent进行全面的技术研究。

### 研究范围

1. **输入处理**
   - 意图识别：准确率>90%的实现方案
   - 输入验证：安全性和有效性保障
   - 多语言支持：中英文混合处理

2. **检索增强**
   - 多源检索：ArXiv / PubMed / SS 的最优组合
   - 查询优化：改写 / 扩展 / 去重
   - 结果融合：排序算法与置信度计算

3. **文档解析**
   - PDF解析：文本 / 表格 / 图表 / 公式
   - 结构化：章节分类 / 引用链接 / 知识抽取
   - 质量评估：解析准确率的衡量标准

4. **内容生成**
   - 论文写作：各章节的生成策略
   - 质量控制：Self-RAG / 反思机制 / 修订流程
   - 引用生成：自动插入与格式规范

5. **系统架构**
   - 多Agent协作：通信协议 / 状态管理 / 错误处理
   - Pipeline编排：串行 / 并行 / 条件分支
   - 可扩展性：模块化 / 插件机制

### 研究要求

1. **技术深度**：每个环节需要深入到具体算法和实现细节
2. **实践验证**：通过代码实验验证方案的可行性
3. **对比分析**：对比多个方案的优劣
4. **改进建议**：指出现有系统的不足，提出具体的改进方向

### 输出结构

1. 每个链路的现状分析
2. 关键技术点详解
3. 最佳实践建议
4. 遗漏点清单
5. 优先级排序的改进计划

### 发现遗漏点时的要求

当你发现现有系统中没有注意到的重要技术点时：
1. 详细说明该技术点的价值
2. 提供具体的实现思路
3. 给出预期的效果提升
4. 评估实现的复杂度
```

---

### 十四、发现遗漏点报告模板

```markdown
## 遗漏点报告

### 1. [技术点名称]

**发现位置**: __________
**当前状态**: ❌ 未实现 / ⚠️ 部分实现

**详细描述**:
...

**实现价值**:
- 价值1
- 价值2

**实现方案**:
```python
# 伪代码或关键逻辑
...
```

**预期效果**:
- 指标1提升: X% → Y%
- 指标2提升: X% → Y%

**实现复杂度**: 低 / 中 / 高

**优先级**: P0 / P1 / P2
```

---

## 附录：代码位置索引

| Agent类型 | 代码位置 | 提示词特点 |
|----------|----------|-----------|
| QueryRouter | `qa/query_router.py` | 问题分类、多路径映射 |
| TopicRefiner | `problem_oriented/topic_refiner.py` | 诊断-建议模式 |
| TopicAgent | `paper_agents/topic_agent.py` | Few-Shot示例丰富 |
| LiteratureReview | `writing/literature_review.py` | 多模式（full/tracking/summary） |
| ReportRefiner | `writing/report_refiner.py` | 多轮迭代、质量评分 |
| PaperFlash | `qa/paper_flash.py` | 快讯格式、5分钟阅读 |

---

*文档版本: v2.0（融合版）*
*原文档: Agent深度研究提示词.md + Agent提示词写法规范.md*
*更新时间: 2026-04-28*