import asyncio
from pydantic import BaseModel, Field
from typing import Optional,List,Dict,Any
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage,SystemMessage
from src.core.prompt import search_agent_prompt_1,search_agent_prompt_2
from src.core.model import llm
from langchain_mcp_adapters.client import MultiServerMCPClient
from utils.log_utils import   setup_logger
from utils.mcp_utils import mcp_server_config
from langgraph.types import interrupt,Command
from langgraph.graph import StateGraph,START,END
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser,JsonOutputParser
from langgraph.checkpoint.memory import  MemorySaver
from src.core.state_model import State
import json

# tool=get_mcp_tools()


class SearchAgent(BaseModel):
    query: str#类属性
    next_node:Optional[str]=Field(default=None)
    structed_query: Optional[dict|str]=Field(default=None,description="进行修改查询")
    papers_filter: Optional[dict]=Field(default_factory=dict,description="论文过滤要求")
    papers:Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="检索到的论文元数据列表")

    def __init__(self,**data):
        super().__init__(**data)
        # 如果未提供 structed_query，使用 query
        if not self.structed_query:
            self.structed_query = self.query

# ============ 节点 1：生成查询 ============
async def generate_query_node(state: SearchAgent):
    """生成初始结构化查询"""
    prompt = ChatPromptTemplate.from_template(
        """
        用户需求：{user_request}
        角色定义：{search_agent_prompt}
        """)
    chain = prompt | llm | JsonOutputParser()  # ✓ 添加输出解析器

    # ✓ 调用链，传入正确的变量
    result = await chain.ainvoke({
        "user_request": state.query,
        "search_agent_prompt":search_agent_prompt_1
    })

    print(f"✓ 生成查询: {result}")
    state.structed_query = result

    # ✓ 返回字典，不修改 state
    return state


# ============ 节点 2：人工检查（中断） ============
async def human_check_node(state: SearchAgent):
    """等待人工审查和修改"""
    from langgraph.types import interrupt

# 暂停并提交给人工
    print("进入人工检查,请输入True or False")
    human_input = interrupt({
        "action": "please_review",
        "current_query": state.structed_query,
        "original_request": state.query,
        "message": "请审查查询是否合理，可以修改或保持原样"
    })

    print(f"检查结果为{human_input}退出人工检查")



    if human_input:
        state.next_node="paper_search_node"
    else:
          state.next_node="query_transform_node"
    return state





# ============ 节点 3：改写查询 ============
async def query_transform_node(state: SearchAgent):
    """使用 LLM 改写查询为高质量学术格式"""
    prompt_template = ChatPromptTemplate.from_template(
        """
        当前查询质量差：{query}
        用户需求：{user_request}
        
        改写为高质量学术查询（仅输出查询文本）：
        {search_Agent_prompt_1}
        """)

    # ✓ 添加输出解析器
    chain = prompt_template | llm | JsonOutputParser()

    try:
        # ✓ 使用 ainvoke（异步）
        result = await chain.ainvoke({
            "query": state.structed_query,
            "user_request": state.query,
            "search_Agent_prompt_1":search_agent_prompt_1
        })

        print(f"✓ 改写成功: {result}")

        state.structed_query = result

        # ✓ 返回字典更新状态
        return state

    except Exception as e:
        print(f"❌ 错误: {e}")

mcp_client = MultiServerMCPClient(mcp_server_config)

import re
import json


def safe_json_load(content):
    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        print("解析失败，尝试修复非法转义...")
        # 修复非法反斜杠
        raise e
# from datetime import date
# class Paper(BaseModel):
#     paper_id: str
#     title: str
#     authors: List[str]
#     abstract: str
#     url: str
#     pdf_url: Optional[str] = None
#     published_date: Optional[date] = None
#     updated_date: Optional[date] = None
#     source: str
#     categories: List[str] = Field(default_factory=list)
#     keywords: List[str] = Field(default_factory=list)
#     doi: Optional[str] = None
# ============ 节点 4：搜索论文 ============
async def paper_search_node(state: SearchAgent):
    """使用搜索 Agent 查询论文"""
    mcp_tools=await mcp_client.get_tools()
    search_agent=create_react_agent(model=llm,tools=mcp_tools)
    query = state.structed_query
    print(f"🔍 正在搜索: {query}")
    resp = await search_agent.ainvoke({
            "messages": [HumanMessage(content=f"{search_agent_prompt_2}{query}")]
        })
    print(f"🔍 搜索完成")

        # ✓ 从响应中提取搜索结果
    search_content = resp["messages"][-1].content
    state.papers=safe_json_load(search_content)

    print(f"✓ 搜索结果: {search_content}")
    return state


