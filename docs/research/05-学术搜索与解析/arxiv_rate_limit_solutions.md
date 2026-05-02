# arXiv 限流问题解决方案完整指南

> 更新时间：2026年5月
>
> 针对 arXiv 限流问题的全面解决方案汇总

---

## 一、arXiv API 官方限制说明

### 1.1 官方速率限制

根据 arXiv 官方文档和社区经验，arXiv API 的限制主要包括：

| 限制类型 | 具体数值 | 说明 |
|---------|---------|------|
| **推荐请求间隔** | **≥ 3 秒/次** | 两次请求之间的最小间隔 |
| **最大请求频率** | **≤ 1 请求/3秒** | 保守使用建议 |
| **每小时请求上限** | **约 4000 次** | 部分用户报告触发限流的阈值 |
| **单次最大结果数** | **2000 条** | 超过会返回错误 |
| **每日建议上限** | **< 5000 次** | 保持长期稳定使用 |

### 1.2 触发限流的常见原因

- 请求频率过高（连续快速请求）
- 同时从多个进程/线程发起请求
- 大规模批量下载 PDF 文件
- 使用自动化脚本未添加适当延迟
- 短时间内请求量超过阈值

### 1.3 限流后的错误表现

```xml
<!-- HTTP 429 Too Many Requests -->
<!-- 服务器可能返回 Retry-After 头 -->
HTTP/1.1 429 Too Many Requests
Retry-After: 30
Content-Type: application/xml
```

---

## 二、核心解决方案

### 方案一：请求频率控制（最基础、最有效）

#### 1. 基础延迟实现

```python
import time
import random

def safe_request(url):
    """安全的请求函数，包含适当的延迟"""
    # 每次请求间隔 3-5 秒（带随机抖动，避免被识别为机器人）
    delay = random.uniform(3, 5)
    time.sleep(delay)

    # 执行实际请求
    response = requests.get(url)
    return response
```

#### 2. 使用 Tenacity 库实现智能重试

```python
from tenacity import retry, wait_exponential, retry_if_exception_type, stop_after_attempt
import requests

@retry(
    wait=wait_exponential(multiplier=1, min=10, max=120),
    retry=retry_if_exception_type(requests.exceptions.RequestException),
    stop=stop_after_attempt(5)
)
def fetch_with_smart_retry(url):
    """智能重试机制，自动指数退避"""
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response
```

#### 3. 令牌桶限流器实现

```python
import time
from threading import Lock

class RateLimiter:
    """令牌桶限流器"""

    def __init__(self, rate=1/3, capacity=1):
        """
        Args:
            rate: 每秒产生的令牌数
            capacity: 桶的容量
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.time()
        self.lock = Lock()

    def acquire(self):
        """获取令牌，如果桶为空则等待"""
        with self.lock:
            now = time.time()
            # 更新令牌数量
            elapsed = now - self.last_update
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            self.last_update = now

            if self.tokens >= 1:
                self.tokens -= 1
                return True
            else:
                # 计算需要等待的时间
                wait_time = (1 - self.tokens) / self.rate
                time.sleep(wait_time)
                self.tokens = 0
                self.last_update = time.time()
                return True

# 使用示例
limiter = RateLimiter(rate=1/3, capacity=1)  # 每3秒一个令牌

for url in urls:
    limiter.acquire()  # 自动限流
    response = requests.get(url)
```

#### 4. 使用 Guava RateLimiter

```python
from guava.ratelimiter import RateLimiter

# 创建一个每秒1/3个请求的限流器（每3秒1个请求）
limiter = RateLimiter.create(0.33)

for url in urls:
    limiter.acquire()  # 阻塞直到获取到令牌
    response = requests.get(url)
```

---

### 方案二：429 错误处理

#### 1. 解析 Retry-After 响应头

```python
import requests
import time

def handle_429_with_retry_after(response):
    """处理 429 错误，读取 Retry-After 头"""
    if response.status_code == 429:
        retry_after = response.headers.get('Retry-After')

        if retry_after:
            wait_time = int(retry_after)
        else:
            # 无 Retry-After 时使用指数退避
            wait_time = 60

        print(f"Rate limited. Waiting {wait_time}s...")
        time.sleep(wait_time)
        return True
    return False

# 在请求中使用
def safe_get(url, max_retries=5):
    for attempt in range(max_retries):
        response = requests.get(url)

        if handle_429_with_retry_after(response):
            continue

        return response

    raise Exception(f"Failed after {max_retries} retries")
```

