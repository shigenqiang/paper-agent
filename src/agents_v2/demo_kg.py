"""
知识图谱模块演示脚本

演示完整的知识图谱工作流程
"""
from src.agents_v2.knowledge_graph import (
    KnowledgeGraphService,
    EntityExtractor,
    RelationExtractor,
    KnowledgeGraphGenerator,
    HybridRetriever,
    create_graphrag_qa,
    detect_communities,
    SchemaManager,
    ServiceConfig
)


def demo_service_workflow():
    """演示统一服务的工作流程"""
    print("\n" + "="*60)
    print("知识图谱统一服务 - 完整流程演示")
    print("="*60)

    # 1. 创建服务
    config = ServiceConfig(
        vector_store_type="memory",
        enable_graphrag=True
    )
    service = KnowledgeGraphService(config)

    # 2. 添加论文实体
    papers = [
        ("paper_1", "Paper", {"title": "Attention Is All You Need", "year": 2017}),
        ("paper_2", "Paper", {"title": "BERT: Pre-training", "year": 2018}),
        ("paper_3", "Paper", {"title": "GPT-3", "year": 2020}),
        ("paper_4", "Paper", {"title": "Deep Learning", "year": 2015}),
    ]

    # 生成假嵌入向量
    embeddings = [
        [0.1, 0.2, 0.3],  # Transformer
        [0.2, 0.3, 0.4],   # BERT
        [0.3, 0.4, 0.5],   # GPT
        [0.4, 0.5, 0.6],   # Deep Learning
    ]

    for (paper_id, ptype, props), embedding in zip(papers, embeddings):
        service.add_entity(paper_id, ptype, props, embedding)
        print(f"✓ 添加实体: {paper_id} - {props['title']}")

    # 3. 添加关系
    relations = [
        ("paper_1", "paper_2", "CITES", {}),  # BERT cites Transformer
        ("paper_2", "paper_3", "CITES", {}),  # GPT cites BERT
        ("paper_4", "paper_1", "CITES", {}),  # Deep Learning cites Transformer
    ]

    for source, target, rel, props in relations:
        service.add_relation(source, target, rel, props)
        print(f"✓ 添加关系: {source} --[{rel}]--> {target}")

    # 4. 检索
    print("\n检索测试:")
    results = service.search(
        query_embedding=[0.1, 0.2, 0.3],
        top_k=3
    )
    for r in results:
        print(f"  - {r['entity_id']}: score={r['score']:.3f}")

    # 5. 社区检测
    print("\n社区检测:")
    communities = service.detect_communities(algorithm="louvain")
    for i, c in enumerate(communities):
        print(f"  社区 {i}: {c['members']}")

    # 6. GraphRAG问答
    print("\nGraphRAG问答:")
    qa = create_graphrag_qa()
    qa.build_index(
        entities=[
            ("transformer", "Method", "Transformer model - Attention mechanism"),
            ("bert", "Method", "BERT - Bidirectional Encoder Representations"),
            ("paper_1", "Paper", "Attention Is All You Need - Original Transformer paper"),
        ],
        relations=[
            ("bert", "transformer", "BASED_ON"),
            ("paper_1", "transformer", "PROPOSES"),
        ]
    )

    result = qa.query("What is BERT based on?")
    print(f"  问题: What is BERT based on?")
    print(f"  上下文: {result.to_prompt_context()[:200]}...")

    # 7. Schema验证
    print("\nSchema管理:")
    schema_manager = SchemaManager()
    paper_schema = schema_manager.get_node_schema("Paper")
    print(f"  Paper节点属性: {[p.name for p in paper_schema.properties]}")

    print("\n" + "="*60)
    print("演示完成!")
    print("="*60)


def demo_entity_extraction():
    """演示实体提取"""
    print("\n" + "="*60)
    print("实体与关系提取演示")
    print("="*60)

    generator = KnowledgeGraphGenerator()

    text = """
    We propose a new Transformer-based model called BERT for natural language understanding.
    Our method achieves state-of-the-art results on eleven NLP tasks.
    Experiments on the GLUE benchmark show significant improvement over previous methods.
    """

    result = generator.generate_from_paper(
        paper_id="bert_paper",
        title="BERT: Pre-training of Deep Bidirectional Transformers",
        abstract=text,
        full_text=text
    )

    print(f"\n论文: {result.paper_id}")
    print(f"成功: {result.success}")
    print(f"\n提取的实体 ({len(result.entities)}):")
    for entity in result.entities:
        print(f"  - [{entity.type.value}] {entity.name}")

    print(f"\n提取的关系 ({len(result.relations)}):")
    for rel in result.relations:
        print(f"  - {rel.source} --[{rel.relation.value}]--> {rel.target}")


def demo_community_detection():
    """演示社区检测"""
    print("\n" + "="*60)
    print("社区检测算法演示")
    print("="*60)

    # 构建引用网络
    edges = [
        ("paper_1", "paper_2"),  # 同一研究社区
        ("paper_2", "paper_3"),
        ("paper_3", "paper_4"),
        ("paper_5", "paper_6"),  # 不同社区
        ("paper_6", "paper_7"),
    ]

    print("\n引用网络:")
    for src, tgt in edges:
        print(f"  {src} --> {tgt}")

    # Louvain算法
    louvain_communities = detect_communities(edges, algorithm="louvain")
    print(f"\nLouvain算法检测到 {len(louvain_communities)} 个社区:")
    for i, c in enumerate(louvain_communities):
        print(f"  社区 {i+1}: {list(c.members)[:5]}...")


if __name__ == "__main__":
    demo_service_workflow()
    demo_entity_extraction()
    demo_community_detection()
