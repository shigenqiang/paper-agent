# LLM 提示词与结构化输出模块专项开发报告

更新时间：2026-06-01

## 0. 与产品方案的关联

### 0.1 可借鉴技术

本模块可借鉴的产品与技术方案（来源：`当前产品方案.md` + `学术报告生成系统产品借鉴与技术方案调研.md` + `Agent提示词工程指南`）：

| 借鉴来源 | 借鉴内容 | 落地位置 |
| --- | --- | --- |
| LettuceDetect | Token-level 幻觉检测（ModernBERT），F1=79.22%，MIT 开源 | §9 结构化输出 + §11 错误处理 |
| PapersFlow | Chain of Verification (CoVe)：提取声明→逐条验证→标记状态 | §8 Prompt 管理 |
| GPT-Researcher | Review-Revise 循环（Writer→Reviewer→Revisor） | §8 Prompt 管理 + §14 模块接入 |
| Atlas | H/V ratio 质量指标（目标 < 0.1） | §12 日志与指标 |
| PRISMA-trAIce | AI 辅助 SR 透明报告检查清单（12 项） | §12 日志与指标 |
| Anthropic | Prompt Engineering 最佳实践：Few-Shot、CoT、角色设定 | §8 Prompt 管理 |
| RAGFlow | Parent-Child Chunking 上下文管理 | §13 模型路由与预算 |
| OpenAI Structured Outputs | JSON Schema 强制、function calling | §9 结构化输出 |
| Instructor | Pydantic schema → LLM structured output | §9 结构化输出 |

### 0.2 代码对齐状态

| 产品方案要求 | 代码现状 | 对齐状态 |
| --- | --- | --- |
| LLMService.invoke / invoke_json / invoke_structured | 已实现 | ✅ 已对齐 |
| PromptRegistry + PromptTemplateSpec | 已实现（4 个内置 prompt） | ✅ 已对齐 |
| JSON 提取（markdown/包围文本/尾逗号修复） | 已实现 extract_json + repair_json_with_llm | ✅ 已对齐 |
| 8 种错误类型 | 已实现 llm_errors.py | ✅ 已对齐 |
| 日志脱敏（截断 + API key 检测） | 已实现 redact_text + hash_text | ✅ 已对齐 |
| FakeLLMService 测试注入 | 已实现 | ✅ 已对齐 |
| LLMCallResult 调用元数据 | 已实现 | ✅ 已对齐 |
| 幻觉检测集成（LettuceDetect） | 未实现 | ❌ 未对齐 |
| Chain of Verification prompt 模板 | 未实现 | ❌ 未对齐 |
| Review-Revise prompt 模板 | 未实现 | ❌ 未对齐 |
| H/V ratio 记录到 LLMCallResult | 未实现 | ❌ 未对齐 |
| Few-Shot 示例管理 | 未实现 | ❌ 未对齐 |
| CoT (Chain of Thought) 模板 | 未实现 | ❌ 未对齐 |
| Token budget 估算 | 未实现 | ❌ 未对齐 |
| ModelRouter 任务路由 | 未实现 | ❌ 未对齐 |
| 上下文压缩 prompt | 未实现 | ❌ 未对齐 |
| Prompt Golden Tests 自动回归 | 未实现 | ❌ 未对齐 |

## 实现状态

P0 全部完成（2026-05-28）。

### 已完成

```text
LLMConfig 增强: timeout/max_retries/retry_backoff/seed/extra ✅
LLMCallResult: 调用元数据模型 ✅
llm_errors.py: LLMServiceError/LLMProviderError/LLMTimeoutError/LLMRateLimitError/EmptyLLMResponseError/JsonExtractionError/StructuredOutputError/JsonRepairError ✅
llm_json.py: extract_json (direct/markdown/surrounding text) + _try_fix_json + repair_json_with_llm ✅
llm_logging.py: redact_text + hash_text + log_llm_call (脱敏日志) ✅
prompt_registry.py: PromptTemplateSpec + PromptRegistry + 4 个内置 prompt ✅
invoke_structured: schema 校验 + repair + 错误分类 ✅
FakeLLMService: 测试用 fake，不调用真实 API ✅
reset_llm_service: 测试用重置 ✅
```

### 新增文件

- `llm_errors.py` — 8 种错误类型
- `llm_json.py` — JSON 提取（markdown 代码块/包围文本/尾逗号修复）+ LLM repair
- `llm_logging.py` — 日志脱敏（截断 + API key 检测）+ 调用指标日志
- `prompt_registry.py` — PromptTemplateSpec + PromptRegistry + 内置 prompt（paper_card/scope_qa/review/innovation）

### 当前代码路径对齐

当前实现已经拆入 `llm/` 子包，后续开发和文档维护以子包路径为准：

```text
src/agents_v3/research_workspace/llm/service.py
src/agents_v3/research_workspace/llm/errors.py
src/agents_v3/research_workspace/llm/json_utils.py
src/agents_v3/research_workspace/llm/prompts.py
src/agents_v3/research_workspace/llm/logging.py
```

当前仍需收敛：

```text
1. 业务模块逐步统一使用 `llm/service.py` 的 invoke_structured。
2. PromptRegistry 的 prompt_name/version/module 要写入 PaperCard、QAResponse、Report metadata。
3. LLMCallResult 与 evaluation.metrics 打通，记录 latency、success、error_type、json_repair。
4. 旧文档或旧代码中的根目录 `llm_service.py` 命名需要迁移为 `llm/service.py`。
5. FakeLLMService 应成为所有生成模块默认测试入口。
```

LLM 提示词与结构化输出模块负责统一 research_workspace 中所有模型调用、Prompt 版本管理、结构化输出校验、JSON 提取与修复、错误处理、fallback 协议、日志脱敏、调用指标和模型路由。它不是简单封装一次 `ChatOpenAI.invoke()`，而是整个项目的 LLM 网关：所有抽取、问答、综述、创新点生成都应通过这一层获得可校验、可追踪、可回归测试的模型输出。

对应代码：

```text
src/agents_v3/research_workspace/llm/service.py
src/agents_v3/research_workspace/llm/prompts.py
src/agents_v3/research_workspace/llm/json_utils.py
src/agents_v3/research_workspace/llm/errors.py
src/agents_v3/research_workspace/llm/logging.py
src/agents_v3/research_workspace/paper_card.py
src/agents_v3/research_workspace/scope_qa.py
src/agents_v3/research_workspace/review_generator.py
src/agents_v3/research_workspace/innovation_generator.py
```

建议新增或拆分：

```text
src/agents_v3/research_workspace/llm_errors.py
src/agents_v3/research_workspace/llm_json.py
src/agents_v3/research_workspace/llm_structured.py
src/agents_v3/research_workspace/llm_logging.py
src/agents_v3/research_workspace/model_router.py
src/agents_v3/research_workspace/prompt_registry.py
src/agents_v3/research_workspace/prompts/
tests/agents_v3/research_workspace/test_llm_service.py
tests/agents_v3/research_workspace/test_llm_json_extract.py
tests/agents_v3/research_workspace/test_llm_structured_output.py
tests/agents_v3/research_workspace/test_llm_repair.py
tests/agents_v3/research_workspace/test_llm_logging_redaction.py
tests/agents_v3/research_workspace/test_prompt_registry.py
```

## 1. 模块定位

### 1.1 在产品链路中的位置

LLM 模块是多个核心能力的共同底座：

```text
PDF chunks
  -> PaperCard structured extraction
  -> Evidence table
  -> ScopeQA structured answer
  -> Review structured sections
  -> Innovation structured candidates
  -> Report validation/export metadata
```

本模块不直接决定业务事实是否正确，但它必须保证：

```text
1. 模型输出能被解析。
2. 模型输出能被 schema 校验。
3. 模型失败能被业务模块识别。
4. 调用记录能用于调试、评估和成本控制。
5. 日志不会泄露 API key、完整 PDF、完整 prompt 或用户敏感材料。
```

### 1.2 上下游关系

