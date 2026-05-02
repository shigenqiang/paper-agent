# Paper Agent 各模块开发计划

> 规划日期：2026-05-02
> 版本：v1.0
> 基于：未来框架设计 v2.1 + 调研报告 + 已实现架构

---

## 模块总览

| 序号 | 模块 | 优先级 | 状态 | 开发周期 |
|------|------|--------|------|----------|
| 1 | MCP/A2A/Agent Skills 协议集成 | P0 | 待开始 | 2-3周 |
| 2 | 记忆系统 v4.0 升级 | P0 | 待开始 | 3-4周 |
| 3 | 意图路由三级级联升级 | P1 | 待开始 | 2-3周 |
| 4 | Evaluator/Harness 质量保障体系 | P1 | 部分实现 | 3-4周 |
| 5 | PDF 解析系统升级 | P1 | 待开始 | 2-3周 |
| 6 | 可观测性架构升级 | P2 | 待开始 | 2-3周 |
| 7 | 前端 AG-UI 集成 | P2 | 待开始 | 2-3周 |
| 8 | Skill 体系重构 | P2 | 待开始 | 2-3周 |

---

## 模块1：MCP/A2A/Agent Skills 协议集成

### 1.1 背景与目标

**现状**：
- Agent 直接调用工具，缺乏标准化协议层
- 工具调用分散在各 Agent 内部

**目标**：
- 接入 MCP 协议（Agent ↔ 工具/数据源）
- 接入 A2A 协议（Agent ↔ Agent）
- 重构 Skill 体系（Agent Skills 标准）

### 1.2 MCP 协议集成计划

#### Phase 1：MCP Server 标准化（1周）

**目标**：将学术搜索封装为标准 MCP Server

**任务清单**：

| 任务 | 说明 | 文件 |
|------|------|------|
| MCP Server 基础框架 | 使用 mcp[Python] SDK 创建服务 | `src/agents_v2/mcp/` |
| ArXiv MCP Server | 实现 arXiv 搜索 MCP 工具 | `src/agents_v2/mcp/arxiv_server.py` |
| PubMed MCP Server | 实现 PubMed 搜索 MCP 工具 | `src/agents_v2/mcp/pubmed_server.py` |
| Semantic Scholar MCP Server | 实现 SS 搜索 MCP 工具 | `src/agents_v2/mcp/semantic_scholar_server.py` |
| MCP 客户端集成 | 在 Agent 中通过 MCP 调用工具 | `src/agents_v2/core/mcp_client.py` |

**MCP Server 实现示例**：

```python
# src/agents_v2/mcp/arxiv_server.py
from mcp.server import Server
from mcp.types import Tool, Resource
from typing import List

arxiv_server = Server("paper-agent-arxiv")

@arxiv_server.list_tools()
async def list_tools() -> List[Tool]:
    return [
        Tool(
            name="arxiv_search",
            description="在 arXiv 数据库中搜索预印本论文",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索关键词"},
                    "max_results": {"type": "integer", "default": 10}
                }
            }
        )
    ]

@arxiv_server.call_tool()
async def call_tool(name: str, arguments: dict) -> dict:
    if name == "arxiv_search":
        return await arxiv_search(
            query=arguments["query"],
            max_results=arguments.get("max_results", 10)
        )
```

#### Phase 2：A2A 协议基础实现（1周）

**目标**：实现 Agent 间标准化通信

**任务清单**：

| 任务 | 说明 | 文件 |
|------|------|------|
| AgentCard 定义 | 定义各 Agent 能力描述 | `src/agents_v2/a2a/agent_card.py` |
| A2A Client 实现 | Agent 间任务发送/订阅 | `src/agents_v2/a2a/client.py` |
| A2A Server 实现 | 接收并处理任务 | `src/agents_v2/a2a/server.py` |
| 任务路由集成 | MasterSupervisor 通过 A2A 分发任务 | `src/agents_v2/unified/master_supervisor.py` |

**AgentCard 示例**：

```json
{
  "name": "PaperAgent-Writer",
  "description": "学术论文写作智能体，支持逐章节撰写和引用标注",
  "url": "http://localhost:8000",
  "version": "1.0.0",
  "capabilities": {
    "streaming": true,
    "pushNotifications": false
  },
  "skills": [
    {
      "id": "draft_generation",
      "name": "初稿生成",
      "description": "基于大纲和参考文献生成论文初稿",
      "tags": ["academic", "writing", "draft"]
    }
  ]
}
```

