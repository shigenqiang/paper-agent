"""
知识图谱嵌入模块测试
"""
import pytest
import math
from src.agents_v2.knowledge_graph import kg_embeddings


class TestEmbeddingResult:
    """EmbeddingResult类测试"""

    def test_creation(self):
        """测试创建"""
        result = kg_embeddings.EmbeddingResult(
            entity_id="paper_1",
            embedding=[0.1, 0.2, 0.3],
            entity_type="Paper"
        )
        assert result.entity_id == "paper_1"
        assert result.embedding == [0.1, 0.2, 0.3]
        assert result.entity_type == "Paper"

    def test_default_type(self):
        """测试默认类型"""
        result = kg_embeddings.EmbeddingResult(
            entity_id="e1",
            embedding=[0.1, 0.2]
        )
        assert result.entity_type == "Unknown"


class TestTransEInit:
    """TransE初始化测试"""

    def test_creation(self):
        """测试创建"""
        model = kg_embeddings.TransE(
            num_entities=100,
            num_relations=50,
            embedding_dim=100
        )
        assert model.num_entities == 100
        assert model.num_relations == 50
        assert model.embedding_dim == 100
        assert model.margin == 1.0
        assert model.learning_rate == 0.01
        assert model.batch_size == 128
        assert model.epochs == 100

    def test_default_values(self):
        """测试默认值"""
        model = kg_embeddings.TransE(num_entities=100, num_relations=50)
        assert model.embedding_dim == 100
        assert model.margin == 1.0
        assert model.learning_rate == 0.01
        assert model.batch_size == 128
        assert model.epochs == 100

    def test_not_initialized(self):
        """测试未初始化状态"""
        model = kg_embeddings.TransE(num_entities=100, num_relations=50)
        assert model._initialized is False
        assert model.get_entity_embedding("e1") is None


class TestTransEInitialize:
    """TransE初始化嵌入测试"""

    def test_initialize(self):
        """测试初始化"""
        model = kg_embeddings.TransE(num_entities=3, num_relations=2, embedding_dim=10)
        entity_ids = ["e1", "e2", "e3"]
        relation_ids = ["r1", "r2"]

        model.initialize(entity_ids, relation_ids)

        assert model._initialized is True
        assert "e1" in model.entity_embeddings
        assert "e2" in model.entity_embeddings
        assert "e3" in model.entity_embeddings
        assert "r1" in model.relation_embeddings
        assert "r2" in model.relation_embeddings

        # 检查维度
        assert len(model.entity_embeddings["e1"]) == 10
        assert len(model.relation_embeddings["r1"]) == 10

    def test_initialize_range(self):
        """测试初始化向量在合理范围内"""
        model = kg_embeddings.TransE(num_entities=2, num_relations=1, embedding_dim=5)
        model.initialize(["e1", "e2"], ["r1"])

        # 检查向量不为零
        for emb in model.entity_embeddings.values():
            norm = math.sqrt(sum(x * x for x in emb))
            assert norm > 0


class TestTransEDistance:
    """TransE距离计算测试"""

    def test_distance_same(self):
        """测试相同向量距离为0"""
        model = kg_embeddings.TransE(num_entities=1, num_relations=1, embedding_dim=3)
        model.initialize(["e1"], ["r1"])

        h = [1.0, 0.0, 0.0]
        r = [0.0, 0.0, 0.0]
        t = [1.0, 0.0, 0.0]

        dist = model._distance(h, r, t)
        assert dist == pytest.approx(0.0)

    def test_distance_translation(self):
        """测试翻译距离"""
        model = kg_embeddings.TransE(num_entities=1, num_relations=1, embedding_dim=3)

        h = [1.0, 0.0, 0.0]
        r = [0.0, 1.0, 0.0]  # 翻译
        t = [1.0, 1.0, 0.0]  # h + r

        dist = model._distance(h, r, t)
        assert dist == pytest.approx(0.0)

    def test_distance_l1(self):
        """测试L1距离"""
        model = kg_embeddings.TransE(num_entities=1, num_relations=1, embedding_dim=3)

        h = [1.0, 0.0, 0.0]
        r = [0.0, 0.0, 0.0]
        t = [0.0, 1.0, 0.0]

        dist = model._distance(h, r, t)
        assert dist == pytest.approx(2.0)  # |1-0| + |0-1| + |0-0| = 2


class TestTransEMarginLoss:
    """TransE边缘损失测试"""

    def test_margin_loss_positive(self):
        """测试正损失"""
        model = kg_embeddings.TransE(num_entities=1, num_relations=1, margin=1.0)
        loss = model._margin_loss(3.0, 1.0)
        assert loss == 0.0  # margin - (3.0 - 1.0) = 1 - 2 < 0

    def test_margin_loss_violated(self):
        """测试违反边界"""
        model = kg_embeddings.TransE(num_entities=1, num_relations=1, margin=1.0)
        loss = model._margin_loss(1.0, 3.0)
        # max(0, margin - (pos - neg)) = max(0, 1 - (1-3)) = max(0, 1 + 2) = 3
        assert loss == pytest.approx(3.0)