| 上游/下游 | 关系 | 本模块职责 |
| --- | --- | --- |
| 04 PDF 解析与分块 | 提供 chunks | 控制 prompt 输入长度和脱敏记录 |
| 05 论文卡片 | 使用 LLM 抽取结构化字段 | 提供 `invoke_structured(PaperCardExtractionResult)` |
| 06 证据表 | 后续可用 LLM 辅助 evidence schema | 提供强 schema 与来源约束 |
| 09 ScopeQA/RAG | 使用 LLM 生成答案 | 输出必须绑定 evidence_ids，失败进入拒答/fallback |
| 10 综述生成 | 使用 LLM 生成章节 | 输出 sections/source ids/uncertainty |
| 11 创新点报告 | 使用 LLM 补全候选创新点 | 输出 source_signal_ids/supporting_evidence_ids |
| 12 报告版本与导出 | 保存 prompt/model metadata | 提供 prompt_version、model、usage |
| 15 评估日志监控 | 统计 LLM 失败率、解析率、成本 | 输出结构化调用指标 |

### 1.3 核心原则

```text
1. LLM 输出不是可信数据，必须经过 schema 和业务校验。
2. JSON 解析失败不能返回伪成功。
3. Prompt 必须有 name/version/module。
4. 模型失败、解析失败、schema 失败要有不同错误类型。
5. fallback 是业务层策略，但 LLM 层要给出可判断的错误。
6. 日志记录指标，不记录完整私有文本。
7. 测试必须能使用 FakeLLM，不依赖真实 API。
8. 旧的 invoke_json 调用需要平滑迁移。
```

## 2. 本地调研结论落地

### 2.1 论文卡片模块要求

05 论文卡片模块已经要求：

```text
PaperCardExtractionResult
ExtractedClaim
quote + chunk_id
Pydantic validate
repair once
fallback confidence <= 0.5
prompt_version
model_name
```

对本模块的落地要求：

| 要求 | LLM 层能力 |
| --- | --- |
| 每条 claim 有 quote/chunk_id | schema 强制字段 + 业务层 source validation |
| 输出可 repair | `invoke_structured(..., repair=True)` |
| 记录 prompt_version | `PromptTemplateSpec` |
| 记录 model_name | `LLMCallResult.model` |
| fallback 低置信 | 结构化错误抛给业务层 |

当前 `paper_card.py` 已有局部 repair，但这应逐步上移到统一 LLM 层，避免每个模块重复实现。

### 2.2 ScopeQA 模块要求

09 ScopeQA 要求：

```text
只基于 scope evidence。
证据不足要拒答。
输出 supporting_evidence_ids。
LLM 输出越界引用要过滤。
JSON 解析失败要 fallback 和 warning。
测试注入 FakeLLM。
```

对本模块的落地要求：

```text
QA prompt 必须声明 scope boundary。
QA schema 必须包含 answer、supporting_evidence_ids、supporting_papers、uncertainty。
LLM 层只保证 schema，ScopeGuard 仍在 QA 业务层。
LLM 层错误必须能区分 parse_failed / schema_failed / provider_failed。
```

### 2.3 综述生成模块要求

10 综述生成模块要求：

```text
每个主要章节返回 evidence_ids 和 paper_ids。
不信任 LLM 自带引用。
报告需要 section_sources。
长 Scope 需要 token budget。
LLM 失败进入 fallback。
```

对本模块的落地要求：

```text
ReviewSection schema。
ReviewGenerationResult schema。
Prompt 中显式要求每节来源。
LLM 调用记录 prompt_tokens/completion_tokens 或估算值。
支持 max_context_tokens 和 prompt length 统计。
```

### 2.4 创新点报告模块要求

11 创新点报告模块要求：

```text
source_signal_ids
supporting_evidence_ids
limiting_evidence_ids
evidence_status
scores_hint / uncertainty
不得虚构 paper_id/evidence_id
```

对本模块的落地要求：

```text
InnovationGenerationResult schema。
Prompt 输入必须传入可用 ID 列表。
schema 只保证字段存在，ID 是否越界由业务层 validator 校验。
repair prompt 不得新增事实和 ID。
```

### 2.5 报告版本与导出模块要求

12 报告模块需要保存：

```text
prompt_name
prompt_version
model
provider
generation_mode
token_usage
latency_ms
```

对本模块的落地要求：

```text
LLMCallResult 可序列化。
StructuredLLMResult 带 metadata。
生成模块能把调用元数据写入 Report.scope.report_metadata 或 Report.metadata。
```

### 2.6 评估日志模块要求

15 评估日志模块需要统计：

```text
json_parse_failure_rate
llm_failure_rate
latency_ms
token cost
redaction_check
```

对本模块的落地要求：

```text
统一日志事件 llm.call。
统一错误类型。
统一脱敏函数。
记录 prompt_hash/response_hash，而不是完整文本。
测试检查日志不含 API key 和长 prompt。
```

## 3. 主流做法与本项目选择

### 3.1 Structured Outputs / JSON Schema

主流 LLM 应用倾向使用 JSON Schema 或 Pydantic schema 约束输出，减少自然语言解析失败。

本项目选择：

```text
P0 使用 Pydantic schema + prompt JSON schema 说明。
P1 增加 invoke_structured(schema) 统一校验和 repair。
P2 如果 provider 支持原生 structured output，再接入 provider-native schema。
```

理由：

```text
当前代码已使用 Pydantic。
业务模型较多，Pydantic 便于复用和测试。
provider-native structured output 能力会随模型变化，先避免强绑定。
```

### 3.2 LangChain Structured Output

LangChain 提供结构化输出能力，但本项目不能完全把业务校验交给框架：

```text
LangChain 可用于 provider 调用。
JSON 提取、repair、业务错误类型、日志脱敏仍建议自有封装。
```

原因：

```text
业务需要强 ScopeGuard、source quote 校验和 fallback 元数据。
框架返回的异常类型不一定稳定。
项目测试需要 FakeLLM，而不是总走真实 LangChain。
```

### 3.3 Instructor 风格

Instructor 的启发是：以 Pydantic schema 为中心做 LLM 调用、重试和校验。

本项目落地：

```text
invoke_structured(schema)
schema validation error -> repair once
repair still failed -> StructuredOutputError
business fallback handles error
```

### 3.4 Observability / OpenTelemetry / LangSmith

主流 LLM 应用会记录：

```text
model
latency
token usage
retry count
error
prompt version
trace id
```

本项目 P0 不引入外部观测平台，只做本地结构化日志：

```text
Loguru event dict
redacted metrics
optional JSONL logs
```

P2 再考虑：

```text
OpenTelemetry adapter
LangSmith adapter
dashboard metrics
```

## 4. 当前实现分析

### 4.1 当前 LLMService 能力

当前 `llm/` 子包包含：

```text
LLMConfig
LLMService.llm lazy property
LLMService._create_llm()
LLMService.invoke(system_prompt, user_prompt)
LLMService.invoke_json(system_prompt, user_prompt)
get_llm_service(config=None)
```

`LLMConfig` 当前字段：

```text
provider = "openai"
model_name = "MiniMax-M2.7"
temperature = 0.7
max_tokens = 4096
api_key = None
base_url = None
```

`_create_llm()` 当前支持：

```text
openai -> langchain_openai.ChatOpenAI
anthropic -> langchain_anthropic.ChatAnthropic
unknown provider -> fallback ChatOpenAI
```

`invoke_json()` 当前逻辑：

```text
1. 调用 invoke。
2. 如果包含 ```json，用 split 提取。
3. 如果包含普通 ```，用 split 提取。
4. 否则把整个响应当 JSON。
5. json.loads。
6. JSONDecodeError 时记录 warning，并返回 {"raw_response": response}。
```

### 4.2 当前各生成模块调用方式

| 模块 | 当前调用方式 | 当前 fallback |
| --- | --- | --- |
| `paper_card.py` | `self.llm.invoke_json(SYSTEM_PROMPT, user_prompt)` | `_extract_card_fallback()` |
| `scope_qa.py` | `self.llm.invoke_json(QA_SYSTEM_PROMPT, user_prompt)` | `_fallback_answer()` |
| `review_generator.py` | `self.llm.invoke_json(REVIEW_SYSTEM_PROMPT, user_prompt)` | `_generate_fallback()` |
| `innovation_generator.py` | `self.llm.invoke_json(INNOVATION_SYSTEM_PROMPT, user_prompt)` | `_generate_fallback()` |

当前 Prompt 状态：

