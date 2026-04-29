我构建了一个基于多Agent协作架构的智能学术论文研究助手PaperAgent，采用MasterSupervisor作为全局协调器，通过PhaseSupervisor管理六大阶段，各阶段由专业Agent负责。

核心痛点解决：学术研究面临信息过载（日增数千篇论文难以筛选）、报告耗时（2-4小时整理文献）、写作门槛高（选题缺乏评估、修改迭代效率低）三大困境。

核心逻辑流：

系统包含三类Agent协同工作。问题导向Agent包括TopicRefiner（选题诊断）、LiteratureMapper（文献分析）、MethodologyAdvisor（方法指导）、ArgumentBuilder（论点构建）、DiscussionDeepener（讨论增强）、ChartFormatter（图表优化）、LanguagePolisher（语言润色）等。Pipeline Agent按流水线执行：选题→文献检索→Thesis凝练→大纲生成→初稿撰写→编辑优化→评审把关。Writing Agent专注写作任务：LiteratureReviewAgent支持full_review/tracking/summary三种综述模式、ReportRefinerAgent执行多轮迭代精炼、SmartReviserAgent智能修订、ProposalGeneratorAgent生成开题报告。

长链推理：系统通过ReAct范式实现"意图识别→问题分解→多源检索→知识聚合→报告生成→质量评估→迭代优化"的长链路推理。意图识别引擎将查询分为BASIC_QUERY/PROFESSIONAL/FRONTIER/APPLICATION四类，自动路由至最优通道。

多源检索：并行访问arXiv、PubMed、Semantic Scholar、DBLP、OpenAlex五大平台；查询扩展基于同义词库（将"深度学习"扩展为"neural network、CNN、transformer"等）提升召回率；结果融合采用相关性0.6+引用数0.3+时效性0.1的加权评分。

知识图谱：Neo4jStore模块构建论文引用关系图谱，提取引用关系、作者合作网络、主题关联强度，帮助理解研究脉络。

---

订阅推送：SubscriptionManager管理订阅配置，ReportScheduler基于Cron表达式（日报`0 9 * * *`、周报`0 9 * * 1`、月报`0 9 1 * *`）定时触发；PaperFlash生成快讯（HOT热点、TRENDING趋势、CONFERENCE顶会）。