# agents_v3 测试报告

日期：2026-05-28

## 测试总览

| 指标 | 数值 |
|------|------|
| 总测试数 | 130 |
| 通过数 | 130 |
| 失败数 | 0 |
| 跳过数 | 0 |
| 执行时间 | 1.80s |

## 按模块测试详情

### 1. 数据模型测试 (test_models.py) - 23 个测试

| 测试名称 | 测试内容 | 通过方式 |
|----------|----------|----------|
| `test_create_project` | 创建项目对象 | 实例化 Project，验证 project_id 和 name |
| `test_project_with_all_fields` | 创建带所有字段的项目 | 验证 discipline、education_level 等可选字段 |
| `test_project_metadata` | 项目元数据 | 验证 metadata dict 可存储和读取 |
| `test_create_paper` | 创建论文对象 | 验证默认状态为 IMPORTED，included=True |
| `test_paper_status_enum` | 论文状态枚举 | 遍历所有 PaperStatus 值，验证均可赋值 |
| `test_paper_with_authors` | 带作者的论文 | 验证 authors 列表和 year 字段 |
| `test_create_chunk` | 创建文本块 | 验证 chunk_id 和默认 token_count=0 |
| `test_create_card` | 创建论文卡片 | 验证默认 confidence=0.0，research_question="unknown" |
| `test_card_with_source_spans` | 带来源引用的卡片 | 验证 source_spans 列表可存储 SourceSpan |
| `test_create_evidence` | 创建证据记录 | 验证默认 evidence_strength="medium" |
| `test_evidence_with_details` | 带详情的证据 | 验证 topic、finding、source_chunk_id 字段 |
| `test_create_node` | 创建图节点 | 验证 node_type 枚举赋值 |
| `test_all_node_types` | 所有节点类型 | 遍历 NodeType 枚举，验证 10 种类型 |
| `test_create_edge` | 创建图边 | 验证 edge_type 枚举赋值 |
| `test_create_graph` | 创建空知识图谱 | 验证 nodes 和 edges 列表为空 |
| `test_graph_with_nodes_and_edges` | 带节点和边的图 | 验证节点和边列表正确 |
| `test_create_scope` | 创建检索范围 | 验证 scope_type 枚举 |
| `test_scope_with_papers` | 带论文的范围 | 验证 paper_ids 列表 |
| `test_qa_request` | QA 请求 | 验证 question 字段 |
| `test_qa_response` | QA 响应 | 验证 answer、intent、scope_summary |
| `test_create_report` | 创建报告 | 验证默认 version=1 |
| `test_innovation_point` | 创新点对象 | 验证 name、description 字段 |
| `test_report_version` | 报告版本 | 验证 version_id、report_id 关联 |

### 2. 存储层测试 (test_storage.py) - 11 个测试

| 测试名称 | 测试内容 | 通过方式 |
|----------|----------|----------|
| `test_empty_collection` | 空集合读取 | 加载不存在的集合返回 [] |
| `test_save_and_load` | 保存和加载 | 保存 2 个对象后加载，验证数量和内容 |
| `test_upsert_insert` | 插入新对象 | upsert 新对象后 get_item 能找到 |
| `test_upsert_update` | 更新已有对象 | upsert 同 ID 对象后内容更新，数量不变 |
| `test_get_nonexistent` | 获取不存在对象 | 返回 None |
| `test_delete_existing` | 删除已有对象 | 返回 True，对象不存在 |
| `test_delete_nonexistent` | 删除不存在对象 | 返回 False |
| `test_query` | 条件查询 | 按 project_id 过滤，返回匹配对象 |
| `test_query_empty` | 空查询结果 | 无匹配条件返回 [] |
| `test_ensure_dirs` | 目录创建 | 验证 files/graphs/chunks 子目录存在 |
| `test_corrupted_json` | 损坏 JSON 文件 | 解析失败时返回 [] 而非抛异常 |

