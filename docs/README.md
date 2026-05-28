# Paper Agent Documentation

## Structure

```
docs/
├── getting-started/     # Quick start, setup, project overview
├── architecture/        # System architecture (per-module docs)
├── api/                 # API reference
├── development/         # Development guide, plans, testing, code standards
└── research/            # Technical research notes
```

## Getting Started

| Document | Description |
|----------|-------------|
| [Project Overview](getting-started/project-overview.md) | Architecture, tech stack, module overview |
| [Quick Start](getting-started/quickstart.md) | How to run the project |
| [Running Guide](getting-started/running.md) | Detailed startup instructions |
| [Frontend Overview](getting-started/frontend-overview.md) | Frontend pages and features |
| [Docker Registry](getting-started/docker-registry.md) | Container image registry |

## Architecture

System architecture docs organized by module.

| Document | Description |
|----------|-------------|
| [Architecture Diagram](architecture/architecture-diagram.md) | Full system architecture |
| [Execution Paths](architecture/execution-paths.md) | Execution flow and tracing |
| [Agents Catalog](architecture/agents-catalog.md) | Complete agent inventory |

### Core

| Module | Document |
|--------|----------|
| core | [Base Agent](architecture/core/base-agent.md) |
| unified | [Circuit Breaker](architecture/unified/circuit-breaker.md), [Intent Router](architecture/unified/intent-router.md), [Multi-Agent](architecture/unified/multi-agent.md) |
| config | [Config Module](architecture/config/config-module.md) |
| security | [Security Module](architecture/security/security-module.md) |
| validation | [Validation Module](architecture/validation/validation-module.md) |

### Workflow & API

| Module | Document |
|--------|----------|
| langgraph_workflow | [LangGraph Workflow](architecture/langgraph_workflow/langgraph-workflow.md) |
| api | [API Gateway](architecture/api/api-gateway.md) |
| server | [Server Module](architecture/server/server-module.md) |
| sdk | [SDK Module](architecture/sdk/sdk-module.md) |

### Agents

| Module | Document |
|--------|----------|
| paper_agents | [Paper Agents](architecture/paper_agents/paper-agents.md) |
| paper_search | [Paper Search](architecture/paper_search/paper-search-module.md) |
| writing | [Writing Module](architecture/writing/writing-module.md) |
| academic_qa | [Academic QA](architecture/academic_qa/academic-qa-system.md) |
| problem_oriented | [Problem Oriented](architecture/problem_oriented/problem-oriented-module.md) |

### Data & Retrieval

| Module | Document |
|--------|----------|
| search | [Search Module](architecture/search/search-module.md), [Search System](architecture/search/search-system.md) |
| retrieval | [Retrieval System](architecture/retrieval/retrieval-system.md) |
| knowledge_graph | [Knowledge Graph](architecture/knowledge_graph/knowledge-graph.md) |
| memory | [Memory System](architecture/memory/memory-system.md) |
| storage | [Storage Layer](architecture/storage/storage-layer.md) |

### Infrastructure

| Module | Document |
|--------|----------|
| monitoring | [Monitoring System](architecture/monitoring/monitoring-system.md) |
| evaluation | [Evaluation System](architecture/evaluation/evaluation-system.md) |
| routing | [Routing System](architecture/routing/routing-system.md) |
| intent | [Intent Router](architecture/intent/intent-router.md) |
| citation | [Citation Module](architecture/citation/citation-module.md) |
| tools | [Tools Module](architecture/tools/tools-module.md) |
| skills | [Skills System](architecture/skills/skills-system.md) |
| scheduler | [Scheduler System](architecture/scheduler/scheduler-system.md) |
| personalization | [Personalization](architecture/personalization/personalization-system.md) |
| multimodal | [Multimodal](architecture/multimodal/multimodal-system.md) |
| state | [State Management](architecture/state/state-management.md) |

## API

| Document | Description |
|----------|-------------|
| [API Reference](api/api-reference.md) | REST API endpoints |
| [Logging](api/logging.md) | Loguru logging configuration |

## Development

| Document | Description |
|----------|-------------|
| [Development Guide](development/development-guide.md) | Main development doc |
| [Code Standards](development/代码规范.md) | Code conventions and style guide |
| [Project Standards](development/项目规范.md) | Project structure and conventions |
| [Architecture Review](development/architecture-review.md) | Architecture audit report |
| [Plans](development/plans/) | Per-module development plans |

## Research

Technical research organized by topic.

| Topic | Description |
|-------|-------------|
| [00-General Research](research/00-综合调研报告/) | Cross-cutting research and guides |
| [01-Agent Protocols](research/01-Agent协议与架构/) | MCP, A2A, Skills protocols |
| [02-Prompt Engineering](research/02-提示词工程/) | Prompt engineering guides |
| [03-Agent Evaluation](research/03-Agent能力评估/) | Agent evaluation frameworks |
| [04-PaperAgent Skills](research/04-PaperAgent技能/) | Skill ecosystem research |
| [05-Academic Search](research/05-学术搜索与解析/) | PDF parsing, academic search |
| [06-Intent & Routing](research/06-意图识别与路由/) | Intent recognition research |
| [07-Memory System](research/07-记忆系统/) | Memory system architecture |
| [08-Logging & Monitoring](research/08-日志与监控/) | Logging system research |
| [10-Academic QA](research/10-学术QA系统/) | QA system research |
| [10-Knowledge Graph](research/10-知识图谱/) | Knowledge graph research |
| [11-Product & Dev](research/11-产品方案与开发/) | Product plans and dev specs |
| [12-Optimization](research/12-优化方案/) | Performance optimization |
| [13-Mixed Research](research/13-综合调研/) |综合调研报告 |
