"""
API Server - HTTP接口服务

提供HTTP API访问Agent能力

使用方法:
    python -m src.agents_v2.api_server

认证:
    设置环境变量 API_KEY，然后请求头添加 X-API-Key
"""
from src.agents_v2.logging_config import get_logging_logger, add_sink

import asyncio
import uuid

import time
from typing import Any, Dict, Optional
from datetime import datetime
from aiohttp import web
import os
import json

# 加载 .env 文件
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# 设置日志
logger = get_logging_logger(__name__)

# API Key配置
API_KEY = os.getenv('API_KEY', 'dev-api-key')

# 公开端点（不需要认证）
PUBLIC_ENDPOINTS = {'/', '/health', '/docs', '/openapi.json'}


def is_public_endpoint(path: str) -> bool:
    """检查是否是公开端点"""
    return path in PUBLIC_ENDPOINTS or path.startswith('/static')


@web.middleware
async def request_logging_middleware(request: web.Request, handler):
    """
    请求日志中间件

    使用 Loguru 的上下文绑定为每个请求添加唯一的 request_id
    """
    request_id = request.headers.get('X-Request-ID') or str(uuid.uuid4())[:8]
    start_time = time.time()

    # 创建带 request_id 上下文的日志记录器
    req_logger = logger.bind(request_id=request_id, path=request.path)

    # 将请求日志绑定到请求对象，供后续处理函数使用
    request['logger'] = req_logger
    request['request_id'] = request_id

    req_logger.info("Request started", method=request.method)

    try:
        response = await handler(request)
        duration_ms = (time.time() - start_time) * 1000

        req_logger.info(
            "Request completed",
            status=response.status,
            duration_ms=round(duration_ms, 2)
        )
        return response

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        req_logger.exception(
            "Request failed",
            duration_ms=round(duration_ms, 2),
            error_type=type(e).__name__
        )
        raise


@web.middleware
async def api_key_auth_middleware(request: web.Request, handler):
    """
    API密钥认证中间件

    公开端点不需要认证，其他端点需要有效的API密钥
    """
    # 公开端点跳过认证
    if is_public_endpoint(request.path):
        return await handler(request)

    # 检查API密钥
    api_key = request.headers.get('X-API-Key')
    if not api_key:
        logger.warning(f"Missing API key for {request.path}")
        return web.json_response({
            "success": False,
            "error": "Missing API key. Set X-API-Key header."
        }, status=401)

    if api_key != API_KEY:
        logger.warning(f"Invalid API key for {request.path}")
        return web.json_response({
            "success": False,
            "error": "Invalid API key"
        }, status=401)

    return await handler(request)


async def health_check(request: web.Request) -> web.Response:
    """健康检查"""
    from datetime import datetime
    import time

    return web.json_response({
        "status": "healthy",
        "version": "1.0",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "api": "available",
            "llm": "available" if os.getenv('OPENAI_API_KEY') else "unavailable",
            "cache": "available"
        }
    })


