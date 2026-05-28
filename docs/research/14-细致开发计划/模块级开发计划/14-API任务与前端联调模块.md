# API 任务与前端联调模块专项开发计划

更新时间：2026-05-28

API 任务与前端联调模块负责把 v3 `research_workspace` 的 service 能力暴露为稳定、可测试、可前端集成的本地 API，同时补齐长任务状态、任务事件、统一错误结构、演示 pipeline、OpenAPI 契约和前端页面数据流。它不是把 service 方法简单套一层 HTTP，而是后端 service 与前端研究工作台之间的产品契约层。

对应现有代码：

```text
src/agents_v3/research_workspace/
src/agents_v2/api/
pyproject.toml
docs/getting-started/frontend-overview.md
```

建议新增：

```text
src/agents_v3/research_workspace/api.py
src/agents_v3/research_workspace/api_models.py
src/agents_v3/research_workspace/api_errors.py
src/agents_v3/research_workspace/api_deps.py
src/agents_v3/research_workspace/task_service.py
src/agents_v3/research_workspace/task_runner.py
src/agents_v3/research_workspace/task_events.py
src/agents_v3/research_workspace/demo_pipeline.py
tests/agents_v3/research_workspace/test_api_projects.py
tests/agents_v3/research_workspace/test_api_papers.py
tests/agents_v3/research_workspace/test_api_tasks.py
tests/agents_v3/research_workspace/test_api_scope_qa.py
tests/agents_v3/research_workspace/test_api_reports.py
tests/agents_v3/research_workspace/test_demo_pipeline.py
```

## 1. 模块定位

### 1.1 在产品链路中的位置

API 与任务模块位于 service 层之上、前端 UI 之下：

```text
Frontend Research Workspace
  -> API Client / Zustand stores
  -> FastAPI /api/rw
  -> TaskService / TaskRunner / EventBus
  -> research_workspace services
  -> JSONStorage / files / LLM / search sources
```

它要把以下能力连接起来：

```text
项目管理
论文搜索和导入
PDF 上传、解析和分块
论文卡片生成
证据表生成
知识图谱构建和查询
RetrievalScope 解析
Scope QA
综述生成
创新点报告
报告版本、校验和导出
任务进度和事件
```

### 1.2 本模块负责什么

```text
FastAPI app/router
Pydantic request/response DTO
统一 API response 和 error contract
TaskService 持久化任务状态
TaskRunner 执行长任务
任务轮询和事件流
demo pipeline
OpenAPI 文档和前端类型生成准备
前端页面数据契约
本地安全策略：API key、CORS、上传限制、路径隔离
API 集成测试
```

### 1.3 本模块不负责什么

```text
重新实现搜索、解析、卡片、证据、图谱、QA、报告逻辑
替代各 service 的业务校验
复杂分布式任务队列
多用户权限系统
完整云端部署体系
前端页面具体 UI 实现
```

### 1.4 核心原则

```text
1. 前端只依赖 API contract，不直接读 JSONStorage。
2. 短操作同步返回，长操作返回 task_id。
3. 所有错误使用统一结构。
4. 所有长任务可轮询进度，P1 再支持 SSE。
5. API DTO 与内部模型可以相似，但不要把内部存储细节直接暴露为唯一契约。
6. demo pipeline 必须可重复运行，便于端到端 smoke test。
7. 单元测试和 API 测试不能依赖真实 LLM 或外部搜索源。
```

## 2. 本地调研结论落地

### 2.1 模块总览要求

`00-模块总览与依赖关系.md` 要求 v3 形成从项目创建到报告导出的闭环：

```text
Project
  -> Paper Library
  -> Parse
  -> PaperCard
  -> Evidence
  -> Graph
  -> ScopeQA
  -> Review / Innovation
  -> Report Export
```

对 API 模块的落地要求：

| 闭环步骤 | API 能力 |
| --- | --- |
| 创建项目 | `POST /projects` |
| 搜索/导入论文 | `POST /papers/search`、`POST /papers/search/commit` |
| PDF 上传解析 | `POST /papers/upload`、`POST /papers/{paper_id}/parse` |
| 批量生成卡片 | `POST /projects/{project_id}/cards` |
| 构建证据表 | `POST /projects/{project_id}/evidence/build` |
| 构建图谱 | `POST /projects/{project_id}/graph/build` |
| Scope QA | `POST /projects/{project_id}/qa` |
| 生成报告 | `POST /projects/{project_id}/reports/literature-review`、`/innovation` |
| 导出报告 | `GET /reports/{report_id}/export/markdown`、`/json` |

### 2.2 当前 v3 service 能力

当前已有 service：

```text
ProjectService
PaperLibraryService
ParserService
PaperCardGenerator
EvidenceTableService
GraphService
RetrievalScopeService
ScopeQAService
LiteratureReviewGenerator
InnovationReportGenerator
ReportService
LLMService
```

API 层要做的是编排和封装，而不是复制业务逻辑。

### 2.3 v2 API 可借鉴资产

`src/agents_v2/api` 已有：

```text
api_server.py
paper_api.py
reports_api.py
knowledge_graph_api.py
workflow_api.py
sse_helper.py
gateway.py
```

可借鉴：

```text
request_id 日志中间件
API key header
health endpoint
SSE event 格式
任务/工作流概念
报告接口分组
```

不建议照搬：

```text
aiohttp 作为 v3 主框架
内存全局存储
success/error 混杂响应
HTML 手写 docs 页面
业务逻辑直接写在 handler 中
```

v3 推荐使用 FastAPI，原因：

```text
pyproject.toml 已把 fastapi/uvicorn 放入 optional api。
Pydantic 模型可直接生成 OpenAPI。
前端可基于 OpenAPI 生成 TypeScript 类型。
依赖注入和测试客户端更适合当前模块化 service。
```

### 2.4 前端现状和约束

`docs/getting-started/frontend-overview.md` 描述的前端技术栈：

```text
React 18 + Vite
Ant Design 5
Zustand
React Router 6
axios
AntV G6
react-markdown
```

当前仓库根目录没有看到 `frontend/` 实体目录，因此本模块先提供：

```text
API contract
前端页面数据结构
store 设计建议
联调流程
测试验收标准
```

不直接修改前端代码。

### 2.5 相关模块对 API 的要求

