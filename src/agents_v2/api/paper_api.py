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

        # Use TopicAgent to generate outline
        from src.agents_v2.paper_agents import TopicAgent
        from src.agents_v2.paper_agents.base_paper_agent import LLMConfig

        llm_config = LLMConfig(
            provider="openai",
            model_name=os.getenv("LLM_MODEL", "MiniMax-M2.7"),
            temperature=0.7,
            api_key=DEFAULT_API_KEY,
            base_url=DEFAULT_BASE_URL
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
            model_name=os.getenv("LLM_MODEL", "MiniMax-M2.7"),
            temperature=0.7,
            api_key=DEFAULT_API_KEY,
            base_url=DEFAULT_BASE_URL
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

            # 调用API，启用reasoning_split
            response = client.chat.completions.create(
                model=os.getenv("LLM_MODEL", "MiniMax-M2.7"),
                messages=api_messages,
                extra_body={"reasoning_split": True}
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

    # Literature file upload
    app.router.add_post('/api/literature/upload', upload_literature_file)

    # Chat
    app.router.add_post('/api/papers/{paperId}/chat', chat)
    app.router.add_get('/api/papers/{paperId}/chat/history', get_chat_history)

    # Settings
    app.router.add_get('/api/settings', get_settings)
    app.router.add_put('/api/settings', update_settings)
