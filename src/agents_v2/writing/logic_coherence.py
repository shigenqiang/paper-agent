"""
论文逻辑一致性检查器

功能:
1. 论文各章节间的逻辑连贯性检查
2. 引用关系的一致性验证
3. 论点与论据的匹配检查
4. 生成后的自我修订机制

设计原则:
- 作为后处理步骤，对生成内容进行检查
- 发现问题后提供具体的修复建议
- 不阻断生成流程，但标记需要人工审核的区域
"""
from src.agents_v2.logging_config import get_logging_logger

import re

from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING
from dataclasses import dataclass, field
import json

logger = get_logging_logger(__name__)


@dataclass
class CoherenceIssue:
    """一致性问题"""
    issue_type: str  # "citation", "logic", "structure", "terminology", "reference"
    severity: str  # "critical", "major", "minor"
    location: str  # "Chapter X", "Section Y", etc.
    description: str
    suggestion: str  # 修复建议
    original_text: str = ""
    recommended_fix: str = ""


@dataclass
class CoherenceReport:
    """一致性检查报告"""
    passed: bool
    overall_score: float  # 0-1
    issues: List[CoherenceIssue] = field(default_factory=list)
    citation_map: Dict[str, List[str]] = field(default_factory=dict)  # 引用映射
    terminology_map: Dict[str, str] = field(default_factory=dict)  # 术语映射
    logical_flow_score: float = 0.0
    structural_score: float = 0.0

    def get_issues_by_severity(self, severity: str) -> List[CoherenceIssue]:
        return [i for i in self.issues if i.severity == severity]

    def has_critical_issues(self) -> bool:
        return any(i.severity == "critical" for i in self.issues)

    def summary(self) -> str:
        critical = len(self.get_issues_by_severity("critical"))
        major = len(self.get_issues_by_severity("major"))
        minor = len(self.get_issues_by_severity("minor"))
        return f"Issues found: {critical} critical, {major} major, {minor} minor. Score: {self.overall_score:.2f}"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "passed": self.passed,
            "overall_score": self.overall_score,
            "issues": [
                {
                    "severity": i.severity,
                    "issue_type": i.issue_type,
                    "description": i.description,
                    "location": i.location,
                    "recommended_fix": i.recommended_fix,
                }
                for i in self.issues
            ],
            "citation_map": self.citation_map,
            "terminology_map": self.terminology_map,
            "logical_flow_score": self.logical_flow_score,
            "structural_score": self.structural_score,
        }