async def paper_filter_node(state: SearchAgent) -> dict:
        """
        三阶段论文过滤：
        1. 基于LLM的相关性评分（标题+摘要 vs 查询）
        2. 基于元数据的客观评分（引用数、发表年份等）
        3. 加权线性组合 + Top-K选择
        """
        papers = state.get("papers", [])
        query = state.papers_filter.get("query", "")
        top_k = state.papers_filter.get("top_k", 5)
        llm_weight = state.papers_filter.get("llm_weight", 0.7)
        metadata_weight = state.papers_filter.get("metadata_weight", 0.3)

        if not papers:
            return {"filtered_papers": [], "papers": papers}
        # 第一步：LLM相关性评分
        print("=" * 50)
        print("开始LLM相关性评分...")
        print("=" * 50)

        papers_with_llm_scores = []
        for idx, paper in enumerate(papers, 1):
            # 构建评分提示词
            eval_prompt = f"""请评估以下论文与搜索查询的相关性。
            搜索查询：{query}
            论文标题：{paper.title}
            论文摘要：{paper.abstract}
            请在0-10的范围内评分，其中：
            - 10分：高度相关，直接解决查询问题
            - 7-9分：很相关，有重要关联
            - 5-6分：中等相关，有一定关联
            - 3-4分：弱相关，间接相关
            - 0-2分：不相关
            请用JSON格式返回，包含score（分数）和reasoning（理由）字段。
            示例：{{"score": 8, "reasoning": "该论文直接讨论了..."}}
            """

            try:
                # 获取LLM评分
                response = llm.invoke(eval_prompt)
                response_text = response.content.strip()
    
                # 解析JSON格式的响应
                score_data = json.loads(response_text)
                llm_score = float(score_data.get("score", 5))
                llm_score = min(10, max(0, llm_score))  # 限制在0-10范围内
    
                print(f"\n论文 {idx}: {paper.title}")
                print(f"LLM评分: {llm_score}/10 - {score_data.get('reasoning', '')}")
    
            except (json.JSONDecodeError, ValueError, KeyError) as e:
                print(f"评分解析失败，使用默认值5.0")
                llm_score = 5.0
    
            paper.llm_score =llm_score
            papers_with_llm_scores.append(paper)
    
        # 第二步：元数据评分
        print("\n" + "=" * 50)
        print("开始元数据评分...")
        print("=" * 50)
    
        if papers_with_llm_scores:
                # 提取引用数和年份用于归一化
                years_list = [p.published_date for p in papers_with_llm_scores if p.published_date is not None]

                max_year = max(years_list) if years_list else 2024
                min_year = min(years_list) if years_list else 2020
                year_range = max_year - min_year if max_year > min_year else 1
    
                for paper in papers_with_llm_scores:
                    # 引用评分：引用数越多越好（0-5分）

    
                    # 新近度评分：发表年份越近越好（0-5分）
                    recency_score = ((paper.published_date - min_year) / year_range) * 5 if year_range > 0 else 5
    
                    # 组合元数据评分（0-10分）
                    paper.metadata_score =recency_score
    
                    print(f"\n论文: {paper.title}")
                    print(f"  发表年份: {paper.published_date} → 新近度评分: {recency_score:.2f}")
                    print(f"  元数据评分: {paper.metadata_score:.2f}/10")
    
        # 第三步：加权线性组合和排序
                    print("\n" + "=" * 50)
                    print("计算最终综合评分...")
                    print("=" * 50)
    
                    for paper in papers_with_llm_scores:
                        paper.final_score = (
                                paper.llm_score * llm_weight +
                                paper.metadata_score *
                                metadata_weight
                        )
                        print(f"\n论文: {paper.title}")
                        print(
                            f"  最终评分: {paper.llm_score:.1f}×{llm_weight} + {paper.metadata_score:.1f}×{metadata_weight} = {paper.final_score:.2f}")
    
                    # 按最终评分排序并选择前K篇
                    ranked_papers = sorted(
                        papers_with_llm_scores,
                        key=lambda p: p.final_score,
                        reverse=True
                    )
    
                    filtered_papers = ranked_papers[:top_k]
    
                    # 输出过滤结果
                    print("\n" + "=" * 50)
                    print(f"论文过滤结果 (前{top_k}篇)：")
                    print("=" * 50)
                    for i, paper in enumerate(filtered_papers, 1):
                        print(f"\n{i}. 【{paper.final_score:.2f}分】{paper.title}")
                        print(f"   LLM相关性: {paper.llm_score:.1f}/10")
                        print(f"   元数据质量: {paper.metadata_score:.1f}/10")
                        print(f"   引用数: {paper.citations} | 发表年份: {paper.published_date}")
    
        # 更新状态
                    return {"filtered_papers": filtered_papers,"papers": papers_with_llm_scores}  # 保留所有论文及其评分以供参考
# ============ 构建图 ============

class SearchWorkflow:
    def __init__(self):
        self.workflow = self.build_workflow()

    def build_workflow(self):
        builder = StateGraph(SearchAgent)
        # 添加节点
        builder.add_node("generate_query_node", generate_query_node)
        builder.add_node("human_check_node", human_check_node)
        builder.add_node("query_transform_node", query_transform_node)
        builder.add_node("paper_search_node", paper_search_node)

        # 添加边
        builder.add_edge(START, "generate_query_node")
        builder.add_edge("generate_query_node", "human_check_node")

        # 条件边：人工选择是否改写
        builder.add_conditional_edges("human_check_node", lambda x: x.next_node,{"query_transform_node":"query_transform_node", "paper_search_node":"paper_search_node"  })


        builder.add_edge("query_transform_node", "paper_search_node")
        builder.add_edge("paper_search_node", END)

        # 编译
        graph = builder.compile(checkpointer=MemorySaver())
        graph.get_graph().print_ascii()
        return graph
config = {"configurable": {"thread_id": "session_1"}}
async def search_node(state:State):
    current_state=state["value"]
    current_state.current_step="searching"
    search_state = SearchAgent(query=current_state.search_state.get("query"))
    search_workflow= SearchWorkflow()
    paper_content=await search_workflow.workflow.ainvoke(search_state,config=config)
    final_search_state= await search_workflow.workflow.ainvoke(
        Command(resume=True),
        config
    )
    if len(final_search_state.get("papers"))>0:
        print(f"共搜索到{len(final_search_state.get('papers'))}篇论文")
    else:
        current_state.error.search_node_error="没有找到相关论文,请尝试其他查询条件"

    current_state.search_state=final_search_state

    return {"value": current_state}






import grandalf
# graph.get_graph().print_ascii()
#论文过滤，
#论文质量评估
#根据引用量













#将用户查询转换为结构化搜索条件
# response_format=SearchQuery






