"""论文Agent Web界面"""
import streamlit as st
import asyncio
import requests
from typing import Optional
import json

# 页面配置
st.set_page_config(
    page_title="论文Agent",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        padding: 2rem 0;
    }
    .query-box {
        padding: 1.5rem;
        background: #f8f9fa;
        border-radius: 10px;
        margin: 1rem 0;
    }
    .result-card {
        padding: 1.5rem;
        background: white;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 1rem 0;
    }
    .paper-badge {
        background: #e7f3ff;
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
        font-size: 0.85rem;
        color: #0066cc;
    }
</style>
""", unsafe_allow_html=True)

# 初始化session state
if "history" not in st.session_state:
    st.session_state.history = []
if "api_url" not in st.session_state:
    st.session_state.api_url = "http://localhost:8000"


def query_api(query: str, max_results: int = 20, year_range: tuple = (2020, 2025)) -> Optional[dict]:
    """调用API查询"""
    try:
        with st.spinner("正在搜索和分析论文..."):
            response = requests.post(
                f"{st.session_state.api_url}/query",
                json={
                    "query": query,
                    "max_results": max_results,
                    "year_range": year_range
                },
                timeout=120
            )
            response.raise_for_status()
            return response.json()
    except requests.exceptions.Timeout:
        st.error("查询超时，请稍后重试")
        return None
    except requests.exceptions.ConnectionError:
        st.error("无法连接到API服务，请确保后端服务已启动")
        return None
    except Exception as e:
        st.error(f"查询失败: {str(e)}")
        return None


def render_markdown(content: str):
    """渲染Markdown内容"""
    st.markdown(content, unsafe_allow_html=False)


# 主界面
st.markdown('<div class="main-header">📚 论文Agent</div>', unsafe_allow_html=True)

# 侧边栏配置
with st.sidebar:
    st.header("⚙️ 配置")
    api_url = st.text_input("API地址", value=st.session_state.api_url)
    if api_url != st.session_state.api_url:
        st.session_state.api_url = api_url

    st.divider()

    st.header("🔍 查询设置")
    max_results = st.slider("最大结果数", 5, 50, 20)
    year_start = st.number_input("起始年份", 2010, 2025, 2020)
    year_end = st.number_input("结束年份", 2020, 2026, 2025)

    st.divider()

    st.header("📜 查询历史")
    if st.session_state.history:
        for i, item in enumerate(reversed(st.session_state.history)):
            if st.button(f"{item[:30]}...", key=f"history_{i}", use_container_width=True):
                st.session_state.query_input = item
                st.rerun()
    else:
        st.info("暂无查询历史")

# 主查询区域
st.markdown('<div class="query-box">', unsafe_allow_html=True)

query_input = st.text_area(
    "请输入您想要了解的研究主题",
    placeholder="例如：函数型数据分析的最新进展",
    height=100,
    key="query_input"
)

col1, col2, col3 = st.columns([1, 1, 2])
with col1:
    query_btn = st.button("🔍 开始查询", type="primary", use_container_width=True)
with col2:
    clear_btn = st.button("🗑️ 清空", use_container_width=True)

st.markdown('</div>', unsafe_allow_html=True)

# 清空按钮
if clear_btn:
    st.session_state.query_input = ""
    st.session_state.last_result = None
    st.rerun()

# 查询处理
if query_btn and query_input:
    # 保存到历史记录
    if query_input not in st.session_state.history:
        st.session_state.history.append(query_input)
        if len(st.session_state.history) > 10:
            st.session_state.history.pop(0)

    # 调用API
    result = query_api(query_input, max_results, (year_start, year_end))

    if result:
        st.session_state.last_result = result
        st.session_state.last_query = query_input

# 显示结果
if "last_result" in st.session_state and st.session_state.last_result:
    result = st.session_state.last_result

    if result["status"] == "success":
        st.success(f"✅ 查询成功！找到 {result.get('papers_count', 0)} 篇相关论文")

        # 查询概览
        st.divider()
        st.subheader("📊 查询概览")
        if "last_query" in st.session_state:
            st.info(f"查询: {st.session_state.last_query}")
        st.info(f"论文数量: {result.get('papers_count', 0)}")

        # 详细报告
        st.divider()
        st.subheader("📝 研究报告")

        if result.get("report_markdown"):
            render_markdown(result["report_markdown"])
        else:
            st.warning("未生成报告内容")

    elif result["status"] == "error":
        st.error(f"❌ 查询失败: {result.get('message', '未知错误')}")

# 页脚
st.divider()
st.markdown("""
<div style='text-align: center; color: #888; padding: 1rem;'>
    论文Agent v1.0 | 基于LangGraph构建
</div>
""", unsafe_allow_html=True)

# API状态检查
try:
    health_response = requests.get(f"{st.session_state.api_url}/health", timeout=5)
    if health_response.status_code == 200:
        st.toast("✅ API服务连接正常", icon="✅")
except:
    st.toast("⚠️ API服务未连接，请检查配置", icon="⚠️")
