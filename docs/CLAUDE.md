# 错误码与解决方案文档

本文档记录系统中可能遇到的错误及其解决方案，供开发和调试参考。

---

## 维护规则

### 写入新错误

当遇到新的错误和解决方案时，将其添加到对应的章节中。每个错误条目应包含：
- **错误信息**：完整的错误日志或异常描述
- **原因分析**：为什么会发生这个错误
- **错误场景**：在什么情况下会触发
- **解决方案**：具体的修复代码或步骤
- **预防措施**：如何避免再次发生

### 压缩机制

当文档达到一定长度时，进行以下压缩：

1. **触发条件**：文档超过 2000 行时
2. **压缩策略**：
   - 保留最近 100 条错误记录
   - 将更早的记录合并到"历史错误"章节，只保留错误摘要和解决方案链接
   - 精简重复的代码示例，保留核心片段
   - 移除过时的错误信息（原系统/版本已不存在的）
3. **压缩频率**：每次添加新错误时检查，触发条件时执行压缩

---

## 目录

0. [维护规则](#维护规则)
1. [前端 React/Antd 错误](#1-前端-reactantd-错误)
2. [Python 网络请求错误](#2-python-网络请求错误)
3. [异步编程错误](#3-异步编程错误)
4. [MiniMax API 错误](#4-minimax-api-错误)
5. [学术数据库 API 错误](#5-学术数据库-api-错误)
6. [内部错误处理](#6-内部错误处理)
7. [后端 API 错误](#7-后端-api-错误)
   - [7.1 AI生成大纲返回404](#71-ai生成大纲返回404---paper-not-found)
   - [7.2 修正格式失败 - LLM未初始化](#72-修正格式失败---llm未初始化)
   - [7.2.1 修正格式失败 - LLM Connection error](#721-修正格式失败---llm-connection-error)
   - [7.3 论文数据时有时无](#73-论文数据时有时无服务器重启后数据丢失)
   - [7.4 切换论文时界面没有更新](#74-切换论文时界面没有更新)
8. [调试建议](#8-调试建议)
9. [历史错误（已压缩）](#9-历史错误已压缩)

---

## 1. 前端 React/Antd 错误

### 1.1 App.useMessage is not a function

**错误信息**:
```
TypeError: App.useMessage is not a function
    at HomePage (HomePage.jsx:175:45)
```

**原因分析**:
在 antd v5 中，`App` 组件没有静态方法 `useMessage`。`message.useMessage()` 是独立的 hook，不依赖 `App` 组件。

**错误场景**:
- 错误地将 `App.useMessage()` 与 `message.useMessage()` 混淆
- 在使用 `App` 组件时，尝试调用 `App.useMessage()`

**解决方案**:
使用 `message.useMessage()` hook:

```jsx
import { message } from 'antd';

const HomePage = () => {
  const [messageApi, contextHolder] = message.useMessage();

  return (
    <>
      {contextHolder}
      {/* component content */}
    </>
  );
};
```

**注意事项**:
- `message.useMessage()` 可以在任何组件中使用，不一定需要 `<App>` 包裹
- 如果需要使用 `<App>` 组件（提供全局配置和应用状态），仍然使用 `message.useMessage()` 获取 message 实例
- 不要使用 `App.useMessage()` - 这个方法不存在

---

### 1.2 Message called in render warning (React 18)

**警告信息**:
```
Warning: [antd: Message] You are calling notice in render which will break in React 18 concurrent mode. Please trigger in effect instead.
```

**原因分析**:

在 React 18 并发模式下，`message.useMessage()` 返回的 `message` API 不能在组件渲染期间调用，只能在 effect 或事件处理函数中使用。

**错误场景**:

- 在 `if (!paperId) { message.error(...) }` 这样的条件判断中直接调用 message（渲染期间）
- 在组件的 return 语句之前调用 message

**解决方案**:

改用 `App.useApp()` 获取 message 实例，这是 antd v5 推荐的方式：

```jsx
import { App } from 'antd';

const OutlinePage = () => {
  const { message } = App.useApp()
  // ...
  // 在事件处理函数或 effect 中调用
  const handleGenerateOutline = async () => {
    if (!paperTitle.trim()) {
      message.warning('请输入论文标题')  // 正确：在事件处理中
      return
    }
    // ...
  }
  // ...
}
```

**受影响的文件**:

- `OutlinePage.jsx` - 已修复
- `SettingsPage.jsx` - 已移除未使用的 message import
- `LiteraturePage.jsx` - 已移除未使用的 message import
- `ReportsPage.jsx` - 已移除未使用的 message import

**注意事项**:

- `App.useApp()` 需要组件被 `<App>` 包裹（大多数页面已由 MainLayout 提供）
- 如果确实需要在渲染时触发消息，考虑使用 `useEffect` 配合 `useRef` 或 state

---

### 1.3 Spin tip only works in nest or fullscreen pattern

**警告信息**:
```
Warning: [antd: Spin] `tip` only work in nest or fullscreen pattern.
```

**原因分析**:

antd 的 Spin 组件的 `tip` 属性只在线模式（nested）或全屏模式（fullscreen）下生效。当 Spin 作为独立元素使用时，`tip` 不会显示。

**解决方案**:

这是 cosmetic warning，不影响功能。如需显示加载提示，可以移除 `tip` 属性：

```jsx
// 原代码
<Spin tip="AI正在生成大纲..." />

// 改为（无 tip）
<Spin />
```

或者保持现状，这是一个无害的警告。

---

### 1.4 ReportsPage.jsx 中 message is not defined

**错误信息**:
```
Uncaught ReferenceError: message is not defined
    at ReportsPage (ReportsPage.jsx:102:39)
```

**原因分析**:

在 `ReportsPage.jsx` 中，虽然导入了 `message` from 'antd'，但错误发生在第 102 行而不是第 77 行（定义 `messageApi` 的位置）。这通常意味着：
1. 代码在 `messageApi` 被定义之前就尝试使用它
2. 或者某些代码路径在访问 `message` 时上下文中没有定义

**错误场景**:

组件渲染时，在 `messageApi` 被定义之前就有代码尝试调用 `message.useMessage()` 或其他 `message` 相关操作。

**解决方案**:

确保 `message.useMessage()` 在组件的最开始阶段就被调用，并且在使用 `messageApi` 之前所有条件分支都已正确处理。

```jsx
const ReportsPage = () => {
  // 确保 messageApi 在所有使用之前定义
  const [messageApi, contextHolder] = message.useMessage()

  // 然后再执行其他逻辑
  const loadKeywords = async () => {
    // ...
  }
  // ...
}
```

---

## 2. Python 网络请求错误

### 2.1 SSL 证书验证失败

**错误信息**:
```
urllib.error.URLError: <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed>
```

**原因分析**:
Python 在调用外部 API（如 arXiv、PubMed）时，默认会验证 SSL 证书。在某些环境中，证书验证会失败，导致请求失败。

**错误场景**:
- 调用 arXiv API 时连接失败
- 调用 PubMed API 时连接失败
- 没有任何错误日志，但结果为空

**解决方案**:
创建 SSL 上下文并绕过证书验证（仅用于开发/测试环境）:

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

## 3. 异步编程错误

### 3.1 在同步函数中调用 async 函数

**错误信息**:
```
TypeError: Object of type coroutine was not expected for 'generate_from_paper'
```

**原因分析**:
在同步函数中直接调用 async 函数返回的是 coroutine 对象，而不是实际结果。需要使用 `asyncio.run()` 来执行 async 函数。

**错误场景**:
- 同步函数中调用 async 方法
- 忘记使用 `asyncio.run()` 包装 async 调用

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

## 4. MiniMax API 错误

### 4.1 Invalid tool parameters / Content block is not a input_json block

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

### 4.2 Rate Limit Error (429)

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

### 4.3 Context Overflow Error

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

### 4.4 Authentication Error

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

## 5. 学术数据库 API 错误

### 5.1 arXiv API 错误

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

### 5.2 PubMed API 错误

**错误信息**:
```
PubMed API error: Invalid API key or rate limit exceeded
```

**解决方案**:
1. 检查 PubMed API Key 配置
2. 实施请求间隔和重试机制

---

### 5.3 Semantic Scholar API 错误

**错误信息**:
```
Semantic Scholar API error: Request blocked due to rate limiting
```

**解决方案**:
```python
SEMANTIC_SCHOLAR_RATE_LIMIT = 1  # 每秒请求数
```

---

## 6. 内部错误处理

### 6.1 错误分类

| 错误类别 | 说明 | 处理策略 |
|---------|------|---------|
| `INVALID_INPUT` | 输入参数无效 | 验证并返回错误信息 |
| `TIMEOUT` | 操作超时 | 重试或使用缓存 |
| `LLM_RATE_LIMIT` | LLM API 限流 | 退避重试 |
| `LLM_CONTEXT_OVERFLOW` | 上下文溢出 | 截断或总结历史 |
| `EXTERNAL_API_FAILURE` | 外部 API 失败 | 重试或降级 |
| `VALIDATION_FAILURE` | 验证失败 | 返回详细错误 |

### 6.2 错误恢复策略

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

## 7. 后端 API 错误

### 7.1 AI生成大纲返回404 - Paper not found

**错误信息**:
```
生成失败: Request failed with status code 404
```

**原因分析**:

1. **论文ID不存在**：前端调用 `/api/papers/{id}/outline/generate` 时，`project?.id` 为空。用户没有先在写作页面创建论文。

2. **环境变量未加载**：服务器启动时 `DEFAULT_API_KEY` 被设置为 `"dev-api-key"` 占位符，`load_dotenv()` 没有在正确的时机加载 `.env` 文件中的真实 API Key。

**错误场景**:

1. 用户直接进入"AI生成大纲"页面，没有先创建论文
2. 服务器重启后内存存储的论文数据丢失
3. API Key 配置在 `.env` 文件中但服务器启动时未正确加载

**解决方案**:

**前端修复**（OutlinePage.jsx）：在没有论文ID时自动创建论文

```javascript
const handleGenerateOutline = async () => {
  // ...
  let paperId = project?.id

  // 如果没有论文ID，先创建一个
  if (!paperId) {
    const createResult = await paperAPI.createPaper({
      title: paperTitle,
      topic: ''
    })
    if (createResult.success && createResult.data) {
      paperId = createResult.data.id
      setProject(createResult.data)
    } else {
      message.error('创建论文失败')
      setGenerating(false)
      return
    }
  } else {
    // 更新论文标题
    await paperAPI.updatePaper(paperId, { title: paperTitle })
  }

  const result = await paperAPI.generateOutline(paperId, paperTitle)
  // ...
}
```

**后端修复**：确保 `load_dotenv()` 在读取环境变量之前执行

```python
# 加载 .env 文件
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# 读取环境变量（load_dotenv 之后）
DEFAULT_API_KEY = os.getenv("OPENAI_API_KEY", "dev-api-key")
DEFAULT_BASE_URL = os.getenv("OPENAI_BASE_URL", None)
```

**预防措施**:

1. 前端已修复：会在没有论文时自动创建
2. 后端环境变量加载时机已调整
3. 论文数据应考虑持久化存储（当前为内存存储）

---

### 7.2 修正格式失败 - LLM未初始化

**错误信息**:
```
TypeError: 'LLMConfig' object has no attribute 'timeout'
修正格式错误: AxiosError: Request failed with status code 500
```

**原因分析**:

`LLMConfig` 类缺少 `timeout` 属性，导致 `LanguagePolisherAgent` 初始化时 LLM 失败。

**错误场景**:

1. 调用"修正格式"接口时返回 500 错误
2. 日志显示 "LLM初始化失败: 'LLMConfig' object has no attribute 'timeout'"

**解决方案**:

在 `LLMConfig` 类中添加 `timeout` 属性：

```python
class LLMConfig(BaseModel):
    """LLM配置"""
    provider: str = Field(default="openai", description="LLM提供商")
    model_name: str = Field(default="gpt-4", description="模型名称")
    temperature: float = Field(default=0.7, description="温度参数")
    max_tokens: int = Field(default=4096, description="最大token数")
    api_key: Optional[str] = Field(None, description="API密钥")
    base_url: Optional[str] = Field(None, description="API基础URL")
    timeout: int = Field(default=180, description="超时时间(秒)")
```

**受影响的文件**: `src/agents_v2/paper_agents/base_paper_agent.py`

**预防措施**:
确保 `LLMConfig` 包含所有 LLM 调用需要的属性

---

**错误信息**:
```
修正格式失败: Request failed with status code 404
```

**原因分析**:

1. **章节内容为空**：最常见的原因。前端调用 `/api/papers/{id}/sections/{sectionId}/format` 时，`content` 字段为空。

2. **编码问题**（Windows + curl）：在 Windows 系统上使用 curl 发送中文内容时，如果 curl 使用 GBK 编码而非 UTF-8 编码请求体，会导致后端无法正确解析 JSON。

   - 错误编码的 body (GBK): `7b22636f6e74656e74223a2022b2e2cad4c4dac8dd227d`
   - 正确编码的 body (UTF-8): `7b22636f6e74656e74223a20225c75366434625c75386264355c75353138355c7535626239227d`

3. **论文不存在或已过期**：内存存储的论文数据丢失（服务器重启后会清空）。

**错误场景**:

1. 用户没有先生成内容，直接点击"修正格式"按钮
2. 章节内容编辑器为空
3. 使用 curl 在 Windows 上测试 API 时发送中文内容

**排查步骤**:

1. 打开浏览器开发者工具 (F12) → Network 标签
2. 点击"修正格式"按钮
3. 查看请求 `/api/papers/{id}/sections/{sectionId}/format`
4. 检查 Request Body 中 `content` 字段是否有值

**解决方案**:

1. **确保章节有内容**：先点击"生成内容"按钮填充章节内容，再进行"修正格式"操作
2. **创建新论文**：如果论文数据丢失，重新创建论文
3. **使用正确的编码**：如果用 Python 测试，使用 `json.dumps().encode('utf-8')` 确保 UTF-8 编码

```python
# 正确的做法 - Python
import urllib.request
import json

data = json.dumps({'content': '测试内容'}).encode('utf-8')
req = urllib.request.Request(
    'http://localhost:8000/api/papers/{id}/sections/{sectionId}/format',
    data=data,
    headers={
        'Content-Type': 'application/json',
        'X-API-Key': 'dev-api-key'
    },
    method='POST'
)
```

**后端日志示例**:

启用全链路追踪后，日志会显示详细信息：

```
[FORMAT_REQUEST] paper_id=xxx, section_id=1
[FORMAT_REQUEST] provided_content_length=0, preview=EMPTY           # content 为空
[FORMAT_REQUEST] raw_body_hex=7b22636f6e74656e74223a2022b2...      # 可用于检查编码
[FORMAT_REQUEST] paper_id=xxx, found=True
[FORMAT_REQUEST] section_id=1, title=1, content_length=0
```

**预防措施**:

1. 前端在调用"修正格式"前检查 `sectionContent` 是否为空，为空时给出提示
2. 后端已添加详细日志，可通过日志查看请求内容、编码和链路追踪信息
3. 论文数据已实现持久化存储（见 7.3）

---

**错误信息**:
```
修正格式失败: Connection error.
修正格式失败: object of type 'NoneType' has no len()
```

**原因分析**:

1. **LLM 连接失败**：无法连接到 LLM 服务（网络问题或 API 配置错误）
2. **polished_text 为 None**：当 LLM 调用失败时，降级润色也失败，导致 `result.result` 为 `None`

**错误场景**:

1. LLM API 服务不可用或网络不通
2. API Key 配置错误
3. 代理/防火墙阻止了请求

**解决方案**:

1. 检查 LLM 服务是否可用
2. 验证 API Key 和 base_url 配置
3. 检查网络连接

```bash
# 测试 LLM 连接
curl -X POST "https://api.minimax.chat/v1/text/chatcompletion_v2" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"MiniMax-M2.7","messages":[{"role":"user","content":"Hello"}]}'
```

**后端日志示例**:

```
LLM初始化失败: Connection error.
LanguagePolisherAgent execution failed: Connection error.
Fallback polish failed: Connection error.
Success: False
Error: Connection error.
Result type: <class 'NoneType'>
Result: None
```

**预防措施**:

1. 添加更完善的 LLM 调用重试机制
2. 当 LLM 失败时返回更有意义的错误信息给前端
3. 考虑添加 LLM 服务健康检查

---

### 7.3 论文数据时有时无（服务器重启后数据丢失）

**错误信息**:
服务器重启后，之前创建的论文全部消失。

**原因分析**:
论文数据存储在内存字典 `PAPERS_STORAGE` 中，服务器重启后内存数据被清空。

**解决方案**:
实现文件持久化，将论文数据保存到 JSON 文件中。

```python
# 文件持久化路径
STORAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data")
PAPERS_FILE = os.path.join(STORAGE_DIR, "papers_storage.json")

def load_papers_storage() -> Dict[str, Dict]:
    """从文件加载论文存储"""
    if os.path.exists(PAPERS_FILE):
        with open(PAPERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_papers_storage(storage: Dict[str, Dict]) -> None:
    """保存论文存储到文件"""
    with open(PAPERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(storage, f, ensure_ascii=False, indent=2)

# 启动时加载
PAPERS_STORAGE: Dict[str, Dict] = load_papers_storage()

# 在 create/update/delete 操作后保存
PAPERS_STORAGE[paper_id] = paper
save_papers_storage(PAPERS_STORAGE)
```

**存储位置**: `data/papers_storage.json`

**预防措施**:
1. 所有论文操作后自动保存到文件
2. 服务器启动时自动从文件恢复数据

---

### 7.4 切换论文时界面没有更新

**错误信息**:
切换论文后，左侧章节树和右侧编辑器内容没有变化。

**原因分析**:
切换论文时只更新了 `project` 和 `paperTitle`，没有重置 `selectedSection` 和 `sectionContent` 状态。

**错误场景**:
在论文列表选择不同的论文后，界面显示的仍是原论文的内容。

**解决方案**:
在 Select 的 onChange 中重置章节选择状态：

```javascript
<Select
  value={project?.id}
  onChange={(paperId) => {
    const paper = papers.find(p => p.id === paperId)
    if (paper) {
      setProject(paper)
      setPaperTitle(paper.title || '未命名论文')
      // 切换论文时重置章节选择
      if (paper.sections && paper.sections.length > 0) {
        setSelectedSection(paper.sections[0].id)
        setSectionContent(paper.sections[0].content || '')
      } else {
        setSelectedSection('')
        setSectionContent('')
      }
    }
  }}
>
```

**受影响的文件**: `frontend/src/pages/WritingPage.jsx`

**预防措施**:
切换论文时始终重置章节选择状态为新论文的第一个章节

---

## 8. 调试建议

### 8.1 启用详细日志

```python
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
```

### 8.2 常见错误快速检查清单

- [ ] API Key 是否正确配置
- [ ] 网络连接是否正常
- [ ] 工具参数是否符合 schema
- [ ] 是否超出了 API 限流
- [ ] 上下文长度是否超限

### 8.3 联系支持

如果遇到未列出的错误，请提供:
1. 完整的错误信息
2. 错误发生的上下文
3. 请求/响应的日志
4. 发生频率

---

## 9. 历史错误（已压缩）

此章节存放较旧的错误记录，仅保留摘要。详细信息可能已精简。

<!-- 压缩时将旧错误移至此处的摘要格式：
### 历史错误标题
**摘要**：简要描述  
**状态**：已解决/已绕过/已废弃  
**参考**：原章节编号或日期
-->
