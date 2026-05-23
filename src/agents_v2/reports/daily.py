"""
日报生成器 - Daily Report Generator

功能：
1. 生成每日研究进展报告
2. 收集当日重要论文和发现
3. 结构化输出（摘要、亮点、详情）
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from .base import BaseReportGenerator, ReportConfig, ReportSection, ReportType, Report
from ..routing import SemanticKeywordExpander

from ..logging_config import get_logging_logger

logger = get_logging_logger(__name__)


class DailyReportGenerator(BaseReportGenerator):
    """
    日报生成器

    生成结构：
    1. 今日摘要
    2. 重要发现
    3. 详细分析
    4. 明日展望
    """

    def __init__(self, config: Optional[ReportConfig] = None):
        if config is None:
            config = ReportConfig.from_env(overrides={"report_type": ReportType.DAILY})
        super().__init__(config)

        self.system_prompt = """你是一个专业的日报生成助手。根据今日的研究信息，生成结构化的日报。
格式要求：
1. 今日摘要（100字内）
2. 重要发现（3-5条）
3. 详细分析
4. 明日展望

语言：中文
风格：专业、简洁
"""

    async def generate(
        self,
        topic: str = "",
        papers: Optional[List[Dict[str, Any]]] = None,
        search_results: Optional[List[Dict[str, Any]]] = None,
        date: Optional[str] = None,
        min_relevance: float = 0.0,
        keywords: Optional[List[str]] = None,
        auto_search: bool = False,
        max_search_results: int = 30,
        **kwargs
    ) -> Report:
        """
        生成日报（文献综述风格）

        Args:
            topic: 研究主题（可从环境变量 DEFAULT_REPORT_TOPIC 读取）
            papers: 今日收集的论文列表
            search_results: 搜索结果
            date: 日期（默认今天）
            min_relevance: 最小相关性阈值（0.0-1.0），默认0.0
            keywords: 关键词列表，用于过滤与主题语义相关的论文
            auto_search: 是否自动搜索论文（默认False，如果papers为空且auto_search=True则自动搜索）
            max_search_results: 自动搜索时的最大结果数

        Returns:
            Report 对象
        """
        import os
        # 如果 topic 为空，尝试从环境变量读取
        if not topic:
            topic = os.getenv("DEFAULT_REPORT_TOPIC", "")
        if not topic:
            topic = os.getenv("REPORT_TOPIC", "")

        date = date or datetime.now().strftime("%Y-%m-%d")

        logger.info(f"Generating daily report (literature review style) for {date}, topic: {topic}")

        # 自动搜索论文（当papers为空且auto_search=True时）
        if not papers and auto_search and topic:
            logger.info(f"Auto-searching papers for topic: {topic}")
            try:
                from ..paper_search.paper_search import PaperSearchAgent
                search_agent = PaperSearchAgent()
                result = await search_agent.execute(
                    query=topic,
                    context={'source': 'all', 'max_results': max_search_results, 'time_range': 365}
                )
                papers = result.get('papers', [])
                logger.info(f"Auto-search found {len(papers)} papers")
            except Exception as e:
                logger.error(f"Auto-search failed: {e}")
                papers = []

        # 过滤低相关性论文
        if papers and min_relevance > 0:
            original_count = len(papers)
            papers = [p for p in papers if p.get('relevance', 1.0) >= min_relevance]
            logger.info(f"Filtered {original_count - len(papers)} papers below relevance threshold {min_relevance}")

        # 过滤论文日期（只保留year < 报告年份的论文，同年论文因无法确认月份需排除）
        if papers and date:
            report_year = int(date.split('-')[0]) if date else datetime.now().year
            original_count = len(papers)
            papers = [p for p in papers if int(p.get('year', 0)) < report_year]
            logger.info(f"Filtered {original_count - len(papers)} papers with year >= {report_year}")

        # 基于关键词和语义相关性过滤论文
        if papers and keywords:
            original_count = len(papers)
            papers = self._filter_by_keywords_and_semantics(papers, topic, keywords)
            logger.info(f"Filtered {original_count - len(papers)} papers by keywords/semantics")

        # 构建prompt - 文献综述风格
        prompt = self._build_prompt(topic, papers, search_results, date)

        # 调用LLM生成
        raw_content = await self._call_llm(prompt)

        # 生成报告名称（基于总结）
        report_title = self._generate_title(topic, papers, raw_content, date)

        # 创建报告
        report = Report(
            title=report_title,
            config=self.config,
            raw_content=raw_content
        )

        # 添加文献综述风格的默认章节
        report.add_section(self._create_section("今日摘要", level=1))
        report.add_section(self._create_section("一、研究背景", level=1))
        report.add_section(self._create_section("二、核心论文分析", level=1))
        report.add_section(self._create_section("三、主要研究发现", level=1))
        report.add_section(self._create_section("四、技术方法对比", level=1))
        report.add_section(self._create_section("五、结论与展望", level=1))
        report.add_section(self._create_section("六、今日总结", level=1))

        # 解析内容填充章节
        sections = self.parse_raw_to_sections(raw_content)
        if sections:
            report.sections = sections[:self.config.max_sections]

        # 设置元数据
        report.metadata = {
            "date": date,
            "topic": topic,
            "papers_count": len(papers) if papers else 0,
            "search_count": len(search_results) if search_results else 0,
            "style": "literature_review",
        }

        # 添加参考文献（使用过滤后的论文）
        if self.config.include_references and papers:
            report.references = self._format_references(papers)

        return report

    def _build_prompt(
        self,
        topic: str,
        papers: Optional[List[Dict]],
        search_results: Optional[List[Dict]],
        date: str
    ) -> str:
        """构建文献综述风格的prompt（遵循Agent提示词工程指南五部分结构）"""

        # 构建带年份的论文列表（用于正文引用）
        paper_refs = ""
        if papers:
            for i, p in enumerate(papers[:20]):
                title = p.get('title', 'N/A')[:40]
                year = p.get('year', 'n.d.')
                authors = p.get('authors', [])
                if isinstance(authors, list) and authors:
                    author_str = authors[0].split()[-1] if authors else 'Unknown'
                else:
                    author_str = 'Unknown'
                paper_refs += f"[{i+1}] {author_str} ({year}): {title}\n"

        # 从日期中提取年份用于约束
        report_year = int(date.split('-')[0]) if date else datetime.now().year

        prompt = f"""你是一位专业学术研究员。请撰写关于"{topic}"的文献综述日报，包含以下结构。

