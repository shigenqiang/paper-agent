import asyncio
import sys
import os
import json
from typing import Dict, Any, List
from src.core.prompt import global_analyse_agent_prompt
from src.agents.analysis.deep.deep_analysis_agent import DeepAnalyseResult
from langgraph.prebuilt import create_react_agent
from src.core.model import llm
from langchain_core.messages import SystemMessage

class GlobalanalyseAgent:
    async def run(self, cluster_results: List[DeepAnalyseResult]):
        """统一接口方法"""
        result= await self.generate_global_analyse(cluster_results)
        return result

    def __init__(self):
        """初始化聚类智能体"""
        self.global_analyse_agent = create_react_agent(model=llm,tools=[],prompt=SystemMessage(global_analyse_agent_prompt))

    async def generate_global_analyse(self, analyse_results: List[DeepAnalyseResult]) -> Dict[str, Any]:
        """生成全局分析草稿 - 汇总各主题分析结果"""


        # 准备所有聚类的分析内容
        cluster_summaries = []
        for result in analyse_results:
            cluster_summaries.append({
                "cluster_id": result.cluster_id,
                "theme": result.theme,
                "keywords": result.keywords,
                "paper_count": result.paper_count,
                "analyse_summary": result.deep_analyse[:1000] + "..." if len(
                    result.deep_analyse) > 10000 else result.deep_analyse
            })

        prompt = f"""
基于以下多主题聚类分析结果（见下方 JSON 数据），生成一份逻辑严谨、内容详实的全局分析草稿，需严格覆盖以下 6 大核心模块，且各模块内容需紧密关联主题数据，避免脱离分析基础：
{json.dumps(cluster_summaries, ensure_ascii=False, indent=2)}

# 全局分析核心模块要求（需逐项满足）

## 1. 技术趋势总结


* 明确各主题间的技术交叉点（如技术依赖、协同应用场景）；

* 梳理整体技术发展脉络（如从基础技术到衍生应用的演进路径）；

* 标注关键技术节点（如推动多主题共同发展的核心技术突破）。

## 2. 方法对比


* 按主题分类提炼核心方法（含技术原理、实现路径）；

* 从效率、成本、适用场景、精度等维度横向对比不同方法；

* 总结各方法的技术优势与适用边界。

## 3. 应用领域分析


* 按行业 / 场景维度（如医疗、工业、金融等）归类各主题的应用案例；

* 分析不同应用领域的需求差异对技术选择的影响；

* 标注高潜力应用领域（需结合当前落地效果与市场需求）。

## 4. 研究热点识别


* 提炼当前各主题中关注度较高的技术方向（需说明关注原因，如解决行业痛点、技术创新性等）；

* 预测未来 1-3 年的潜在研究热点（需结合技术发展规律、市场需求变化等给出依据）；

* 区分 “短期热点”（如技术优化类）与 “长期趋势”（如技术架构变革类）。

## 5. 局限性总结


* 归纳各技术路线的共性局限性（如数据依赖、算力需求、兼容性问题等）；

* 分析局限性产生的根本原因（如技术原理限制、产业链配套不足等）；

* 说明局限性对实际应用的影响（如落地场景受限、成本居高不下等）。

## 6. 建议与展望


* 针对局限性提出具体研究建议（如技术突破方向、产业链完善措施等）；

* 给出不同主体（如科研机构、企业、政策制定者）的行动建议；

* 展望技术成熟后的应用前景（如对行业变革的影响、对社会生活的改变等）。


请生成结构清晰、内容完整的全局分析草稿。
"""

        # response = await self.global_analyse_agent.run(task=prompt)
        # global_analyse = response.messages[-1].content

        response =await self.global_analyse_agent.ainvoke({"messages":prompt})
        global_analyse=response['messages'][-1].content



        return  { "total_clusters": len(analyse_results),
                "total_papers": sum(result.paper_count for result in analyse_results),
                "cluster_themes": [result.theme for result in analyse_results],
                "global_analyse": global_analyse,
                "cluster_summaries": cluster_summaries
            }


if __name__ == '__main__':
    global_analyse_agent = GlobalanalyseAgent()