async def handle_docs(request: web.Request) -> web.Response:
    """API文档页面"""
    docs_html = """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Paper Agent API Documentation</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 40px 20px;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
            }
            .header {
                text-align: center;
                color: white;
                margin-bottom: 40px;
            }
            .header h1 {
                font-size: 3em;
                margin-bottom: 10px;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
            }
            .header p {
                font-size: 1.2em;
                opacity: 0.9;
            }
            .badge {
                display: inline-block;
                background: rgba(255,255,255,0.2);
                padding: 5px 15px;
                border-radius: 20px;
                margin-top: 10px;
                font-size: 0.9em;
            }
            .card {
                background: white;
                border-radius: 15px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                padding: 30px;
                margin-bottom: 30px;
            }
            .card h2 {
                color: #333;
                font-size: 1.5em;
                margin-bottom: 20px;
                padding-bottom: 10px;
                border-bottom: 3px solid #667eea;
                display: flex;
                align-items: center;
                gap: 10px;
            }
            .card h2 .icon { font-size: 1.2em; }
            .endpoint {
                background: #f8f9fa;
                border-radius: 10px;
                padding: 20px;
                margin-bottom: 15px;
                border-left: 4px solid #667eea;
                transition: all 0.3s ease;
                cursor: pointer;
            }
            .endpoint:hover {
                background: #f0f2ff;
                transform: translateX(5px);
            }
            .endpoint-header {
                display: flex;
                align-items: center;
                gap: 15px;
                margin-bottom: 10px;
            }
            .method {
                padding: 6px 16px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 0.85em;
                text-transform: uppercase;
                min-width: 80px;
                text-align: center;
            }
            .method-get { background: #4CAF50; color: white; }
            .method-post { background: #2196F3; color: white; }
            .method-put { background: #FF9800; color: white; }
            .method-delete { background: #f44336; color: white; }
            .method-ws { background: #9C27B0; color: white; }
            .path {
                font-family: 'Monaco', 'Menlo', monospace;
                font-size: 1.1em;
                color: #333;
                font-weight: 600;
            }
            .desc {
                color: #666;
                font-size: 0.95em;
                margin-bottom: 12px;
            }
            .details {
                display: none;
                margin-top: 15px;
                padding-top: 15px;
                border-top: 1px dashed #ddd;
            }
            .details.show { display: block; }
            .details h4 {
                color: #667eea;
                margin-bottom: 8px;
                font-size: 0.9em;
                text-transform: uppercase;
                letter-spacing: 1px;
            }
            .code-block {
                background: #1e1e1e;
                color: #d4d4d4;
                padding: 15px 20px;
                border-radius: 8px;
                font-family: 'Monaco', 'Menlo', monospace;
                font-size: 0.9em;
                overflow-x: auto;
                margin: 10px 0;
                position: relative;
            }
            .code-block .copy-btn {
                position: absolute;
                top: 10px;
                right: 10px;
                background: rgba(255,255,255,0.1);
                border: none;
                color: white;
                padding: 5px 10px;
                border-radius: 4px;
                cursor: pointer;
                font-size: 0.8em;
            }
            .code-block .copy-btn:hover { background: rgba(255,255,255,0.2); }
            .code-key { color: #9cdcfe; }
            .code-string { color: #ce9178; }
            .code-number { color: #b5cea8; }
            .code-comment { color: #6a9955; }
            .tag {
                display: inline-block;
                padding: 3px 10px;
                border-radius: 12px;
                font-size: 0.75em;
                margin-right: 5px;
            }
            .tag-auth { background: #fff3cd; color: #856404; }
            .tag-public { background: #d4edda; color: #155724; }
            .tag-stream { background: #e8daef; color: #6c3483; }
            .auth-section {
                background: linear-gradient(135deg, #fff3cd 0%, #ffeeba 100%);
                border-radius: 10px;
                padding: 20px;
                margin-top: 20px;
            }
            .auth-section h3 {
                color: #856404;
                margin-bottom: 10px;
            }
            .auth-section code {
                background: rgba(0,0,0,0.1);
                padding: 2px 8px;
                border-radius: 4px;
                font-family: monospace;
            }
            .stats {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }
            .stat-card {
                background: white;
                border-radius: 10px;
                padding: 20px;
                text-align: center;
                box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            }
            .stat-card .number {
                font-size: 2.5em;
                font-weight: bold;
                color: #667eea;
            }
            .stat-card .label {
                color: #666;
                font-size: 0.9em;
                margin-top: 5px;
            }
            .toc {
                position: fixed;
                right: 20px;
                top: 50%;
                transform: translateY(-50%);
                background: white;
                border-radius: 10px;
                padding: 15px;
                box-shadow: 0 4px 15px rgba(0,0,0,0.1);
                max-height: 80vh;
                overflow-y: auto;
                z-index: 100;
            }
            .toc a {
                display: block;
                color: #667eea;
                text-decoration: none;
                padding: 5px 10px;
                border-radius: 5px;
                font-size: 0.85em;
                margin-bottom: 3px;
            }
            .toc a:hover { background: #f0f2ff; }
            @media (max-width: 1400px) {
                .toc { display: none; }
            }
            .footer {
                text-align: center;
                color: white;
                padding: 30px;
                opacity: 0.8;
            }
            .collapsible {
                cursor: pointer;
                user-select: none;
            }
            .collapsible::after {
                content: ' [+]';
                font-size: 0.8em;
                color: #999;
            }
            .collapsible.expanded::after {
                content: ' [-]';
            }
            /* Quick Start Steps */
            .step-card {
                background: #f8f9fa;
                border-radius: 12px;
                padding: 24px;
                margin-bottom: 20px;
                border-left: 5px solid #667eea;
                position: relative;
            }
            .step-card .step-num {
                position: absolute;
                top: -12px;
                left: -12px;
                width: 36px;
                height: 36px;
                background: linear-gradient(135deg, #667eea, #764ba2);
                color: white;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-weight: bold;
                font-size: 1.1em;
                box-shadow: 0 2px 8px rgba(102,126,234,0.4);
            }
            .step-card h3 { color: #333; margin-bottom: 8px; font-size: 1.15em; }
            .step-card .step-desc { color: #666; font-size: 0.9em; margin-bottom: 15px; }
            .code-tabs { display: flex; gap: 0; margin-bottom: -1px; position: relative; z-index: 1; }
            .code-tab {
                padding: 8px 20px;
                background: #ddd;
                border: none;
                border-radius: 8px 8px 0 0;
                cursor: pointer;
                font-size: 0.85em;
                font-weight: 600;
                color: #666;
                transition: all 0.2s;
            }
            .code-tab.active { background: #1e1e1e; color: #d4d4d4; }
            .code-panel { display: none; }
            .code-panel.active { display: block; }
            .try-btn {
                display: inline-flex;
                align-items: center;
                gap: 6px;
                padding: 8px 18px;
                background: linear-gradient(135deg, #667eea, #764ba2);
                color: white;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                font-size: 0.85em;
                font-weight: 600;
                transition: all 0.2s;
                margin-top: 10px;
            }
            .try-btn:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(102,126,234,0.4); }
            .try-btn.loading { opacity: 0.7; cursor: wait; }
            .response-box { margin-top: 15px; display: none; }
            .response-box.show { display: block; }
            .response-box .response-header { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
            .response-box .status-badge { padding: 3px 10px; border-radius: 12px; font-size: 0.8em; font-weight: bold; }
            .status-2xx { background: #d4edda; color: #155724; }
            .status-4xx { background: #fff3cd; color: #856404; }
            .status-5xx { background: #f8d7da; color: #721c24; }
            .response-box .time-badge { color: #999; font-size: 0.8em; }
            .steps-connector {
                position: absolute;
                left: 6px;
                top: 24px;
                bottom: 24px;
                width: 2px;
                background: linear-gradient(to bottom, #667eea, #764ba2);
                z-index: 0;
            }
            .steps-wrapper { position: relative; padding-left: 20px; }
            .modal-overlay {
                display: none;
                position: fixed;
                top: 0; left: 0; right: 0; bottom: 0;
                background: rgba(0,0,0,0.5);
                z-index: 1000;
                align-items: center;
                justify-content: center;
            }
            .modal-overlay.show { display: flex; }
            .modal { background: white; border-radius: 15px; padding: 30px; max-width: 450px; width: 90%; box-shadow: 0 20px 60px rgba(0,0,0,0.3); }
            .modal h3 { color: #333; margin-bottom: 15px; }
            .modal input { width: 100%; padding: 12px; border: 2px solid #ddd; border-radius: 8px; font-size: 1em; margin-bottom: 15px; }
            .modal input:focus { border-color: #667eea; outline: none; }
            .modal-actions { display: flex; gap: 10px; justify-content: flex-end; }
            .modal-actions button { padding: 10px 24px; border-radius: 8px; border: none; cursor: pointer; font-weight: 600; }
            .btn-primary { background: linear-gradient(135deg, #667eea, #764ba2); color: white; }
            .btn-secondary { background: #eee; color: #666; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Paper Agent API</h1>
                <p>Intelligent Academic Paper Writing Assistant</p>
                <div class="badge">v1.0 | Multi-Agent System</div>
            </div>

            <div class="stats">
                <div class="stat-card">
                    <div class="number">25+</div>
                    <div class="label">API Endpoints</div>
                </div>
                <div class="stat-card">
                    <div class="number">6</div>
                    <div class="label">AI Agents</div>
                </div>
                <div class="stat-card">
                    <div class="number">5</div>
                    <div class="label">Writing Phases</div>
                </div>
                <div class="stat-card">
                    <div class="number">16</div>
                    <div class="label">LLM Models</div>
                </div>
            </div>

            <!-- Public Endpoints -->
            <div class="card">
                <h2><span class="icon">🔓</span> Public Endpoints</h2>

                <div class="endpoint" onclick="toggleDetails(this)">
                    <div class="endpoint-header">
                        <span class="method method-get">GET</span>
                        <span class="path">/</span>
                        <span class="tag tag-public">Public</span>
                    </div>
                    <div class="desc">API information and version</div>
                    <div class="details">
                        <h4>Response</h4>
                        <div class="code-block">
<button class="copy-btn" onclick="copyCode(this)">Copy</button>
{
  "name": "Paper Research API",
  "version": "1.0",
  "docs": "/docs",
  "health": "/health"
}</div>
                    </div>
                </div>

                <div class="endpoint" onclick="toggleDetails(this)">
                    <div class="endpoint-header">
                        <span class="method method-get">GET</span>
                        <span class="path">/health</span>
                        <span class="tag tag-public">Public</span>
                    </div>
                    <div class="desc">Health check - system status</div>
                    <div class="details">
                        <h4>Response</h4>
                        <div class="code-block">
<button class="copy-btn" onclick="copyCode(this)">Copy</button>
{
  "status": "healthy",
  "services": {
    "api": "available",
    "llm": "available",
    "cache": "available"
  }
}</div>
                    </div>
                </div>
            </div>

            <!-- Paper Management -->
            <div class="card">
                <h2><span class="icon">📄</span> Paper Management</h2>
                <p style="color: #666; margin-bottom: 20px;">CRUD operations for papers, outlines, and content generation</p>

                <div class="endpoint" onclick="toggleDetails(this)">
                    <div class="endpoint-header">
                        <span class="method method-get">GET</span>
                        <span class="path">/api/papers</span>
                        <span class="tag tag-auth">Auth</span>
                    </div>
                    <div class="desc">List all papers with pagination</div>
                    <div class="details">
                        <h4>Query Parameters</h4>
                        <div class="code-block">
<button class="copy-btn" onclick="copyCode(this)">Copy</button>
page: int = 1          # Page number
pageSize: int = 10     # Items per page
status: string         # Filter by status (draft/reviewing/published)</div>
                        <h4>Response</h4>
                        <div class="code-block">
<button class="copy-btn" onclick="copyCode(this)">Copy</button>
{
  "success": true,
  "data": [...],
  "total": 100,
  "page": 1,
  "pageSize": 10
}</div>
                    </div>
                </div>

                <div class="endpoint" onclick="toggleDetails(this)">
                    <div class="endpoint-header">
                        <span class="method method-post">POST</span>
                        <span class="path">/api/papers</span>
                        <span class="tag tag-auth">Auth</span>
                    </div>
                    <div class="desc">Create a new paper</div>
                    <div class="details">
                        <h4>Request Body</h4>
                        <div class="code-block">
<button class="copy-btn" onclick="copyCode(this)">Copy</button>
{
  "title": "Research Paper Title",
  "topic": "Research topic description",
  "outline": [],        // Optional
  "content": ""         // Optional
}</div>
                        <h4>Response (201)</h4>
                        <div class="code-block">
<button class="copy-btn" onclick="copyCode(this)">Copy</button>
{
  "success": true,
  "data": {
    "id": "uuid",
    "title": "...",
    "status": "draft",
    "created_at": "2024-01-01T00:00:00"
  }
}</div>
                    </div>
                </div>

                <div class="endpoint" onclick="toggleDetails(this)">
                    <div class="endpoint-header">
                        <span class="method method-get">GET</span>
                        <span class="path">/api/papers/{id}</span>
                        <span class="tag tag-auth">Auth</span>
                    </div>
                    <div class="desc">Get paper by ID</div>
                    <div class="details">
                        <h4>Path Parameters</h4>
                        <div class="code-block">
<button class="copy-btn" onclick="copyCode(this)">Copy</button>
id: string (uuid) - Paper ID</div>
                    </div>
                </div>

                <div class="endpoint" onclick="toggleDetails(this)">
                    <div class="endpoint-header">
                        <span class="method method-put">PUT</span>
                        <span class="path">/api/papers/{id}</span>
                        <span class="tag tag-auth">Auth</span>
                    </div>
                    <div class="desc">Update paper</div>
                    <div class="details">
                        <h4>Request Body (partial update)</h4>
                        <div class="code-block">
<button class="copy-btn" onclick="copyCode(this)">Copy</button>
{
  "title": "Updated Title",
  "topic": "Updated topic",
  "status": "reviewing"
}</div>
                    </div>
                </div>

                <div class="endpoint" onclick="toggleDetails(this)">
                    <div class="endpoint-header">
                        <span class="method method-delete">DELETE</span>
                        <span class="path">/api/papers/{id}</span>
                        <span class="tag tag-auth">Auth</span>
                    </div>
                    <div class="desc">Delete paper</div>
                </div>

                <div class="endpoint" onclick="toggleDetails(this)">
                    <div class="endpoint-header">
                        <span class="method method-post">POST</span>
                        <span class="path">/api/papers/upload</span>
                        <span class="tag tag-auth">Auth</span>
                    </div>
                    <div class="desc">Upload paper file (MD/TXT/PDF/DOCX)</div>
                    <div class="details">
                        <h4>Request</h4>
                        <div class="code-block">
<button class="copy-btn" onclick="copyCode(this)">Copy</button>
Content-Type: multipart/form-data
file: binary - Paper file</div>
                    </div>
                </div>
            </div>

            <!-- AI Generation -->
            <div class="card">
                <h2><span class="icon">🤖</span> AI Generation</h2>
                <p style="color: #666; margin-bottom: 20px;">AI-powered content generation endpoints</p>

                <div class="endpoint" onclick="toggleDetails(this)">
                    <div class="endpoint-header">
                        <span class="method method-post">POST</span>
                        <span class="path">/api/papers/{id}/outline/generate</span>
                        <span class="tag tag-auth">Auth</span>
                    </div>
                    <div class="desc">Generate paper outline using AI</div>
                    <div class="details">
                        <h4>Request Body</h4>
                        <div class="code-block">
<button class="copy-btn" onclick="copyCode(this)">Copy</button>
{
  "topic": "Research topic for outline generation"
}</div>
                        <h4>Response</h4>
                        <div class="code-block">
<button class="copy-btn" onclick="copyCode(this)">Copy</button>
{
  "success": true,
  "data": {
    "structure": {...},
    "chapters": [...],
    "key_arguments": [...]
  }
}</div>
                    </div>
                </div>

                <div class="endpoint" onclick="toggleDetails(this)">
                    <div class="endpoint-header">
                        <span class="method method-post">POST</span>
                        <span class="path">/api/papers/{id}/sections/{sid}/generate</span>
                        <span class="tag tag-auth">Auth</span>
                    </div>
                    <div class="desc">Generate section content using AI</div>
                    <div class="details">
                        <h4>Request Body</h4>
                        <div class="code-block">
<button class="copy-btn" onclick="copyCode(this)">Copy</button>
{
  "prompt": "Optional additional instructions"
}</div>
                    </div>
                </div>

                <div class="endpoint" onclick="toggleDetails(this)">
                    <div class="endpoint-header">
                        <span class="method method-post">POST</span>
                        <span class="path">/api/papers/{id}/sections/{sid}/format</span>
                        <span class="tag tag-auth">Auth</span>
                    </div>
                    <div class="desc">Polish and format section content</div>
                    <div class="details">
                        <h4>Request Body</h4>
                        <div class="code-block">
<button class="copy-btn" onclick="copyCode(this)">Copy</button>
{
  "content": "Content to polish and format"
}</div>
                    </div>
                </div>

                <div class="endpoint" onclick="toggleDetails(this)">
                    <div class="endpoint-header">
                        <span class="method method-post">POST</span>
                        <span class="path">/api/papers/{id}/outline/generate/stream</span>
                        <span class="tag tag-auth">Auth</span>
                        <span class="tag tag-stream">SSE</span>
                    </div>
                    <div class="desc">Generate outline with streaming response</div>
                </div>

                <div class="endpoint" onclick="toggleDetails(this)">
                    <div class="endpoint-header">
                        <span class="method method-post">POST</span>
                        <span class="path">/api/papers/{id}/sections/{sid}/generate/stream</span>
                        <span class="tag tag-auth">Auth</span>
                        <span class="tag tag-stream">SSE</span>
                    </div>
                    <div class="desc">Generate content with streaming response</div>
                </div>
            </div>

            <!-- Literature & Knowledge -->
            <div class="card">
                <h2><span class="icon">📚</span> Literature & Knowledge Graph</h2>
                <p style="color: #666; margin-bottom: 20px;">Literature management and knowledge graph operations</p>

                <div class="endpoint" onclick="toggleDetails(this)">
                    <div class="endpoint-header">
                        <span class="method method-post">POST</span>
                        <span class="path">/api/literature/search</span>
                        <span class="tag tag-auth">Auth</span>
                    </div>
                    <div class="desc">Search academic papers across multiple sources</div>
                    <div class="details">
                        <h4>Request Body</h4>
                        <div class="code-block">
<button class="copy-btn" onclick="copyCode(this)">Copy</button>
{
  "query": "deep learning NLP",
  "max_results": 10,
  "page": 1
}</div>
                        <h4>Supported Sources</h4>
                        <div class="code-block">
<button class="copy-btn" onclick="copyCode(this)">Copy</button>
arxiv, pubmed, semantic_scholar,
openalex, crossref, base</div>
                    </div>
                </div>

                <div class="endpoint" onclick="toggleDetails(this)">
                    <div class="endpoint-header">
                        <span class="method method-post">POST</span>
                        <span class="path">/api/papers/{pid}/literature</span>
                        <span class="tag tag-auth">Auth</span>
                    </div>
                    <div class="desc">Add literature to paper</div>
                    <div class="details">
                        <h4>Request Body</h4>
                        <div class="code-block">
<button class="copy-btn" onclick="copyCode(this)">Copy</button>
{
  "title": "Paper Title",
  "authors": "Author 1, Author 2",
  "year": "2024",
  "journal": "Journal Name",
  "abstract": "...",
  "url": "https://..."
}</div>
                    </div>
                </div>

                <div class="endpoint" onclick="toggleDetails(this)">
                    <div class="endpoint-header">
                        <span class="method method-get">GET</span>
                        <span class="path">/api/knowledge-graph/literature</span>
                        <span class="tag tag-auth">Auth</span>
                    </div>
                    <div class="desc">Get knowledge graph for all literature</div>
                </div>

                <div class="endpoint" onclick="toggleDetails(this)">
                    <div class="endpoint-header">
                        <span class="method method-post">POST</span>
                        <span class="path">/api/knowledge-graph/generate</span>
                        <span class="tag tag-auth">Auth</span>
                    </div>
                    <div class="desc">Generate knowledge graph from literature</div>
                    <div class="details">
                        <h4>Request Body</h4>
                        <div class="code-block">
<button class="copy-btn" onclick="copyCode(this)">Copy</button>
{
  "literatureIds": ["id1", "id2", ...]
}</div>
                    </div>
                </div>

                <div class="endpoint" onclick="toggleDetails(this)">
                    <div class="endpoint-header">
                        <span class="method method-post">POST</span>
                        <span class="path">/api/knowledge-graph/query</span>
                        <span class="tag tag-auth">Auth</span>
                    </div>
                    <div class="desc">GraphRAG question answering</div>
                </div>
            </div>

            <!-- Chat & Reports -->
            <div class="card">
                <h2><span class="icon">💬</span> Chat & Reports</h2>
                <p style="color: #666; margin-bottom: 20px;">Interactive chat and automated report generation</p>

                <div class="endpoint" onclick="toggleDetails(this)">
                    <div class="endpoint-header">
                        <span class="method method-post">POST</span>
                        <span class="path">/api/papers/{pid}/chat</span>
                        <span class="tag tag-auth">Auth</span>
                    </div>
                    <div class="desc">Chat with AI about the paper</div>
                    <div class="details">
                        <h4>Request Body</h4>
                        <div class="code-block">
<button class="copy-btn" onclick="copyCode(this)">Copy</button>
{
  "message": "Your question about the paper",
  "user_id": "optional_user_id",
  "session_id": "optional_session_id"
}</div>
                    </div>
                </div>

                <div class="endpoint" onclick="toggleDetails(this)">
                    <div class="endpoint-header">
                        <span class="method method-post">POST</span>
                        <span class="path">/api/papers/{pid}/chat/stream</span>
                        <span class="tag tag-auth">Auth</span>
                        <span class="tag tag-stream">SSE</span>
                    </div>
                    <div class="desc">Chat with streaming response</div>
                </div>

                <div class="endpoint" onclick="toggleDetails(this)">
                    <div class="endpoint-header">
                        <span class="method method-get">GET</span>
                        <span class="path">/api/reports</span>
                        <span class="tag tag-auth">Auth</span>
                    </div>
                    <div class="desc">List all reports</div>
                </div>

                <div class="endpoint" onclick="toggleDetails(this)">
                    <div class="endpoint-header">
                        <span class="method method-get">GET</span>
                        <span class="path">/api/reports/daily</span>
                        <span class="tag tag-auth">Auth</span>
                    </div>
                    <div class="desc">Get daily report</div>
                </div>

                <div class="endpoint" onclick="toggleDetails(this)">
                    <div class="endpoint-header">
                        <span class="method method-get">GET</span>
                        <span class="path">/api/reports/weekly</span>
                        <span class="tag tag-auth">Auth</span>
                    </div>
                    <div class="desc">Get weekly report</div>
                </div>

                <div class="endpoint" onclick="toggleDetails(this)">
                    <div class="endpoint-header">
                        <span class="method method-get">GET</span>
                        <span class="path">/api/reports/monthly</span>
                        <span class="tag tag-auth">Auth</span>
                    </div>
                    <div class="desc">Get monthly report</div>
                </div>
            </div>

            <!-- System -->
            <div class="card">
                <h2><span class="icon">⚙️</span> System</h2>
                <p style="color: #666; margin-bottom: 20px;">System configuration and utilities</p>

                <div class="endpoint" onclick="toggleDetails(this)">
                    <div class="endpoint-header">
                        <span class="method method-get">GET</span>
                        <span class="path">/api/settings</span>
                        <span class="tag tag-auth">Auth</span>
                    </div>
                    <div class="desc">Get user settings</div>
                </div>

                <div class="endpoint" onclick="toggleDetails(this)">
                    <div class="endpoint-header">
                        <span class="method method-put">PUT</span>
                        <span class="path">/api/settings</span>
                        <span class="tag tag-auth">Auth</span>
                    </div>
                    <div class="desc">Update user settings</div>
                    <div class="details">
                        <h4>Request Body</h4>
                        <div class="code-block">
<button class="copy-btn" onclick="copyCode(this)">Copy</button>
{
  "language": "zh-CN",
  "theme": "light",
  "autoSave": true,
  "defaultModel": "gpt-4"
}</div>
                    </div>
                </div>

                <div class="endpoint" onclick="toggleDetails(this)">
                    <div class="endpoint-header">
                        <span class="method method-get">GET</span>
                        <span class="path">/api/models</span>
                        <span class="tag tag-auth">Auth</span>
                    </div>
                    <div class="desc">List available LLM models</div>
                    <div class="details">
                        <h4>Supported Providers</h4>
                        <div class="code-block">
<button class="copy-btn" onclick="copyCode(this)">Copy</button>
OpenAI (GPT-4o, GPT-4, GPT-3.5)
Anthropic (Claude Opus 4, Sonnet 4)
MiniMax (M2.7, M1)
DeepSeek (R1, V3)
Qwen (Max, Plus, Turbo)
GLM (GLM-4, GLM-4-Flash)</div>
                    </div>
                </div>

                <div class="endpoint" onclick="toggleDetails(this)">
                    <div class="endpoint-header">
                        <span class="method method-ws">WS</span>
                        <span class="path">/ws/status</span>
                        <span class="tag tag-auth">Auth</span>
                    </div>
                    <div class="desc">WebSocket for real-time status updates</div>
                </div>
            </div>

            <!-- Authentication -->
            <div class="card">
                <h2><span class="icon">🔐</span> Authentication</h2>
                <div class="auth-section">
                    <h3>API Key Authentication</h3>
                    <p>All endpoints except public ones require authentication via API key.</p>
                    <div class="code-block" style="margin-top: 15px;">
<button class="copy-btn" onclick="copyCode(this)">Copy</button>
# Add to request header
X-API-Key: your-api-key

# Example with curl
curl -H "X-API-Key: dev-api-key" http://localhost:8000/api/papers</div>
                    <p style="margin-top: 15px; color: #856404;">
                        <strong>Default development key:</strong> <code>dev-api-key</code>
                    </p>
                </div>
            </div>

            <!-- Quick Start -->
            <div class="card" id="quickstart">
                <h2><span class="icon">🚀</span> Quick Start</h2>
                <div class="steps-wrapper">
                    <div class="steps-connector"></div>

                    <div class="step-card">
                        <div class="step-num">1</div>
                        <h3>Create a Paper</h3>
                        <div class="step-desc">Create a new paper. Save the returned <code>id</code> for next steps.</div>
                        <div class="code-tabs">
                            <button class="code-tab active" onclick="switchTab(this,'curl1')">curl</button>
                            <button class="code-tab" onclick="switchTab(this,'py1')">Python</button>
                        </div>
                        <div class="code-panel active" id="curl1"><div class="code-block"><button class="copy-btn" onclick="copyCode(this)">Copy</button>curl -X POST http://localhost:8000/api/papers \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-api-key" \
  -d '{"title": "My Research Paper", "topic": "AI in Education"}'</div></div>
                        <div class="code-panel" id="py1"><div class="code-block"><button class="copy-btn" onclick="copyCode(this)">Copy</button>import requests

resp = requests.post("http://localhost:8000/api/papers",
    json={"title": "My Research Paper", "topic": "AI in Education"},
    headers={"X-API-Key": "dev-api-key"})
paper_id = resp.json()["data"]["id"]</div></div>
                        <button class="try-btn" onclick="tryIt(this,'POST','/api/papers',{title:'My Research Paper',topic:'AI in Education'})">▶ Try it</button>
                        <div class="response-box"><div class="response-header"><span class="status-badge"></span><span class="time-badge"></span></div><div class="code-block"></div></div>
                    </div>

                    <div class="step-card">
                        <div class="step-num">2</div>
                        <h3>Generate Outline</h3>
                        <div class="step-desc">Use <code>paper_id</code> from step 1 to generate an AI-powered outline.</div>
                        <div class="code-tabs">
                            <button class="code-tab active" onclick="switchTab(this,'curl2')">curl</button>
                            <button class="code-tab" onclick="switchTab(this,'py2')">Python</button>
                        </div>
                        <div class="code-panel active" id="curl2"><div class="code-block"><button class="copy-btn" onclick="copyCode(this)">Copy</button>curl -X POST http://localhost:8000/api/papers/{paper_id}/outline/generate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-api-key" \
  -d '{"topic": "AI in Education"}'</div></div>
                        <div class="code-panel" id="py2"><div class="code-block"><button class="copy-btn" onclick="copyCode(this)">Copy</button>resp = requests.post(
    f"http://localhost:8000/api/papers/{paper_id}/outline/generate",
    json={"topic": "AI in Education"},
    headers={"X-API-Key": "dev-api-key"})</div></div>
                        <button class="try-btn" onclick="tryIt(this,'POST','/api/papers/{paper_id}/outline/generate',{topic:'AI in Education'})">▶ Try it</button>
                        <div class="response-box"><div class="response-header"><span class="status-badge"></span><span class="time-badge"></span></div><div class="code-block"></div></div>
                    </div>

                    <div class="step-card">
                        <div class="step-num">3</div>
                        <h3>Generate Section Content</h3>
                        <div class="step-desc">Generate content for a section. Use <code>section_id</code> from the outline.</div>
                        <div class="code-tabs">
                            <button class="code-tab active" onclick="switchTab(this,'curl3')">curl</button>
                            <button class="code-tab" onclick="switchTab(this,'py3')">Python</button>
                        </div>
                        <div class="code-panel active" id="curl3"><div class="code-block"><button class="copy-btn" onclick="copyCode(this)">Copy</button>curl -X POST http://localhost:8000/api/papers/{paper_id}/sections/{section_id}/generate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-api-key" \
  -d '{}'</div></div>
                        <div class="code-panel" id="py3"><div class="code-block"><button class="copy-btn" onclick="copyCode(this)">Copy</button>resp = requests.post(
    f"http://localhost:8000/api/papers/{paper_id}/sections/{section_id}/generate",
    json={},
    headers={"X-API-Key": "dev-api-key"})</div></div>
                        <button class="try-btn" onclick="tryIt(this,'POST','/api/papers/{paper_id}/sections/{section_id}/generate',{})">▶ Try it</button>
                        <div class="response-box"><div class="response-header"><span class="status-badge"></span><span class="time-badge"></span></div><div class="code-block"></div></div>
                    </div>

                    <div class="step-card">
                        <div class="step-num">4</div>
                        <h3>Polish Content</h3>
                        <div class="step-desc">Polish and format the section content using AI.</div>
                        <div class="code-tabs">
                            <button class="code-tab active" onclick="switchTab(this,'curl4')">curl</button>
                            <button class="code-tab" onclick="switchTab(this,'py4')">Python</button>
                        </div>
                        <div class="code-panel active" id="curl4"><div class="code-block"><button class="copy-btn" onclick="copyCode(this)">Copy</button>curl -X POST http://localhost:8000/api/papers/{paper_id}/sections/{section_id}/format \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-api-key" \
  -d '{"content": "Your content here..."}'</div></div>
                        <div class="code-panel" id="py4"><div class="code-block"><button class="copy-btn" onclick="copyCode(this)">Copy</button>resp = requests.post(
    f"http://localhost:8000/api/papers/{paper_id}/sections/{section_id}/format",
    json={"content": "Your content here..."},
    headers={"X-API-Key": "dev-api-key"})</div></div>
                        <button class="try-btn" onclick="tryIt(this,'POST','/api/papers/{paper_id}/sections/{section_id}/format',{content:'Your content here...'})">▶ Try it</button>
                        <div class="response-box"><div class="response-header"><span class="status-badge"></span><span class="time-badge"></span></div><div class="code-block"></div></div>
                    </div>
                </div>
            </div>

            <div class="footer">
                <p>Paper Agent API v1.0 | Multi-Agent Academic Writing System</p>
                <p>Built with aiohttp + LangGraph + React</p>
            </div>
        </div>

        <!-- Table of Contents -->
        <div class="toc">
            <a href="#quickstart">Quick Start</a>
            <a href="#public">Public</a>
            <a href="#papers">Papers</a>
            <a href="#ai-generation">AI Generation</a>
            <a href="#literature">Literature</a>
            <a href="#chat">Chat</a>
            <a href="#system">System</a>
        </div>

        <script>
            let apiKey = localStorage.getItem('api_key') || 'dev-api-key';

            function toggleDetails(el) {
                const details = el.querySelector('.details');
                if (details) {
                    details.classList.toggle('show');
                    el.classList.toggle('expanded');
                }
            }

            function copyCode(btn) {
                const code = btn.parentElement.textContent.replace('Copy', '').trim();
                navigator.clipboard.writeText(code).then(() => {
                    btn.textContent = 'Copied!';
                    setTimeout(() => btn.textContent = 'Copy', 2000);
                });
            }

            function switchTab(tabBtn, panelId) {
                const parent = tabBtn.closest('.step-card') || tabBtn.closest('.endpoint');
                parent.querySelectorAll('.code-tab').forEach(t => t.classList.remove('active'));
                parent.querySelectorAll('.code-panel').forEach(p => p.classList.remove('active'));
                tabBtn.classList.add('active');
                document.getElementById(panelId).classList.add('active');
            }

            async function tryIt(btn, method, path, body) {
                const responseBox = btn.nextElementSibling;
                const statusBadge = responseBox.querySelector('.status-badge');
                const timeBadge = responseBox.querySelector('.time-badge');
                const codeBlock = responseBox.querySelector('.code-block');

                btn.classList.add('loading');
                btn.innerHTML = '⏳ Loading...';
                responseBox.classList.add('show');
                codeBlock.textContent = 'Loading...';
                statusBadge.textContent = '';
                timeBadge.textContent = '';

                const start = performance.now();
                try {
                    const opts = { method, headers: { 'Content-Type': 'application/json', 'X-API-Key': apiKey } };
                    if (body) opts.body = JSON.stringify(body);
                    const resp = await fetch(path, opts);
                    const elapsed = Math.round(performance.now() - start);
                    const data = await resp.json();
                    const statusClass = resp.status < 300 ? 'status-2xx' : resp.status < 500 ? 'status-4xx' : 'status-5xx';
                    statusBadge.className = 'status-badge ' + statusClass;
                    statusBadge.textContent = resp.status + ' ' + resp.statusText;
                    timeBadge.textContent = elapsed + 'ms';
                    codeBlock.textContent = JSON.stringify(data, null, 2);
                } catch (e) {
                    const elapsed = Math.round(performance.now() - start);
                    statusBadge.className = 'status-badge status-5xx';
                    statusBadge.textContent = 'Error';
                    timeBadge.textContent = elapsed + 'ms';
                    codeBlock.textContent = 'Error: ' + e.message;
                }
                btn.classList.remove('loading');
                btn.innerHTML = '▶ Try it';
            }
        </script>
    </body>
    </html>
    """
    return web.Response(text=docs_html, content_type='text/html')


