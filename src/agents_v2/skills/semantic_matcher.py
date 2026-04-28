"""
Semantic Skill Matcher - 语义技能匹配器

基于语义理解而非关键词匹配技能。
"""
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import math
import logging

logger = logging.getLogger(__name__)


@dataclass
class Skill:
    """技能定义"""
    skill_id: str
    name: str
    description: str
    category: str = ""
    success_rate: float = 0.5  # 成功率
    usage_count: int = 0  # 使用次数
    avg_execution_time: float = 0.0  # 平均执行时间
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SkillMatch:
    """技能匹配结果"""
    skill: Skill
    score: float
    match_type: str  # "exact", "semantic", "category"


class SemanticSkillMatcher:
    """
    语义技能匹配器

    基于语义理解而非关键词匹配技能

    使用示例:
        matcher = SemanticSkillMatcher()

        # 注册技能
        await matcher.register_skill(Skill(
            skill_id="draft_write",
            name="论文写作",
            description="撰写学术论文"
        ))

        # 匹配技能
        matches = await matcher.match_skills("帮我写一篇深度学习论文")
        print(f"最佳匹配: {matches[0].skill.name}")
    """

    def __init__(self, embedding_model: Any = None):
        self.embedding_model = embedding_model
        self._skill_embeddings: Dict[str, List[float]] = {}
        self._skill_library: Dict[str, Skill] = {}

    async def register_skill(
        self,
        skill: Skill,
        description_embedding: Optional[List[float]] = None
    ) -> None:
        """
        注册技能并计算嵌入

        Args:
            skill: 技能定义
            description_embedding: 描述嵌入（可选）
        """
        self._skill_library[skill.skill_id] = skill

        if description_embedding:
            self._skill_embeddings[skill.skill_id] = description_embedding
        else:
            # 使用LLM生成描述嵌入
            embedding = await self._generate_embedding(skill.description)
            self._skill_embeddings[skill.skill_id] = embedding

        logger.debug(f"Registered skill: {skill.name}")

    async def match_skills(
        self,
        task_description: str,
        top_k: int = 5,
        min_score: float = 0.5,
        category: Optional[str] = None
    ) -> List[SkillMatch]:
        """
        匹配技能

        Args:
            task_description: 任务描述
            top_k: 返回前K个匹配
            min_score: 最低分数阈值
            category: 限定类别

        Returns:
            List[SkillMatch]: 匹配的技能列表
        """
        # 生成任务嵌入
        task_embedding = await self._generate_embedding(task_description)

        # 计算与所有技能的相似度
        scores = []
        for skill_id, skill in self._skill_library.items():
            # 类别过滤
            if category and skill.category != category:
                continue

            # 计算语义相似度
            skill_emb = self._skill_embeddings.get(skill_id)
            if not skill_emb:
                continue

            similarity = self._cosine_similarity(task_embedding, skill_emb)

            # 结合技能质量（使用率、成功率）
            quality_factor = (
                skill.success_rate * 0.3 +
                min(skill.usage_count / 100, 1.0) * 0.2
            )

            # 综合分数
            final_score = similarity * 0.7 + quality_factor * 0.3

            if final_score >= min_score:
                scores.append(SkillMatch(
                    skill=skill,
                    score=final_score,
                    match_type="semantic"
                ))

        # 排序返回
        scores.sort(key=lambda x: x.score, reverse=True)

        return scores[:top_k]

    async def match_skills_by_keywords(
        self,
        keywords: List[str],
        top_k: int = 5
    ) -> List[SkillMatch]:
        """
        基于关键词匹配技能

        Args:
            keywords: 关键词列表
            top_k: 返回前K个匹配

        Returns:
            List[SkillMatch]: 匹配的技能列表
        """
        keyword_set = set(k.lower() for k in keywords)
        scores = []

        for skill_id, skill in self._skill_library.items():
            # 检查关键词重叠
            skill_keywords = set(
                k.lower()
                for k in skill.name.split() + skill.description.split()
            )

            overlap = len(keyword_set & skill_keywords)
            if overlap == 0:
                continue

            # Jaccard相似度
            union = len(keyword_set | skill_keywords)
            score = overlap / union if union > 0 else 0

            scores.append(SkillMatch(
                skill=skill,
                score=score,
                match_type="keyword"
            ))

        scores.sort(key=lambda x: x.score, reverse=True)
        return scores[:top_k]

    async def _generate_embedding(self, text: str) -> List[float]:
        """生成文本嵌入"""
        if self.embedding_model:
            try:
                return self.embedding_model.encode(text)
            except Exception as e:
                logger.warning(f"Embedding generation failed: {e}")

        # 回退：使用TF-IDF或简单词袋
        return self._simple_embedding(text)

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        dot = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))

        return dot / (norm1 * norm2) if norm1 and norm2 else 0.0

    def _simple_embedding(self, text: str) -> List[float]:
        """简单嵌入（词袋）"""
        words = text.lower().split()
        vec = [0.0] * 1000

        for i, word in enumerate(words[:100]):
            vec[hash(word) % 1000] += 1

        # 归一化
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]

        return vec

    def get_skill(self, skill_id: str) -> Optional[Skill]:
        """获取技能"""
        return self._skill_library.get(skill_id)

    def get_all_skills(self, category: Optional[str] = None) -> List[Skill]:
        """获取所有技能"""
        if category:
            return [s for s in self._skill_library.values() if s.category == category]
        return list(self._skill_library.values())

    def record_skill_usage(
        self,
        skill_id: str,
        success: bool,
        execution_time: float
    ) -> None:
        """记录技能使用"""
        skill = self._skill_library.get(skill_id)
        if not skill:
            return

        skill.usage_count += 1

        # 更新成功率（指数移动平均）
        old_rate = skill.success_rate
        skill.success_rate = old_rate * 0.9 + (1.0 if success else 0.0) * 0.1

        # 更新平均执行时间
        if skill.avg_execution_time == 0:
            skill.avg_execution_time = execution_time
        else:
            skill.avg_execution_time = (
                skill.avg_execution_time * 0.9 + execution_time * 0.1
            )


class SkillRegistry:
    """技能注册表"""

    def __init__(self):
        self._skills: Dict[str, Skill] = {}
        self._categories: Dict[str, List[str]] = {}  # category -> skill_ids

    def register(self, skill: Skill) -> None:
        """注册技能"""
        self._skills[skill.skill_id] = skill

        if skill.category:
            if skill.category not in self._categories:
                self._categories[skill.category] = []
            self._categories[skill.category].append(skill.skill_id)

    def get(self, skill_id: str) -> Optional[Skill]:
        """获取技能"""
        return self._skills.get(skill_id)

    def get_by_category(self, category: str) -> List[Skill]:
        """按类别获取技能"""
        skill_ids = self._categories.get(category, [])
        return [self._skills[sid] for sid in skill_ids if sid in self._skills]

    def list_categories(self) -> List[str]:
        """列出所有类别"""
        return list(self._categories.keys())

    def list_all(self) -> List[Skill]:
        """列出所有技能"""
        return list(self._skills.values())


def create_skill_matcher(embedding_model: Any = None) -> SemanticSkillMatcher:
    """创建语义技能匹配器"""
    return SemanticSkillMatcher(embedding_model=embedding_model)


def create_skill_registry() -> SkillRegistry:
    """创建技能注册表"""
    return SkillRegistry()
