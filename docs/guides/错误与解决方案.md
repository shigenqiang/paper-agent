# 错误与解决方案文档

本文档记录系统中可能遇到的 API 错误及其解决方案，供开发和调试参考。

---

## 0. 前端 React/Antd 错误

### 0.1 App.useMessage is not a function

**错误信息**:
```
TypeError: App.useMessage is not a function
    at HomePage (HomePage.jsx:175:45)
```

**原因分析**:
在 antd v5 中，`App` 组件没有静态方法 `useMessage`。`message.useMessage()` 是独立的 hook，不依赖 `App` 组件。

**错误场景**:
1. 错误地将 `App.useMessage()` 与 `message.useMessage()` 混淆
2. 在使用 `App` 组件时，尝试调用 `App.useMessage()`

**解决方案**:
使用 `message.useMessage()` hook:

```jsx
import { message } from 'antd'

const HomePage = () => {
  const [messageApi, contextHolder] = message.useMessage()

  return (
    <>
      {contextHolder}
      {/* component content */}
    </>
  )
}
```

**注意事项**:
- `message.useMessage()` 可以在任何组件中使用，不一定需要 `<App>` 包裹
- 如果需要使用 `<App>` 组件（提供全局配置和应用状态），仍然使用 `message.useMessage()` 获取 message 实例
- 不要使用 `App.useMessage()` - 这个方法不存在

**预防措施**:
- 始终使用 `message.useMessage()` 而不是 `App.useMessage()`
- 如果需要 App 的其他功能（如 `notification`），单独导入 `<App>` 组件

---

### 0.2 message is not defined

**错误信息**:
```
ReferenceError: message is not defined
    at ReportsPage (ReportsPage.jsx:77:39)
```

**原因分析**:
在 antd v5 中使用 `message.useMessage()` 时，需要先从 `antd` 中导入 `message` 模块。

**错误场景**:
1. 使用了 `message.useMessage()` 但没有导入 `message`
2. 在 import 语句中漏掉了 `message`

**解决方案**:
确保在 import 语句中包含 `message`:

```jsx
import { Card, Tabs, Button, message } from 'antd'
// 或者
import { Card, Tabs, Button, Space, Typography, App, message } from 'antd'
```

**预防措施**:
- 使用 `message.useMessage()` 时检查 import 语句是否包含 `message`
- 保持 import 语句整齐，按字母顺序排列有助于发现遗漏

---

## 0.3 SSL 证书验证失败

**错误信息**:
```
urllib.error.URLError: <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed>
```

**原因分析**:
Python 在调用外部 API（如 arXiv、PubMed）时，默认会验证 SSL 证书。在某些环境中，证书验证会失败，导致返回空结果。

**错误场景**:
1. 调用 arXiv API 时返回空结果
2. 调用 PubMed API 时返回空结果
3. 没有任何错误日志，但结果为空

**解决方案**:
创建 SSL 上下文并绕过证书验证:

```python
import ssl
import urllib.request

# 创建SSL上下文（忽略证书验证）
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# 在请求时使用 ssl_context
with urllib.request.urlopen(url, timeout=30, context=ssl_context) as response:
    data = response.read().decode("utf-8")
```

**预防措施**:
- 仅在开发/测试环境中忽略 SSL 证书
- 生产环境应配置正确的证书路径
- 添加 fallback 逻辑处理验证失败的情况

---

## 0.4 asyncio.run() 在同步函数中调用 async 函数

**错误信息**:
```
TypeError: Object of type coroutine was not expected for 'generate_from_paper'
```

**原因分析**:
在同步函数中直接调用 async 函数返回的是 coroutine 对象，而不是实际结果。需要使用 `asyncio.run()` 来执行 async 函数。

**错误场景**:
1. 同步函数中调用 async 方法
2. 忘记使用 `asyncio.run()` 包装 async 调用

