# 端到端测试

## 前置条件

1. PostgreSQL 运行中（默认 localhost:5432）
2. Qdrant 运行中（默认 localhost:6333）
3. 服务已启动：

```powershell
python -m src.service --port 8000
```

## 测试文件

### test_search_to_library.py

**功能**：创建项目 → 搜索论文 → 确认入库 → 验证

**运行**：

```powershell
# 默认参数
python -m tests.e2e.test_search_to_library

# 自定义搜索词
python -m tests.e2e.test_search_to_library --query "functional PCA sparse"

# 指定数量和来源
python -m tests.e2e.test_search_to_library --query "sparse functional data" --limit 15 --sources openalex,arxiv

# 指定项目名
python -m tests.e2e.test_search_to_library --name "my_project"
```

**参数**：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--query` | sparse functional data | 搜索关键词 |
| `--limit` | 10 | 搜索数量 |
| `--sources` | openalex,arxiv,semantic_scholar | 搜索源，逗号分隔 |
| `--name` | 自动生成 | 项目名称 |

**测试流程**：

```
① 等待服务就绪（最多 15 秒）
② POST /api/rw/projects                    → 创建项目
③ POST /api/rw/projects/{id}/papers/search → 搜索论文
④ POST /api/rw/projects/{id}/papers/search/commit → 确认入库
⑤ GET  /api/rw/projects/{id}/papers        → 验证论文存在
⑥ 输出 PASS/FAIL
```

**输出示例**：

```
============================================================
端到端测试: 创建项目 → 搜索论文 → 确认入库
============================================================
服务就绪: http://localhost:8000

[1/3] 创建项目: e2e_test_1780156758
  -> project_id: proj_eb64e904

[2/3] 搜索论文: "sparse functional data"
  sources=['openalex', 'arxiv', 'semantic_scholar'], limit=5
  -> session_id: ss_1aeda1b0
  -> 找到 5 篇论文:
      1. [0.939] Functional Data Analysis for Sparse Longitudinal Data (2005) [no-pdf]
      2. [0.640] Clustering for Sparsely Sampled Functional Data (2003) [no-pdf]
      ...

[3/3] 确认入库 (5 篇)...
  -> 成功入库 5 篇

项目论文统计:
  总数:     5
  有 PDF:   1
  有摘要:   5
  验证:     PASS (期望 >= 1)

============================================================
测试通过!
项目 ID: proj_eb64e904
============================================================
```

**返回值**：
- 退出码 0 = 测试通过
- 退出码 1 = 测试失败

## 注意事项

- 测试会在数据库中创建真实项目和论文记录
- 测试完成后项目不会自动删除，需手动清理
- 搜索依赖外部 API（OpenAlex、arXiv、Semantic Scholar），网络不通会失败
- 每次运行会创建新项目（名称带时间戳），不会与已有项目冲突
