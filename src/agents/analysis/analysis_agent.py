import asyncio
import json
from typing import List, Dict, Any
from src.core.state_model import State
from src.agents.analysis.cluster.cluster_agent import (
    PaerCluster,
    Cluster_data,
)
from src.agents.analysis.deep.deep_analysis_agent import (
    DeepAnalyseAgent,
    DeepAnalyseResult,
)
from src.agents.analysis.global.global_analysis_agent import (
    GlobalanalyseAgent,
)

class AnalyseAgent:
    """
    论文分析总控 Agent（LangGraph 版本）

    流程：
        1. 聚类
        2. 每个聚类深度分析
        3. 全局汇总
    """

    def __init__(self):
        self.cluster_agent = PaerCluster()
        self.deep_agent = DeepAnalyseAgent()
        self.global_agent = GlobalanalyseAgent()

    # ===============================================
    # 主入口
    # ===============================================
    async def run(self, papers: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        执行完整分析流程

        参数：
            papers: List[Dict] 论文数据

        返回：
            全局分析结果 Dict
        """

        if not papers:
            return {
                "total_clusters": 0,
                "total_papers": 0,
                "cluster_themes": [],
                "global_analyse": "没有可分析的论文数据。",
                "cluster_summaries": [],
            }

        # -------------------------------------------
        # Step 1️⃣ 聚类
        # -------------------------------------------
        cluster_results: List[Cluster_data] = self.cluster_agent.run(papers)

        if not cluster_results:
            return {
                "total_clusters": 0,
                "total_papers": len(papers),
                "cluster_themes": [],
                "global_analyse": "聚类失败。",
                "cluster_summaries": [],
            }
        print("聚类完成")

        # -------------------------------------------
        # Step 2️⃣ 深度分析（并发）
        # -------------------------------------------
        deep_results: List[DeepAnalyseResult] = await asyncio.gather(
            *[self.deep_agent.run(cluster) for cluster in cluster_results]
        )

        print("深度分析完成")

        # -------------------------------------------
        # Step 3️⃣ 全局分析
        # -------------------------------------------
        final_result = None

        final_result =await  self.global_agent.run(deep_results)
        print("全局分析完成")


        return final_result



async def analyse_node(state: State) -> State:
    """搜索论文节点"""
    try:
        current_state = state["value"]
        current_state.current_step="analyzing"
        extracted_papers = current_state.papers_content
        analyse_agent = AnalyseAgent()
        # task = TextMessage(content=json.dumps(extracted_papers.model_dump(),ensure_ascii=False), source="User")
        analyse_results = await analyse_agent.run(extracted_papers)


        current_state.analysis_result = analyse_results


        return {"value": current_state}

    except Exception as e:
        err_msg = f"Analyse failed: {str(e)}"
        state["value"].error.analyse_node_error = err_msg
        return state
# if __name__ == "__main__":
    # import asyncio
    #
    # example_papers = [
    #     {
    #         "core_problem": "时间序列预测",
    #         "key_methodology_name": "Transformer",
    #         "key_methodology_principle": "Self-attention mechanism",
    #         "main_results": ["提高预测精度"],
    #         "contributions": ["提出新模型结构"],
    #     }
    # ]
    #
    # agent = AnalyseAgent()
    #
    # result = asyncio.run(agent.run(result_json))
    #
    # print(json.dumps(result, ensure_ascii=False, indent=2))