import copy
import json
from langchain_core.documents import Document
from pydantic import BaseModel, Field
from typing import Optional,List,Dict
from src.core.model import  llm
from langgraph.prebuilt import  create_react_agent
# from paper_search.paper_search import paper_search_node
from src.core.state_model import State
from langchain_core.messages import HumanMessage,SystemMessage
# from src.core.prompt import
import  asyncio
from langchain_milvus import Milvus, BM25BuiltInFunction
#LangChain 提供的 Milvus 向量库封装#
#BM25BuiltInFunction
# • Milvus 内置的 BM25 函数
# • 用于 关键词倒排检索（稀疏检索）
# • 通常用于 Hybrid Search（向量 + 关键词）
from pymilvus import IndexType, Function
from pymilvus.client.types import MetricType, DataType, FunctionType
from utils.mcp_utils import mcp_server_config


from utils.env_utils import MILVUS_URI, COLLECTION_NAME
from pymilvus import MilvusClient
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_community.document_loaders import UnstructuredPDFLoader
from langchain_mcp_adapters.client import MultiServerMCPClient
from src.core.prompt import read_analyse_prompt
from langsmith import traceable
from utils.env_utils import LANGCHAIN_TRACING_V2,LANGCHAIN_PROJECT,LANGCHAIN_API_KEY
from src.core.model import embed_model
from src.services.milvus import MilvusVectorSave
from  langgraph.graph import StateGraph,START,END
from src.core.state_model import paperagentstate
# client = MilvusClient(uri=MILVUS_URI,username=user,password=password  )

class KeyMethodology(BaseModel):
    name: Optional[str] = Field(default=None, description="方法名称（如“Transformer-based Sentiment Classifier”）")
    principle: Optional[str] = Field(default=None, description="核心原理")
    novelty: Optional[str] = Field(default=None, description="创新点（如“首次引入领域自适应预训练”）")

class ExtractedPaperData(BaseModel):
    # paper_id: str = Field(default=None, description="论文ID")
    core_problem: str = Field(default=None, description="核心问题")
    key_methodology: KeyMethodology = Field(default=None, description="关键方法")
    datasets_used: List[str] = Field(default=[], description="使用的数据集")
    evaluation_metrics: List[str] = Field(default=[], description="评估指标")
    main_results: str = Field(default="", description="主要结果")
    limitations: str = Field(default="", description="局限性")
    contributions: List[str] = Field(default=[], description="贡献")
    # author_institutions: Optional[str]  # 如“Stanford University, Department of CS”

# 创建一个新的Pydantic模型来包装列表
class ExtractedPapersData(BaseModel):
    papers: List[ExtractedPaperData] = Field(default=[], description="提取的论文数据列表")

mcp_client = MultiServerMCPClient(mcp_server_config)

async def reading_download_node(state:State ):
    papers = state["value"].search_state["papers"]
    papers_id=[]
    for paper in papers:
        papers_id.append(paper.get('paper_id'))
    mcp_tools = await mcp_client.get_tools()
    read_download_agent=create_react_agent(model=llm,tools=mcp_tools)
    # 将papers合理分割成多个任务，交给多个read_agent并行执行，最后合并结果
    # 并行执行任务，使用asyncio.gather
    # results = await read_download_agent.ainvoke({"messages":HumanMessage(content=f"你的任务是：下载论文,论文id是{paper_id}, 存储在D:\pycharmprojects\pythonProject1\论文")})
    #下载论文
    # results=await asyncio.gather(*[read_download_agent.ainvoke({"messages":HumanMessage(content=f"你的任务是：下载论文,论文id是{paper_id}, 存储在D:\pycharmprojects\pythonProject1\论文")}) for paper_id in papers_id])
    for paper_id in papers_id:
        result = await read_download_agent.ainvoke({
            "messages": HumanMessage(
                content=f"你的任务是：下载论文,论文id是{paper_id}, 存储在D:\\pycharmprojects\\pythonProject1\\论文"
            )
        })
    return state

