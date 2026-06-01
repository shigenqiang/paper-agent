# 重排（Reranker）模型调研报告

> 调研时间：2026-05-31
> 调研范围：Cross-Encoder、LLM-based、轻量级重排模型；RAG集成方案；本地部署与性能

---

## 1. 重排模型推荐排名

| 排名 | 模型 | 类型 | 参数量 | 最大输入 | MTEB Re-Ranking | 推理速度 | 许可证 | 多语言 |
|-----|------|------|--------|----------|----------------|---------|--------|--------|
| 1 | **BGE-reranker-v2-m3** | Cross-Encoder | 568M | 8192 | ~68.5 | ~35ms | MIT | 100+ |
| 2 | **Jina Reranker v2** | Cross-Encoder | 560M | 8192 | ~67-68 | ~30-50ms | Apache 2.0 | 89+ |
| 3 | **BGE-reranker-v2-gemma** | Cross-Encoder | 2.5B | 4096 | ~69.8 | ~80ms | MIT | 部分 |
| 4 | **Cohere Rerank v3** | Cross-Encoder | 未公开 | 4096 | ~68-70 | ~150ms(API) | 闭源API | 100+ |
| 5 | **nv-rerankqa-mistral-4b** | Cross-Encoder | 4B | 32768 | ~65+ | ~300ms | NVIDIA | 部分 |
| 6 | **gte-multilingual-reranker** | Cross-Encoder | 278M | 8192 | ~65-67 | ~30ms | Apache 2.0 | 70+ |
| 7 | **BGE-reranker-large** | Cross-Encoder | 560M | 512 | ~67.3 | ~30ms | MIT | 中英 |
| 8 | **MiniLM-L-12-v2** | Cross-Encoder | 33M | 512 | — | ~8ms | Apache 2.0 | 英文 |
| 9 | **FlashRank Small** | CE(ONNX) | ~30M | 512 | — | ~5ms | Apache 2.0 | 英文 |

### LLM-based 重排（仅研究，不用于生产）

| 模型 | TREC DL NDCG@10 | 速度 | 用途 |
|------|----------------|------|------|
| RankGPT (GPT-4) | ~70.2 | ~15s/top-100 | 教师模型蒸馏 |
| RankZephyr | ~69.5 | ~8s/top-100 | 开源替代 |
| LLaMA-reranker | ~68.8 | ~10s/top-100 | 开源替代 |

---

## 2. 原理说明

### Cross-Encoder（主流）

```
输入: [CLS] query [SEP] document [SEP]
      → Transformer编码 → [CLS]表示 → 线性层 → 相关性分数
```

- 精度最高，但每个query-doc对都要独立编码
- 计算复杂度 O(n)，n为候选文档数
- 不同于Bi-Encoder（可预计算文档向量），Cross-Encoder无法离线预计算

### Listwise（LLM重排）

```
输入: prompt包含query + 候选文档列表
      → LLM生成排序结果
```

- 精度最高（GPT-4超越所有监督模型），但成本/延迟不可接受
- 主要用于蒸馏训练数据

### RRF融合（非神经网络）

```
RRF_score(d) = Σ 1 / (k + rank_i(d))，k=60
```

- 多检索器排名融合，极快（<1ms）
- 精度低于神经网络重排，但无额外开销

---

## 3. RAG集成架构

### 推荐：三阶段检索

```
查询
  ├─ Dense召回 (BGE-M3) → top-100
  └─ BM25召回           → top-100
       ↓
  RRF融合 → top-100
       ↓
  Cross-Encoder重排 (BGE-reranker-v2-m3) → top-10~20
       ↓
  送入LLM生成
```

### 效果提升量化

| 方案 | NDCG@10 | 相对BM25基线提升 |
|------|---------|----------------|
| BM25基线 | 基准 | — |
| Dense检索 | +2-3 | +2-3pp |
| Dense + Reranker | +4-5 | +4-5pp |
| BM25 + Reranker | +3-7 | +3-7pp |
| **Dense + BM25 + RRF + Reranker** | **+10-14** | **+10-14pp** |