#### 2. 指数退避策略

```python
import time
import random

def exponential_backoff(attempt, base_delay=10, max_delay=600):
    """指数退避策略"""
    # 基础延迟 * 2^尝试次数 + 随机抖动
    delay = min(base_delay * (2 ** attempt) + random.uniform(0, 5), max_delay)
    return delay

def request_with_backoff(url, max_attempts=5):
    """带指数退避的请求"""
    for attempt in range(max_attempts):
        try:
            response = requests.get(url, timeout=30)

            if response.status_code == 429:
                wait_time = exponential_backoff(attempt)
                print(f"Attempt {attempt + 1}: Rate limited. Waiting {wait_time:.2f}s...")
                time.sleep(wait_time)
                continue

            response.raise_for_status()
            return response

        except requests.exceptions.RequestException as e:
            if attempt < max_attempts - 1:
                wait_time = exponential_backoff(attempt)
                print(f"Attempt {attempt + 1} failed: {e}. Retrying in {wait_time:.2f}s...")
                time.sleep(wait_time)
            else:
                raise

    raise Exception(f"Failed after {max_attempts} attempts")
```

---

### 方案三：使用中国镜像加速访问

#### 3.1 国内镜像站点列表

| 镜像名称 | 镜像地址 | 状态 | 速度 | 备注 |
|---------|---------|------|------|------|
| **中科院理论物理所** | `http://xxx.itp.ac.cn` | ✅ 正常 | 快 | **推荐使用** |
| **中科大镜像** | `cn.arxiv.org` | ⚠️ 不稳定 | 快 | 有时失效 |
| **国际镜像** | `de.arxiv.org` | ✅ 正常 | 一般 | 欧洲用户 |
| **印度镜像** | `in.arxiv.org` | ✅ 正常 | 一般 | 亚洲用户 |
| **日本镜像** | `jp.arxiv.org` | ✅ 正常 | 一般 | 日本用户 |

#### 3.2 镜像地址转换规则

```
# 原地址
https://arxiv.org/abs/2003.00911
https://arxiv.org/pdf/2003.00911.pdf

# 转换为中科院镜像
http://xxx.itp.ac.cn/abs/2003.00911
http://xxx.itp.ac.cn/pdf/2003.00911.pdf

# 或使用 cn.arxiv.org
http://cn.arxiv.org/abs/2003.00911
http://cn.arxiv.org/pdf/2003.00911.pdf
```

#### 3.3 Python 实现镜像自动切换

```python
import requests
from urllib.parse import urlparse

class ArxivMirrorManager:
    """arXiv 镜像管理器"""

    # 镜像列表，按优先级排序
    MIRRORS = [
        'http://xxx.itp.ac.cn',
        'http://cn.arxiv.org',
        'http://in.arxiv.org',
        'https://arxiv.org',  # 原始地址作为最后备选
    ]

    def __init__(self):
        self.current_mirror = self.MIRRORS[0]

    def convert_url(self, url):
        """将 arXiv URL 转换为镜像 URL"""
        parsed = urlparse(url)

        if 'arxiv.org' not in parsed.netloc:
            return url  # 非 arXiv URL，不做处理

        # 替换域名为当前镜像
        new_netloc = self.current_mirror.replace('http://', '').replace('https://', '')
        new_url = url.replace(parsed.netloc, new_netloc)

        return new_url

    def test_mirror(self, mirror_url):
        """测试镜像是否可用"""
        test_url = f"{mirror_url}/"
        try:
            response = requests.get(test_url, timeout=5)
            return response.status_code == 200
        except:
            return False

    def select_best_mirror(self):
        """自动选择可用的最佳镜像"""
        for mirror in self.MIRRORS:
            if self.test_mirror(mirror):
                self.current_mirror = mirror
                print(f"Selected mirror: {mirror}")
                return mirror

        # 所有镜像都失败，使用原始地址
        self.current_mirror = 'https://arxiv.org'
        print("All mirrors failed, using original arXiv.org")
        return self.current_mirror

# 使用示例
manager = ArxivMirrorManager()
manager.select_best_mirror()

# 转换 URL
original_url = "https://arxiv.org/pdf/2003.00911.pdf"
mirrored_url = manager.convert_url(original_url)
print(f"Original: {original_url}")
print(f"Mirrored: {mirrored_url}")
```

