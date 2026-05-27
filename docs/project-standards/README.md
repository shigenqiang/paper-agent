# 项目规范目录

本文档集合为 PaperAgent 项目定义工程标准和代码规范。
基于 2025-2026 年最新标准，覆盖 Ruff、uv、PEP 621/735、MCP、Agent Protocol、OWASP LLM Top 10。

---

## 1. 规范文件索引

### [项目规范](./项目规范.md)

项目工程相关的标准和约定。

| 章节 | 内容 |
|------|------|
| 1. 项目结构规范 | src layout、目录组织 |
| 2. pyproject.toml 规范 | PEP 621 元数据、PEP 735 依赖组 |
| 3. 工具链规范 | Ruff（统一 lint+format）、uv（包管理）、类型检查、pre-commit |
| 4. Git 工作流规范 | 分支命名、Conventional Commits、PR 合并 |
| 5. 文档规范 | README、CHANGELOG、CITATION.cff |
| 6. AI Agent 开发规范 | Agent 架构原则、MCP、Agent Protocol、可观测性 |
| 7. 安全规范 | OWASP LLM Top 10、输入验证、速率限制、输出过滤 |
| 8. 学术研究可复现性规范 | FAIR 原则、ACM Artifact 认证 |
| 9. 依赖管理规范 | pyproject.toml、package.json |
| 10. CI/CD 规范 | GitHub Actions、发布流程 |

### [代码规范](./代码规范.md)

源代码编写标准和最佳实践。

| 章节 | 内容 |
|------|------|
| 1. 命名规范 | 变量/函数/类/文件命名 |
| 2. 类型注解规范 | PEP 561、Protocol、TypedDict、Literal、py.typed |
| 3. 代码格式规范 | 缩进、空格、换行、导入 |
| 4. 注释规范 | Google 风格 docstring、TODO 注释 |
| 5. 函数/方法规范 | 单一职责、参数控制、返回值 |
| 6. 异步代码规范 | async/await、并发、超时、异步迭代器 |
| 7. 错误处理规范 | 异常层次、重试机制 |
| 8. 测试规范 | pytest-asyncio、Arrange-Act-Assert、Mock |
| 9. LLM/Agent 代码规范 | LLM 客户端封装、Agent 基类、知识图谱模式 |
| 10. Linter/Formatter | Ruff 配置和命令 |

---

## 2. 推荐工具链（2025-2026）

| 关注点 | 推荐工具 | 说明 |
|--------|----------|------|
| **构建系统** | hatchling | PEP 621 标准 |
| **包管理** | uv | 替代 pip/pip-tools/virtualenv/pyenv |
| **Lint** | ruff | 替代 flake8/isort/pylint/bandit |
| **格式化** | ruff format | 替代 black |
| **类型检查** | mypy + pyright | 互补覆盖 |
| **测试** | pytest + pytest-asyncio | 异步测试自动模式 |
| **Pre-commit** | pre-commit + ruff hooks | 提交前自动检查 |
| **CI/CD** | GitHub Actions | 自动化流水线 |
| **Agent 协议** | MCP | Anthropic 开放协议 |
| **可观测性** | OpenTelemetry + LangFuse | 追踪 + 评估 |
| **安全扫描** | ruff (S rules) | 内置安全检查 |

---

## 3. 官方规范参考

| 规范 | 来源 | 适用 |
|------|------|------|
| [PEP 8](https://pep8.org/) | Python 官方 | Python 编码规范 |
| [PEP 621](https://peps.python.org/pep-0621/) | Python 官方 | pyproject.toml 元数据 |
| [PEP 735](https://peps.python.org/pep-0735/) | Python 官方 | 依赖组 |
| [PEP 561](https://peps.python.org/pep-0561/) | Python 官方 | 类型信息分发 |
| [Google Style Guides](https://github.com/google/styleguide) | Google | JS/C++/Python/Go |
| [Conventional Commits](https://www.conventionalcommits.org/) | 社区 | Git 提交规范 |
| [Keep a Changelog](https://keepachangelog.com/) | 社区 | 变更日志 |
| [Ruff 文档](https://docs.astral.sh/ruff/) | Astral | Lint + Format |
| [uv 文档](https://docs.astral.sh/uv/) | Astral | 包管理 |
| [MCP 规范](https://modelcontextprotocol.io/) | Anthropic | Agent 协议 |
| [Agent Protocol](https://agentprotocol.ai/) | AI Engineer Foundation | Agent 通信 |
| [OWASP LLM Top 10](https://owasp.org/www-project-top-10-for-large-language-model-applications/) | OWASP | LLM 安全 |
| [FAIR 原则](https://fair-software.nl/) | 社区 | 研究软件可复现性 |
| [ACM Artifact Review](https://www.acm.org/publications/policies/artifact-review-badging) | ACM | 研究产物认证 |

---

## 4. 工具链配置速查

### Python（pyproject.toml）

```toml
[tool.ruff]
target-version = "py311"
line-length = 88

[tool.ruff.lint]
select = ["E", "W", "F", "I", "N", "UP", "B", "SIM", "C4", "S", "RUF", "T20", "LOG"]
ignore = ["E501", "S101"]

[tool.mypy]
strict = true
disallow_untyped_defs = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

**安装开发依赖：**
```bash
uv sync                                    # 同步所有依赖
uv run ruff check --fix .                  # 检查并修复
uv run ruff format .                       # 格式化
uv run mypy src/                           # 类型检查
uv run pytest                              # 运行测试
```

### Pre-commit

```bash
uv run pre-commit install                  # 安装钩子
uv run pre-commit run --all-files          # 手动运行
```

---

## 5. Commit Message 格式

```
<type>(<scope>): <subject>

[optional body]

[optional footer]
```

**示例：**
```
feat(search): add semantic query expansion

Implement semantic expansion using embedding similarity.
Fixes #123
```

---

## 6. 命名对照速查

| 类型 | Python |
|------|--------|
| 变量 | `snake_case` |
| 常量 | `UPPER_SNAKE_CASE` |
| 函数 | `snake_case` |
| 类 | `PascalCase` |
| 文件 | `snake_case.py` |
| 测试文件 | `test_xxx.py` |
| 私有成员 | `_snake_case` |
| 布尔变量 | `is/has/can/should` 前缀 |
| 枚举值 | `UPPER_SNAKE_CASE` |
| 类型变量 | `PascalCase` |

---

## 7. 相关资源

- 项目 CLAUDE.md：[../../CLAUDE.md](../../CLAUDE.md) — 项目任务和配置
- 详细调研报告：[../research/项目规范与代码规范最佳实践调研报告.md](../research/项目规范与代码规范最佳实践调研报告.md)
