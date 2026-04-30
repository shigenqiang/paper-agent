"""
Dashboard - Web监控面板

提供系统监控、Agent状态查看和请求追踪的Web界面
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
from aiohttp import web
import json
import asyncio
import logging

logger = logging.getLogger(__name__)


class DashboardData:
    """监控面板数据提供者"""

    @staticmethod
    def get_metrics() -> Dict[str, Any]:
        """获取系统指标"""
        from src.agents_v2.monitoring import get_global_metrics

        metrics = get_global_metrics()
        return {
            "system": {
                "uptime": metrics.get("uptime", 0),
                "version": "1.0",
                "status": "healthy"
            },
            "requests": {
                "total": metrics.get("total_requests", 0),
                "success": metrics.get("successful_requests", 0),
                "failed": metrics.get("failed_requests", 0),
                "success_rate": metrics.get("success_rate", 0)
            },
            "performance": {
                "avg_response_time": metrics.get("avg_response_time", 0),
                "p95_response_time": metrics.get("p95_response_time", 0),
                "requests_per_minute": metrics.get("requests_per_minute", 0)
            },
            "cache": {
                "hit_rate": metrics.get("cache_hit_rate", 0),
                "hits": metrics.get("cache_hits", 0),
                "misses": metrics.get("cache_misses", 0)
            },
            "llm": {
                "total_calls": metrics.get("llm_calls", 0),
                "failed_calls": metrics.get("llm_failures", 0),
                "avg_latency": metrics.get("llm_avg_latency", 0)
            },
            "timestamp": datetime.now().isoformat()
        }

    @staticmethod
    def get_agent_status() -> List[Dict[str, Any]]:
        """获取Agent状态"""
        return [
            {"name": "TopicAgent", "status": "idle", "requests": 0, "avg_time": 0},
            {"name": "LiteratureAgent", "status": "idle", "requests": 0, "avg_time": 0},
            {"name": "ThesisAgent", "status": "idle", "requests": 0, "avg_time": 0},
            {"name": "OutlineAgent", "status": "idle", "requests": 0, "avg_time": 0},
            {"name": "DraftWriterAgent", "status": "idle", "requests": 0, "avg_time": 0},
            {"name": "EditorAgent", "status": "idle", "requests": 0, "avg_time": 0},
            {"name": "ReviewerAgent", "status": "idle", "requests": 0, "avg_time": 0}
        ]

    @staticmethod
    def get_recent_requests(limit: int = 20) -> List[Dict[str, Any]]:
        """获取最近请求"""
        # 模拟最近请求数据
        return [
            {
                "id": f"req_{i}",
                "endpoint": endpoint,
                "method": "POST",
                "status": 200,
                "response_time": 0.5,
                "timestamp": datetime.now().isoformat()
            }
            for i, endpoint in enumerate([
                "/api/topic", "/api/search", "/api/route",
                "/api/literature", "/api/proposal"
            ] * 4)[:limit]
        ]

    @staticmethod
    def get_circuit_breaker_status() -> Dict[str, Any]:
        """获取断路器状态"""
        return {
            "llm_circuit_breaker": {
                "status": "closed",
                "failure_count": 0,
                "last_failure": None
            },
            "search_circuit_breaker": {
                "status": "closed",
                "failure_count": 0,
                "last_failure": None
            }
        }


# HTML监控面板模板
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Paper Agent Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        :root {
            --primary: #3498db;
            --success: #27ae60;
            --warning: #f39c12;
            --danger: #e74c3c;
            --dark: #2c3e50;
            --light: #ecf0f1;
            --gray: #95a5a6;
        }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; }
        .header { background: var(--dark); color: white; padding: 20px 30px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        .header h1 { font-size: 24px; display: flex; align-items: center; gap: 10px; }
        .header-subtitle { font-size: 12px; color: var(--gray); margin-top: 4px; }
        .container { max-width: 1600px; margin: 0 auto; padding: 20px; }
        .toolbar { display: flex; gap: 12px; margin-bottom: 20px; align-items: center; flex-wrap: wrap; }
        .btn { padding: 10px 20px; border: none; border-radius: 6px; cursor: pointer; font-weight: 500; transition: all 0.3s; display: flex; align-items: center; gap: 6px; }
        .btn-primary { background: var(--primary); color: white; }
        .btn-primary:hover { background: #2980b9; transform: translateY(-1px); }
        .btn-success { background: var(--success); color: white; }
        .btn-danger { background: var(--danger); color: white; }
        .btn:disabled { opacity: 0.6; cursor: not-allowed; }
        .status-indicator { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }
        .status-healthy { background: var(--success); box-shadow: 0 0 8px var(--success); }
        .status-warning { background: var(--warning); box-shadow: 0 0 8px var(--warning); }
        .status-error { background: var(--danger); box-shadow: 0 0 8px var(--danger); }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; }
        .card { background: white; border-radius: 12px; padding: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); transition: transform 0.3s; }
        .card:hover { transform: translateY(-2px); }
        .card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
        .card-title { font-size: 14px; font-weight: 600; color: var(--dark); display: flex; align-items: center; gap: 8px; }
        .card-badge { padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 500; }
        .metric { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid var(--light); }
        .metric:last-child { border-bottom: none; }
        .metric-label { color: var(--gray); font-size: 13px; }
        .metric-value { font-weight: 600; color: var(--dark); font-size: 14px; }
        .metric-value.highlight { color: var(--primary); font-size: 18px; }
        .metric-value.success { color: var(--success); }
        .metric-value.warning { color: var(--warning); }
        .metric-value.danger { color: var(--danger); }
        .chart-container { height: 120px; display: flex; align-items: flex-end; gap: 4px; padding: 10px 0; }
        .chart-bar { flex: 1; background: linear-gradient(to top, var(--primary), #74b9ff); border-radius: 4px 4px 0 0; min-height: 4px; transition: height 0.5s ease; }
        .chart-bar.warning { background: linear-gradient(to top, var(--warning), #fdcb6e); }
        .chart-bar.danger { background: linear-gradient(to top, var(--danger), #ff7675); }
        .agent-card { display: flex; align-items: center; gap: 12px; padding: 12px; background: var(--light); border-radius: 8px; margin-bottom: 8px; }
        .agent-icon { width: 36px; height: 36px; background: var(--primary); border-radius: 8px; display: flex; align-items: center; justify-content: center; color: white; font-size: 14px; font-weight: bold; }
        .agent-info { flex: 1; }
        .agent-name { font-weight: 600; font-size: 13px; color: var(--dark); }
        .agent-stats { font-size: 11px; color: var(--gray); margin-top: 2px; }
        table { width: 100%; border-collapse: collapse; }
        th, td { text-align: left; padding: 12px 8px; border-bottom: 1px solid var(--light); font-size: 13px; }
        th { color: var(--gray); font-weight: 500; font-size: 11px; text-transform: uppercase; }
        .status-badge { display: inline-block; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: 500; }
        .badge-success { background: #d4edda; color: #155724; }
        .badge-warning { background: #fff3cd; color: #856404; }
        .badge-danger { background: #f8d7da; color: #721c24; }
        .progress-bar { height: 6px; background: var(--light); border-radius: 3px; overflow: hidden; margin-top: 8px; }
        .progress-fill { height: 100%; background: linear-gradient(90deg, var(--primary), #74b9ff); border-radius: 3px; transition: width 0.5s; }
        .tab-container { margin-bottom: 20px; }
        .tabs { display: flex; gap: 4px; background: rgba(255,255,255,0.1); padding: 4px; border-radius: 8px; }
        .tab { padding: 8px 16px; border: none; background: transparent; color: rgba(255,255,255,0.7); cursor: pointer; border-radius: 6px; font-size: 13px; transition: all 0.3s; }
        .tab.active { background: white; color: var(--dark); font-weight: 500; }
        .tab:hover:not(.active) { color: white; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        .timestamp { color: rgba(255,255,255,0.7); font-size: 12px; margin-top: 10px; text-align: center; }
        .nav-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-top: 20px; }
        .nav-item { background: rgba(255,255,255,0.1); padding: 15px; border-radius: 8px; text-align: center; color: white; cursor: pointer; transition: all 0.3s; border: 1px solid rgba(255,255,255,0.2); }
        .nav-item:hover { background: rgba(255,255,255,0.2); transform: translateY(-2px); }
        .nav-item-icon { font-size: 24px; margin-bottom: 8px; }
        .nav-item-label { font-size: 12px; }
        @media (max-width: 768px) {
            .header { padding: 15px; }
            .container { padding: 15px; }
            .grid { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
            </svg>
            Paper Agent Dashboard
        </h1>
        <div class="header-subtitle">论文智能写作系统 - 实时监控</div>
    </div>
    <div class="container">
        <div class="toolbar">
            <button class="btn btn-primary" onclick="refreshData()">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M23 4v6h-6M1 20v-6h6M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15"/>
                </svg>
                刷新数据
            </button>
            <label style="color: white; display: flex; align-items: center; gap: 8px;">
                <input type="checkbox" id="autoRefresh" checked onchange="toggleAutoRefresh()"> <span id="lbl-auto-refresh">自动刷新</span>
            </label>
            <span style="color: white; display: flex; align-items: center; gap: 8px;">
                <span class="status-indicator status-healthy" id="connection-status"></span>
                <span id="connection-text">已连接</span>
            </span>
            <select onchange="setLanguage(this.value)" style="padding: 6px 10px; border-radius: 4px; border: none; cursor: pointer;">
                <option value="zh-CN">中文</option>
                <option value="en-US">English</option>
            </select>
        </div>

        <div class="tab-container">
            <div class="tabs">
                <button class="tab active" onclick="switchTab('overview')">概览</button>
                <button class="tab" onclick="switchTab('agents')">Agent状态</button>
                <button class="tab" onclick="switchTab('performance')">性能分析</button>
                <button class="tab" onclick="switchTab('requests')">请求追踪</button>
            </div>
        </div>

        <div id="tab-overview" class="tab-content active">
            <div class="grid">
                <div class="card">
                    <div class="card-header">
                        <span class="card-title">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#3498db" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>
                            系统状态
                        </span>
                        <span class="status-badge badge-success" id="system-status-badge">运行中</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">运行状态</span>
                        <span class="metric-value"><span class="status-indicator status-healthy" id="system-status-icon"></span> <span id="system-status">健康</span></span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">版本</span>
                        <span class="metric-value" id="system-version">1.0</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">运行时间</span>
                        <span class="metric-value highlight" id="system-uptime">-</span>
                    </div>
                </div>

                <div class="card">
                    <div class="card-header">
                        <span class="card-title">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#3498db" stroke-width="2"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
                            请求统计
                        </span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">总请求数</span>
                        <span class="metric-value highlight" id="req-total">0</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">成功</span>
                        <span class="metric-value success" id="req-success">0</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">失败</span>
                        <span class="metric-value danger" id="req-failed">0</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">成功率</span>
                        <span class="metric-value" id="req-success-rate">0%</span>
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill" id="success-rate-bar" style="width: 100%"></div>
                    </div>
                </div>

                <div class="card">
                    <div class="card-header">
                        <span class="card-title">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#3498db" stroke-width="2"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>
                            性能指标
                        </span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">平均响应时间</span>
                        <span class="metric-value" id="perf-avg-time">0ms</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">P95响应时间</span>
                        <span class="metric-value" id="perf-p95-time">0ms</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">请求/分钟</span>
                        <span class="metric-value highlight" id="perf-rpm">0</span>
                    </div>
                    <div class="chart-container" id="perf-chart">
                        <div class="chart-bar" style="height: 20%"></div>
                        <div class="chart-bar" style="height: 40%"></div>
                        <div class="chart-bar" style="height: 30%"></div>
                        <div class="chart-bar" style="height: 60%"></div>
                        <div class="chart-bar" style="height: 50%"></div>
                        <div class="chart-bar" style="height: 70%"></div>
                        <div class="chart-bar" style="height: 45%"></div>
                        <div class="chart-bar" style="height: 55%"></div>
                        <div class="chart-bar" style="height: 35%"></div>
                        <div class="chart-bar" style="height: 65%"></div>
                    </div>
                </div>

                <div class="card">
                    <div class="card-header">
                        <span class="card-title">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#3498db" stroke-width="2"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12"/></svg>
                            缓存状态
                        </span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">命中率</span>
                        <span class="metric-value highlight" id="cache-hit-rate">0%</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">命中次数</span>
                        <span class="metric-value success" id="cache-hits">0</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">未命中次数</span>
                        <span class="metric-value" id="cache-misses">0</span>
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill" id="cache-hit-bar" style="width: 0%"></div>
                    </div>
                </div>

                <div class="card">
                    <div class="card-header">
                        <span class="card-title">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#3498db" stroke-width="2"><path d="M12 2a10 10 0 1010 10A10 10 0 0012 2zm0 18a8 8 0 118-8 8 8 0 01-8 8z"/><path d="M12 6v6l4 2"/></svg>
                            LLM状态
                        </span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">总调用数</span>
                        <span class="metric-value highlight" id="llm-calls">0</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">失败调用</span>
                        <span class="metric-value danger" id="llm-failures">0</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">平均延迟</span>
                        <span class="metric-value" id="llm-latency">0ms</span>
                    </div>
                    <div class="chart-container" id="llm-chart">
                        <div class="chart-bar" style="height: 30%"></div>
                        <div class="chart-bar" style="height: 50%"></div>
                        <div class="chart-bar" style="height: 40%"></div>
                        <div class="chart-bar" style="height: 70%"></div>
                        <div class="chart-bar" style="height: 60%"></div>
                        <div class="chart-bar" style="height: 80%"></div>
                        <div class="chart-bar" style="height: 55%"></div>
                        <div class="chart-bar" style="height: 65%"></div>
                        <div class="chart-bar" style="height: 45%"></div>
                        <div class="chart-bar" style="height: 75%"></div>
                    </div>
                </div>

                <div class="card">
                    <div class="card-header">
                        <span class="card-title">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#3498db" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0110 0v4"/></svg>
                            断路器状态
                        </span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">LLM断路器</span>
                        <span class="metric-value"><span class="status-badge badge-success" id="cb-llm-status">关闭</span></span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">失败计数</span>
                        <span class="metric-value" id="cb-llm-failures">0</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">搜索断路器</span>
                        <span class="metric-value"><span class="status-badge badge-success" id="cb-search-status">关闭</span></span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">失败计数</span>
                        <span class="metric-value" id="cb-search-failures">0</span>
                    </div>
                </div>
            </div>
        </div>

        <div id="tab-agents" class="tab-content">
            <div class="grid" id="agent-grid">
                <div class="card">
                    <div class="card-header">
                        <span class="card-title">Pipeline Agents</span>
                    </div>
                    <div id="pipeline-agents-list"></div>
                </div>
                <div class="card">
                    <div class="card-header">
                        <span class="card-title">Problem-Oriented Agents</span>
                    </div>
                    <div id="problem-agents-list"></div>
                </div>
                <div class="card">
                    <div class="card-header">
                        <span class="card-title">Writing Agents</span>
                    </div>
                    <div id="writing-agents-list"></div>
                </div>
                <div class="card">
                    <div class="card-header">
                        <span class="card-title">QA Agents</span>
                    </div>
                    <div id="qa-agents-list"></div>
                </div>
            </div>
        </div>

        <div id="tab-performance" class="tab-content">
            <div class="grid">
                <div class="card">
                    <div class="card-header">
                        <span class="card-title">响应时间分布</span>
                    </div>
                    <div class="chart-container" style="height: 200px;" id="response-time-chart"></div>
                </div>
                <div class="card">
                    <div class="card-header">
                        <span class="card-title">吞吐量趋势</span>
                    </div>
                    <div class="chart-container" style="height: 200px;" id="throughput-chart"></div>
                </div>
            </div>
        </div>

        <div id="tab-requests" class="tab-content">
            <div class="card">
                <table>
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>端点</th>
                            <th>方法</th>
                            <th>状态</th>
                            <th>响应时间</th>
                            <th>时间</th>
                        </tr>
                    </thead>
                    <tbody id="recent-requests">
                        <tr><td colspan="6">加载中...</td></tr>
                    </tbody>
                </table>
            </div>
        </div>

        <p class="timestamp">最后更新: <span id="last-update">-</span></p>
    </div>

    <script>
        // 国际化支持
        const i18n = {
            'zh-CN': {
                'title': 'Paper Agent Dashboard',
                'subtitle': '论文智能写作系统 - 实时监控',
                'refresh': '刷新数据',
                'auto_refresh': '自动刷新',
                'connected': '已连接',
                'websocket': '实时连接',
                'sse': 'SSE连接',
                'polling': 'HTTP轮询',
                'disconnected': '连接失败',
                'tabs': {
                    'overview': '概览',
                    'agents': 'Agent状态',
                    'performance': '性能分析',
                    'requests': '请求追踪'
                },
                'system': {
                    'title': '系统状态',
                    'status': '运行状态',
                    'healthy': '健康',
                    'error': '异常',
                    'version': '版本',
                    'uptime': '运行时间'
                },
                'requests': {
                    'title': '请求统计',
                    'total': '总请求数',
                    'success': '成功',
                    'failed': '失败',
                    'success_rate': '成功率'
                },
                'performance': {
                    'title': '性能指标',
                    'avg_time': '平均响应时间',
                    'p95_time': 'P95响应时间',
                    'rpm': '请求/分钟'
                },
                'cache': {
                    'title': '缓存状态',
                    'hit_rate': '命中率',
                    'hits': '命中次数',
                    'misses': '未命中次数'
                },
                'llm': {
                    'title': 'LLM状态',
                    'calls': '总调用数',
                    'failures': '失败调用',
                    'latency': '平均延迟'
                },
                'circuit_breaker': {
                    'title': '断路器状态',
                    'llm': 'LLM断路器',
                    'search': '搜索断路器',
                    'failures': '失败计数',
                    'closed': '关闭',
                    'open': '打开',
                    'half_open': '半开'
                },
                'agents': {
                    'pipeline': 'Pipeline Agents',
                    'problem': 'Problem-Oriented Agents',
                    'writing': 'Writing Agents',
                    'qa': 'QA Agents'
                },
                'last_update': '最后更新'
            },
            'en-US': {
                'title': 'Paper Agent Dashboard',
                'subtitle': 'Paper Writing System - Real-time Monitoring',
                'refresh': 'Refresh',
                'auto_refresh': 'Auto Refresh',
                'connected': 'Connected',
                'websocket': 'WebSocket',
                'sse': 'SSE',
                'polling': 'HTTP Polling',
                'disconnected': 'Disconnected',
                'tabs': {
                    'overview': 'Overview',
                    'agents': 'Agents',
                    'performance': 'Performance',
                    'requests': 'Requests'
                },
                'system': {
                    'title': 'System',
                    'status': 'Status',
                    'healthy': 'Healthy',
                    'error': 'Error',
                    'version': 'Version',
                    'uptime': 'Uptime'
                },
                'requests': {
                    'title': 'Requests',
                    'total': 'Total',
                    'success': 'Success',
                    'failed': 'Failed',
                    'success_rate': 'Success Rate'
                },
                'performance': {
                    'title': 'Performance',
                    'avg_time': 'Avg Response',
                    'p95_time': 'P95 Response',
                    'rpm': 'Req/min'
                },
                'cache': {
                    'title': 'Cache',
                    'hit_rate': 'Hit Rate',
                    'hits': 'Hits',
                    'misses': 'Misses'
                },
                'llm': {
                    'title': 'LLM',
                    'calls': 'Total Calls',
                    'failures': 'Failures',
                    'latency': 'Avg Latency'
                },
                'circuit_breaker': {
                    'title': 'Circuit Breakers',
                    'llm': 'LLM CB',
                    'search': 'Search CB',
                    'failures': 'Failures',
                    'closed': 'Closed',
                    'open': 'Open',
                    'half_open': 'Half Open'
                },
                'agents': {
                    'pipeline': 'Pipeline Agents',
                    'problem': 'Problem-Oriented Agents',
                    'writing': 'Writing Agents',
                    'qa': 'QA Agents'
                },
                'last_update': 'Last Update'
            }
        };

        let currentLang = 'zh-CN';
        let autoRefreshEnabled = true;
        let refreshInterval = null;
        let wsConnection = null;
        let sseSource = null;
        let historyData = { perf: [], llm: [], requests: 0 };
        let useWebSocket = true;

        function setLanguage(lang) {
            currentLang = lang;
            localStorage.setItem('dashboard_lang', lang);
            // 页面刷新以应用新语言
            location.reload();
        }

        function t(key) {
            const keys = key.split('.');
            let value = i18n[currentLang];
            for (const k of keys) {
                value = value?.[k];
            }
            return value || key;
        }

        function switchTab(tabName) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            document.querySelector(`[onclick="switchTab('${tabName}')"]`).classList.add('active');
            document.getElementById(`tab-${tabName}`).classList.add('active');
        }

        function toggleAutoRefresh() {
            autoRefreshEnabled = document.getElementById('autoRefresh').checked;
            if (autoRefreshEnabled) {
                if (useWebSocket) connectWebSocket();
                else connectSSE();
            } else {
                disconnectAll();
            }
        }

        function disconnectAll() {
            if (wsConnection) {
                wsConnection.close();
                wsConnection = null;
            }
            if (sseSource) {
                sseSource.close();
                sseSource = null;
            }
            if (refreshInterval) {
                clearInterval(refreshInterval);
                refreshInterval = null;
            }
        }

        function connectWebSocket() {
            disconnectAll();
            try {
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const wsUrl = `${protocol}//${window.location.host}/ws/status`;

                wsConnection = new WebSocket(wsUrl);

                wsConnection.onopen = () => {
                    console.log('WebSocket connected');
                    document.getElementById('connection-status').className = 'status-indicator status-healthy';
                    document.getElementById('connection-text').textContent = '实时连接';
                };

                wsConnection.onmessage = (event) => {
                    try {
                        const msg = JSON.parse(event.data);
                        if (msg.type === 'metrics') {
                            updateFromWebSocket(msg.data);
                        }
                    } catch (e) {
                        console.error('Failed to parse WebSocket message:', e);
                    }
                };

                wsConnection.onerror = (error) => {
                    console.error('WebSocket error, falling back to HTTP', error);
                    useWebSocket = false;
                    connectSSE();
                };

                wsConnection.onclose = () => {
                    if (autoRefreshEnabled) {
                        setTimeout(connectWebSocket, 5000);
                    }
                };

            } catch (e) {
                console.error('WebSocket connection failed, using HTTP polling', e);
                useWebSocket = false;
                startAutoRefresh();
            }
        }

        function connectSSE() {
            disconnectAll();
            try {
                sseSource = new EventSource('/api/metrics/stream');

                sseSource.onopen = () => {
                    document.getElementById('connection-status').className = 'status-indicator status-healthy';
                    document.getElementById('connection-text').textContent = 'SSE连接';
                };

                sseSource.onmessage = (event) => {
                    try {
                        const data = JSON.parse(event.data);
                        updateDashboard(data);
                    } catch (e) {
                        console.error('Failed to parse SSE message:', e);
                    }
                };

                sseSource.onerror = () => {
                    console.error('SSE error, falling back to HTTP polling');
                    sseSource.close();
                    startAutoRefresh();
                };

            } catch (e) {
                console.error('SSE connection failed, using HTTP polling', e);
                startAutoRefresh();
            }
        }

        function updateFromWebSocket(data) {
            document.getElementById('req-total').textContent = data.total_requests || 0;
            document.getElementById('req-success-rate').textContent = ((data.success_rate || 0) * 100).toFixed(1) + '%';
            document.getElementById('perf-avg-time').textContent = ((data.avg_response_time || 0) * 1000).toFixed(0) + 'ms';
            document.getElementById('cache-hit-rate').textContent = ((data.cache_hit_rate || 0) * 100).toFixed(1) + '%';
            document.getElementById('last-update').textContent = new Date().toLocaleString();

            // 添加到历史
            historyData.perf.push((data.avg_response_time || 0) * 100);
            if (historyData.perf.length > 10) historyData.perf.shift();
            updateChart('perf-chart', historyData.perf);
        }

        function updateDashboard(data) {
            document.getElementById('system-version').textContent = data.system?.version || '1.0';
            document.getElementById('system-uptime').textContent = formatUptime(data.system?.uptime || 0);
            document.getElementById('req-total').textContent = data.requests?.total || 0;
            document.getElementById('req-success').textContent = data.requests?.success || 0;
            document.getElementById('req-failed').textContent = data.requests?.failed || 0;

            const successRate = ((data.requests?.success_rate || 0) * 100).toFixed(1);
            document.getElementById('req-success-rate').textContent = successRate + '%';
            document.getElementById('success-rate-bar').style.width = successRate + '%';

            document.getElementById('perf-avg-time').textContent = ((data.performance?.avg_response_time || 0) * 1000).toFixed(0) + 'ms';
            document.getElementById('perf-p95-time').textContent = ((data.performance?.p95_response_time || 0) * 1000).toFixed(0) + 'ms';
            document.getElementById('perf-rpm').textContent = data.performance?.requests_per_minute || 0;

            const hitRate = ((data.cache?.hit_rate || 0) * 100).toFixed(1);
            document.getElementById('cache-hit-rate').textContent = hitRate + '%';
            document.getElementById('cache-hit-bar').style.width = hitRate + '%';

            document.getElementById('llm-calls').textContent = data.llm?.total_calls || 0;
            document.getElementById('llm-latency').textContent = ((data.llm?.avg_latency || 0) * 1000).toFixed(0) + 'ms';

            document.getElementById('last-update').textContent = new Date().toLocaleString();
        }

        function startAutoRefresh() {
            if (refreshInterval) clearInterval(refreshInterval);
            refreshInterval = setInterval(refreshData, 5000);
            document.getElementById('connection-status').className = 'status-indicator status-warning';
            document.getElementById('connection-text').textContent = 'HTTP轮询';
        }

        async function refreshData() {
            try {
                const response = await fetch('/api/metrics');
                const data = await response.json();
                updateDashboard(data);
                document.getElementById('connection-status').className = 'status-indicator status-healthy';
                document.getElementById('connection-text').textContent = 'HTTP轮询';

                historyData.perf.push((data.performance?.avg_response_time || 0) * 1000);
                if (historyData.perf.length > 10) historyData.perf.shift();
                updateChart('perf-chart', historyData.perf);

            } catch (e) {
                console.error('Failed to refresh data:', e);
                document.getElementById('connection-status').className = 'status-indicator status-error';
                document.getElementById('connection-text').textContent = '连接失败';
            }
        }

        async function loadAgentStatus() {
            try {
                const response = await fetch('/api/agents');
                const agents = await response.json();

                const containers = {
                    'pipeline': document.getElementById('pipeline-agents-list'),
                    'problem': document.getElementById('problem-agents-list'),
                    'writing': document.getElementById('writing-agents-list'),
                    'qa': document.getElementById('qa-agents-list')
                };

                Object.keys(containers).forEach(k => {
                    if (containers[k]) containers[k].innerHTML = '';
                });

                agents.forEach(agent => {
                    const statusClass = agent.status === 'running' ? 'badge-warning' :
                                       agent.status === 'error' ? 'badge-danger' : 'badge-success';
                    const statusText = agent.status === 'running' ? '运行中' :
                                      agent.status === 'error' ? '错误' : '空闲';

                    const html = `
                        <div class="agent-card">
                            <div class="agent-icon">${agent.name.charAt(0)}</div>
                            <div class="agent-info">
                                <div class="agent-name">${agent.name}</div>
                                <div class="agent-stats">请求: ${agent.requests} | 平均: ${agent.avg_time.toFixed(2)}s</div>
                            </div>
                            <span class="status-badge ${statusClass}">${statusText}</span>
                        </div>
                    `;

                    const container = containers[getAgentCategory(agent.name)];
                    if (container) container.innerHTML += html;
                });
            } catch (e) {
                console.error('Failed to load agent status:', e);
            }
        }

        function getAgentCategory(name) {
            if (name.includes('Topic') || name.includes('Literature') || name.includes('Thesis') ||
                name.includes('Outline') || name.includes('Draft')) return 'pipeline';
            if (name.includes('Problem') || name.includes('Diagnosis')) return 'problem';
            if (name.includes('Writing') || name.includes('Editor')) return 'writing';
            return 'qa';
        }

        function updateChart(chartId, history) {
            const chart = document.getElementById(chartId);
            if (!chart) return;

            const bars = chart.querySelectorAll('.chart-bar');
            bars.forEach((bar, i) => {
                if (i < history.length) {
                    const val = Math.min(100, Math.max(10, history[history.length - 1 - i]));
                    bar.style.height = val + '%';
                    if (val > 70) bar.className = 'chart-bar danger';
                    else if (val > 50) bar.className = 'chart-bar warning';
                    else bar.className = 'chart-bar';
                }
            });
        }

        function formatUptime(seconds) {
            if (!seconds) return '-';
            const hours = Math.floor(seconds / 3600);
            const minutes = Math.floor((seconds % 3600) / 60);
            const secs = Math.floor(seconds % 60);
            return `${hours}小时${minutes}分钟${secs}秒`;
        }

        // 初始化
        refreshData();
        loadAgentStatus();
        if (autoRefreshEnabled) {
            if (useWebSocket) connectWebSocket();
            else startAutoRefresh();
        }
    </script>
</body>
</html>
"""


