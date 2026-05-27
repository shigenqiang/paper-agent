# 学术AI Agent主流技术调研报告（2025-2026）

> 最后更新：2026年5月20日

---

## 更新日志

| 时间 | 更新内容 |
|------|---------|
| 2026-05-20 | 添加2026年最新学术Agent进展：Vibe Coding时代的科研Agent、HERMES系统等 |

---

## 1. 核心概念与定义

**AI Agent（人工智能代理）** 是能够自主感知环境、进行推理规划、调用工具并执行复杂任务的智能系统。与传统LLM的被动问答不同，Agent具备"自主行动"能力，可完成多步骤复杂任务。

**学术Agent** 指专门服务于科研场景的AI Agent，涵盖文献检索、实验设计、论文撰写、数据分析等学术全流程。

**核心架构范式**：
- **ReAct (Reasoning + Acting)**: 将推理与行动交错进行，让LLM边想边做
- **CoT (Chain-of-Thought)**: 链式推理，逐步分解复杂问题
- **ToT (Tree-of-Thoughts)**: 分支式推理，支持多路径探索与回溯

---

## 2. 主流学术Agent系统深度解析

### 2.1 Agent Laboratory（AMD + 约翰·霍普金斯大学）

**定位**: 全流程自动化科研框架，专注于论文撰写全链路

**GitHub**: https://github.com/AgentLaboratory/Agent-Laboratory
**论文**: arXiv:2501.04227

**核心能力**:
- 输入：一个概念想法
- 输出：自动检索arXiv文献 → 完成实验设计 → 生成代码 → 输出实验报告
- 相比传统研究方法节省**84%的研究费用**

**架构设计**:
- **PhDStudent Agent**: 文献综述阶段，通过arXiv API检索相关论文，执行摘要提取和文献整合
- **MLEngineer Agent**: 实验设计阶段，利用自动化工具执行代码生成和实验优化
- **Professor Agent**: 论文撰写阶段，将研究成果整合为符合学术标准的报告

### 2.2 PaSa（字节跳动研究团队）

**定位**: 学术论文检索智能体，专注于文献调研

**GitHub**: https://github.com/bytedance/pasa
**演示网站**: https://pasa-agent.ai

**核心能力**:
- 只需输入学术问题，2分钟内完成详尽的文献调研
- 自动调用搜索引擎，浏览论文，追踪引文网络
- 在Paper Banana基准测试中**远超Google、Betterinus等主流工具**

**技术亮点**: 基于强化学习训练的paper search agent，能够自主做出决策调用工具

### 2.3 AI Scientist（SakanaAI）

**定位**: 全自动化开放性科学发现系统

**GitHub**: https://github.com/SakanaAI/AI-Scientist
**Stars**: 10k+

**核心能力**:
- 端到端自动化科学研究：从idea生成、实验设计、代码实现到论文撰写
- AI生成的论文已通过ICLR同行评审（被接收后主动撤回）

**AI Scientist-v2** (最新版本):
- Workshop-Level Automated Scientific Discovery via Agentic Tree Search
- 采用Agentic Tree Search进行自动化科研发现

---

## 3. 计算机控制Agent（GUI Agent）

### 3.1 Claude Computer Use (Anthropic)

**技术原理**:
- 基于Claude 3.5 Sonnet升级版，支持鼠标光标控制、点击按钮、键盘输入
- 在OSWorld测试中得分**14.9%**（AI模型中首位，第二名仅7.8%）
- 支持macOS桌面控制，集成到Claude Code CLI

**能力表现**:
- 合理规划多步骤任务
- 协调不同应用程序之间的操作
- 持续评估进度并调整策略

### 3.2 OpenAI Operator (CUA模型)

**定位**: 通用浏览器自动化Agent

**核心技术**:
- CUA (Computer-Using Agent) 模型，结合GPT-4o视觉能力与强化学习
- 通过屏幕截图"看到"内容，用鼠标键盘执行操作

**功能**:
- 预订机票、餐厅、在线购物
- 填写表单、生成表情包
- 2025年5月升级到o3模型，推理能力大幅提升

---

## 4. 多智能体协作框架

### 4.1 AutoGen（微软）

**GitHub**: https://github.com/microsoft/autogen

