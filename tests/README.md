# Paper Agent 测试套件

## 快速开始

```bash
# 运行所有测试
python tests/run_all_tests.py

# 或者直接用 pytest
python -m pytest tests/ -v
```

## 测试文件说明

| 文件 | 测试数 | 说明 |
|------|:------:|------|
| `test_api_comprehensive.py` | 28 | API 接口单元测试 |
| `test_e2e_paper_generation.py` | 11 | 端到端论文生成全链路测试 |
| `run_all_tests.py` | - | 统一测试入口 |

## 运行方式

### 统一入口

```bash
python tests/run_all_tests.py all      # 运行所有测试
python tests/run_all_tests.py api      # 只运行 API 测试
python tests/run_all_tests.py e2e      # 只运行端到端测试
python tests/run_all_tests.py quick    # 快速测试（遇错即停）
python tests/run_all_tests.py report   # 运行并显示耗时报告
```

### 直接用 pytest

```bash
# 运行所有测试
python -m pytest tests/test_api_comprehensive.py tests/test_e2e_paper_generation.py -v

# 只运行某一类
python -m pytest tests/test_e2e_paper_generation.py -v -s

# 运行单个测试
python -m pytest tests/test_e2e_paper_generation.py::TestFullPipeline::test_full_pipeline_topic_to_final_paper -v -s
```

## 测试覆盖范围

### API 单元测试 (test_api_comprehensive.py)

| 测试类 | 测试内容 |
|--------|---------|
| `TestPaperCRUD` | 论文创建、列表、查询、更新、删除，含 404 场景 |
| `TestOutlineOperations` | 大纲获取、空大纲处理 |
| `TestSettingsOperations` | 设置读取与更新 |
| `TestChatOperations` | 聊天历史、会话管理 |
| `TestLiteratureOperations` | 文献添加、查询、引用格式（APA/MLA/IEEE） |
| `TestKnowledgeGraphOperations` | 知识图谱获取与生成 |
| `TestEdgeCases` | 最小数据创建、部分更新、分页、存储持久化 |
| `TestIntegrationScenarios` | 完整论文生命周期、多论文管理 |

### 端到端测试 (test_e2e_paper_generation.py)

| 测试类 | 测试内容 |
|--------|---------|
| `TestOutlineGeneration` | OutlineAgent 生成大纲结构，LLM 失败降级处理 |
| `TestContentGeneration` | DraftWriterAgent 单章/多章内容生成 |
| `TestContentPolishing` | LanguagePolisherAgent 内容润色 |
| `TestApiIntegration` | API 层面的论文创建、大纲生成、内容生成、格式修正 |
| `TestFullPipeline` | **全链路**: 主题 → 大纲 → 逐章草稿 → 润色 → 组装最终论文 |
| `TestPipelineReport` | 全链路运行并生成详细报告 |

## 全链路测试流程

```
输入: 论文主题
  │
  ├─ Step 1: OutlineAgent 生成大纲
  │    ├─ 设计章节结构
  │    ├─ 规划各章内容
  │    └─ 确定关键论点
  │
  ├─ Step 2: DraftWriterAgent 逐章生成草稿
  │    ├─ 第1章: 技术演进与挑战
  │    ├─ 第2章: 模型设计
  │    ├─ 第3章: 对话建模
  │    ├─ 第4章: 实验评估
  │    └─ 第5章: 系统部署
  │
  ├─ Step 3: LanguagePolisherAgent 润色各章
  │
  └─ 输出: 完整论文
```

## 注意事项

- 测试使用 mock LLM，不会发起真实 API 调用
- 每个测试前后会自动清理存储数据
- 端到端测试会打印详细的流水线日志（用 `-s` 参数查看）
