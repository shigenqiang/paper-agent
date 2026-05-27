# WebSearch API 返回 400 错误

**日期**：2026-05-09
**类型**：API错误
**状态**：已记录（绕过方案）

## 问题现象

使用内置 `WebSearch` 工具时，返回 API 错误：

```json
API Error: 400 {"type":"error","error":{"type":"invalid_request_error","message":"invalid params, function name or parameters is empty (2013)"},"request_id":"..."}
```

## 复现步骤

1. 调用 `WebSearch(query="test query")`
2. 返回 400 错误

## 根因分析

内置 WebSearch 工具的 API 凭据或参数配置有问题，导致请求被拒绝。

## 解决方案

### 绕过方案

使用 MCP 工具 `mcp__MiniMax__web_search` 替代内置 WebSearch：

1. 在 CLAUDE.md 中添加规则：**禁止使用内置 WebSearch 工具**
2. 调研时必须使用 `mcp__MiniMax__web_search`
3. 通过 Agent 代理调用 MCP 工具进行搜索

### 代码修改

**CLAUDE.md** 添加：
```markdown
### 调研工具使用规则

**禁止使用内置 WebSearch 工具**：
- 内置 WebSearch API 返回 400 错误（参数错误），无法使用
- **必须使用 MCP 工具**：`mcp__MiniMax__web_search`
- 通过 Agent 代理或其他方式调用 MiniMax MCP 的 web_search 功能进行搜索
```

**调研提示词.md** 更新：
```markdown
## 绝对禁止的行为

...
5. **使用内置 WebSearch 工具** - WebSearch API 返回 400 错误，必须使用 `mcp__MiniMax__web_search`

**调研工具**：
- 内置 WebSearch API 返回 400 错误（参数错误），**禁止使用**
- **必须使用 MCP 工具**：`mcp__MiniMax__web_search`
```

## 验证结果

通过 Agent 代理使用 MCP 工具可以正常进行搜索。

## 经验教训

1. 内置工具可能存在配置问题，需要及时发现并记录
2. 有 MCP 服务时，优先使用 MCP 工具而非内置工具
3. 问题记录有助于后续维护和团队协作