#### 3.4 wget 命令行下载加速

```bash
# 使用 --user-agent=Lynx 伪装用户代理，加速下载
wget --user-agent=Lynx https://arxiv.org/pdf/1911.05722.pdf

# 下载到指定目录
wget -P /path/to/save/ --user-agent=Lynx https://arxiv.org/pdf/1911.05722.pdf

# Windows PowerShell 版本
Invoke-WebRequest -Uri "https://arxiv.org/pdf/1911.05722.pdf" -OutFile "paper.pdf" -UserAgent "Lynx"
```

---

### 方案四：浏览器脚本自动重定向（Tampermonkey）

#### 4.1 安装油猴脚本

1. 安装 [Tampermonkey](https://www.tampermonkey.net/) 浏览器插件
2. 点击插件图标 → 创建新脚本

#### 4.2 自动重定向脚本

```javascript
// ==UserScript==
// @name         arXiv 自动重定向到国内镜像
// @namespace    http://tampermonkey.net/
// @version      1.2
// @description  自动将 arXiv 链接重定向到国内镜像，提升下载速度
// @author       Your Name
// @match        https://arxiv.org/*
// @grant        none
// ==/UserScript==

(function() {
    'use strict';

    // 镜像地址列表（按优先级）
    const MIRRORS = [
        'http://xxx.itp.ac.cn',
        'http://cn.arxiv.org'
    ];

    let currentMirror = MIRRORS[0];

    // 测试镜像可用性
    async function testMirror(mirror) {
        try {
            const response = await fetch(mirror, {
                method: 'HEAD',
                mode: 'no-cors'
            });
            return true;
        } catch {
            return false;
        }
    }

    // 初始化时选择可用镜像
    async function init() {
        for (const mirror of MIRRORS) {
            if (await testMirror(mirror)) {
                currentMirror = mirror;
                console.log('ArXiv Mirror: Selected', currentMirror);
                break;
            }
        }
    }

    // 重定向函数
    function redirectToMirror() {
        // 处理 PDF 链接
        document.querySelectorAll('a[href*="arxiv.org/pdf"]').forEach(link => {
            const href = link.getAttribute('href');
            if (href && !href.includes('xxx.itp.ac.cn') && !href.includes('cn.arxiv.org')) {
                link.setAttribute('href', href.replace('https://arxiv.org', currentMirror));
            }
        });

        // 处理 Abstract 页面链接
        document.querySelectorAll('a[href*="arxiv.org/abs"]').forEach(link => {
            const href = link.getAttribute('href');
            if (href && !href.includes('xxx.itp.ac.cn') && !href.includes('cn.arxiv.org')) {
                link.setAttribute('href', href.replace('https://arxiv.org', currentMirror));
            }
        });
    }

    // 监听 DOM 变化
    const observer = new MutationObserver(() => {
        redirectToMirror();
    });

    // 启动
    init().then(() => {
        redirectToMirror();
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    });
})();
```

---

### 方案五：异步请求 + 并发控制

#### 5.1 使用 asyncio + aiohttp

```python
import asyncio
import aiohttp
import time
from aiohttp import ClientResponseError

async def fetch_with_semaphore(sem, session, url):
    """使用信号量控制的异步请求"""
    async with sem:
        for attempt in range(3):
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 429:
                        # 读取 Retry-After
                        retry_after = response.headers.get('Retry-After', 60)
                        wait_time = int(retry_after) if retry_after.isdigit() else 60
                        print(f"Rate limited for {url}, waiting {wait_time}s...")
                        await asyncio.sleep(wait_time)
                        continue

                    response.raise_for_status()
                    return await response.text()

            except ClientResponseError as e:
                if attempt < 2:
                    wait_time = 10 * (2 ** attempt)  # 指数退避
                    print(f"Error {e.status} for {url}, retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    print(f"Failed to fetch {url} after 3 attempts")
                    return None

            except Exception as e:
                print(f"Unexpected error for {url}: {e}")
                await asyncio.sleep(5)
                return None

        return None

async def batch_fetch(urls, max_concurrent=1):
    """
    批量获取 URL

    Args:
        urls: URL 列表
        max_concurrent: 最大并发数（建议设为1以避免限流）
    """
    # 创建信号量，限制并发数
    sem = asyncio.Semaphore(max_concurrent)

    connector = aiohttp.TCPConnector(limit=max_concurrent)
    timeout = aiohttp.ClientTimeout(total=60)

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        tasks = [fetch_with_semaphore(sem, session, url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results

# 使用示例
urls = [
    "http://export.arxiv.org/api/query?id_list=2301.00001,2301.00002,2301.00003",
    "http://export.arxiv.org/api/query?id_list=2301.00004,2301.00005,2301.00006",
]

# 每次最多1个并发请求
results = asyncio.run(batch_fetch(urls, max_concurrent=1))
```

#### 5.2 带进度条的批量下载

```python
from tqdm.asyncio import tqdm
import asyncio
import aiohttp

async def fetch_with_progress(session, sem, url, pbar):
    """带进度条的下载"""
    async with sem:
        try:
            async with session.get(url) as response:
                if response.status == 429:
                    await asyncio.sleep(60)
                    return await fetch_with_progress(session, sem, url, pbar)

                content = await response.read()
                pbar.update(1)
                return content
        except Exception as e:
            pbar.update(1)
            print(f"\nError: {e}")
            return None

async def download_all(urls, max_concurrent=1):
    """带进度条的批量下载"""
    sem = asyncio.Semaphore(max_concurrent)

    async with aiohttp.ClientSession() as session:
        with tqdm(total=len(urls), desc="Downloading") as pbar:
            tasks = [
                fetch_with_progress(session, sem, url, pbar)
                for url in urls
            ]
            return await asyncio.gather(*tasks)

# 使用
results = asyncio.run(download_all(paper_urls))
```

---

### 方案六：代理池方案（企业级）

#### 6.1 代理池架构

```
┌─────────────────────────────────────────────────────────────┐
│                      Client                                  │
│                   (你的爬虫代码)                              │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    Proxy Pool                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Proxy 1  │  │ Proxy 2  │  │ Proxy 3  │  │ Proxy N  │   │
│  │ 1.2.3.4  │  │ 5.6.7.8  │  │ 9.10.11.12│ │ x.x.x.x  │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   arXiv API                                 │
│               (export.arxiv.org)                            │
└─────────────────────────────────────────────────────────────┘
```

#### 6.2 代理池实现

```python
import requests
import random
import time
from threading import Lock

class ProxyPool:
    """代理池管理器"""

    def __init__(self, api_url, api_key=None):
        self.api_url = api_url
        self.api_key = api_key
        self.proxies = []
        self.failed_proxies = set()
        self.lock = Lock()
        self.last_fetch = 0
        self.fetch_interval = 300  # 5分钟刷新一次

    def fetch_proxies(self):
        """从代理 API 获取代理列表"""
        now = time.time()
        if now - self.last_fetch < self.fetch_interval and self.proxies:
            return  # 代理还在有效期内

        try:
            headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}

            # 示例 API：实际使用时替换为你的代理服务 API
            response = requests.get(
                self.api_url,
                headers=headers,
                timeout=10
            )
            data = response.json()

            # 解析代理列表（根据实际 API 返回格式调整）
            self.proxies = [
                {
                    'http': f"http://{p['ip']}:{p['port']}",
                    'https': f"http://{p['ip']}:{p['port']}"
                }
                for p in data.get('data', [])
            ]

            self.last_fetch = now
            print(f"Fetched {len(self.proxies)} proxies")

        except Exception as e:
            print(f"Failed to fetch proxies: {e}")

    def get_random_proxy(self):
        """获取随机代理"""
        with self.lock:
            if not self.proxies:
                self.fetch_proxies()

            available = [p for p in self.proxies if p['http'] not in self.failed_proxies]

            if not available:
                # 重置失败列表，重新尝试
                self.failed_proxies.clear()
                self.fetch_proxies()
                available = self.proxies

            return random.choice(available) if available else None

    def mark_failed(self, proxy_url):
        """标记失败的代理"""
        with self.lock:
            self.failed_proxies.add(proxy_url)

            # 如果失败比例过高，重新获取
            if len(self.failed_proxies) > len(self.proxies) * 0.5:
                self.fetch_proxies()

# 使用示例
proxy_pool = ProxyPool(
    api_url="https://api.your-proxy-service.com/get_proxy",
    api_key="your_api_key"
)

def request_with_proxy(url):
    """使用代理发起请求"""
    proxy = proxy_pool.get_random_proxy()
    if not proxy:
        return requests.get(url)  # 无代理时直接请求

    try:
        response = requests.get(url, proxies=proxy, timeout=30)

        if response.status_code == 429:
            proxy_pool.mark_failed(proxy['http'])
            return request_with_proxy(url)  # 使用其他代理重试

        return response

    except Exception as e:
        proxy_pool.mark_failed(proxy['http'])
        return request_with_proxy(url)
```

#### 6.3 常用代理服务商

| 服务商 | 特点 | 官网 |
|-------|------|------|
| **天启代理** | 静态IP可用时长>5分钟，高可用 | tianqiip.com |
| **蘑菇代理** | 价格实惠，适合小规模爬取 | moguip.com |
| **阿布云** | 稳定高速，企业级服务 | abuyun.com |
| **Luminati** | 全球覆盖，高匿名 | luminati.io |

---

### 方案七：分批查询 + 结果缓存

#### 7.1 分页查询策略

```python
import time
import random
from typing import List, Dict, Any

class ArxivBatchQuery:
    """arXiv 批量查询管理器"""

    def __init__(self, delay=3.5):
        self.delay = delay  # 请求间隔（秒）
        self.cache = {}  # 结果缓存

    def _delay(self):
        """添加随机延迟"""
        time.sleep(self.delay + random.uniform(-0.5, 0.5))

    def query_by_date_range(
        self,
        start_date: str,
        end_date: str,
        category: str = "cs.AI",
        max_results: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        按日期范围查询论文

        Args:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            category: 论文分类
            max_results: 最大结果数（单次最多1000）
        """
        results = []
        start = 0

        while True:
            self._delay()

            # 构建查询 URL
            base_url = "http://export.arxiv.org/api/query"
            params = {
                "search_query": f"cat:{category}",
                "start": start,
                "max_results": min(1000, max_results - start),
                "sortBy": "submittedDate",
                "sortOrder": "descending"
            }

            response = requests.get(base_url, params=params)
            if response.status_code != 200:
                print(f"Error: {response.status_code}")
                break

            # 解析 XML 响应
            papers = self._parse_atom_response(response.text)

            # 按日期过滤
            filtered = [
                p for p in papers
                if start_date <= p['published'][:10] <= end_date
            ]
            results.extend(filtered)

            # 检查是否还有更多结果
            if len(papers) < 1000 or start + 1000 >= max_results:
                break

            start += 1000

        return results[:max_results]

    def query_by_id_list(self, arxiv_ids: List[str]) -> List[Dict[str, Any]]:
        """
        按 ID 列表查询论文

        Args:
            arxiv_ids: arXiv ID 列表（如 ["2301.00001", "2301.00002"]）
        """
        results = []

        # 每批最多 2000 个 ID（根据实际限制调整）
        batch_size = 100

        for i in range(0, len(arxiv_ids), batch_size):
            batch = arxiv_ids[i:i + batch_size]

            # 检查缓存
            cached = [self.cache.get(id) for id in batch if id in self.cache]
            missing = [id for id in batch if id not in self.cache]

            results.extend([c for c in cached if c])

            if missing:
                self._delay()

                ids_param = ",".join(missing)
                url = f"http://export.arxiv.org/api/query?id_list={ids_param}"

                response = requests.get(url)

                if response.status_code == 200:
                    papers = self._parse_atom_response(response.text)
                    for paper in papers:
                        self.cache[paper['id']] = paper
                    results.extend(papers)

        return results

    def _parse_atom_response(self, xml_content: str) -> List[Dict[str, Any]]:
        """解析 Atom XML 响应"""
        from xml.etree import ElementTree as ET

        papers = []
        root = ET.fromstring(xml_content)

        # Atom 命名空间
        ns = {
            'atom': 'http://www.w3.org/2005/Atom',
            'arxiv': 'http://arxiv.org/schemas/atom'
        }

        for entry in root.findall('atom:entry', ns):
            paper = {
                'id': entry.find('atom:id', ns).text,
                'title': entry.find('atom:title', ns).text.strip().replace('\n', ' '),
                'summary': entry.find('atom:summary', ns).text.strip(),
                'published': entry.find('atom:published', ns).text,
                'authors': [
                    author.find('atom:name', ns).text
                    for author in entry.findall('atom:author', ns)
                ],
                'categories': [
                    cat.get('term')
                    for cat in entry.findall('atom:category', ns)
                ],
                'links': {
                    'abs': None,
                    'pdf': None
                }
            }

            # 解析链接
            for link in entry.findall('atom:link', ns):
                if link.get('title') == 'pdf':
                    paper['links']['pdf'] = link.get('href')
                elif link.get('type') == 'text/html':
                    paper['links']['abs'] = link.get('href')

            papers.append(paper)

        return papers
```

#### 7.2 结果缓存机制

```python
import json
import os
import hashlib
from datetime import datetime, timedelta

class ArxivCache:
    """arXiv 结果缓存管理器"""

    def __init__(self, cache_dir="./arxiv_cache", ttl_days=7):
        self.cache_dir = cache_dir
        self.ttl_days = ttl_days
        os.makedirs(cache_dir, exist_ok=True)

    def _get_cache_key(self, query: str, params: dict) -> str:
        """生成缓存键"""
        content = json.dumps({"query": query, "params": params}, sort_keys=True)
        return hashlib.md5(content.encode()).hexdigest()

    def _get_cache_path(self, cache_key: str) -> str:
        """获取缓存文件路径"""
        return os.path.join(self.cache_dir, f"{cache_key}.json")

    def get(self, query: str, params: dict) -> tuple:
        """
        获取缓存

        Returns:
            (data, is_valid): 缓存数据和是否有效
        """
        cache_key = self._get_cache_key(query, params)
        cache_path = self._get_cache_path(cache_key)

        if not os.path.exists(cache_path):
            return None, False

        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)

            # 检查是否过期
            cached_time = datetime.fromisoformat(cache_data['timestamp'])
            if datetime.now() - cached_time > timedelta(days=self.ttl_days):
                return None, False

            return cache_data['data'], True

        except Exception as e:
            print(f"Cache read error: {e}")
            return None, False

    def set(self, query: str, params: dict, data):
        """设置缓存"""
        cache_key = self._get_cache_key(query, params)
        cache_path = self._get_cache_path(cache_key)

        cache_data = {
            'timestamp': datetime.now().isoformat(),
            'query': query,
            'params': params,
            'data': data
        }

        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Cache write error: {e}")

    def clear_expired(self):
        """清理过期缓存"""
        count = 0
        for filename in os.listdir(self.cache_dir):
            if not filename.endswith('.json'):
                continue

            filepath = os.path.join(self.cache_dir, filename)
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)

                cached_time = datetime.fromisoformat(data['timestamp'])
                if datetime.now() - cached_time > timedelta(days=self.ttl_days):
                    os.remove(filepath)
                    count += 1

            except:
                os.remove(filepath)
                count += 1

        print(f"Cleared {count} expired cache files")
```

---

## 三、替代数据源方案

完全避免 arXiv 限流的替代方案：

### 3.1 Semantic Scholar API

| 特点 | 说明 |
|-----|------|
| **免费额度** | 每秒 100 次请求 |
| **数据量** | 超过 2 亿篇学术论文 |
| **数据丰富度** | 引用关系、影响因素、关键词等 |
| **官网** | https://api.semanticscholar.org |

```python
import requests

def search_semantic_scholar(query, limit=10):
    """使用 Semantic Scholar API 搜索论文"""
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query": query,
        "limit": limit,
        "fields": "title,authors,abstract,year,citationCount,openAccessPdf"
    }

    response = requests.get(url, params=params)
    return response.json()
```

### 3.2 OpenAlex API

| 特点 | 说明 |
|-----|------|
| **免费额度** | 完全免费，无需 API Key |
| **数据量** | 超过 2 亿篇学术作品 |
| **数据丰富度** | 完整的引用网络、机构信息 |
| **官网** | https://api.openalex.org |

```python
import requests

def search_openalex(query, limit=10):
    """使用 OpenAlex API 搜索论文"""
    url = "https://api.openalex.org/works"
    params = {
        "search": query,
        "per-page": limit,
        "filter": "host_venue.name:arXiv"  # 只搜索 arXiv 论文
    }

    response = requests.get(url, params=params)
    return response.json()
```

### 3.3 CORE API

| 特点 | 说明 |
|-----|------|
| **免费额度** | 每天 1000 次请求 |
| **数据量** | 超过 2 亿篇论文 |
| **特色** | 聚合多个数据源 |
| **官网** | https://api.core.ac.uk |

### 3.4 arxiv-txt.org

| 特点 | 说明 |
|-----|------|
| **用途** | LLM 友好的纯文本格式 |
| **优点** | 直接获取论文文本，无需 PDF 解析 |
| **官网** | https://arxiv-txt.org |

```python
def get_arxiv_text(arxiv_id):
    """获取 arXiv 论文纯文本"""
    # 例如: 1706.03762 -> https://arxiv-txt.org/abs/1706.03762
    url = f"https://arxiv-txt.org/abs/{arxiv_id}"
    response = requests.get(url)
    return response.text
```

### 3.5 Papers with Code API

| 特点 | 说明 |
|-----|------|
| **特色** | 论文与代码关联 |
| **数据量** | 丰富的 ML/AI 论文 |
| **官网** | https://paperswithcode.com/api |

### 3.6 DeepXiv（智源开源）

| 特点 | 说明 |
|-----|------|
| **开发者** | 智源研究院 |
| **定位** | 专为 AI 智能体设计 |
| **功能** | 论文搜索、渐进式阅读、热点追踪 |
| **官网** | https://github.com/baaiu |

---

## 四、完整解决方案示例

### 4.1 生产级 arXiv 爬虫

```python
import requests
import time
import random
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from xml.etree import ElementTree as ET
from tenacity import retry, wait_exponential, stop_after_attempt

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ArxivCrawler:
    """生产级 arXiv 爬虫"""

    # 镜像列表
    MIRRORS = [
        'http://xxx.itp.ac.cn',
        'http://cn.arxiv.org',
        'https://export.arxiv.org'  # 原始 API
    ]

    def __init__(
        self,
        delay: float = 3.5,
        max_retries: int = 3,
        use_cache: bool = True
    ):
        self.delay = delay
        self.max_retries = max_retries
        self.use_cache = use_cache
        self.cache = {}
        self.current_mirror = self.MIRRORS[0]
        self.session = requests.Session()

        # 设置请求头
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; ArxivCrawler/1.0)',
            'Accept': 'application/atom+xml'
        })

    def _delay(self):
        """请求间隔延迟"""
        actual_delay = self.delay + random.uniform(-0.5, 0.5)
        time.sleep(max(0.1, actual_delay))

    @retry(
        wait=wait_exponential(multiplier=1, min=10, max=120),
        stop=stop_after_attempt(3)
    )
    def _make_request(self, url: str) -> requests.Response:
        """发起请求，带重试"""
        response = self.session.get(url, timeout=60)

        if response.status_code == 429:
            retry_after = response.headers.get('Retry-After', '60')
            wait_time = int(retry_after)
            logger.warning(f"Rate limited. Waiting {wait_time}s...")
            time.sleep(wait_time)
            raise requests.exceptions.RequestException("Rate limited")

        response.raise_for_status()
        return response

    def search_papers(
        self,
        query: str,
        category: Optional[str] = None,
        max_results: int = 100,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> List[Dict]:
        """
        搜索论文

        Args:
            query: 搜索关键词
            category: 论文分类（如 'cs.AI', 'cs.CL'）
            max_results: 最大结果数
            date_from: 开始日期 (YYYY-MM-DD)
            date_to: 结束日期 (YYYY-MM-DD)
        """
        all_papers = []
        start = 0
        batch_size = 1000

        # 构建查询字符串
        search_parts = [f'all:{query}']
        if category:
            search_parts.insert(0, f'cat:{category}')
        if date_from:
            search_parts.append(f' submittedDate:[{date_from} TO {date_to or datetime.now().strftime("%Y-%m-%d")}]')

        search_query = '+AND+'.join(search_parts)

        while len(all_papers) < max_results:
            self._delay()

            params = {
                'search_query': search_query,
                'start': start,
                'max_results': min(batch_size, max_results - start),
                'sortBy': 'relevance',
                'sortOrder': 'descending'
            }

            url = f"{self.current_mirror}/api/query"
            logger.info(f"Fetching papers {start} to {start + batch_size}...")

            try:
                response = self._make_request(url, params=params)
                papers = self._parse_response(response.text)
                all_papers.extend(papers)

                if len(papers) < batch_size:
                    break

                start += batch_size

            except Exception as e:
                logger.error(f"Error fetching papers: {e}")
                # 尝试切换镜像
                self._switch_mirror()
                continue

        return all_papers[:max_results]

    def download_pdf(self, paper_id: str, output_path: str) -> bool:
        """
        下载 PDF

        Args:
            paper_id: 论文 ID（如 '2301.00001'）
            output_path: 保存路径
        """
        # 检查缓存
        if self.use_cache and os.path.exists(output_path):
            logger.info(f"Using cached PDF: {output_path}")
            return True

        self._delay()

        pdf_url = f"{self.current_mirror}/pdf/{paper_id}.pdf"
        logger.info(f"Downloading PDF: {pdf_url}")

        try:
            response = self._make_request(pdf_url)

            with open(output_path, 'wb') as f:
                f.write(response.content)

            logger.info(f"Saved PDF to: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Error downloading PDF: {e}")
            return False

    def _parse_response(self, xml_content: str) -> List[Dict]:
        """解析 Atom XML 响应"""
        papers = []
        root = ET.fromstring(xml_content)

        ns = {'atom': 'http://www.w3.org/2005/Atom'}

        for entry in root.findall('atom:entry', ns):
            paper = {
                'id': entry.find('atom:id', ns).text.split('/')[-1],
                'title': entry.find('atom:title', ns).text.strip().replace('\n', ' '),
                'summary': entry.find('atom:summary', ns).text.strip(),
                'published': entry.find('atom:published', ns).text[:10],
                'updated': entry.find('atom:updated', ns).text[:10],
                'authors': [
                    author.find('atom:name', ns).text
                    for author in entry.findall('atom:author', ns)
                ],
                'categories': [
                    cat.get('term')
                    for cat in entry.findall('atom:category', ns)
                ]
            }

            # 解析链接
            for link in entry.findall('atom:link', ns):
                if link.get('title') == 'pdf':
                    paper['pdf_url'] = link.get('href')

            papers.append(paper)

        return papers

    def _switch_mirror(self):
        """切换到下一个可用镜像"""
        current_index = self.MIRRORS.index(self.current_mirror)
        next_index = (current_index + 1) % len(self.MIRRORS)
        self.current_mirror = self.MIRRORS[next_index]
        logger.info(f"Switched to mirror: {self.current_mirror}")


# 使用示例
if __name__ == "__main__":
    crawler = ArxivCrawler(delay=3.5)

    # 搜索论文
    papers = crawler.search_papers(
        query="large language model",
        category="cs.CL",
        max_results=100
    )

    print(f"Found {len(papers)} papers")

    # 下载第一篇论文的 PDF
    if papers:
        paper_id = papers[0]['id']
        crawler.download_pdf(paper_id, f"./papers/{paper_id}.pdf")
```

---

## 五、最佳实践总结

### 5.1 限流应对策略优先级

| 优先级 | 策略 | 适用场景 |
|-------|------|---------|
| **★★★★★** | 合理请求间隔（≥3秒） | 日常使用，必做 |
| **★★★★★** | 429 错误处理 + Retry-After | 触发限流时 |
| **★★★★☆** | 使用国内镜像 | 中国用户 |
| **★★★★☆** | 结果缓存 | 重复查询 |
| **★★★☆☆** | 异步 + 限流器 | 大规模爬取 |
| **★★☆☆☆** | 代理池 | 企业级应用 |
| **★☆☆☆☆** | 替代数据源 | 完全规避 |

### 5.2 开发建议

1. **始终添加适当的请求间隔**，不要依赖触发限流后再处理
2. **实现指数退避策略**，避免持续重试加剧限流
3. **使用缓存机制**，减少重复请求
4. **实现镜像自动切换**，提高稳定性
5. **监控请求成功率**，及时调整策略
6. **遵守 robots.txt**，保持对服务器的尊重

### 5.3 快速排查清单

```markdown
□ 是否添加了请求间隔（建议 3-5 秒）？
□ 是否处理了 429 错误和 Retry-After？
□ 是否实现了重试机制？
□ 是否使用了缓存避免重复请求？
□ 是否配置了合适的超时时间？
□ 是否设置了合理的 User-Agent？
□ 是否在测试环境验证过？
□ 是否有日志记录请求状态？
```

---

## 六、参考资料

- [arXiv API 官方文档](https://info.arxiv.org/help/api/)
- [arXiv API 使用条款](https://info.arxiv.org/help/api/tou.html)
- [Python arXiv 库](https://pypi.org/project/arxiv/)
- [Tenacity 重试库](https://github.com/jd/tenacity)
- [Semantic Scholar API](https://api.semanticscholar.org/)
- [OpenAlex API](https://api.openalex.org/)

---

> **版权声明**：本文档仅供学术研究参考，请勿用于商业爬虫或任何违反 arXiv 服务条款的活动。