**特点**:
- 双智能体架构：User Agent + Assistant Agent
- 卓越的多智能体协调能力，尤其在编程任务
- 支持人工干预通道，适合复杂系统开发
- 2025年1月发布AutoGen 0.4，完全重写以支持企业级部署

**AutoGen Studio**: 低代码多智能体应用构建平台

### 4.2 CrewAI

**特点**:
- 角色驱动的协作式框架
- 操作简便，适合快速原型开发
- Agent间共享内存和消息传递

**适用场景**: 快速演示、竞品分析等轻量级协作任务

### 4.3 LangGraph（LangChain）

**特点**:
- 图状架构，支持循环流
- 内置内存，深度定制能力强
- 适合复杂的多智能体工作流编排

---

## 5. Agent通信协议生态

### 5.1 MCP (Model Context Protocol)

**主导方**: Anthropic
**定位**: AI模型与外部工具、数据源的标准化连接

**类比**: "AI应用的USB-C接口"
**官网**: https://modelcontextprotocol.io

### 5.2 A2A (Agent-to-Agent Protocol)

**主导方**: Google
**发布时间**: 2025年4月Google Cloud Next大会

**核心能力**:
- 跨框架、跨供应商的AI Agent互操作
- 得到Salesforce、SAP、ServiceNow、MongoDB等50+合作伙伴支持
- 定义了任务发送、状态跟踪、结果获取等标准化接口

### 5.3 Skills Protocol

**主导方**: Anthropic
**发布时间**: 2025年12月

**定位**: Agent技能标准化开放标准
**官网**: https://agentskills.io

---

## 6. 开放世界Agent研究

### 6.1 Voyager (DeepMind + 李飞飞)

**GitHub**: https://github.com/MineDojo/Voyager
**论文**: arXiv:2305.16291

**定位**: Minecraft开放世界中的终身学习Agent

**核心创新**:
- 首次由LLM驱动，在无人工干预的情况下终身学习新技能
- 提出"Skill Library"机制，累积可重用技能
- 使用GPT-4作为认知引擎，结合Mineflayer API

### 6.2 SIMI (Scalable Instructable Multiworld Agent)

**发布方**: DeepMind
**发布时间**: 2024年3月

**定位**: 首个能在广泛3D虚拟环境和视频游戏中遵循自然语言指令的通用AI智能体

---

## 7. 主流框架对比

| 框架 | 主导方 | 定位 | 核心优势 | 适用场景 |
|------|--------|------|----------|----------|
| AutoGen | 微软 | 多智能体对话系统 | 代码生成、调试、人工干预通道 | 复杂软件开发 |
| CrewAI | - | 角色驱动协作框架 | 易用性、快速搭建 | 原型开发、演示 |
| LangGraph | LangChain | 图状工作流编排 | 灵活性、深度定制 | 复杂业务流程 |
| Swarm | OpenAI | 多智能体编排 | 轻量级、易上手 | 实验性项目 |

---

## 8. 技术发展趋势（2025-2026）

1. **Computer Use能力爆发**: Claude Computer Use和OpenAI Operator推动GUI Agent成为热点
2. **协议标准化**: MCP、A2A、Skills三大协议形成Agent互联互通生态
3. **科研Agent爆发**: Agent Laboratory、AI Scientist等实现论文撰写全流程自动化
4. **多智能体协作深化**: 从单Agent向Multi-Agent系统演进
5. **企业级部署**: AutoGen 0.4等框架开始面向生产环境优化

---

## 9. 参考资源

### GitHub仓库
- Agent Laboratory: https://github.com/AgentLaboratory/Auto-Laboratory
- PaSa: https://github.com/bytedance/pasa
- AI Scientist: https://github.com/SakanaAI/AI-Scientist
- Voyager: https://github.com/MineDojo/Voyager
- AutoGen: https://github.com/microsoft/autogen

### 论文
- Agent Laboratory: arXiv:2501.04227
- Voyager: arXiv:2305.16291
- ReAct: (姚顺雨等)

### 技术标准
- MCP: https://modelcontextprotocol.io
- A2A: https://google.github.io/A2A
- Skills: https://agentskills.io

---

**总结**: 当前学术Agent的主流方向集中在科研全流程自动化（文献检索→实验→论文撰写）、计算机控制Agent（GUI自动化）、多智能体协作框架三大领域。微软AutoGen、Anthropic Claude、OpenAI Operator、Google A2A等形成完整的Agent技术生态。