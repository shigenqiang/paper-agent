# 项目规范目录

本文档集合为 PaperAgent 项目定义工程标准和代码规范。

---

## 1. 规范文件索引

### [项目规范](./项目规范.md)
项目工程相关的标准和约定。

| 章节 | 内容 |
|------|------|
| 1. 项目结构规范 | 通用结构、多模块monorepo |
| 2. Git工作流规范 | 分支命名、Conventional Commits、PR合并 |
| 3. 文档规范 | README模板、CHANGELOG标准、OpenAPI |
| 4. 开发流程规范 | Issue模板、Sprint周期、发布流程 |
| 5. 环境与配置规范 | dev/staging/prod、.env管理 |
| 6. 依赖管理规范 | pyproject.toml、package.json |
| 7. 错误处理规范 | 错误码体系、日志规范 |

### [代码规范](./代码规范.md)
源代码编写标准和最佳实践。

| 章节 | 内容 |
|------|------|
| 1. 命名规范 | 变量/函数/类/文件、Python vs JS对照 |
| 2. 代码格式规范 | 缩进、空格、换行、空行 |
| 3. 注释规范 | 文件头、类、方法、TODO注释 |
| 4. 函数方法规范 | 单一职责、参数控制、返回值 |
| 5. 类与模块规范 | 设计原则、依赖注入 |
| 6. 错误处理规范 | Python/JS异常处理最佳实践 |
| 7. 测试规范 | pytest/Jest结构、命名 |
| 8. Linter/Formatter | black、ESLint、Prettier配置 |

---

## 2. 官方规范参考

| 规范 | 来源 | 适用 |
|------|------|------|
| [Google Style Guides](https://github.com/google/styleguide) | Google | JS/C++/Python/Go/TypeScript |
| [PEP 8](https://pep8.org/) | Python官方 | Python编码规范 |
| [Conventional Commits](https://www.conventionalcommits.org/) | 社区 | Git提交规范 |

---

## 3. 工具链配置

### Python (pyproject.toml)

```toml
[tool.black]
line-length = 88          # Black默认
target-version = ["py310"]

[tool.ruff]
line-length = 88
select = ["E", "W", "F", "I", "N", "UP", "B", "C4", ...]
ignore = ["E501"]         # 由black处理行长度
```

**安装开发依赖：**
```bash
pip install black isort ruff mypy pytest pytest-asyncio
```

**格式化命令：**
```bash
black src/ tests/ demos/           # 格式化代码
isort src/ tests/ demos/           # 排序imports
ruff check src/ --fix              # 检查并修复
mypy src/                          # 类型检查
```

### JavaScript/TypeScript

**ESLint规则（.eslintrc.json）：**
- no-console: warn
- no-unused-vars: error
- react-hooks规则: error

**Prettier配置（.prettierrc）：**
```json
{
  "semi": true,
  "singleQuote": true,
  "tabWidth": 2,
  "printWidth": 100
}
```

**安装前端lint：**
```bash
cd frontend
npm install eslint prettier eslint-plugin-react eslint-plugin-react-hooks
```

---

## 4. Commit Message格式

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

Closes #456
```

**Type参考：**

| Type | 说明 |
|------|------|
| `feat` | 新功能 |
| `fix` | Bug修复 |
| `docs` | 文档更新 |
| `style` | 格式调整 |
| `refactor` | 重构 |
| `perf` | 性能优化 |
| `test` | 测试相关 |
| `chore` | 构建/工具变更 |

---

## 5. 分支命名规范

```
feature/<issue-id>-<short-description>   # 功能分支
fix/<issue-id>-<short-description>       # 修复分支
release/<version>                        # 发布分支
hotfix/<issue-id>-<short-description>   # 热修复分支
```

---

## 6. 命名对照速查

| 类型 | Python | JavaScript |
|------|--------|------------|
| 变量 | `snake_case` | `camelCase` |
| 常量 | `UPPER_SNAKE_CASE` | `camelCase` |
| 函数 | `snake_case` | `camelCase` |
| 类 | `PascalCase` | `PascalCase` |
| 文件 | `snake_case.py` | `camelCase.js` |
| 测试文件 | `test_xxx.py` | `xxx.test.js` |
| 私有成员 | `_snake_case` | `_camelCase` |

---

## 7. 相关资源

- 详细调研报告：[项目规范与代码规范最佳实践调研报告](../research/项目规范与代码规范最佳实践调研报告.md)
- 项目CLAUDE.md：[../../CLAUDE.md](../../CLAUDE.md) — 项目任务和配置