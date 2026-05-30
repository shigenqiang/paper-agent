# Paper Agent Documentation

## Structure

```
docs/
├── getting-started/     # Quick start, setup, project overview
├── api/                 # API reference
├── development/         # Code and project standards
└── research/            # Technical research notes
```

## Getting Started

| Document | Description |
|----------|-------------|
| [Quick Start](getting-started/quickstart.md) | 安装、配置、启动、API 端点一览 |
| [Framework](getting-started/framework.md) | 框架架构与各模块实现情况 |
| [Project Overview](getting-started/project-overview.md) | Architecture, tech stack, module overview |
| [Docker Registry](getting-started/docker-registry.md) | Container image registry |

## API

| Document | Description |
|----------|-------------|
| [Quick Start - HTTP API](getting-started/quickstart.md#http-api-一览) | 完整 HTTP API 端点和使用示例 |
| [Logging](api/logging.md) | Loguru logging configuration |

## Modules

| Document | Description |
|----------|-------------|
| [PDF Parsing](pdf-parsing.md) | PDF 解析架构、分块策略、中文处理、质量标记 |
| [PDF Parsing Issues](pdf-parsing-issues.md) | 已知问题清单：公式、图片、表格、碎片化、OCR |
| [Search Module](search-module.md) | 搜索源、搜索模式、排序算法、去重合并 |
| [Search Token Report](search-stage-token-report.md) | 搜索阶段 Token 消耗分析 |

## Development

| Document | Description |
|----------|-------------|
| [Code Standards](development/代码规范.md) | Code conventions and style guide |
| [Project Standards](development/项目规范.md) | Project structure and conventions |

## Research

Technical research organized by topic.

| Topic | Description |
|-------|-------------|
| [00-General Research](research/00-综合调研报告/) | Cross-cutting research and guides |
| [论文完整信息描述字段设计](research/00-综合调研报告/论文完整信息描述字段设计.md) | 论文数据模型调研：40+字段设计（身份/内容/关系/质量四层） |
| [01-Agent Protocols](research/01-Agent协议与架构/) | MCP, A2A, Skills protocols |
| [02-Prompt Engineering](research/02-提示词工程/) | Prompt engineering guides |
| [03-Agent Evaluation](research/03-Agent能力评估/) | Agent evaluation frameworks |
| [04-PaperAgent Skills](research/04-PaperAgent技能/) | Skill ecosystem research |
| [05-Academic Search](research/05-学术搜索与解析/) | Academic search, paper selection, dedup |
| [PDF Parsing Research](research/05-学术搜索与解析/pdf-parsing/) | 8份PDF解析调研：布局检测、中文PDF、边缘问题、技术选型、优化路线 |
| [06-Intent & Routing](research/06-意图识别与路由/) | Intent recognition research |
| [07-Memory System](research/07-记忆系统/) | Memory system architecture |
| [08-Logging & Monitoring](research/08-日志与监控/) | Logging system research |
| [10-Academic QA](research/10-学术QA系统/) | QA system research |
| [10-Knowledge Graph](research/10-知识图谱/) | Knowledge graph research |
| [11-Product & Dev](research/11-产品方案与开发/) | Product plans and dev specs |
| [12-Optimization](research/12-优化方案/) | Performance optimization |
| [13-Mixed Research](research/13-综合调研/) | General research reports |