#### Phase 3：Agent Skills 重构（1周）

**目标**：按 SKILL.md 三层渐进式披露标准重构

**任务清单**：

| 任务 | 说明 | 文件 |
|------|------|------|
| paper-search Skill | 论文搜索能力封装 | `src/agents_v2/skills/paper-search/SKILL.md` |
| paper-analysis Skill | 论文分析能力封装 | `src/agents_v2/skills/paper-analysis/SKILL.md` |
| report-generation Skill | 报告生成能力封装 | `src/agents_v2/skills/report-generation/SKILL.md` |
| citation-format Skill | 引用格式能力封装 | `src/agents_v2/skills/citation-format/SKILL.md` |
| Skill 加载器 | 支持 SKILL.md 三层加载 | `src/agents_v2/skills/loader.py` |

**SKILL.md 结构**：

```markdown
# Paper Search Skill

## 1. Metadata（~50 token）
- ID: paper-search
- Name: 论文搜索
- Trigger: 用户请求搜索论文

## 2. Core Instructions（500-2000 token）
[激活时加载 - 搜索工具调用规范]

## 3. Reference Materials（深度需要时）
[搜索源 API 文档、示例查询]
```

### 1.3 验收标准

- [ ] ArXiv/PubMed/SS 三个 MCP Server 正常工作
- [ ] Agent 间可通过 A2A 协议通信
- [ ] AgentCard 可通过 `/.well-known/agent.json` 访问
- [ ] 至少 2 个 Skill 按 SKILL.md 标准重构

---

## 模块2：记忆系统 v4.0 升级计划

### 2.1 背景与目标

**现状**：
- 已有 UnifiedMemoryManager v4 分层架构
- 智能触发机制已在 `长期记忆写入短期记忆机制改进方案.md` 中定义
- 遗忘曲线尚未完全集成到调用链

**目标**：
- 完整实现智能触发机制（`_should_recall_memories()`）
- 完整集成遗忘曲线（`retention = importance × e^(-t/S)`）
- 重要性阈值过滤（默认 0.3）
- 三系统整合（Hermes/Hindsight/Obsidian）

### 2.2 实施计划

#### Phase 1：智能触发机制集成（1周）

**任务清单**：

| 任务 | 说明 | 文件 |
|------|------|------|
| 修复 MemoryNode 导入 | 使用 UnifiedMemoryManager | `src/agents_v2/langgraph_workflow/nodes/memory.py` |
| 实现 _should_recall_memories | 历史关键词检测 | `src/agents_v2/core/context_injector.py` |
| 实现遗忘曲线计算 | _calculate_retention_score | `src/agents_v2/core/context_injector.py` |
| 实现重要性阈值过滤 | _prioritize_memories | `src/agents_v2/core/context_injector.py` |
| 单元测试 | 测试智能触发逻辑 | `tests/test_memory_recall_improvement.py` |

#### Phase 2：存储层升级（1-2周）

**任务清单**：

| 任务 | 说明 | 文件 |
|------|------|------|
| PostgreSQL 会话存储 | 会话记忆持久化 | `src/agents_v2/memory/session.py` |
| 向量存储集成 | Qdrant 向量检索 | `src/agents_v2/memory/embeddings.py` |
| 知识图谱集成 | Neo4j 实体关系 | `src/agents_v2/knowledge_graph/kg_service.py` |
| 重要性评分系统 | 五级重要性体系 | `src/agents_v2/memory/importance_scorer.py` |

#### Phase 3：三系统整合（1周）

**任务清单**：

| 任务 | 说明 | 参考 |
|------|------|------|
| Hermes 学习循环 | Tracker→Evaluator→Reflector→Crystallizer | `docs/research/AI_Agent_记忆系统调研报告_Hermes_Hindsight_Obsidian.md` |
| Hindsight 图谱 | TEMPR 时序检索 + CARA 自适应推理 | 同上 |
| Obsidian 文档 | Markdown 双向链接 | 同上 |

### 2.3 验收标准

- [ ] `_should_recall_memories()` 在历史问题场景正确触发
- [ ] 遗忘曲线时间衰减正常工作
- [ ] 重要性 < 0.3 的记忆被正确过滤
- [ ] 会话记忆可通过 PostgreSQL 持久化