```text
SYSTEM_PROMPT 常量分散在各模块文件内。
没有 prompt name。
没有 prompt version。
没有 prompt registry。
没有统一输出 schema registry。
```

### 4.3 当前已有局部能力

`paper_card.py` 已有较强局部能力：

```text
PaperCardExtractionResult
Pydantic 校验
_repair_extraction_result
fallback
validation_errors
quality_score
```

但问题是：

```text
这些能力没有复用到 QA/Review/Innovation。
repair 逻辑只处理特定 schema。
LLM 层仍可能返回 raw_response 伪成功。
```

### 4.4 当前测试状态

当前已有 LLMService 测试文件，但仍需要按结构化输出子能力继续拆细：

```text
tests/agents_v3/research_workspace/test_llm_service.py 已存在
test_llm_json_extract.py 待按 json_utils.py 补充
test_llm_structured_output.py 待按 invoke_structured 补充
```

部分 E2E 测试通过：

```text
service.llm = None
```

来触发 fallback。这可以避免真实 API，但无法测试：

```text
JSON fenced block 提取
schema validation
repair
redaction
retry
metrics
```

### 4.5 当前关键缺口

| 问题 | 当前表现 | 影响 | 优先级 |
| --- | --- | --- | --- |
| JSON 失败返回伪成功 | `{"raw_response": response}` | 下游可能当作有效 dict | P0 |
| 无统一 schema 调用 | 各模块自行解析 | QA/Review/Innovation 输出质量不稳定 | P0 |
| Prompt 常量分散 | 每个模块一个常量 | 无版本、难评估、难回归 | P0 |
| 无错误类型 | 只抛普通异常或返回 raw_response | 业务层无法精确 fallback | P0 |
| 无 retry/timeout | provider 故障不可控 | 长任务不稳定 | P0 |
| 无 repair 通用流程 | 只有 PaperCard 局部 repair | 常见 JSON 小错无法恢复 | P0 |
| 无日志指标 | 只记录异常文本 | 无 latency/token/failure rate | P0 |
| 脱敏不统一 | warning 记录 response 前 200 字 | 可能泄露用户材料 | P0 |
| 单例配置易混乱 | `_llm_service` 已存在时忽略新 config | 测试和多模型配置不稳定 | P1 |
| 无模型路由 | 所有任务共用同配置 | 成本和质量不可控 | P1 |
| 无 token budget | 输入长度只在业务层粗略截断 | 上下文过长风险 | P1 |
| 无 prompt golden tests | Prompt 改坏难发现 | 质量回归不可控 | P1 |
| 无 provider-native structured output | 只靠 prompt 约束 | 解析失败率更高 | P2 |

## 5. 目标与边界

### 5.1 一句话目标

建立统一、可校验、可修复、可观测、可回归测试的 LLM 结构化输出层，让所有生成模块都能稳定获得 typed result 或明确失败原因。

### 5.2 MVP 成功标准

```text
1. LLMConfig 支持 timeout、max_retries、temperature、max_tokens、request_timeout。
2. invoke_json 解析失败不再返回 raw_response 伪成功。
3. 新增 extract_json(text)，支持常见 JSON/fenced block 提取。
4. 新增 invoke_structured(schema)，返回 Pydantic 对象或 StructuredOutputError。
5. 支持一次 JSON repair，且 repair prompt 不得新增事实。
6. LLMCallResult 记录 model、provider、latency_ms、retry_count、status、error_type。
7. 日志不记录 API key、完整 prompt、完整 PDF 文本、完整 response。
8. PromptTemplateSpec 包含 name/version/module/output_schema_name。
9. PaperCard、ScopeQA、Review、Innovation 有迁移到 structured output 的开发路径。
10. 单测使用 FakeLLM，不访问真实 API。
```

### 5.3 非目标

MVP 不做：

```text
1. 完整多供应商高级路由。
2. 完整 token 计费系统。
3. 流式 UI 输出。
4. 批量并发限流队列。
5. OpenTelemetry/LangSmith 深度集成。
6. 完整 Prompt 自动优化系统。
7. 用 LLM judge 替代业务校验。
```

P2 可扩展：

```text
provider-native structured outputs
streaming response
batch requests
rate limiter
cost dashboard
prompt experiment registry
LLM judge evaluation
OpenTelemetry adapter
```

## 6. 目标架构

### 6.1 服务拆分

```text
LLMService
  对外门面，兼容 invoke/invoke_json，并新增 invoke_structured。

ProviderClientFactory
  根据 LLMConfig 创建 ChatOpenAI/ChatAnthropic 等 client。

PromptRegistry
  管理 prompt name/version/module/schema。

PromptRenderer
  渲染 system/user prompt，注入 schema 和规则。

JsonExtractor
  从模型响应中提取 JSON 对象或数组。

StructuredOutputParser
  Pydantic schema 校验和错误收集。

JsonRepairer
  对格式损坏的 JSON 做一次受约束修复。

LLMCallLogger
  记录脱敏后的调用指标。

ModelRouter
  P1 根据 task_type 选择模型配置。

TokenBudgetEstimator
  P1 估算 prompt 长度和截断风险。
```

### 6.2 推荐调用链

结构化调用：

```text
business module
  -> PromptRegistry.get(name, version)
  -> PromptRenderer.render(input)
  -> LLMService.invoke_structured(schema)
  -> provider invoke with retry/timeout
  -> JsonExtractor.extract
  -> schema.model_validate
  -> optional JsonRepairer.repair
  -> StructuredLLMResult
  -> business validation
  -> business fallback if needed
```

旧调用兼容：

```text
business module
  -> LLMService.invoke_json(system_prompt, user_prompt)
  -> strict JSON parse
  -> dict
```

P0 保留 `invoke_json`，但改为：

```text
解析失败抛 JsonParseError。
如果需要旧行为，可提供 invoke_json_legacy 或 options.strict=False。
```

### 6.3 依赖方向

```text
llm/service.py
  -> llm/errors.py
  -> llm/json_utils.py
  -> llm/logging.py
  -> llm/prompts.py
  -> prompt/model router 预留扩展
```

业务模块：

```text
paper_card.py
scope_qa.py
review_generator.py
innovation_generator.py
```

只能调用 LLMService，不应直接依赖 provider SDK。

## 7. 数据模型设计

### 7.1 LLMConfig

```python
class LLMConfig(BaseModel):
    provider: str = "openai"
    model_name: str = "MiniMax-M2.7"
    temperature: float = 0.2
    max_tokens: int = 4096
    timeout: float = 60.0
    request_timeout: float | None = None
    max_retries: int = 2
    retry_backoff_seconds: float = 1.0
    api_key: str | None = None
    base_url: str | None = None
    organization: str | None = None
    seed: int | None = None
    extra: dict[str, Any] = Field(default_factory=dict)
```

默认建议：

```text
temperature = 0.2
max_tokens = 4096
timeout = 60
max_retries = 2
```

结构化抽取任务默认低温，创新点可由业务层通过 task_type 提高到 0.3-0.5，但仍必须有证据校验。

### 7.2 PromptTemplateSpec

```python
class PromptTemplateSpec(BaseModel):
    name: str
    version: str
    module: str
    task_type: str
    system_prompt: str
    user_template: str = ""
    output_schema_name: str = ""
    output_schema_version: str = "v1"
    rules: list[str] = Field(default_factory=list)
    forbidden: list[str] = Field(default_factory=list)
    examples: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
```

Prompt 命名：

```text
paper_card_extraction_v1
scope_qa_answer_v1
review_generation_v1
innovation_generation_v1
json_repair_v1
```

### 7.3 PromptRenderResult

```python
class PromptRenderResult(BaseModel):
    prompt_name: str
    prompt_version: str
    module: str
    system_prompt: str
    user_prompt: str
    input_hash: str = ""
    prompt_hash: str = ""
    estimated_prompt_tokens: int = 0
    redacted_preview: str = ""
```

用途：

```text
记录 prompt 版本。
记录 prompt hash。
避免日志写完整 prompt。
为 token budget 提供输入。
```

### 7.4 LLMCallResult

```python
class LLMCallResult(BaseModel):
    success: bool
    content: str = ""
    model: str = ""
    provider: str = ""
    latency_ms: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    retry_count: int = 0
    status: str = "success"
    error_type: str = ""
    error_message: str = ""
    request_id: str = ""
    prompt_name: str = ""
    prompt_version: str = ""
    prompt_hash: str = ""
    response_hash: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
```

