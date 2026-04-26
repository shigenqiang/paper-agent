"""
PubMed MCP 单元测试

测试PubMed MCP协议实现
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.agents_v2.mcp.search.pubmed_mcp import (
    PubmedMCPClient,
    PubmedArticle,
    PubmedSearchResult,
    search_pubmed,
    get_pubmed_article
)


class TestPubmedMCPClient:
    """PubmedMCPClient 测试"""

    def setup_method(self):
        self.client = PubmedMCPClient(api_key="test_key", timeout=5.0)

    def test_client_initialization(self):
        """测试客户端初始化"""
        assert self.client.api_key == "test_key"
        assert self.client.timeout == 5.0
        assert self.client.ESEARCH_URL == "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"

    @pytest.mark.asyncio
    async def test_search_articles_empty_response(self):
        """测试空响应"""
        with patch.object(self.client, '_fetch', return_value=""):
            result = await self.client.search_articles("cancer", max_results=5)

            assert result.articles == []
            assert result.total_count == 0

    @pytest.mark.asyncio
    async def test_search_articles_invalid_xml(self):
        """测试无效XML"""
        with patch.object(self.client, '_fetch', return_value="not xml"):
            result = await self.client.search_articles("test")

            assert result.articles == []

    def test_parse_pmids_empty(self):
        """测试解析空PMID"""
        pmids = self.client._parse_pmids("")
        assert pmids == []

    def test_parse_pmids_invalid_xml(self):
        """测试解析无效XML"""
        pmids = self.client._parse_pmids("<invalid>")
        assert pmids == []


class TestPubmedArticle:
    """PubmedArticle 测试"""

    def test_create_article(self):
        """测试创建文章对象"""
        from datetime import datetime

        article = PubmedArticle(
            pmid="12345678",
            title="Test Article Title",
            authors=["Author One", "Author Two"],
            abstract="This is the abstract.",
            journal="Nature",
            pub_date=datetime.now(),
            mesh_terms=["Humans", "Male"],
            doi="10.1234/test"
        )

        assert article.pmid == "12345678"
        assert article.title == "Test Article Title"
        assert len(article.mesh_terms) == 2
        assert article.doi == "10.1234/test"


class TestPubmedSearchResult:
    """PubmedSearchResult 测试"""

    def test_create_result(self):
        """测试创建搜索结果"""
        result = PubmedSearchResult(
            articles=[],
            total_count=0,
            query="test",
            search_time=0.5
        )

        assert result.total_count == 0
        assert result.query == "test"
        assert result.search_time == 0.5


class TestConvenienceFunctions:
    """便捷函数测试"""

    @pytest.mark.asyncio
    async def test_search_pubmed(self):
        """测试便捷搜索函数"""
        with patch('src.agents_v2.mcp.search.pubmed_mcp.PubmedMCPClient') as MockClient:
            mock_instance = AsyncMock()
            mock_instance.search_articles = AsyncMock(return_value=PubmedSearchResult(
                articles=[],
                total_count=0,
                query="test",
                search_time=0.1
            ))
            mock_instance.close = AsyncMock()
            MockClient.return_value = mock_instance

            result = await search_pubmed("test", max_results=5)
            assert result.query == "test"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])