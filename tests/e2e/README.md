# 端到端测试

## 前置条件

1. PostgreSQL 运行中（默认 localhost:5432）
2. Qdrant 运行中（默认 localhost:6333）
3. 服务已启动：

```powershell
python -m src.service --port 8000
```

---

### test_search_to_library.py

**功能**：创建项目 → 搜索论文 → 确认入库 → 验证 → 删除项目

**完整示例**：

```powershell
# ① 默认参数（搜索 "sparse functional data"，10 篇，三个来源，测试后自动删除）
python -m tests.e2e.test_search_to_library

# ② 自定义搜索词
python -m tests.e2e.test_search_to_library --query "functional PCA sparse"

# ③ 指定数量和来源
python -m tests.e2e.test_search_to_library --query "sparse functional data" --limit 15 --sources openalex,arxiv

# ④ 指定项目名称
python -m tests.e2e.test_search_to_library --name "my_project"

# ⑤ 测试后保留项目（不删除）
python -m tests.e2e.test_search_to_library --query "neural networks" --no-cleanup

# ⑥ 完整参数示例
python -m tests.e2e.test_search_to_library --query "deep learning" --limit 20 --sources openalex,arxiv,semantic_scholar --name "dl_project" --no-cleanup
```

**参数**：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--query` | `sparse functional data` | 搜索关键词 |
| `--limit` | `10` | 搜索数量 |
| `--sources` | `openalex,arxiv,semantic_scholar` | 搜索源，逗号分隔 |
| `--name` | 自动生成（`e2e_test_<时间戳>`） | 项目名称 |
| `--no-cleanup` | 不设置（默认删除） | 测试后保留项目，不删除 |

**测试流程**：

```
① 等待服务就绪（最多 15 秒）
② POST /api/rw/projects                    → 创建项目
③ POST /api/rw/projects/{id}/papers/search → 搜索论文
④ POST /api/rw/projects/{id}/papers/search/commit → 确认入库
⑤ GET  /api/rw/projects/{id}/papers        → 验证论文存在
⑥ DELETE /api/rw/projects/{id}             → 删除项目（默认）
⑦ GET  /api/rw/projects/{id}              → 验证项目已删除
⑧ 输出 PASS/FAIL
```

**输出示例**：

```
============================================================
端到端测试: 创建项目 → 搜索论文 → 确认入库 → 删除项目
============================================================
服务就绪: http://localhost:8000

[1/4] 创建项目: e2e_test_1780156758
  -> project_id: proj_eb64e904

[2/4] 搜索论文: "sparse functional data"
  sources=['openalex', 'arxiv', 'semantic_scholar'], limit=10
  -> session_id: ss_1aeda1b0
  -> 找到 10 篇论文:
      1. [0.939] Functional Data Analysis for Sparse Longitudinal Data (2005) [PDF]
      2. [0.640] Clustering for Sparsely Sampled Functional Data (2003) [no-pdf]
      ...

[3/4] 确认入库 (10 篇)...
  -> 成功入库 10 篇
     p_001: Functional Data Analysis for Sparse...
     ...

项目论文统计:
  总数:     10
  有 PDF:   3
  有摘要:   8
  验证:     PASS (期望 >= 1)

[4/4] 删除项目: proj_eb64e904
  -> 删除成功，清理了 10 篇论文的向量数据
  验证:     PASS (项目已删除)

============================================================
测试通过!
============================================================
```

**返回值**：
- 退出码 `0` = 测试通过
- 退出码 `1` = 测试失败

---

### test_ranking.py

**功能**：验证搜索排序 — 摘要权重是否高于标题权重，过滤无关论文

**完整示例**：

```powershell
# ① 默认参数（搜索 "sparse functional data"，20 篇）
python -m tests.e2e.test_ranking

# ② 自定义搜索词
python -m tests.e2e.test_ranking --query "functional PCA"

# ③ 指定数量和来源
python -m tests.e2e.test_ranking --query "sparse functional data" --limit 30 --sources openalex,arxiv

# ④ 只用 Semantic Scholar
python -m tests.e2e.test_ranking --query "sparse functional principal component" --sources semantic_scholar
```

**参数**：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--query` | `sparse functional data` | 搜索关键词 |
| `--limit` | `20` | 搜索数量 |
| `--sources` | `openalex,arxiv,semantic_scholar` | 搜索源，逗号分隔 |

**测试流程**：

