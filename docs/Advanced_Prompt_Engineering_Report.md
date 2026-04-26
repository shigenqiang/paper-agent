# 先进提示词工程技术调研报告

> 调研时间：2026年4月 | 信息来源：GitHub、arXiv、OpenAI、Anthropic、Google 官方文档

---

## 一、概述

提示词工程（Prompt Engineering）是引导大语言模型（LLM）生成高质量输出的关键技术。本报告系统调研了当前最先进的提示词技术，涵盖框架、Agent应用、学术研究等多个维度。

**核心技术分类：**

| 类别 | 技术 |
|------|------|
| 基于样本提示 | Zero-shot、Few-shot、Medprompt |
| 思维链技术 | CoT、Auto-CoT、CoT-SC、Logical CoT |
| 思维演化 | ToT、GoT、AoT |
| 自动优化 | APE、Auto-Prompt、DSPy |
| Agent框架 | ReAct、Plan-and-Execute、MetaGPT、CrewAI |
| 多模态 | Multimodal CoT、Visual CoT |

---

## 二、基础提示范式

### 2.1 Zero-Shot Prompting

无需提供任何示例，直接使用模型先验知识完成任务。

**适用场景：** 简单、直接的任务

**最佳实践（OpenAI官方）：**
- 将指令放在提示开头
- 使用分隔符（如 `###`、`"""`）分隔指令和上下文
- 明确具体地描述期望的背景、结果、长度、格式、风格
- 指定输出格式时提供示例

---

### 2.2 Few-Shot Prompting

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

---

### 2.3 Medprompt 技术

Medprompt 是由 Google 提出的一组先进提示技术组合，在医学问答（MMLU）上达到90.10%的准确率，超越 GPT-4。

**核心组件：**

1. **Chain-of-Thought with Self-Consistency**：结合思维链和自一致性
2. **Selection-inference prompting**：选择-推理提示
3. **Ensemble reasoning**：集成推理

**扩展应用：**
Google 团队将 Medprompt+ 扩展到非医疗领域，在 GSM8K、MATH、HumanEval 等基准上也取得了显著提升。

---

## 三、思维链（Chain-of-Thought）技术

### 3.1 标准 CoT

通过在提示中提供中间推理步骤，引导模型逐步思考。

**核心方法：**
- 在提示中加入 "Let's think step by step"
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

### 3.4 Logical CoT

在标准 CoT 基础上增加逻辑验证步骤：

1. **假设生成**：提出多个可能的解决方案
2. **逻辑验证**：检验每个假设的有效性
3. **一致性检查**：确保推理过程自洽

---

### 3.5 程序辅助语言模型（PAL）

使用 LLM 生成程序作为中间推理步骤，而非自由形式文本。

**与 CoT 的区别：**
- 将解决步骤卸载到编程运行时（如 Python 解释器）
- 适合需要日期理解、数学计算等任务

**示例：**
```python
# 提示模型生成 Python 代码解决日期问题
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

### 4.1 Tree of Thoughts (ToT)

将问题解决过程建模为树结构，允许模型探索多条推理路径。

**流程：**
1. **生成**：为每个节点生成多个候选思维
2. **评估**：评估每个思维的价值
3. **扩展**：选择最有希望的节点继续扩展
4. **搜索**：使用 BFS/DFS 进行搜索

**适用场景：**
- 需要探索多种可能性的复杂决策
- 创意写作、战略规划

---

### 4.2 Graph of Thoughts (GoT)

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

### 4.3 Algorithm of Thoughts (AoT)

使用算法思维引导推理，结合搜索算法的思想。

**特点：**
- 将确定性算法思想引入提示
- 减少推理的随机性
- 提高可解释性

---

## 五、自动提示优化技术

### 5.1 Automatic Prompt Engineer (APE)

让模型自己生成和优化提示。

**方法：**
1. **Forward Generation Template**：生成候选 prompt
2. **Reverse Generation Template**：反向生成 prompt
3. **评估**：基于训练数据评估候选 prompt 质量

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

**GitHub：** stanfordnlp/dspy（4,400+ stars）

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

---

### 6.3 MetaGPT

多代理协作框架，支持代理间的复杂交互。

**特点：**
- 丰富的预定义代理库
- 支持标准操作程序（SOP）
- 严重依赖 asyncio

---

### 6.4 CrewAI

多代理协作框架，强调角色定义和任务分配。

**核心概念：**
- **Agent**：具有特定角色的代理
- **Task**：需要完成的任务
- **Crew**：代理团队

---

### 6.5 LangChain Agent

LangChain 提供的 Agent 开发框架。

**核心组件：**
```python
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain_community.tools import DuckDuckGoSearchRun

llm = ChatOpenAI(temperature=0)
tools = [DuckDuckGoSearchRun()]

agent = create_agent(llm, tools, system_prompt="""...""")