| 模块 | 对 API 的要求 |
| --- | --- |
| 03 搜索模块 | 搜索预览、commit 入库、任务进度、来源错误展示 |
| 04 PDF 解析 | 上传、解析、parse result、质量 flags |
| 05 论文卡片 | 单篇/批量生成、卡片质量、source spans |
| 06 证据表 | evidence 列表、筛选、review status、导出 |
| 07 知识图谱 | 图谱构建、节点/边查询、子图、来源 evidence |
| 08 RetrievalScope | scope resolve、filters、preview |
| 09 ScopeQA | 问答、引用、history、suggested actions |
| 10 综述生成 | 长任务生成、报告保存、来源索引 |
| 11 创新点报告 | 候选预览、生成、评分、接受/拒绝 |
| 12 报告版本导出 | 报告列表、详情、版本、校验、导出 |
| 13 LLM | 错误结构、模型调用失败、日志脱敏 |
| 15 评估日志 | task/log/evaluation API、quality gate |

## 3. 主流 API 和任务做法

### 3.1 FastAPI / OpenAPI

可借鉴做法：

```text
Pydantic request/response model
dependency injection
middleware request_id
exception handler
OpenAPI docs
TestClient / AsyncClient
```

本项目落地：

```text
api_models.py 定义所有 DTO。
api_errors.py 定义统一错误。
api_deps.py 管理 storage/service 依赖。
api.py 注册 router。
```

### 3.2 长任务系统

类似 Celery/RQ 的任务状态：

```text
queued
running
succeeded
failed
cancelled
```

本项目 P0 不引入 Celery/RQ，采用：

```text
JSONStorage TaskService
FastAPI BackgroundTasks 或 asyncio.to_thread
任务轮询
```

P1 再增强：

```text
SSE event stream
cancel token
retry
resume checkpoints
```

### 3.3 SSE / WebSocket

v2 已有 SSE helper，可借鉴事件格式：

```text
event: task_progress
data: {...}
```

本项目选择：

```text
P0 polling。
P1 SSE。
P2 如需要再考虑 WebSocket。
```

原因：

```text
轮询易测试、易实现、足够支持 MVP。
SSE 单向推送适合任务进度和生成过程。
WebSocket 对当前本地研究工作台不是必要复杂度。
```

### 3.4 前端状态管理

前端应把 API 数据分成领域 store：

```text
projectStore
paperStore
taskStore
graphStore
qaStore
reportStore
uiStore
```

不要让单个 store 承载所有数据；任务状态应由 `taskStore` 统一管理，页面只订阅相关 task。

## 4. 当前实现分析

### 4.1 当前已有后端服务

```text
project_service.py
paper_library.py
parser_service.py
paper_card.py
evidence_table.py
graph_service.py
scope.py
scope_qa.py
review_generator.py
innovation_generator.py
report_service.py
llm_service.py
```

这些 service 大多是同步方法，API 层需要处理：

```text
同步调用封装。
长任务后台执行。
错误转换为 APIError。
序列化为 Pydantic response。
```

### 4.2 当前数据模型

已有核心模型：

```text
Project
Paper
PaperStatus
ParseResult
PaperChunk
PaperCard
EvidenceRecord
KnowledgeGraph
RetrievalScope
QARequest
QAResponse
Report
ReportVersion
```

缺少 API/任务模型：

```text
ApiResponse
ApiError
PageRequest
PageResponse
WorkspaceTask
TaskEvent
TaskStatus
TaskType
ProjectStatsDTO
HealthDTO
ReportDetailDTO
GraphDTO
```

### 4.3 当前技术栈状态

`pyproject.toml`：

```text
Python >= 3.11
pydantic >= 2.5
httpx >= 0.27
aiohttp >= 3.8
fastapi >= 0.110 optional api
uvicorn >= 0.27 optional api
pytest >= 8.0
pytest-asyncio >= 0.24
```

建议 v3 API 使用：

```text
FastAPI
Pydantic v2
JSONStorage
BackgroundTasks / asyncio.to_thread
httpx AsyncClient for tests
```

### 4.4 当前主要缺口

| 领域 | 当前状态 | 问题 | 优先级 |
| --- | --- | --- | --- |
| v3 API | 无统一 app/router | 前端无法调用 v3 service | P0 |
| DTO | 无 `api_models.py` | OpenAPI 和前端类型无法稳定 | P0 |
| 长任务 | 无 `TaskService` | 批量解析/报告生成无法展示进度 | P0 |
| 任务事件 | 无 event model | 前端不能展示 pipeline 步骤 | P0 |
| 错误结构 | service 返回 None/异常/对象混杂 | 前端错误处理困难 | P0 |
| 搜索 commit | search 和 import 契约未统一 | 搜索结果暂存和入库流程不清 | P0 |
| 文件上传 | 无 API 限制 | 路径穿越和大文件风险 | P0 |
| Scope preview | 无 API DTO | 前端无法构建范围选择器 | P0 |
| 报告详情 | ReportService 基础 | 缺 source_index/validation DTO | P1 |
| SSE | v3 无 | 长任务体验弱 | P1 |
| OpenAPI 类型生成 | 无 | 前端手写类型易漂移 | P1 |
| 鉴权/CORS | 未定义 | 本地 MVP 也需最小安全边界 | P1 |
| demo pipeline | 无 | 无法端到端联调和演示 | P0 |
| 取消/重试 | 无 | 长任务失败恢复弱 | P1 |

## 5. 目标与边界

### 5.1 一句话目标

提供一个能跑通 v3 research workspace 闭环的本地 API、任务系统和前端数据契约，让论文库、知识图谱、Scope QA、成果报告四个核心页面可以稳定联调。

### 5.2 MVP 成功标准

```text
1. 新增 FastAPI app，统一前缀 /api/rw。
2. Project/Paper/Search/Parse/Card/Evidence/Graph/Scope/QA/Report/Task API 有 Pydantic DTO。
3. 批量解析、批量卡片、证据构建、图谱构建、报告生成返回 task_id。
4. TaskService 支持 create/start/update_progress/succeed/fail/cancel/get/list/events。
5. P0 支持任务轮询。
6. API 错误统一为 {error:{code,message,details,request_id}}。
7. 支持 health/stats/demo pipeline。
8. API 测试能用临时 JSONStorage 和 fake LLM/search，不访问外部服务。
9. OpenAPI docs 可访问。
10. 前端四页有明确数据契约和状态流。
```