class LogicCoherenceChecker:
    """论文逻辑一致性检查器"""

    def __init__(self):
        self.issue_patterns = self._init_issue_patterns()

    def _init_issue_patterns(self) -> Dict[str, re.Pattern]:
        """初始化检查模式"""
        return {
            # 未定义的引用
            "undefined_citation": re.compile(r'\[(\d+)\](?!.*?\[\1\])'),
            # 可能的术语不一致
            "terminology_variation": re.compile(
                r'\b(our method|our approach|this paper|this study|we)\b',
                re.IGNORECASE
            ),
            # 缺少过渡词
            "missing_transition": re.compile(
                r'\n\n([A-Z][a-z]+)',
            ),
            # 空洞的结论表述
            "weak_conclusion": re.compile(
                r'(very|quite|somewhat|fairly|interesting|important)\s+\w+',
                re.IGNORECASE
            ),
            # 逻辑连接词缺失
            "missing_connectors": re.compile(
                r'([.!?])\s*([A-Z][a-z]+\s+(?:show|indicates|suggests|demonstrates|reveals))',
            ),
        }

    async def check_draft(
        self,
        draft: str,
        outline: Dict[str, Any],
        references: List[str]
    ) -> CoherenceReport:
        """检查论文初稿的一致性

        Args:
            draft: 论文全文
            outline: 大纲结构
            references: 参考文献列表

        Returns:
            CoherenceReport
        """
        issues = []

        # 1. 检查章节结构连贯性
        structural_issues = self._check_structure(draft, outline)
        issues.extend(structural_issues)

        # 2. 检查引用一致性
        citation_issues = self._check_citations(draft, references)
        issues.extend(citation_issues)

        # 3. 检查术语一致性
        terminology_issues = self._check_terminology(draft)
        issues.extend(terminology_issues)

        # 4. 检查逻辑流
        logical_issues = self._check_logical_flow(draft)
        issues.extend(logical_issues)

        # 5. 检查引用映射关系
        citation_map = self._extract_citation_map(draft)
        terminology_map = self._extract_terminology_map(draft)

        # 计算各项分数
        structural_score = max(0, 1 - len(structural_issues) * 0.1)
        citation_score = max(0, 1 - len(citation_issues) * 0.2)
        terminology_score = max(0, 1 - len(terminology_issues) * 0.15)
        logical_score = max(0, 1 - len(logical_issues) * 0.1)

        overall_score = (
            structural_score * 0.25 +
            citation_score * 0.3 +
            terminology_score * 0.2 +
            logical_score * 0.25
        )

        return CoherenceReport(
            passed=not any(i.severity == "critical" for i in issues),
            overall_score=overall_score,
            issues=issues,
            citation_map=citation_map,
            terminology_map=terminology_map,
            logical_flow_score=logical_score,
            structural_score=structural_score
        )

    def _check_structure(
        self,
        draft: str,
        outline: Dict[str, Any]
    ) -> List[CoherenceIssue]:
        """检查章节结构"""
        issues = []
        chapters = outline.get("chapters", [])

        # 检查大纲中的章节是否都在正文中
        for i, chapter in enumerate(chapters):
            title = chapter.get("title", "")
            if title and title.lower() not in draft.lower():
                issues.append(CoherenceIssue(
                    issue_type="structure",
                    severity="major",
                    location=f"Chapter {i+1}",
                    description=f"章节标题 '{title}' 未在正文中找到",
                    suggestion="确保章节标题完全匹配或在正文中使用相同术语"
                ))

        # 检查章节顺序
        chapter_positions = []
        for i, chapter in enumerate(chapters):
            title = chapter.get("title", "")
            if title:
                match = re.search(rf'{re.escape(title)}', draft, re.IGNORECASE)
                if match:
                    chapter_positions.append((title, match.start()))

        # 检查是否有章节被跳过
        for j in range(len(chapter_positions) - 1):
            title1, pos1 = chapter_positions[j]
            title2, pos2 = chapter_positions[j + 1]
            if pos2 < pos1:
                issues.append(CoherenceIssue(
                    issue_type="structure",
                    severity="major",
                    location=title1,
                    description=f"章节顺序异常：'{title2}' 出现在 '{title1}' 之前",
                    suggestion="调整章节顺序使其符合逻辑"
                ))

        return issues

    def _check_citations(
        self,
        draft: str,
        references: List[str]
    ) -> List[CoherenceIssue]:
        """检查引用一致性"""
        issues = []

        # 提取所有引用
        citation_pattern = r'\[(\d+(?:-\d+)?(?:,\s*\d+(?:-\d+)?)*)\]'
        citations = re.findall(citation_pattern, draft)

        # 扩展引用的引用编号
        all_cited_nums = set()
        for cit in citations:
            nums = re.findall(r'\d+', cit)
            for num in nums:
                all_cited_nums.add(int(num))

        # 检查引用编号是否超出范围
        max_ref = len(references)
        for num in all_cited_nums:
            if num > max_ref:
                issues.append(CoherenceIssue(
                    issue_type="citation",
                    severity="critical",
                    location="全文",
                    description=f"引用编号 [{num}] 超出参考文献范围（共{max_ref}条）",
                    suggestion=f"检查是否应该是 [{min(num, max_ref)}] 或其他有效编号"
                ))

        # 检查是否有悬空引用（只有数字没有对应参考文献）
        ref_section = re.search(r'(?:References|Bibliography|参考文献)(.*?)$', draft, re.DOTALL | re.IGNORECASE)
        if not ref_section:
            issues.append(CoherenceIssue(
                issue_type="citation",
                severity="critical",
                location="全文",
                description="未找到参考文献部分",
                suggestion="确保参考文献部分存在且包含所有引用的文献"
            ))

        return issues

    def _check_terminology(self, draft: str) -> List[CoherenceIssue]:
        """检查术语一致性"""
        issues = []

        # 常见需要保持一致的术语对
        terminology_pairs = [
            # 英文术语变体
            ("neural network", "neural networks"),
            ("deep learning", "deep learn"),
            ("machine learning", "machine learning"),
            ("our method", "the proposed method"),
            ("this paper", "this study"),
            # 中文术语变体
            ("神经网络", "神经网路"),
            ("深度学习", "深度 学习"),
            ("机器学习", "机器 学习"),
        ]

        # 检查第一段出现的术语在后续是否保持一致
        first_para_match = re.match(r'^(.*?)\n\n', draft, re.DOTALL)
        if not first_para_match:
            return issues

        first_para = first_para_match.group(1).lower()

        # 检测后续段落中可能的不一致用法
        for term1, term2 in terminology_pairs:
            if term1.lower() in first_para:
                # 检查是否在后续使用了变体
                if term2.lower() in draft.lower():
                    # 确认不是偶然出现
                    if term1.lower() not in term2.lower():
                        issues.append(CoherenceIssue(
                            issue_type="terminology",
                            severity="minor",
                            location="术语使用",
                            description=f"可能存在术语不一致：'{term1}' 和 '{term2}'",
                            suggestion=f"统一使用 '{term1}'"
                        ))

        return issues

    def _check_logical_flow(self, draft: str) -> List[CoherenceIssue]:
        """检查逻辑流程"""
        issues = []

        # 检查章节间的过渡
        chapter_headers = re.findall(r'\n##\s+(.+?)\n', draft)
        if len(chapter_headers) > 1:
            for i in range(len(chapter_headers) - 1):
                current = chapter_headers[i]
                next_ch = chapter_headers[i + 1]

                # 检查两章之间是否有过渡内容
                current_pos = draft.find(f"## {current}")
                next_pos = draft.find(f"## {next_ch}")

                between_text = draft[next_pos:next_pos + 100] if next_pos > 0 else ""

                # 检查下一章开头是否有逻辑连接词
                if next_pos > 0:
                    next_start = draft[next_pos:next_pos + 200]
                    if not re.search(r'\b(However|But|Therefore|Thus|Additionally|Furthermore|Moreover|Meanwhile)\b', next_start, re.IGNORECASE):
                        if len(chapter_headers) > 1:  # 不是最后一章
                            issues.append(CoherenceIssue(
                                issue_type="logic",
                                severity="minor",
                                location=f"'{next_ch}' 开头",
                                description="章节间缺少过渡词",
                                suggestion="在章节开头添加 'However', 'Furthermore' 等过渡词以改善流畅性"
                            ))

        # 检查论点与论据的匹配
        claim_pattern = r'(we show|we demonstrate|we prove|实验表明|研究表明|本文证明)'
        claims = re.finditer(claim_pattern, draft, re.IGNORECASE)

        for claim in claims:
            claim_pos = claim.start()
            # 检查claim后面是否有具体数据或证据
            following_text = draft[claim_pos:claim_pos + 500]

            # 查找是否有具体数字或实验结果
            has_evidence = bool(re.search(r'\d+(\.\d+)?%|\d+\.\d+%|实验结果|准确率|召回率|F1', following_text))

            if not has_evidence:
                issues.append(CoherenceIssue(
                    issue_type="logic",
                    severity="major",
                    location=f"位置 {claim_pos}",
                    description="论点缺乏具体证据支持",
                    suggestion="在声称后面添加具体的数据或实验结果作为支撑"
                ))

        return issues

    def _extract_citation_map(self, draft: str) -> Dict[str, List[str]]:
        """提取引用映射（章节->引用）"""
        citation_map = {}

        # 找到每个章节的引用
        chapter_sections = re.split(r'\n##\s+', draft)

        for section in chapter_sections[1:]:  # 跳过可能是摘要的部分
            if not section.strip():
                continue

            # 获取章节标题
            title_match = re.match(r'(.+?)\n', section)
            if not title_match:
                continue

            chapter_title = title_match.group(1).strip()

            # 提取该章节中的引用
            citations = re.findall(r'\[(\d+(?:-\d+)?)\]', section)
            citation_map[chapter_title] = citations

        return citation_map

    def _extract_terminology_map(self, draft: str) -> Dict[str, str]:
        """提取术语映射"""
        terminology_map = {}

        # 提取首次出现的关键术语及其定义
        definition_patterns = [
            r'(?:called|termed|defined as|称为|定义为)\s+["\'](.+?)["\']',
            r'(.+?)\s+(?:called|termed|defined as|称为|定义为)\s+["\'](.+?)["\']',
        ]

        for pattern in definition_patterns:
            matches = re.finditer(pattern, draft, re.IGNORECASE)
            for match in matches:
                if len(match.groups()) >= 2:
                    term = match.group(1).strip()
                    definition = match.group(2).strip()
                    if len(term) < 50 and len(definition) < 100:
                        terminology_map[term] = definition

        return terminology_map


