# tools 模块开发计划

> 状态：已规划
> 与未来框架设计 v2.1 对齐

## 模块定位

tools 模块是工具系统核心，提供：
- PDF 解析（Marker + PDF-Extract-Kit）
- MCP 工具注册
- 公式提取
- 引文/元数据解析

## 与未来框架设计对应

| 未来框架设计 | 本模块任务 |
|-------------|-----------|
| PDF 解析升级 | Marker 主引擎 + PDF-Extract-Kit 中文/公式 |
| MCP 工具 | ToolRegistry + MCP Wrapper |
| 智能路由 | 中文/公式 → PDF-Extract-Kit |

## 详细计划

见 `tools模块开发计划.md`

## 进度追踪

- [ ] Marker 集成
- [ ] PDF-Extract-Kit 集成
- [ ] 自动路由
- [ ] 公式提取
- [ ] ToolRegistry
- [ ] MCP Wrapper

---

**版本**：v1.0
**更新日期**：2026-05-02
