from langgraph.prebuilt import create_react_agent
from src.core.model import llm
from langchain_core.messages import SystemMessage



from src.core.prompt import retrieval_agent_prompt
from typing import Dict, Any,List
from langchain_core.tools import tool

from src.services.retriveal_tools import retrieval_tool
from src.agents.writing.writing_state import SectionState,WritingState
import asyncio


@tool(description="Retrieve 资料")
def retrieval_tool(content:List[str]):
    return retrieval_tool(content)

retrieval_agent = create_react_agent(model=llm,tools=[retrieval_tool],prompt=SystemMessage(retrieval_agent_prompt))


def parse_to_list(s: str) -> list[str]:
    # 使用正则表达式提取[]之间的内容
    # 只保留第一个匹配到的[]对中的内容
    import re
    # 去除首尾的换行符和空格
    s = s.strip()

    match = re.search(r'\[(.*?)\]', s, re.DOTALL)
    if not match:
        return []

    content = match.group(1).strip()
    if not content:
        return []

    content = content.replace('，', ',')  # 中文逗号替换为英文逗号
    # 按逗号分割并过滤空字符串
    items = [item.strip() for item in content.split(',') if item.strip()]
    return items


async def retrieval_node(state: WritingState) -> Dict[str, Any]:


    try:
        writted_sections = state["writted_sections"]
        retrieved_docs = state["retrieved_docs"]

        query = writted_sections[-1].content

        querys = parse_to_list(query)
        # querys = ['语言模型', '大模型', '语言模型原理']
        # retrieved_docs = []
        # 将querys并行交给retrieval_tool去执行，并将结果合并
        results = retrieval_tool(querys)
        # results = await asyncio.gather(*[retrieval_tool(query) for query in querys])
        # 去重
        for result in results:
            for paper in result:
                flag = True
                for doc in retrieved_docs:
                    if paper["paper_id"] == doc["paper_id"]:
                        flag = False
                if flag:
                    retrieved_docs.append(paper)

        # 生成检索条件
        # response = await retrieval_agent.run(task = prompt)
        # content = response.messages[-1].content

        # 调用检索服务
        # retrieved_docs = retrieval_tool(content)
        # retrieved_docs = [{"paper_id": "1", "title": "langraph介绍", "abstract": "是一个AI框架", "content": "LangGraph 是一个专为构建复杂、有状态的 AI 智能体（Agent）工作流设计的框架，基于图状态机（Graph State Machine）架构，由 LangChain 团队开发，可看作是对 LangChain 的扩展与增强。"}]
        return {"retrieved_docs": retrieved_docs}
    except Exception as e:

        return state