```
① 等待服务就绪（最多 15 秒）
② POST /api/rw/projects                    → 创建临时项目
③ POST /api/rw/projects/{id}/papers/search → 搜索论文
④ 检查分数是否降序排列
⑤ 检查摘要相关性（摘要中查询词覆盖率 ≥ 50% 为相关）
⑥ DELETE /api/rw/projects/{id}             → 删除临时项目
⑦ 输出 PASS/FAIL
```

**输出示例**：

```
============================================================
端到端测试: 搜索排序验证
============================================================
服务就绪: http://localhost:8000

[1/4] 创建临时项目...
  -> proj_tmp1234

[2/4] 搜索: "sparse functional data"
  sources=['openalex', 'arxiv', 'semantic_scholar'], limit=20
  -> 找到 20 篇

前 10 个结果:
--------------------------------------------------------------------------------
   1. [0.939] rel=0.935 qual=0.612 | Functional Data Analysis for Sparse Longitudinal Data
      摘要: 380字
   2. [0.640] rel=0.580 qual=0.421 | Clustering for Sparsely Sampled Functional Data
      摘要: 295字
   ...

[3/4] 检查分数排序...
  PASS: 分数降序正确

[4/4] 检查摘要相关性...
  相关论文: 15/20 (75%)
  问题论文:
    [ 6] 摘要相关度低 (1/3) [0.320]: Some Unrelated Paper Title
    [12] 标题匹配但摘要无关 [0.280]: Another Paper With Generic Title

清理临时项目...

============================================================
测试通过!
  排序: PASS
  相关性: 15/20 (75%) PASS
============================================================
```

**判断标准**：
- 排序：分数必须严格降序排列
- 相关性：摘要中查询词覆盖率 ≥ 50% 的论文占比需 ≥ 50%

**返回值**：
- 退出码 `0` = 测试通过
- 退出码 `1` = 测试失败

---

### test_delete_project.py

**功能**：删除指定项目并清理关联数据（PostgreSQL + Qdrant 向量）

**完整示例**：

```powershell
# ① 按项目 ID 删除（需确认）
python -m tests.e2e.test_delete_project --id proj_eb64e904

# ② 按项目名称删除（需唯一匹配）
python -m tests.e2e.test_delete_project --name "my_project"

# ③ 跳过确认提示，直接删除
python -m tests.e2e.test_delete_project --id proj_eb64e904 --force

# ④ 列出所有项目（不删除）
python -m tests.e2e.test_delete_project --list
```

**参数**：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--id` | 无（必填，除非用 `--name`） | 项目 ID |
| `--name` | 无（必填，除非用 `--id`） | 按名称查找项目（需唯一匹配） |
| `--list` | 不设置 | 列出所有项目后退出 |
| `--force` | 不设置 | 跳过确认提示，直接删除 |

**测试流程**：

```
① 等待服务就绪（最多 15 秒）
② GET  /api/rw/projects          → 查找/列出项目
③ GET  /api/rw/projects/{id}     → 显示项目详情和论文统计
④ DELETE /api/rw/projects/{id}   → 删除项目
⑤ GET  /api/rw/projects/{id}     → 验证项目已删除（期望 404）
⑥ 输出 PASS/FAIL
```

**输出示例**：

```
============================================================
端到端测试: 删除项目
============================================================
服务就绪: http://localhost:8000

[1/3] 查找项目...

项目详情:
  ID:       proj_eb64e904
  名称:     my_project
  创建时间: 2026-05-31T00:25:18
  论文总数: 10
  有 PDF:   3
  有摘要:   8

确认删除? (y/N): y

[2/3] 删除项目...
删除项目: proj_eb64e904
  -> 删除成功，清理了 10 篇论文的向量数据

[3/3] 验证删除...
  验证: PASS (项目已删除)

============================================================
测试通过!
============================================================
```

**返回值**：
- 退出码 `0` = 测试通过或删除成功
- 退出码 `1` = 测试失败或参数错误

---

## 注意事项

- 测试会在数据库中创建真实项目和论文记录
- `test_search_to_library.py` 默认会在测试完成后删除项目，使用 `--no-cleanup` 可保留
- `test_delete_project.py` 默认需要手动确认，使用 `--force` 可跳过
- 搜索依赖外部 API（OpenAlex、arXiv、Semantic Scholar），网络不通会失败
- 删除操作会同时清理 PostgreSQL 数据和 Qdrant 向量数据
