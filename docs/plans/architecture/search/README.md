# search 模块开发计划

> 状态：已规划
> 与未来框架设计 v2.1 对齐

## 模块定位

search 模块是学术搜索核心，提供：
- 6源并行搜索（ArXiv/PubMed/SS/OpenAlex/CrossRef）
- MCP Server 标准化封装
- 智能速率限制
- 结果质量优化

## 与未来框架设计对应

| 未来框架设计 | 本模块任务 |
|-------------|-----------|
| MCP 协议集成 | ArXiv/PubMed/SS MCP Server |
| 速率限制 | 指数退避 + 令牌桶 + 备源切换 |
| 结果质量 | LLM 评分 + 去重 + RRF 融合 |

## 详细计划

见 `search模块开发计划.md`

## 进度追踪

- [ ] ArXiv MCP Server
- [ ] PubMed MCP Server
- [ ] SS MCP Server
- [ ] 指数退避重试
- [ ] 备源自动切换
- [ ] LLM 评分筛选

---

**版本**：v1.0
**更新日期**：2026-05-02