class TestTransETrain:
    """TransE训练测试"""

    def test_train_empty(self):
        """测试空训练"""
        model = kg_embeddings.TransE(num_entities=0, num_relations=0)
        history = model.train([])
        assert history == {}

    def test_train_single_triplet(self):
        """测试单三元组训练"""
        model = kg_embeddings.TransE(
            num_entities=2,
            num_relations=1,
            embedding_dim=10,
            epochs=5
        )
        triplets = [("e1", "r1", "e2")]
        history = model.train(triplets)

        assert len(history) == 5
        assert 0 in history
        assert model._initialized is True

    def test_train_multiple_triplets(self):
        """测试多三元组训练"""
        model = kg_embeddings.TransE(
            num_entities=3,
            num_relations=2,
            embedding_dim=10,
            epochs=10
        )
        triplets = [
            ("e1", "r1", "e2"),
            ("e2", "r1", "e3"),
            ("e1", "r2", "e3")
        ]
        history = model.train(triplets)

        assert len(history) == 10
        assert model.get_entity_embedding("e1") is not None
        assert model.get_entity_embedding("e2") is not None
        assert model.get_relation_embedding("r1") is not None


class TestTransEPredict:
    """TransE预测测试"""

    def test_predict_tail(self):
        """测试预测尾实体"""
        model = kg_embeddings.TransE(
            num_entities=3,
            num_relations=1,
            embedding_dim=10,
            epochs=10
        )
        triplets = [("e1", "r1", "e2"), ("e1", "r1", "e3")]
        model.train(triplets)

        predictions = model.predict_tail("e1", "r1", top_k=2)

        assert len(predictions) <= 2
        assert all(isinstance(p[0], str) and isinstance(p[1], float) for p in predictions)

    def test_predict_head(self):
        """测试预测头实体"""
        model = kg_embeddings.TransE(
            num_entities=3,
            num_relations=1,
            embedding_dim=10,
            epochs=10
        )
        triplets = [("e1", "r1", "e2"), ("e2", "r1", "e3")]
        model.train(triplets)

        predictions = model.predict_head("e3", "r1", top_k=2)

        assert len(predictions) <= 2
        # 只验证返回格式正确
        if predictions:
            assert all(isinstance(p[0], str) and isinstance(p[1], float) for p in predictions)

    def test_predict_not_initialized(self):
        """测试未初始化预测"""
        model = kg_embeddings.TransE(num_entities=10, num_relations=5)
        assert model.predict_tail("e1", "r1") == []
        assert model.predict_head("e1", "r1") == []


class TestComplExInit:
    """ComplEx初始化测试"""

    def test_creation(self):
        """测试创建"""
        model = kg_embeddings.ComplEx(
            num_entities=100,
            num_relations=50,
            embedding_dim=100
        )
        assert model.num_entities == 100
        assert model.num_relations == 50
        assert model.embedding_dim == 100
        assert model.learning_rate == 0.01

    def test_default_values(self):
        """测试默认值"""
        model = kg_embeddings.ComplEx(num_entities=100, num_relations=50)
        assert model.embedding_dim == 100
        assert model.learning_rate == 0.01
        assert model.batch_size == 128
        assert model.epochs == 100


class TestComplExScore:
    """ComplEx得分计算测试"""

    def test_score_symmetric(self):
        """测试对称关系得分"""
        model = kg_embeddings.ComplEx(num_entities=2, num_relations=1, embedding_dim=5)
        model.initialize(["e1", "e2"], ["r1"])

        # 设置相同向量 (对称关系)
        model.entity_embeddings_real["e1"] = [1.0, 0.0, 0.0, 0.0, 0.0]
        model.entity_embeddings_imag["e1"] = [0.0, 0.0, 0.0, 0.0, 0.0]
        model.entity_embeddings_real["e2"] = [1.0, 0.0, 0.0, 0.0, 0.0]
        model.entity_embeddings_imag["e2"] = [0.0, 0.0, 0.0, 0.0, 0.0]
        model.relation_embeddings_real["r1"] = [1.0, 0.0, 0.0, 0.0, 0.0]
        model.relation_embeddings_imag["r1"] = [0.0, 0.0, 0.0, 0.0, 0.0]

        score = model._score(
            model.entity_embeddings_real["e1"],
            model.entity_embeddings_imag["e1"],
            model.relation_embeddings_real["r1"],
            model.relation_embeddings_imag["r1"],
            model.entity_embeddings_real["e2"],
            model.entity_embeddings_imag["e2"]
        )

        # e1 * r1 * conj(e2) = 1 * 1 * 1 = 1
        assert score == pytest.approx(1.0)