## 今日摘要（约200字）

请先撰写一段今日摘要，必须使用"## 今日摘要"作为标题。摘要应该：
- 介绍今日分析的论文类型（如：主成分分析方法论文、深度学习应用论文、统计推断论文等）
- 概括这些论文的核心主题和主要贡献
- 用1-2句话总结对实践的指导意义

格式：
## 今日摘要
[摘要内容，简洁段落，不使用列表，让读者通过摘要就能知道今日关注了哪些类型的论文]

## 六章正文

重要规则：
1. 直接输出学术报告正文，不要包含任何思考过程、规划说明、结构框架
2. 不要使用[think]、[judge]、[analyze]等标签
3. 章节标题格式必须为"## 一、研究背景"、"## 二、核心论文分析"等，使用##而非###
4. 章节编号必须连续：一、二、三、四、五、六，不要跳过任何编号
5. 不要写"让我按照结构来撰写"、"首先"、"其次"、"最后"等引导语
6. 论文的年份必须 <= {report_year}，严禁引用{report_year}年之后发表的论文
7. **正文必须引用论文**：使用[1][2][3]格式在正文中引用相关论文，每段至少引用1-2篇论文

参考论文列表：
{paper_refs}

## 一、研究背景

请阐述{topic}的研究背景、重要性、主要方法和当前挑战。结合论文[1][2]等说明该领域的发展脉络和现状。

## 二、核心论文分析

请综合分析所有论文的重要发现和技术贡献，按主题分类阐述：
1. 最主要的研究方向是什么？有哪些代表性方法？
2. 各种方法的核心技术是什么？有什么优缺点？
3. 在实际应用中效果如何？有哪些具体案例？

必须引用论文支持分析，例如：[1]采用...方法取得了...效果，[3]在...任务上达到...准确率。分析要具体、有深度，不能空洞。

## 三、主要研究发现

请总结核心论文的共同发现和研究趋势。必须包含从"第一"到"第八"的完整八条发现，每条至少50字。每条发现要：
- 明确说明发现了什么
- 引用具体论文[1][2]等作为证据
- 说明这个发现的意义

