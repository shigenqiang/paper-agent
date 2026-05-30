# 搜索质量测试

测试搜索结果的相关性、排序准确性、LLM过滤效果。

## 测试文件

| 文件 | 用途 |
|------|------|
| `test_search_quality.py` | 对比测试：短语匹配 vs LLM过滤 vs 无筛选 |
| `test_ranking.py` | 排序准确性验证：分数递减 + 摘要相关性 |

## 运行方式

```bash
# 搜索质量对比测试（4种方案对比，输出报告到 docs/search-quality-report.md）
python -m tests.search_quality.test_search_quality

# 排序准确性测试
python -m tests.search_quality.test_ranking --query "sparse functional data"

# 自定义查询
python -m tests.search_quality.test_ranking --query "transformer attention mechanism"
```

## 测试方案说明

`test_search_quality.py` 对比以下4种方案：

| 方案 | 短语匹配加分 | min_score | LLM过滤 |
|------|------------|-----------|---------|
| 场景1 | 开 | 关 | 关 |
| 场景2 | 开 | 0.3 | 关 |
| 场景3 | 开 | 关 | 开 |
| 场景4 | 开 | 0.3 | 开 |

## 测试结果

测试报告输出到 `docs/search-quality-report.md`，包含：
- 各方案精准率对比
- 耗时与 Token 消耗
- 详细论文列表（标记相关/不相关）
- 优化建议

## 相关性判断标准

- 论文标题或摘要必须同时包含查询中的核心关键词
- 仅包含泛词（如 "deep learning"、"data"）的论文判定为不相关