def document_parser(file_path:str,strategy,mode):
    ###首先可能会发生几个问题
    # 1\由于pdf的排版问题
    # 2\没识别到这个是有父节点
    # 3\解析的顺序问题
    #现在还有的问题就是得到数据的顺序问题
    loader = UnstructuredPDFLoader(rf"{file_path}", strategy=strategy,mode=mode)
    documents = loader.load()

    #先对document进行排序
    parent_dict = {}
    s=0
    for document in documents:
        # s.add(document.metadata.get("category"))
        metadata = document.metadata
        category = metadata.get('category', None)
        element_id = metadata.get('element_id', None)
        # if metadata.get("parent_id")=="f64bffcf860afc40b67ff21f8df858c5":
        #     print(document)
        if metadata.get("category") in {'Footer', 'UncategorizedText'}:
            continue
        if metadata.get("category") in {'Header'}:
            s+=1
            if s>1:
                continue
        # 有父节点但是父节点的类型不是title,就将其父节点转换为现在的章节的节点,parent_dict只记录了有Title的
        if metadata.get('parent_id') and metadata.get('parent_id') in parent_dict:
            parent_id = metadata.get('parent_id')
        # else:
        #     parent_id = metadata.get('parent_id', parent_id)

        # 把没有父节点认为是上个父节点的内容。因为可能是pdf的解析，没解析到

        # 处理标题
        if category in ("Title", "Header"):
            document.metadata['title'] = document.page_content
            if metadata.get('parent_id') in parent_dict:  # 看是否是子标题
                document.page_content = parent_dict[parent_id].page_content + ' -> ' + document.page_content#数据出现重复在这里，原因是header无parent_id，把之前的数据给进来了
                # 在前面加上前缀，就是加上主标题的名称。也就是形成 主标题->子标题
            parent_dict[element_id] = document
            ##这个是标题对应的内容，根据id,。document是标题
        else:
            # 类型不是标题，而且具有父类，说明是内容的一部分
            parent_dict[parent_id].page_content = parent_dict[parent_id].page_content + ' ' + document.page_content
            # 更新文档内容
            parent_dict[parent_id].metadata['category'] = 'content'#为什么会出现parent_dict呈现的数据很相似
    for key,document in list(parent_dict.items()):#删除一些只有标题，没有其他内容的数据
            print(key,document)
            if document.metadata.get("title")==document.page_content:
                parent_dict.pop(key)
    return list(parent_dict.values())

read_analysis_agent=create_react_agent(model=llm,tools=[],prompt=read_analyse_prompt)
def safe_json_load(content):
    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        print("解析失败，尝试修复非法转义...")
        # 修复非法反斜杠
        raise e




async  def reading_analyze_node(state: State) -> State:#状态要加个file_path
    current_state=state["value"]
    import os
    papers_id=[os.path.splitext(id)[0] for id in os.listdir(r"D:\pycharmprojects\pythonProject1\论文")]
    paper_clean_data=[]
    for i in range(len(papers_id)):
        paper_id=papers_id[i]
        datas=document_parser(rf"D:\pycharmprojects\pythonProject1\论文\{paper_id}.pdf",strategy="hi_res",mode="elements")#参数strategy和mode与UnstructuredPDFLoader的参数意思一样
        paper_pagecontent=""
        for data in datas:
            paper_pagecontent=paper_pagecontent+"/n"+data.page_content
        paper_clean_data.append(paper_pagecontent)

    results = await asyncio.gather(*[read_analysis_agent.ainvoke({"messages":paper}) for paper in paper_clean_data])
    # result = await read_analysis_agent.ainvoke( {"messages":paper_clean_data[0]})
    result_json = [safe_json_load(result.get("messages")[-1].content) for result in results]

    current_state.papers_content=result_json
    #将分析的数据插入到数据库中
    mv = MilvusVectorSave()
    mv.create_milvus_client()
    mv.create_collection()
    mv.insert(result_json)
    #状态更新

    return {"value":current_state}#返回状态
class reading_Workflow:
    def __init__(self):
        self.workflow = self.build_workflow()

    def build_workflow(self):
        builder = StateGraph(State)

        # 添加节点
        builder.add_node("reading_download_node", reading_download_node)
        builder.add_node("reading_analyze_node", reading_analyze_node)

        builder.set_entry_point("reading_download_node")

        # 添加边
        builder.add_edge("reading_download_node","reading_analyze_node")
        # 编译
        graph = builder.compile()
        return graph
async def reading_node(state:State):
    current_state=state
    current_state["value"].current_step = "reading"
    reading_workflow= reading_Workflow()
    final_search_state= await reading_workflow.workflow.ainvoke(current_state)
    return final_search_state