### 5.3 非目标

MVP 不做：

```text
1. Celery/RQ/Redis 分布式队列。
2. 完整多用户权限系统。
3. 云端文件对象存储。
4. WebSocket 双向协同。
5. 前端完整 UI 实现。
6. 生产级部署、监控、限流网关。
7. 在线支付、账号体系、团队协作。
```

P2 可扩展：

```text
Redis/Celery
WebSocket
OpenAPI TypeScript 自动生成
API key 管理页面
导出文件下载缓存
任务恢复和断点续跑
```

## 6. 目标架构

### 6.1 后端组件

```text
api.py
  FastAPI app、router、middleware、exception handler。

api_models.py
  所有 request/response DTO。

api_errors.py
  APIError、error code、异常映射。

api_deps.py
  storage、service factory、request context、settings。

task_service.py
  持久化 WorkspaceTask 和 TaskEvent。

task_runner.py
  执行长任务，更新进度，捕获错误。

task_events.py
  EventBus、SSE 格式、事件订阅。

demo_pipeline.py
  创建演示项目并跑通最小流程。
```

### 6.2 API 调用链

短操作：

```text
HTTP request
  -> FastAPI router
  -> validate request DTO
  -> service method
  -> response DTO
  -> ApiResponse
```

长操作：

```text
HTTP request
  -> create task
  -> return task_id immediately
  -> TaskRunner background execution
  -> update task progress/events
  -> frontend polls /tasks/{task_id}
```

P1 SSE：

```text
frontend EventSource
  -> GET /tasks/{task_id}/events
  -> task event stream
```

### 6.3 服务依赖注入

```python
def get_storage() -> JSONStorage: ...
def get_project_service(storage=Depends(...)) -> ProjectService: ...
def get_task_service(storage=Depends(...)) -> TaskService: ...
```

测试时：

```text
override dependency -> temp JSONStorage
override LLMService -> FakeLLMService
override search adapters -> FakeSearchAdapter
```

### 6.4 执行模式

P0 支持两种模式：

```text
run_inline=true
  测试和调试使用，同步执行任务，直接得到 succeeded/failed 状态。

run_inline=false
  API 默认，返回 task_id，后台执行。
```

长任务执行方式：

```text
FastAPI BackgroundTasks for simple P0.
asyncio.to_thread for blocking service method.
P1 再抽象为 TaskRunner queue。
```

## 7. API 基础契约

### 7.1 统一成功响应

```json
{
  "data": {},
  "meta": {
    "request_id": "req_abc123",
    "timestamp": "2026-05-28T10:00:00",
    "duration_ms": 23
  }
}
```

列表响应：

```json
{
  "data": [],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 100,
    "has_next": true
  },
  "meta": {
    "request_id": "req_abc123"
  }
}
```

### 7.2 统一错误响应

```json
{
  "error": {
    "code": "paper_not_found",
    "message": "Paper not found",
    "details": {
      "paper_id": "paper_xxx"
    },
    "request_id": "req_abc123"
  }
}
```

### 7.3 HTTP 状态码

| 场景 | 状态码 |
| --- | --- |
| 成功查询 | 200 |
| 成功创建 | 201 |
| 长任务已创建 | 202 |
| 请求参数错误 | 400 |
| 未认证 | 401 |
| 无权限 | 403 |
| 资源不存在 | 404 |
| 版本冲突/重复导入 | 409 |
| 校验失败 | 422 |
| 依赖缺失 | 424 |
| 外部服务失败 | 502 |
| 任务执行失败 | 500 |

### 7.4 常见错误 code

```text
invalid_request
project_not_found
paper_not_found
report_not_found
task_not_found
scope_empty
scope_violation
validation_failed
dependency_missing
search_failed
parse_failed
llm_failed
json_parse_failed
file_too_large
unsupported_file_type
unsafe_file_path
version_conflict
task_cancelled
task_already_finished
internal_error
```

### 7.5 Request Context

每个请求生成：

```text
request_id
started_at
client_host
user_id optional
api_key_id optional
```

写入：

```text
response meta
error response
logs
task.input.request_id
```

## 8. API 数据模型

### 8.1 基础 DTO

```python
class ApiMeta(BaseModel):
    request_id: str
    timestamp: str
    duration_ms: int = 0

class ApiErrorBody(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    request_id: str = ""

class PageParams(BaseModel):
    page: int = 1
    page_size: int = 20

class PageInfo(BaseModel):
    page: int
    page_size: int
    total: int
    has_next: bool
```

### 8.2 Project DTO

```python
class ProjectCreateRequest(BaseModel):
    name: str
    description: str = ""
    discipline: str = ""
    education_level: str = ""
    research_goal: str = ""

class ProjectUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    discipline: str | None = None
    education_level: str | None = None
    research_goal: str | None = None

class ProjectStatsResponse(BaseModel):
    paper_count: int = 0
    parsed_count: int = 0
    card_count: int = 0
    evidence_count: int = 0
    graph_node_count: int = 0
    report_count: int = 0
    running_task_count: int = 0
```

### 8.3 Paper DTO

```python
class PaperListQuery(BaseModel):
    status: str | None = None
    included: bool | None = None
    source: str | None = None
    year_from: int | None = None
    year_to: int | None = None
    q: str | None = None

class PaperUpdateRequest(BaseModel):
    title: str | None = None
    authors: list[str] | None = None
    year: int | None = None
    venue: str | None = None
    abstract: str | None = None
    included: bool | None = None
    exclude_reason: str | None = None
```

### 8.4 Search DTO

```python
class SearchPapersRequest(BaseModel):
    query: str
    sources: list[str] = Field(default_factory=list)
    limit: int = 20
    year_from: int | None = None
    year_to: int | None = None
    field: str = ""
    use_cache: bool = True
    force_refresh: bool = False

class SearchCommitRequest(BaseModel):
    session_id: str | None = None
    results: list[dict[str, Any]] = Field(default_factory=list)
    selected_result_ids: list[str] = Field(default_factory=list)
```

### 8.5 Task DTO

