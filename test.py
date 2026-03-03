from langgraph.graph import StateGraph, END, START
from src.agent.paper_search_agent import paper_search_node
from typing import TypedDict
from langgraph.checkpoint.memory import MemorySaver
from src.core.state_model import paperagentstate
import sys
import os

from sqlalchemy import Null
from sqlalchemy.sql.functions import current_date

# 将项目根目录添加到Python路径
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from typing import TypedDict, Annotated, Sequence
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
# from src.core.state_model import PaperAgentState, ExecutionState, NodeError,State
from src.agent.paper_search_agent import  search_node
from src.agent.reading.reading_agent import reading_node
from src.agent.analyse_agent import analyse_node
from src.agent.writing_agent import writing_node
from src.agent.reprot_agent import report_node
from typing import Dict, Any

from src.core.state_model import State, ConfigSchema

import asyncio

builder = StateGraph(State)

# 添加节点
builder.add_node("search_node", search_node)
builder.add_node("reading_node", reading_node)
builder.add_node("analyse_node", analyse_node)
builder.add_node("writing_node", writing_node)
builder.add_node("report_node", report_node)
# builder.add_node("handle_error_node", self.handle_error_node)

builder.set_entry_point("search_node")

# 定义工作流路径
builder.add_edge(START, "search_node")
builder.add_edge("search_node", "reading_node")

builder.add_edge("reading_node", "analyse_node")
builder.add_edge("analyse_node", "writing_node")
builder.add_edge("writing_node", "report_node")

builder.add_edge("report_node", END)
# builder.add_edge("writing_node", "report_node")
# builder.add_conditional_edges("search_node", self.condition_handler)
# builder.add_conditional_edges("reading_node", self.condition_handler)
# builder.add_conditional_edges("analyse_node", self.condition_handler)
# builder.add_conditional_edges("writing_node", self.condition_handler)
# builder.add_conditional_edges("report_node", self.condition_handler)
# builder.add_edge("handle_error_node", END)
graph = builder.compile()
import uuid

config = {
    "configurable": {
        "thread_id": uuid.uuid4(),
    }
}
from src.core.state_model import SearchAgent

state = State(value=paperagentstate(search_state=SearchAgent(query="请搜索3篇2022-2025年的函数型数据论文"), ))
ans = await graph.ainvoke(state, config=config)
