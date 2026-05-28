# BaseAgent 核心基类详解

> 位置: `src/agents_v2/core/base_agent.py` (12,218 字节)

## 一、类结构

```
BaseAgent (ABC)
├── __init__(llm_config: LLMConfig)
├── execute(user_input: str) → AgentOutput
├── _init_llm() → ChatOpenAI
├── _build_messages(user_input: str) → List[BaseMessage]
├── _llm_call(prompt: str) → str
├── _parse_response(raw_text: str) → AgentOutput
└── _clean_thinking_blocks(text: str) → str
```

## 二、核心属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `llm_config` | LLMConfig | 模型配置 (model, api_key, base_url, temperature) |
| `llm` | ChatOpenAI | LangChain LLM 实例 |
| `system_prompt` | str | Agent 系统提示词 |
| `agent_name` | str | Agent 名称标识 |

## 三、执行流程

```
execute(user_input)
  │
  ├─ 1. _init_llm()
  │    └─ langchain_openai.ChatOpenAI(
  │         model=llm_config.model,
  │         base_url=llm_config.base_url,
  │         api_key=llm_config.api_key,
  │         temperature=llm_config.temperature
  │       )
  │
  ├─ 2. _build_messages(user_input)
  │    └─ [SystemMessage(system_prompt), HumanMessage(user_input)]
  │
  ├─ 3. _llm_call(prompt)
  │    └─ llm.ainvoke(messages)
  │        → HTTP POST → OpenAI-compatible API
  │
  ├─ 4. _clean_thinking_blocks(raw_response)
  │    ├─ 移除 <think>... 块
  │    ├─ 截断参考文献
  │    ├─ 剥离 markdown 代码围栏
  │    └─ 修复 UTF-8 字节转义
  │
  └─ 5. _parse_response(cleaned_text)
       └─ json.loads(text)
          → AgentOutput(success, result, quality_score, next_actions)
```

## 四、LLMConfig 配置

```python
class LLMConfig:
    model: str          # 模型名: "miniMax/M2.7"
    api_key: str        # API 密钥
    base_url: str       # API 地址: "https://api.minimax.chat/v1"
    temperature: float  # 随机性: 0.0-1.0 (默认 0.7)
    max_tokens: int     # 最大 token 数
    timeout: int        # 超时秒数
```

支持的模型类别:
- **OpenAI**: GPT-4o, GPT-4, GPT-3.5
- **Anthropic**: Claude Opus 4, Claude Sonnet 4
- **MiniMax**: M2.7, M1
- **DeepSeek**: R1, V3
- **Qwen**: Max, Plus, Turbo
- **GLM**: 4, 4-Flash

## 五、AgentOutput 结构

```python
class AgentOutput(BaseModel):
    success: bool                      # 是否成功
    result: Any                        # 执行结果
    agent_name: str                    # Agent 名称
    reasoning: str                     # 思考过程
    quality_score: float               # 质量评分 (0-10)
    next_actions: List[str]            # 建议的下一步
    metadata: Dict[str, Any]           # 元数据
    error: Optional[str]              # 错误信息
```

## 六、Prompt 清洗逻辑

```python
def _clean_thinking_blocks(text: str) -> str:
    # 1. 移除思考块
    text = re.sub(r'<think>.*?', '', text, flags=re.DOTALL)

    # 2. 截断参考文献
    text = re.sub(r'##?\s*参考文献.*$', '', text, flags=re.MULTILINE)

    # 3. 移除代码围栏
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)

    # 4. 修复 UTF-8 字节转义
    text = re.sub(r'\\x([0-9a-fA-F]{2})', lambda m: bytes.fromhex(m.group(1)).decode('utf-8'), text)

    # 5. 去除控制字符
    text = re.sub(r'[\x00-\x08]', '', text)

    return text.strip()
```

## 七、子类实现

| Agent | 文件 | 主要功能 |
|-------|------|----------|
| TopicAgent | paper_agents/topic_agent.py | 选题生成 |
| LiteratureAgent | paper_agents/literature_agent.py | 文献综述 |
| OutlineAgent | paper_agents/outline_agent.py | 大纲制定 |
| DraftWriterAgent | paper_agents/draft_writer.py | 初稿撰写 |
| DigestReportAgent | paper_agents/digest_agent.py | 摘要生成 |

## 八、MiniMax 特殊适配

```python
# reasoning_split: False 防止模型分离思考过程
extra_body = {"reasoning_split": False}
ChatOpenAI(
    model="MiniMax/M2.7",
    extra_headers={"X-API-Key": api_key},
    extra_body=extra_body
)
```

---

**更新日期**: 2026-05-02
**基于代码**: `src/agents_v2/core/base_agent.py`