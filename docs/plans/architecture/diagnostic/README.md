# Diagnostic 诊断模块

> 标准化论文诊断体系开发计划

## 概述

本文档定义了 Paper Agent 诊断模块的开发计划，基于[学术论文诊断阶段调研报告](../../research/学术论文诊断阶段调研报告.md)设计。

## 核心设计

### 5维诊断体系

| 维度 | 权重 | 核心评估内容 |
|------|------|-------------|
| **学术规范性** | 20% | 引用格式、术语使用、结构规范 |
| **研究质量** | 25% | 创新性、严谨性、贡献度 |
| **内容完整性** | 20% | 文献覆盖、论证完整、局限承认 |
| **表达质量** | 15% | 清晰度、连贯性、语法风格 |
| **逻辑严谨性** | 20% | 因果推理、论据质量、结论推导 |

### 诊断 Agent 矩阵

| Agent | 负责维度 | 修复 Agent |
|-------|----------|------------|
| TopicDiagnostician | 选题 | TopicRefinerAgent |
| LiteratureDiagnostician | 文献综述 | LiteratureMapperAgent |
| MethodologyDiagnostician | 方法论 | MethodologyAdvisorAgent |
| ArgumentDiagnostician | 论证逻辑 | ArgumentBuilderAgent |
| ExpressionDiagnostician | 表达规范 | LanguagePolisherAgent |
| StructureDiagnostician | 结构规范 | CitationFormatterAgent |
| DiscussionDiagnostician | 讨论深度 | DiscussionDeepenerAgent |

## 开发计划

详细计划见 [diagnostic模块开发计划.md](diagnostic模块开发计划.md)

## 状态

- [x] 调研完成
- [ ] 开发计划已评审
- [ ] Phase 1: 诊断框架基础
- [ ] Phase 2: 诊断 Agent 开发
- [ ] Phase 3: 评分体系集成
- [ ] Phase 4: 诊断-修复衔接

---

**版本**: v1.0
**更新日期**: 2026-05-03