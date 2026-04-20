from langgraph.prebuilt import create_react_agent
from src.core.model import llm
from langchain_core.messages import SystemMessage
from src.core.prompt import report_agent_prompt
from src.core.state_model import State

report_agent = create_react_agent(model=llm,tools=[],prompt=SystemMessage(report_agent_prompt))

async def report_node(state: State) -> State:
    """报告生成节点"""
    try:
        current_state = state["value"]
        current_state.current_step="reporting"
        sections = current_state.writted_sections
        sections_text = "\n".join(sections) if sections else "无章节内容提供"

        prompt = f"""
        请将以下提供的章节内容组装成一份完整的调研报告，并以Markdown格式输出。

        【章节内容开始】
        {sections_text}
        【章节内容结束】

        【输出要求】
        1. 使用Markdown格式进行排版（标题、列表、加粗等）
        2. 自动补充必要的过渡语句使报告连贯
        3. 保持专业学术风格
        4. 直接输出完整报告，无需解释过程

        【额外说明】
        请确保章节逻辑顺序合理，如有需要可调整章节排列。
        """
        repsone=await report_agent.ainvoke({"messages":prompt})
        content=repsone["messages"][-1].content
        current_state.report_markdown = content


        return {"value": current_state}

    except Exception as e:
        err_msg = f"Report failed: {str(e)}"
        state["value"].error.report_node_error = err_msg

        return state