result = agent.invoke({"messages": [{"role": "user", "content": "..."}]})
```

---

### 6.6 决策模型对比

| 框架 | 特点 | 适用场景 |
|------|------|----------|
| **ReAct** | 边推理边执行 | 开放域问答、搜索 |
| **Plan-and-Execute** | 先规划后执行 | 复杂多步任务 |
| **LLMCompiler** | 并行执行，生成DAG | 工具调用密集型 |
| **BabyAGI** | 目标分解+反思 | 自主任务完成 |

---

## 七、高级 RAG 提示技术

### 7.1 预检索优化

| 技术 | 说明 |
|------|------|
| **hyde** | 生成假设性文档改善检索 |
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

## 八、提示词安全

### 8.1 对抗性提示（Adversarial Prompting）

**攻击类型：**

| 类型 | 说明 | 防御策略 |
|------|------|----------|
| **Prompt Injection** | 注入恶意指令覆盖原指令 | 输入验证、分隔符 |
| **Prompt Leaking** | 试图提取系统提示 | 限制响应范围 |
| **Jailbreaking** | 绕过安全限制 | 安全边界控制 |

---

### 8.2 防御最佳实践

1. **输入验证和清洗**：过滤恶意注入
2. **分隔符明确**：区分用户输入和系统指令
3. **输出限制**：控制模型响应范围
4. **Sandbox**：隔离敏感操作

---

## 九、框架与模板

### 9.1 CRISPE 框架

| 组成部分 | 说明 |
|----------|------|
| **C - Capacity and Role** | 能力与角色 |
| **I - Insight** | 洞察/背景 |
| **S - Statement** | 陈述/任务 |
| **P - Personality** | 个性/风格 |
| **E - Experiment** | 实验/尝试 |

---

### 9.2 BROKE 框架

融合 OKR 方法论：

| 组成部分 | 说明 |
|----------|------|
| **B - Background** | 背景 |
| **R - Role** | 角色 |
| **O - Objectives** | 目标 |
| **K - Key Results** | 关键结果 |
| **E - Evolve** | 演变/优化 |

---

### 9.3 T.C.R.E.I 框架（Google）

| 组成部分 | 说明 |
|----------|------|
| **T - Task** | 任务定义 |
| **C - Context** | 上下文 |
| **R - References** | 参考资料 |
| **E - Evaluate** | 评估 |
| **I - Iterate** | 迭代 |

---

### 9.4 COAST 框架

| 组成部分 | 说明 |
|----------|------|
| **C - Context** | 背景 |
| **O - Objective** | 目标 |
| **A - Action** | 行动 |
| **S - Style** | 风格 |
| **T - Tone** | 语气 |

---

## 十、最佳实践与资源

### 10.1 GitHub 热门项目

| 项目 | Stars | 说明 |
|------|-------|------|
| [dair-ai/Prompt-Engineering-Guide](https://github.com/dair-ai/Prompt-Engineering-Guide) | 55k+ | 权威提示词指南 |
| [stanfordnlp/dspy](https://github.com/stanfordnlp/dsp) | 15k+ | 自动提示优化框架 |
| [MKartaviciute/promptbase](https://github.com/MKartaviciute/promptbase) | - | Medprompt 实现 |
| [promptslab/Awesome-Prompt-Engineering](https://github.com/promptslab/Awesome-Prompt-Engineering) | 200+ | 提示词资源汇总 |

---

### 10.2 必读论文

| 论文 | 年份 | 核心贡献 |
|------|------|----------|
| Chain-of-Thought Prompting Elicits Reasoning | 2022 | CoT 基础 |
| ReAct: Synergizing Reasoning and Acting | 2022 | ReAct 框架 |
| Tree of Thoughts: Deliberate Problem Solving | 2023 | ToT 方法 |
| Graph of Thoughts: Solving Elaborate Problems | 2023 | GoT 方法 |
| DSPy: Compiling Declarative LM Calls | 2023 | DSPy 框架 |
| Medprompt: A Systematic Study | 2023 | Medprompt 技术 |
| Automatic Prompt Engineer | 2022 | APE 方法 |

---

### 10.3 官方文档

- [OpenAI Prompt Engineering Guide](https://platform.openai.com/docs/guides/prompt-engineering)
- [Anthropic Claude Documentation](https://docs.anthropic.com/)
- [Google Vertex AI Prompt Engineering](https://cloud.google.com/blog/products/ai-machine-learning/prompt-engineering-best-practices)
- [DeepLearning.ai ChatGPT Prompt Engineering](https://www.deeplearning.ai/courses/chatgpt-prompt-eng/)

---

## 十一、结论与建议

### 11.1 技术选型建议

| 场景 | 推荐技术 |
|------|----------|
| 简单问答 | Zero-shot + 明确指令 |
| 复杂推理 | CoT + Self-consistency |
| 多步骤任务 | ReAct / Plan-and-Execute |
| 开放创意 | ToT / GoT |
| 生产部署 | DSPy 自动优化 |
| 知识密集 | RAG + CoT |

### 11.2 未来趋势

1. **自动化**：DSPy 等框架将提示工程从手工转向自动化
2. **多模态**：Multimodal CoT 将成为重要方向
3. **安全**：对抗性提示和防护技术将持续演进
4. **组合**：多种技术的组合使用（如 Medprompt+）

### 11.3 实践建议

1. **从简单开始**：先用 Zero-shot 验证，再逐步增加复杂度
2. **使用框架**：选择合适的框架（如 LangChain、DSPy）
3. **持续优化**：通过 A/B 测试和用户反馈迭代
4. **关注安全**：始终考虑提示词注入风险

---

## 参考来源

- [A Systematic Survey of Prompt Engineering in LLMs](https://arxiv.org/abs/2311.16452)
- [The Prompt Report: A Systematic Survey of Prompting Techniques](https://github.com/dair-ai/Prompt-Engineering-Guide)
- [DSPy: Compiling Declarative Language Model Calls](https://github.com/stanfordnlp/dsp)
- [Graph of Thoughts: Solving Elaborate Problems](https://arxiv.org/abs/2308.09687)
- [Medprompt: A Systematic Study](https://github.com/MKartaviciute/promptbase)
- [ReAct: Synergizing Reasoning and Acting](https://arxiv.org/abs/2210.03629)