async def handle_topic(request: web.Request) -> web.Response:
    """处理选题请求"""
    start_time = time.time()
    try:
        data = await request.json()
        user_request = data.get("user_request", "")

        if not user_request:
            return web.json_response({
                "success": False,
                "error": "user_request is required",
                "execution_time": time.time() - start_time,
                "timestamp": datetime.now().isoformat()
            }, status=400)

        from src.agents_v2.paper_agents import TopicAgent
        from src.agents_v2.agents.paper.base_paper_agent import LLMConfig

        llm_config = LLMConfig(
            provider="openai",
            model_name="minimax-m2.7",
            temperature=0.7
        )

        agent = TopicAgent(llm_config)
        result = await agent.execute({"user_request": user_request})

        execution_time = time.time() - start_time
        return web.json_response({
            "success": result.success,
            "result": result.result,
            "quality_score": result.quality_score,
            "error": result.error,
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Topic handler error: {e}")
        execution_time = time.time() - start_time
        return web.json_response({
            "success": False,
            "error": str(e),
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat()
        }, status=500)


async def handle_search(request: web.Request) -> web.Response:
    """处理论文搜索请求"""
    start_time = time.time()
    try:
        data = await request.json()
        query = data.get("query", "")
        source = data.get("source", "all")
        max_results = data.get("max_results", 10)

        if not query:
            return web.json_response({
                "success": False,
                "error": "query is required",
                "execution_time": time.time() - start_time,
                "timestamp": datetime.now().isoformat()
            }, status=400)

        from src.agents_v2.paper_search import PaperSearchAgent

        agent = PaperSearchAgent()
        result = await agent.execute(
            query,
            {"source": source, "max_results": max_results}
        )

        execution_time = time.time() - start_time
        return web.json_response({
            "success": True,
            "papers": result.get("papers", []),
            "total": len(result.get("papers", [])),
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Search handler error: {e}")
        execution_time = time.time() - start_time
        return web.json_response({
            "success": False,
            "error": str(e),
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat()
        }, status=500)


async def handle_route(request: web.Request) -> web.Response:
    """处理意图路由请求"""
    start_time = time.time()
    try:
        data = await request.json()
        user_request = data.get("user_request", "")

        if not user_request:
            return web.json_response({
                "success": False,
                "error": "user_request is required",
                "execution_time": time.time() - start_time,
                "timestamp": datetime.now().isoformat()
            }, status=400)

        from src.agents_v2.unified import IntentRouter

        router = IntentRouter()
        result = await router.route(user_request)

        execution_time = time.time() - start_time
        result["execution_time"] = execution_time
        result["timestamp"] = datetime.now().isoformat()

        return web.json_response(result)

    except Exception as e:
        logger.error(f"Route handler error: {e}")
        execution_time = time.time() - start_time
        return web.json_response({
            "success": False,
            "error": str(e),
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat()
        }, status=500)


async def handle_literature(request: web.Request) -> web.Response:
    """处理文献综述请求"""
    start_time = time.time()
    try:
        data = await request.json()
        topic = data.get("topic", "")

        if not topic:
            return web.json_response({
                "success": False,
                "error": "topic is required",
                "execution_time": time.time() - start_time,
                "timestamp": datetime.now().isoformat()
            }, status=400)

        from src.agents_v2.writing import LiteratureReviewAgent

        agent = LiteratureReviewAgent()
        result = await agent.execute({"topic": topic})

        execution_time = time.time() - start_time
        return web.json_response({
            "success": result.success,
            "result": result.result,
            "quality_score": result.quality_score,
            "error": result.error,
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Literature handler error: {e}")
        execution_time = time.time() - start_time
        return web.json_response({
            "success": False,
            "error": str(e),
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat()
        }, status=500)


async def handle_proposal(request: web.Request) -> web.Response:
    """处理开题报告请求"""
    start_time = time.time()
    try:
        data = await request.json()
        topic = data.get("topic", "")
        research_background = data.get("research_background", "")
        research_significance = data.get("research_significance", "")

        if not topic:
            return web.json_response({
                "success": False,
                "error": "topic is required",
                "execution_time": time.time() - start_time,
                "timestamp": datetime.now().isoformat()
            }, status=400)

        from src.agents_v2.writing import ProposalGeneratorAgent

        agent = ProposalGeneratorAgent()
        result = await agent.execute({
            "topic": topic,
            "research_background": research_background,
            "research_significance": research_significance
        })

        execution_time = time.time() - start_time
        return web.json_response({
            "success": result.success,
            "result": result.result,
            "quality_score": result.quality_score,
            "error": result.error,
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Proposal handler error: {e}")
        execution_time = time.time() - start_time
        return web.json_response({
            "success": False,
            "error": str(e),
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat()
        }, status=500)


async def handle_full_paper(request: web.Request) -> web.Response:
    """处理完整论文请求

    使用 UnifiedWorkflow（LangGraph）处理完整论文写作流程，
    包含诊断阶段和 HITL 人工介入支持。
    """
    start_time = time.time()
    try:
        data = await request.json()
        topic = data.get("topic", "")

        if not topic:
            return web.json_response({
                "success": False,
                "error": "topic is required",
                "execution_time": time.time() - start_time,
                "timestamp": datetime.now().isoformat()
            }, status=400)

        enable_hitl = data.get("enable_hitl", False)

        # 使用 UnifiedWorkflow（LangGraph）处理写作流程
        from src.agents_v2.workflow.langgraph.unified_workflow import UnifiedWorkflow

        workflow = UnifiedWorkflow(
            enable_memory=True,
            enable_multimodal=True,
            enable_kg=True,
            enable_evaluation=True,
            enable_hitl=enable_hitl,
        )
        workflow.compile()

        # 设置路由意图为 writing，触发 diagnostic → outline → write → review → evaluation 流程
        result = await workflow.run(
            query=topic,
            route_path="writing",  # 触发写作工作流（包含诊断）
            enable_hitl=enable_hitl,
        )

        # 检查是否被 HITL 中断
        interrupted = result.get("interrupted", False)
        if interrupted:
            execution_time = time.time() - start_time
            return web.json_response({
                "success": True,
                "interrupted": True,
                "interrupt_stage": result.get("interrupt_stage", ""),
                "interrupt_reason": result.get("interrupt_reason", ""),
                "thread_id": result.get("thread_id", ""),
                "execution_time": execution_time,
                "timestamp": datetime.now().isoformat()
            }, status=202)  # 202 Accepted 表示请求已接受但尚未完成

        execution_time = time.time() - start_time
        return web.json_response({
            "success": True,
            "result": result,
            "quality_score": result.get("final_quality", 0),
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Full paper handler error: {e}")
        execution_time = time.time() - start_time
        return web.json_response({
            "success": False,
            "error": str(e),
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat()
        }, status=500)


async def handle_draft(request: web.Request) -> web.Response:
    """处理论文初稿请求"""
    start_time = time.time()
    try:
        data = await request.json()
        topic = data.get("topic", "")
        outline = data.get("outline", None)

        if not topic:
            return web.json_response({
                "success": False,
                "error": "topic is required",
                "execution_time": time.time() - start_time,
                "timestamp": datetime.now().isoformat()
            }, status=400)

        from src.agents_v2.writing import DraftGeneratorAgent

        agent = DraftGeneratorAgent()
        input_data = {"topic": topic}
        if outline:
            input_data["outline"] = outline

        result = await agent.execute(input_data)

        execution_time = time.time() - start_time
        return web.json_response({
            "success": result.success,
            "result": result.result,
            "quality_score": result.quality_score,
            "error": result.error,
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Draft handler error: {e}")
        execution_time = time.time() - start_time
        return web.json_response({
            "success": False,
            "error": str(e),
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat()
        }, status=500)


async def handle_revise(request: web.Request) -> web.Response:
    """处理论文局部修改请求"""
    start_time = time.time()
    try:
        data = await request.json()
        content = data.get("content", "")
        revision_type = data.get("revision_type", "general")

        if not content:
            return web.json_response({
                "success": False,
                "error": "content is required",
                "execution_time": time.time() - start_time,
                "timestamp": datetime.now().isoformat()
            }, status=400)

        from src.agents_v2.writing import SmartReviserAgent

        agent = SmartReviserAgent()
        result = await agent.execute({
            "content": content,
            "revision_type": revision_type
        })

        execution_time = time.time() - start_time
        return web.json_response({
            "success": result.success,
            "result": result.result,
            "quality_score": result.quality_score,
            "error": result.error,
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Revise handler error: {e}")
        execution_time = time.time() - start_time
        return web.json_response({
            "success": False,
            "error": str(e),
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat()
        }, status=500)


async def handle_diagnostics(request: web.Request) -> web.Response:
    """处理诊断请求"""
    start_time = time.time()
    try:
        data = await request.json()
        content = data.get("content", {})
        phase = data.get("phase", "general")

        if not content:
            return web.json_response({
                "success": False,
                "error": "content is required",
                "execution_time": time.time() - start_time,
                "timestamp": datetime.now().isoformat()
            }, status=400)

        from src.agents_v2.unified import MasterSupervisor

        supervisor = MasterSupervisor()
        supervisor.register_problem_agents()

        result = await supervisor.run("diagnostic_only", {
            "content": content,
            "phase": phase
        })

        execution_time = time.time() - start_time
        return web.json_response({
            "success": True,
            "result": result,
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Diagnostics handler error: {e}")
        execution_time = time.time() - start_time
        return web.json_response({
            "success": False,
            "error": str(e),
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat()
        }, status=500)


def create_app() -> web.Application:
    """创建Web应用"""
    app = web.Application()

    # 添加日志中间件（按顺序：先日志，后认证）
    app.middlewares.append(request_logging_middleware)

    # 添加认证中间件
    app.middlewares.append(api_key_auth_middleware)

    # 启动时创建默认定时任务
    async def on_startup(app):
        # 启动报告调度器
        from src.agents_v2.scheduler import get_report_scheduler
        scheduler = get_report_scheduler()
        # 创建每日报告默认任务（每天早上8点）
        settings = await _get_settings()
        keywords = settings.get("keywords", ["machine learning", "deep learning"])
        scheduler.create_task(
            name="每日学术资讯",
            task_type="daily_report",
            schedule="0 8 * * *",
            keywords=keywords,
            schedule_type="cron"
        )
        # 创建每周报告默认任务（每周一早上9点）
        scheduler.create_task(
            name="每周学术资讯",
            task_type="weekly_report",
            schedule="0 9 * * 1",
            keywords=keywords,
            schedule_type="cron"
        )
        # 创建每月报告默认任务（每月1号早上10点）
        scheduler.create_task(
            name="每月学术资讯",
            task_type="monthly_report",
            schedule="0 10 1 * *",
            keywords=keywords,
            schedule_type="cron"
        )
        # 后台启动调度器
        scheduler.start_background()
        logger.info("报告调度器已启动")

    async def _get_settings():
        """获取设置"""
        try:
            from src.agents_v2.core.config import get_settings
            return get_settings()
        except:
            return {"keywords": ["machine learning", "deep learning"]}

    app.on_startup.append(on_startup)

    async def on_shutdown(app):
        """关闭时清理资源"""
        try:
            from src.agents_v2.scheduler import get_report_scheduler
            scheduler = get_report_scheduler()
            scheduler.stop_scheduler()
        except Exception:
            pass

    app.on_shutdown.append(on_shutdown)

    async def root_handler(request: web.Request) -> web.Response:
        return web.json_response({
            "name": "Paper Research API",
            "version": "1.0",
            "docs": "/docs",
            "health": "/health"
        })

    # 路由
    app.router.add_get('/', root_handler)
    app.router.add_get('/health', health_check)
    app.router.add_get('/docs', handle_docs)
    app.router.add_post('/api/topic', handle_topic)
    app.router.add_post('/api/search', handle_search)
    app.router.add_post('/api/route', handle_route)
    app.router.add_post('/api/literature', handle_literature)
    app.router.add_post('/api/proposal', handle_proposal)
    app.router.add_post('/api/paper', handle_full_paper)
    app.router.add_post('/api/draft', handle_draft)
    app.router.add_post('/api/revise', handle_revise)
    app.router.add_post('/api/diagnostics', handle_diagnostics)
    app.router.add_post('/api/batch', handle_batch)

    # WebSocket端点
    app.router.add_get('/ws/status', handle_websocket_status)

    # Paper Agent RESTful API (frontend)
    from src.agents_v2.api.paper_api import setup_paper_routes
    setup_paper_routes(app)

    # Reports API
    from src.agents_v2.api.reports_api import setup_reports_routes
    setup_reports_routes(app)

    # Knowledge Graph API
    from src.agents_v2.api.knowledge_graph_api import setup_knowledge_graph_routes
    setup_knowledge_graph_routes(app)

    # Workflow API
    from src.agents_v2.api.workflow_api import register_routes as register_workflow_routes
    register_workflow_routes(app)

    return app


async def handle_batch(request: web.Request) -> web.Response:
    """处理批量请求"""
    start_time = time.time()
    try:
        data = await request.json()
        requests = data.get("requests", [])

        if not requests or not isinstance(requests, list):
            return web.json_response({
                "success": False,
                "error": "requests must be a non-empty array",
                "execution_time": time.time() - start_time,
                "timestamp": datetime.now().isoformat()
            }, status=400)

        results = []
        for req in requests:
            req_type = req.get("type")
            req_data = req.get("data", {})

            try:
                if req_type == "topic":
                    from src.agents_v2.paper_agents import TopicAgent
                    agent = TopicAgent()
                    result = await agent.execute({"user_request": req_data.get("user_request", "")})
                    results.append({"success": result.success, "result": result.result})
                elif req_type == "search":
                    from src.agents_v2.paper_search import PaperSearchAgent
                    agent = PaperSearchAgent()
                    result = await agent.execute(req_data.get("query", ""), {"max_results": req_data.get("max_results", 10)})
                    results.append({"success": True, "result": result.get("papers", [])})
                elif req_type == "literature":
                    from src.agents_v2.writing import LiteratureReviewAgent
                    agent = LiteratureReviewAgent()
                    result = await agent.execute({"topic": req_data.get("topic", "")})
                    results.append({"success": result.success, "result": result.result})
                else:
                    results.append({"success": False, "error": f"Unknown request type: {req_type}"})
            except Exception as e:
                results.append({"success": False, "error": str(e)})

        execution_time = time.time() - start_time
        return web.json_response({
            "success": True,
            "results": results,
            "total": len(results),
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Batch handler error: {e}")
        execution_time = time.time() - start_time
        return web.json_response({
            "success": False,
            "error": str(e),
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat()
        }, status=500)


async def handle_websocket_status(request: web.Request) -> web.WebSocketResponse:
    """WebSocket状态推送"""
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    try:
        from src.agents_v2.monitoring import get_global_metrics

        while True:
            metrics = get_global_metrics()
            await ws.send_json({
                "type": "metrics",
                "data": {
                    "total_requests": metrics.get("total_requests", 0),
                    "success_rate": metrics.get("success_rate", 0),
                    "avg_response_time": metrics.get("avg_response_time", 0),
                    "cache_hit_rate": metrics.get("cache_hit_rate", 0),
                    "timestamp": datetime.now().isoformat()
                }
            })
            await asyncio.sleep(5)  # 每5秒推送一次

    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await ws.close()

    return ws


def main():
    """主函数"""
    import asyncio
    import signal

    app = create_app()

    async def run_server():
        logger.info("Starting API server on http://0.0.0.0:8000")
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', 8000)
        await site.start()

        # 等待中断信号
        stop_event = asyncio.Event()
        loop = asyncio.get_event_loop()

        def handle_signal(sig):
            logger.info(f"收到信号 {sig}，正在关闭服务...")
            stop_event.set()

        # 注册信号处理器
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, lambda s=sig: handle_signal(s))
            except NotImplementedError:
                # Windows 不支持 add_signal_handler
                pass

        try:
            await stop_event.wait()
        except asyncio.CancelledError:
            logger.info("服务被中断")
            stop_event.set()

        # 清理
        logger.info("正在关闭服务...")
        await runner.cleanup()
        logger.info("服务已关闭")

    asyncio.run(run_server())


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n服务已停止")
