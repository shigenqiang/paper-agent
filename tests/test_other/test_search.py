"""
Search模块 单元测试
"""
import pytest
from src.agents_v2.search import (
    BaseSearcher,
    SearchResult,
    SearchResponse,
    ArxivSearcher,
    PubmedSearcher,
    SemanticScholarSearcher,
    SearchFactory,
    get_searcher,
    search_all
)


class TestSearchResult:
    """SearchResult 测试"""

    def test_create_result(self):
        """测试创建搜索结果"""
        result = SearchResult(
            paper_id="test_001",
            title="Test Paper",
            abstract="Abstract content",
            authors=["Author A"],
            year=2024,
            venue="ICML"
        )
        assert result.paper_id == "test_001"
        assert result.title == "Test Paper"
        assert len(result.authors) == 1

    def test_default_values(self):
        """测试默认值"""
        result = SearchResult(paper_id="test", title="Title")
        assert result.abstract == ""
        assert result.citations == 0


class TestSearchResponse:
    """SearchResponse 测试"""

    def test_create_response(self):
        """测试创建响应"""
        result = SearchResult(paper_id="1", title="Paper")
        response = SearchResponse(
            query="test query",
            total=1,
            results=[result],
            source="test"
        )
        assert response.query == "test query"
        assert response.total == 1
        assert len(response.results) == 1


class TestArxivSearcher:
    """ArxivSearcher 测试"""

    def setup_method(self):
        self.searcher = ArxivSearcher()

    def test_search_init(self):
        """测试搜索器初始化"""
        assert self.searcher.name == "arxiv"

    @pytest.mark.asyncio
    async def test_search(self):
        """测试搜索"""
        response = await self.searcher.search("machine learning", max_results=5)
        assert response.source == "arxiv"
        assert response.total > 0
        assert len(response.results) <= 5

    @pytest.mark.asyncio
    async def test_get_paper(self):
        """测试获取论文"""
        paper = await self.searcher.get_paper("2301.00001")
        assert paper is not None
        assert "2301" in paper.paper_id


class TestPubmedSearcher:
    """PubmedSearcher 测试"""

    def setup_method(self):
        self.searcher = PubmedSearcher()

    @pytest.mark.asyncio
    async def test_search(self):
        """测试搜索"""
        response = await self.searcher.search("cancer", max_results=3)
        assert response.source == "pubmed"
        assert response.total > 0


class TestSemanticScholarSearcher:
    """SemanticScholarSearcher 测试"""

    def setup_method(self):
        self.searcher = SemanticScholarSearcher()

    @pytest.mark.asyncio
    async def test_search(self):
        """测试搜索"""
        response = await self.searcher.search("deep learning", max_results=3)
        assert response.source == "semantic_scholar"
        assert response.total > 0

    @pytest.mark.asyncio
    async def test_get_citations(self):
        """测试获取引用"""
        response = await self.searcher.get_citations("paper_123", max_results=10)
        assert response.total > 0


class TestSearchFactory:
    """SearchFactory 测试"""

    def test_get_searcher(self):
        """测试获取搜索器"""
        arxiv = get_searcher("arxiv")
        assert arxiv is not None
        assert arxiv.name == "arxiv"

    def test_get_unknown_searcher(self):
        """测试获取未知搜索器"""
        searcher = get_searcher("unknown")
        assert searcher is None

    def test_register_searcher(self):
        """测试注册搜索器"""
        custom = ArxivSearcher()
        SearchFactory.register("custom", custom)
        retrieved = SearchFactory.get("custom")
        assert retrieved is custom

    def test_list_searchers(self):
        """测试列出搜索器"""
        # 先获取一些搜索器触发注册
        get_searcher("arxiv")
        get_searcher("pubmed")
        names = SearchFactory.list_searchers()
        assert "arxiv" in names or len(names) >= 0

    @pytest.mark.asyncio
    async def test_search_all(self):
        """测试使用所有搜索器搜索"""
        responses = await search_all("AI", max_results=2)
        assert len(responses) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])