## 四、技术方法对比

请对比不同论文的方法论。对比要具体：
- 方法A vs 方法B：各自优缺点、适用场景
- 用具体论文数据说明：比如[1]的方法比[2]的准确率高X%
- 不同方法在不同任务上的表现差异

## 五、结论与展望

请总结研究结论和未来研究方向。要有具体结论和具体方向，不能泛泛而谈。引用相关论文。

## 六、今日总结

请对今日{topic}领域的研究进展进行总结：
- 最重要的3个发现是什么？
- 最值得关注的新方法或新趋势？
- 对实际应用有什么指导意义？

每章内容至少200字，直接输出学术报告正文。正文必须包含论文引用。"""

        return prompt

    def _extract_noun_phrases(self, text: str) -> List[str]:
        """从文本中提取有意义的名词短语"""
        import re

        # 加载停用词表
        stopwords = self._load_stopwords()

        # 提取所有可能的中文词序列（3-7字）
        all_chunks = re.findall(r'[一-龥]{3,7}', text)

        # 过滤停用词和包含停用词的短语
        filtered = []
        for c in all_chunks:
            if c not in stopwords and not any(sw in c for sw in stopwords):
                filtered.append(c)

        # 统计频率
        from collections import Counter
        counts = Counter(filtered)

        # 获取高频短语（出现2次以上）
        frequent = [(phrase, count) for phrase, count in counts.most_common(300) if count >= 2]

        # 去重：优先保留更长的完整短语，移除被包含的短片段
        final_phrases = []
        for phrase, count in frequent:
            # 跳过被其他更高频短语包含的短语
            if any(phrase in longer and len(phrase) < len(longer) for longer, _ in frequent):
                continue
            # 跳过常见无意义开头
            skip_starts = ('的', '是', '在', '和', '了', '有', '一个', '这种', '可以', '进行')
            if any(phrase.startswith(s) for s in skip_starts):
                continue
            final_phrases.append(phrase)

        # 返回排序后的短语（优先返回更长的、有意义的）
        final_phrases.sort(key=lambda x: (-len(x), -counts[x]))

        # 取前10个，返回4字以上的完整短语
        result = [p for p in final_phrases[:20] if len(p) >= 4][:10]
        return result

    def _load_stopwords(self) -> set:
        """加载停用词表（优先使用下载的，停用则使用内置）"""
        import os
        import urllib.request

        # 停用词表路径
        stopwords_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "data", "stopwords", "cn_stopwords.txt"
        )

        # 如果文件不存在，尝试下载
        if not os.path.exists(stopwords_file):
            os.makedirs(os.path.dirname(stopwords_file), exist_ok=True)
            try:
                # 从 GitHub 下载中文停用词表
                url = "https://raw.githubusercontent.com/goto456/stopwords/master/baidu_stopwords.txt"
                urllib.request.urlretrieve(url, stopwords_file)
                logger.info(f"Downloaded stopwords to {stopwords_file}")
            except Exception as e:
                logger.warning(f"Failed to download stopwords: {e}")

        # 读取停用词表
        if os.path.exists(stopwords_file):
            try:
                with open(stopwords_file, 'r', encoding='utf-8') as f:
                    stopwords = set(line.strip() for line in f if line.strip())
                return stopwords
            except Exception as e:
                logger.warning(f"Failed to read stopwords file: {e}")

        # 内置基本停用词（备用）
        return set([
            '的', '是', '在', '和', '了', '有', '我', '你', '他', '她', '它',
            '这个', '那个', '这些', '那些', '一种', '一些', '可以', '能够',
            '通过', '因此', '但是', '然而', '由于', '对于', '关于', '以及',
            '发现', '方法', '研究', '数据', '分析', '进行', '使用',
            '问题', '情况', '过程', '结果', '影响', '方面',
            '提出', '表示', '认为', '显示', '表明', '基于', '利用', '采用',
            '包括', '涉及', '属于', '具有', '可能', '应该', '需要',
            '一个', '两个', '多个', '每个', '各种', '本身', '之间',
            '其中', '其他', '另外', '首先', '其次', '最后', '主要', '次要',
            '相关', '不同', '相同', '相似', '比较', '对应', '作用',
            '水平', '程度', '质量', '数量', '类型', '模型', '系统', '技术',
            '领域', '方向', '问题', '特点', '特征', '因素', '原因',
            '发展', '出现', '存在', '形成', '建立', '实现', '完成', '获得',
            '提高', '增加', '降低', '减少', '改善', '促进', '推动', '加强',
            '论文', '文献', '报告', '工作', '任务', '目标', '目的',
            '稀疏函数型数据', '等人', '等人提出', '等人研究', '等人发现',
        ])

    def _generate_title(
        self,
        topic: str,
        papers: Optional[List[Dict]],
        raw_content: str,
        date: str
    ) -> str:
        """
        根据报告内容动态生成总结标题

        Args:
            topic: 研究主题
            papers: 论文列表
            raw_content: 生成的报告内容
            date: 日期

        Returns:
            str: 动态生成的报告名称 - 基于内容总结
        """
        if not raw_content:
            return f"日报 - {topic} - {date}"

        # 从完整内容中提取关键词
        phrases = self._extract_noun_phrases(raw_content)

        # 统计每个短语在全文中的出现频率
        phrase_count = {}
        for phrase in phrases:
            count = raw_content.count(phrase)
            if count >= 2:
                phrase_count[phrase] = count

        # 按频率排序
        sorted_phrases = sorted(phrase_count.items(), key=lambda x: x[1], reverse=True)

        # 取前4个核心主题
        core_themes = [phrase for phrase, _ in sorted_phrases[:4]]

        # 如果主题太少，用论文标题补充
        if len(core_themes) < 3 and papers:
            for paper in papers[:10]:
                title = paper.get('title', '')
                title_phrases = self._extract_noun_phrases(title)
                for tp in title_phrases:
                    if tp not in core_themes and len(core_themes) < 5:
                        core_themes.append(tp)

        # 构建总结性标题
        if core_themes:
            # 格式：日报 - {核心主题1}/{核心主题2}/... - {日期}
            themes_str = '/'.join(core_themes[:4])
            return f"日报 - {themes_str} - {date}"
        else:
            return f"日报 - {topic} - {date}"

    def _format_references(self, papers: List[Dict]) -> List[Dict[str, Any]]:
        """格式化参考文献 - 生成完整的学术引用"""
        references = []

        for i, paper in enumerate(papers[:self.config.max_references]):
            title = paper.get('title', 'Unknown Title')
            authors = paper.get('authors', [])
            year = paper.get('year', None)
            contribution = paper.get('key_contribution', '')

            # 标准化authors为字符串列表
            if isinstance(authors, list):
                flat_authors = []
                for a in authors:
                    if isinstance(a, list):
                        flat_authors.extend(a)
                    else:
                        flat_authors.append(str(a))
                authors = flat_authors
            elif authors is None:
                authors = []
            else:
                authors = [str(authors)]

            # 生成APA格式作者字符串（确保不重复句号）
            def format_author_apa(name):
                parts = name.split()
                if len(parts) >= 2:
                    return f"{parts[-1]}, {' '.join(parts[:-1])}"
                return name

            if not authors:
                authors_str = "Unknown"
            elif len(authors) == 1:
                authors_str = format_author_apa(authors[0])
            elif len(authors) == 2:
                authors_str = f"{format_author_apa(authors[0])}, & {format_author_apa(authors[1])}"
            elif len(authors) == 3:
                authors_str = f"{format_author_apa(authors[0])}, {format_author_apa(authors[1])}, & {format_author_apa(authors[2])}"
            else:
                authors_str = f"{format_author_apa(authors[0])} et al."

            # 生成年份字符串
            year_str = f"({year})" if year else "(n.d.)"

            # APA格式：Author(s). (Year). Title. Contribution.
            # 对于"et al."情况，authors_str末尾已含句号，不再重复添加
            if len(authors) > 3:
                formatted_text = f"{authors_str} {year_str}. {title}. {contribution}" if contribution else f"{authors_str} {year_str}. {title}."
            else:
                formatted_text = f"{authors_str}. {year_str}. {title}. {contribution}" if contribution else f"{authors_str}. {year_str}. {title}."

            references.append({
                "formatted": f"[{i+1}] {formatted_text}",
                "title": title,
                "authors": authors,
                "year": year,
                "contribution": contribution
            })

        return references

    def _expand_topic_to_keywords(self, topic: str) -> List[str]:
        """将研究主题扩展为专业的关键词列表

        Args:
            topic: 研究主题

        Returns:
            扩展后的关键词列表
        """
        # 使用 SemanticKeywordExpander 进行语义扩展
        expander = SemanticKeywordExpander()
        result = expander.expand(topic)

        # 获取所有扩展词
        expanded = result.expanded if result.expanded else [topic]

        # 添加日报特有的领域关键词（基于主题匹配）
        topic_lower = topic.lower()
        if "sparse" in topic_lower or "函数数据" in topic_lower:
            expanded.extend([
                "sparse functional data", "functional data analysis", "sparse regression",
                "function approximation", "variable selection", "regularization",
                "dimensionality reduction", "sparse representation"
            ])
        if "医学" in topic_lower or "medical" in topic_lower or "图像" in topic_lower or "image" in topic_lower:
            expanded.extend([
                "medical image", "radiology", "CT", "MRI", "X-ray",
                "image classification", "segmentation", "detection"
            ])

        # 去重保持顺序
        return list(dict.fromkeys(expanded))

    def _filter_by_keywords_and_semantics(
        self,
        papers: List[Dict[str, Any]],
        topic: str,
        keywords: List[str]
    ) -> List[Dict[str, Any]]:
        """根据关键词和语义相关性过滤论文

        Args:
            papers: 论文列表
            topic: 研究主题
            keywords: 关键词列表

        Returns:
            过滤后的论文列表
        """
        import re

        # 扩展主题为专业关键词
        expanded_keywords = self._expand_topic_to_keywords(topic)
        # 合并用户提供的关键词
        all_keywords = list(set(expanded_keywords + keywords))

        logger.info(f"Expanded keywords: {all_keywords[:10]}...")

        def calculate_relevance(paper: Dict) -> float:
            """计算论文与主题的相关性分数"""
            title = paper.get('title', '').lower()
            authors = paper.get('authors', [])
            if isinstance(authors, list):
                authors_str = ' '.join([str(a).lower() for a in authors])
            else:
                authors_str = str(authors).lower()
            contribution = paper.get('key_contribution', '').lower()
            abstract = paper.get('abstract', '').lower()

            # 论文的完整文本用于匹配
            text_content = f"{title} {authors_str} {contribution} {abstract}"

            # 计算关键词匹配次数
            match_count = 0
            for term in all_keywords:
                # 统计词出现次数（中英文都适用）
                matches = len(re.findall(re.escape(term.lower()), text_content))
                match_count += matches

            # 计算相关性分数（归一化到0-1）
            if not text_content.strip():
                return 0.0

            # 标题匹配权重更高
            title_matches = sum(1 for term in all_keywords if term.lower() in title)
            contribution_matches = sum(1 for term in all_keywords if term.lower() in contribution)

            # 综合分数：标题匹配(权重0.4) + 内容匹配(权重0.3) + 匹配次数(权重0.15)
            score = min((title_matches * 0.4 + contribution_matches * 0.3 + match_count * 0.15), 1.0)
            return score

        # 过滤并排序
        scored_papers = []
        for paper in papers:
            score = calculate_relevance(paper)
            paper['semantic_score'] = score
            if score > 0:
                scored_papers.append(paper)

        # 按相关性排序
        scored_papers.sort(key=lambda x: x.get('semantic_score', 0), reverse=True)

        # 只保留相关性>0.5的论文
        filtered = [p for p in scored_papers if p.get('semantic_score', 0) > 0.5]

        logger.info(f"Keyword/semantic filtering: {len(scored_papers)} papers with score>0, top paper: {filtered[0].get('title', 'N/A')[:50] if filtered else 'N/A'}")

        return filtered


async def generate_daily_report(
    topic: str,
    papers: Optional[List[Dict[str, Any]]] = None,
    search_results: Optional[List[Dict[str, Any]]] = None,
    date: Optional[str] = None,
    **kwargs
) -> Report:
    """
    便捷函数：生成日报

    Args:
        topic: 研究主题
        papers: 论文列表
        search_results: 搜索结果
        date: 日期

    Returns:
        Report 对象
    """
    generator = DailyReportGenerator()
    return await generator.generate(topic, papers, search_results, date, **kwargs)