---

## 模块3：意图路由三级级联升级计划

### 3.1 背景与目标

**现状**：
- IntentRouter 已实现 11 种意图类型
- 采用关键词匹配 + LLM 辅助的两步路由

**目标**：
- 实现三级级联混合路由（关键词→语义向量→LLM）
- 降低 85% 路由成本
- P50 延迟从 800ms 降至 15ms

### 3.2 实施计划

#### Phase 1：语义向量路由层（1周）

**任务清单**：

| 任务 | 说明 | 文件 |
|------|------|------|
| 语义向量模型 | BAAI/bge-small-zh-v1.5 | `src/agents_v2/routing/vector_encoder.py` |
| 向量索引构建 | FastEmbed 索引 | `src/agents_v2/routing/vector_index.py` |
| 语义相似度计算 | 余弦相似度 | `src/agents_v2/routing/similarity.py` |
| Layer 2 路由实现 | 语义向量路由 | `src/agents_v2/routing/cascade_router.py` |

#### Phase 2：级联路由组装（1周）

**任务清单**：

| 任务 | 说明 | 文件 |
|------|------|------|
| Layer 1 优化 | 关键词匹配 | `src/agents_v2/routing/keyword_matcher.py` |
| Layer 3 LLM 降级 | Instructor 结构化输出 | `src/agents_v2/routing/llm_classifier.py` |
| 置信度校准 | 三层结果合并 | `src/agents_v2/routing/confidence_calibrator.py` |
| 降级兜底 | fallback_router.py | `src/agents_v2/routing/fallback_router.py` |

#### Phase 3：性能优化（1周）

**任务清单**：

| 任务 | 说明 | 文件 |
|------|------|------|
| Prompt Cache | 缓存高频 Prompt | `src/agents_v2/core/prompt_cache.py` |
| 批量推理 | 向量批量编码 | `src/agents_v2/routing/batch_encoder.py` |
| 路由指标 | P50/P95 延迟统计 | `src/agents_v2/monitoring/route_metrics.py` |

### 3.3 验收标准

- [ ] Layer 1/2/3 三级路由正常工作
- [ ] LLM 路由占比从 60% 降至 20%
- [ ] P50 路由延迟 < 50ms

---

## 模块4：Evaluator/Harness 质量保障体系计划

### 4.1 背景与目标

**现状**：
- Evaluator 已实现 7 维度评分
- CircuitBreaker 已实现
- HITL Manager 已实现 5 个中断点

**目标**：
- 完善 5 大维度评估体系（学术规范性/研究质量/内容完整性/表达质量/逻辑严谨性）
- 集成 AgentBench/SWE-bench/PaperBench 评估基准
- 完善 AuditTrail 审计溯源

### 4.2 实施计划

#### Phase 1：Evaluator 完善（1-2周）

**任务清单**：

| 任务 | 说明 | 文件 |
|------|------|------|
| 5 维度评分实现 | 学术规范性/研究质量/内容完整性/表达质量/逻辑严谨性 | `src/agents_v2/evaluation/evaluator.py` |
| 权重配置 | 各维度权重（20%/25%/20%/15%/20%） | `src/agents_v2/evaluation/weights.py` |
| LLM-as-Judge | 结构化输出评分 | `src/agents_v2/evaluation/llm_judge.py` |
| 规则引擎 | 格式/引用规则校验 | `src/agents_v2/evaluation/rule_engine.py` |

#### Phase 2：评估基准集成（1周）

**任务清单**：

| 任务 | 说明 | 文件 |
|------|------|------|
| AgentBench 接口 | 8 环境评估 | `src/agents_v2/evaluation/benchmarks/agent_bench.py` |
| PaperBench 接口 | 论文复现评估 | `src/agents_v2/evaluation/benchmarks/paper_bench.py` |
| 评估报告生成 | JSON 格式评估结果 | `src/agents_v2/evaluation/report_generator.py` |

#### Phase 3：AuditTrail 完善（1周）

**任务清单**：

