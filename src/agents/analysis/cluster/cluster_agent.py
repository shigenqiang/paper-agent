from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel
from typing import Dict,List,Any,TypedDict
import numpy as np
from src.core.model import llm
from src.core.prompt import analyse_cluster_prompt
from src.core.model import embed_model
from sklearn.cluster import KMeans
from dataclasses import dataclass



class Cluster_data(TypedDict):
    cluster_id: int
    paper:list[Dict]
    theme_description: str
    keywords: List[str]
    centroid_vector: np.ndarray = None




class PaerCluster:#如何设计一个类，首先进行嵌入，再使用聚类，
    def __init__(self):
        self.cluster_agent=create_react_agent(model=llm,tools=[])
        self.embed_model=embed_model


    def prepare_text_for_embedding(self, papers: List[Dict]) -> List[str]:#为多个论文进行处理
        texts_result=[]
        for paper in papers:
            """准备用于生成嵌入向量的文本"""
            text_parts = []

            # 核心问题
            if paper.get('core_problem'):
                text_parts.append(f"Problem: {paper['core_problem']}")

            # 方法论
            if paper.get('key_methodology_name'):
                methodology = paper['key_methodology_name']
                methodology_principle = paper['key_methodology_principle']
                text_parts.append(f"Method: {methodology} - {methodology_principle}")

            # 主要结果
            if paper.get('main_results'):
                if isinstance(paper['main_results'], list):
                    results = "; ".join(paper['main_results'])
                else:
                    results = str(paper['main_results'])
                text_parts.append(f"Results: {results}")

            # 贡献
            if paper.get('contributions'):
                contributions = "; ".join(paper['contributions'])
                text_parts.append(f"Contributions: {contributions}")

            text=" ".join(text_parts)
            texts_result.append(text)
        return texts_result


    def get_embedding(self,texts:List[str])->List[List[float]]:
        "Abstract,core_problem,main_results,limitations,contributions"
        embedding_datas=[]

        for text in texts:
            embedding_data =self.embed_model.embed_query(text)
            embedding_datas.append(embedding_data)
        return embedding_datas

    def determine_optimal_clusters(self, embeddings:List[List[float]], max_k: int = 5) -> int:
        """使用肘部法则确定最佳聚类数量"""
        if len(embeddings) <= 2:
            return 1

        max_clusters = min(max_k, len(embeddings) - 1)
        if max_clusters == 1:
            return 1

        inertias = []
        k_range = range(1, max_clusters + 1)

        for k in k_range:
            if k <= len(embeddings):
                kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
                kmeans.fit(embeddings)
                inertias.append(kmeans.inertia_)

        # 简单的肘部法则实现
        if len(inertias) >= 3:
            differences = [inertias[i - 1] - inertias[i] for i in range(1, len(inertias))]
            optimal_k = differences.index(max(differences)) + 2
            return min(optimal_k, max_clusters)
        else:
            return min(2, max_clusters)


    def cluster(self,embedding_datas:List[List[float]],papers:List[Dict])->List[Cluster_data]:
        if not embedding_datas:
            return []
        cluster_num=self.determine_optimal_clusters(embedding_datas)

        cluster = KMeans(n_clusters=cluster_num)

        # 确定聚类数量
        n_clusters = self.determine_optimal_clusters(embedding_datas)

        if n_clusters == 1 or len(embedding_datas) <= n_clusters:
            # 所有论文在一个聚类中
            return [Cluster_data(
                cluster_id=0,
                paper=papers,
                theme_description="General Research Papers",
                keywords=["general"],
                centroid_vector=np.mean(embedding_datas, axis=0)
            )]

        # 执行KMeans聚类
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        cluster_labels = kmeans.fit_predict(embedding_datas)#数据的类别标签

        # 构建聚类结果
        clusters = []
        for cluster_id in range(n_clusters):
            cluster_papers = [
                papers[i] for i, label in enumerate(cluster_labels)
                if label == cluster_id
            ]

            cluster_embeddings = [
                np.array(embedding_datas[i]) for i, label in enumerate(cluster_labels)
                if label == cluster_id
            ]

            centroid = np.mean(cluster_embeddings, axis=0)

            clusters.append(Cluster_data(
                cluster_id=cluster_id,
                paper=cluster_papers,
                theme_description="",
                keywords=[],
                centroid_vector=centroid
            ))

        return clusters
    def parse_llm_response(self,response:str):
        """解析LLM响应，提取主题描述和关键词"""
        # try:
        import re

        # 使用正则表达式匹配主题描述，支持中英文冒号、空格等变化
        theme_pattern = r'主题描述\s*[:：]\s*(.*?)\s*(?:\n|$)'
        theme_match = re.search(theme_pattern, response, re.IGNORECASE)

        # 使用正则表达式匹配关键词，支持中英文冒号、空格等变化
        keywords_pattern = r'关键词\s*[:：]\s*(.*?)\s*(?:\n|$)'
        keywords_match = re.search(keywords_pattern, response, re.IGNORECASE)

        # 提取主题描述
        if theme_match:
            theme_description = theme_match.group(1).strip()
            # 清理可能的额外引号或空格
            theme_description = re.sub(r'^["\']|["\']$', '', theme_description).strip()
        else:
            # 尝试其他可能的格式变体
            alt_theme_patterns = [
                r'主题\s*[:：]\s*([^\n]+)',
                r'theme\s*[:：]\s*([^\n]+)',
                r'主题描述\s*[:：]\s*([^\n]+)'
            ]

            theme_description = "未分类研究主题"
            for pattern in alt_theme_patterns:
                match = re.search(pattern, response, re.IGNORECASE)
                if match:
                    theme_description = match.group(1).strip()
                    break

        # 提取关键词
        if keywords_match:
            keywords_str = keywords_match.group(1).strip()
            # 支持逗号、分号、空格等多种分隔符
            keywords = []
            for separator in [',', ';', '，', '；']:
                if separator in keywords_str:
                    keywords = [kw.strip() for kw in keywords_str.split(separator) if kw.strip()]
                    break

            # 如果没有找到分隔符，尝试按空格分割
            if not keywords:
                keywords = [kw.strip() for kw in keywords_str.split() if kw.strip()]

            # 清理每个关键词中的额外引号
            keywords = [re.sub(r'^["\']|["\']$', '', kw).strip() for kw in keywords]
        else:
            # 尝试其他可能的关键词格式
            alt_keywords_patterns = [
                r'关键词\s*[:：]\s*([^\n]+)',
                r'keywords\s*[:：]\s*([^\n]+)',
                r'key\s+words\s*[:：]\s*([^\n]+)'
            ]

            keywords = ["research"]
            for pattern in alt_keywords_patterns:
                match = re.search(pattern, response, re.IGNORECASE)
                if match:
                    keywords_str = match.group(1).strip()
                    keywords = [kw.strip() for kw in keywords_str.split(',') if kw.strip()]
                    break

        # 确保至少有一个关键词
        if not keywords:
            keywords = ["research"]

        # 限制关键词数量
        keywords = keywords[:5]

        return theme_description, keywords

        # except Exception as e:
        #     return "未分类研究主题", ["research"]
    def llm_topic(self,cluster:Cluster_data) -> List[str]:
        """使用LLM为聚类生成主题描述和关键词"""##单个主题的处理
        import json
        paper_data=cluster["paper"]
        paper_summaries=[]
        for paper in paper_data[:2]:  # 限制前3篇论文
            summary = {
                "problem": paper.get("core_problem"),
                "method": paper.get("key_methodology_name"),
                "results": paper.get("main_results")
            }
            paper_summaries.append(summary)
        prompt = f"""
                       基于以下论文信息，为这一类论文生成一个简洁的主题描述(必须生成一个主题，不能生成空主题)和3-5个关键词：

                       论文信息：
                       {json.dumps(paper_summaries, ensure_ascii=False, indent=2)}

                       请提供：
                       1. 一个简洁的主题描述（20-30字）
                       2. 3-5个关键词（用逗号分隔）

                       格式：
                       主题描述：[主题描述]
                       关键词：[关键词1, 关键词2, 关键词3]
                   """
        response = self.cluster_agent.invoke({"messages":f"{prompt}"})
        # 解析LLM响应
        theme_description, keywords = self.parse_llm_response(response['messages'][-1].content)
        return theme_description, keywords

    def run_clustering_analyse(self, papers_data: Dict[str, Any]) -> List[Cluster_data]:
        """运行完整的聚类分析流程"""

        papers = papers_data

        if not papers:
            return []

        # -----------------------
        # Step 1: 构造嵌入文本
        # -----------------------
        texts = self.prepare_text_for_embedding(papers)

        # -----------------------
        # Step 2: 生成嵌入向量
        # -----------------------
        embedding_datas = self.get_embedding(texts)

        if not embedding_datas:
            return []

        # -----------------------
        # Step 3: 聚类
        # -----------------------
        clusters = self.cluster(embedding_datas, papers)
        print(clusters)

        # -----------------------
        # Step 4: LLM生成主题
        # -----------------------
        results = []

        for cluster in clusters:
            theme_description, keywords = self.llm_topic(cluster)

            updated_cluster = Cluster_data(
                cluster_id=cluster["cluster_id"],
                paper=cluster["paper"],
                theme_description=theme_description,
                keywords=keywords,
                centroid_vector=cluster["centroid_vector"]
            )

            results.append(updated_cluster)

        return results

    def run(self, papers_data):
        """统一接口方法"""
        return self.run_clustering_analyse(papers_data)





if "__name__ "== '__main__':
    example=PaerCluster()
    result_ananlyse_cluster=example.run(result_json)










