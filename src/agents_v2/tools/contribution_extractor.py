"""
论文贡献提取器

功能:
1. 从摘要提取贡献声明
2. 从引言提取创新点
3. 从结论提取总结
4. 生成创新性声明

设计原则:
- 多源融合提取贡献
- 分类和排序贡献重要性
- 生成简洁的创新性声明
"""
import re
import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ContributionType(str, Enum):
    """贡献类型"""
    METHOD = "method"        # 方法创新
    THEORY = "theory"        # 理论贡献
    APPLICATION = "application"  # 应用贡献
    DATASET = "dataset"      # 数据集贡献
    ALGORITHM = "algorithm"  # 算法改进
    FRAMEWORK = "framework"  # 系统框架
    INSIGHT = "insight"      # 新见解


@dataclass
class Contribution:
    """论文贡献"""
    type: ContributionType
    description: str
    evidence: str = ""  # 证据来源
    chapter: str = ""   # 来自哪个章节
    confidence: float = 0.5  # 置信度


@dataclass
class PaperContributions:
    """论文贡献集合"""
    contributions: List[Contribution] = field(default_factory=list)
    novelty_statement: str = ""  # 创新性声明
    impact_summary: str = ""      # 影响总结
    main_contribution: str = ""   # 最主要的贡献


class ContributionExtractor:
    """论文贡献提取器"""

    # 贡献声明模式
    CONTRIBUTION_PATTERNS = {
        # 明确的贡献声明
        "we_propose": [
            r'we\s+propose\s+([^.]+)',
            r'this\s+paper\s+proposes\s+([^.]+)',
            r'we\s+present\s+([^.]+)',
            r'we\s+introduce\s+([^.]+)',
        ],
        "contribute": [
            r'our\s+contribution\s+(?:is|includes?|to)\s+([^.]+)',
            r'we\s+contribute\s+([^.]+)',
            r'major\s+contributions?\s+(?:include|are)\s+([^.]+)',
        ],
        "novel": [
            r'(?:novel|new|original)\s+([^.]+)',
            r'first\s+to\s+([^.]+)',
            r'first\s+(?:propose|introduce|present)\s+([^.]+)',
        ],
        "improve": [
            r'(?:significantly|substantially)\s+improve\s+([^.]+)',
            r'outperform(?:s|ed)?\s+([^.]+)',
            r'state-of-the-art\s+([^.]+)',
        ],
    }

    # 中文贡献模式
    CHINESE_PATTERNS = {
        "提出": [r'(?:我们)?\s*提出\s+([^。]+)', r'(?:本文)?\s*提出\s+([^。]+)'],
        "贡献": [r'主要贡献\s+(?:包括)?\s*([^。]+)', r'贡献\s+(?:包括)?\s*([^。]+)'],
        "创新": [r'(?:具有)?\s*创新性\s+([^。]+)', r'创新点\s+(?:在于)?\s*([^。]+)'],
        "首次": [r'首次\s+([^。]+)', r'首次提出\s+([^。]+)'],
    }

    def __init__(self, llm: Any = None):
        self.llm = llm

    async def extract(
        self,
        paper_content: Dict[str, Any]
    ) -> PaperContributions:
        """提取论文贡献

        Args:
            paper_content: 论文内容，包含以下键：
                - abstract: 摘要
                - introduction: 引言
                - conclusion: 结论
                - method: 方法章节（可选）

        Returns:
            PaperContributions: 贡献集合
        """
        all_contributions = []

        # 1. 从摘要提取
        if "abstract" in paper_content:
            abstract_contrib = self._extract_from_abstract(paper_content["abstract"])
            all_contributions.extend(abstract_contrib)

        # 2. 从引言提取
        if "introduction" in paper_content:
            intro_contrib = self._extract_from_introduction(paper_content["introduction"])
            all_contributions.extend(intro_contrib)

        # 3. 从结论提取
        if "conclusion" in paper_content:
            conclusion_contrib = self._extract_from_conclusion(paper_content["conclusion"])
            all_contributions.extend(conclusion_contrib)

        # 4. 从方法章节提取（如果提供）
        if "method" in paper_content:
            method_contrib = self._extract_from_method(paper_content["method"])
            all_contributions.extend(method_contrib)

        # 5. 融合去重
        merged = self._merge_contributions(all_contributions)

        # 6. 分类
        categorized = self._categorize_contributions(merged)

        # 7. 生成创新性声明
        novelty = await self._generate_novelty_statement(categorized)
        impact = await self._generate_impact_summary(categorized)
        main = self._identify_main_contribution(categorized)

        return PaperContributions(
            contributions=categorized,
            novelty_statement=novelty,
            impact_summary=impact,
            main_contribution=main
        )

    def _extract_from_abstract(self, abstract: str) -> List[Contribution]:
        """从摘要提取贡献"""
        contributions = []

        # 查找明确的贡献声明
        for pattern_key, patterns in self.CONTRIBUTION_PATTERNS.items():
            for pattern in patterns:
                matches = re.finditer(pattern, abstract, re.IGNORECASE)
                for match in matches:
                    desc = match.group(1).strip()
                    if len(desc) > 10:  # 过滤太短的
                        contributions.append(Contribution(
                            type=self._infer_contribution_type(desc),
                            description=desc,
                            evidence=f"Abstract: {match.group(0)[:50]}...",
                            chapter="abstract",
                            confidence=0.8
                        ))

        # 检查中文模式
        for pattern_key, patterns in self.CHINESE_PATTERNS.items():
            for pattern in patterns:
                matches = re.finditer(pattern, abstract)
                for match in matches:
                    desc = match.group(1).strip()
                    if len(desc) > 10:
                        contributions.append(Contribution(
                            type=self._infer_contribution_type(desc),
                            description=desc,
                            evidence=f"摘要中'{pattern_key}'表述",
                            chapter="abstract",
                            confidence=0.8
                        ))

        return contributions

    def _extract_from_introduction(self, introduction: str) -> List[Contribution]:
        """从引言提取贡献"""
        contributions = []

        # 引言中的贡献声明通常在最后几段
        paragraphs = introduction.split('\n\n')
        last_paragraphs = paragraphs[-3:] if len(paragraphs) > 3 else paragraphs

        for para in last_paragraphs:
            # 查找 "Our contributions include..."
            if re.search(r'contributions?\s+(?:include|are|et al\.)', para, re.IGNORECASE):
                # 提取列表项
                items = re.findall(r'(?:•|-|\d+\.)\s*([^.\n]+)', para)
                for item in items:
                    if len(item) > 10:
                        contributions.append(Contribution(
                            type=self._infer_contribution_type(item),
                            description=item.strip(),
                            evidence="Introduction contribution list",
                            chapter="introduction",
                            confidence=0.9
                        ))

            # 查找 "The key contributions of this paper are..."
            key_match = re.search(r'(?:key|major|main)\s+contributions?\s+(?:of this paper)?\s*(?:include|are|:)\s*([^.]+)', para, re.IGNORECASE)
            if key_match:
                text = key_match.group(1)
                # 可能包含多个贡献点
                items = re.split(r'(?:,|and|;|\d+\.)', text)
                for item in items:
                    item = item.strip()
                    if len(item) > 10:
                        contributions.append(Contribution(
                            type=self._infer_contribution_type(item),
                            description=item,
                            evidence="Introduction key contributions",
                            chapter="introduction",
                            confidence=0.95
                        ))

        # 中文引言模式
        for para in last_paragraphs:
            if re.search(r'主要贡献|本文贡献', para):
                items = re.findall(r'(?:[①②③]|[a-c])\s*([^。\n]+)', para)
                for item in items:
                    if len(item) > 5:
                        contributions.append(Contribution(
                            type=self._infer_contribution_type(item),
                            description=item.strip(),
                            evidence="引言贡献声明",
                            chapter="introduction",
                            confidence=0.9
                        ))

        return contributions

    def _extract_from_conclusion(self, conclusion: str) -> List[Contribution]:
        """从结论提取贡献"""
        contributions = []

        # 结论中的贡献通常以总结形式呈现
        # 查找 "In this paper, we..."
        matches = re.finditer(r'in\s+this\s+(?:paper|study)\s+(?:propose|present|introduce|develop)\s+([^.]+)', conclusion, re.IGNORECASE)
        for match in matches:
            desc = match.group(1).strip()
            if len(desc) > 10:
                contributions.append(Contribution(
                    type=self._infer_contribution_type(desc),
                    description=desc,
                    evidence="Conclusion summary",
                    chapter="conclusion",
                    confidence=0.7
                ))

        # 查找 "We have shown that..."
        matches = re.finditer(r'we\s+(?:have\s+)?shown\s+([^.]+)', conclusion, re.IGNORECASE)
        for match in matches:
            desc = match.group(1).strip()
            if len(desc) > 10:
                contributions.append(Contribution(
                    type=ContributionType.INSIGHT,
                    description=f"Shown: {desc}",
                    evidence="Conclusion claim",
                    chapter="conclusion",
                    confidence=0.6
                ))

        return contributions

    def _extract_from_method(self, method: str) -> List[Contribution]:
        """从方法章节提取独特设计"""
        contributions = []

        # 查找方法中的独特创新点
        innovation_keywords = [
            "novel", "new", "original", "unique", "innovative",
            "提出", "创新", "独特", "首次"
        ]

        sentences = method.split('.')
        for sent in sentences:
            sent_lower = sent.lower()
            if any(kw in sent_lower for kw in innovation_keywords):
                if len(sent) > 20 and len(sent) < 200:
                    contributions.append(Contribution(
                        type=self._infer_contribution_type(sent),
                        description=sent.strip(),
                        evidence="Method section innovation",
                        chapter="method",
                        confidence=0.6
                    ))

        return contributions

    def _infer_contribution_type(self, text: str) -> ContributionType:
        """推断贡献类型"""
        text_lower = text.lower()

        if any(kw in text_lower for kw in ['method', 'approach', 'model', 'architecture']):
            return ContributionType.METHOD
        elif any(kw in text_lower for kw in ['theory', 'theorem', 'proof', 'analysis']):
            return ContributionType.THEORY
        elif any(kw in text_lower for kw in ['algorithm', 'optimization', 'efficiency']):
            return ContributionType.ALGORITHM
        elif any(kw in text_lower for kw in ['dataset', 'benchmark', 'evaluation']):
            return ContributionType.DATASET
        elif any(kw in text_lower for kw in ['framework', 'system', 'platform']):
            return ContributionType.FRAMEWORK
        elif any(kw in text_lower for kw in ['find', 'discover', 'insight', 'reveal']):
            return ContributionType.INSIGHT
        else:
            return ContributionType.APPLICATION

    def _merge_contributions(
        self,
        contributions: List[Contribution]
    ) -> List[Contribution]:
        """融合去重相似的贡献"""
        if not contributions:
            return []

        merged = []
        seen = set()

        for contrib in contributions:
            # 创建简化的指纹
            fingerprint = self._create_fingerprint(contrib.description)

            if fingerprint not in seen:
                seen.add(fingerprint)
                merged.append(contrib)
            else:
                # 找到已存在的，增强置信度
                for existing in merged:
                    if self._create_fingerprint(existing.description) == fingerprint:
                        existing.confidence = min(1.0, existing.confidence + 0.1)
                        # 保留更详细的描述
                        if len(contrib.description) > len(existing.description):
                            existing.description = contrib.description
                        break

        # 按置信度排序
        merged.sort(key=lambda x: x.confidence, reverse=True)

        return merged

    def _create_fingerprint(self, text: str) -> str:
        """创建文本指纹用于去重"""
        # 移除常见动词和修饰词
        words_to_remove = ['we', 'our', 'the', 'a', 'an', 'this', 'paper', 'study']
        words = text.lower().split()
        filtered = [w for w in words if w not in words_to_remove]
        return ' '.join(filtered[:10])

    def _categorize_contributions(
        self,
        contributions: List[Contribution]
    ) -> List[Contribution]:
        """对贡献进行分类"""
        categorized = []

        for contrib in contributions:
            # 更新类型（可能已经更准确）
            contrib.type = self._infer_contribution_type(contrib.description)
            categorized.append(contrib)

        return categorized

    async def _generate_novelty_statement(
        self,
        contributions: List[Contribution]
    ) -> str:
        """生成创新性声明

        Args:
            contributions: 贡献列表

        Returns:
            str: 创新性声明（一句话）
        """
        if not contributions:
            return "No clear novelty statement extracted."

        # 找出置信度最高的贡献
        top_contrib = contributions[0]

        # 构建声明
        statement = f"本文首次提出{top_contrib.description}"

        # 检查是否需要使用LLM
        if self.llm and len(contributions) > 1:
            try:
                prompt = f"""
基于以下论文贡献，生成一句简洁的创新性声明（50字以内）：

贡献列表：
{chr(10).join([f"- {c.description}" for c in contributions[:5]])}

创新性声明应该：
1. 突出与已有工作的最大区别
2. 使用"首次"、"novel"、"首次提出"等表达
3. 控制在50字以内

只返回声明，不要其他解释。
"""
                from langchain_core.messages import HumanMessage, SystemMessage
                messages = [
                    SystemMessage(content="你是一个研究论文写作专家。"),
                    HumanMessage(content=prompt)
                ]
                response = await self.llm.ainvoke(messages)
                content = response.content if hasattr(response, 'content') else str(response)
                return content.strip()

            except Exception as e:
                logger.warning(f"LLM novelty statement generation failed: {e}")
                return statement

        return statement

    async def _generate_impact_summary(
        self,
        contributions: List[Contribution]
    ) -> str:
        """生成影响总结

        Args:
            contributions: 贡献列表

        Returns:
            str: 影响总结
        """
        if not contributions:
            return "No impact summary extracted."

        # 统计贡献类型分布
        type_counts = {}
        for contrib in contributions:
            type_counts[contrib.type.value] = type_counts.get(contrib.type.value, 0) + 1

        # 构建总结
        summary_parts = []
        for contrib_type, count in type_counts.items():
            summary_parts.append(f"{contrib_type}({count})")

        return f"本文贡献类型分布: {', '.join(summary_parts)}"

    def _identify_main_contribution(self, contributions: List[Contribution]) -> str:
        """识别最主要贡献

        Args:
            contributions: 贡献列表

        Returns:
            str: 最主要贡献的描述
        """
        if not contributions:
            return ""

        # 返回置信度最高的
        return contributions[0].description


# 便捷函数
async def extract_paper_contributions(
    paper_content: Dict[str, Any],
    llm: Any = None
) -> PaperContributions:
    """提取论文贡献的便捷函数

    Args:
        paper_content: 论文内容
        llm: 可选的LLM实例

    Returns:
        PaperContributions: 贡献集合
    """
    extractor = ContributionExtractor(llm)
    return await extractor.extract(paper_content)


def get_contributions_by_type(
    contributions: List[Contribution],
    contrib_type: ContributionType
) -> List[Contribution]:
    """按类型筛选贡献

    Args:
        contributions: 贡献列表
        contrib_type: 贡献类型

    Returns:
        List[Contribution]: 筛选后的贡献
    """
    return [c for c in contributions if c.type == contrib_type]