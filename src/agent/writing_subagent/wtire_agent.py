from langgraph.prebuilt import create_react_agent
from src.core.model import llm
from langchain_core.messages import SystemMessage

from src.core.prompt import writing_agent_prompt
from src.agent.writing_subagent.WritingState import WritingState,SectionState
from typing import Dict, Any


writing_agent =create_react_agent(model=llm,tools=[],prompt=SystemMessage(writing_agent_prompt))

start_flag = 0


async def section_writing_node(state: WritingState) -> Dict[str, Any]:
    try:
        current_section_index = state["current_section_index"]
        sections = state["sections"]
        writted_sections = state["writted_sections"]
        retrieved_docs = state["retrieved_docs"]
        global_analyse = state["global_analysis"]

        global start_flag
        if start_flag == 0:
            start_flag = 1


        # 第一次开始写作 或者 第一次写某一部分
        if (len(writted_sections) == 0) or (len(writted_sections) == current_section_index + 1 and writted_sections[
            current_section_index].completed):
            current_section_index += 1
            new_section = SectionState()
            writted_sections.append(new_section)

        # writing_task = sections[state["current_section_index"]]
        writing_task = sections[current_section_index]
        prompt = f"""请根据以下内容完成写作任务：

                当前写作子任务: {writing_task}
                论文全局分析: {global_analyse}
                可用资料: 
                {retrieved_docs}

                请开始写作：
                
            .其中注意将Cluster id，在写作过程将Cluster id替换成该类主题名称。
        """

        response = await writing_agent.ainvoke({"messages":prompt})
        content = response['messages'][-1].content
        writted_sections[-1].content = content


        if "APPROVED" in content:
            writted_sections[-1].completed = True
            retrieved_docs = []


        return {"writted_sections": writted_sections, "retrieved_docs": retrieved_docs,
                "current_section_index": current_section_index}
    except Exception as e:

        return state