`status` 枚举：

```text
success
provider_error
timeout
rate_limited
empty_response
parse_failed
schema_failed
repair_failed
cancelled
```

### 7.5 StructuredLLMResult

```python
class StructuredLLMResult(BaseModel, Generic[T]):
    parsed: T
    raw_content: str = ""
    call: LLMCallResult
    repaired: bool = False
    repair_attempts: int = 0
    validation_warnings: list[str] = Field(default_factory=list)
```

对于业务层，推荐使用：

```python
result = llm.invoke_structured(..., schema=QAAnswerSchema)
answer = result.parsed
metadata = result.call
```

### 7.6 LLMError 类型

```python
class LLMServiceError(Exception): ...
class LLMProviderError(LLMServiceError): ...
class LLMTimeoutError(LLMServiceError): ...
class LLMRateLimitError(LLMServiceError): ...
class EmptyLLMResponseError(LLMServiceError): ...
class JsonExtractionError(LLMServiceError): ...
class StructuredOutputError(LLMServiceError): ...
class JsonRepairError(LLMServiceError): ...
```

错误对象应包含：

```text
error_type
message
prompt_name
prompt_version
model
provider
raw_excerpt_hash
validation_errors
```

不要在异常 message 中拼完整 prompt 或完整 response。

### 7.7 ModelRoute

```python
class ModelRoute(BaseModel):
    task_type: str
    budget: str = "balanced"
    config: LLMConfig
    max_context_tokens: int = 12000
    allow_repair: bool = True
    allow_native_structured_output: bool = False
```

## 8. Prompt 管理

### 8.1 PromptRegistry

建议结构：

```text
src/agents_v3/research_workspace/llm/prompts.py
  PromptRegistry
  PromptTemplateSpec
  paper_card / scope_qa / review / innovation / repair prompt specs
```

每个文件导出：

```python
PROMPTS = {
    "paper_card_extraction_v1": PromptTemplateSpec(...),
}
```

注册入口：

```python
class PromptRegistry:
    def get(self, name: str, version: str | None = None) -> PromptTemplateSpec: ...
    def list(self, module: str | None = None) -> list[PromptTemplateSpec]: ...
```

### 8.2 Prompt 必备内容

每个 Prompt 必须包含：

```text
任务角色
输入边界
可用来源 ID
禁止事项
字段缺失处理
不确定性处理
输出 JSON schema
引用规则
失败时行为
```

### 8.2.1 Prompt Engineering 最佳实践（借鉴 Anthropic）

产品方案和调研报告要求 Prompt 采用结构化工程方法：

**5 部分结构（System Prompt 标准模板）**：

```text
1. Role（角色设定）：明确任务身份和专业领域
2. Context（上下文）：输入数据、Scope、可用 evidence
3. Task（任务描述）：具体要做什么、输出格式
4. Constraints（约束）：禁止事项、引用规则、不确定性处理
5. Examples（示例）：Few-Shot 示例（可选）
```

**Few-Shot 示例管理**：

```text
每个关键 prompt 应提供 1-3 个 Few-Shot 示例：
  - 示例输入：真实的 evidence 摘要
  - 示例输出：符合 schema 的 JSON
  - 示例应覆盖：正常情况、边界情况、拒答情况

示例存储：
  prompts/examples/{prompt_name}_{version}.json
  PromptTemplateSpec.few_shot_examples: list[dict]
```

**Chain of Thought (CoT)**：

```text
对于复杂推理任务（综述、创新点），在 JSON 输出前要求模型先推理：
  - "在输出 JSON 前，先分析以下几点："
  - 1. 证据是否充分？
  - 2. 结论是否有来源支撑？
  - 3. 是否存在反证？
  - 4. 不确定性有多大？

CoT 推理过程不进入最终 JSON，但可记录到 debug 日志。
```

**JSON 降级策略**：

```text
当模型无法输出完整 JSON 时：
  1. 要求模型至少输出 {"answer": "...", "confidence": 0.x}
  2. 如果仍然失败，invoke_json 返回 {"raw_response": "..."}
  3. 业务层从 raw_response 提取 answer，标记 generation_mode=fallback
```

### 8.3 禁止事项模板

通用禁止事项：

```text
不得使用输入以外的论文、事实或 ID。
不得虚构 paper_id、evidence_id、chunk_id、graph_node_id。
证据不足时必须标记 uncertainty 或 insufficient_evidence。
不得把 graph path 当作事实证据。
不得输出 Markdown 解释，只输出 JSON。
```

### 8.4 Prompt 版本策略

版本命名：

```text
v1
v1.1
v2
```

版本变化规则：

```text
仅措辞优化，不改变 schema -> patch version。
改变字段或规则 -> minor/major version。
改变业务含义 -> major version。
```

记录位置：

```text
PaperCard.prompt_version
QAHistory.prompt_version
Report.scope.report_metadata.prompt_version
ReportVersion.source_snapshot.prompt_version
```

### 8.5 Prompt Golden Tests

每个关键 prompt 至少有一个 golden case：

```text
输入 fixture
FakeLLM 输出
schema parse result
business validation expectation
```

Prompt 变更时检查：

```text
schema name 是否变化。
必填规则是否仍在 prompt。
禁止事项是否仍在 prompt。
输出示例是否仍合法 JSON。
```

## 9. 结构化输出设计

### 9.1 invoke_structured 签名

```python
def invoke_structured(
    self,
    system_prompt: str,
    user_prompt: str,
    schema: type[T],
    *,
    prompt_name: str = "",
    prompt_version: str = "",
    task_type: str = "",
    repair: bool = True,
    strict: bool = True,
    metadata: dict[str, Any] | None = None,
) -> StructuredLLMResult[T]:
    ...
```

### 9.2 流程

```text
1. 记录 start_time。
2. 调用 invoke_raw。
3. 提取 JSON。
4. schema.model_validate。
5. 成功则返回 StructuredLLMResult。
6. JSON 提取或 schema 校验失败时，repair 一次。
7. repair 后再次提取和校验。
8. 仍失败则抛 StructuredOutputError。
9. 记录脱敏日志。
```

### 9.3 schema 校验层次

LLM 层校验：

```text
字段是否存在。
字段类型是否正确。
枚举值是否合法。
默认值是否填充。
```

业务层校验：

```text
paper_id/evidence_id 是否属于 Scope。
quote 是否真的出现在 chunk。
supporting_evidence_ids 是否存在。
章节来源是否覆盖主要结论。
创新点是否空泛。
```

不要把业务校验塞进通用 LLM 层。

### 9.4 输出 schema registry

建议集中定义或导出：

```text
PaperCardExtractionResult
ScopeQAOutput
ReviewGenerationOutput
InnovationGenerationOutput
JsonRepairOutput
```

当前已经存在的 schema：

```text
PaperCardExtractionResult in paper_card.py
```

P0 可先复用业务模块中的 Pydantic 类；P1 再迁移到 `schemas/` 或模块内统一导出。

### 9.5 结构化结果元数据

业务模块保存结果时，应记录：

```text
model_name
provider
prompt_name
prompt_version
generation_mode = llm / repaired / fallback
latency_ms
token_usage
schema_name
schema_version
```

## 10. JSON 提取与 Repair

### 10.1 JsonExtractor 支持范围

必须支持：

```text
裸 JSON object
裸 JSON array
```json fenced block
普通 ``` fenced block
前后带自然语言说明的 JSON object
前后带自然语言说明的 JSON array
```

注意：上面的 fenced block 示例在实际文档中可能表现为代码围栏。实现时应按字符串模式处理。

### 10.2 提取策略

推荐顺序：

```text
1. strip 后直接 json.loads。
2. 查找 ```json ... ```。
3. 查找任意 ``` ... ```。
4. 从文本中扫描第一个平衡的 { ... } 或 [ ... ]。
5. 全部失败则抛 JsonExtractionError。
```

不要使用简单：

```python
response.split("```json")[1].split("```")[0]
```

原因：

