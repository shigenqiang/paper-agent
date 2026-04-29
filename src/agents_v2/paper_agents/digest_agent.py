"""
DigestReportAgent - 学术资讯快报Agent

职责：
1. 日报：快速抓取今日最新论文，简洁摘要
2. 周报：按研究主题聚类，分析一周趋势
3. 月报：深度综合分析，前沿展望

支持多种报告类型的差异化生成策略。
"""
from typing import Any, Dict, List, Optional
import logging
import json
from datetime import datetime, timedelta

from .base_paper_agent import PaperAgentBase, AgentOutput, LLMConfig

logger = logging.getLogger(__name__)


class DigestReportAgent(PaperAgentBase):
    """
    DigestReportAgent - 学术资讯快报生成Agent

    支持生成日报、周报、月报三种类型，每种类型有不同的策略：

    日报 (daily):
    - 聚焦今日/最近24小时最新论文
    - 论文数量：10-20篇
    - 报告长度：500-800字
    - 结构：今日热点 + 代表性论文

    周报 (weekly):
    - 覆盖一周内的重要论文
    - 论文数量：20-40篇
    - 报告长度：1000-1500字
    - 结构：本周概览 + 主题聚类 + 趋势分析

    月报 (monthly):
    - 全月综合分析
    - 论文数量：40-60篇
    - 报告长度：2000-3000字
    - 结构：月度概览 + 主题深度分析 + 前沿展望 + 重点论文解读
    """

    # 各类型报告的配置
    REPORT_CONFIGS = {
        "daily": {
            "name": "每日学术资讯",
            "paper_limit": 20,
            "report_length": "约500-800字",
            "focus": "最新突破、重要进展",
            "structure": ["今日热点", "代表性论文", "快速点评"]
        },
        "weekly": {
            "name": "每周学术资讯",
            "paper_limit": 40,
            "report_length": "约1000-1500字",
            "focus": "研究趋势、主题分布、进展对比",
            "structure": ["本周概览", "主题聚类", "趋势分析", "重点论文"]
        },
        "monthly": {
            "name": "每月学术资讯",
            "paper_limit": 60,
            "report_length": "约2000-3000字",
            "focus": "深度分析、前沿展望、方法论创新",
            "structure": ["月度概览", "主题深度分析", "前沿展望", "重点论文解读", "未来方向"]
        }
    }

    def __init__(self, llm_config: Optional[LLMConfig] = None):
        system_prompt = """你是一位资深学术资讯分析师，专注于为研究人员提供精准、高质量的学术动态分析。

你的核心能力：
1. 从海量学术论文中识别最重要的研究进展
2. 按研究主题/方向进行分类和聚类
3. 综合分析多篇论文，发现关联和趋势
4. 评估研究的影响力和潜在价值
5. 撰写专业、易懂的学术分析报告

报告风格：
- 语言专业但不过于晦涩
- 引用规范：[论文编号] 格式
- 分析有理有据，避免空泛
- 适当保留英文专业术语"""

        super().__init__(
            name="digest_report_agent",
            llm_config=llm_config,
            description="学术资讯快报生成",
            system_prompt=system_prompt
        )

    async def execute(
        self,
        input_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AgentOutput:
        """
        执行学术资讯报告生成

        Args:
            input_data: {
                papers: List[Dict],  # 论文列表
                keywords: List[str],  # 监测关键词
                digest_type: str,     # daily/weekly/monthly
                date_range: str,      # 日期范围描述
                sources: List[str]     # 数据来源
            }
            context: 执行上下文
        """
        papers = input_data.get("papers", [])
        keywords = input_data.get("keywords", [])
        digest_type = input_data.get("digest_type", "daily")
        date_range = input_data.get("date_range", "")
        sources = input_data.get("sources", [])

        if not papers:
            return AgentOutput(
                success=True,
                result={"report": "# 本期暂无相关论文\n\n请稍后重试或调整关键词。", "theme_groups": {}, "paper_count": 0},
                agent_name=self.name,
                reasoning="无论文数据",
                quality_score=0.0
            )

        config = self.REPORT_CONFIGS.get(digest_type, self.REPORT_CONFIGS["daily"])

        try:
            # 1. 预处理论文数据
            processed_papers = self._preprocess_papers(papers, config["paper_limit"])

            # 2. 按研究主题聚类
            theme_groups = self._cluster_papers(processed_papers)

            # 3. 排序论文（按引用/重要性）
            sorted_papers = self._rank_papers(processed_papers)

            # 4. 生成报告
            if digest_type == "daily":
                report = await self._generate_daily_report(sorted_papers, theme_groups, keywords, date_range, config)
            elif digest_type == "weekly":
                report = await self._generate_weekly_report(sorted_papers, theme_groups, keywords, date_range, config)
            else:  # monthly
                report = await self._generate_monthly_report(sorted_papers, theme_groups, keywords, date_range, config)

            # 5. 添加参考文献
            references = self._format_references(sorted_papers)
            final_report = report + "\n\n## 参考文献\n\n" + references

            return AgentOutput(
                success=True,
                result={
                    "report": final_report,
                    "theme_groups": {k: [{"title": p["title"], "citation_index": p.get("citation_index")} for p in v] for k, v in theme_groups.items()},
                    "paper_count": len(sorted_papers),
                    "themes": list(theme_groups.keys()),
                    "report_type": digest_type
                },
                agent_name=self.name,
                reasoning=f"生成了{digest_type}学术资讯报告，包含{len(sorted_papers)}篇论文，{len(theme_groups)}个主题",
                quality_score=0.85
            )

        except Exception as e:
            logger.error(f"DigestReportAgent execution failed: {e}")
            return AgentOutput(
                success=False,
                result=None,
                agent_name=self.name,
                error=str(e)
            )

    def _preprocess_papers(self, papers: List[Dict], limit: int) -> List[Dict]:
        """预处理论文数据"""
        # 去重
        seen = set()
        unique_papers = []
        for p in papers:
            pid = p.get("paper_id") or p.get("id")
            if pid and pid not in seen:
                seen.add(pid)
                unique_papers.append(p)

        # 限制数量
        return unique_papers[:limit]

    def _cluster_papers(self, papers: List[Dict]) -> Dict[str, List[Dict]]:
        """将论文按研究主题聚类"""
        theme_groups: Dict[str, List[Dict]] = {}

        theme_keywords = {
            "大语言模型 (LLM)": [
                "large language model", "llm", "chatgpt", "gpt-", "claude", "gemini",
                "language model", "text generation", "instruction following", "chain-of-thought"
            ],
            "深度学习与神经网络": [
                "deep learning", "neural network", "transformer", "attention mechanism",
                "convolutional", "residual", "backpropagation", "optimizer"
            ],
            "计算机视觉": [
                "image", "vision", "object detection", "segmentation", "classification",
                "visual", "image generation", "diffusion", "stable diffusion", "dall-e"
            ],
            "自然语言处理": [
                "natural language processing", "nlp", "sentiment", "text classification",
                "named entity recognition", "machine translation", "text mining"
            ],
            "强化学习与决策": [
                "reinforcement learning", "policy gradient", "q-learning", "reward",
                "agent", "environment", "multi-agent", "game"
            ],
            "图神经网络": [
                "graph neural network", "gcn", "gat", "graph attention",
                "knowledge graph", "network embedding", "node classification"
            ],
            "联邦学习与隐私计算": [
                "federated learning", "privacy-preserving", "distributed learning",
                "secure aggregation", "differential privacy", "model compression"
            ],
            "医学AI与生物信息学": [
                "medical ai", "clinical", "diagnosis", "biomarker", "genomic",
                "protein", "drug discovery", "medical imaging", "healthcare"
            ],
            "优化方法与训练技术": [
                "optimization", "gradient descent", "convergence", "training dynamics",
                "loss landscape", "generalization", "regularization"
            ],
            "可解释性与可信AI": [
                "explainable ai", "interpretability", "fairness", "bias",
                "transparency", "trustworthy ai", "accountability"
            ],
            "机器人与具身智能": [
                "robotics", "embodied ai", "manipulation", "navigation",
                "autonomous", "humanoid", "sensorimotor"
            ],
            "AI安全与对齐": [
                "ai safety", "alignment", "rlhf", "constitutional ai",
                "value alignment", "robustness", "adversarial"
            ]
        }

        for paper in papers:
            text = (paper.get('abstract', '') + ' ' + paper.get('title', '')).lower()
            matched_theme = None

            for theme, keywords in theme_keywords.items():
                for kw in keywords:
                    if kw.lower() in text:
                        matched_theme = theme
                        break
                if matched_theme:
                    break

            if not matched_theme:
                matched_theme = "其他研究"

            if matched_theme not in theme_groups:
                theme_groups[matched_theme] = []
            theme_groups[matched_theme].append(paper)

        return theme_groups

    def _rank_papers(self, papers: List[Dict]) -> List[Dict]:
        """对论文进行排序"""
        # 计算重要性分数
        for paper in papers:
            citations = paper.get('citations', 0) or 0
            # 简单评分：引用 + 新鲜度
            score = citations * 0.7  # 简化处理
            paper['_importance_score'] = score

        # 按重要性排序
        return sorted(papers, key=lambda x: x.get('_importance_score', 0), reverse=True)

    async def _generate_daily_report(
        self,
        papers: List[Dict],
        theme_groups: Dict[str, List[Dict]],
        keywords: List[str],
        date_range: str,
        config: Dict
    ) -> str:
        """生成日报"""
        # 取最重要5篇论文
        top_papers = papers[:5]

        # 构建论文摘要
        papers_text = ""
        for i, paper in enumerate(top_papers, 1):
            paper['citation_index'] = i
            title = paper.get('title', '未知')
            authors = ', '.join(paper.get('authors', [])[:2])
            if len(paper.get('authors', [])) > 2:
                authors += ' 等'
            abstract = paper.get('abstract', '')
            if abstract and len(abstract) > 300:
                abstract = abstract[:300] + "..."
            papers_text += f"[{i}] {title}\n作者: {authors}\n摘要: {abstract}\n\n"

        kw_str = '、'.join(keywords) if keywords else 'AI/ML'

        prompt = f"""请为以下今日最新论文撰写一篇**简短精炼**的学术资讯日报。

## 要求
1. **简短精炼**：约500-800字
2. **今日热点**：识别1-3个最重要的发现/突破
3. **代表性论文**：简要点评最重要的5篇论文
4. **格式**：用 [1]、[2] 等引用论文
5. 直接输出Markdown，不要标题和参考文献列表

## 监测领域
{kw_str}

## 今日重点论文
{papers_text}

## 主题分布
{', '.join(list(theme_groups.keys())[:5])}

请直接输出报告正文："""

        try:
            content = await self._llm_call(prompt)
            title = f"# 📅 每日学术资讯\n**日期**: {date_range} | **监测**: {kw_str} | **收录**: {len(papers)}篇\n\n"
            return title + content
        except Exception as e:
            logger.error(f"Daily report LLM call failed: {e}")
            return self._generate_fallback_report(papers, theme_groups, keywords, "daily", date_range, config)

    async def _generate_weekly_report(
        self,
        papers: List[Dict],
        theme_groups: Dict[str, List[Dict]],
        keywords: List[str],
        date_range: str,
        config: Dict
    ) -> str:
        """生成周报"""
        top_papers = papers[:10]
        for i, paper in enumerate(top_papers, 1):
            paper['citation_index'] = i

        # 按主题组织
        themes_text = ""
        for theme, theme_papers in sorted(theme_groups.items(), key=lambda x: len(x[1]), reverse=True)[:6]:
            themes_text += f"\n### {theme}（{len(theme_papers)}篇）\n"
            for p in theme_papers[:2]:
                idx = p.get('citation_index', 0)
                title = p.get('title', '未知')[:80]
                themes_text += f"- [{title}...] [{idx}]\n"

        papers_text = ""
        for paper in top_papers:
            idx = paper.get('citation_index', 0)
            title = paper.get('title', '未知')
            authors = ', '.join(paper.get('authors', [])[:2])
            if len(paper.get('authors', [])) > 2:
                authors += ' 等'
            abstract = paper.get('abstract', '')
            if abstract and len(abstract) > 200:
                abstract = abstract[:200] + "..."
            papers_text += f"[{idx}] {title}\n作者: {authors}\n摘要: {abstract}\n\n"

        kw_str = '、'.join(keywords) if keywords else 'AI/ML'

        prompt = f"""请为以下本周论文撰写一篇**综合性学术资讯周报**。

## 要求
1. **结构清晰**：本周概览 + 主题分析 + 重点论文 + 趋势观察
2. **报告长度**：约1000-1500字
3. **主题聚类**：按研究主题分组分析
4. **趋势观察**：指出本周研究趋势
5. 用 [1]、[2] 等引用论文
6. 直接输出Markdown，不要参考文献列表

## 监测领域
{kw_str}

## 论文列表（按重要性排序）
{papers_text}

## 主题分布
{themes_text}

请直接输出报告正文："""

        try:
            content = await self._llm_call(prompt)
            title = f"# 📰 每周学术资讯\n**周期**: {date_range} | **监测**: {kw_str} | **收录**: {len(papers)}篇\n\n"
            return title + content
        except Exception as e:
            logger.error(f"Weekly report LLM call failed: {e}")
            return self._generate_fallback_report(papers, theme_groups, keywords, "weekly", date_range, config)

    async def _generate_monthly_report(
        self,
        papers: List[Dict],
        theme_groups: Dict[str, List[Dict]],
        keywords: List[str],
        date_range: str,
        config: Dict
    ) -> str:
        """生成月报"""
        top_papers = papers[:15]
        for i, paper in enumerate(top_papers, 1):
            paper['citation_index'] = i

        # 按主题组织（深度分析）
        themes_text = ""
        for theme, theme_papers in sorted(theme_groups.items(), key=lambda x: len(x[1]), reverse=True)[:8]:
            themes_text += f"\n### {theme}（{len(theme_papers)}篇）\n"
            for p in theme_papers[:3]:
                idx = p.get('citation_index', 0)
                title = p.get('title', '未知')[:80]
                abstract = p.get('abstract', '')[:150]
                themes_text += f"- **[{title}]** [{idx}]\n  > {abstract}...\n"

        papers_text = ""
        for paper in top_papers:
            idx = paper.get('citation_index', 0)
            title = paper.get('title', '未知')
            authors = ', '.join(paper.get('authors', [])[:3])
            if len(paper.get('authors', [])) > 3:
                authors += ' 等'
            abstract = paper.get('abstract', '')
            if abstract and len(abstract) > 250:
                abstract = abstract[:250] + "..."
            venue = paper.get('venue', '') or paper.get('journal', '')
            year = paper.get('year', '')
            papers_text += f"[{idx}] {title}\n作者: {authors} | 来源: {venue}, {year}\n摘要: {abstract}\n\n"

        kw_str = '、'.join(keywords) if keywords else 'AI/ML'

        prompt = f"""请为以下本月论文撰写一篇**深度综合性学术资讯月报**。

## 要求
1. **深度分析**：不是简单罗列，而是融会贯通的综合分析
2. **结构完整**：月度概览 + 主题深度分析 + 前沿展望 + 重点论文解读
3. **报告长度**：约2000-3000字
4. **方法论视角**：关注方法创新和技术突破
5. **未来展望**：基于本月趋势预测下月可能的研究方向
6. 用 [1]、[2] 等引用论文
7. 直接输出Markdown，不要参考文献列表

## 监测领域
{kw_str}

## 论文列表（按重要性排序）
{papers_text}

## 主题深度分析
{themes_text}

请直接输出报告正文："""

        try:
            content = await self._llm_call(prompt)
            title = f"# 📊 每月学术资讯\n**月份**: {date_range} | **监测**: {kw_str} | **收录**: {len(papers)}篇 | **主题**: {len(theme_groups)}个\n\n"
            return title + content
        except Exception as e:
            logger.error(f"Monthly report LLM call failed: {e}")
            return self._generate_fallback_report(papers, theme_groups, keywords, "monthly", date_range, config)

    def _generate_fallback_report(
        self,
        papers: List[Dict],
        theme_groups: Dict[str, List[Dict]],
        keywords: List[str],
        digest_type: str,
        date_range: str,
        config: Dict
    ) -> str:
        """模板方式生成报告（LLM失败时的备选）"""
        type_names = {"daily": "每日", "weekly": "每周", "monthly": "每月"}
        type_name = type_names.get(digest_type, "本期")
        kw_str = '、'.join(keywords) if keywords else 'AI/ML'

        report = f"# {type_name}学术资讯\n**时间**: {date_range} | **监测**: {kw_str} | **收录**: {len(papers)}篇\n\n"

        report += f"## 📋 概述\n\n本期共收录 {len(papers)} 篇相关论文，涵盖 {len(theme_groups)} 个研究方向。\n\n"

        report += "## 📚 主题分布\n\n"
        for theme, theme_papers in sorted(theme_groups.items(), key=lambda x: len(x[1]), reverse=True):
            report += f"- **{theme}**：{len(theme_papers)} 篇\n"
        report += "\n"

        report += "## 📄 重点论文\n\n"
        for i, paper in enumerate(papers[:10], 1):
            paper['citation_index'] = i
            title = paper.get('title', '未知')[:60]
            authors = ', '.join(paper.get('authors', [])[:2])
            report += f"[{i}] **{title}**... - {authors}\n"

        return report

    def _format_references(self, papers: List[Dict]) -> str:
        """格式化参考文献列表"""
        if not papers:
            return "（暂无参考文献）"

        refs = []
        for paper in papers:
            idx = paper.get("citation_index", 0)
            if not idx:
                continue

            authors = paper.get('authors', [])
            if isinstance(authors, list):
                authors = ', '.join(authors[:3])
                if len(paper.get('authors', [])) > 3:
                    authors += ' et al.'
            else:
                authors = str(authors)

            title = paper.get('title', '未知标题')
            year = paper.get('year', 'n.d.')
            venue = paper.get('venue', '') or paper.get('journal', '')
            url = paper.get('url', '')
            sources = paper.get('sources', [])
            source = sources[0] if sources else '学术数据库'

            ref = f"[{idx}] {authors}. \"{title}\". {venue}"
            if year:
                ref += f", {year}"
            if source:
                ref += f". {source}"
            if url:
                ref += f"\n   URL: {url}"

            refs.append(ref)

        return '\n\n'.join(refs)
