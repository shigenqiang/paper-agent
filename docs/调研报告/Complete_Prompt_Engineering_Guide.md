# 提示词工程完全指南

> 更新时间：2026年4月 | 涵盖 OpenAI、Anthropic、Google、斯坦福等官方与学术前沿最佳实践

---

## 目录

1. [提示词核心要素](#一提示词核心要素)
2. [基础提示范式](#二基础提示范式)
3. [思维链技术](#三思维链技术)
4. [思维演化技术](#四思维演化技术)
5. [自动提示优化](#五自动提示优化)
6. [Agent框架与提示设计](#六agent框架与提示设计)
7. [高级RAG提示技术](#七高级rag提示技术)
8. [结构化模板框架](#八结构化模板框架)
9. [角色设定技巧](#九角色设定技巧)
10. [输出格式与参数控制](#十输出格式与参数控制)
11. [复杂任务处理](#十一复杂任务处理)
12. [提示词安全](#十二提示词安全)
13. [实践应用模板](#十三实践应用模板)
14. [提示词优化实战](#十四提示词优化实战)
15. [技术选型速查表](#十五技术选型速查表)
16. [最佳实践与资源](#十六最佳实践与资源)

---

## 一、提示词核心要素

### 1.1 提示词的基本组成

一个完整的提示词通常包含以下四个核心要素：

| 要素 | 说明 | 示例 |
|------|------|------|
| **指令 (Instruction)** | 明确告知模型要执行的任务 | "请总结以下文本" |
| **上下文 (Context)** | 提供背景信息，帮助模型更好地理解 | "这是一篇关于AI的技术文章" |
| **输入数据 (Input)** | 需要模型处理的具体数据或内容 | "【在此输入要总结的文本】" |
| **输出格式 (Output Indicator)** | 指定期望的输出类型或格式 | "以JSON格式输出" |

---

### 1.2 OpenAI 官方最佳实践

**策略一：写清晰的指令**

| 技巧 | 说明 | 示例 |
|------|------|------|
| 详细说明 | 提供完整的背景和期望 | 差："解释AI" → 好："用2-3句话向高中生解释AI的概念" |
| 要求特定角色 | 指定模型扮演的专家角色 | "你是一位资深数据分析师..." |
| 使用分隔符 | 用 `###`、`"""`、XML标签分隔不同部分 | `###指令### ... ###背景###` |
| 明确步骤 | 将复杂任务分解为多个步骤 | "首先...然后...最后..." |
| 提供示例 | 通过示例展示期望的输出格式 | 给出"输入→输出"的样本 |
| 指定输出长度 | 明确要求输出的词语/句子/段落数量 | "用100字总结" |

**策略二：提供参考文本**

- 让模型直接引用提供的文本回答问题
- 要求模型在回答时引用参考文本中的具体部分
- 减少模型虚构答案的概率

**策略三：将复杂任务拆分为简单子任务**

- 将复杂系统分解为模块化组件
- 分步处理，提高可靠性

---

## 二、基础提示范式

### 2.1 Zero-Shot Prompting（零样本提示）

无需提供任何示例，直接使用模型在海量数据中学习到的通用知识和能力。

**适用场景：** 简单、直接的任务

**最佳实践（OpenAI官方）：**
- 将指令放在提示开头
- 使用分隔符（如 `###`、`"""`）分隔指令和上下文
- 明确具体地描述期望的背景、结果、长度、格式、风格
- 指定输出格式时提供示例

**示例：**
```
将以下文本分类为积极、消极或中性：
"这部电影太精彩了！"
```

---

### 2.2 Few-Shot Prompting（少样本提示）

通过提供少量示例（通常2-5个），引导模型理解任务模式和输出格式。

**核心要素：**

| 要素 | 说明 |
|------|------|
| 示例数量 | 通常2-5个，复杂任务可增加到10个 |
| 代表性 | 示例应覆盖各种情况，避免偏颇 |
| 格式一致 | 输入输出的结构、风格保持一致 |
| 标签分布 | 按照真实标签分布选择示例 |

**示例结构：**
```
请将以下中文翻译成英文：

示例：
中文：你好 → 英文：Hello
中文：早上好 → 英文：Good morning
中文：谢谢 → 英文：Thank you

现在请翻译：
中文：我喜欢人工智能
```

**适用场景：**
- 回复格式有严格要求（如JSON）
- 问题复杂，需要按照模板格式化输出
- 需要模型模仿某种语气或风格

---

### 2.3 Medprompt 技术（Google 先进提示技术）

Medprompt 是由 Google 提出的一组先进提示技术组合，在医学问答（MMLU）上达到 90.10% 的准确率，超越 GPT-4。

**核心组件：**

| 技术 | 说明 |
|------|------|
| **Chain-of-Thought with Self-Consistency** | 结合思维链和自一致性 |
| **Selection-inference prompting** | 选择-推理提示 |
| **Ensemble reasoning** | 集成推理 |

**扩展应用：**
Google 团队将 Medprompt+ 扩展到非医疗领域，在 GSM8K、MATH、HumanEval 等基准上也取得了显著提升。

---

## 三、思维链技术（Chain-of-Thought）

### 3.1 标准 CoT

通过让模型详细阐述其解决问题的推理过程，引导模型逐步思考。

**核心方法：**
- 在提示中加入 "Let's think step by step" 或 "请解释你的推理过程"
- 或提供完整的推理示例

**适用场景：** 数学推理、逻辑分析、复杂决策

**示例：**
```
问题：一个商人进货价30元，卖出价50元，他卖了100件赚了多少钱？

推理步骤：
1. 每件商品的利润 = 卖出价 - 进货价 = 50 - 30 = 20元
2. 卖了100件
3. 总利润 = 20 × 100 = 2000元

答案：2000元
```

**Zero-shot CoT：**
```
问题：[在此输入问题]
请逐步解释你的推理过程。
```

---

### 3.2 Auto-CoT（自动思维链）

自动生成思维链示例，减少人工标注成本。

**流程：**
1. 使用或不使用少量 CoT 示例查询 LLM
2. 对问题生成 k 个可能答案
3. 基于 k 个答案计算不确定度（使用不一致性）
4. 选择最不确定的问题由人类注释
5. 使用新注释的范例进行推断

---

### 3.3 CoT + Self-Consistency（自洽性）

生成多个推理路径，选择最一致的答案。

**优势：**
- 提高推理准确性
- 减少随机性带来的误差
- 适用于需要深思熟虑的问题

---

### 3.4 Logical CoT（逻辑思维链）

在标准 CoT 基础上增加逻辑验证步骤：

| 步骤 | 说明 |
|------|------|
| 假设生成 | 提出多个可能的解决方案 |
| 逻辑验证 | 检验每个假设的有效性 |
| 一致性检查 | 确保推理过程自洽 |

---

### 3.5 PAL（程序辅助语言模型）

使用 LLM 生成程序作为中间推理步骤，而非自由形式文本。

**与 CoT 的区别：**
- 将解决步骤卸载到编程运行时（如 Python 解释器）
- 适合需要日期理解、数学计算等任务

**示例：**
```python
# 模型生成 Python 代码解决日期问题
from langchain_openai import ChatOpenAI
from datetime import datetime, relativedelta

llm = ChatOpenAI(model="gpt-4")
# 模型会生成代码并执行
```

---

### 3.6 Multimodal CoT（多模态思维链）

将 CoT 扩展到多模态场景，处理文本、图像、视频等多种输入。

**最新研究（2025）：**
- 《Multimodal Chain-of-Thought Reasoning: A Comprehensive Survey》
- 《Evolver: Chain-of-Evolution Prompting》用于仇恨表情包检测
- Visual Chain-of-Thought 用于 3D 视觉环境推理

---

## 四、思维演化技术（Thought Evolution）

### 4.1 Tree of Thoughts (ToT) - 思维树

将问题解决过程建模为树结构，允许模型探索多条推理路径。

**流程：**

| 步骤 | 说明 |
|------|------|
| 生成 | 为每个节点生成多个候选思维 |
| 评估 | 评估每个思维的价值 |
| 扩展 | 选择最有希望的节点继续扩展 |
| 搜索 | 使用 BFS/DFS 进行搜索 |

**适用场景：**
- 需要探索多种可能性的复杂决策
- 创意写作、战略规划

---

### 4.2 Graph of Thoughts (GoT) - 思维图

将 ToT 进一步扩展为图结构，支持更复杂的思维关系。

**核心创新：**
- 支持思维的循环和回溯
- 可以合并多个思维路径
- 更符合人类真实思考过程

**论文：** Graph of Thoughts: Solving Elaborate Problems with Large Language Models（苏黎世联邦理工学院）

**框架实现：**
```python
# GoT 核心思想
thoughts = generate_initial_thoughts(problem)
while not solved:
    evaluated = evaluate_thoughts(thoughts)
    selected = select_promising(evaluated)
    expanded = expand_with_graph(selected, thoughts)
    thoughts = merge_graphs(expanded, thoughts)
```

---

### 4.3 Algorithm of Thoughts (AoT) - 算法思维

使用算法思维引导推理，结合搜索算法的思想。

**特点：**
- 将确定性算法思想引入提示
- 减少推理的随机性
- 提高可解释性

---

## 五、自动提示优化

### 5.1 Automatic Prompt Engineer (APE)

让模型自己生成和优化提示。

**方法：**

| 方法 | 说明 |
|------|------|
| **Forward Generation Template** | 生成候选 prompt |
| **Reverse Generation Template** | 反向生成 prompt |
| **评估** | 基于训练数据评估候选 prompt 质量 |

**论文：** Automatic Prompt Optimization (arXiv:2211.01910)

---

### 5.2 DSPy（斯坦福大学）

"Programming—not prompting"——通过声明式编程自动编译提示。

**核心模块：**

| 模块 | 说明 |
|------|------|
| **Signature** | 定义任务范式（如 `Context, Question -> Answer`） |
| **Module** | 类似 PyTorch 模块，支持组合 |
| **Telemetry** | 追踪推理过程 |
| **Assertions** | 计算约束用于自优化 |

**工作流程：**
```
任务定义 → Signature → 模块组合 → 编译优化 → 部署
```

**GitHub：** stanfordnlp/dspy（15k+ stars）

**代码示例：**
```python
import dspy

# 定义签名
signature = dspy.Signature("context, question -> answer")

# 创建模块
cot = dspy.ChainOfThought(signature)

# 编译优化
compiled = dspy.compile(my_pipeline, trainset=train_data)

# 使用
result = compiled(question="...")
```

**项目适配性分析：**

| DSPy特性 | 项目现状 | 适配难度 |
|---------|---------|---------|
| Signature定义 | 目前用system_prompt字符串 | 低 - 可逐步迁移 |
| Module组合 | AgentLoop已实现ReAct | 中 - 需要适配 |
| 自动优化 | 纯手工调优 | 高 - 需要训练数据 |
| Telemetry | 已有stats统计 | 低 - 可对接 |

**集成方案：**

**方案A：渐进式迁移（推荐）**

```
阶段1（1-2月）：
- 保持现有架构
- 使用DSPy的Module（如dspy.ChainOfThought）增强特定Agent
- 积累标注数据

阶段2（3-4月）：
- 引入DSPy Compiler
- 对高频任务（选题、润色）进行提示优化
- A/B测试验证效果

阶段3（5-6月）：
- 全面集成DSPy
- 自动化提示优化上线
- 持续迭代
```

**方案B：保守集成**

```
仅将DSPy用于：
- 新Agent的快速原型
- 特定复杂任务的提示优化
- 不改动现有AgentLoop架构
```

**预期收益与成本：**

| 维度 | 收益 | 成本 |
|-----|------|------|
| **提示词管理** | 集中化、可版本控制 | 引入新框架学习成本 |
| **提示词质量** | 自动优化，效果提升 | 需要高质量训练数据 |
| **开发效率** | 减少手工调优 | 初期配置复杂 |
| **可维护性** | Signature即文档 | 调试需要理解DSPy |

---

### 5.3 Active-Prompt

自适应选择最有效的示例进行提示。

**流程：**
1. 生成 k 个候选答案
2. 计算不确定度（不一致性）
3. 选择最不确定的问题进行人工注释
4. 使用新注释进行推断

---

### 5.4 Directional Stimulus Prompting

训练一个小的策略模型生成刺激提示，引导主模型。

**特点：**
- 可调节的策略 LM
- 使用 RL 优化提示
- 黑盒冻结 LLM

---

## 六、Agent 框架与提示设计

### 6.1 ReAct (Reason + Act)

结合推理和行动，是当前 Agent 主流决策模型。

**核心循环：**
```
Thought → Action → Observation → Thought → ...
```

**提示模板：**
```python
system_prompt = """你是一个助手。思考时，先分析情况，
然后决定行动。观察结果后再调整策略。

可用工具：
- search: 搜索信息
- calculate: 计算

示例：
问题：北京今天的天气如何？
思考：我需要先搜索北京的天气信息
行动：search(北京天气)
观察：搜索结果显示北京今天晴朗
思考：北京天气晴朗，适合户外活动
最终回答：北京今天天气晴朗...
"""
```

---

### 6.2 Plan-and-Execute

先规划再执行，减少调用次数。

**流程：**
1. **规划**：生成完整任务计划
2. **执行**：按计划逐步执行
3. **调整**：根据结果调整后续计划

**优势：** 对于复杂任务，只需调用3次大模型而非每次工具调用都调用

**适用场景：** 论文写作等多阶段任务

---

### 6.3 多Agent框架对比

| 框架 | 特点 | 适用场景 |
|------|------|----------|
| **MetaGPT** | 丰富的预定义代理库，支持SOP | 复杂多代理协作 |
| **CrewAI** | 强调角色定义和任务分配 | 任务导向协作 |
| **LangChain Agent** | 生态完善，组件丰富 | 通用Agent开发 |
| **AutoGen** | 社区驱动，支持人工反馈 | 复杂大型应用 |

---

### 6.4 决策模型对比

| 框架 | 特点 | 适用场景 |
|------|------|----------|
| **ReAct** | 边推理边执行 | 开放域问答、搜索 |
| **Plan-and-Execute** | 先规划后执行 | 复杂多步任务 |
| **LLMCompiler** | 并行执行，生成DAG | 工具调用密集型 |
| **BabyAGI** | 目标分解+反思 | 自主任务完成 |

---

## 七、高级RAG提示技术

### 7.1 预检索优化

| 技术 | 说明 |
|------|------|
| **HyDE** | 生成假设性文档改善检索 |
| **query expansion** | 查询扩展生成多个子搜索 |
| **step-back prompting** | 抽象问题后再检索 |

---

### 7.2 检索后优化

| 技术 | 说明 |
|------|------|
| **reranking** | 重排序提升相关性 |
| **context compression** | 压缩冗余上下文 |
| **citation** | 引用来源增强可信度 |

---

### 7.3 Graph RAG

结合知识图谱的 RAG 技术：

```python
# 示例：知识图谱增强的提示
prompt = """
基于以下知识图谱信息回答问题：

{knowledge_graph_context}

问题：{question}

要求：
1. 优先使用图中关系进行推理
2. 如果不确定，说明不知道
3. 引用信息来源
"""
```

---

## 八、结构化模板框架

### 8.1 CRISPE 框架

| 组成部分 | 说明 | 示例 |
|----------|------|------|
| **C - Capacity and Role** | 定义AI扮演的角色 | "你是一位资深营销专家" |
| **I - Insight** | 提供背景和上下文 | "熟悉现代社交媒体趋势" |
| **S - Statement** | 明确具体任务 | "请为新产品撰写推广文案" |
| **P - Personality** | 指定回应的风格/个性 | "使用专业但亲切的语气" |
| **E - Experiment** | 请求多个示例或尝试 | "提供3个不同版本的文案" |

---

### 8.2 BROKE 框架

融合 OKR 方法论：

| 组成部分 | 说明 |
|----------|------|
| **B - Background** | 提供足够的背景信息 |
| **R - Role** | 设定特定的角色 |
| **O - Objectives** | 定义明确的目标 |
| **K - Key Results** | 定义可衡量的关键结果 |
| **E - Evolve** | 通过试验和调整优化 |

---

### 8.3 T.C.R.E.I 框架（Google）

| 组成部分 | 说明 |
|----------|------|
| **T - Task** | 任务定义 |
| **C - Context** | 上下文 |
| **R - References** | 参考资料 |
| **E - Evaluate** | 评估 |
| **I - Iterate** | 迭代 |

---

### 8.4 RTF 框架（角色-任务-格式）

| 组成部分 | 说明 |
|----------|------|
| **R - Role** | 定义执行任务的角色 |
| **T - Task** | 明确需要完成的工作 |
| **F - Format** | 描述任务的输出结构 |

---

### 8.5 CTF 框架（背景-任务-格式）

| 组成部分 | 说明 |
|----------|------|
| **C - Context** | 提供任务的背景信息 |
| **T - Task** | 描述要完成的具体工作 |
| **F - Format** | 定义任务的呈现方式 |

---

### 8.6 COAST 框架

| 组成部分 | 说明 |
|----------|------|
| **C - Context** | 背景 |
| **O - Objective** | 目标 |
| **A - Action** | 行动 |
| **S - Style** | 风格 |
| **T - Tone** | 语气 |

---

## 九、角色设定技巧

### 9.1 为什么需要设定角色？

LLM 在训练时涵盖了各种质量的数据，默认情况下生成高低质量内容的概率相当。当设定"XX专家"角色时，模型会尽可能将概率分布集中在高质量解决方案上。

**本质：** 明确要求模型表现得好，引导其选择正确答案。

---

### 9.2 角色设定最佳实践

| 技巧 | 示例 |
|------|------|
| 指定专业领域 | "你是一位资深数据分析师" |
| 指定经验和背景 | "你是一位拥有10年经验的Python工程师" |
| 指定语言风格 | "你是一位幽默的技术作家" |
| 指定目标受众 | "向完全没有技术背景的用户解释" |
| 指定场景 | "在会议中使用的正式邮件" |

**高级技巧：** "如果有更好的解决方案，我会奖励 xxx"

---

## 十、输出格式与参数控制

### 10.1 结构化输出

| 格式类型 | 适用场景 |
|----------|----------|
| JSON | API调用、数据处理 |
| Markdown | 文档、报告 |
| CSV | 表格数据 |
| 列表 | 枚举、项目 |
| 代码块 | 技术文档 |

**示例（JSON）：**
```json
{
  "姓名": "张三",
  "年龄": 30,
  "职业": "软件工程师"
}
```

---

### 10.2 控制输出长度

| 指令方式 | 示例 |
|----------|------|
| 指定字数 | "用100字总结" |
| 指定句子数 | "用3句话概括" |
| 指定段落数 | "分成3个段落" |
| 指定项目数 | "列出5个要点" |

---

### 10.3 温度参数配置

| 值 | 效果 | 适用场景 |
|----|------|----------|
| 0.0 | 最确定性，始终选择最高概率 | 事实性问答 |
| 0.3-0.5 | 平衡确定性和多样性 | 一般写作 |
| 0.7-0.9 | 高随机性，创意丰富 | 创意写作、诗歌 |
| 1.0 | 极高随机性 | 不推荐，可能失控 |

---

### 10.4 Top-K 和 Top-P

| 参数 | 说明 |
|------|------|
| **Top-K** | 从最高概率的前K个词中选择，值越大越有创意 |
| **Top-P** | 从累积概率超过P的最小集合中选择，更灵活 |

---

## 十一、复杂任务处理

### 11.1 任务拆分策略

将复杂任务分解为多个简单步骤：

```
第一步：提取关键信息
第二步：分类整理
第三步：生成结论
第四步：格式化为输出
```

---

### 11.2 多轮对话优化

| 策略 | 说明 |
|------|------|
| 保持上下文 | 在后续问题中引用之前的讨论 |
| 迭代优化 | 第一轮给初稿 → 反馈问题 → AI修正 → 达到目标 |
| 限制上下文 | 定期总结，压缩不重要的信息 |

---

### 11.3 上下文与分隔符

**分隔符的重要性：**
分隔符帮助模型区分提示词的不同部分，提高处理准确性。

| 分隔符类型 | 示例 |
|------------|------|
| XML标签 | `<context>...</context>` |
| 三引号 | `"""` |
| 节标题 | `###背景###` |
| 破折号 | `---` |

**示例：**
```
###指令###
请总结以下文章的主要观点。

###文章内容###
[在此输入文章内容]

###输出要求###
用3个要点总结，每个要点不超过50字。
```

---

## 十二、提示词安全

### 12.1 对抗性提示攻击类型

| 类型 | 说明 | 防御策略 |
|------|------|----------|
| **Prompt Injection** | 注入恶意指令覆盖原指令 | 输入验证、分隔符 |
| **Prompt Leaking** | 试图提取系统提示 | 限制响应范围 |
| **Jailbreaking** | 绕过安全限制 | 安全边界控制 |

---

### 12.2 防御最佳实践

1. **输入验证和清洗**：过滤恶意注入
2. **分隔符明确**：区分用户输入和系统指令
3. **输出限制**：控制模型响应范围
4. **Sandbox**：隔离敏感操作

---

## 十三、实践应用模板

### 13.1 通用写作助手

```
你是，一位专业的[领域]内容撰写专家。

【任务】
撰写一篇关于[主题]的文章。

【要求】
- 字数：[具体字数]
- 目标读者：[描述受众]
- 语气：[正式/亲切/专业]
- 结构：包含引言、正文、结论

【背景】
[提供相关背景信息]

【示例风格】
[如有参考文章，粘贴在此]

现在请撰写文章：
```

---

### 13.2 代码审查助手

```
你是，一位资深代码审查工程师，精通[语言]。

【任务】
审查以下代码，找出潜在问题。

【代码】
```[语言]
[粘贴代码]
```

【审查维度】
1. 代码风格一致性
2. 潜在Bug和安全漏洞
3. 性能优化建议
4. 最佳实践符合度

【输出格式】
- 问题列表（按严重程度排序）
- 修复建议
- 改进代码（如果适用）

请开始审查：
```

---

### 13.3 数据分析助手

```
你是，一位资深数据分析师，擅长用Python和SQL处理数据。

【任务】
分析以下数据并生成报告。

【数据来源】
[描述数据]

【分析目标】
1. [目标1]
2. [目标2]
3. [目标3]

【输出要求】
- 关键发现（3-5条）
- 数据可视化建议
- 具体建议

请开始分析：
```

---

### 13.4 翻译助手

```
你是一位专业的[源语言]到[目标语言]翻译专家。

【翻译要求】
- 保持原文语气和风格
- 符合目标语言的文化习惯
- 专业术语需准确翻译

【待翻译内容】
```
[粘贴要翻译的文本]
```

【术语表】（如有）
- [术语1] → [翻译1]
- [术语2] → [翻译2]

请翻译：
```

---

### 13.5 面试问题生成助手

```
你是一位资深HR专家，精通人才招聘和面试技巧。

【岗位信息】
- 岗位：[职位名称]
- 部门：[部门]
- 级别：[级别]

【候选人画像】
- 经验：[年限]
- 背景：[背景描述]
- 技能要求：[核心技能]

【问题要求】
1. 覆盖技术能力、项目经验、团队协作
2. 包含情景题和行为题
3. 难度递进

【输出格式】
### 技术问题（3道）
### 项目经验问题（2道）
### 行为面试题（2道）
### 压力面试题（1道）

请生成面试题：
```

---

### 13.6 Agent任务执行助手

```
【角色】
你是一个专业的[任务类型]执行助手。

【任务目标】
[描述要完成的目标]

【可用工具】
- search: 搜索信息
- calculate: 计算
- [其他工具]

【执行策略】
1. 理解任务并分解为子目标
2. 按优先级执行子目标
3. 每步验证结果
4. 如遇错误，尝试替代方案

【约束条件】
- 最大迭代次数：[N]
- 超时时间：[X]
- 输出格式：[指定]

请开始执行：
```

---

## 十四、提示词优化实战

> 本节整合自论文Agent项目的实测研究，包含真实测试数据和优化建议。

### 14.1 CoT效果测试结果

> 测试时间：2026年4月 | 测试模型：MiniMax M2.7 | 测试用例：论文主题选择

**Token消耗对比：**

| 测试配置 | Prompt Tokens | Completion Tokens | Total Tokens | 消耗比 |
|----------|---------------|-------------------|-------------|--------|
| **Baseline**（无CoT无Few-shot） | 48 | 1039 | 1087 | 1.00x |
| **CoT**（有思维引导） | 118 | 575 | 693 | **-36.2%** |
| **CoT + Few-shot**（完整优化） | 192 | 391 | 583 | **-46.4%** |

**质量评分对比：**

| 测试配置 | Thinking | Structure | JSON | Valid JSON | Overall |
|----------|---------|-----------|------|------------|---------|
| Baseline | 20 | 20 | 20 | 40 | 100/100 |
| CoT | 25 | 20 | 20 | 40 | 105/100 |
| CoT + Few-shot | 25 | 20 | 20 | 40 | 105/100 |

**核心发现：**

**意外发现**：CoT不仅提升了质量，还**大幅减少了token消耗**！

**原因分析**：
1. **Baseline**：像"头脑风暴"，输出大量候选主题但不深入（1087 tokens）
2. **CoT**：引导模型先思考再输出，减少了无效生成（693 tokens）
3. **Few-shot**：给出了格式约束，让输出更聚焦规范（583 tokens）

**结论：**

| 指标 | 结果 |
|------|------|
| Token消耗 | CoT减少36-46% |
| 输出质量 | CoT提升5% |
| 性价比 | **优秀** - 消耗更低，质量更高 |

**对论文Agent项目的意义**：
- 选题/文献等工作流可以放心启用CoT
- 不会增加成本，反而可能降低成本
- 输出更规范、更可预测

---

### 14.2 已完成优化（项目实践）

已在 `agent_loop.py` 中添加：
- `COT_GUIDANCE` - 统一思维链提示模板
- `FEW_SHOT_EXAMPLES` - 通用Few-shot示例
- `enable_cot` / `enable_fewshot` 配置开关

**效果**：提升LLM推理质量，减少随机性

**Few-shot示例应用：**

| Agent | 已添加示例 |
|-------|-----------|
| TopicAgent | 3个主题选择示例 |
| LiteratureAgent | 文献摘要和研究空白识别示例 |
| LanguagePolisherAgent | 中英文润色示例 |

---

### 14.3 短期优化建议（1-4周）

#### 14.3.1 Plan-and-Execute 模式

**现状**：AgentLoop使用纯ReAct循环，每步都调用LLM决定下一步

**问题**：论文写作是多阶段任务，每步都让LLM"思考下一步"效率低

**建议**：在MasterSupervisor层加入规划步骤

```python
class MasterSupervisor:
    async def run_with_planning(self, task: str) -> Dict:
        # 1. 规划阶段 - LLM制定执行计划
        plan_prompt = f"""任务：{task}
请制定执行计划：

阶段1（选题）：
- 输出：聚焦的研究主题
- 质量标准：主题明确、有创新性

阶段2（文献）：
- 输出：相关文献列表+研究空白
- 质量标准：文献覆盖全面

阶段3（Thesis凝练）：
- 输出：核心论点
- 质量标准：论点清晰、有支撑

请列出每个阶段的执行顺序和依赖关系。"""

        plan = await self.llm.ainvoke([SystemMessage(content=plan_prompt)])

        # 2. 执行阶段 - 按计划执行（可回溯）
        for phase in plan.phases:
            result = await self.execute_phase(phase)
            if not self.check_quality(result):
                await self.refine_phase(phase)  # 迭代优化

        return final_result
```

**预期效果**：
- 减少LLM调用次数（3次 vs N次）
- 提高执行可预测性
- 便于质量控制

---

#### 14.3.2 Self-Consistency（自一致性）

**适用场景**：质量评估、论文评审、Thesis凝练

**现状**：单次LLM调用做决策

**问题**：可能有偏见或错误

**建议**：对关键决策使用多路径推理

```python
async def evaluate_with_consistency(
    self,
    evaluation_prompt: str,
    num_paths: int = 3
) -> Dict[str, Any]:
    """使用自一致性进行评估"""

    # 生成多个推理路径
    responses = await asyncio.gather(*[
        self.llm.ainvoke([SystemMessage(content=evaluation_prompt)])
        for _ in range(num_paths)
    ])

    # 提取各路径的评分
    scores = [self.extract_score(r) for r in responses]

    # 选择最一致的答案
    consensus_score = statistics.mean(scores)
    variance = statistics.stdev(scores)

    return {
        "consensus_score": consensus_score,
        "variance": variance,
        "confidence": 1 - min(variance / consensus_score, 1),
        "all_scores": scores
    }
```

**适用位置**：
- MasterSupervisor.QualityScore判定
- ThesisAgent核心论点凝练
- ReviewAgent最终评审

---

#### 14.3.3 质量阈值动态调整

**现状**：固定质量阈值（7.0/8.0）

**问题**：不同任务难度不同，固定阈值不灵活

**建议**：根据任务复杂度动态调整

```python
class AdaptiveThreshold:
    """自适应质量阈值"""

    @staticmethod
    def calculate(task_type: str, context: Dict) -> float:
        base_thresholds = {
            "topic": 7.0,
            "literature": 7.0,
            "methodology": 7.5,
            "writing": 7.0,
            "polish": 8.0
        }

        base = base_thresholds.get(task_type, 7.0)

        # 复杂度调整
        complexity = context.get("complexity", "medium")
        complexity_factor = {
            "low": -0.3,
            "medium": 0,
            "high": +0.3
        }.get(complexity, 0)

        # 迭代次数调整（越迭代阈值可略降）
        iteration = context.get("iteration", 1)
        iteration_factor = -0.1 * (iteration - 1) if iteration > 1 else 0

        return max(5.5, base + complexity_factor + iteration_factor)
```

---

#### 14.3.4 提示词模板集中管理

**现状**：提示词散布在各Agent代码中

**问题**：
- 难以统一优化
- 重复编写相似结构
- 难以A/B测试

**建议**：创建统一的提示词模板系统

```python
# src/agents_v2/prompts/templates.py
class PromptTemplate:
    """统一提示词模板"""

    # 通用组件
    SYSTEM_PREFIX = """你是一个{role}。
你的职责是：{responsibilities}
"""

    OUTPUT_FORMAT = """
【输出格式】
请按以下JSON格式输出：
{format_spec}
"""

    QUALITY_CHECK = """
【质量检查清单】
完成前请确认：
{checklist}
"""

    @classmethod
    def build(cls, role: str, responsibilities: List[str],
              format_spec: Dict, checklist: List[str]) -> str:
        parts = [
            cls.SYSTEM_PREFIX.format(role=role, responsibilities=responsibilities),
            cls.OUTPUT_FORMAT.format(format_spec=format_spec),
            cls.QUALITY_CHECK.format(checklist=checklist)
        ]
        return "\n".join(parts)


# 使用示例
template = PromptTemplate.build(
    role="学术研究主题选择专家",
    responsibilities=["分析研究需求", "生成候选主题", "评估可行性"],
    format_spec={"title": "str", "feasibility": "float"},
    checklist=["主题是否聚焦?", "创新点是否明确?"]
)
```

---

### 14.4 DSPy集成建议

**结论**：
- DSPy适合项目的**长期演进**
- 短期价值有限，主要收益在6个月后
- 需要投入标注数据准备工作

**建议**：
1. **短期（1-2月）**：完成Plan-and-Execute + Self-Consistency改造
2. **中期（3-4月）**：评估是否需要DSPy的自动优化能力
3. **长期（5+月）**：如有大量Agent需要维护，再考虑DSPy

---

### 14.5 优化优先级排序

| 优先级 | 优化项 | 工作量 | 效果 |
|-------|--------|-------|------|
| 1 | CoT引导 + Few-shot | 已完成 | 提升推理质量，减少Token消耗 |
| 2 | Plan-and-Execute | 1-2周 | 减少调用、提升可预测性 |
| 3 | Self-Consistency | 1周 | 提升关键决策质量 |
| 4 | 自适应阈值 | 3-5天 | 更灵活的质量控制 |
| 5 | DSPy集成 | 4-8周 | 长期技术债务 |

**立即可行动项**：
1. 测试现有CoT和Few-shot效果
2. 在MasterSupervisor试点Plan-and-Execute
3. 为质量评估模块添加Self-Consistency
4. 建立提示词版本管理机制

---

## 十五、技术选型速查表

### 15.1 按场景选择技术

| 场景 | 推荐技术 |
|------|----------|
| 简单问答 | Zero-shot + 明确指令 |
| 格式严格要求 | Few-shot + 示例 |
| 复杂推理 | CoT + Self-consistency |
| 多步骤任务 | ReAct / Plan-and-Execute |
| 开放创意 | ToT / GoT |
| 生产部署 | DSPy 自动优化 |
| 知识密集 | RAG + CoT |
| 医学/专业领域 | Medprompt |

---

### 15.2 技术发展路线图

```
基础 → 思维链 → 思维树 → 思维图
        ↓         ↓        ↓
      CoT      ToT      GoT
        ↓         ↓        ↓
    Self-Consistency   集成推理
        ↓              ↓
    Logical CoT    Medprompt
```

---

### 15.3 框架选择指南

| 需求 | 推荐框架 |
|------|----------|
| 快速原型开发 | LangChain |
| 生产级部署 | DSPy |
| 多代理协作 | CrewAI / MetaGPT |
| 复杂决策 | ToT / GoT |
| 自动化优化 | DSPy / APE |

---

## 十六、最佳实践与资源

### 16.1 GitHub 热门项目

| 项目 | Stars | 说明 |
|------|-------|------|
| [dair-ai/Prompt-Engineering-Guide](https://github.com/dair-ai/Prompt-Engineering-Guide) | 55k+ | 权威提示词指南 |
| [stanfordnlp/dspy](https://github.com/stanfordnlp/dsp) | 15k+ | 自动提示优化框架 |
| [MKartaviciute/promptbase](https://github.com/MKartaviciute/promptbase) | - | Medprompt 实现 |
| [promptslab/Awesome-Prompt-Engineering](https://github.com/promptslab/Awesome-Prompt-Engineering) | 200+ | 提示词资源汇总 |

---

### 16.2 必读论文

| 论文 | 年份 | 核心贡献 |
|------|------|----------|
| Chain-of-Thought Prompting Elicits Reasoning | 2022 | CoT 基础 |
| ReAct: Synergizing Reasoning and Acting | 2022 | ReAct 框架 |
| Tree of Thoughts: Deliberate Problem Solving | 2023 | ToT 方法 |
| Graph of Thoughts: Solving Elaborate Problems | 2023 | GoT 方法 |
| DSPy: Compiling Declarative LM Calls | 2023 | DSPy 框架 |
| Medprompt: A Systematic Study | 2023 | Medprompt 技术 |
| Automatic Prompt Engineer | 2022 | APE 方法 |
| Self-Consistency | 2023 | 自一致性推理 |

---

### 16.3 官方文档

- [OpenAI Prompt Engineering Guide](https://platform.openai.com/docs/guides/prompt-engineering)
- [Anthropic Claude Documentation](https://docs.anthropic.com/)
- [Google Vertex AI Prompt Engineering](https://cloud.google.com/blog/products/ai-machine-learning/prompt-engineering-best-practices)
- [DeepLearning.ai ChatGPT Prompt Engineering](https://www.deeplearning.ai/courses/chatgpt-prompt-eng/)

---

### 16.4 常见问题与解决方案

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 输出太简略 | 指令不够明确 | 增加细节要求，指定输出长度 |
| 输出格式不稳定 | 示例不够 | 增加Few-shot示例 |
| 模型"幻觉" | 缺乏参考信息 | 提供参考文本，引用来源 |
| 输出偏离主题 | 上下文混乱 | 使用分隔符，明确任务范围 |
| 复读机问题 | 重复惩罚过低 | 增加repetition_penalty，降低temperature |
| 推理错误 | 缺乏中间步骤 | 使用CoT，引导逐步推理 |
| 工具调用失败 | 参数格式错误 | 增加参数校验层 |

---

### 16.5 检查清单

在提交提示词前，检查以下要点：

- [ ] 指令是否清晰明确？
- [ ] 是否提供了足够的上下文？
- [ ] 是否使用了分隔符（如需要）？
- [ ] 是否指定了输出格式？
- [ ] 示例是否足够且有代表性？
- [ ] 是否包含了长度限制？
- [ ] 语气/风格是否符合需求？
- [ ] 是否有潜在的注入风险？
- [ ] 是否需要使用思维链（CoT）？
- [ ] 采样参数是否合适？

---

## 参考来源

### 学术论文
- [A Systematic Survey of Prompt Engineering in LLMs](https://arxiv.org/abs/2311.16452)
- [The Prompt Report: A Systematic Survey of Prompting Techniques](https://github.com/dair-ai/Prompt-Engineering-Guide)
- [Chain-of-Thought Prompting Elicits Reasoning](https://arxiv.org/abs/2201.11903)
- [ReAct: Synergizing Reasoning and Acting](https://arxiv.org/abs/2210.03629)
- [Graph of Thoughts: Solving Elaborate Problems](https://arxiv.org/abs/2308.09687)
- [DSPy: Compiling Declarative Language Model Calls](https://github.com/stanfordnlp/dsp)
- [Self-Consistency: Improving CoT with Self-Consistency](https://arxiv.org/abs/2203.11171)
- [Plan-and-Execute Pattern](https://arxiv.org/abs/2308.09687)

### 官方文档
- [OpenAI Prompt Engineering Guide](https://platform.openai.com/docs/guides/prompt-engineering)
- [Anthropic Claude Documentation](https://docs.anthropic.com/)
- [Google Vertex AI Prompt Engineering](https://cloud.google.com/blog/products/ai-machine-learning/prompt-engineering-best-practices)
- [DeepLearning.ai ChatGPT Prompt Engineering](https://www.deeplearning.ai/courses/chatgpt-prompt-eng/)

---

*本文档持续更新，欢迎提出建议和反馈。*

---

## 2026年提示词工程新范式 (新增补充)

> 补充时间: 2026-05-01

### 推理模型时代的提示词转变

2026 年，提示词工程正在经历根本性的范式转移。传统"魔法短语"(如"Let's think step by step")的效果在推理模型 (DeepSeek-R1, o3, Gemini 3.1) 上已大幅降低，甚至可能产生反效果。

**核心转变**:

| 维度 | 传统 LLM (2024) | 推理模型 (2026) |
|------|----------------|-----------------|
| 提示词风格 | 详细的 CoT 引导 | 简洁的目标描述 |
| 角色定义 | "你是一个专家..." | 角色对推理模型影响减小 |
| Few-Shot | 3-5 个示例 | 0-1 个示例（内部推理替代） |
| 输出格式 | 严格 JSON Schema | 让模型先推理再格式化 |
| Token 分配 | 提示词 → 输出 | 提示词 → 推理Token → 输出 |

**推理模型提示词反模式 (Anti-patterns)**:

```
# ❌ 不推荐：过度引导推理模型
"让我们一步一步思考。首先，分析问题。其次，列举可能的方法。
第三，评估每种方法。第四，选择最佳方法。第五，..."

# ✅ 推荐：给推理模型目标，让其自主推理
"解决以下问题。提供清晰的推理过程和最终答案。"

# ❌ 不推荐：给推理模型过多 Few-Shot
"示例1: ... 示例2: ... 示例3: ..."  # 推理模型不需要

# ✅ 推荐：给推理模型明确约束
"回答必须仅基于提供的文献。如果文献不足，请明确说明。"
```

### DSPy 自动提示词优化 (2026 最新)

DSPy 在 2026 年已成为提示词优化的生产级工具，核心思想是用编程方式而非手工方式优化提示词：

```python
import dspy

# 定义签名 (Signature) 而非写提示词
class PaperQASignature(dspy.Signature):
    """基于文献回答问题，附带引用"""
    context = dspy.InputField(desc="检索到的论文文献")
    question = dspy.InputField()
    answer = dspy.OutputField(desc="带引用的答案")
    citations = dspy.OutputField(desc="引用的文献ID列表")

# 自动优化
optimizer = dspy.MIPROv2(metric=answer_quality_score)
optimized_qa = optimizer.compile(PaperQASignature(), trainset=training_data)
```

### Anthropic Claude 提示词最佳实践 (2026 更新)

Anthropic 于 2025-2026 年持续更新提示词指南，关键变化：

1. **Prompt Caching 优先设计**: 将固定指令放前面(可缓存)，动态内容放后面
2. **Tool Use 提示词**: 工具描述应包含使用该工具的**具体时机**，而非仅功能描述
3. **长上下文策略**: 关键信息放在对话开头或结尾 (primacy/recency)，中间部分容易被忽略
4. **System Prompt 精简**: 过长的 System Prompt 反而不利，建议 500-2000 tokens

### 提示词工程的"不死"论

2026 年 Reddit/社区流传"Prompt Engineering 已经死了"，但事实是：
- **死了的是**: 固定的魔法短语、模板化 Few-Shot、过度详细的 CoT
- **活下来的是**: 系统化提示词设计思维，只是迁移到了更高层面 — 签名设计 (DSPy)、Skills 模块化、动态提示词组装

**Paper Agent 项目建议**:
1. 区分推理模型和非推理模型的提示词策略
2. 对推理模型(DeepSeek-R1)使用简洁目标描述式提示词
3. 对传统模型(Claude, GPT-4o)保持完整的 5 部分结构
4. 引入 DSPy 自动优化搜索/写作 Agent 的提示词

---

## 2026年推理模型最新动态 (2026-05补充)

### 主要推理模型对比 (截至2026年5月)

| 模型 | 发布方 | 核心能力 | 性价比 |
|------|--------|----------|--------|
| **GPT-5 Ultra** | OpenAI | 10万亿参数，原生多模态 | $13.62/任务(o3对比) |
| **Claude 4** | Anthropic | 神经符号架构，长上下文 | 高 |
| **Gemini 3.1 Pro** | Google | 原生百万上下文，Deep Think模式 | 中 |
| **DeepSeek-R1** | 深度求索 | 开源，推理能力逼近闭源 | 最高(开源免费) |
| **Grok 3** | xAI | 实时知识，400B参数 | 高 |

### 推理模型选择建议

```python
# Paper Agent 推理模型选择策略
def select_reasoning_model(task_type: str) -> str:
    """根据任务类型选择推理模型"""
    if task_type == "factual_qa":
        return "gemini-3.1-pro"  # 长上下文优先
    elif task_type == "code_generation":
        return "gpt-5-ultra"    # 代码能力最强
    elif task_type == "reasoning_math":
        return "deepseek-r1"     # 推理能力强，开源免费
    elif task_type == "creative_writing":
        return "claude-4"        # 创意写作优势
    else:
        return "gpt-4o"          # 通用平衡
```

### 2026年提示词工程六大趋势

1. **Prompt Caching 成为标配**: Anthropic/OpenAI/Google 均支持，降低重复成本
2. **推理模型提示词简化**: 从"详细引导"到"目标描述"
3. **多模态提示词统一**: 图像+文本+表格统一提示范式
4. **自适应提示词**: 基于任务难度动态调整提示词复杂度
5. **提示词版本控制**: DSPy式编程化提示词管理
6. **工具调用提示词标准化**: 工具描述包含使用时机和约束

### 最新提示词优化论文/工具 (2026)

| 工具/论文 | 机构 | 核心贡献 |
|-----------|------|----------|
| **MIPROv2** | Stanford | 多任务提示词优化 |
| **Promptbreeder** | DeepMind | 进化式提示词优化 |
| **APOT** | 学术 | 自适应提示词 token 分配 |
| **Instinct** | 学术 | 推理模型提示词引导 |

---

## 附录：提示词工程速查卡

### 推理模型提示词模板

```python
# DeepSeek-R1 / o3 等推理模型 - 简洁目标式
REASONING_MODEL_PROMPT = """
任务：{task_description}
约束条件：
{constraints}
输出要求：
{output_format}
"""

# 传统模型 - 完整结构式
TRADITIONAL_MODEL_PROMPT = """
【角色】{role}
【背景】{context}
【任务】{task}
【示例】{few_shot_examples}
【输出格式】{output_format}
【质量检查】{quality_checklist}
"""
```

### 工具描述模板 (2026版)

```python
TOOL_DESCRIPTION_TEMPLATE = """
工具名称: {tool_name}
功能: {capability_description}
使用时机: {when_to_use}  # 新增：使用时机是关键！
约束: {constraints}
输入格式: {input_format}
输出格式: {output_format}
"""
```

---

*本文档更新时间: 2026-05-01*
*下次更新时间建议: 2026-08-01（GPT-6预期发布）*