```text
多个代码块会失败。
大小写 JSON 标记会失败。
前后有其他 fenced block 会误提取。
对象中包含 ``` 字符可能失败。
```

### 10.3 Repair 原则

Repair 只修格式，不补事实。

允许修：

```text
尾逗号
单引号
Markdown 包裹
缺少外层对象但字段明确
布尔值大小写
多余解释文字
```

不允许修：

```text
新增 paper_id/evidence_id。
新增 source_quote。
改写研究结论。
把缺失证据补成看似合理的证据。
替业务层判断 Scope。
```

### 10.4 Repair Prompt

```text
你只负责把以下模型输出修复为符合 JSON schema 的 JSON。
不要新增事实。
不要新增输入中不存在的 ID。
不要改写字段语义。
缺失字段使用 schema 默认值、空字符串、空数组或 unknown。
只输出 JSON，不输出解释。
```

### 10.5 Repair 输入

```json
{
  "schema_name": "ScopeQAOutput",
  "schema_json": {},
  "raw_output_excerpt": "...",
  "validation_errors": []
}
```

`raw_output_excerpt` 默认截断。完整 raw output 不写日志，但 repair 调用可以使用完整响应，仍需避免持久化。

### 10.6 Repair 失败处理

```text
repair_attempts = 1
repair_failed -> StructuredOutputError(error_type="repair_failed")
业务层捕获 -> fallback
fallback metadata 中写 llm_error_type
```

## 11. 错误处理与 fallback 契约

### 11.1 错误类型

| 错误 | 含义 | 业务层建议 |
| --- | --- | --- |
| `provider_error` | provider SDK 报错 | fallback 或重试任务 |
| `timeout` | 调用超时 | fallback，记录可重试 |
| `rate_limited` | 限流 | 延迟重试或提示用户 |
| `empty_response` | 模型返回空 | fallback |
| `json_parse_failed` | 无法提取 JSON | repair，再 fallback |
| `schema_validation_failed` | JSON 不符合 schema | repair，再 fallback |
| `repair_failed` | repair 后仍失败 | fallback |
| `redaction_error` | 日志脱敏异常 | 不阻断业务，但记录内部 warning |

### 11.2 业务 fallback 统一要求

fallback 不是“假装成功”，必须标记：

```text
generation_mode = fallback
confidence <= 0.5
validation_warnings includes llm_failed/json_failed/schema_failed
uncertainty 明确说明
不新增 scope 外事实
```

模块要求：

| 模块 | fallback 行为 |
| --- | --- |
| PaperCard | 用规则抽取，低置信，字段不足填 unknown |
| ScopeQA | 基于 evidence 摘要回答或拒答 |
| Review | 生成简短证据摘要，不写强结论 |
| Innovation | 只从 GapSignal 规则生成低置信候选 |

### 11.3 invoke_json 兼容策略

P0 改造建议：

```python
def invoke_json(..., strict: bool = True) -> dict[str, Any]:
    ...
```

行为：

```text
strict=True：解析失败抛 JsonExtractionError。
strict=False：返回 {"raw_response": response, "_parse_error": "..."}，仅用于临时兼容。
```

迁移目标：

```text
业务模块最终不再依赖 raw_response。
所有结构化任务迁移到 invoke_structured。
```

### 11.4 单例配置问题

当前：

```python
if _llm_service is None:
    _llm_service = LLMService(config)
return _llm_service
```

问题：

```text
第一次初始化后，后续传入 config 不生效。
测试间可能污染。
不同任务不能使用不同模型配置。
```

P0 处理：

```text
测试继续 monkeypatch _llm_service=None。
get_llm_service(config, force_new=False) 可选 force_new。
```

P1 处理：

```text
使用 ModelRouter，不依赖全局单例承载所有配置。
```

## 12. 日志、指标与脱敏

### 12.1 结构化日志事件

```text
llm.call.started
llm.call.completed
llm.call.failed
llm.json.extracted
llm.schema.validated
llm.repair.started
llm.repair.completed
llm.repair.failed
```

P0 可只记录一个聚合事件：

```text
llm.call
```

### 12.2 日志字段

```text
event_type
provider
model
prompt_name
prompt_version
task_type
project_id
paper_id
report_id
latency_ms
prompt_tokens
completion_tokens
total_tokens
retry_count
status
error_type
request_id
prompt_hash
response_hash
prompt_length
response_length
```

### 12.3 脱敏规则

禁止记录：

```text
API key
Authorization header
完整 system prompt
完整 user prompt
完整 PDF/chunk 文本
完整模型响应
用户本地文件绝对路径中的敏感片段
```

允许记录：

```text
prompt length
response length
hash
model
provider
latency
token usage
错误类型
截断后的错误摘要
```

### 12.4 Redactor

```python
class LLMRedactor:
    def redact_text(self, text: str, max_chars: int = 200) -> str: ...
    def hash_text(self, text: str) -> str: ...
    def redact_error(self, error: Exception) -> str: ...
    def redact_metadata(self, metadata: dict[str, Any]) -> dict[str, Any]: ...
```

需要识别：

```text
sk-...
Bearer ...
OPENAI_API_KEY=...
api_key=...
Windows absolute paths
very long chunk text
```

### 12.5 Token usage

LangChain 返回对象可能包含：

```text
response_metadata
usage_metadata
```

P0 策略：

```text
能读取 provider usage 就读取。
读不到则记录 estimated_prompt_tokens / estimated_completion_tokens。
估算可以用字符数 / 4 的粗略规则。
```

P1：

```text
引入更准确 tokenizer 或 provider-specific usage adapter。
```

### 12.6 指标

```text
llm_success_rate
llm_failure_rate
json_parse_failure_rate
schema_validation_failure_rate
repair_success_rate
fallback_rate
avg_latency_ms
p95_latency_ms
avg_prompt_tokens
avg_completion_tokens
redaction_check_pass_rate
```

## 13. 模型路由与预算

### 13.1 ModelRouter

P1 新增：

```python
class ModelRouter:
    def select(
        self,
        task_type: str,
        *,
        budget: str = "balanced",
        max_context_tokens: int | None = None,
    ) -> LLMConfig:
        ...
```

### 13.2 task_type

```text
paper_card
evidence_extraction
scope_qa
review_generation
innovation_generation
json_repair
evaluation
```

### 13.3 默认策略

| 任务 | temperature | 重点 |
| --- | --- | --- |
| paper_card | 0.1-0.2 | 稳定抽取、少幻觉 |
| evidence_extraction | 0.0-0.2 | 字段准确、来源严格 |
| scope_qa | 0.1-0.3 | 忠实回答、拒答 |
| review_generation | 0.2-0.4 | 组织结构和可读性 |
| innovation_generation | 0.3-0.5 | 有一定发散但证据约束 |
| json_repair | 0.0 | 只修格式 |
| evaluation | 0.0-0.2 | 稳定判断 |

### 13.4 TokenBudgetEstimator

P1 需要提供：

```python
estimate_tokens(text: str) -> int
check_budget(system_prompt, user_prompt, max_context_tokens) -> TokenBudgetReport
```

`TokenBudgetReport`：

```text
estimated_prompt_tokens
max_context_tokens
over_budget
suggested_truncation
largest_sections
```

业务模块仍负责如何截断或分批，LLM 层只提供预算报告。

## 14. 模块接入方案

### 14.1 PaperCard 接入

当前：

```python
result = self.llm.invoke_json(SYSTEM_PROMPT, user_prompt)
extraction = self._validate_extraction(result)
```

目标：

```python
result = self.llm.invoke_structured(
    system_prompt,
    user_prompt,
    PaperCardExtractionResult,
    prompt_name="paper_card_extraction",
    prompt_version="v1",
    task_type="paper_card",
)
extraction = result.parsed
```

仍保留：

```text
_validate_card()
quote/chunk_id 校验
fallback
quality_score
```

### 14.2 ScopeQA 接入

新增 schema：

```python
class ScopeQAOutput(BaseModel):
    answer: str = ""
    key_points: list[str] = Field(default_factory=list)
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    supporting_paper_ids: list[str] = Field(default_factory=list)
    graph_node_ids: list[str] = Field(default_factory=list)
    uncertainty: str = ""
    suggested_actions: list[str] = Field(default_factory=list)
```

LLM 层保证 schema。QA 层继续做：

```text
ScopeGuard
citation validation
empty evidence refusal
fallback answer
```

### 14.3 Review 接入

新增 schema：

```python
class ReviewSectionOutput(BaseModel):
    section_id: str
    title: str
    content: str
    paper_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    uncertainty: str = ""