```python
class TaskCreateResponse(BaseModel):
    task_id: str
    status: str
    task_type: str
    poll_url: str
    events_url: str | None = None

class TaskProgressResponse(BaseModel):
    task_id: str
    project_id: str
    task_type: str
    status: str
    progress: float = 0.0
    current_step: str = ""
    total_items: int = 0
    completed_items: int = 0
    failed_items: int = 0
    output: dict[str, Any] = Field(default_factory=dict)
    error: dict[str, Any] = Field(default_factory=dict)
    checkpoints: list[dict[str, Any]] = Field(default_factory=list)
    created_at: str
    updated_at: str
    finished_at: str = ""
```

### 8.6 Scope 和 QA DTO

```python
class ScopeResolveRequest(BaseModel):
    scope: dict[str, Any] = Field(default_factory=dict)

class ScopeResolveResponse(BaseModel):
    scope: dict[str, Any]
    paper_count: int
    evidence_count: int
    graph_node_count: int
    warnings: list[str] = Field(default_factory=list)

class QARequestDTO(BaseModel):
    question: str
    scope: dict[str, Any] = Field(default_factory=dict)
    options: dict[str, Any] = Field(default_factory=dict)
```

### 8.7 Report DTO

```python
class ReportGenerateRequest(BaseModel):
    scope: dict[str, Any] = Field(default_factory=dict)
    options: dict[str, Any] = Field(default_factory=dict)
    run_inline: bool = False

class ReportDetailResponse(BaseModel):
    report: dict[str, Any]
    source_index: dict[str, Any] = Field(default_factory=dict)
    validation_result: dict[str, Any] = Field(default_factory=dict)
    versions: list[dict[str, Any]] = Field(default_factory=list)
```

## 9. TaskService 设计

### 9.1 WorkspaceTask

```python
class WorkspaceTask(BaseModel):
    task_id: str
    project_id: str
    task_type: str
    status: str = "queued"
    progress: float = 0.0
    current_step: str = ""
    total_items: int = 0
    completed_items: int = 0
    failed_items: int = 0
    input: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] = Field(default_factory=dict)
    checkpoints: list[dict[str, Any]] = Field(default_factory=list)
    error: dict[str, Any] = Field(default_factory=dict)
    cancel_requested: bool = False
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    started_at: str = ""
    finished_at: str = ""
```

### 9.2 TaskEvent

```python
class TaskEvent(BaseModel):
    event_id: str
    task_id: str
    project_id: str
    event_type: str
    sequence: int = 0
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
```

### 9.3 状态机

```text
queued -> running -> succeeded
queued -> running -> failed
queued -> cancelled
running -> cancelling -> cancelled
running -> failed
```

不允许：

```text
succeeded -> running
failed -> running
cancelled -> running
```

重试策略：

```text
P0 不复用同一个 task 重试。
P1 retry_task 创建新 task，并记录 parent_task_id。
```

### 9.4 TaskService 方法

```python
class TaskService:
    def create_task(self, project_id: str, task_type: str, input: dict[str, Any] | None = None) -> WorkspaceTask: ...
    def start(self, task_id: str, step: str = "") -> WorkspaceTask: ...
    def update_progress(self, task_id: str, progress: float, step: str = "", checkpoint: dict[str, Any] | None = None) -> WorkspaceTask: ...
    def increment(self, task_id: str, completed_delta: int = 1, failed_delta: int = 0, step: str = "") -> WorkspaceTask: ...
    def succeed(self, task_id: str, output: dict[str, Any]) -> WorkspaceTask: ...
    def fail(self, task_id: str, code: str, message: str, details: dict[str, Any] | None = None) -> WorkspaceTask: ...
    def request_cancel(self, task_id: str) -> WorkspaceTask: ...
    def cancel(self, task_id: str, reason: str = "") -> WorkspaceTask: ...
    def get_task(self, task_id: str) -> WorkspaceTask | None: ...
    def list_tasks(self, project_id: str, status: str | None = None) -> list[WorkspaceTask]: ...
    def append_event(self, task_id: str, event_type: str, payload: dict[str, Any]) -> TaskEvent: ...
    def list_events(self, task_id: str, after_sequence: int | None = None) -> list[TaskEvent]: ...
```

### 9.5 任务类型

```text
search_papers
commit_search_results
upload_paper
parse_paper
parse_project
generate_card
generate_cards
build_evidence
build_graph
resolve_scope
scope_qa
generate_review
generate_innovation
validate_report
export_report
demo_pipeline
```

### 9.6 进度规则

批量任务：

```text
progress = completed_items / total_items
```

多阶段任务：

```text
search 10%
import 20%
parse 40%
card 60%
evidence 75%
graph 90%
reports 100%
```

报告生成：

```text
resolve scope 15%
collect materials 35%
generate content 70%
validate/save 90%
done 100%
```

### 9.7 取消语义

P0：

```text
cancel_requested=true。
长循环任务在每个 item 之间检查。
正在执行的单个 blocking service 不强杀。
```

P1：

```text
TaskRunner cancel token。
可取消 search/parse batch/report generation。
```

## 10. API 详细规划

### 10.1 系统接口

```text
GET /api/rw/health
GET /api/rw/version
GET /api/rw/openapi.json
```

Health 响应：

```json
{
  "status": "healthy",
  "components": {
    "storage": "ok",
    "llm": "configured",
    "search": "partial",
    "api": "ok"
  },
  "version": "v3",
  "timestamp": "..."
}
```

### 10.2 项目接口

```text
POST   /api/rw/projects
GET    /api/rw/projects
GET    /api/rw/projects/{project_id}
PATCH  /api/rw/projects/{project_id}
DELETE /api/rw/projects/{project_id}?cascade=false
GET    /api/rw/projects/{project_id}/stats
GET    /api/rw/projects/{project_id}/health
POST   /api/rw/projects/demo
```

`project health` 返回：

```text
papers_ready
parse_ready
cards_ready
evidence_ready
graph_ready
reports_ready
blocking_issues
suggested_actions
```

### 10.3 论文搜索和导入接口

```text
POST /api/rw/projects/{project_id}/papers/search
POST /api/rw/projects/{project_id}/papers/search/commit
GET  /api/rw/projects/{project_id}/search/sessions
GET  /api/rw/search/sessions/{session_id}
```

策略：

```text
search 只返回预览结果，不直接入库。
commit 才把用户选择的结果导入 papers。
如果用户 options.auto_commit=true，可搜索后直接入库。
```

搜索响应：

