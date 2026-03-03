import asyncio
import sys
import os
import json
from typing import Dict, Any, List
from dataclasses import dataclass

from src.agent.sub_analyse_agent.analyse_cluster_subagent import Cluster_data
from langgraph.prebuilt import  create_react_agent
from src.core.model import llm

from src.core.prompt import deep_analyse_agent_prompt

from  langchain_core.messages import SystemMessage
@dataclass
class DeepAnalyseResult:
    """聚类分析结果封装类"""
    cluster_id: int
    theme: str
    keywords: List[str]
    paper_count: int
    deep_analyse: str
    papers: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "cluster_id": self.cluster_id,
            "theme": self.theme,
            "keywords": self.keywords,
            "paper_count": self.paper_count,
            "deep_analyse": self.deep_analyse,
            "papers": self.papers
        }


deep_analyse_agent=create_react_agent(model=llm,tools=[],prompt=deep_analyse_agent_prompt)

class DeepAnalyseAgent:
    async def run(self, cluster_data):
        """统一接口方法"""
        return await self.deep_analyze_cluster(cluster_data)

    def __init__(self):
        """初始化聚类智能体"""
        self.deep_analyse_agent = create_react_agent(model=llm,tools=[],prompt=SystemMessage(deep_analyse_agent_prompt))

    async def deep_analyze_cluster(self, cluster:Cluster_data ) -> DeepAnalyseResult:
        """对单个聚类进行深入分析"""
        try:

            prompt = f"""
                基于以下聚类信息和详细的论文内容，进行深入的学术分析：

                ## 基本信息
                - **聚类主题**：{cluster['theme_description']}
                - **核心关键词**：{', '.join(cluster['theme_description'])}
                - **论文数量**：{len(cluster['paper'])}

                ## 详细论文数据
                {json.dumps(cluster['paper'], ensure_ascii=False, indent=2)}

                请以结构化的方式组织你的分析结果。
"""

            response = await self.deep_analyse_agent.ainvoke({'messages': prompt})
            analyse_content = response["messages"][-1].content

            return DeepAnalyseResult(
                cluster_id=cluster['cluster_id'],
                theme=cluster['theme_description'],
                keywords=cluster['keywords'],
                paper_count=len(cluster["paper"]),
                deep_analyse=analyse_content,
                papers=cluster["paper"]
            )

        except Exception as e:

            return DeepAnalyseResult(
                cluster_id=cluster['cluster_id'],
                theme=cluster['theme_description'],
                keywords=cluster['keywords'],
                paper_count=len(cluster["paper"]),
                deep_analyse=f"分析失败: {str(e)}",
                papers=cluster["paper"]
            )

if __name__ == '__main__':
    deep_analyse= DeepAnalyseAgent()
    result_deep_analyse=[asyncio.run(deep_analyse.run(result_ananlyse_cluster_nrom)) for result_ananlyse_cluster_nrom in result_ananlyse_cluster]
