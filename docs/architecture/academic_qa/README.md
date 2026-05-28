# Academic QA System

> 版本：v1.0
> 更新日期：2026-05-03

## 概述

学术问答系统，提供基于论文的智能问答、对比分析等功能。

## 核心组件

| 组件 | 文件 | 说明 |
|------|------|------|
| System | system.py | 学术 QA 主系统 |
| AnswerGenerator | answer_generator.py | 答案生成器 |
| AnswerAggregator | answer_aggregator.py | 多答案聚合 |
| QueryDecomposer | query_decomposer.py | 查询分解 |
| MultiHopReasoner | multi_hop_reasoner.py | 多跳推理 |
| HybridRetriever | hybrid_retriever.py | 混合检索 |
| RAGAS Evaluator | ragas_evaluator.py | RAGAS 评估 |
| Self-RAG | self_rag.py | 自检索增强生成 |
| CRAG | crag.py | 置信度检索增强 |
| HallucinationDetector | hallucination_detector.py | 幻觉检测 |
| ConfidenceCalibrator | confidence_calibrator.py | 置信度校准 |
| ChunkedDocParser | chunker.py | 分块文档解析 |
| DocParser | doc_parser.py | 文档解析 |
| CitationTracker | citation_tracker.py | 引用追踪 |
| KGIntegration | kg_integration.py | 知识图谱集成 |

## 架构

```
用户问题
  → QueryDecomposer (分解)
  → HybridRetriever (混合检索)
  → Self-RAG / CRAG (增强)
  → MultiHopReasoner (多跳推理)
  → AnswerGenerator (生成)
  → AnswerAggregator (聚合)
  → HallucinationDetector + ConfidenceCalibrator (质量检查)
  → 最终答案
```

## 评估指标

- RAGAS: faithfulness, answer_relevancy, context_relevancy
- 幻觉检测率
- 多跳推理准确率
