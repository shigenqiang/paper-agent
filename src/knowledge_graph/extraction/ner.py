"""
学术领域命名实体识别
Academic Named Entity Recognition
"""

import re
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, field

from ..schema.academic_kg_schema import Entity, EntityType, ParsedDocument


@dataclass
class RecognizedEntity:
    """识别出的实体"""
    text: str
    type: EntityType
    start_pos: int
    end_pos: int
    confidence: float = 1.0
    properties: Dict[str, Any] = field(default_factory=dict)


class AcademicNER:
    """学术领域命名实体识别"""

    def __init__(
        self,
        use_transformers: bool = False,
        model_name: str = "dmis-lab/biobert-base-cased-v1.2"
    ):
        self.use_transformers = use_transformers
        self.model_name = model_name
        self.model = None

        # 初始化规则基础NER
        self._init_rule_based_ner()

        # 初始化transformers模型（如果可用）
        if use_transformers:
            self._init_transformers_model()

    def _init_rule_based_ner(self):
        """初始化基于规则的NER"""
        # 实体模式定义
        self.entity_patterns = {
            EntityType.PAPER: [
                # 论文标题模式（被引号或特殊格式包围）
                r'"([^"]+)"',
                r'《([^》]+)》',
                r'"([^"]+)"',
            ],
            EntityType.AUTHOR: [
                # 英文名字模式：首字母大写的姓
                r'\b([A-Z][a-z]+ [A-Z][a-z]+)\b',
                # 中文名字模式
                r'\b([A-Z][a-z]{1,2}·?[A-Z][a-z]{1,2})\b',
            ],
            EntityType.INSTITUTION: [
                # 大学模式
                r'\b(University of [A-Z][A-Za-z\s]+)\b',
                r'\b([A-Z][A-Za-z]+ University)\b',
                r'\b(Institute of [A-Z][A-Za-z\s]+)\b',
                r'\b([A-Z][A-Za-z]+ Institute)\b',
                # 中文机构
                r'(大学|学院|研究所|研究院|实验室)',
            ],
            EntityType.VENUE: [
                # 期刊/会议模式
                r'\b([A-Z][A-Za-z]+ Conference)\b',
                r'\b([A-Z][A-Za-z]+ Journal)\b',
                r'\b(IEEE [A-Z][A-Za-z]+)\b',
                r'\b(ACM [A-Z][A-Za-z]+)\b',
                r'\b(NeurIPS|ICML|ICLR|AAAI|IJCAI|CVPR|ECCV)\b',
            ],
            EntityType.KEYWORD: [
                # 关键词模式（括号内或特定格式）
                r'keywords?:\s*([^.\n]+)',
            ],
            EntityType.METHOD: [
                # 常见模型名称
                r'\b(Transformer|BERT|GPT|GAN|ResNet|VGG|LSTM|CNN)\b',
                r'\b([A-Z][a-z]+Net)\b',  # AlexNet, etc.
            ],
            EntityType.DATASET: [
                # 常见数据集
                r'\b(ImageNet|GLUE|MNIST|COCO|SQuAD|WikiBio)\b',
            ]
        }

        # 机构关键词
        self.institution_keywords = [
            "University", "Institute", "Laboratory", "Lab", "College",
            "School", "Research", "Academy", "Center", "Centre",
            "大学", "学院", "研究所", "研究院", "实验室", "研究中心"
        ]

        # 期刊/会议缩写
        self.venue_abbrevs = {
            "NeurIPS": "Advances in Neural Information Processing Systems",
            "ICML": "International Conference on Machine Learning",
            "ICLR": "International Conference on Learning Representations",
            "AAAI": "Association for the Advancement of Artificial Intelligence",
            "IJCAI": "International Joint Conference on Artificial Intelligence",
            "CVPR": "Computer Vision and Pattern Recognition",
            "ECCV": "European Conference on Computer Vision",
            "ICCV": "International Conference on Computer Vision",
            "ACL": "Association for Computational Linguistics",
            "EMNLP": "Empirical Methods in Natural Language Processing",
            "NAACL": "North American Chapter of the ACL",
            "COLING": "International Conference on Computational Linguistics",
        }

    def _init_transformers_model(self):
        """初始化transformers模型"""
        try:
            from transformers import AutoTokenizer, AutoModelForTokenClassification
            import torch

            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForTokenClassification.from_pretrained(self.model_name)
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self.model.to(self.device)
        except Exception as e:
            print(f"Failed to load transformers model: {e}")
            self.use_transformers = False

    def extract_entities(self, text: str) -> List[RecognizedEntity]:
        """提取实体"""
        entities = []

        # 使用transformers模型
        if self.use_transformers and self.model:
            entities.extend(self._extract_with_transformers(text))
        else:
            # 使用规则基础方法
            entities.extend(self._extract_with_rules(text))

        # 后处理
        entities = self._post_process_entities(entities)

        return entities

    def _extract_with_rules(self, text: str) -> List[RecognizedEntity]:
        """使用规则提取实体"""
        entities = []

        for entity_type, patterns in self.entity_patterns.items():
            for pattern in patterns:
                for match in re.finditer(pattern, text):
                    entity = RecognizedEntity(
                        text=match.group(1) if match.lastindex else match.group(0),
                        type=entity_type,
                        start_pos=match.start(),
                        end_pos=match.end(),
                        confidence=0.8
                    )
                    entities.append(entity)

        # 提取机构（更复杂的规则）
        entities.extend(self._extract_institutions(text))

        # 提取方法名
        entities.extend(self._extract_methods(text))

        return entities

    def _extract_institutions(self, text: str) -> List[RecognizedEntity]:
        """提取机构"""
        entities = []

        for keyword in self.institution_keywords:
            pattern = rf'\b([A-Z][A-Za-z\s]+ {keyword})\b|\b({keyword} [A-Z][A-Za-z\s]+)\b'
            for match in re.finditer(pattern, text):
                entity = RecognizedEntity(
                    text=match.group(0),
                    type=EntityType.INSTITUTION,
                    start_pos=match.start(),
                    end_pos=match.end(),
                    confidence=0.85
                )
                entities.append(entity)

        return entities

    def _extract_methods(self, text: str) -> List[RecognizedEntity]:
        """提取方法名"""
        entities = []

        # 常见深度学习模型
        model_patterns = [
            r'\b([A-Z][a-z]+(Net|BERT|GPT|Transformer))\b',
            r'\b(ResNet|VGG|AlexNet|Inception)\b\d*',
            r'\b(LSTM|GRU|RNN|CNN)\b',
            r'\b(GAN|VAE|Diffusion)\b',
            r'\b(BERT|GPT-\d?|RoBERTa|ALBERT|ELECTRA)\b',
        ]

        for pattern in model_patterns:
            for match in re.finditer(pattern, text):
                entity = RecognizedEntity(
                    text=match.group(0),
                    type=EntityType.METHOD,
                    start_pos=match.start(),
                    end_pos=match.end(),
                    confidence=0.9
                )
                entities.append(entity)

        return entities

    def _extract_with_transformers(self, text: str) -> List[RecognizedEntity]:
        """使用transformers模型提取实体"""
        from transformers import AutoTokenizer, AutoModelForTokenClassification
        import torch

        # 分句处理
        sentences = text.split('\n')
        all_entities = []

        for sentence in sentences:
            if not sentence.strip():
                continue

            # Tokenize
            inputs = self.tokenizer(
                sentence,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=512
            )
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            # 预测
            with torch.no_grad():
                outputs = self.model(**inputs)

            predictions = torch.argmax(outputs.logits, dim=-1)

            # 解码
            tokens = self.tokenizer.convert_ids_to_tokens(
                inputs["input_ids"][0]
            )
            pred_labels = predictions[0].cpu().numpy()

            # 提取实体
            current_entity = None
            current_text = []
            current_start = 0

            for i, (token, label) in enumerate(zip(tokens, pred_labels)):
                if token in ["[CLS]", "[SEP]", "[PAD]", "[UNK]"]:
                    continue

                label_name = self.model.config.id2label[label]

                if label_name.startswith("B-"):
                    # 新实体开始
                    if current_entity:
                        all_entities.append(current_entity)

                    current_text = [token]
                    current_start = i
                    entity_type = label_name[2:]

                elif label_name.startswith("I-") and current_entity:
                    current_text.append(token)
                else:
                    if current_entity:
                        all_entities.append(current_entity)
                        current_entity = None

            if current_entity:
                all_entities.append(current_entity)

        return all_entities

    def _post_process_entities(
        self,
        entities: List[RecognizedEntity]
    ) -> List[RecognizedEntity]:
        """后处理实体"""
        # 移除重叠实体（保留置信度更高的）
        entities = self._remove_overlapping_entities(entities)

        # 合并相邻的同类实体
        entities = self._merge_adjacent_entities(entities)

        # 过滤噪声
        entities = self._filter_noise_entities(entities)

        return entities

    def _remove_overlapping_entities(
        self,
        entities: List[RecognizedEntity]
    ) -> List[RecognizedEntity]:
        """移除重叠实体"""
        # 按置信度排序
        entities.sort(key=lambda e: e.confidence, reverse=True)

        filtered = []
        used_ranges = []

        for entity in entities:
            # 检查是否与已选实体重叠
            is_overlapping = False
            for start, end in used_ranges:
                if (entity.start_pos < end and entity.end_pos > start):
                    is_overlapping = True
                    break

            if not is_overlapping:
                filtered.append(entity)
                used_ranges.append((entity.start_pos, entity.end_pos))

        return filtered

    def _merge_adjacent_entities(
        self,
        entities: List[RecognizedEntity]
    ) -> List[RecognizedEntity]:
        """合并相邻实体"""
        if not entities:
            return []

        # 按位置排序
        entities.sort(key=lambda e: e.start_pos)

        merged = [entities[0]]

        for entity in entities[1:]:
            last = merged[-1]

            # 检查是否相邻且类型相同
            if (entity.type == last.type and
                entity.start_pos <= last.end_pos + 2 and
                entity.start_pos >= last.end_pos):
                # 合并
                merged_text = last.text + " " + entity.text
                last.text = merged_text
                last.end_pos = entity.end_pos
                last.confidence = (last.confidence + entity.confidence) / 2
            else:
                merged.append(entity)

        return merged

    def _filter_noise_entities(
        self,
        entities: List[RecognizedEntity]
    ) -> List[RecognizedEntity]:
        """过滤噪声实体"""
        filtered = []

        for entity in entities:
            text = entity.text.strip()

            # 过滤太短的
            if len(text) < 2:
                continue

            # 过滤包含数字过多的
            digit_ratio = sum(c.isdigit() for c in text) / len(text)
            if digit_ratio > 0.5:
                continue

            # 过滤常见噪声词
            noise_words = ["Figure", "Table", "Eq", "Figure", "Tab"]
            if any(text.startswith(w) for w in noise_words):
                continue

            filtered.append(entity)

        return filtered

    def extract_from_document(self, doc: ParsedDocument) -> List[RecognizedEntity]:
        """从文档中提取实体"""
        text = doc.content
        entities = self.extract_entities(text)

        # 添加文档相关属性
        for entity in entities:
            entity.properties["source_document"] = doc.file_path

        return entities

    def recognize_to_entities(
        self,
        text: str,
        id_prefix: str = "ent"
    ) -> List[Entity]:
        """将识别结果转换为Entity列表"""
        recognized = self.extract_entities(text)

        entities = []
        for i, rec in enumerate(recognized):
            entity = Entity(
                id=f"{id_prefix}_{i}",
                name=rec.text,
                type=rec.type,
                properties={
                    "confidence": rec.confidence,
                    "start_pos": rec.start_pos,
                    "end_pos": rec.end_pos
                }
            )
            entities.append(entity)

        return entities
