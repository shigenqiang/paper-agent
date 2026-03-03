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

class MilvusVectorSave:
    """把新数据插入到数据库中"""
    def __init__(self) -> object:
        """自定义collection的索引"""
        self.client: MilvusClient = None

    def create_milvus_client(self) :
        self.client = MilvusClient("http://localhost:19530")

    def create_collection(self):
        #创建了一个MilvusClient实例，用于与Milvus服务器进行交互。跟langchain无关
        schema = self.client.create_schema(enable_dynamic_field=True)
        #一个表示新创建模式的对象、模式的名称或其他相关信息，具体取决于该方法的实现。
        #就是一个存储数据的结构
        schema.add_field(
            field_name="id",  # Primary field name
            is_primary=True,
            auto_id=True,  # Milvus generates IDs automatically; Defaults to False
            datatype=DataType.INT64
        )
        schema.add_field(field_name="title", datatype=DataType.VARCHAR,max_length=1000)
        schema.add_field(field_name='core_problem', datatype=DataType.VARCHAR, max_length=1000)
        schema.add_field(field_name="Abstract", datatype=DataType.VARCHAR,analyzer_params={"tokenizer": "standard", "filter": ["cnalphanumonly"]},enable_analyzer=True, max_length=10000)
        schema.add_field(field_name='key_methodology_name', datatype=DataType.VARCHAR, max_length=1000)
        schema.add_field(field_name='key_methodology_principle', datatype=DataType.VARCHAR, max_length=1000)
        schema.add_field(field_name='key_methodology_novelty', datatype=DataType.VARCHAR, max_length=1000)
        schema.add_field(field_name='datasets_used', datatype=DataType.VARCHAR, max_length=1000,nullable=
True )
        schema.add_field(field_name='evaluation_metrics', datatype=DataType.VARCHAR, max_length=1000,nullable=
True )
        schema.add_field(field_name='main_results', datatype=DataType.VARCHAR, max_length=10000,nullable=
True )
        schema.add_field(field_name='limitations', datatype=DataType.VARCHAR, max_length=1000,nullable=
True )
        schema.add_field(field_name='contributions', datatype=DataType.VARCHAR, max_length=10000)
        schema.add_field(field_name="sparse", datatype=DataType.SPARSE_FLOAT_VECTOR)
        schema.add_field(field_name="dense",datatype=DataType.FLOAT_VECTOR,dim=4096)

        bm25_function = Function(
            name="text_bm25_emb",  # Function name，该名称用于在数据库中注册和调用此函数
            input_field_names=["Abstract"],  # Name of the VARCHAR field containing raw text data
            output_field_names=["sparse"],
            # Name of the SPARSE_FLOAT_VECTOR field reserved to store generated embeddings
            function_type=FunctionType.BM25,  # Set to `BM25`
        )
        #
        schema.add_function(bm25_function)
        #当执行 schema.add_function(bm25_function) 时，就是将实现了 BM25 算法的函数注册到 schema 所代表的模式中。
        # 这样在后续的操作中，就可以通过这个模式来调用 BM25 函数，对符合该模式的数据进行相关性检索等操作。
        # 例如，在一个数据库系统中，可能会用这种方式添加自定义的检索函数，以便在查询数据时使用 BM25 算法来提高检索的准确性。

        # dense_function = Function(
        #     name="text_dense_emb",  # Function name，该名称用于在数据库中注册和调用此函数
        #     input_field_names=["Abstract"],  # Name of the VARCHAR field containing raw text data
        #     output_field_names=["dense"],
        #     # Name of the SPARSE_FLOAT_VECTOR field reserved to store generated embeddings
        #     function_type=FunctionType.TEXTEMBEDDING  # Set to `BM25`
        # )
        # schema.add_function(dense_function)
        index_params = self.client.prepare_index_params()
        #创建并返回一个包含了默认或推荐配置的索引参数对象。
        #用于 生成创建索引（index）时所需的参数模板
        index_params.add_index(
            field_name="sparse",#要与上面的相同
            index_name="sparse_inverted_index",
            index_type="SPARSE_INVERTED_INDEX",  # Inverted index type for sparse vectors
            metric_type="BM25",
            params={
                "inverted_index_algo": "DAAT_MAXSCORE",
                # Algorithm for building and querying the index. Valid values: DAAT_MAXSCORE, DAAT_WAND, TAAT_NAIVE.
                "bm25_k1": 1.2,#控制 “词频（TF）” 对相关性得分的影响程度，避免单个词在文档中过度重复导致得分失真（即 “词频饱和”）。
                "bm25_b": 0.75#控制文档长度对相关性得分的影响程度
            },
        )
        #采用 DAAT_MAXSCORE 优化算法的稀疏倒排索引，
        index_params.add_index(
            field_name="dense",#指定要为哪个字段创建索引。
            index_name="dense_inverted_index",
            index_type=IndexType.HNSW,  # Inverted index type for sparse vectors
            metric_type=MetricType.IP,#内积
            params={"M": 16, "efConstruction": 64}  # M :邻接节点数, efConstruction: 搜索范围
        )

        if COLLECTION_NAME in self.client.list_collections():
            # 先释放， 再删除索引，再删除collection
            self.client.release_collection(collection_name="paper_Data")
            self.client.drop_index(collection_name=COLLECTION_NAME, index_name='sparse_inverted_index')
            self.client.drop_index(collection_name=COLLECTION_NAME, index_name='dense_inverted_index')
            self.client.drop_collection(collection_name=COLLECTION_NAME)
        #安全地删除一个可能已存在的集合
        self.client.create_collection(
            collection_name="paper_Data",
            schema=schema#定义集合的结构，即集合中包含哪些字段以及每个字段的数据类型等信息
            # index_params=index_params#指定集合的索引参数。index_params 是一个字典或其他数据结构，
            # 用于定义集合的索引，例如主键索引、唯一索引等。
        )
    def insert(self,datas:list[Dict]):
        def normalize_paper(p):
            return {
                    "title": p["title"],
                    "Abstract": p["Abstract"],
                    "core_problem": p["core_problem"],
                    "key_methodology_name": p["key_methodology_name"],
                    "key_methodology_principle": p["key_methodology_principle"],
                    "key_methodology_novelty": p["key_methodology_novelty"],
                    "datasets_used": ", ".join(p["datasets_used"]) if isinstance(p["datasets_used"], list) else p.get("datasets_used")or "",
                    "evaluation_metrics": ", ".join(p["evaluation_metrics"]) if isinstance(p["evaluation_metrics"], list) else p.get("evaluation_metrics")or "",
                    "main_results": ", ".join(p["main_results"]) if isinstance(p["main_results"], list) else p.get("main_results",[])or "",
                    "limitations": ", ".join(p["limitations"]) if isinstance(p["limitations"], list) else p.get("limitations")or "",
                    "contributions": "".join(p["contributions"]) if isinstance(p["contributions"], list) else p.get("contributions")or "",
                    "dense":p["dense"]
                    }
        for data in datas:
            dat=data
            dat.update({"dense":embed_model.embed_query(dat["Abstract"])})
            self.client.insert(
                collection_name="paper_Data",
                data=normalize_paper(dat)
            )
            title=dat.get("title")
            print(f"插入数据成功{title}")
        return f"插入数据成功"