```json
{
  "session_id": "search_xxx",
  "query": {},
  "results": [],
  "source_stats": {},
  "dedup_summary": {},
  "errors": [],
  "cache_hit": false
}
```

长任务：

```text
多源搜索可能慢，默认返回 task_id。
limit <= 20 且 sources 少时可支持 run_inline=true。
```

### 10.4 论文库接口

```text
GET   /api/rw/projects/{project_id}/papers
GET   /api/rw/papers/{paper_id}
PATCH /api/rw/papers/{paper_id}
POST  /api/rw/papers/{paper_id}/include
POST  /api/rw/papers/{paper_id}/exclude
DELETE /api/rw/papers/{paper_id}
```

列表支持：

```text
page/page_size
status
included
source
year_from/year_to
q
sort=year_desc/title/status
```

### 10.5 导入和上传接口

```text
POST /api/rw/projects/{project_id}/papers/import/doi
POST /api/rw/projects/{project_id}/papers/import/bibtex
POST /api/rw/projects/{project_id}/papers/upload
```

上传限制：

```text
只允许 PDF。
默认最大 50MB。
文件名不可信，后端生成 paper_id.pdf。
只写入 storage.data_dir/files/{project_id}/。
禁止用户传入目标路径。
```

### 10.6 解析和卡片接口

```text
POST /api/rw/papers/{paper_id}/parse
POST /api/rw/projects/{project_id}/parse
GET  /api/rw/papers/{paper_id}/chunks
GET  /api/rw/papers/{paper_id}/parse-result
POST /api/rw/papers/{paper_id}/card
POST /api/rw/projects/{project_id}/cards
GET  /api/rw/papers/{paper_id}/card
GET  /api/rw/projects/{project_id}/cards
```

批量卡片生成返回 task_id：

```json
{
  "task_id": "task_xxx",
  "status": "queued",
  "task_type": "generate_cards",
  "poll_url": "/api/rw/tasks/task_xxx"
}
```

### 10.7 证据表接口

```text
POST /api/rw/projects/{project_id}/evidence/build
GET  /api/rw/projects/{project_id}/evidence
GET  /api/rw/evidence/{evidence_id}
PATCH /api/rw/evidence/{evidence_id}
POST /api/rw/evidence/{evidence_id}/accept
POST /api/rw/evidence/{evidence_id}/reject
GET  /api/rw/projects/{project_id}/evidence/export/json
```

查询过滤：

```text
topic
method
paper_id
evidence_strength
review_status
q
```

### 10.8 图谱接口

```text
POST /api/rw/projects/{project_id}/graph/build
GET  /api/rw/projects/{project_id}/graph
GET  /api/rw/projects/{project_id}/graph/stats
POST /api/rw/projects/{project_id}/graph/subgraph
GET  /api/rw/graph/nodes/{node_id}
GET  /api/rw/graph/nodes/{node_id}/evidence
POST /api/rw/projects/{project_id}/graph/paths
```

图谱响应：

```json
{
  "project_id": "proj_xxx",
  "nodes": [],
  "edges": [],
  "stats": {
    "node_count": 0,
    "edge_count": 0,
    "node_type_counts": {}
  },
  "source_index": {}
}
```

前端 G6 需要：

```text
id
label
type
size/degree
properties
source/target
edge_type
```

### 10.9 Scope 接口

```text
POST /api/rw/projects/{project_id}/scope/resolve
GET  /api/rw/projects/{project_id}/scope/filters
POST /api/rw/projects/{project_id}/scope/preview
```

filters 响应：

```text
topics
methods
years
paper_statuses
evidence_strengths
graph_node_types
```

preview 用于前端选择范围时即时显示：

```text
paper_count
evidence_count
graph_node_count
warnings
empty_reason
suggested_actions
```

### 10.10 ScopeQA 接口

```text
POST /api/rw/projects/{project_id}/qa
GET  /api/rw/projects/{project_id}/qa/history
GET  /api/rw/qa/{qa_id}
POST /api/rw/qa/{qa_id}/save-as-material
```

P0 可不持久化完整 history，但 API 契约先定义。

QA 响应：

```json
{
  "qa_id": "qa_xxx",
  "answer": "",
  "intent": "summary",
  "scope_summary": "",
  "supporting_papers": [],
  "evidence_records": [],
  "graph_paths": [],
  "uncertainty": "",
  "suggested_actions": [],
  "validation_warnings": [],
  "retrieval_diagnostics": {}
}
```

### 10.11 报告接口

```text
POST /api/rw/projects/{project_id}/reports/literature-review
POST /api/rw/projects/{project_id}/reports/innovation
GET  /api/rw/projects/{project_id}/reports
GET  /api/rw/reports/{report_id}
PATCH /api/rw/reports/{report_id}
GET  /api/rw/reports/{report_id}/versions
POST /api/rw/reports/{report_id}/versions
POST /api/rw/reports/{report_id}/validate
GET  /api/rw/reports/{report_id}/export/markdown
GET  /api/rw/reports/{report_id}/export/json
POST /api/rw/reports/{report_id}/archive
DELETE /api/rw/reports/{report_id}
```

报告生成默认是长任务：

```text
resolve scope
collect materials
generate
validate
save
return report_id
```

### 10.12 任务接口

```text
GET  /api/rw/tasks/{task_id}
GET  /api/rw/projects/{project_id}/tasks
GET  /api/rw/tasks/{task_id}/events
POST /api/rw/tasks/{task_id}/cancel
POST /api/rw/tasks/{task_id}/retry
```

P0：

```text
events 返回 JSON list。
cancel 只设置 cancel_requested。
retry 可先不实现。
```

P1：

```text
events 使用 SSE。
retry 创建新任务。
```

## 11. 事件流设计

### 11.1 P0 轮询

前端每 1-2 秒请求：

```text
GET /api/rw/tasks/{task_id}
GET /api/rw/tasks/{task_id}/events?after_sequence=12
```

优点：

```text
实现简单。
测试简单。
不依赖长连接。
```

### 11.2 P1 SSE

```text
GET /api/rw/tasks/{task_id}/events/stream
```

SSE 格式：

```text
id: 13
event: task_progress
data: {"task_id":"task_xxx","progress":0.45,"current_step":"Generating cards"}
```

事件类型：