class DashboardServer:
    """监控面板服务器"""

    @staticmethod
    async def get_home(request: web.Request) -> web.Response:
        """返回HTML监控页面"""
        return web.Response(
            text=DASHBOARD_HTML,
            content_type='text/html',
            charset='utf-8'
        )

    @staticmethod
    async def get_metrics_json(request: web.Request) -> web.Response:
        """返回JSON格式指标"""
        metrics = DashboardData.get_metrics()
        return web.json_response(metrics)

    @staticmethod
    async def get_agent_list(request: web.Request) -> web.Response:
        """返回Agent列表"""
        agents = DashboardData.get_agent_status()
        return web.json_response(agents)

    @staticmethod
    async def get_recent_requests(request: web.Request) -> web.Response:
        """返回最近请求列表"""
        limit = int(request.query.get('limit', 20))
        requests = DashboardData.get_recent_requests(limit)
        return web.json_response(requests)

    @staticmethod
    async def get_circuit_breakers(request: web.Request) -> web.Response:
        """返回断路器状态"""
        status = DashboardData.get_circuit_breaker_status()
        return web.json_response(status)

    @staticmethod
    async def stream_metrics(request: web.Request) -> web.Response:
        """SSE流式推送指标"""
        response = web.StreamResponse(
            status=200,
            headers={
                'Content-Type': 'text/event-stream',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'Access-Control-Allow-Origin': '*'
            }
        )
        await response.prepare(request)

        try:
            while True:
                metrics = DashboardData.get_metrics()
                response.write(f"data: {json.dumps(metrics)}\n\n".encode())
                await asyncio.sleep(5)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"SSE stream error: {e}")
        finally:
            await response.write_eof()

        return response
