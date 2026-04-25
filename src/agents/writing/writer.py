from langgraph.prebuilt import create_react_agent
from src.core.model import llm
from langchain_core.messages import SystemMessage

from src.core.prompt import writing_agent_prompt
from src.agents.writing.writing_state import WritingState,SectionState
from typing import Dict, Any


writing_agent =create_react_agent(model=llm,tools=[],prompt=SystemMessage(writing_agent_prompt))


async def section_writing_node(state: WritingState) -> Dict[str, Any]:
    """
    写作节点：处理当前小节的写作任务

    索引推进逻辑：
    - 如果 writted_sections 为空（首次），初始化第一个节
    - 如果当前节完成（completed=True），推进到下一个节
    - 否则继续处理当前节
    """
    try:
        current_section_index = state["current_section_index"]
        sections = state["sections"] or []
        writted_sections = state["writted_sections"] or []
        retrieved_docs = state["retrieved_docs"] or []
        global_analyse = state["global_analysis"] or ""

        # 边界检查
        if not sections or current_section_index >= len(sections):
            return {
                "writted_sections": writted_sections,
                "retrieved_docs": retrieved_docs,
                "current_section_index": current_section_index
            }

        # 确定要处理的节索引
        section_idx_to_write = current_section_index

        # 判断是否需要初始化新的节或推进到下一个节
        if len(writted_sections) == 0:
            # 首次写作，初始化第一个节
            section_idx_to_write = 0
            writted_sections.append(SectionState())
        elif writted_sections[-1].completed:
            # 上一个节已完成，检查是否还有更多节
            next_idx = current_section_index + 1
            if next_idx < len(sections):
                # 还有更多节，初始化下一个节
                section_idx_to_write = next_idx
                writted_sections.append(SectionState())
                current_section_index = next_idx
            else:
                # 所有节都处理完了
                return {
                    "writted_sections": writted_sections,
                    "retrieved_docs": retrieved_docs,
                    "current_section_index": current_section_index
                }
        else:
            # 当前节还没完成，继续处理它
            section_idx_to_write = current_section_index

        # 获取写作任务
        writing_task = sections[section_idx_to_write]
        prompt = f"""请根据以下内容完成写作任务：

        当前写作子任务: {writing_task}
        论文全局分析: {global_analyse}
        可用资料:
        {retrieved_docs}

        请开始写作：

        注意：将Cluster id在写作过程中替换成该类主题名称。
        """

        response = await writing_agent.ainvoke({"messages":prompt})
        content = response['messages'][-1].content
        writted_sections[-1].content = content

        if "APPROVED" in content:
            writted_sections[-1].completed = True
            retrieved_docs = []
            # 如果当前节完成，自动推进索引到下一个位置
            # 这样 condition_edge 检查时会知道还有更多节
            # 但 actual 处理仍由下一个 section_writing_node 调用完成

        return {
            "writted_sections": writted_sections,
            "retrieved_docs": retrieved_docs,
            "current_section_index": current_section_index
        }
    except Exception as e:
        print(f"section_writing_node error: {e}")
        return state
