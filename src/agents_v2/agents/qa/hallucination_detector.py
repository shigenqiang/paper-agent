"""
幻觉检测器 - Hallucination Detector

基于 SelfCheckGPT 的幻觉检测方法。
通过多次采样评估答案中每个声明的一致性。
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from src.agents_v2.logging_config import get_logging_logger

import asyncio
import re

logger = get_logging_logger(__name__)


@dataclass
class StatementCheck:
    """声明检查结果"""
    text: str
    consistency: float  # 一致性分数 (0-1)
    hallucination_score: float  # 幻觉分数 (0-1)
    is_suspicious: bool  # 是否可疑
    support_count: int = 0  # 支持的采样数
    total_samples: int = 0  # 总采样数


@dataclass
class HallucinationReport:
    """幻觉检测报告"""
    overall_score: float  # 总体幻觉分数 (0-1)
    statements: List[StatementCheck]  # 各声明检查结果
    suspicious_count: int  # 可疑声明数量
    total_statements: int  # 总声明数量
    risk_level: str  # "low", "medium", "high"
    sampled_answers: List[str] = field(default_factory=list)


class HallucinationDetector:
    """幻觉检测器

    使用 SelfCheckGPT 方法：
    1. 多次采样生成同一问题的不同答案
    2. 提取待检测答案中的声明
    3. 检查每个声明在其他采样答案中的出现频率
    4. 计算一致性分数，识别可能的幻觉
    """

    def __init__(
        self,
        llm: Optional[Any] = None,
        num_samples: int = 5,
        suspicious_threshold: float = 0.5,
        consistency_threshold: float = 0.7,
    ):
        """初始化幻觉检测器

        Args:
            llm: LLM 实例
            num_samples: 采样次数
            suspicious_threshold: 可疑阈值
            consistency_threshold: 一致性阈值
        """
        self.llm = llm
        self.num_samples = num_samples
        self.suspicious_threshold = suspicious_threshold
        self.consistency_threshold = consistency_threshold

    async def detect(
        self,
        question: str,
        answer: str,
    ) -> HallucinationReport:
        """检测答案中的幻觉

        Args:
            question: 用户问题
            answer: 待检测的答案

        Returns:
            HallucinationReport: 幻觉检测报告
        """
        if not self.llm:
            return self._simple_detection(answer)

        # 1. 多次采样
        sampled_answers = await self._multiple_sampling(question)

        # 2. 提取声明
        statements = await self._extract_statements(answer)

        if not statements:
            return HallucinationReport(
                overall_score=0.0,
                statements=[],
                suspicious_count=0,
                total_statements=0,
                risk_level="low",
                sampled_answers=sampled_answers,
            )

        # 3. 一致性检查
        statement_checks = []
        for stmt in statements:
            check = await self._check_statement_consistency(
                stmt, sampled_answers, answer
            )
            statement_checks.append(check)

        # 4. 计算总体分数
        hallucination_scores = [s.hallucination_score for s in statement_checks]
        overall_score = sum(hallucination_scores) / len(hallucination_scores) if hallucination_scores else 0.0

        suspicious_count = sum(1 for s in statement_checks if s.is_suspicious)

        # 5. 风险等级
        if overall_score < 0.3:
            risk_level = "low"
        elif overall_score < 0.6:
            risk_level = "medium"
        else:
            risk_level = "high"

        return HallucinationReport(
            overall_score=overall_score,
            statements=statement_checks,
            suspicious_count=suspicious_count,
            total_statements=len(statements),
            risk_level=risk_level,
            sampled_answers=sampled_answers,
        )

    async def _multiple_sampling(self, question: str) -> List[str]:
        """多次采样生成不同答案

        Args:
            question: 用户问题

        Returns:
            List[str]: 采样答案列表
        """
        samples = []

        prompt = f"""问题: {question}

请直接回答，生成一个完整的答案。"""

        for i in range(self.num_samples):
            try:
                answer = await self._call_llm(prompt)
                samples.append(answer)
            except Exception as e:
                logger.error(f"Sampling {i+1} failed: {e}")

        return samples

    async def _check_statement_consistency(
        self,
        statement: str,
        sampled_answers: List[str],
        original_answer: str,
    ) -> StatementCheck:
        """检查声明的一致性

        Args:
            statement: 待检测的声明
            sampled_answers: 采样答案列表
            original_answer: 原始答案（用于对比）

        Returns:
            StatementCheck: 检查结果
        """
        # 计算有多少采样答案支持这个声明
        support_count = 0
        total = len(sampled_answers) if sampled_answers else 1

        for sample in sampled_answers:
            if self._stmt_in_answer(statement, sample):
                support_count += 1

        # 计算一致性分数
        consistency = support_count / total if total > 0 else 0.0
        hallucination_score = 1.0 - consistency

        return StatementCheck(
            text=statement,
            consistency=consistency,
            hallucination_score=hallucination_score,
            is_suspicious=consistency < self.suspicious_threshold,
            support_count=support_count,
            total_samples=total,
        )

    def _stmt_in_answer(self, stmt: str, answer: str) -> bool:
        """检查声明是否在答案中出现

        使用简单的词重叠方法。
        更精确的方法可以使用 embedding 相似度。
        """
        # 提取关键术语
        stmt_terms = self._extract_key_terms(stmt)
        answer_terms = self._extract_key_terms(answer)

        if not stmt_terms:
            return True  # 空声明默认支持

        # 计算重叠度
        overlap = len(stmt_terms & answer_terms)
        overlap_ratio = overlap / len(stmt_terms)

        return overlap_ratio >= 0.7

    def _extract_key_terms(self, text: str) -> set:
        """提取关键术语

        过滤停用词，提取有意义的术语。
        """
        # 停用词列表
        stopwords = {
            "的", "了", "是", "在", "有", "和", "与", "为", "与", "或",
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "这", "那", "个", "等", "也", "就", "都", "而", "及", "以",
        }

        # 提取词（中文和英文）
        chinese = set(re.findall(r"[一-鿿]+", text))
        english = set(re.findall(r"[a-zA-Z]+", text))

        # 过滤停用词
        chinese = {w for w in chinese if w not in stopwords and len(w) > 1}
        english = {w.lower() for w in english if w.lower() not in stopwords and len(w) > 2}

        return chinese | english

    async def _extract_statements(self, text: str) -> List[str]:
        """从文本中提取可验证的事实声明

        Args:
            text: 文本

        Returns:
            List[str]: 声明列表
        """
        if not self.llm:
            return self._simple_extract_statements(text)

        prompt = f"""从以下文本中提取所有可验证的事实声明。