Reranker是提升最大的单一组件（+5pp）。

---

## 4. 学术论文重排策略

### 输入格式

```
query: "sparse functional data deep learning"
document: title + " " + abstract  # 推荐拼接方式
```

### 元数据增强信号

| 信号 | 权重 | 计算方式 |
|------|------|---------|
| Reranker分数 | alpha=0.8 | Cross-Encoder输出 |
| 引用数 | beta=0.1 | log(1+citations) 归一化 |
| 时效性 | gamma=0.1 | e^(-0.05×age) |

```
final_score = 0.8×reranker + 0.1×citation_norm + 0.1×recency
```

---

## 5. 部署方案对比

### 开发环境

| 方案 | 部署方式 | 延迟 | 依赖 |
|------|---------|------|------|
| FlashRank | `pip install flashrank` | 5-10ms | 仅ONNX Runtime |
| Sentence-Transformers | `CrossEncoder('model')` | 20-50ms | PyTorch |

### 生产环境

| 方案 | 部署方式 | 延迟 | 适合规模 |
|------|---------|------|---------|
| TEI (Hugging Face) | Docker | ~35ms/100docs | 中大规模 |
| vLLM | Docker | ~50ms/100docs | 大模型(2B+) |
| Cohere API | HTTP调用 | ~150ms | 小规模/零运维 |

### TEI 部署示例

```bash
model=BAAI/bge-reranker-v2-m3
docker run --gpus all -p 8080:80 \
  -v $PWD/data:/data \
  ghcr.io/huggingface/text-embeddings-inference:latest \
  --model-id $model
```

---

## 6. 成本分析

### API成本

| 服务 | 定价 | 月10万次成本 | 月100万次成本 |
|------|------|------------|-------------|
| Cohere Rerank v3 | $1/1000次 | $100 | $1,000 |
| Jina Reranker | $0.02/1000 token | ~$50 | ~$500 |

### 自建成本

| 方案 | 月固定成本 | 月10万次成本 | 月100万次成本 |
|------|-----------|------------|-------------|
| FlashRank (CPU) | ~$0 | ~$0 | ~$0 |
| TEI + T4 GPU | ~$300 | $300 | $300 |
| TEI + A10 GPU | ~$600 | $600 | $600 |

### 盈亏平衡

| 场景 | 结论 |
|------|------|
| 月搜索 < 10万次 | API更划算 |
| 月搜索 10-40万次 | 自建CPU方案（FlashRank）更划算 |
| 月搜索 > 40万次 | 自建GPU方案（TEI+T4）更划算 |

---

## 7. 向量数据库内置重排

| 数据库 | 支持情况 |
|--------|---------|
| Milvus | 内置Reranker API，支持Cross-Encoder |
| Qdrant | 通过FastEmbed集成 |
| Weaviate | 内置rerank-v2模型 |
| LlamaIndex | SentenceTransformerRerank / CohereRerank |
| LangChain | CrossEncoderReranker / CohereRerank |

---

## 8. 对本项目的推荐

### 推荐模型：BGE-reranker-v2-m3

**理由：**
1. 8192 token输入 — 覆盖大部分论文摘要和关键段落
2. 100+语言 — 支持中英文混合论文
3. MIT协议 — 商用无风险
4. 568M参数 — 单卡T4/RTX 4090即可运行
5. MTEB顶级分数 — 仅次于v2-gemma

### 推荐架构

```
查询 → Dense(BGE-M3) + BM25 → RRF融合 → BGE-reranker-v2-m3 → top-10 → LLM
```

### 分阶段实施

| 阶段 | 方案 | 说明 |
|------|------|------|
| 开发期 | FlashRank + MiniLM-L-12 | CPU即可，零成本验证 |
| MVP | Sentence-Transformers + bge-reranker-v2-m3 | Python直接调用 |
| 生产 | TEI Docker + T4 GPU | 高性能，动态批处理 |

---

详细子报告：
- `05-学术搜索与解析/reranker-integration-research.md` — RAG集成方案
- `16-重排模型部署/重排模型本地部署方案与性能对比调研报告.md` — 部署与性能
