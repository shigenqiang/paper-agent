"""
Paper API - RESTful API for Paper Agent Frontend

Provides CRUD operations for papers, literature, and writing sessions.
"""
import time
import asyncio
import logging
import os
from typing import Any, Dict, List, Optional
from datetime import datetime
from aiohttp import web
import uuid
import json

# 加载 .env 文件
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)

# 读取环境变量
DEFAULT_API_KEY = os.getenv("OPENAI_API_KEY", "dev-api-key")
DEFAULT_BASE_URL = os.getenv("OPENAI_BASE_URL", None)

# 文件持久化路径
STORAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data")
PAPERS_FILE = os.path.join(STORAGE_DIR, "papers_storage.json")
LITERATURE_FILE = os.path.join(STORAGE_DIR, "literature_storage.json")

# 确保存储目录存在
os.makedirs(STORAGE_DIR, exist_ok=True)


def load_papers_storage() -> Dict[str, Dict]:
    """从文件加载论文存储"""
    try:
        if os.path.exists(PAPERS_FILE):
            with open(PAPERS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.info(f"Loaded {len(data)} papers from storage file")
                return data
    except Exception as e:
        logger.warning(f"Failed to load papers from file: {e}")
    return {}


def save_papers_storage(storage: Dict[str, Dict]) -> None:
    """保存论文存储到文件"""
    try:
        with open(PAPERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(storage, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Failed to save papers to file: {e}")


def load_literature_storage() -> Dict[str, Dict]:
    """从文件加载文献存储"""
    try:
        if os.path.exists(LITERATURE_FILE):
            with open(LITERATURE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load literature from file: {e}")
    return {}


def save_literature_storage(storage: Dict[str, Dict]) -> None:
    """保存文献存储到文件"""
    try:
        with open(LITERATURE_FILE, 'w', encoding='utf-8') as f:
            json.dump(storage, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Failed to save literature to file: {e}")


# In-memory storage with file persistence
PAPERS_STORAGE: Dict[str, Dict] = load_papers_storage()
LITERATURE_STORAGE: Dict[str, Dict] = load_literature_storage()
SETTINGS_STORAGE: Dict[str, Any] = {
    "language": "zh-CN",
    "theme": "light",
    "autoSave": True,
    "autoSaveInterval": 30,
    "defaultCitationStyle": "apa",
    "defaultModel": "gpt-4",
    "keywords": [
        "machine learning",
        "deep learning",
        "natural language processing",
        "computer vision",
        "artificial intelligence"
    ],
    "sources": ["arxiv", "pubmed", "semantic_scholar", "openalex", "crossref", "base"],  # 默认全部启用
}

# Chat session context storage: {(user_id, session_id): [messages]}
# Each message: {"role": "user"/"assistant", "content": "...", "reasoning": "..." (optional)}
CHAT_SESSIONS: Dict[tuple, List[Dict]] = {}


def get_paper_or_404(paper_id: str) -> Optional[Dict]:
    """Get paper by ID or return None"""
    return PAPERS_STORAGE.get(paper_id)


def get_literature_or_404(lit_id: str) -> Optional[Dict]:
    """Get literature by ID or return None"""
    return LITERATURE_STORAGE.get(lit_id)


# Paper CRUD endpoints
async def list_papers(request: web.Request) -> web.Response:
    """GET /papers - List all papers"""
    try:
        page = int(request.query.get("page", 1))
        page_size = int(request.query.get("pageSize", 10))
        status = request.query.get("status")

        papers = list(PAPERS_STORAGE.values())
        if status:
            papers = [p for p in papers if p.get("status") == status]

        # Pagination
        start = (page - 1) * page_size
        end = start + page_size
        paginated = papers[start:end]

        return web.json_response({
            "success": True,
            "data": paginated,
            "total": len(papers),
            "page": page,
            "pageSize": page_size,
        })
    except Exception as e:
        logger.error(f"List papers error: {e}")
        return web.json_response({
            "success": False,
            "error": str(e)
        }, status=500)


async def create_paper(request: web.Request) -> web.Response:
    """POST /papers - Create a new paper"""
    try:
        # Always read content first to handle encoding issues
        body = await request.content.read()
        body_text = body.decode('utf-8', errors='ignore')
        import json
        try:
            data = json.loads(body_text) if body_text else {}
        except json.JSONDecodeError:
            data = {}
        paper_id = str(uuid.uuid4())

        paper = {
            "id": paper_id,
            "title": data.get("title", "Untitled Paper"),
            "topic": data.get("topic", ""),
            "outline": data.get("outline", []),
            "content": data.get("content", ""),
            "status": "draft",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "literature_ids": [],
            "versions": [],
        }

        PAPERS_STORAGE[paper_id] = paper
        save_papers_storage(PAPERS_STORAGE)
        logger.info(f"Created paper {paper_id}, total papers: {len(PAPERS_STORAGE)}")

        return web.json_response({
            "success": True,
            "data": paper,
        }, status=201)
    except Exception as e:
        logger.error(f"Create paper error: {e}")
        return web.json_response({
            "success": False,
            "error": str(e)
        }, status=500)


async def get_paper(request: web.Request) -> web.Response:
    """GET /papers/{id} - Get paper by ID"""
    try:
        paper_id = request.match_info["id"]
        paper = get_paper_or_404(paper_id)

        if not paper:
            return web.json_response({
                "success": False,
                "error": "Paper not found"
            }, status=404)

        return web.json_response({
            "success": True,
            "data": paper,
        })
    except Exception as e:
        logger.error(f"Get paper error: {e}")
        return web.json_response({
            "success": False,
            "error": str(e)
        }, status=500)


async def update_paper(request: web.Request) -> web.Response:
    """PUT /papers/{id} - Update paper"""
    try:
        paper_id = request.match_info["id"]
        paper = get_paper_or_404(paper_id)

        if not paper:
            return web.json_response({
                "success": False,
                "error": "Paper not found"
            }, status=404)

        data = await request.json()

        # Update fields
        if "title" in data:
            paper["title"] = data["title"]
        if "topic" in data:
            paper["topic"] = data["topic"]
        if "outline" in data:
            paper["outline"] = data["outline"]
        if "content" in data:
            paper["content"] = data["content"]
        if "status" in data:
            paper["status"] = data["status"]

        paper["updated_at"] = datetime.now().isoformat()

        save_papers_storage(PAPERS_STORAGE)
        logger.info(f"Updated paper {paper_id}")

        return web.json_response({
            "success": True,
            "data": paper,
        })
    except Exception as e:
        logger.error(f"Update paper error: {e}")
        return web.json_response({
            "success": False,
            "error": str(e)
        }, status=500)


async def delete_paper(request: web.Request) -> web.Response:
    """DELETE /papers/{id} - Delete paper"""
    try:
        paper_id = request.match_info["id"]

        if paper_id not in PAPERS_STORAGE:
            return web.json_response({
                "success": False,
                "error": "Paper not found"
            }, status=404)

        del PAPERS_STORAGE[paper_id]
        save_papers_storage(PAPERS_STORAGE)
        logger.info(f"Deleted paper {paper_id}, remaining papers: {len(PAPERS_STORAGE)}")

        return web.json_response({
            "success": True,
            "message": "Paper deleted",
        })
    except Exception as e:
        logger.error(f"Delete paper error: {e}")
        return web.json_response({
            "success": False,
            "error": str(e)
        }, status=500)


# Paper outline endpoints
async def get_outline(request: web.Request) -> web.Response:
    """GET /papers/{id}/outline - Get paper outline"""
    try:
        paper_id = request.match_info["id"]
        paper = get_paper_or_404(paper_id)

        if not paper:
            return web.json_response({
                "success": False,
                "error": "Paper not found"
            }, status=404)

        return web.json_response({
            "success": True,
            "data": paper.get("outline", []),
        })
    except Exception as e:
        logger.error(f"Get outline error: {e}")
        return web.json_response({
            "success": False,
            "error": str(e)
        }, status=500)


async def generate_outline(request: web.Request) -> web.Response:
    """POST /papers/{id}/outline/generate - Generate paper outline"""
    try:
        paper_id = request.match_info["id"]
        paper = get_paper_or_404(paper_id)

        if not paper:
            return web.json_response({
                "success": False,
                "error": "Paper not found"
            }, status=404)

        data = await request.json()
        topic = data.get("topic", paper.get("topic", ""))

        # Use OutlineAgent to generate outline
        from src.agents_v2.paper_agents import OutlineAgent
        from src.agents_v2.paper_agents.base_paper_agent import LLMConfig

        llm_config = LLMConfig(
            provider="openai",
            model_name=os.getenv("LLM_MODEL", "MiniMax-M2.7"),
            temperature=0.7,
            api_key=DEFAULT_API_KEY,
            base_url=DEFAULT_BASE_URL
        )

        agent = OutlineAgent(llm_config)
        result = await agent.execute({"task_description": topic})

        if result.success:
            # Parse outline from result - OutlineAgent returns {"outline": {...}}
            result_data = result.result if isinstance(result.result, dict) else {}
            outline = result_data.get("outline", {})

            paper["outline"] = outline
            paper["updated_at"] = datetime.now().isoformat()

            return web.json_response({
                "success": True,
                "data": outline,
            })
        else:
            return web.json_response({
                "success": False,
                "error": result.error
            }, status=500)

    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logger.error(f"Generate outline error: {e}\n{tb}")
        # 检查是否是 agent 返回的 fallback（即 LLM 调用失败但 agent 返回了成功）
        return web.json_response({
            "success": False,
            "error": f"大纲生成失败: {str(e)}"
        }, status=500)


# Content generation endpoint
async def generate_content(request: web.Request) -> web.Response:
    """POST /papers/{id}/sections/{sectionId}/generate - Generate section content"""
    try:
        paper_id = request.match_info["id"]
        section_id = request.match_info["sectionId"]

        paper = get_paper_or_404(paper_id)
        if not paper:
            return web.json_response({
                "success": False,
                "error": "Paper not found"
            }, status=404)

        data = await request.json()
        prompt = data.get("prompt", "")

        # 获取章节信息
        sections = paper.get("sections", []) or paper.get("outline", [])
        section_title = section_id
        section_content = ""

        for s in sections:
            if s.get("id") == section_id:
                section_title = s.get("title", section_id)
                section_content = s.get("content", "")
                break

        # 使用 DraftWriterAgent 生成内容
        from src.agents_v2.paper_agents import DraftWriterAgent
        from src.agents_v2.paper_agents.base_paper_agent import LLMConfig

        llm_config = LLMConfig(
            provider="openai",
            model_name=os.getenv("LLM_MODEL", "MiniMax-M2.7"),
            temperature=0.7,
            api_key=DEFAULT_API_KEY,
            base_url=DEFAULT_BASE_URL
        )

        agent = DraftWriterAgent(llm_config)

        # 构建 outline 格式（按照 Agent 期望的格式）
        chapters = []
        for s in sections:
            chapters.append({
                "name": s.get("title", "未命名章节"),
                "main_points": [],
                "citations_needed": [],
                "depends_on": None
            })

        outline = {"chapters": chapters}

        # 调用 Agent（使用 context 传递参数）
        result = await agent.execute(
            input_data={"outline": outline, "section": section_title},
            context={
                "outline": outline,
                "thesis_statement": paper.get("title", ""),
                "literature_result": {}
            }
        )

        if result.success:
            # 从 result 中提取内容
            content = ""
            if isinstance(result.result, dict):
                if "full_draft" in result.result:
                    content = result.result.get("full_draft", "")
                elif "content" in result.result:
                    content = result.result.get("content", "")
                else:
                    content = str(result.result)
            else:
                content = str(result.result)

            return web.json_response({
                "success": True,
                "data": {"content": content, "section_id": section_id},
            })
        else:
            logger.error(f"Agent execution failed: {result.error}")
            return web.json_response({
                "success": False,
                "error": result.error or "Agent执行失败"
            }, status=500)

    except Exception as e:
        logger.error(f"Generate content error: {e}")
        return web.json_response({
            "success": False,
            "error": str(e)
        }, status=500)


async def format_content(request: web.Request) -> web.Response:
    """POST /papers/{id}/sections/{sectionId}/format - 修正格式（公式和格式）"""
    from src.agents_v2.monitoring.chain_tracer import chain_trace, ChainPhase, ChainStatus

    # 创建链路追踪上下文
    trace_ctx = None
    span_info = {}

    try:
        paper_id = request.match_info["id"]
        section_id = request.match_info["sectionId"]

        # 启动链路追踪
        from src.agents_v2.monitoring.chain_tracer import get_chain_tracer
        tracer = get_chain_tracer()
        trace_ctx = tracer.start_trace()

        # 创建输入处理span
        input_span = trace_ctx.create_span(
            phase=ChainPhase.INPUT,
            operation="parse_format_request",
            input_data={
                "paper_id": paper_id,
                "section_id": section_id,
                "content_length": len(section_id)  # placeholder
            }
        )

        logger.info(f"[FORMAT_REQUEST] paper_id={paper_id}, section_id={section_id}")

        # 手动解析JSON，避免编码问题
        body = await request.content.read()
        body_text = body.decode('utf-8', errors='ignore')
        try:
            data = json.loads(body_text) if body_text else {}
        except json.JSONDecodeError:
            data = {}

        # 记录原始数据长度
        input_span.add_attribute("body_length", len(body))
        input_span.add_attribute("body_text_length", len(body_text))
        input_span.add_attribute("data_keys", list(data.keys()))

        provided_content = data.get("content", "")
        input_span.add_attribute("provided_content_length", len(provided_content))
        input_span.add_attribute("provided_content_preview", provided_content[:100] if provided_content else "EMPTY")
        input_span.add_attribute("raw_body_hex", body.hex()[:100] if body else "EMPTY")
        input_span.add_attribute("body_text_preview", body_text[:100] if body_text else "EMPTY")
        logger.info(f"[FORMAT_REQUEST] provided_content_length={len(provided_content)}, preview={provided_content[:50] if provided_content else 'EMPTY'}")
        logger.info(f"[FORMAT_REQUEST] raw_body_hex={body.hex()[:80]}")

        trace_ctx.finish_span(input_span.span_id)

        # 创建获取论文span
        fetch_span = trace_ctx.create_span(
            phase=ChainPhase.RETRIEVAL,
            operation="fetch_paper",
            input_data={"paper_id": paper_id}
        )

        # 尝试获取论文，但即使论文不存在，只要有content就可以处理
        paper = get_paper_or_404(paper_id)
        fetch_span.add_attribute("paper_found", paper is not None)
        fetch_span.add_attribute("has_sections", bool(paper.get("sections") if paper else False))
        logger.info(f"[FORMAT_REQUEST] paper_id={paper_id}, found={paper is not None}")

        trace_ctx.finish_span(fetch_span.span_id)

        if not paper and not provided_content:
            return web.json_response({
                "success": False,
                "error": "论文不存在或已过期，请刷新页面后重试。如果问题持续，请新建论文后重试。"
            }, status=404)

        # 创建章节查找span
        section_span = trace_ctx.create_span(
            phase=ChainPhase.RETRIEVAL,
            operation="find_section",
            input_data={"section_id": section_id}
        )

        # 获取章节信息
        section_title = section_id
        section_content = ""

        if paper:
            sections = paper.get("sections", []) or paper.get("outline", [])
            section_span.add_attribute("total_sections", len(sections))
            for s in sections:
                if s.get("id") == section_id:
                    section_title = s.get("title", section_id)
                    section_content = s.get("content", "")
                    break

        section_span.add_attribute("section_title", section_title)
        section_span.add_attribute("section_content_length", len(section_content))
        logger.info(f"[FORMAT_REQUEST] section_id={section_id}, title={section_title}, content_length={len(section_content)}")

        trace_ctx.finish_span(section_span.span_id)

        # 如果章节内容为空但提供了content参数，使用提供的content
        if not section_content and provided_content:
            section_content = provided_content
            logger.info(f"[FORMAT_REQUEST] Using provided content instead, length={len(section_content)}")

        # 如果仍然没有内容，返回错误
        if not section_content:
            tracer.end_trace(ChainStatus.FAILED)
            return web.json_response({
                "success": False,
                "error": "章节内容为空"
            }, status=400)

        # 创建LLM调用span
        llm_span = trace_ctx.create_span(
            phase=ChainPhase.GENERATION,
            operation="language_polish",
            input_data={
                "text_length": len(section_content),
                "language": "zh",
                "polish_level": "medium"
            }
        )

        # 直接调用 LanguagePolisherAgent 修正格式（使用writing中的融合版）
        from src.agents_v2.writing import LanguagePolisherAgent
        from src.agents_v2.paper_agents.base_paper_agent import LLMConfig

        llm_config = LLMConfig(
            provider="openai",
            model_name=os.getenv("LLM_MODEL", "MiniMax-M2.7"),
            temperature=0.3,
            api_key=DEFAULT_API_KEY,
            base_url=DEFAULT_BASE_URL
        )

        try:
            agent = LanguagePolisherAgent(llm_config)
            # 使用diagnose方法进行诊断和润色
            result = await agent.diagnose({
                "text": section_content,
                "language": "zh",
                "domain": ""
            })

            llm_span.add_attribute("result_success", result.success)
            if result.error:
                llm_span.add_attribute("result_error", result.error)

            trace_ctx.finish_span(llm_span.span_id)

            if result.success and result.result:
                corrected_content = result.result.get("polished_text", section_content)
                logger.info(f"[FORMAT_REQUEST] Success, corrected_content_length={len(corrected_content)}")

                tracer.end_trace(ChainStatus.COMPLETED)
                return web.json_response({
                    "success": True,
                    "data": {
                        "content": corrected_content,
                        "section_id": section_id
                    },
                })
            else:
                logger.warning(f"[FORMAT_REQUEST] Agent failed: {result.error}")
                tracer.end_trace(ChainStatus.FAILED)
                return web.json_response({
                    "success": False,
                    "error": result.error or "格式修正失败"
                }, status=500)
        except Exception as llm_error:
            llm_span.set_error(llm_error)
            trace_ctx.finish_span(llm_span.span_id)
            logger.error(f"[FORMAT_REQUEST] LanguagePolisherAgent exception: {llm_error}")
            tracer.end_trace(ChainStatus.FAILED)
            return web.json_response({
                "success": False,
                "error": f"格式修正失败: {str(llm_error)}"
            }, status=500)

    except Exception as e:
        logger.error(f"[FORMAT_REQUEST] Unexpected error: {e}", exc_info=True)
        if trace_ctx:
            trace_ctx.finish(error=Exception(str(e)))
            tracer.end_trace(ChainStatus.FAILED)
        return web.json_response({
            "success": False,
            "error": str(e)
        }, status=500)


# Literature endpoints
async def search_literature(request: web.Request) -> web.Response:
    """POST /literature/search - Search literature"""
    try:
        data = await request.json()
        query = data.get("query", "")

        # Use PaperSearchAgent to search
        from src.agents_v2.paper_search import PaperSearchAgent

        agent = PaperSearchAgent()
        page = data.get("page", 1)
        result = await agent.execute(query, {
            "max_results": data.get("max_results", 10),
            "page": page,
        })

        papers = result.get("papers", []) if isinstance(result, dict) else []

        return web.json_response({
            "success": True,
            "data": papers,
            "total": len(papers),
        })

    except Exception as e:
        logger.error(f"Search literature error: {e}")
        return web.json_response({
            "success": False,
            "error": str(e)
        }, status=500)


async def get_literature(request: web.Request) -> web.Response:
    """GET /literature/{id} - Get literature details"""
    try:
        lit_id = request.match_info["id"]
        literature = get_literature_or_404(lit_id)

        if not literature:
            return web.json_response({
                "success": False,
                "error": "Literature not found"
            }, status=404)

        return web.json_response({
            "success": True,
            "data": literature,
        })
    except Exception as e:
        logger.error(f"Get literature error: {e}")
        return web.json_response({
            "success": False,
            "error": str(e)
        }, status=500)


async def add_literature(request: web.Request) -> web.Response:
    """POST /papers/{paperId}/literature - Add literature to paper"""
    try:
        paper_id = request.match_info["paperId"]
        paper = get_paper_or_404(paper_id)

        if not paper:
            return web.json_response({
                "success": False,
                "error": "Paper not found"
            }, status=404)

        data = await request.json()
        lit_id = str(uuid.uuid4())

        literature = {
            "id": lit_id,
            "title": data.get("title", ""),
            "authors": data.get("authors", ""),
            "year": data.get("year", ""),
            "journal": data.get("journal", ""),
            "abstract": data.get("abstract", ""),
            "url": data.get("url", ""),
            "cited": False,
            "added_at": datetime.now().isoformat(),
        }

        LITERATURE_STORAGE[lit_id] = literature
        paper.setdefault("literature_ids", []).append(lit_id)

        return web.json_response({
            "success": True,
            "data": literature,
        }, status=201)

    except Exception as e:
        logger.error(f"Add literature error: {e}")
        return web.json_response({
            "success": False,
            "error": str(e)
        }, status=500)


async def get_citation(request: web.Request) -> web.Response:
    """GET /literature/{id}/citation - Get citation format"""
    try:
        lit_id = request.match_info["id"]
        literature = get_literature_or_404(lit_id)
        style = request.query.get("style", "apa")

        if not literature:
            return web.json_response({
                "success": False,
                "error": "Literature not found"
            }, status=404)

        # Generate citation based on style
        authors = literature.get("authors", "")
        year = literature.get("year", "")
        title = literature.get("title", "")
        journal = literature.get("journal", "")

        if style == "apa":
            citation = f"{authors} ({year}). {title}. {journal}."
        elif style == "mla":
            citation = f"{authors}. \"{title}.\" {journal}, {year}."
        elif style == "ieee":
            citation = f"{authors}, \"{title},\" {journal}, {year}."
        else:
            citation = f"{authors}. {title}. {journal}, {year}."

        return web.json_response({
            "success": True,
            "data": {"citation": citation, "style": style},
        })

    except Exception as e:
        logger.error(f"Get citation error: {e}")
        return web.json_response({
            "success": False,
            "error": str(e)
        }, status=500)


# Knowledge Graph endpoints
async def get_literature_graph(request: web.Request) -> web.Response:
    """GET /api/knowledge-graph/literature - Get knowledge graph for all literature"""
    try:
        # 获取所有文献的图谱数据
        graph_data = {
            "nodes": [],
            "edges": [],
            "stats": {
                "totalEntities": 0,
                "totalRelations": 0,
                "entityTypes": {}
            }
        }

        # 从literature存储构建简单图谱
        for lit_id, lit in LITERATURE_STORAGE.items():
            # 添加文献节点
            graph_data["nodes"].append({
                "id": lit_id,
                "label": lit.get("title", "Untitled")[:50],
                "type": "paper",
                "data": {
                    "title": lit.get("title", ""),
                    "authors": lit.get("authors", ""),
                    "year": lit.get("year", ""),
                    "journal": lit.get("journal", "")
                }
            })

            # 提取关键词作为实体节点（简化处理）
            keywords = lit.get("keywords", [])
            for kw in keywords[:5]:  # 最多5个关键词
                kw_id = f"kw_{kw}"
                if not any(n["id"] == kw_id for n in graph_data["nodes"]):
                    graph_data["nodes"].append({
                        "id": kw_id,
                        "label": kw,
                        "type": "keyword"
                    })

                # 添加连接边
                graph_data["edges"].append({
                    "source": lit_id,
                    "target": kw_id,
                    "relation": "related_to"
                })

        # 统计
        node_types = {}
        for n in graph_data["nodes"]:
            t = n["type"]
            node_types[t] = node_types.get(t, 0) + 1
        graph_data["stats"]["totalEntities"] = len(graph_data["nodes"])
        graph_data["stats"]["totalRelations"] = len(graph_data["edges"])
        graph_data["stats"]["entityTypes"] = node_types

        return web.json_response({
            "success": True,
            "data": graph_data
        })

    except Exception as e:
        logger.error(f"Get literature graph error: {e}")
        return web.json_response({
            "success": False,
            "error": str(e)
        }, status=500)


async def generate_literature_graph(request: web.Request) -> web.Response:
    """POST /api/knowledge-graph/generate - Generate knowledge graph from literature"""
    try:
        body = await request.content.read()
        body_text = body.decode('utf-8', errors='ignore')
        try:
            data = json.loads(body_text) if body_text else {}
        except json.JSONDecodeError:
            data = {}

        literature_ids = data.get("literatureIds", [])

        # 使用已存储的文献生成图谱
        graph_data = {
            "nodes": [],
            "edges": [],
            "generated": True,
            "timestamp": datetime.now().isoformat()
        }

        # 为每篇文献创建节点和关系
        for i, lit_id in enumerate(literature_ids):
            lit = LITERATURE_STORAGE.get(lit_id)
            if not lit:
                continue

            lit_node_id = f"lit_{lit_id}"
            title = lit.get("title", "")[:50]

            # 文献节点
            graph_data["nodes"].append({
                "id": lit_node_id,
                "label": title,
                "type": "paper",
                "data": lit
            })

            # 方法/数据集节点（从摘要提取）
            abstract = lit.get("abstract", "")
            if abstract:
                # 简单提取词汇作为实体（实际应该用NLP）
                words = abstract.split()[:10]
                for j, word in enumerate(words):
                    if len(word) > 4:
                        node_id = f"{lit_node_id}_entity_{j}"
                        graph_data["nodes"].append({
                            "id": node_id,
                            "label": word,
                            "type": "concept"
                        })
                        graph_data["edges"].append({
                            "source": lit_node_id,
                            "target": node_id,
                            "relation": "contains"
                        })

        return web.json_response({
            "success": True,
            "data": graph_data
        })

    except Exception as e:
        logger.error(f"Generate literature graph error: {e}")
        return web.json_response({
            "success": False,
            "error": str(e)
        }, status=500)


async def get_entity_relations(request: web.Request) -> web.Response:
    """GET /api/knowledge-graph/entity/{entityId} - Get relations for an entity"""
    try:
        entity_id = request.match_info.get("entityId")

        # 简化：返回该实体的直接关联
        relations = []

        # 查找所有边
        for lit_id, lit in LITERATURE_STORAGE.items():
            if entity_id in [lit_id, f"lit_{lit_id}"]:
                relations.append({
                    "source": entity_id,
                    "target": lit.get("title", "")[:50],
                    "relation": "same_paper"
                })

        return web.json_response({
            "success": True,
            "data": {
                "entityId": entity_id,
                "relations": relations,
                "count": len(relations)
            }
        })

    except Exception as e:
        logger.error(f"Get entity relations error: {e}")
        return web.json_response({
            "success": False,
            "error": str(e)
        }, status=500)


# Literature file upload endpoint
async def upload_literature_file(request: web.Request) -> web.Response:
    """POST /api/literature/upload - Upload and extract metadata from a literature file"""
    try:
        # 获取上传的文件
        reader = await request.multipart()
        field = await reader.next()

        if not field or field.name != 'file':
            return web.json_response({
                "success": False,
                "error": "No file field found"
            }, status=400)

        filename = field.filename
        file_content = await field.read()

        # 根据文件扩展名处理
        file_ext = os.path.splitext(filename)[1].lower() if filename else ""

        # 提取文件名的基本信息作为提示
        name_from_file = os.path.splitext(filename)[0] if filename else ""

        # 使用LLM从文件名和内容提取元数据
        try:
            from openai import OpenAI

            client = OpenAI(
                api_key=DEFAULT_API_KEY,
                base_url=DEFAULT_BASE_URL if DEFAULT_BASE_URL else "https://api.minimax.chat/v1"
            )

            # 构建提示
            prompt = f"""请从以下论文信息中提取元数据，返回JSON格式：
文件名: {filename or '未知'}
文件内容摘要: {file_content[:500] if file_content else '无内容'}

请提取以下信息（如果无法提取则返回空字符串）：
- title: 论文标题
- authors: 作者（多个作者用逗号分隔）
- year: 年份（4位数字）
- journal: 期刊/会议名称
- abstract: 摘要（如果有）

只返回JSON，不要其他内容。"""

            response = client.chat.completions.create(
                model=os.getenv("LLM_MODEL", "MiniMax-M2.7"),
                messages=[{"role": "user", "content": prompt}],
                extra_body={"reasoning_split": True}
            )

            content = response.choices[0].message.content or ""

            # 尝试解析JSON
            import re
            json_match = re.search(r'\{[^}]+\}', content, re.DOTALL)
            if json_match:
                metadata = json.loads(json_match.group())
            else:
                metadata = {}

        except Exception as llm_error:
            logger.warning(f"LLM extraction failed: {llm_error}, using filename only")
            metadata = {"title": name_from_file or "未命名论文"}

        # 创建文献记录
        lit_id = str(uuid.uuid4())
        literature = {
            "id": lit_id,
            "title": metadata.get("title", name_from_file or "未命名论文"),
            "authors": metadata.get("authors", ""),
            "year": metadata.get("year", ""),
            "journal": metadata.get("journal", ""),
            "abstract": metadata.get("abstract", ""),
            "cited": False,
            "added_at": datetime.now().isoformat(),
            "file_name": filename,
            "file_size": len(file_content),
        }

        LITERATURE_STORAGE[lit_id] = literature

        return web.json_response({
            "success": True,
            "data": literature,
        }, status=201)

    except Exception as e:
        logger.error(f"Upload literature error: {e}")
        return web.json_response({
            "success": False,
            "error": str(e)
        }, status=500)


# Chat endpoint
async def chat(request: web.Request) -> web.Response:
    """POST /papers/{paperId}/chat - Send chat message with context maintenance

    Request body:
    {
        "user_id": "string",
        "session_id": "string",
        "message": "string"
    }
    """
    data = None
    try:
        # 手动解析JSON，避免aiohttp的编码问题
        body = await request.content.read()
        body_text = body.decode('utf-8', errors='ignore')
        import json
        data = json.loads(body_text) if body_text else {}
        message = data.get("message", "")
        user_id = data.get("user_id", "default_user")
        session_id = data.get("session_id", "default_session")

        if not message:
            return web.json_response({
                "success": False,
                "error": "Message is required"
            }, status=400)

        # 获取或创建会话上下文
        session_key = (user_id, session_id)
        if session_key not in CHAT_SESSIONS:
            CHAT_SESSIONS[session_key] = []

        messages_context = CHAT_SESSIONS[session_key]

        # 添加用户消息到上下文
        messages_context.append({
            "role": "user",
            "content": message
        })

        # 直接调用LLM，使用reasoning_split=True
        try:
            from openai import OpenAI

            client = OpenAI(
                api_key=DEFAULT_API_KEY,
                base_url=DEFAULT_BASE_URL if DEFAULT_BASE_URL else "https://api.minimax.chat/v1"
            )

            # 构建消息历史
            system_prompt = "你是一个友好的AI写作助手。请用中文回答用户的问题。"
            api_messages = [{"role": "system", "content": system_prompt}] + messages_context

            # 调用API，禁用reasoning_split避免星号包裹的思考过程
            response = client.chat.completions.create(
                model=os.getenv("LLM_MODEL", "MiniMax-M2.7"),
                messages=api_messages,
                extra_body={"reasoning_split": False}
            )

            # 提取回复内容（不含think）
            reasoning_details = ""
            content = response.choices[0].message.content or ""

            if hasattr(response.choices[0].message, 'reasoning_details') and \
               response.choices[0].message.reasoning_details:
                reasoning_details = response.choices[0].message.reasoning_details[0].get('text', '')

            # 保存完整上下文（包含reasoning）
            messages_context.append({
                "role": "assistant",
                "content": content,
                "reasoning": reasoning_details
            })

            # 限制上下文长度（最多保存20条）
            if len(messages_context) > 20:
                CHAT_SESSIONS[session_key] = messages_context[-20:]

            return web.json_response({
                "success": True,
                "data": {
                    "message": message,
                    "response": content,
                    "agent": "SimpleChatAgent",
                    "messages": [{"role": m["role"], "content": m["content"]} for m in messages_context],
                },
            })

        except Exception as llm_error:
            # 调用失败时移除刚添加的用户消息
            if messages_context and messages_context[-1].get("role") == "user":
                messages_context.pop()

            logger.warning(f"LLM call failed: {llm_error}, returning friendly response")
            return web.json_response({
                "success": True,
                "data": {
                    "message": message,
                    "response": f"收到您的消息！\n\n当前AI服务暂时不可用（{type(llm_error).__name__}），请稍后再试。",
                    "agent": "SimpleChatAgent",
                },
            })

    except (UnicodeDecodeError, UnicodeEncodeError) as decode_err:
        import traceback
        logger.error(f"Unicode error in chat: {decode_err}\n{traceback.format_exc()}")
        return web.json_response({
            "success": True,
            "data": {
                "message": data.get("message", "") if data else "",
                "response": "收到您的消息！当前AI服务暂时不可用，请稍后再试。",
                "agent": "SimpleChatAgent",
            },
        })

    except Exception as e:
        logger.error(f"Chat error: {e}")
        return web.json_response({
            "success": True,
            "data": {
                "message": data.get("message", "") if data else "",
                "response": "抱歉，发生了未知错误。请刷新页面重试。",
                "agent": "SimpleChatAgent",
            },
        })


# Chat history endpoint
async def get_chat_history(request: web.Request) -> web.Response:
    """GET /papers/{paperId}/chat/history?user_id=xxx&session_id=xxx - Get chat history"""
    try:
        paper_id = request.match_info["paperId"]
        user_id = request.query.get("user_id", "default_user")
        session_id = request.query.get("session_id", paper_id or "default_session")

        session_key = (user_id, session_id)
        messages = CHAT_SESSIONS.get(session_key, [])

        # 返回不含reasoning的消息
        clean_messages = [{"role": m["role"], "content": m["content"]} for m in messages]

        return web.json_response({
            "success": True,
            "data": {
                "messages": clean_messages,
                "count": len(clean_messages),
            },
        })
    except Exception as e:
        logger.error(f"Get chat history error: {e}")
        return web.json_response({
            "success": False,
            "error": str(e)
        }, status=500)


# Settings endpoints
async def get_settings(request: web.Request) -> web.Response:
    """GET /settings - Get user settings"""
    return web.json_response({
        "success": True,
        "data": SETTINGS_STORAGE,
    })


async def update_settings(request: web.Request) -> web.Response:
    """PUT /settings - Update user settings"""
    try:
        data = await request.json()

        SETTINGS_STORAGE.update(data)

        return web.json_response({
            "success": True,
            "data": SETTINGS_STORAGE,
        })
    except Exception as e:
        logger.error(f"Update settings error: {e}")
        return web.json_response({
            "success": False,
            "error": str(e)
        }, status=500)


# Paper file upload endpoint
async def upload_paper_file(request: web.Request) -> web.Response:
    """POST /api/papers/upload - Upload and parse an existing paper file"""
    try:
        reader = await request.multipart()
        field = await reader.next()

        if not field:
            return web.json_response({
                "success": False,
                "error": "No file field found"
            }, status=400)

        filename = field.filename
        file_content = await field.read()
        file_ext = os.path.splitext(filename)[1].lower() if filename else ""

        # Parse content based on file type
        content = ""
        title = os.path.splitext(filename)[0] if filename else "未命名论文"
        outline = []

        if file_ext == '.md':
            # Markdown: try to extract title from first heading and outline from subsequent headings
            try:
                text = file_content.decode('utf-8', errors='ignore')
                content = text
                # Extract title from first # heading
                import re
                match = re.search(r'^#\s+(.+)$', text, re.MULTILINE)
                if match:
                    title = match.group(1).strip()

                # Extract outline from ## and ### headings
                heading_pattern = re.compile(r'^(#{2,3})\s+(.+)$', re.MULTILINE)
                for match in heading_pattern.finditer(text):
                    level = len(match.group(1))
                    heading_text = match.group(2).strip()
                    section_id = str(uuid.uuid4())[:8]
                    outline.append({
                        "id": section_id,
                        "title": heading_text,
                        "level": level,
                        "content": ""
                    })
            except Exception:
                content = file_content.decode('utf-8', errors='ignore')

        elif file_ext == '.txt':
            content = file_content.decode('utf-8', errors='ignore')
            # First line as title
            lines = content.split('\n')
            if lines:
                title = lines[0].strip()[:100]
                content = '\n'.join(lines[1:])

        elif file_ext in ['.pdf', '.docx']:
            # For binary formats, store as base64 or just indicate file exists
            # In production, use proper parsers like PyPDF2 or python-docx
            content = f"[文件已上传: {filename}]"
            try:
                # Try to extract text (basic approach)
                if file_ext == '.pdf':
                    # Basic PDF text extraction - in production use PyPDF2
                    content = f"[PDF文件已上传: {filename}, 大小: {len(file_content)} bytes]\n\n建议使用Markdown格式上传以获得更好的编辑体验。"
            except Exception:
                pass

        else:
            # Default: try UTF-8 decode
            try:
                content = file_content.decode('utf-8', errors='ignore')
            except Exception:
                content = f"[文件已上传: {filename}]"

        # Create paper with parsed content
        paper_id = str(uuid.uuid4())
        paper = {
            "id": paper_id,
            "title": title,
            "topic": "",
            "outline": outline,
            "sections": outline,
            "content": content,
            "status": "draft",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "literature_ids": [],
            "versions": [],
            "file_name": filename,
            "file_size": len(file_content),
        }

        PAPERS_STORAGE[paper_id] = paper

        return web.json_response({
            "success": True,
            "data": paper,
        }, status=201)

    except Exception as e:
        logger.error(f"Upload paper error: {e}")
        return web.json_response({
            "success": False,
            "error": str(e)
        }, status=500)


# Models endpoint
async def get_available_models(request: web.Request) -> web.Response:
    """GET /api/models - Get list of available LLM models"""
    try:
        from src.agents_v2.core.config import (
            get_all_models,
            get_default_model,
            MODEL_CATEGORIES,
            SUPPORTED_MODELS,
        )

        return web.json_response({
            "success": True,
            "data": {
                "models": get_all_models(),
                "categories": MODEL_CATEGORIES,
                "default_model": get_default_model(),
            },
        })
    except Exception as e:
        logger.error(f"Get models error: {e}")
        return web.json_response({
            "success": False,
            "error": str(e)
        }, status=500)


# ---- SSE Streaming Endpoints ----

async def generate_outline_stream(request: web.Request) -> web.StreamResponse:
    """POST /papers/{id}/outline/generate/stream - Generate outline with SSE streaming"""
    from .sse_helper import SSEResponse

    sse = SSEResponse(request)
    await sse.start()

    try:
        paper_id = request.match_info["id"]
        paper = get_paper_or_404(paper_id)

        if not paper:
            await sse.send_error("Paper not found")
            return sse

        body = await request.content.read()
        body_text = body.decode('utf-8', errors='ignore')
        try:
            data = json.loads(body_text) if body_text else {}
        except json.JSONDecodeError:
            data = {}

        topic = data.get("topic", paper.get("topic", ""))
        await sse.send_phase("outline", "start", f"正在生成大纲: {topic[:50]}")

        from src.agents_v2.paper_agents import OutlineAgent
        from src.agents_v2.paper_agents.base_paper_agent import LLMConfig

        llm_config = LLMConfig(
            provider="openai",
            model_name=os.getenv("LLM_MODEL", "MiniMax-M2.7"),
            temperature=0.7,
            api_key=DEFAULT_API_KEY,
            base_url=DEFAULT_BASE_URL
        )

        agent = OutlineAgent(llm_config)
        result = await agent.execute({"task_description": topic})

        if result.success:
            result_data = result.result if isinstance(result.result, dict) else {}
            outline = result_data.get("outline", {})
            paper["outline"] = outline
            paper["updated_at"] = datetime.now().isoformat()
            save_papers_storage(PAPERS_STORAGE)

            await sse.send_phase("outline", "complete", "大纲生成完成")
            await sse.send_complete({"success": True, "data": outline})
        else:
            await sse.send_error(result.error or "大纲生成失败")

    except Exception as e:
        logger.error(f"Generate outline stream error: {e}")
        await sse.send_error(str(e))

    return sse


async def generate_content_stream(request: web.Request) -> web.StreamResponse:
    """POST /papers/{id}/sections/{sectionId}/generate/stream - Generate content with SSE"""
    from .sse_helper import SSEResponse

    sse = SSEResponse(request)
    await sse.start()

    try:
        paper_id = request.match_info["id"]
        section_id = request.match_info["sectionId"]

        paper = get_paper_or_404(paper_id)
        if not paper:
            await sse.send_error("Paper not found")
            return sse

        body = await request.content.read()
        body_text = body.decode('utf-8', errors='ignore')
        try:
            data = json.loads(body_text) if body_text else {}
        except json.JSONDecodeError:
            data = {}

        prompt = data.get("prompt", "")
        sections = paper.get("sections", []) or paper.get("outline", [])
        section_title = section_id

        for s in sections:
            if s.get("id") == section_id:
                section_title = s.get("title", section_id)
                break

        await sse.send_phase("content", "start", f"正在生成: {section_title}")

        from src.agents_v2.paper_agents import DraftWriterAgent
        from src.agents_v2.paper_agents.base_paper_agent import LLMConfig

        llm_config = LLMConfig(
            provider="openai",
            model_name=os.getenv("LLM_MODEL", "MiniMax-M2.7"),
            temperature=0.7,
            api_key=DEFAULT_API_KEY,
            base_url=DEFAULT_BASE_URL
        )

        agent = DraftWriterAgent(llm_config)
        chapters = [{"name": s.get("title", "未命名"), "main_points": [], "citations_needed": [], "depends_on": None} for s in sections]
        outline = {"chapters": chapters}

        result = await agent.execute(
            input_data={"outline": outline, "section": section_title},
            context={"outline": outline, "thesis_statement": paper.get("title", ""), "literature_result": {}}
        )

        if result.success:
            content = ""
            if isinstance(result.result, dict):
                content = result.result.get("full_draft", "") or result.result.get("content", "") or str(result.result)
            else:
                content = str(result.result)

            # 分块发送内容模拟流式
            chunk_size = 50
            for i in range(0, len(content), chunk_size):
                await sse.send_token(content[i:i + chunk_size])
                await asyncio.sleep(0.02)

            await sse.send_phase("content", "complete", "内容生成完成")
            await sse.send_complete({"success": True, "data": {"content": content, "section_id": section_id}})
        else:
            await sse.send_error(result.error or "内容生成失败")

    except Exception as e:
        logger.error(f"Generate content stream error: {e}")
        await sse.send_error(str(e))

    return sse


async def chat_stream(request: web.Request) -> web.StreamResponse:
    """POST /papers/{paperId}/chat/stream - Chat with SSE streaming"""
    from .sse_helper import SSEResponse

    sse = SSEResponse(request)
    await sse.start()

    data = None
    try:
        paper_id = request.match_info["paperId"]
        body = await request.content.read()
        body_text = body.decode('utf-8', errors='ignore')
        data = json.loads(body_text) if body_text else {}
        message = data.get("message", "")
        user_id = data.get("user_id", "default_user")
        session_id = data.get("session_id", "default_session")

        if not message:
            await sse.send_error("Message is required")
            return sse

        session_key = (user_id, session_id)
        if session_key not in CHAT_SESSIONS:
            CHAT_SESSIONS[session_key] = []

        messages_context = CHAT_SESSIONS[session_key]
        messages_context.append({"role": "user", "content": message})

        await sse.send_phase("chat", "start", "正在思考...")

        try:
            from openai import OpenAI

            client = OpenAI(
                api_key=DEFAULT_API_KEY,
                base_url=DEFAULT_BASE_URL if DEFAULT_BASE_URL else "https://api.minimax.chat/v1"
            )

            system_prompt = "你是一个友好的AI写作助手。请用中文回答用户的问题。"
            api_messages = [{"role": "system", "content": system_prompt}] + messages_context

            # 尝试流式调用
            try:
                stream = client.chat.completions.create(
                    model=os.getenv("LLM_MODEL", "MiniMax-M2.7"),
                    messages=api_messages,
                    stream=True,
                    extra_body={"reasoning_split": False}
                )

                full_content = ""
                for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        token = chunk.choices[0].delta.content
                        full_content += token
                        await sse.send_token(token)

            except Exception:
                # 流式失败，降级到非流式
                response = client.chat.completions.create(
                    model=os.getenv("LLM_MODEL", "MiniMax-M2.7"),
                    messages=api_messages,
                    extra_body={"reasoning_split": False}
                )
                full_content = response.choices[0].message.content or ""
                # 分块发送
                for i in range(0, len(full_content), 20):
                    await sse.send_token(full_content[i:i + 20])
                    await asyncio.sleep(0.02)

            messages_context.append({"role": "assistant", "content": full_content})
            if len(messages_context) > 20:
                CHAT_SESSIONS[session_key] = messages_context[-20:]

            await sse.send_phase("chat", "complete", "回复完成")
            await sse.send_complete({
                "success": True,
                "data": {"message": message, "response": full_content}
            })

        except Exception as llm_error:
            if messages_context and messages_context[-1].get("role") == "user":
                messages_context.pop()
            logger.warning(f"LLM call failed in stream chat: {llm_error}")
            await sse.send_error(f"AI服务暂时不可用: {type(llm_error).__name__}")

    except Exception as e:
        logger.error(f"Chat stream error: {e}")
        await sse.send_error(str(e))

    return sse


async def format_content_stream(request: web.Request) -> web.StreamResponse:
    """POST /papers/{id}/sections/{sectionId}/format/stream - 修正格式（SSE 流式）"""
    from .sse_helper import SSEResponse

    sse = SSEResponse(request)
    await sse.start()

    try:
        paper_id = request.match_info["id"]
        section_id = request.match_info["sectionId"]

        body = await request.content.read()
        body_text = body.decode('utf-8', errors='ignore')
        try:
            data = json.loads(body_text) if body_text else {}
        except json.JSONDecodeError:
            data = {}

        provided_content = data.get("content", "")
        if not provided_content:
            await sse.send_error("content 不能为空")
            return sse

        await sse.send_phase("format", "start", "开始修正格式")

        try:
            from src.agents_v2.writing.smart_reviser import LanguagePolisherAgent

            # 获取 LLM 配置
            from src.agents_v2.core.config import LLMConfig
            llm_config = LLMConfig()
            agent = LanguagePolisherAgent(llm_config=llm_config)

            await sse.send_phase("format", "processing", "AI 正在修正格式...")

            result = await agent.execute(provided_content)

            if result and result.success:
                content = str(result.result)
                # 分块发送
                chunk_size = 50
                for i in range(0, len(content), chunk_size):
                    chunk = content[i:i + chunk_size]
                    await sse.send_token(chunk)
                    await asyncio.sleep(0.02)

                await sse.send_phase("format", "complete", "格式修正完成")
                await sse.send_complete({
                    "success": True,
                    "data": {"content": content, "section_id": section_id}
                })
            else:
                await sse.send_error(result.error or "格式修正失败")

        except Exception as e:
            logger.error(f"Format stream error: {e}")
            await sse.send_error(str(e))

    except Exception as e:
        logger.error(f"Format stream error: {e}")
        await sse.send_error(str(e))

    return sse


async def verify_citations(request: web.Request) -> web.Response:
    """POST /api/papers/{id}/citations/verify - 验证论文中的引用

    Request body:
        citations: [{"title": "...", "authors": [...], "year": "...", "doi": "..."}]

    Returns:
        验证结果报告
    """
    try:
        paper_id = request.match_info["id"]
        paper = get_paper_or_404(paper_id)

        data = await request.json()
        citations_data = data.get("citations", [])

        if not citations_data:
            # 从论文草稿中提取引用
            if paper and paper.get("draft"):
                import re
                draft = paper["draft"]
                citations_in_text = re.findall(r'\[(\d+(?:[,-]\d+)*)\]', draft)
                return web.json_response({
                    "success": True,
                    "data": {
                        "found_citations": len(citations_in_text),
                        "message": "请提供 citations 列表进行验证",
                    }
                })
            return web.json_response({
                "success": False,
                "error": "citations 列表为空"
            }, status=400)

        # 构建 Citation 对象
        from src.agents_v2.writing.citation_generator import Citation, CitationVerifier

        citations = []
        for c in citations_data:
            citations.append(Citation(
                authors=c.get("authors", []),
                year=str(c.get("year", "")),
                title=c.get("title", ""),
                journal=c.get("journal"),
                doi=c.get("doi"),
            ))

        # 批量验证
        verifier = CitationVerifier()
        results = await verifier.verify_batch(citations)
        report = verifier.generate_verification_report(results)

        return web.json_response({
            "success": True,
            "data": report,
        })

    except Exception as e:
        logger.error(f"Verify citations error: {e}")
        return web.json_response({
            "success": False,
            "error": str(e)
        }, status=500)


async def reflect_paper(request: web.Request) -> web.Response:
    """POST /api/papers/{id}/reflect - 对论文进行多层质量反思

    Request body (all optional):
        outline: 大纲数据
        sections: [{"title": "...", "content": "..."}]
        full_text: 完整文本

    Returns:
        多层反思结果
    """
    try:
        paper_id = request.match_info["id"]
        paper = get_paper_or_404(paper_id)

        data = await request.json() if request.content_length else {}

        outline = data.get("outline")
        sections_data = data.get("sections")
        full_text = data.get("full_text")

        # 如果没有提供数据，使用论文数据
        if not outline and paper:
            outline = paper.get("outline")
        if not full_text and paper:
            full_text = paper.get("draft")
        if not sections_data and paper:
            # 从草稿中提取章节
            if paper.get("draft"):
                import re
                parts = re.split(r'\n#{1,3}\s+', paper["draft"])
                if len(parts) > 1:
                    sections_data = []
                    for i, part in enumerate(parts[1:], 1):
                        title_end = part.find('\n')
                        if title_end > 0:
                            sections_data.append({
                                "title": part[:title_end].strip(),
                                "content": part[title_end:].strip(),
                            })

        from src.agents_v2.writing.reflection_engine import MultiLayerReflector

        reflector = MultiLayerReflector()

        sections = None
        if sections_data:
            sections = [(s["title"], s["content"]) for s in sections_data]

        result = await reflector.reflect_all(
            outline=outline,
            sections=sections,
            full_text=full_text,
        )

        return web.json_response({
            "success": True,
            "data": result.to_dict(),
        })

    except Exception as e:
        logger.error(f"Reflect paper error: {e}")
        return web.json_response({
            "success": False,
            "error": str(e)
        }, status=500)


def setup_paper_routes(app: web.Application):
    """Setup all paper-related routes"""
    # Paper CRUD
    app.router.add_get('/api/papers', list_papers)
    app.router.add_post('/api/papers', create_paper)
    app.router.add_get('/api/papers/{id}', get_paper)
    app.router.add_put('/api/papers/{id}', update_paper)
    app.router.add_delete('/api/papers/{id}', delete_paper)

    # Paper file upload
    app.router.add_post('/api/papers/upload', upload_paper_file)

    # Paper outline
    app.router.add_get('/api/papers/{id}/outline', get_outline)
    app.router.add_post('/api/papers/{id}/outline/generate', generate_outline)

    # Content generation
    app.router.add_post('/api/papers/{id}/sections/{sectionId}/generate', generate_content)

    # Format correction (修正格式)
    app.router.add_post('/api/papers/{id}/sections/{sectionId}/format', format_content)

    # Literature
    app.router.add_post('/api/literature/search', search_literature)
    app.router.add_get('/api/literature/{id}', get_literature)
    app.router.add_post('/api/papers/{paperId}/literature', add_literature)
    app.router.add_get('/api/literature/{id}/citation', get_citation)

    # Literature file upload
    app.router.add_post('/api/literature/upload', upload_literature_file)

    # Chat
    app.router.add_post('/api/papers/{paperId}/chat', chat)
    app.router.add_get('/api/papers/{paperId}/chat/history', get_chat_history)

    # SSE Streaming endpoints
    app.router.add_post('/api/papers/{id}/outline/generate/stream', generate_outline_stream)
    app.router.add_post('/api/papers/{id}/sections/{sectionId}/generate/stream', generate_content_stream)
    app.router.add_post('/api/papers/{paperId}/chat/stream', chat_stream)
    app.router.add_post('/api/papers/{id}/sections/{sectionId}/format/stream', format_content_stream)

    # Citation verification & reflection
    app.router.add_post('/api/papers/{id}/citations/verify', verify_citations)
    app.router.add_post('/api/papers/{id}/reflect', reflect_paper)

    # Settings
    app.router.add_get('/api/settings', get_settings)
    app.router.add_put('/api/settings', update_settings)

    # Models
    app.router.add_get('/api/models', get_available_models)