```text
task.created
task.started
task.progress
task.checkpoint
task.warning
task.succeeded
task.failed
task.cancelled
paper.searched
paper.imported
paper.parsed
card.generated
evidence.generated
graph.built
qa.answered
report.generated
report.exported
```

### 11.3 事件持久化

P0 使用：

```text
task_events.json
```

每个事件保留：

```text
event_id
task_id
sequence
event_type
payload
created_at
```

P1 可增加内存订阅：

```text
EventBus.subscribe(task_id)
EventBus.publish(event)
```

## 12. 前端页面契约

### 12.1 页面划分

本项目 research workspace 前端建议先做四个核心页面：

```text
项目论文库
知识图谱
研究 QA
成果报告
```

可选：

```text
任务中心
项目设置
```

### 12.2 项目论文库页

接口：

```text
GET /projects
GET /projects/{project_id}/stats
GET /projects/{project_id}/papers
POST /projects/{project_id}/papers/search
POST /projects/{project_id}/papers/search/commit
POST /projects/{project_id}/papers/upload
POST /projects/{project_id}/parse
POST /projects/{project_id}/cards
POST /projects/{project_id}/evidence/build
GET /tasks/{task_id}
```

页面状态：

```text
active_project
paper_filters
selected_paper_ids
search_session
search_results
batch_task_ids
paper_table_loading
```

关键交互：

```text
搜索论文 -> 预览结果 -> 选择结果 -> commit 入库。
上传 PDF -> 创建 paper -> 可解析。
选择论文 -> 批量解析/卡片/证据。
任务进度条显示当前步骤和失败项。
```

### 12.3 知识图谱页

接口：

```text
GET /projects/{project_id}/graph
POST /projects/{project_id}/graph/build
POST /projects/{project_id}/graph/subgraph
GET /graph/nodes/{node_id}/evidence
POST /projects/{project_id}/scope/preview
```

页面状态：

```text
graph_data
selected_node
selected_edge
node_type_filters
selected_subgraph_ids
layout_mode
source_panel
```

关键交互：

```text
构建图谱。
筛选节点类型。
点击节点查看论文/证据来源。
框选子图生成 RetrievalScope。
从子图进入 QA 或报告生成。
```

### 12.4 研究 QA 页

接口：

```text
GET /projects/{project_id}/scope/filters
POST /projects/{project_id}/scope/resolve
POST /projects/{project_id}/qa
GET /projects/{project_id}/qa/history
GET /evidence/{evidence_id}
```

页面状态：

```text
scope_builder_state
resolved_scope
question
qa_messages
selected_evidence
answer_loading
```

关键交互：

```text
选择 Scope。
预览 Scope 内论文/证据数量。
提问。
答案展示 evidence 和 uncertainty。
点击 evidence 查看 source_quote。
把 QA 回答保存为报告素材。
```

### 12.5 成果报告页

接口：

```text
POST /projects/{project_id}/reports/literature-review
POST /projects/{project_id}/reports/innovation
GET /projects/{project_id}/reports
GET /reports/{report_id}
GET /reports/{report_id}/versions
POST /reports/{report_id}/validate
GET /reports/{report_id}/export/markdown
GET /reports/{report_id}/export/json
GET /tasks/{task_id}
```

页面状态：

```text
report_filters
selected_report_id
report_detail
version_list
source_index
validation_result
export_options
generation_task_id
```

关键交互：

```text
选择 Scope 生成综述。
选择 Scope 生成创新报告。
查看报告正文。
查看来源索引和质量校验。
查看版本历史。
导出 Markdown/JSON。
```

### 12.6 Task Center

接口：

```text
GET /projects/{project_id}/tasks
GET /tasks/{task_id}
POST /tasks/{task_id}/cancel
```

展示：

```text
任务类型
状态
进度
当前步骤
开始时间
结束时间
错误原因
输出链接
```

## 13. 前端 Store 建议

### 13.1 Store 拆分

```text
projectStore
  projects, activeProjectId, stats

paperStore
  papers, filters, searchSession, selectedPaperIds

taskStore
  tasksById, taskEventsById, polling

graphStore
  graphData, selectedNode, filters

scopeStore
  scopeDraft, resolvedScope, filters

qaStore
  messages, history, activeQaId

reportStore
  reports, reportDetail, versions, exportState

uiStore
  layout, theme, panels
```

### 13.2 API Client

建议：

```text
frontend/src/services/rwApi.ts
frontend/src/services/taskClient.ts
frontend/src/types/rwApi.ts
```

功能：

```text
统一 baseURL。
统一 X-API-Key。
统一 request_id。
统一错误解析。
统一 task polling。
```

### 13.3 任务轮询 hook

```text
useTask(taskId)
useProjectTasks(projectId)
useTaskEvents(taskId)
```

行为：

```text
queued/running/cancelling -> polling
succeeded/failed/cancelled -> stop polling
onSucceeded 回调刷新对应资源
onFailed 显示错误详情
```

### 13.4 前端错误处理

错误展示策略：

| code | UI |
| --- | --- |
| project_not_found | 返回项目选择 |
| scope_empty | 展示 suggested_actions |
| llm_failed | 提示可重试或使用 fallback |
| parse_failed | 展示 PDF 解析失败原因 |
| validation_failed | 打开质量校验面板 |
| file_too_large | 上传控件提示限制 |
| task_cancelled | 标记任务已取消 |

## 14. 安全和配置

### 14.1 API Key

本地 MVP：

```text
RW_API_KEY optional。
未设置时 dev mode 可跳过。
设置后所有 /api/rw 非 health/openapi 端点需要 X-API-Key。
```

P1：

```text
API key hash。
key id。
错误日志不记录明文 key。
```

### 14.2 CORS

配置：

