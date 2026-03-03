from typing import List, Dict, Any
from src.services.milvus import MilvusVectorSave


def retrieval_tool(querys: List[str], n_results: int = 5) -> List[List[Dict[str, Any]]]:
    """
    检索工具，从向量数据库中查询相关文档

    :param query: 查询文本
    :param n_results: 返回结果数量
    :return: 包含文档metadata的列表
    """
    # 初始化Milvus客户端
    Milvus = MilvusVectorSave()
    client=Milvus.client
    # 执行查询
    query_results = client.query(query_texts=querys, n_results=n_results)
    print(query_results)
    # 提取metadata列表
    if query_results and 'metadatas' in query_results:
        return query_results['metadatas']

    return []