class ReviewGenerationOutput(BaseModel):
    title: str
    summary: str = ""
    sections: list[ReviewSectionOutput] = Field(default_factory=list)
    limitations: str = ""
    source_notes: list[str] = Field(default_factory=list)
```

业务层继续做：

```text
section_sources 校验
ReportService 保存
traceability
```

### 14.4 Innovation 接入

新增 schema：

```python
class InnovationCandidateOutput(BaseModel):
    name: str
    description: str = ""
    source_signal_ids: list[str] = Field(default_factory=list)
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    limiting_evidence_ids: list[str] = Field(default_factory=list)
    graph_node_ids: list[str] = Field(default_factory=list)
    why_innovative: str = ""
    research_foundation: str = ""
    gap: str = ""
    feasibility: str = ""
    risk: str = ""
    possible_topic: str = ""
    evidence_status: str = "supported"
    uncertainty: str = ""

class InnovationGenerationOutput(BaseModel):
    innovation_points: list[InnovationCandidateOutput] = Field(default_factory=list)
```

业务层继续做：

```text
source_signal 校验
evidence_id ScopeGuard
generic filter
scoring
```

## 15. Fake LLM 与测试工具

### 15.1 FakeLLMService

统一测试工具：

```python
class FakeLLMService:
    def __init__(self, responses: list[str | dict[str, Any]]):
        self.responses = responses
        self.calls = []

    def invoke(self, system_prompt: str, user_prompt: str) -> str:
        ...

    def invoke_json(self, system_prompt: str, user_prompt: str, **kwargs) -> dict[str, Any]:
        ...

    def invoke_structured(self, system_prompt, user_prompt, schema, **kwargs):
        ...
```

用途：

```text
不访问真实 API。
断言 prompt_name/prompt_version。
模拟 provider_error。
模拟 invalid JSON。
模拟 schema error。
模拟 repair success。
```

### 15.2 fixture 建议

```text
fake_llm_success
fake_llm_invalid_json
fake_llm_schema_error
fake_llm_timeout
fake_llm_rate_limited
fake_llm_repair_success
```

### 15.3 测试不要做的事

```text
不要在单元测试中调用真实 LLM。
不要依赖具体模型自然语言输出。
不要断言完整 prompt 文本，只断言关键规则存在。
不要把 API key 写入测试 fixture。
```

## 16. API 与配置

### 16.1 环境变量

当前支持：

```text
OPENAI_API_KEY
OPENAI_BASE_URL
```

建议补充：

```text
RW_LLM_PROVIDER
RW_LLM_MODEL
RW_LLM_TEMPERATURE
RW_LLM_MAX_TOKENS
RW_LLM_TIMEOUT
RW_LLM_MAX_RETRIES
RW_LLM_LOG_LEVEL
RW_LLM_DISABLE_REAL_CALLS_FOR_TESTS
```

### 16.2 配置优先级

```text
显式 LLMConfig
  > task route config
  > environment variables
  > default config
