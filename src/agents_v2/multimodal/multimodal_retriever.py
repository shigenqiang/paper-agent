"""
多模态检索器 - Multimodal Retriever

集成视觉编码器、图表分析、公式识别、流程图解析的多模态RAG系统。
"""
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class MultimodalRetrievalResult:
    """多模态检索结果"""
    text_results: List[str] = field(default_factory=list)
    image_results: List[Any] = field(default_factory=list)
    chart_results: List[Any] = field(default_factory=list)
    formula_results: List[Any] = field(default_factory=list)
    diagram_results: Any = None
    combined_context: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class MultimodalRetriever:
    """多模态检索器

    支持:
    - 文本检索 (基于已有的retriever)
    - 图像检索 (CLIP编码)
    - 图表理解 (折线/柱状/饼/散点/热力图)
    - 公式识别 (LaTeX)
    - 流程图解析
    """

    def __init__(self,
                 text_retriever: Any = None,
                 vision_encoder: Any = None,
                 chart_analyzer: Any = None,
                 formula_recognizer: Any = None,
                 diagram_parser: Any = None):
        """初始化多模态检索器

        Args:
            text_retriever: 文本检索器 (有retrieve方法)
            vision_encoder: 视觉编码器
            chart_analyzer: 图表分析器
            formula_recognizer: 公式识别器
            diagram_parser: 流程图解析器
        """
        self.text_retriever = text_retriever

        # 延迟导入避免循环依赖
        if vision_encoder is None:
            from .vision_encoder import VisionEncoder
            vision_encoder = VisionEncoder()

        if chart_analyzer is None:
            from .chart_analyzer import ChartAnalyzer
            chart_analyzer = ChartAnalyzer()

        if formula_recognizer is None:
            from .formula_recognizer import FormulaRecognizer
            formula_recognizer = FormulaRecognizer()

        if diagram_parser is None:
            from .diagram_parser import DiagramParser
            diagram_parser = DiagramParser()

        self.vision_encoder = vision_encoder
        self.chart_analyzer = chart_analyzer
        self.formula_recognizer = formula_recognizer
        self.diagram_parser = diagram_parser

        self._image_index: List[Any] = []
        self._image_embeddings: List[List[float]] = []

    async def retrieve(self,
                       query: str,
                       top_k: int = 10,
                       modalities: List[str] = None) -> MultimodalRetrievalResult:
        """执行多模态检索

        Args:
            query: 查询字符串
            top_k: 返回结果数量
            modalities: 要检索的模态列表，默认["text", "image", "chart"]

        Returns:
            MultimodalRetrievalResult: 检索结果
        """
        if modalities is None:
            modalities = ["text", "image", "chart"]

        result = MultimodalRetrievalResult()
        metadata = {}

        # 文本检索
        if "text" in modalities and self.text_retriever:
            try:
                text_docs = await self.text_retriever.retrieve(query, top_k=top_k)
                result.text_results = text_docs if isinstance(text_docs, list) else []
                metadata["text_count"] = len(result.text_results)
            except Exception as e:
                logger.error(f"文本检索失败: {e}")
                metadata["text_error"] = str(e)

        # 图像检索 (基于CLIP)
        if "image" in modalities and self._image_index:
            try:
                image_results = await self._retrieve_images(query, top_k)
                result.image_results = image_results
                metadata["image_count"] = len(image_results)
            except Exception as e:
                logger.error(f"图像检索失败: {e}")
                metadata["image_error"] = str(e)

        # 图表检索
        if "chart" in modalities:
            await self._retrieve_charts(query, result, top_k)

        metadata["modalities_used"] = modalities
        result.metadata = metadata

        # 生成组合上下文
        result.combined_context = self._build_context(result)

        return result

    async def _retrieve_images(self, query: str, top_k: int) -> List[Any]:
        """检索相似图像

        Args:
            query: 查询文本
            top_k: 返回数量

        Returns:
            List[Any]: 相似图像列表
        """
        if not self._image_index:
            return []

        query_embedding = self.vision_encoder.encode_text(query)

        # 计算相似度
        similarities = []
        for i, img_embedding in enumerate(self._image_embeddings):
            sim = self._cosine_similarity(query_embedding, img_embedding)
            similarities.append((i, sim))

        # 排序
        similarities.sort(key=lambda x: x[1], reverse=True)

        return [self._image_index[i] for i, _ in similarities[:top_k]]

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        v1 = np.array(vec1)
        v2 = np.array(vec2)

        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(np.dot(v1, v2) / (norm1 * norm2))

    async def _retrieve_charts(self,
                                query: str,
                                result: MultimodalRetrievalResult,
                                top_k: int):
        """检索并分析图表

        Args:
            query: 查询
            result: 结果对象
            top_k: 数量
        """
        # 如果image_results中有图表，对其进行分析
        for img in result.image_results[:top_k]:
            try:
                chart_analysis = await self.chart_analyzer.analyze(img)
                result.chart_results.append(chart_analysis)
            except Exception as e:
                logger.warning(f"图表分析失败: {e}")

    def add_image(self, image: Any, metadata: Dict = None):
        """添加图像到索引

        Args:
            image: PIL.Image或图像路径
            metadata: 可选的元数据
        """
        embedding = self.vision_encoder.encode_image(image)

        self._image_index.append({
            "image": image,
            "metadata": metadata or {}
        })
        self._image_embeddings.append(embedding)

    def add_image_batch(self, images: List[Any], metadata_list: List[Dict] = None):
        """批量添加图像

        Args:
            images: 图像列表
            metadata_list: 元数据列表
        """
        for i, img in enumerate(images):
            meta = metadata_list[i] if metadata_list and i < len(metadata_list) else {}
            self.add_image(img, meta)

    async def analyze_image(self, image: Any) -> Dict[str, Any]:
        """分析图像内容

        Args:
            image: PIL.Image或图像路径

        Returns:
            Dict: 分析结果
        """
        result = {
            "type": "unknown",
            "description": "",
            "details": {}
        }

        # 尝试识别图表
        try:
            chart_analysis = await self.chart_analyzer.analyze(image)
            if chart_analysis.chart_type.value != "unknown":
                result["type"] = "chart"
                result["description"] = chart_analysis.description
                result["details"] = {
                    "chart_type": chart_analysis.chart_type.value,
                    "title": chart_analysis.title,
                    "key_points": chart_analysis.key_points,
                    "confidence": chart_analysis.confidence
                }
                return result
        except Exception as e:
            logger.debug(f"图表识别失败: {e}")

        # 尝试识别公式
        try:
            formula_result = await self.formula_recognizer.extract_from_image(image)
            if formula_result.confidence > 0.5:
                result["type"] = "formula"
                result["description"] = formula_result.plain_text
                result["details"] = {
                    "latex": formula_result.latex,
                    "confidence": formula_result.confidence,
                    "is_valid": formula_result.is_valid
                }
                return result
        except Exception as e:
            logger.debug(f"公式识别失败: {e}")

        # 尝试识别流程图
        try:
            diagram_result = await self.diagram_parser.parse(image)
            if diagram_result.nodes:
                result["type"] = "diagram"
                result["description"] = diagram_result.description
                result["details"] = {
                    "node_count": len(diagram_result.nodes),
                    "edge_count": len(diagram_result.edges),
                    "key_info": diagram_result.key_info
                }
                return result
        except Exception as e:
            logger.debug(f"流程图解析失败: {e}")

        # 通用图像描述
        result["type"] = "image"
        result["description"] = "普通图像"

        return result

    async def extract_formula(self, image: Any) -> Dict[str, Any]:
        """从图像提取公式

        Args:
            image: PIL.Image或图像路径

        Returns:
            Dict: 提取结果
        """
        formula = await self.formula_recognizer.extract_from_image(image)

        return {
            "latex": formula.latex,
            "plain_text": formula.plain_text,
            "confidence": formula.confidence,
            "is_valid": formula.is_valid,
            "explanation": formula.explanation
        }

    async def parse_diagram(self, image: Any) -> Dict[str, Any]:
        """解析流程图

        Args:
            image: PIL.Image或图像路径

        Returns:
            Dict: 解析结果
        """
        result = await self.diagram_parser.parse(image)

        return {
            "nodes": [
                {"id": n.id, "label": n.label, "type": n.node_type}
                for n in result.nodes
            ],
            "edges": [
                {"source": e.source, "target": e.target, "label": e.label}
                for e in result.edges
            ],
            "description": result.description,
            "key_info": result.key_info,
            "confidence": result.confidence
        }

    def _build_context(self, result: MultimodalRetrievalResult) -> str:
        """构建组合上下文

        Args:
            result: 检索结果

        Returns:
            str: 组合后的上下文
        """
        parts = []

        # 文本上下文
        if result.text_results:
            text_context = "\n".join([
                f"[文本{i+1}] {doc[:200]}..." if len(doc) > 200 else f"[文本{i+1}] {doc}"
                for i, doc in enumerate(result.text_results[:5])
            ])
            parts.append(f"=== 文本检索结果 ===\n{text_context}")

        # 图表上下文
        if result.chart_results:
            chart_context = "\n".join([
                f"[图表{i+1}] {c.description}"
                for i, c in enumerate(result.chart_results[:3])
            ])
            parts.append(f"=== 图表分析结果 ===\n{chart_context}")

        # 公式上下文
        if result.formula_results:
            formula_context = "\n".join([
                f"[公式{i+1}] {f.latex}"
                for i, f in enumerate(result.formula_results[:3])
            ])
            parts.append(f"=== 公式识别结果 ===\n{formula_context}")

        return "\n\n".join(parts) if parts else ""


# 便捷函数
async def multimodal_retrieve(query: str,
                               text_retriever: Any = None,
                               top_k: int = 10) -> MultimodalRetrievalResult:
    """多模态检索的便捷函数

    Args:
        query: 查询字符串
        text_retriever: 文本检索器
        top_k: 返回数量

    Returns:
        MultimodalRetrievalResult: 检索结果
    """
    retriever = MultimodalRetriever(text_retriever=text_retriever)
    return await retriever.retrieve(query, top_k)


async def analyze_image_multimodal(image: Any) -> Dict[str, Any]:
    """多模态分析图像的便捷函数

    Args:
        image: PIL.Image或图像路径

    Returns:
        Dict: 分析结果
    """
    retriever = MultimodalRetriever()
    return await retriever.analyze_image(image)