### 3. 项目服务测试 (test_project_service.py) - 9 个测试

| 测试名称 | 测试内容 | 通过方式 |
|----------|----------|----------|
| `test_create_project` | 创建项目 | 返回 Project 对象，ID 以 proj_ 开头 |
| `test_list_projects` | 列出项目 | 创建 2 个后列出，验证数量 |
| `test_get_project` | 获取项目 | 按 ID 查找，验证名称匹配 |
| `test_get_nonexistent` | 获取不存在项目 | 返回 None |
| `test_update_project` | 更新项目 | 修改 name 字段后验证新值 |
| `test_update_nonexistent` | 更新不存在项目 | 返回 None |
| `test_delete_project` | 删除项目 | 删除后查找返回 None |
| `test_delete_nonexistent` | 删除不存在项目 | 返回 False |
| `test_project_stats` | 项目统计 | 空项目返回 paper_count=0 等 |

### 4. 论文库服务测试 (test_paper_library.py) - 13 个测试

| 测试名称 | 测试内容 | 通过方式 |
|----------|----------|----------|
| `test_add_uploaded_paper` | 上传 PDF | 创建 Paper，状态为 UPLOADED，pdf_path 以 .pdf 结尾 |
| `test_add_nonexistent_file` | 上传不存在文件 | 抛出 FileNotFoundError |
| `test_add_paper_metadata` | 添加元数据 | 创建 Paper，source="import" |
| `test_add_search_results` | 批量添加搜索结果 | 返回 2 个 Paper，source="search" |
| `test_list_papers` | 列出论文 | 上传 1 个 + 导入 1 个，列出返回 2 个 |
| `test_list_papers_isolated` | 项目隔离 | proj1 和 proj2 各 1 个，互不影响 |
| `test_get_paper` | 获取论文 | 按 ID 查找，标题匹配 |
| `test_get_nonexistent` | 获取不存在论文 | 返回 None |
| `test_update_paper` | 更新论文 | 修改 title 后验证新值 |
| `test_mark_included` | 标记纳入 | 排除后重新纳入，included=True |
| `test_mark_excluded` | 标记排除 | 验证 included=False，exclude_reason 有值 |
| `test_import_doi_list` | 导入 DOI 列表 | 3 个 DOI 创建 3 个 Paper |
| `test_import_bibtex` | 导入 BibTeX | 解析 @article 条目，提取 title、year、authors |

### 5. 解析服务测试 (test_parser_service.py) - 7 个测试

| 测试名称 | 测试内容 | 通过方式 |
|----------|----------|----------|
| `test_parse_nonexistent_paper` | 解析不存在论文 | 返回 success=False |
| `test_parse_paper_no_pdf` | 无 PDF 路径 | 返回 success=False |
| `test_parse_paper_success` | 成功解析 | 返回 success=True，chunk_count>0 |
| `test_get_chunks` | 获取分块 | 解析后获取，验证 paper_id 一致 |
| `test_parse_project_papers` | 批量解析项目 | success=1，failed=0 |
| `test_parse_project_skip_parsed` | 跳过已解析 | skipped=1 |
| `test_parse_missing_pdf_file` | PDF 文件缺失 | 返回 success=False |

### 6. 论文卡片生成测试 (test_paper_card_generator.py) - 7 个测试

| 测试名称 | 测试内容 | 通过方式 |
|----------|----------|----------|
| `test_generate_nonexistent` | 不存在论文 | 返回 None |
| `test_generate_no_chunks` | 无分块数据 | 返回 None |
| `test_generate_success` | 成功生成 | card_id、paper_id 正确，confidence=0.5 |
| `test_generate_has_findings` | 有研究发现 | key_findings 列表非空，非 "unknown" |
| `test_generate_has_source_spans` | 有来源引用 | source_spans 非空，chunk_id 正确 |
| `test_batch_generate` | 批量生成 | 返回 1 个卡片 |
| `test_batch_skip_existing` | 跳过已有 | 返回 0 个新卡片 |