每个声明应该是一个完整的陈述句，可以被判断真伪。
只输出声明，不要解释。

文本: {text}

声明列表（每行一个）："""

        try:
            response = await self._call_llm(prompt)
            statements = self._parse_statements(response)
            return statements
        except Exception as e:
            logger.error(f"Statement extraction failed: {e}")
            return self._simple_extract_statements(text)

    def _simple_extract_statements(self, text: str) -> List[str]:
        """简单的声明提取

        无 LLM 时按句子分割。
        """
        # 按句子分割
        sentence_endings = r'[。！？.!?]+'
        sentences = re.split(sentence_endings, text)

        # 过滤太短或太长的句子
        statements = []
        for s in sentences:
            s = s.strip()
            if len(s) > 10 and len(s) < 500:
                statements.append(s)

        return statements if statements else [text[:500]]

    def _parse_statements(self, response: str) -> List[str]:
        """解析声明列表"""
        lines = response.strip().split("\n")
        statements = []

        for line in lines:
            line = line.strip()
            # 匹配数字列表或横线列表
            if line and (line[0].isdigit() or line[0] in "-●◆"):
                content = line.split(".", 1)[-1] if "." in line else line
                content = content.split("-", 1)[-1] if "-" in line else content
                content = content.strip()
                if content and len(content) > 5:
                    statements.append(content)

        return statements if statements else [response.strip()]

    async def _call_llm(self, prompt: str) -> str:
        """调用 LLM"""
        try:
            if hasattr(self.llm, 'agenerate'):
                result = await self.llm.agenerate([prompt])
                return result.generations[0][0].text.strip()
            elif hasattr(self.llm, 'generate'):
                result = self.llm.generate([prompt])
                return result.generations[0][0].text.strip()
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise

    def _simple_detection(self, answer: str) -> HallucinationReport:
        """简单的幻觉检测

        无 LLM 时的降级方案。
        """
        statements = self._simple_extract_statements(answer)

        # 简单地认为所有声明都是可疑的
        statement_checks = [
            StatementCheck(
                text=stmt,
                consistency=0.5,  # 假设一致性为 0.5
                hallucination_score=0.5,
                is_suspicious=False,  # 无法判断，保持乐观
                support_count=0,
                total_samples=0,
            )
            for stmt in statements
        ]

        return HallucinationReport(
            overall_score=0.5,
            statements=statement_checks,
            suspicious_count=0,
            total_statements=len(statements),
            risk_level="medium",
            sampled_answers=[],
        )

    def format_report(self, report: HallucinationReport) -> str:
        """格式化检测报告

        Args:
            report: 检测报告

        Returns:
            str: 格式化的报告文本
        """
        lines = [
            "=== 幻觉检测报告 ===",
            f"总体幻觉分数: {report.overall_score:.2f}",
            f"风险等级: {report.risk_level.upper()}",
            f"声明总数: {report.total_statements}",
            f"可疑声明: {report.suspicious_count}",
            "",
            "--- 详细检查 ---",
        ]

        for i, stmt_check in enumerate(report.statements, 1):
            risk_tag = "⚠️" if stmt_check.is_suspicious else "✓"
            lines.append(
                f"{i}. {risk_tag} {stmt_check.text[:60]}..."
                if len(stmt_check.text) > 60 else
                f"{i}. {risk_tag} {stmt_check.text}"
            )
            lines.append(f"   一致性: {stmt_check.consistency:.2f}, 幻觉分数: {stmt_check.hallucination_score:.2f}")

        return "\n".join(lines)


# 便捷函数
async def detect_hallucination(
    question: str,
    answer: str,
    llm: Optional[Any] = None,
    **kwargs
) -> HallucinationReport:
    """幻觉检测的便捷函数"""
    detector = HallucinationDetector(llm=llm, **kwargs)
    return await detector.detect(question, answer)


def format_hallucination_report(report: HallucinationReport) -> str:
    """格式化检测报告的便捷函数"""
    detector = HallucinationDetector()
    return detector.format_report(report)