```

### 16.3 测试环境保护

建议：

```text
如果 PYTEST_CURRENT_TEST 存在且未显式 allow_real_llm=True，则真实 LLM 调用抛错。
```

或更保守：

```text
只在 FakeLLM 注入路径做单元测试，不在 LLMService 内判断 pytest。
```

推荐第二种，避免生产逻辑耦合测试环境。

## 17. 开发阶段

### L0：兼容和安全基线

目标：不破坏现有业务模块，同时消除最危险的伪成功。

任务：

```text
T13.0.1 增加 LLMServiceError、JsonExtractionError、StructuredOutputError。
T13.0.2 增加 extract_json(text)。
T13.0.3 invoke_json 增加 strict 参数，默认 strict=True。
T13.0.4 JSON 解析失败抛 JsonExtractionError，不再默认返回 raw_response。
T13.0.5 现有业务模块捕获异常后进入 fallback。
T13.0.6 增加 test_llm_json_extract.py。
```

验收：

```text
fenced JSON 可解析。
自然语言包裹 JSON 可解析。
无效 JSON 会抛可控错误。
PaperCard/QA/Review/Innovation 仍能 fallback。
```

### L1：配置、timeout、retry 和调用结果

目标：让 provider 调用可控、可观测。

任务：

```text
T13.1.1 LLMConfig 增加 timeout/request_timeout/max_retries/retry_backoff_seconds。
T13.1.2 _create_llm 传入 timeout 和 max_retries。
T13.1.3 invoke_raw 返回 LLMCallResult。
T13.1.4 invoke 保持返回 str 兼容，但内部记录 LLMCallResult。
T13.1.5 识别 timeout/rate limit/provider error。
T13.1.6 记录 latency_ms。
```

验收：

```text
LLMConfig 可设置 timeout/max_retries。
provider 异常被映射为稳定 error_type。
调用结果包含 latency 和 model。
```

### L2：结构化输出

目标：统一 Pydantic schema 调用。

任务：

```text
T13.2.1 新增 StructuredLLMResult。
T13.2.2 新增 invoke_structured(schema)。
T13.2.3 schema validation error 转 StructuredOutputError。
T13.2.4 支持 schema_json 注入 Prompt。
T13.2.5 PaperCard 先接入 invoke_structured。
T13.2.6 增加 test_llm_structured_output.py。
```

验收：

```text
合法 JSON -> Pydantic 对象。
缺字段按 schema 默认值处理。
类型错误抛 StructuredOutputError。
PaperCard 结构化抽取路径可测试。
```

### L3：Repair

目标：提高结构化输出成功率，但不新增事实。

任务：

```text
T13.3.1 新增 JsonRepairer。
T13.3.2 新增 repair prompt。
T13.3.3 invoke_structured 在 parse/schema 失败后 repair 一次。
T13.3.4 repair 后再次 schema 校验。
T13.3.5 repair 失败抛 JsonRepairError 或 StructuredOutputError。
T13.3.6 增加 repair tests。
```

验收：

```text
尾逗号、fenced block、轻微格式错误可修复。
repair 不会新增不存在的 evidence_id。
repair 失败进入业务 fallback。
```

### L4：PromptRegistry

目标：Prompt 从模块常量迁移到可版本管理的 registry。

任务：

```text
T13.4.1 新增 PromptTemplateSpec。
T13.4.2 新增 PromptRegistry。
T13.4.3 迁移 PaperCard prompt。
T13.4.4 迁移 ScopeQA prompt。
T13.4.5 迁移 Review prompt。
T13.4.6 迁移 Innovation prompt。
T13.4.7 增加 prompt golden tests。
```

验收：

```text
每个 prompt 有 name/version/module。
业务模块保存 prompt_version。
Prompt 变更有测试覆盖。
```

### L5：日志脱敏和指标

目标：能定位问题，同时不泄露数据。

任务：

```text
T13.5.1 新增 LLMRedactor。
T13.5.2 LLM 调用日志只记录 hash/长度/指标。
T13.5.3 记录 provider/model/prompt/latency/retry/status。
T13.5.4 尝试读取 token usage。
T13.5.5 增加 redaction tests。
T13.5.6 与 15 评估日志模块指标对齐。
```

验收：

```text
日志不含 API key。
日志不含完整 prompt。
日志不含完整 response。
日志包含 latency/model/status。
```

### L6：模块全面接入

目标：所有生成模块统一结构化输出。

任务：

```text
T13.6.1 ScopeQA 接入 ScopeQAOutput。
T13.6.2 Review 接入 ReviewGenerationOutput。
T13.6.3 Innovation 接入 InnovationGenerationOutput。
T13.6.4 所有模块写入 generation metadata。
T13.6.5 所有模块使用 FakeLLM 测试。
T13.6.6 移除对 raw_response 的依赖。
```

验收：

```text
QA/Review/Innovation 结构化输出有 schema 测试。
JSON 失败不会生成越界引用。
业务 fallback 路径稳定。
```

### L7：模型路由和预算

目标：降低成本，提高长上下文任务稳定性。

任务：

```text
T13.7.1 新增 ModelRouter。
T13.7.2 按 task_type 选择 temperature/max_tokens。
T13.7.3 新增 TokenBudgetEstimator。
T13.7.4 业务模块调用前检查 prompt budget。
T13.7.5 记录 estimated tokens。
```

验收：

```text
paper_card/review/innovation 可使用不同 route。
超预算 prompt 能被识别。
日志中有 token 估算或 usage。
```

### L8：高级能力

目标：后续增强。

任务：

```text
T13.8.1 provider-native structured output adapter。
T13.8.2 streaming invoke。
T13.8.3 batch invoke。
T13.8.4 rate limiter。
T13.8.5 OpenTelemetry adapter。
T13.8.6 prompt experiment registry。
```

## 18. 测试计划

### 18.1 测试文件

```text
tests/agents_v3/research_workspace/test_llm_service.py
tests/agents_v3/research_workspace/test_llm_json_extract.py
tests/agents_v3/research_workspace/test_llm_structured_output.py
tests/agents_v3/research_workspace/test_llm_repair.py
tests/agents_v3/research_workspace/test_llm_errors.py
tests/agents_v3/research_workspace/test_llm_logging_redaction.py
tests/agents_v3/research_workspace/test_prompt_registry.py
tests/agents_v3/research_workspace/test_prompt_schema_paper_card.py
tests/agents_v3/research_workspace/test_prompt_schema_qa.py
tests/agents_v3/research_workspace/test_prompt_schema_review.py
tests/agents_v3/research_workspace/test_prompt_schema_innovation.py
```

### 18.2 JSON 提取测试

```text
test_extract_plain_object
test_extract_plain_array
test_extract_json_fenced_block
test_extract_plain_fenced_block
test_extract_object_with_prefix_suffix
test_extract_array_with_prefix_suffix
test_extract_invalid_raises_json_extraction_error
test_extract_multiple_blocks_prefers_json_block
```

### 18.3 结构化输出测试

```text
test_invoke_structured_returns_pydantic_model
test_invoke_structured_applies_schema_defaults
test_invoke_structured_type_error_raises
test_invoke_structured_records_prompt_metadata
test_invoke_structured_repair_success
test_invoke_structured_repair_failure_raises
```

### 18.4 错误和 fallback 测试

```text
test_provider_error_maps_to_llm_provider_error
test_timeout_maps_to_timeout_error
test_empty_response_raises_empty_response_error
test_invoke_json_strict_raises_on_invalid_json
test_invoke_json_non_strict_returns_parse_error_marker
```

业务模块：

```text
test_paper_card_llm_schema_failure_uses_fallback
test_scope_qa_json_failure_uses_fallback
test_review_schema_failure_uses_fallback
test_innovation_schema_failure_uses_fallback
```

### 18.5 日志脱敏测试

```text
test_redactor_removes_api_key
test_redactor_truncates_long_prompt
test_llm_log_does_not_include_full_prompt
test_llm_log_does_not_include_full_response
test_llm_log_contains_latency_model_status
test_error_message_is_redacted
```

### 18.6 Prompt Registry 测试

```text
test_prompt_registry_get_by_name
test_prompt_registry_get_latest_version
test_prompt_has_required_rules
test_prompt_declares_output_schema
test_prompt_version_recorded_in_result
```

## 19. 验收标准

### 19.1 功能验收

```text
LLMConfig 支持 timeout/max_retries。
invoke_json 解析失败不会伪成功。
extract_json 支持常见 JSON 输出形式。
invoke_structured 能返回 Pydantic typed result。
repair 能处理常见格式错误。
Prompt 有 name/version/module。
LLMCallResult 记录基础指标。
FakeLLM 可以覆盖成功、失败、repair 场景。
```

### 19.2 质量验收

```text
所有关键结构化 LLM 输出经过 schema 校验。
所有业务模块有 fallback 路径。
JSON parse failure 有测试覆盖。
schema validation failure 有测试覆盖。
日志不泄露 API key、完整 prompt 和完整 response。
prompt 版本可追踪。
```

### 19.3 工程验收

```text
现有生成模块不因 LLMService 改造而整体失效。
旧 invoke_json 调用有兼容策略。
新增测试不访问真实 LLM API。
LLM 错误类型稳定。
日志字段可供 15 评估日志模块统计。
```

## 20. 最小实现顺序

建议按以下顺序推进：

```text
1. 新增 llm_errors.py 和 llm_json.py。
2. 实现 extract_json，并补测试。
3. invoke_json 增加 strict 参数，默认逐步切到 strict=True。
4. 新增 LLMCallResult 和基础 latency/error logging。
5. 新增 invoke_structured(schema)。
6. 把 PaperCard 接入 invoke_structured。
7. 增加 JsonRepairer。
8. 增加 LLMRedactor 和日志脱敏测试。
9. 迁移 Prompt 到 PromptRegistry。
10. 再接入 QA/Review/Innovation。
```

优先级：

```text
P0：JSON 解析安全、schema 调用、错误类型、FakeLLM。
P1：PromptRegistry、日志指标、repair、模块全面接入。
P2：模型路由、token budget、native structured output、观测平台。
```

## 21. 风险与应对

| 风险 | 表现 | 应对 |
| --- | --- | --- |
| 改造 invoke_json 破坏现有模块 | 旧代码依赖 raw_response | 增加 strict 参数和分阶段迁移 |
| repair 编造内容 | 修复时补出不存在 ID | repair prompt 禁止新增事实，业务层再校验 ID |
| PromptRegistry 增加复杂度 | 小项目维护成本上升 | P0 先保留常量，P1 再迁移 |
| 日志泄露用户材料 | prompt/chunk 写入日志 | Redactor + 日志测试 |
| schema 过严导致频繁 fallback | 模型输出小偏差即失败 | 合理默认值 + 一次 repair |
| 单例污染测试 | get_llm_service 复用旧 config | 测试重置单例，P1 支持 force_new/router |
| provider usage 字段不统一 | token 统计缺失 | usage adapter，读不到则估算 |
| 业务校验误放到 LLM 层 | LLM 层过重 | LLM 层只做格式/schema，Scope/quote 仍在业务层 |
| 真实 LLM 测试不稳定 | 单测慢且成本高 | FakeLLM，真实调用只放手动集成测试 |

## 22. 参考文档

本地参考：

```text
docs/research/14-细致开发计划/模块级开发计划/05-论文卡片生成模块.md
docs/research/14-细致开发计划/模块级开发计划/06-证据表模块.md
docs/research/14-细致开发计划/模块级开发计划/09-ScopeQA与RAG模块.md
docs/research/14-细致开发计划/模块级开发计划/10-综述生成模块.md
docs/research/14-细致开发计划/模块级开发计划/11-创新点报告模块.md
docs/research/14-细致开发计划/模块级开发计划/12-报告版本与导出模块.md
docs/research/14-细致开发计划/模块级开发计划/15-评估日志监控模块.md
```

外部参考：

```text
OpenAI Structured Outputs:
https://platform.openai.com/docs/guides/structured-outputs

LangChain Structured Output:
https://python.langchain.com/docs/concepts/structured_outputs/

Pydantic:
https://docs.pydantic.dev/latest/

Instructor:
https://python.useinstructor.com/

OpenTelemetry:
https://opentelemetry.io/docs/
```

## 23. 研究借鉴增强

### 23.1 幻觉检测 Prompt 集成（借鉴 LettuceDetect）

产品方案要求 QA 和报告使用 LettuceDetect 进行 token-level 幻觉检测。LLM 层需要提供集成接口：

```text
1. 在 invoke_structured() 返回后，新增可选的 hallucination_check 参数
2. 如果启用，将 context + response 传入 LettuceDetect 模型
3. 检测结果写入 LLMCallResult：
   - hallucination_tokens: list[int]
   - hallucination_ratio: float
   - supported_ratio: float
4. 业务模块可根据 hallucination_ratio 决定是否提升 uncertainty 或拒答

MVP 降级：
  如果 LettuceDetect 未部署，使用规则检查：
  - 统计 response 中未被 evidence_id 引用的关键断言
  - 计算 citation_coverage
  - citation_coverage < 0.5 视为等效 hallucination_ratio > 0.3