**解决方案**:
```python
import asyncio

def sync_function():
    # 正确：在同步函数中使用 asyncio.run()
    result = asyncio.run(async_function())
    return result

# 或者在已经处于 async 上下文中时，直接 await
async def async_function_wrapper():
    result = await async_function()
    return result
```

**预防措施**:
- 区分同步函数和异步函数
- 在同步函数中调用 async 函数时使用 `asyncio.run()`
- 考虑将整个调用链改为 async 模式

---

## 0.5 JSX 语法错误 - 相邻 JSX 元素必须包装在闭合标签中

**错误信息**:
```
Internal server error: Adjacent JSX elements must be wrapped in an enclosing tag
Internal server error: Unterminated JSX contents
```

**原因分析**:
在修改 React 组件时，添加 Fragment (`<>...</>`) 或其他包装元素时没有正确闭合标签，导致 JSX 结构不完整。

**错误场景**:
1. 添加了 `<>` 开始标签但没有添加对应的 `</>` 结束标签
2. 在 return 语句中添加了包装元素但括号不匹配
3. 编辑时不小心删除了闭合标签

**解决方案**:
确保 JSX 结构正确闭合:

```jsx
// 错误示例 - Fragment 没有正确闭合
return (
  <>
    <div className="space-y-4">
      {/* content */}
    </div>
  )
  // 缺少 </>
)

// 正确示例
return (
  <>
    <div className="space-y-4">
      {/* content */}
    </div>
  </>
)
```

**预防措施**:
- 使用 Fragment 时确保开始和结束标签配对
- 使用 IDE 的括号匹配功能检查结构
- 编辑后用 Prettier 格式化代码

---

## 1. MiniMax API 错误

### 1.1 Invalid tool parameters / Content block is not a input_json block

**错误信息**:
```
Invalid tool parameters: '...'
API Error: Content block is not a input_json block
```

**原因分析**:
MiniMax API 使用特定的 content block 格式来传递工具调用结果。当 LLM 生成工具调用请求时，API 需要正确的 `input_json` 格式。如果传入的 content block 格式不正确，或者工具参数不符合 schema 定义，就会报此错误。

**常见场景**:
1. 工具参数缺少必需字段
2. 工具参数类型不匹配（如期望 string 但传了 number）
3. 工具参数包含非法字符或格式
4. 使用了 API 不支持的 tool_call 格式

**解决方案**:

```python
# 确保工具参数符合 schema 定义
def validate_tool_params(tool_name: str, params: dict, tools_schema: list) -> dict:
    """验证工具参数"""
    for tool in tools_schema:
        if tool.get("name") == tool_name:
            schema = tool.get("parameters", {})
            required = schema.get("required", [])
            properties = schema.get("properties", {})

            # 检查必需参数
            for req in required:
                if req not in params:
                    raise ValueError(f"Missing required parameter: {req}")

            # 类型检查
            for key, value in params.items():
                if key in properties:
                    expected_type = properties[key].get("type")
                    if not validate_type(value, expected_type):
                        raise TypeError(f"Invalid type for {key}: expected {expected_type}")

            break

    return params
```

**预防措施**:
- 在调用 API 前验证所有工具参数
- 使用 Pydantic 或 JSON Schema 验证输入
- 捕获并记录详细的错误信息用于调试

---

### 1.2 Rate Limit Error (429)

**错误信息**:
```
Rate limit exceeded. Please retry after X seconds.
```

**原因**: API 调用频率超过限制

**解决方案**:
```python
async def retry_with_backoff(func, max_retries=5, base_delay=1):
    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            if "rate limit" in str(e).lower():
                delay = base_delay * (2 ** attempt)
                await asyncio.sleep(delay)
            else:
                raise
    raise Exception("Max retries exceeded")
```

---

### 1.3 Context Overflow Error

**错误信息**:
```
Context length exceeded maximum allowed
```

**原因**: 输入的 context 长度超过模型限制