| 任务 | 说明 | 文件 |
|------|------|------|
| 操作记录 | agent/action/input/output/latency | `src/agents_v2/monitoring/audit_logger.py` |
| 状态转换记录 | from_state/to_state/trigger | `src/agents_v2/monitoring/state_recorder.py` |
| 人机交互记录 | user/action/content/timestamp | `src/agents_v2/unified/hitl_manager.py` |

### 4.3 验收标准

- [ ] 5 维度 Evaluator 评分正常工作
- [ ] CircuitBreaker 在阈值触发时正确熔断
- [ ] AuditTrail 记录完整操作

---

## 模块5：PDF 解析系统升级计划

### 5.1 背景与目标

**现状**：
- 使用 pdfplumber 基础解析
- 无公式/表格/中文专项支持

**目标**：
- 集成 Marker（主解析引擎）
- 集成 PDF-Extract-Kit（复杂公式/中文）
- 实现自动路由

### 5.2 实施计划

#### Phase 1：Marker 集成（1周）

**任务清单**：

| 任务 | 说明 | 文件 |
|------|------|------|
| Marker 安装 | pip install marker-pdf | `requirements.txt` |
| Marker 解析器 | PDF → Markdown | `src/agents_v2/tools/marker_parser.py` |
| 公式提取 | LaTeX/MathML 输出 | 同上 |
| API 封装 | async parse 接口 | 同上 |

#### Phase 2：PDF-Extract-Kit 集成（1-2周）

**任务清单**：

| 任务 | 说明 | 文件 |
|------|------|------|
| PDF-Extract-Kit 安装 | 模型下载 | `requirements.txt` |
| 中文解析器 | 中文论文专项 | `src/agents_v2/tools/chinese_parser.py` |
| 公式识别 | 复杂公式提取 | `src/agents_v2/tools/formula_extractor.py` |
| 自动路由 | 中文/公式 → PDF-Extract-Kit，其他 → Marker | `src/agents_v2/tools/smart_pdf_router.py` |

### 5.3 验收标准

- [ ] Marker 解析英文论文正常工作
- [ ] PDF-Extract-Kit 解析中文论文正常工作
- [ ] 自动路由根据内容类型选择合适引擎

---

## 模块6：可观测性架构升级计划

### 6.1 背景与目标

**现状**：
- WorkflowTracer 实现基础追踪
- 日志使用 Loguru

**目标**：
- 集成 LangfuseTracer（LLM 调用级追踪）
- 符合 OpenTelemetry 标准
- 完善日志系统

### 6.2 实施计划

#### Phase 1：Langfuse 集成（1周）

**任务清单**：

| 任务 | 说明 | 文件 |
|------|------|------|
| Langfuse SDK 安装 | pip install langfuse | `requirements.txt` |
| LangfuseTracer | LLM 调用级追踪 | `src/agents_v2/monitoring/langfuse_tracer.py` |
| Prompt/Completion 捕获 | 完整日志 | 同上 |
| Web UI 集成 | langfuse.com dashboard | `config.yaml` |

#### Phase 2：OpenTelemetry 标准化（1周）

**任务清单**：

| 任务 | 说明 | 文件 |
|------|------|------|
| Trace 接口 | start_trace/end_trace | `src/agents_v2/monitoring/otel_interface.py` |
| Span 记录 | start_node/end_node | 同上 |
| 指标采集 | Token 使用/成本统计 | `src/agents_v2/monitoring/metrics.py` |

#### Phase 3：日志系统升级（1周）

**任务清单**：

| 任务 | 说明 | 文件 |
|------|------|------|
| 结构化日志 | JSON 格式 | `src/agents_v2/logging_config.py` |
| TraceId 串联 | 全链路关联 | 同上 |
| 异步写入 | 不阻塞业务 | 同上 |
| 告警机制 | ERROR/CRITICAL 告警 | `src/agents_v2/monitoring/alerting.py` |

### 6.3 验收标准

- [ ] LangfuseTracer 正常记录 LLM 调用
- [ ] OpenTelemetry 接口符合标准
- [ ] 日志支持 JSON 格式和 TraceId 串联

---

## 模块7：前端 AG-UI 集成计划

### 7.1 背景与目标

**现状**：
- 前端使用 REST 轮询
- 无实时流式交互

**目标**：
- 接入 AG-UI 协议（CopilotKit）
- 实现 16 种事件类型
- 实时流式进度展示

### 7.2 实施计划

#### Phase 1：AG-UI 协议集成（1周）

