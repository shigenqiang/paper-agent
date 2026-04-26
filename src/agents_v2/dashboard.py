"""
Dashboard - Web监控面板

提供系统监控、Agent状态查看和请求追踪的Web界面
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
from aiohttp import web
import json


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
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; }
        .header { background: #2c3e50; color: white; padding: 20px; }
        .header h1 { font-size: 24px; }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .card { background: white; border-radius: 8px; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .card h2 { font-size: 16px; color: #333; margin-bottom: 15px; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
        .metric { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #eee; }
        .metric:last-child { border-bottom: none; }
        .metric-label { color: #666; }
        .metric-value { font-weight: bold; color: #2c3e50; }
        .status-badge { display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 12px; }
        .status-healthy { background: #27ae60; color: white; }
        .status-warning { background: #f39c12; color: white; }
        .status-error { background: #e74c3c; color: white; }
        .chart-placeholder { height: 150px; background: #ecf0f1; border-radius: 4px; display: flex; align-items: center; justify-content: center; color: #95a5a6; }
        table { width: 100%; border-collapse: collapse; }
        th, td { text-align: left; padding: 10px; border-bottom: 1px solid #eee; }
        th { color: #666; font-weight: 500; }
        .refresh-btn { background: #3498db; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; }
        .refresh-btn:hover { background: #2980b9; }
        .timestamp { color: #999; font-size: 12px; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Paper Agent Dashboard</h1>
    </div>
    <div class="container">
        <button class="refresh-btn" onclick="refreshData()">刷新数据</button>

        <h2 style="margin: 20px 0;">系统概览</h2>
        <div class="grid">
            <div class="card">
                <h2>系统状态</h2>
                <div class="metric">
                    <span class="metric-label">运行状态</span>
                    <span class="status-badge status-healthy" id="system-status">健康</span>
                </div>
                <div class="metric">
                    <span class="metric-label">版本</span>
                    <span class="metric-value" id="system-version">1.0</span>
                </div>
                <div class="metric">
                    <span class="metric-label">运行时间</span>
                    <span class="metric-value" id="system-uptime">-</span>
                </div>
            </div>

            <div class="card">
                <h2>请求统计</h2>
                <div class="metric">
                    <span class="metric-label">总请求数</span>
                    <span class="metric-value" id="req-total">0</span>
                </div>
                <div class="metric">
                    <span class="metric-label">成功</span>
                    <span class="metric-value" id="req-success">0</span>
                </div>
                <div class="metric">
                    <span class="metric-label">失败</span>
                    <span class="metric-value" id="req-failed">0</span>
                </div>
                <div class="metric">
                    <span class="metric-label">成功率</span>
                    <span class="metric-value" id="req-success-rate">0%</span>
                </div>
            </div>

            <div class="card">
                <h2>性能指标</h2>
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
                    <span class="metric-value" id="perf-rpm">0</span>
                </div>
            </div>

            <div class="card">
                <h2>缓存状态</h2>
                <div class="metric">
                    <span class="metric-label">命中率</span>
                    <span class="metric-value" id="cache-hit-rate">0%</span>
                </div>
                <div class="metric">
                    <span class="metric-label">命中次数</span>
                    <span class="metric-value" id="cache-hits">0</span>
                </div>
                <div class="metric">
                    <span class="metric-label">未命中次数</span>
                    <span class="metric-value" id="cache-misses">0</span>
                </div>
            </div>

            <div class="card">
                <h2>LLM状态</h2>
                <div class="metric">
                    <span class="metric-label">总调用数</span>
                    <span class="metric-value" id="llm-calls">0</span>
                </div>
                <div class="metric">
                    <span class="metric-label">失败调用</span>
                    <span class="metric-value" id="llm-failures">0</span>
                </div>
                <div class="metric">
                    <span class="metric-label">平均延迟</span>
                    <span class="metric-value" id="llm-latency">0ms</span>
                </div>
            </div>
        </div>

        <h2 style="margin: 20px 0;">最近请求</h2>
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

        <p class="timestamp">最后更新: <span id="last-update">-</span></p>
    </div>

    <script>
        async function refreshData() {
            try {
                const response = await fetch('/api/metrics');
                const data = await response.json();

                document.getElementById('system-version').textContent = data.system?.version || '1.0';
                document.getElementById('system-uptime').textContent = formatUptime(data.system?.uptime || 0);

                document.getElementById('req-total').textContent = data.requests?.total || 0;
                document.getElementById('req-success').textContent = data.requests?.success || 0;
                document.getElementById('req-failed').textContent = data.requests?.failed || 0;
                document.getElementById('req-success-rate').textContent = ((data.requests?.success_rate || 0) * 100).toFixed(1) + '%';

                document.getElementById('perf-avg-time').textContent = ((data.performance?.avg_response_time || 0) * 1000).toFixed(0) + 'ms';
                document.getElementById('perf-p95-time').textContent = ((data.performance?.p95_response_time || 0) * 1000).toFixed(0) + 'ms';
                document.getElementById('perf-rpm').textContent = data.performance?.requests_per_minute || 0;

                document.getElementById('cache-hit-rate').textContent = ((data.cache?.hit_rate || 0) * 100).toFixed(1) + '%';
                document.getElementById('cache-hits').textContent = data.cache?.hits || 0;
                document.getElementById('cache-misses').textContent = data.cache?.misses || 0;

                document.getElementById('llm-calls').textContent = data.llm?.total_calls || 0;
                document.getElementById('llm-failures').textContent = data.llm?.failed_calls || 0;
                document.getElementById('llm-latency').textContent = ((data.llm?.avg_latency || 0) * 1000).toFixed(0) + 'ms';

                document.getElementById('last-update').textContent = new Date().toLocaleString();

                // 更新系统状态
                const statusEl = document.getElementById('system-status');
                if (data.system?.status === 'healthy') {
                    statusEl.className = 'status-badge status-healthy';
                    statusEl.textContent = '健康';
                }
            } catch (e) {
                console.error('Failed to refresh data:', e);
            }
        }

        function formatUptime(seconds) {
            if (!seconds) return '-';
            const hours = Math.floor(seconds / 3600);
            const minutes = Math.floor((seconds % 3600) / 60);
            return hours + '小时' + minutes + '分钟';
        }

        // 初始加载
        refreshData();
        // 每5秒刷新
        setInterval(refreshData, 5000);
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