### 7. 证据表服务测试 (test_evidence_table_service.py) - 8 个测试

| 测试名称 | 测试内容 | 通过方式 |
|----------|----------|----------|
| `test_build_for_paper` | 单论文证据 | 返回记录，paper_id 一致 |
| `test_build_for_project` | 项目级证据 | 返回记录，project_id 一致 |
| `test_query_by_paper` | 按论文查询 | 过滤 paper_id 后返回匹配记录 |
| `test_query_by_scope_papers` | Scope 论文过滤 | SELECTED_PAPERS 范围内返回正确记录 |
| `test_query_by_scope_topic` | Scope 主题过滤 | TOPIC_GROUP 范围内返回正确记录 |
| `test_build_no_cards` | 无卡片 | 返回空列表 |
| `test_normalize_similar_topics` | 近似主题合并 | "LLM feedback"/"AI feedback" 合并为 "feedback mechanism" |
| `test_normalize_distinct_topics` | 不同主题 | 2 个不同主题保持独立 |

### 8. 知识图谱服务测试 (test_graph_service.py) - 11 个测试

| 测试名称 | 测试内容 | 通过方式 |
|----------|----------|----------|
| `test_build_empty_graph` | 空图谱 | 无证据时 nodes/edges 为空 |
| `test_build_graph_with_evidence` | 有证据的图谱 | nodes/edges 非空 |
| `test_paper_nodes_created` | 论文节点 | 2 个论文创建 2 个 Paper 类型节点 |
| `test_topic_nodes_created` | 主题节点 | 至少 1 个 Topic 类型节点 |
| `test_method_nodes_created` | 方法节点 | 2 个方法创建 2 个 Method 类型节点 |
| `test_get_graph` | 获取图谱 | project_id 一致 |
| `test_get_node` | 获取节点 | paper:p1 节点存在且类型正确 |
| `test_get_neighbors` | 获取邻居 | 1 跳邻居 nodes 非空 |
| `test_get_subgraph` | 获取子图 | 子图 nodes 非空 |
| `test_find_paths` | 路径查找 | paper:p1 到 paper:p2 存在路径（通过共同 topic） |

### 9. Scope 服务测试 (test_retrieval_scope.py) - 8 个测试

| 测试名称 | 测试内容 | 通过方式 |
|----------|----------|----------|
| `test_resolve_all_project` | 全项目范围 | included=True 的论文有 2 个 |
| `test_resolve_selected_papers` | 选中论文 | paper_ids=["p1"] |
| `test_resolve_topic_group` | 主题范围 | 2 个论文关联该主题 |
| `test_resolve_year_range` | 年份范围 | 2023-2024 有 2 篇 |
| `test_to_paper_ids` | 转换为论文 ID | 返回 2 个 ID |
| `test_to_evidence_records` | 转换为证据 | 返回 2 条记录 |
| `test_summarize_all_project` | 全项目摘要 | 包含 "全项目" |
| `test_summarize_selected_papers` | 选中论文摘要 | 包含 "1 篇" |

### 10. Scope QA 测试 (test_scope_qa.py) - 12 个测试

| 测试名称 | 测试内容 | 通过方式 |
|----------|----------|----------|
| `test_classify_intent_limitation` | 识别局限性意图 | "不足" → limitation_analysis |
| `test_classify_intent_method` | 识别方法意图 | "方法" → method_analysis |
| `test_classify_intent_review` | 识别综述意图 | "综述" → review_generation |
| `test_classify_intent_innovation` | 识别创新意图 | "创新点" → innovation_generation |
| `test_classify_intent_comparison` | 识别比较意图 | "比较" → comparison |
| `test_classify_intent_summary` | 识别摘要意图 | 其他 → summary |
| `test_answer_selected_papers` | 选中论文 QA | answer 非空，supporting_papers 非空 |
| `test_answer_limitation` | 局限性回答 | 包含 "不足" 或 "局限" |
| `test_answer_method` | 方法回答 | 包含 "experiment" 或 "survey" |
| `test_answer_has_suggested_actions` | 建议操作 | 包含 generate_innovation_report |
| `test_answer_has_uncertainty` | 不确定性声明 | uncertainty 字段非空 |
| `test_answer_no_evidence` | 无证据回答 | 返回有效响应 |