**任务清单**：

| 任务 | 说明 | 文件 |
|------|------|------|
| CopilotKit 安装 | @copilotkit/react | `frontend/package.json` |
| AG-UI 事件类型 | TEXT_MESSAGE/TOOL_CALL/STATE_SNAPSHOT 等 | `frontend/src/components/AGUIProvider.tsx` |
| 流式响应 | SSE 实时推送 | `frontend/src/hooks/useStream.ts` |
| 进度展示 | Step-by-step 进度条 | `frontend/src/components/StreamProgress.tsx` |

#### Phase 2：UI 组件开发（1-2周）

**任务清单**：

| 任务 | 说明 | 文件 |
|------|------|------|
| Diff 视图 | Accept/Reject 补丁 | `frontend/src/components/DiffView.tsx` |
| 状态快照 | STATE_SNAPSHOT 展示 | `frontend/src/components/StateSnapshot.tsx` |
| 工具调用 | TOOL_CALL 展示 | `frontend/src/components/ToolCall.tsx` |
| 错误提示 | ERROR 事件展示 | `frontend/src/components/ErrorToast.tsx` |

### 7.3 验收标准

- [ ] AG-UI 事件正常接收和展示
- [ ] SSE 流式响应正常
- [ ] Diff 视图可 Accept/Reject 修改

---

## 模块8：Skill 体系重构计划

### 8.1 背景与目标

**现状**：
- 已有 `src/agents_v2/skills/` 目录
- 无标准 SKILL.md 格式

**目标**：
- 按 Agent Skills 标准重构
- 实现 SKILL.md 三层渐进式披露
- 支持 Tool Wrapper/Generator/Reviewer/Inversion/Pipeline

### 8.2 实施计划

#### Phase 1：Skill 目录重构（1周）

**任务清单**：

| 任务 | 说明 | 文件 |
|------|------|------|
| paper-search Skill | 论文搜索三层结构 | `src/agents_v2/skills/paper-search/` |
| paper-analysis Skill | 论文分析三层结构 | `src/agents_v2/skills/paper-analysis/` |
| report-generation Skill | 报告生成三层结构 | `src/agents_v2/skills/report-generation/` |
| citation-format Skill | 引用格式三层结构 | `src/agents_v2/skills/citation-format/` |

#### Phase 2：Skill 加载器开发（1周）

**任务清单**：

| 任务 | 说明 | 文件 |
|------|------|------|
| Metadata 加载 | ~50 token/skill | `src/agents_v2/skills/loaders/metadata_loader.py` |
| Core Instructions 加载 | 500-2000 token/skill | `src/agents_v2/skills/loaders/core_loader.py` |
| Reference Materials 加载 | 深度时加载 | `src/agents_v2/skills/loaders/reference_loader.py` |
| 渐进式披露控制器 | 根据需要层级加载 | `src/agents_v2/skills/loaders/progressive_loader.py` |

#### Phase 3：Skill 执行器开发（1周）

**任务清单**：

| 任务 | 说明 | 文件 |
|------|------|------|
| ToolWrapper 执行 | 工具包装执行 | `src/agents_v2/skills/executors/tool_wrapper.py` |
| Generator 执行 | 生成器执行 | `src/agents_v2/skills/executors/generator.py` |
| Reviewer 执行 | 评审器执行 | `src/agents_v2/skills/executors/reviewer.py` |
| Pipeline 执行 | 流水线执行 | `src/agents_v2/skills/executors/pipeline.py` |

### 8.3 验收标准

- [ ] 4 个 Skill 目录符合 SKILL.md 标准
- [ ] 渐进式披露机制正常工作
- [ ] Tool Wrapper/Generator/Reviewer 执行器正常

---

## 附录：开发依赖关系

```
模块1 (MCP/A2A) ─────────┬──→ 模块8 (Skill体系重构)
                         │
模块2 (记忆系统) ─────────┼──→ 模块4 (Harness)
                         │
模块3 (意图路由) ─────────┤
                         │
模块5 (PDF解析) ──────────┼──→ 模块6 (可观测性)
                         │
模块7 (前端AG-UI) ────────┘
```

---

**版本**：v1.0
**规划日期**：2026-05-02
**基于**：未来框架设计 v2.1 + 17 份调研报告 + 已实现架构
