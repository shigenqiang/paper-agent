"""
Paper API - RESTful API for Paper Agent Frontend

Provides CRUD operations for papers, literature, and writing sessions.
"""
import time
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

# In-memory storage for demo (replace with database in production)
PAPERS_STORAGE: Dict[str, Dict] = {}
LITERATURE_STORAGE: Dict[str, Dict] = {}
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
        logger.error(f"Generate outline error: {e}")
        # Return a default outline structure on error - must match DraftWriterAgent format
        default_outline = {
            "structure": "学术论文标准结构",
            "chapters": [
                {"id": "1", "title": "引言", "description": "介绍研究背景和动机", "depends_on": None},
                {"id": "2", "title": "文献综述", "description": "评述相关研究进展", "depends_on": None},
                {"id": "3", "title": "研究方法", "description": "描述研究设计和方法", "depends_on": "1"},
                {"id": "4", "title": "结果与分析", "description": "展示和讨论研究结果", "depends_on": "2,3"},
                {"id": "5", "title": "结论", "description": "总结研究贡献和未来工作", "depends_on": "4"},
            ],
            "key_arguments": []
        }
        return web.json_response({
            "success": True,
            "data": default_outline,
        })


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
    try:
        paper_id = request.match_info["id"]
        section_id = request.match_info["sectionId"]

        # 解析请求体获取要格式化的内容
        data = await request.json()
        provided_content = data.get("content", "")

        # 尝试获取论文，但即使论文不存在，只要有content就可以处理
        paper = get_paper_or_404(paper_id)
        if not paper and not provided_content:
            return web.json_response({
                "success": False,
                "error": "Paper not found and no content provided"
            }, status=404)

        # 获取章节信息
        section_title = section_id
        section_content = ""

        if paper:
            sections = paper.get("sections", []) or paper.get("outline", [])
            for s in sections:
                if s.get("id") == section_id:
                    section_title = s.get("title", section_id)
                    section_content = s.get("content", "")
                    break

        # 如果章节内容为空但提供了content参数，使用提供的content
        if not section_content and provided_content:
            section_content = provided_content

        # 如果仍然没有内容，返回错误
        if not section_content:
            return web.json_response({
                "success": False,
                "error": "章节内容为空"
            }, status=400)

        # 直接调用 LanguagePolisherAgent 修正格式
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
            result = await agent.execute({
                "text": section_content,
                "language": "zh",
                "polish_level": "medium"
            })

            if result.success and result.result:
                corrected_content = result.result.get("polished_text", section_content)
                return web.json_response({
                    "success": True,
                    "data": {
                        "content": corrected_content,
                        "section_id": section_id
                    },
                })
            else:
                return web.json_response({
                    "success": False,
                    "error": result.error or "格式修正失败"
                }, status=500)
        except Exception as llm_error:
            logger.error(f"LanguagePolisherAgent format correction failed: {llm_error}")
            return web.json_response({
                "success": False,
                "error": f"格式修正失败: {str(llm_error)}"
            }, status=500)

    except Exception as e:
        logger.error(f"Format content error: {e}")
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
        from src.agents_v2.qa import PaperSearchAgent

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

    # Knowledge Graph endpoints
    app.router.add_get('/api/knowledge-graph/literature', get_literature_graph)
    app.router.add_post('/api/knowledge-graph/generate', generate_literature_graph)
    app.router.add_get('/api/knowledge-graph/entity/{entityId}', get_entity_relations)

    # Settings
    app.router.add_get('/api/settings', get_settings)
    app.router.add_put('/api/settings', update_settings)