```

### 23.2 Chain of Verification Prompt 模板（借鉴 PapersFlow）

产品方案要求 QA 和创新点使用 Chain of Verification 确保断言有文献支撑。

Prompt 模板设计：

```text
System Prompt 附加指令：
  "在输出 JSON 前，请执行以下验证步骤：
   1. 列出你计划在 answer 中做出的关键声明
   2. 对每个声明，检查是否有对应的 evidence_id 支撑
   3. 对无 evidence 支撑的声明，标记为 unverified
   4. 如果发现与 evidence 矛盾的声明，标记为 contradicted
   5. 在输出中包含 verification_results 字段"

输出 schema 新增：
  "verification_results": [
    {"claim": "声明内容", "status": "supported|unverified|contradicted", "evidence_ids": ["ev1"]}
  ]
```

### 23.3 Review-Revise Prompt 模板（借鉴 GPT-Researcher）

产品方案要求综述和创新点使用 Review-Revise 循环。

Prompt 模板设计：

```text
Writer Prompt（初始生成）：
  "基于以下证据和 Scope，生成 [综述/创新点]..."

Reviewer Prompt（审核）：
  "请审查以下 [综述/创新点]，检查：
   1. 结构完整性：是否覆盖所有必要部分
   2. 证据覆盖：每个结论是否有 evidence_id 支撑
   3. 引用准确性：引用的 evidence_id 是否存在于上下文
   4. 逻辑连贯性：各部分之间是否有逻辑衔接
   5. 泛化表达：是否使用了空泛短语
   输出 JSON：{issues: [{type, description, severity}], overall_quality: 0-1}"

Revisor Prompt（修订）：
  "根据以下审查意见修订 [综述/创新点]：
   审查意见：{reviewer_output}
   原始内容：{original_output}
   修订时保留有效的 evidence_id 引用，修正不准确的引用。"
```

### 23.4 上下文压缩 Prompt（借鉴 GPT-Researcher）

大范围论文（>20 篇）的 prompt 可能超出 token 限制。需要压缩策略：

```text
分层压缩策略：
  - L0 元数据：始终包含（论文标题、作者、年份）
  - L1 摘要：大范围时用摘要替代 PaperCard 全文
  - L2 PaperCard：中等范围
  - L3 EvidenceRecord：精确问答
  - L4 source_quote：深度引用

压缩 prompt 模板：
  "以下是 {n} 篇论文的证据摘要。请按主题分组总结关键发现、方法和局限。
   每组保留最相关的 {top_k} 条证据的完整信息，其余用一句话概括。
   输出格式：{groups: [{topic, key_findings, key_limitations, top_evidence_ids}]}"
```

### 23.5 H/V Ratio 记录（借鉴 Atlas）

产品方案要求将 H/V ratio 作为质量指标。LLM 层需要支持记录：

```text
LLMCallResult 新增字段：
  - h_v_ratio: float | None — 幻觉/验证比（由业务层计算后回写）
  - verification_score: float | None — 已验证声明占比

记录位置：
  - QA history
  - Report metadata
  - evaluation metrics

目标：
  - h_v_ratio < 0.1（优秀）
  - h_v_ratio < 0.2（可接受）
  - h_v_ratio >= 0.3（需要 Review-Revise）
```

### 23.6 透明报告元数据（借鉴 PRISMA-trAIce）

产品方案要求记录透明元数据。LLM 层需要提供：

```text
每次 LLM 调用记录（已有 LLMCallResult）：
  - model_name / provider
  - prompt_name / prompt_version / prompt_hash
  - latency_ms / token_usage
  - success / error_type / error_message
  - repair_count / generation_mode

新增记录：
  - hallucination_check: LettuceDetect 检测结果
  - verification_result: CoVe 验证结果
  - h_v_ratio: 幻觉/验证比
  - context_compression: 是否使用了上下文压缩
  - few_shot_examples: 使用的 Few-Shot 示例数量

汇总到 Report.metadata.transparency：
  - total_llm_calls: 总 LLM 调用次数
  - total_repair_count: 总修复次数
  - avg_h_v_ratio: 平均幻觉/验证比
  - model_info: 使用的模型和参数
```

## 当前代码对齐深化（2026-06-01）

### 当前实现确认

```text
llm/ 子包已实现：
  - service.py（219 行）：LLMService（invoke/invoke_json/invoke_structured）、FakeLLMService、LLMConfig、LLMCallResult
  - errors.py：8 种错误类型（LLMServiceError/LLMProviderError/LLMTimeoutError/LLMRateLimitError/EmptyLLMResponseError/JsonExtractionError/StructuredOutputError/JsonRepairError）
  - json_utils.py：extract_json（direct/markdown/surrounding text）+ _try_fix_json + repair_json_with_llm
  - prompts.py：PromptTemplateSpec + PromptRegistry + 4 个内置 prompt（paper_card/scope_qa/review/innovation）
  - logging.py：redact_text + hash_text + log_llm_call

invoke_structured 已实现：JSON 提取 → schema 校验 → repair → 日志记录。
FakeLLMService 已支持测试注入。
PromptRegistry 已支持 prompt name/version/module/schema。
```

### 与产品方案的 Gap 分析

| 产品方案要求 | 代码现状 | Gap 严重度 |
| --- | --- | --- |
| LettuceDetect 幻觉检测集成 | 未实现 | 高（QA/报告可信度） |
| Chain of Verification prompt 模板 | 未实现 | 高（声明验证） |
| Review-Revise prompt 模板 | 未实现 | 中（综述/创新点质量） |
| Few-Shot 示例管理 | 未实现 | 中（prompt 质量） |
| CoT (Chain of Thought) 模板 | 未实现 | 中（复杂推理） |
| 上下文压缩 prompt | 未实现 | 中（大范围论文） |
| H/V ratio 记录到 LLMCallResult | 未实现 | 中（质量监控） |
| Token budget 估算 | 未实现 | 中（token 控制） |
| ModelRouter 任务路由 | 未实现 | 低（优化成本） |
| Prompt Golden Tests 自动回归 | 未实现 | 中（prompt 稳定性） |
| JSON 降级策略文档化 | 已有基础实现 | ⚠️ 部分对齐 |
| 透明报告元数据 | 已有 LLMCallResult 基础字段 | ⚠️ 部分对齐 |

### 下一步深化任务

```text
优先级 P0（阻塞 QA/报告质量）：
1. 全量调用方迁移到 invoke_structured：PaperCard、ScopeQA、Review、Innovation 都必须传入明确 Pydantic schema
2. PromptRegistry 成为唯一 prompt 入口，prompt version 写入 PaperCard/Report/QA 日志
3. 结构化输出失败分层处理：empty response → JSON extraction → repair → schema validation → provider timeout → rate limit
4. LLM logging 默认 redaction/hash，不保存完整论文正文和用户问题原文

优先级 P1（增强 prompt 质量）：
5. 实现 Few-Shot 示例管理：PromptTemplateSpec.few_shot_examples + 示例文件存储
6. 实现 Chain of Verification prompt 模板（QA 和创新点专用）
7. 实现 Review-Revise prompt 模板（综述和创新点专用）
8. 实现 CoT 推理指令（复杂任务附加）
9. 实现 H/V ratio 字段到 LLMCallResult

优先级 P2（高级能力）：
10. 实现 Token budget 估算（estimate_tokens + check_budget）
11. 实现 ModelRouter 任务路由
12. 实现上下文压缩 prompt
13. 实现 Prompt Golden Tests 自动回归
14. 集成 LettuceDetect 幻觉检测
```

### 验收证据

```text
pytest tests/agents_v3/research_workspace/test_llm_service.py 通过。
PaperCard/QA/Review/Innovation 的测试均可用 FakeLLMService 注入，无需真实 API key。
新增测试覆盖：
  - prompt version 落库
  - schema validation error
  - redaction 不泄露长文本
  - Few-Shot 示例正确注入
  - CoVe prompt 模板生成正确
  - Review-Revise prompt 模板生成正确
  - H/V ratio 记录正确
```

### 风险与阻塞

```text
如果不同模块继续各自拼 prompt 和解析 JSON，后续评估无法判断失败来自 prompt、模型还是 schema。
日志中保存完整论文文本有隐私与体积风险，默认必须截断、脱敏或哈希。
LettuceDetect 集成需要额外依赖（transformers + torch），MVP 可先用规则降级。
Few-Shot 示例需要持续维护，过时的示例可能导致模型输出退化。
CoT 推理会增加 token 消耗，需要在质量和成本之间权衡。
```
