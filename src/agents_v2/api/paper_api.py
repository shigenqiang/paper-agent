"""
Paper API - RESTful API for Paper Agent Frontend

Provides CRUD operations for papers, literature, and writing sessions.
"""
import time
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
from aiohttp import web
import uuid
import json

logger = logging.getLogger(__name__)

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
}


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
        data = await request.json()
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

        # Use TopicAgent to generate outline
        from src.agents_v2.paper_agents import TopicAgent
        from src.agents_v2.paper_agents.base_paper_agent import LLMConfig

        llm_config = LLMConfig(
            provider="openai",
            model_name="minimax",
            temperature=0.7
        )

        agent = TopicAgent(llm_config)
        result = await agent.execute({"user_request": f"Generate outline for: {topic}"})

        if result.success:
            # Parse outline from result
            outline = result.result.get("outline", []) if isinstance(result.result, dict) else []

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
        # Return a default outline structure on error
        default_outline = [
            {"id": "1", "title": "引言", "level": 1, "children": []},
            {"id": "2", "title": "文献综述", "level": 1, "children": []},
            {"id": "3", "title": "研究方法", "level": 1, "children": []},
            {"id": "4", "title": "结果与分析", "level": 1, "children": []},
            {"id": "5", "title": "结论", "level": 1, "children": []},
        ]
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

        # Use DraftWriter to generate content
        from src.agents_v2.paper_agents import DraftWriterAgent
        from src.agents_v2.paper_agents.base_paper_agent import LLMConfig

        llm_config = LLMConfig(
            provider="openai",
            model_name="minimax",
            temperature=0.7
        )

        agent = DraftWriterAgent(llm_config)
        result = await agent.execute({
            "title": paper.get("title", ""),
            "section": section_id,
            "outline": paper.get("outline", []),
            "prompt": prompt,
        })

        if result.success:
            content = result.result.get("content", "") if isinstance(result.result, dict) else str(result.result)

            return web.json_response({
                "success": True,
                "data": {"content": content, "section_id": section_id},
            })
        else:
            return web.json_response({
                "success": False,
                "error": result.error
            }, status=500)

    except Exception as e:
        logger.error(f"Generate content error: {e}")
        # Return placeholder content on error
        return web.json_response({
            "success": True,
            "data": {"content": f"[Auto-generated content for section {section_id}]", "section_id": section_id},
        })


# Literature endpoints
async def search_literature(request: web.Request) -> web.Response:
    """POST /literature/search - Search literature"""
    try:
        data = await request.json()
        query = data.get("query", "")

        # Use PaperSearchAgent to search
        from src.agents_v2.qa import PaperSearchAgent

        agent = PaperSearchAgent()
        result = await agent.execute(query, {"max_results": data.get("max_results", 10)})

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


# Chat endpoint
async def chat(request: web.Request) -> web.Response:
    """POST /papers/{paperId}/chat - Send chat message"""
    try:
        paper_id = request.match_info["paperId"]
        paper = get_paper_or_404(paper_id)

        if not paper:
            return web.json_response({
                "success": False,
                "error": "Paper not found"
            }, status=404)

        data = await request.json()
        message = data.get("message", "")

        # Use LiteratureAgent for chat
        from src.agents_v2.paper_agents import LiteratureAgent
        from src.agents_v2.paper_agents.base_paper_agent import LLMConfig

        llm_config = LLMConfig(
            provider="openai",
            model_name="minimax",
            temperature=0.7
        )

        agent = LiteratureAgent(llm_config)
        result = await agent.execute({
            "topic": paper.get("topic", ""),
            "question": message,
            "literature_ids": paper.get("literature_ids", []),
        })

        if result.success:
            response_text = result.result.get("answer", "") if isinstance(result.result, dict) else str(result.result)

            return web.json_response({
                "success": True,
                "data": {
                    "message": message,
                    "response": response_text,
                    "agent": "LiteratureAgent",
                },
            })
        else:
            return web.json_response({
                "success": True,
                "data": {
                    "message": message,
                    "response": "抱歉，我现在无法回答这个问题。请稍后再试。",
                    "agent": "LiteratureAgent",
                },
            })

    except Exception as e:
        logger.error(f"Chat error: {e}")
        return web.json_response({
            "success": True,
            "data": {
                "message": data.get("message", "") if 'data' in dir() else "",
                "response": "抱歉，我现在无法回答这个问题。请稍后再试。",
                "agent": "LiteratureAgent",
            },
        })


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


def setup_paper_routes(app: web.Application):
    """Setup all paper-related routes"""
    # Paper CRUD
    app.router.add_get('/api/papers', list_papers)
    app.router.add_post('/api/papers', create_paper)
    app.router.add_get('/api/papers/{id}', get_paper)
    app.router.add_put('/api/papers/{id}', update_paper)
    app.router.add_delete('/api/papers/{id}', delete_paper)

    # Paper outline
    app.router.add_get('/api/papers/{id}/outline', get_outline)
    app.router.add_post('/api/papers/{id}/outline/generate', generate_outline)

    # Content generation
    app.router.add_post('/api/papers/{id}/sections/{sectionId}/generate', generate_content)

    # Literature
    app.router.add_post('/api/literature/search', search_literature)
    app.router.add_get('/api/literature/{id}', get_literature)
    app.router.add_post('/api/papers/{paperId}/literature', add_literature)
    app.router.add_get('/api/literature/{id}/citation', get_citation)

    # Chat
    app.router.add_post('/api/papers/{paperId}/chat', chat)

    # Settings
    app.router.add_get('/api/settings', get_settings)
    app.router.add_put('/api/settings', update_settings)