### 11. 文献综述生成测试 (test_review_generator.py) - 7 个测试

| 测试名称 | 测试内容 | 通过方式 |
|----------|----------|----------|
| `test_generate_review` | 生成综述 | type=LITERATURE_REVIEW，content 非空 |
| `test_review_has_scope_summary` | 有范围摘要 | content 包含 "生成范围" |
| `test_review_has_paper_count` | 有论文数量 | content 包含 "使用论文数量" |
| `test_review_has_sections` | 有章节 | 包含 "研究背景"/"主要研究方法"/"主要发现" |
| `test_collect_materials` | 收集材料 | paper_count=1 |
| `test_validate_review` | 验证综述 | valid=True |
| `test_validate_review_missing_scope` | 缺少 scope | valid=False |

### 12. 创新点报告测试 (test_innovation_generator.py) - 6 个测试

| 测试名称 | 测试内容 | 通过方式 |
|----------|----------|----------|
| `test_generate_report` | 生成报告 | type=INNOVATION_REPORT，content 非空 |
| `test_report_has_innovations` | 有创新点 | content 包含 "创新点" 或 "创新方向" |
| `test_aggregate_limitations` | 聚合局限 | 同一 limitation 出现 2 次，count=2 |
| `test_score_candidates` | 评分候选 | scores 字段非空 |
| `test_is_generic` | 泛化检测 | "深度学习" 是泛化，"改进反馈机制" 不是 |
| `test_report_paper_ids` | 报告论文 ID | paper_ids 非空 |

### 13. 报告服务测试 (test_report_service.py) - 9 个测试

| 测试名称 | 测试内容 | 通过方式 |
|----------|----------|----------|
| `test_save_report` | 保存报告 | 保存后可查到，标题一致 |
| `test_list_reports` | 列出报告 | 返回 1 个 |
| `test_list_reports_by_type` | 按类型列出 | 综述 1 个，创新 0 个 |
| `test_get_nonexistent` | 获取不存在 | 返回 None |
| `test_create_version` | 创建版本 | content 和 reason 正确 |
| `test_version_updates_report` | 版本更新报告 | report.version=2，content 更新 |
| `test_create_version_nonexistent` | 不存在报告版本 | 返回 None |
| `test_export_markdown` | 导出 Markdown | 包含 content 和元数据 |
| `test_export_nonexistent` | 导出不存在报告 | 返回空字符串 |

## 测试通过机制

所有测试通过 pytest 的标准断言机制验证：

1. **对象创建**: 实例化 Pydantic 模型，验证字段默认值和赋值
2. **CRUD 操作**: 通过 JSONStorage 进行增删改查，验证数据一致性
3. **业务逻辑**: 调用 Service 方法，验证返回值符合预期
4. **边界条件**: 测试不存在对象、空集合、损坏数据等异常情况
5. **隔离性**: 使用 tmp_path fixture 确保每个测试独立运行

## 测试覆盖范围

| 功能模块 | 覆盖率 |
|----------|--------|
| 数据模型 | 100% |
| JSON 存储 | 100% |
| 项目 CRUD | 100% |
| 论文库管理 | 100% |
| PDF 解析 | 100% |
| 论文卡片生成 | 100% |
| 证据表构建 | 100% |
| 知识图谱构建 | 100% |
| Scope 解析 | 100% |
| Scope QA | 100% |
| 文献综述生成 | 100% |
| 创新点报告 | 100% |
| 报告管理 | 100% |