```text
RW_API_CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

默认：

```text
仅本地地址。
不要默认 allow_origins=["*"] 搭配 credentials。
```

### 14.3 文件上传安全

```text
只允许 .pdf。
MIME 和扩展名都检查。
限制大小，默认 50MB。
不信任原始文件名。
禁止路径穿越。
保存到 storage.data_dir/files/{project_id}/{paper_id}.pdf。
```

### 14.4 路径和导出安全

```text
导出文件名由后端生成。
不允许用户传入任意输出路径。
下载只能下载 storage exports 目录内文件。
```

### 14.5 日志脱敏

```text
不记录 API key。
不记录完整 PDF 文本。
不记录完整 prompt。
错误 details 不包含本机敏感路径。
```

## 15. 日志与监控

### 15.1 API 日志事件

```text
api.request.started
api.request.completed
api.request.failed
task.created
task.started
task.progress
task.succeeded
task.failed
task.cancelled
api.error
```

### 15.2 请求日志字段

```text
request_id
method
path
status_code
duration_ms
project_id
task_id
error_code
client_host
```

### 15.3 指标

```text
api_request_count
api_error_rate
api_p95_latency_ms
task_success_rate
task_failure_rate
task_cancel_rate
avg_task_duration_ms
active_task_count
upload_failure_count
```

### 15.4 与 15 评估日志模块对齐

API 层应向评估模块提供：

```text
demo pipeline result
task metrics
report_traceability result
scope violation count
llm failure count
```

## 16. Demo Pipeline

### 16.1 目标

提供一个稳定的最小演示流程，用于：

```text
开发联调
端到端测试
产品演示
回归检查
```

### 16.2 API

```text
POST /api/rw/projects/demo
POST /api/rw/projects/{project_id}/demo/run
```

### 16.3 P0 演示数据

为了避免外部依赖，P0 demo 不访问真实搜索和真实 LLM：

```text
创建项目。
导入 3 篇 fake papers。
创建 fake chunks 或使用已有测试 fixture。
生成 fallback/fixture paper cards。
生成 evidence records。
构建图谱。
执行一个 QA。
生成 fallback 综述。
导出 Markdown。
```

### 16.4 输出

```json
{
  "project_id": "proj_demo",
  "task_id": "task_demo",
  "created": {
    "papers": 3,
    "cards": 3,
    "evidence": 6,
    "graph_nodes": 10,
    "reports": 1
  },
  "links": {
    "project": "/api/rw/projects/proj_demo",
    "reports": "/api/rw/projects/proj_demo/reports"
  }
}
```

## 17. 开发阶段

### A0：API 骨架和兼容依赖

目标：建立可启动、可测试的 v3 API。

任务：

```text
T14.0.1 新增 api.py。
T14.0.2 新增 create_app(storage=None, settings=None)。
T14.0.3 注册 /api/rw/health。
T14.0.4 新增 api_models.py 基础 ApiMeta/ApiError/PageInfo。
T14.0.5 新增 api_errors.py 和 exception handler。
T14.0.6 新增 request_id middleware。
T14.0.7 增加 FastAPI TestClient 测试。
```

验收：

```text
/api/rw/health 返回正常。
OpenAPI 可访问。
错误结构统一。
测试可注入临时 storage。
```

### A1：Project/Paper API

目标：前端能管理项目和论文库。

任务：

```text
T14.1.1 Project CRUD。
T14.1.2 Project stats/health。
T14.1.3 Paper list/detail/update/include/exclude。
T14.1.4 DOI/BibTeX import。
T14.1.5 Upload PDF。
T14.1.6 分页和过滤。
```

验收：

```text
项目可创建、更新、删除。
论文可导入、上传、筛选。
上传路径安全。
列表分页可用。
```

### A2：TaskService 和轮询

目标：长任务有状态和进度。

任务：

```text
T14.2.1 新增 WorkspaceTask。
T14.2.2 新增 TaskEvent。
T14.2.3 实现 TaskService。
T14.2.4 实现 /tasks/{task_id}。
T14.2.5 实现 /projects/{project_id}/tasks。
T14.2.6 实现 /tasks/{task_id}/events。
T14.2.7 实现 cancel request。
```

验收：

```text
任务可创建、运行、成功、失败、取消。
事件按 sequence 返回。
轮询能看到进度变化。
```

### A3：分析 Pipeline API

目标：解析、卡片、证据、图谱可通过 API 执行。

任务：

```text
T14.3.1 单篇 parse API。
T14.3.2 项目批量 parse task。
T14.3.3 单篇 card API。
T14.3.4 项目批量 cards task。
T14.3.5 evidence build task。
T14.3.6 graph build task。
T14.3.7 chunks/card/evidence/graph 查询 API。
```

验收：

```text
批量任务返回 task_id。
任务完成后 paper status 更新。
前端能查询卡片、证据和图谱。
```

### A4：ScopeQA 和报告 API

目标：研究 QA 和成果报告页可联调。

任务：

```text
T14.4.1 scope filters API。
T14.4.2 scope resolve/preview API。
T14.4.3 QA API。
T14.4.4 QA history 预留。
T14.4.5 literature review report task。
T14.4.6 innovation report task。
T14.4.7 reports list/detail。
T14.4.8 report validate/export。
```

验收：

```text
Scope 选择器可获取 filters。
QA 返回证据和不确定性。
报告生成返回 task_id。
报告详情和导出可用。
```

### A5：Demo Pipeline

目标：一键跑通最小闭环。

任务：

```text
T14.5.1 新增 demo_pipeline.py。
T14.5.2 创建 demo project。
T14.5.3 注入 fake papers/cards/evidence。
T14.5.4 构建 graph。
T14.5.5 生成 QA 和 report。
T14.5.6 输出 summary 和 links。
T14.5.7 test_demo_pipeline.py。
```

验收：

```text
demo pipeline 不依赖外部 API。
可重复运行。
输出 project_id/report_id。
端到端 smoke test 通过。
```

### A6：SSE 和前端体验

目标：长任务进度实时推送。

任务：

```text
T14.6.1 EventBus。
T14.6.2 /tasks/{task_id}/events/stream。
T14.6.3 heartbeat。
T14.6.4 前端 taskStore 接入 SSE。
T14.6.5 SSE 断线回退 polling。
```

验收：

```text
前端能实时看到任务步骤。
断线后可以通过 last event id 恢复。
```

### A7：OpenAPI、类型生成和安全

目标：前端长期维护成本下降。

任务：

```text
T14.7.1 OpenAPI schema 导出。
T14.7.2 TypeScript 类型生成脚本。
T14.7.3 API key middleware。
T14.7.4 CORS settings。
T14.7.5 上传安全测试。
T14.7.6 错误码文档。
```

验收：

```text
前端类型可从 OpenAPI 生成。
API key 可启用。
CORS 可配置。
上传限制有测试。
```

## 18. 测试计划

### 18.1 后端测试文件

```text
test_api_health.py
test_api_projects.py
test_api_papers.py
test_api_search.py
test_api_parse_cards.py
test_api_evidence.py
test_api_graph.py
test_api_scope_qa.py
test_api_reports.py
test_api_tasks.py
test_api_error_contract.py
test_api_upload_security.py
test_task_service.py
test_task_runner.py
test_demo_pipeline.py
```

### 18.2 核心测试用例

```text
health returns ok
create project returns project_id
get missing project returns unified error
list papers supports pagination
upload rejects non-pdf
upload rejects path traversal filename
create task returns queued
task progress updates
task failure records error code
task events ordered by sequence
cancel running task sets cancel_requested
scope preview returns counts
qa returns answer and evidence ids
report generation returns task id
report export markdown returns content
demo pipeline creates project and report
```

### 18.3 测试依赖注入

测试必须使用：

```text
tmp_path JSONStorage
FakeLLMService
FakeSearchAdapter
small PDF fixture or fake parser path
run_inline=true for long tasks
```

不允许：

```text
真实 OpenAI/LLM 调用。
真实外部搜索源。
写入用户真实 data 目录。
依赖固定端口。
```

### 18.4 前端联调测试

P1 增加：

```text
OpenAPI schema generation smoke test
API client contract test
Playwright demo flow
task polling hook test
report export download test
```

端到端流程：

```text
1. 创建 demo project。
2. 查看论文库。
3. 运行 demo pipeline。
4. 查看 task progress。
5. 打开 graph。
6. 提问 QA。
7. 查看报告。
8. 导出 Markdown。
```

## 19. 验收标准

### 19.1 功能验收

```text
v3 API 可启动。
/api/rw/health 可访问。
项目和论文库 API 可用。
长任务可创建、轮询、成功和失败。
解析/卡片/证据/图谱 API 可用。
ScopeQA API 可用。
综述和创新点报告 API 可用。
报告导出 API 可用。
demo pipeline 可跑通。
```

### 19.2 契约验收

```text
所有响应结构稳定。
所有错误使用统一 error contract。
所有请求/响应有 Pydantic DTO。
OpenAPI 文档可访问。
前端四页的数据需求都有对应接口。
```

### 19.3 工程验收

```text
API 测试使用临时 storage。
测试不调用真实 LLM 和外部搜索。
任务状态转换有测试。
上传安全有测试。
日志包含 request_id/task_id。
长任务失败能看到 error code/message。
```

### 19.4 前端验收

```text
论文库页能展示项目统计、论文列表和任务进度。
知识图谱页能展示 graph nodes/edges 和来源。
研究 QA 页能选择 scope、提问、查看证据。
成果报告页能生成、查看、校验和导出报告。
任务中心能展示运行中和历史任务。
```

## 20. 最小实现顺序

建议先做：

```text
1. api_models.py 基础响应和错误模型。
2. api_errors.py 和 exception handler。
3. api.py + /health。
4. Project API。
5. Paper list/import/upload API。
6. TaskService。
7. parse/cards/evidence/graph 批量任务。
8. scope resolve/preview。
9. QA API。
10. report list/detail/export。
11. report generation task。
12. demo pipeline。
13. SSE。
14. OpenAPI 类型生成和前端接入。
```

优先级：

```text
P0：API 骨架、统一错误、Project/Paper、TaskService、ScopeQA、Report、demo pipeline。
P1：SSE、OpenAPI 类型、前端四页联调、取消/重试。
P2：鉴权增强、WebSocket、分布式任务、部署监控。
```

## 21. 风险与应对

| 风险 | 表现 | 应对 |
| --- | --- | --- |
| service 同步阻塞 API | 报告生成请求卡死 | 长任务后台执行，P0 返回 task_id |
| API DTO 直接暴露内部模型 | 前端和存储强耦合 | api_models.py 单独定义 DTO |
| 错误结构不统一 | 前端到处 try/catch 特判 | exception handler 统一转换 |
| 任务状态丢失 | 刷新后进度消失 | JSONStorage 持久化 tasks/events |
| 取消任务不生效 | blocking 调用无法中断 | P0 item 间检查，P1 cancel token |
| 测试触发真实外部服务 | 慢、失败、成本高 | FakeLLM/FakeSearch/run_inline |
| 上传路径不安全 | 任意路径写入 | 后端生成文件名，限制目录 |
| SSE 兼容性问题 | 断线、代理缓冲 | P0 polling，P1 SSE + heartbeat |
| OpenAPI 和前端类型漂移 | 前端字段错误 | 类型生成和 contract test |
| 前端目录缺失 | 无法直接联调 UI | 先完成 API contract 和 demo pipeline |

## 22. 参考文档

本地参考：

```text
docs/research/14-细致开发计划/模块级开发计划/00-模块总览与依赖关系.md
docs/research/14-细致开发计划/模块级开发计划/03-论文库搜索导入模块.md
docs/research/14-细致开发计划/模块级开发计划/04-PDF解析与分块模块.md
docs/research/14-细致开发计划/模块级开发计划/05-论文卡片生成模块.md
docs/research/14-细致开发计划/模块级开发计划/06-证据表模块.md
docs/research/14-细致开发计划/模块级开发计划/07-知识图谱模块.md
docs/research/14-细致开发计划/模块级开发计划/08-RetrievalScope模块.md
docs/research/14-细致开发计划/模块级开发计划/09-ScopeQA与RAG模块.md
docs/research/14-细致开发计划/模块级开发计划/10-综述生成模块.md
docs/research/14-细致开发计划/模块级开发计划/11-创新点报告模块.md
docs/research/14-细致开发计划/模块级开发计划/12-报告版本与导出模块.md
docs/research/14-细致开发计划/模块级开发计划/13-LLM提示词与结构化输出模块.md
docs/research/14-细致开发计划/模块级开发计划/15-评估日志监控模块.md
docs/getting-started/frontend-overview.md
src/agents_v2/api/
```

外部参考：

```text
FastAPI:
https://fastapi.tiangolo.com/

Server-Sent Events:
https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events

OpenAPI:
https://spec.openapis.org/oas/latest.html

Celery Task States:
https://docs.celeryq.dev/en/stable/userguide/tasks.html

Zustand:
https://zustand-demo.pmnd.rs/

Ant Design:
https://ant.design/
```