class TestComplExTrain:
    """ComplEx训练测试"""

    def test_train_empty(self):
        """测试空训练"""
        model = kg_embeddings.ComplEx(num_entities=0, num_relations=0)
        history = model.train([])
        assert history == {}

    def test_train_single_triplet(self):
        """测试单三元组训练"""
        model = kg_embeddings.ComplEx(
            num_entities=2,
            num_relations=1,
            embedding_dim=10,
            epochs=5
        )
        triplets = [("e1", "r1", "e2")]
        history = model.train(triplets)

        assert len(history) == 5
        assert model._initialized is True

    def test_train_updates_embeddings(self):
        """测试训练更新嵌入"""
        model = kg_embeddings.ComplEx(
            num_entities=2,
            num_relations=1,
            embedding_dim=10,
            epochs=5
        )
        triplets = [("e1", "r1", "e2")]
        model.train(triplets)

        # 检查嵌入存在
        assert model.get_entity_embedding("e1") is not None
        assert len(model.get_entity_embedding("e1")) == 20  # 10*2 for real+imag


class TestComplExPredict:
    """ComplEx预测测试"""

    def test_predict_tail(self):
        """测试预测尾实体"""
        model = kg_embeddings.ComplEx(
            num_entities=3,
            num_relations=1,
            embedding_dim=10,
            epochs=10
        )
        triplets = [("e1", "r1", "e2"), ("e1", "r1", "e3")]
        model.train(triplets)

        predictions = model.predict_tail("e1", "r1", top_k=2)
        assert len(predictions) <= 2


class TestEmbeddingTrainer:
    """EmbeddingTrainer测试"""

    def test_create_transe(self):
        """测试创建TransE训练器"""
        trainer = kg_embeddings.EmbeddingTrainer(algorithm="TransE")
        assert trainer.algorithm == "TransE"
        assert trainer.model is None

    def test_create_complex(self):
        """测试创建ComplEx训练器"""
        trainer = kg_embeddings.EmbeddingTrainer(algorithm="ComplEx")
        assert trainer.algorithm == "ComplEx"

    def test_train_transe(self):
        """测试训练TransE"""
        trainer = kg_embeddings.EmbeddingTrainer(algorithm="TransE")
        triplets = [("e1", "r1", "e2"), ("e2", "r1", "e3")]

        result = trainer.train(triplets, epochs=5)

        assert result["model"] is not None
        assert len(result["history"]) == 5
        assert trainer.get_entity_embedding("e1") is not None

    def test_train_complex(self):
        """测试训练ComplEx"""
        trainer = kg_embeddings.EmbeddingTrainer(algorithm="ComplEx")
        triplets = [("e1", "r1", "e2"), ("e2", "r1", "e3")]

        result = trainer.train(triplets, epochs=5)

        assert result["model"] is not None
        assert trainer.get_entity_embedding("e1") is not None

    def test_train_empty(self):
        """测试空训练"""
        trainer = kg_embeddings.EmbeddingTrainer(algorithm="TransE")
        result = trainer.train([])
        assert result["model"] is None

    def test_unknown_algorithm(self):
        """测试未知算法"""
        trainer = kg_embeddings.EmbeddingTrainer(algorithm="Unknown")
        with pytest.raises(ValueError, match="Unknown algorithm"):
            trainer.train([("e1", "r1", "e2")])


class TestTransEEmbeddingDimension:
    """TransE嵌入维度测试"""

    def test_different_dimensions(self):
        """测试不同维度"""
        for dim in [50, 100, 200, 500]:
            model = kg_embeddings.TransE(
                num_entities=5,
                num_relations=2,
                embedding_dim=dim
            )
            model.initialize(["e1", "e2", "e3", "e4", "e5"], ["r1", "r2"])

            emb = model.get_entity_embedding("e1")
            assert len(emb) == dim

            rel_emb = model.get_relation_embedding("r1")
            assert len(rel_emb) == dim


class TestComplexEmbeddingDimension:
    """ComplEx嵌入维度测试"""

    def test_embedding_size(self):
        """测试嵌入大小是输入维度的2倍"""
        dim = 100
        model = kg_embeddings.ComplEx(
            num_entities=5,
            num_relations=2,
            embedding_dim=dim
        )
        model.initialize(["e1", "e2", "e3", "e4", "e5"], ["r1", "r2"])

        # ComplEx返回实部+虚部
        emb = model.get_entity_embedding("e1")
        assert len(emb) == dim * 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