**解决方案**:
```python
def truncate_context(messages, max_tokens=4000):
    """截断上下文，保留最近的消息"""
    truncated = []
    total_tokens = 0

    for msg in reversed(messages):
        tokens = estimate_tokens(msg)
        if total_tokens + tokens <= max_tokens:
            truncated.insert(0, msg)
            total_tokens += tokens
        else:
            break

    return truncated
```

---

### 1.4 Authentication Error

**错误信息**:
```
Invalid API key or authentication failed
```

**原因**: API Key 无效或过期

**解决方案**:
1. 检查环境变量 `OPENAI_API_KEY` 或 `MINIMAX_API_KEY`
2. 确认 API Key 有权限访问目标模型
3. 检查 API Key 是否已过期

---

## 2. 学术数据库 API 错误

### 2.1 arXiv API 错误

**错误信息**:
```
arXiv API error: Too many requests
```

**原因**: arXiv 对 API 请求有频率限制

**解决方案**:
```python
# 添加请求间隔
import asyncio
async def search_arxiv(query, delay=3.0):
    await asyncio.sleep(delay)  # 遵守频率限制
    # 执行搜索...
```

---

### 2.2 PubMed API 错误

**错误信息**:
```
PubMed API error: Invalid API key or rate limit exceeded
```

**解决方案**:
1. 检查 PubMed API Key 配置
2. 实施请求间隔和重试机制

---

### 2.3 Semantic Scholar API 错误

**错误信息**:
```
Semantic Scholar API error: Request blocked due to rate limiting
```

**解决方案**:
```python
SEMANTIC_SCHOLAR_RATE_LIMIT = 1  # 每秒请求数
```

---

## 3. 内部错误处理

### 3.1 错误分类

| 错误类别 | 说明 | 处理策略 |
|---------|------|---------|
| `INVALID_INPUT` | 输入参数无效 | 验证并返回错误信息 |
| `TIMEOUT` | 操作超时 | 重试或使用缓存 |
| `LLM_RATE_LIMIT` | LLM API 限流 | 退避重试 |
| `LLM_CONTEXT_OVERFLOW` | 上下文溢出 | 截断或总结历史 |
| `EXTERNAL_API_FAILURE` | 外部 API 失败 | 重试或降级 |
| `VALIDATION_FAILURE` | 验证失败 | 返回详细错误 |

### 3.2 错误恢复策略

系统在 `error_recovery.py` 中实现了细粒度的错误恢复策略:

```python
# 错误类别到恢复策略的映射
ERROR_RECOVERY_STRATEGY_MAP = {
    ErrorCategory.INVALID_INPUT: [
        {"strategy": "validate_and_retry", "timeout": 5, "max_attempts": 2},
        {"strategy": "use_defaults", "timeout": 1, "max_attempts": 1},
    ],
    ErrorCategory.TIMEOUT: [
        {"strategy": "retry_with_backoff", "timeout": 30, "max_attempts": 3},
        {"strategy": "reduce_scope", "timeout": 15, "max_attempts": 1},
    ],
    ErrorCategory.LLM_RATE_LIMIT: [
        {"strategy": "rate_limit_backoff", "timeout": 60, "max_attempts": 5},
        {"strategy": "switch_to_cache", "timeout": 5, "max_attempts": 1},
    ],
    # ... 更多策略
}
```

---

## 4. 调试建议

### 4.1 启用详细日志

```python
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
```

### 4.2 常见错误快速检查清单

- [ ] API Key 是否正确配置
- [ ] 网络连接是否正常
- [ ] 工具参数是否符合 schema
- [ ] 是否超出了 API 限流
- [ ] 上下文长度是否超限
- [ ] import 语句是否完整（前端检查 `message` 是否导入）

### 4.3 联系支持

如果遇到未列出的错误，请提供:
1. 完整的错误信息
2. 错误发生的上下文
3. 请求/响应的日志
4. 发生频率