class SelfReviseManager:
    """自我修订管理器

    基于一致性检查报告，对生成的内容进行自动修订
    """

    def __init__(self, checker: Optional[LogicCoherenceChecker] = None):
        self.checker = checker or LogicCoherenceChecker()

    async def revise_draft(
        self,
        draft: str,
        outline: Dict[str, Any],
        references: List[str],
        auto_fix: bool = True
    ) -> Tuple[str, CoherenceReport]:
        """修订论文初稿

        Args:
            draft: 论文全文
            outline: 大纲结构
            references: 参考文献列表
            auto_fix: 是否自动修复可修复的问题

        Returns:
            (修订后的文本, 一致性检查报告)
        """
        # 1. 执行一致性检查
        report = await self.checker.check_draft(draft, outline, references)

        if not auto_fix or report.passed:
            return draft, report

        # 2. 自动修复可修复的问题
        revised_draft = draft

        for issue in report.issues:
            if issue.severity == "critical":
                # 严重问题标记，不自动修复
                logger.warning(f"Critical issue in draft: {issue.description}")
                continue

            if issue.issue_type == "logic" and issue.severity == "minor":
                # 逻辑问题可以通过添加过渡词修复
                revised_draft = self._fix_logical_issue(revised_draft, issue)

            elif issue.issue_type == "terminology":
                # 术语问题可以自动替换
                revised_draft = self._fix_terminology_issue(revised_draft, issue)

        return revised_draft, report

    def _fix_logical_issue(self, text: str, issue: CoherenceIssue) -> str:
        """修复逻辑问题"""
        if "章节间缺少过渡词" in issue.description:
            # 在章节开头添加过渡词
            location = issue.location.strip("'")

            # 找到该章节的位置
            pattern = rf'\n##\s+{re.escape(location)}\n'
            match = re.search(pattern, text)

            if match:
                # 在章节标题后添加过渡段落
                insert_pos = match.end()
                text = text[:insert_pos] + "\n*继续前文讨论...*\n" + text[insert_pos:]

        return text

    def _fix_terminology_issue(self, text: str, issue: CoherenceIssue) -> str:
        """修复术语问题"""
        # 从description中提取术语
        match = re.search(r"'(.+?)'\s+和\s+'(.+?)'", issue.description)
        if match:
            old_term = match.group(2)
            new_term = match.group(1)

            # 替换（大小写不敏感）
            pattern = re.compile(re.escape(old_term), re.IGNORECASE)
            text = pattern.sub(new_term, text)

        return text

    def generate_revision_notes(self, report: CoherenceReport) -> str:
        """生成修订注释（供人工审核）"""
        if report.passed:
            return "论文一致性检查通过，无需修订。"

        notes = ["# 论文修订建议\n"]

        for issue in report.issues:
            if issue.severity == "critical":
                notes.append(f"\n## 🔴 严重问题 [{issue.issue_type}]\n")
            elif issue.severity == "major":
                notes.append(f"\n## 🟡 重要问题 [{issue.issue_type}]\n")
            else:
                notes.append(f"\n## 🟢 轻微问题 [{issue.issue_type}]\n")

            notes.append(f"**位置**: {issue.location}")
            notes.append(f"**描述**: {issue.description}")
            notes.append(f"**建议**: {issue.suggestion}")

            if issue.original_text:
                notes.append(f"**原文**: {issue.original_text}")

            if issue.recommended_fix:
                notes.append(f"**推荐修改**: {issue.recommended_fix}")

        notes.append(f"\n\n---\n**总体评分**: {report.overall_score:.2f}")
        notes.append(f"**逻辑流评分**: {report.logical_flow_score:.2f}")
        notes.append(f"**结构评分**: {report.structural_score:.2f}")

        return "\n".join(notes)


# 便捷函数
async def check_coherence(
    draft: str,
    outline: Dict[str, Any],
    references: List[str]
) -> CoherenceReport:
    """检查论文一致性"""
    checker = LogicCoherenceChecker()
    return await checker.check_draft(draft, outline, references)


async def revise_and_check(
    draft: str,
    outline: Dict[str, Any],
    references: List[str]
) -> Tuple[str, CoherenceReport]:
    """修订并检查论文"""
    manager = SelfReviseManager()
    return await manager.revise_draft(draft, outline, references)