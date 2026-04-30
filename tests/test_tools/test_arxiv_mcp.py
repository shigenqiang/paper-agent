"""
ArXiv MCP 单元测试

测试ArXiv MCP协议实现
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.agents_v2._archive.mcp.search.arxiv_mcp import (
    ArxivMCPClient,
    ArxivQuery,
    ArxivPaper,
    ArxivSearchResult,
    SearchField,
    SortBy,
    search_arxiv,
    get_arxiv_paper,
    search_arxiv_by_author,
    search_arxiv_recent
)


class TestArxivQuery:
    """ArxivQuery 测试"""

    def test_simple_query(self):
        """测试简单查询"""
        query = ArxivQuery("machine learning")
        assert "machine learning" in query.build()

    def test_title_query(self):
        """测试标题查询"""
        query = ArxivQuery().title("transformer")
        assert "ti:transformer" in query.build()

    def test_author_query(self):
        """测试作者查询"""
        query = ArxivQuery().author("Hinton")
        assert "au:Hinton" in query.build()

    def test_abstract_query(self):
        """测试摘要查询"""
        query = ArxivQuery().abstract("neural network")
        assert "abs:neural network" in query.build()

    def test_category_query(self):
        """测试分类查询"""
        query = ArxivQuery().category("cs.AI")
        assert "cat:cs.AI" in query.build()

    def test_chained_queries(self):
        """测试链式查询"""
        query = ArxivQuery().title("neural").AND().author("Hinton")
        result = query.build()
        assert "ti:neural" in result
        assert "au:Hinton" in result
        assert "AND" in result

    def test_OR_operator(self):
        """测试OR运算符"""
        query = ArxivQuery().title("CNN").OR().title("RNN")
        result = query.build()
        assert "OR" in result

    def test_phrase_query(self):
        """测试精确短语查询"""
        query = ArxivQuery().phrase("deep learning")
        assert '"deep learning"' in query.build()

    def test_date_range(self):
        """测试日期范围"""
        query = ArxivQuery("deep learning").date_range("2024-01-01", "2024-12-31")
        result = query.build()
        assert "deep learning" in result
        assert "2024-01-01" in result
        assert "2024-12-31" in result

    def test_date_from(self):
        """测试开始日期"""
        query = ArxivQuery("AI").date_from("2024-01-01")
        result = query.build()
        assert "2024-01-01" in result

    def test_date_to(self):
        """测试结束日期"""
        query = ArxivQuery("AI").date_to("2024-12-31")
        result = query.build()
        assert "2024-12-31" in result

    def test_all_fields_query(self):
        """测试全部字段查询"""
        query = ArxivQuery().all("optimization")
        assert "all:optimization" in query.build()


class TestSearchField:
    """SearchField 测试"""

    def test_field_values(self):
        """测试字段枚举值"""
        assert SearchField.TITLE.value == "ti"
        assert SearchField.AUTHOR.value == "au"
        assert SearchField.ABSTRACT.value == "abs"
        assert SearchField.CATEGORY.value == "cat"


class TestSortBy:
    """SortBy 测试"""

    def test_sort_values(self):
        """测试排序枚举值"""
        assert SortBy.RELEVANCE.value == "relevance"
        assert SortBy.SUBMITTED_DATE.value == "submittedDate"


class TestArxivMCPClient:
    """ArxivMCPClient 测试"""

    def setup_method(self):
        self.client = ArxivMCPClient(timeout=5.0, max_retries=2)

    def test_client_initialization(self):
        """测试客户端初始化"""
        assert self.client.timeout == 5.0
        assert self.client.max_retries == 2
        assert self.client.BASE_URL == "https://export.arxiv.org/api/query"

    def test_list_categories(self):
        """测试列出分类"""
        categories = self.client.list_categories()
        assert "cs.AI" in categories
        assert "cs.LG" in categories
        assert categories["cs.LG"] == "Machine Learning"

    @pytest.mark.asyncio
    async def test_search_papers_empty_response(self):
        """测试空响应"""
        with patch.object(self.client, '_fetch', return_value=""):
            result = await self.client.search_papers("machine learning", max_results=5)
            assert result.papers == []
            assert result.total_results == 0

    @pytest.mark.asyncio
    async def test_search_with_arxiv_query(self):
        """测试使用ArxivQuery搜索"""
        with patch.object(self.client, '_fetch', return_value=""):
            query = ArxivQuery().title("transformer").author("Vaswani")
            result = await self.client.search_papers(query)
            assert result.query == str(query)

    @pytest.mark.asyncio
    async def test_search_by_title(self):
        """测试按标题搜索"""
        with patch.object(self.client, '_fetch', return_value=""):
            result = await self.client.search_by_title("BERT")
            assert "ti:BERT" in result.query

    @pytest.mark.asyncio
    async def test_search_by_author(self):
        """测试按作者搜索"""
        with patch.object(self.client, '_fetch', return_value=""):
            result = await self.client.search_by_author("LeCun")
            assert "au:LeCun" in result.query

    @pytest.mark.asyncio
    async def test_search_by_category(self):
        """测试按分类搜索"""
        with patch.object(self.client, '_fetch', return_value=""):
            result = await self.client.search_by_category("cs.LG")
            assert "cat:cs.LG" in result.query

    @pytest.mark.asyncio
    async def test_search_recent(self):
        """测试搜索最近论文"""
        with patch.object(self.client, '_fetch', return_value=""):
            result = await self.client.search_recent("AI", days=7)
            assert "AI" in result.query
            assert "submittedDate" in result.query

    def test_build_query_with_prefix(self):
        """测试已包含前缀的查询"""
        query = self.client._build_query("ti:transformer", None)
        assert query == "ti:transformer"

    def test_build_query_simple(self):
        """测试简单查询构建"""
        query = self.client._build_query("machine learning", None)
        assert "all:machine learning" in query

    def test_build_query_with_categories(self):
        """测试带分类的查询构建"""
        query = self.client._build_query("deep learning", ["cs.AI", "cs.LG"])
        assert "all:deep learning" in query
        assert "cat:cs.AI" in query
        assert "cat:cs.LG" in query


class TestArxivPaper:
    """ArxivPaper 测试"""

    def test_create_paper(self):
        """测试创建论文对象"""
        paper = ArxivPaper(
            id="2301.00001",
            title="Test Paper Title",
            authors=["Author One", "Author Two"],
            abstract="This is the abstract.",
            categories=["cs.AI", "cs.LG"],
            published=None,
            updated=None,
            pdf_url="https://arxiv.org/pdf/2301.00001.pdf"
        )

        assert paper.id == "2301.00001"
        assert paper.title == "Test Paper Title"
        assert len(paper.authors) == 2

    def test_paper_with_extra_fields(self):
        """测试带额外字段的论文"""
        paper = ArxivPaper(
            id="2301.00001",
            title="Test",
            authors=[],
            abstract="",
            categories=[],
            published=None,
            updated=None,
            pdf_url="",
            comment="32 pages, 8 figures",
            journal_ref="Nature 2024"
        )

        assert paper.comment == "32 pages, 8 figures"
        assert paper.journal_ref == "Nature 2024"


class TestArxivSearchResult:
    """ArxivSearchResult 测试"""

    def test_create_result(self):
        """测试创建搜索结果"""
        result = ArxivSearchResult(
            papers=[],
            total_results=0,
            query="test",
            search_time=0.5
        )

        assert result.total_results == 0
        assert result.query == "test"
        assert result.search_time == 0.5


class TestConvenienceFunctions:
    """便捷函数测试"""

    @pytest.mark.asyncio
    async def test_search_arxiv(self):
        """测试便捷搜索函数"""
        with patch('src.agents_v2.mcp.search.arxiv_mcp.ArxivMCPClient') as MockClient:
            mock_instance = AsyncMock()
            mock_instance.search_papers = AsyncMock(return_value=ArxivSearchResult(
                papers=[],
                total_results=0,
                query="test",
                search_time=0.1
            ))
            mock_instance.close = AsyncMock()
            MockClient.return_value = mock_instance

            result = await search_arxiv("test", max_results=5)
            assert result.query == "test"

    @pytest.mark.asyncio
    async def test_search_arxiv_by_author(self):
        """测试按作者搜索便捷函数"""
        with patch('src.agents_v2.mcp.search.arxiv_mcp.ArxivMCPClient') as MockClient:
            mock_instance = AsyncMock()
            mock_instance.search_by_author = AsyncMock(return_value=ArxivSearchResult(
                papers=[],
                total_results=0,
                query="au:Hinton",
                search_time=0.1
            ))
            mock_instance.close = AsyncMock()
            MockClient.return_value = mock_instance

            result = await search_arxiv_by_author("Hinton")
            assert "Hinton" in result.query


if __name__ == "__main__":
    pytest.main([__file__, "-v"])