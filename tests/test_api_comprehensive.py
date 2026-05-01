"""
Comprehensive API Tests for Paper Agent

Tests core CRUD operations, literature management, settings, and chat functionality.
"""
import pytest
import json
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

# Import the module under test
import sys
sys.path.insert(0, 'D:/pycharmprojects/pythonProject1')

from src.agents_v2.api.paper_api import (
    list_papers,
    create_paper,
    get_paper,
    update_paper,
    delete_paper,
    get_outline,
    get_settings,
    update_settings,
    get_chat_history,
    PAPERS_STORAGE,
    LITERATURE_STORAGE,
    SETTINGS_STORAGE,
    CHAT_SESSIONS,
)


# ============ Fixtures ============

@pytest.fixture
def sample_paper_data():
    """Sample paper data for testing"""
    return {
        "title": "Test Paper: AI in Education",
        "topic": "Artificial Intelligence applications in modern education",
        "outline": [
            {"id": "sec1", "title": "Introduction", "level": 1, "content": ""},
            {"id": "sec2", "title": "Literature Review", "level": 1, "content": ""},
            {"id": "sec3", "title": "Methodology", "level": 1, "content": ""},
        ],
        "content": "This is a test paper content.",
        "status": "draft",
    }


@pytest.fixture
def sample_literature_data():
    """Sample literature data for testing"""
    return {
        "title": "Deep Learning for NLP",
        "authors": "Smith, J., Johnson, A.",
        "year": "2024",
        "journal": "Journal of AI Research",
        "abstract": "This paper explores deep learning techniques for NLP tasks.",
        "url": "https://example.com/paper1",
    }


@pytest.fixture
def clean_storage():
    """Clean up storage before and after tests"""
    # Save original state
    orig_papers = PAPERS_STORAGE.copy()
    orig_literature = LITERATURE_STORAGE.copy()
    orig_settings = SETTINGS_STORAGE.copy()
    orig_chat = CHAT_SESSIONS.copy()

    # Clear for test
    PAPERS_STORAGE.clear()
    LITERATURE_STORAGE.clear()
    CHAT_SESSIONS.clear()

    yield

    # Restore original state
    PAPERS_STORAGE.clear()
    PAPERS_STORAGE.update(orig_papers)
    LITERATURE_STORAGE.clear()
    LITERATURE_STORAGE.update(orig_literature)
    SETTINGS_STORAGE.clear()
    SETTINGS_STORAGE.update(orig_settings)
    CHAT_SESSIONS.clear()
    CHAT_SESSIONS.update(orig_chat)


@pytest.fixture
def mock_request():
    """Create a mock aiohttp request"""
    def _make_request(method='GET', path='/', body=None, query=None, match_info=None):
        request = MagicMock()
        request.method = method
        request.path = path
        request.query = query or {}

        if match_info:
            request.match_info = match_info

        if body:
            body_bytes = json.dumps(body).encode('utf-8')
            request.content = AsyncMock()
            request.content.read = AsyncMock(return_value=body_bytes)
            request.json = AsyncMock(return_value=body)
        else:
            request.content = AsyncMock()
            request.content.read = AsyncMock(return_value=b'{}')
            request.json = AsyncMock(return_value={})

        return request

    return _make_request


# ============ Paper CRUD Tests ============

class TestPaperCRUD:
    """Test Paper CRUD operations"""

    @pytest.mark.asyncio
    async def test_create_paper(self, mock_request, clean_storage, sample_paper_data):
        """Test creating a new paper"""
        request = mock_request(method='POST', body=sample_paper_data)

        response = await create_paper(request)
        data = json.loads(response.body)

        assert response.status == 201
        assert data['success'] is True
        assert data['data']['title'] == sample_paper_data['title']
        assert data['data']['topic'] == sample_paper_data['topic']
        assert data['data']['status'] == 'draft'
        assert 'id' in data['data']
        assert 'created_at' in data['data']

    @pytest.mark.asyncio
    async def test_list_papers_empty(self, mock_request, clean_storage):
        """Test listing papers when storage is empty"""
        request = mock_request(method='GET', query={'page': '1', 'pageSize': '10'})

        response = await list_papers(request)
        data = json.loads(response.body)

        assert response.status == 200
        assert data['success'] is True
        assert data['data'] == []
        assert data['total'] == 0

    @pytest.mark.asyncio
    async def test_list_papers_with_data(self, mock_request, clean_storage, sample_paper_data):
        """Test listing papers with existing data"""
        # Create a paper first
        create_req = mock_request(method='POST', body=sample_paper_data)
        await create_paper(create_req)

        # List papers
        list_req = mock_request(method='GET', query={'page': '1', 'pageSize': '10'})
        response = await list_papers(list_req)
        data = json.loads(response.body)

        assert response.status == 200
        assert data['success'] is True
        assert len(data['data']) == 1
        assert data['total'] == 1

    @pytest.mark.asyncio
    async def test_get_paper(self, mock_request, clean_storage, sample_paper_data):
        """Test getting a specific paper by ID"""
        # Create a paper first
        create_req = mock_request(method='POST', body=sample_paper_data)
        create_resp = await create_paper(create_req)
        paper_id = json.loads(create_resp.body)['data']['id']

        # Get the paper
        get_req = mock_request(method='GET', match_info={'id': paper_id})
        response = await get_paper(get_req)
        data = json.loads(response.body)

        assert response.status == 200
        assert data['success'] is True
        assert data['data']['id'] == paper_id
        assert data['data']['title'] == sample_paper_data['title']

    @pytest.mark.asyncio
    async def test_get_paper_not_found(self, mock_request, clean_storage):
        """Test getting a non-existent paper"""
        request = mock_request(method='GET', match_info={'id': 'non-existent-id'})

        response = await get_paper(request)
        data = json.loads(response.body)

        assert response.status == 404
        assert data['success'] is False
        assert 'not found' in data['error'].lower()

    @pytest.mark.asyncio
    async def test_update_paper(self, mock_request, clean_storage, sample_paper_data):
        """Test updating an existing paper"""
        # Create a paper first
        create_req = mock_request(method='POST', body=sample_paper_data)
        create_resp = await create_paper(create_req)
        paper_id = json.loads(create_resp.body)['data']['id']

        # Update the paper
        update_data = {"title": "Updated Paper Title", "status": "reviewing"}
        update_req = mock_request(method='PUT', body=update_data, match_info={'id': paper_id})
        response = await update_paper(update_req)
        data = json.loads(response.body)

        assert response.status == 200
        assert data['success'] is True
        assert data['data']['title'] == "Updated Paper Title"
        assert data['data']['status'] == "reviewing"

    @pytest.mark.asyncio
    async def test_update_paper_not_found(self, mock_request, clean_storage):
        """Test updating a non-existent paper"""
        request = mock_request(method='PUT', body={"title": "Test"}, match_info={'id': 'non-existent'})

        response = await update_paper(request)
        data = json.loads(response.body)

        assert response.status == 404
        assert data['success'] is False

    @pytest.mark.asyncio
    async def test_delete_paper(self, mock_request, clean_storage, sample_paper_data):
        """Test deleting a paper"""
        # Create a paper first
        create_req = mock_request(method='POST', body=sample_paper_data)
        create_resp = await create_paper(create_req)
        paper_id = json.loads(create_resp.body)['data']['id']

        # Delete the paper
        delete_req = mock_request(method='DELETE', match_info={'id': paper_id})
        response = await delete_paper(delete_req)
        data = json.loads(response.body)

        assert response.status == 200
        assert data['success'] is True

        # Verify it's deleted
        get_req = mock_request(method='GET', match_info={'id': paper_id})
        get_resp = await get_paper(get_req)
        assert get_resp.status == 404

    @pytest.mark.asyncio
    async def test_delete_paper_not_found(self, mock_request, clean_storage):
        """Test deleting a non-existent paper"""
        request = mock_request(method='DELETE', match_info={'id': 'non-existent'})

        response = await delete_paper(request)
        data = json.loads(response.body)

        assert response.status == 404
        assert data['success'] is False


# ============ Outline Tests ============

class TestOutlineOperations:
    """Test outline-related operations"""

    @pytest.mark.asyncio
    async def test_get_outline(self, mock_request, clean_storage, sample_paper_data):
        """Test getting paper outline"""
        # Create a paper first
        create_req = mock_request(method='POST', body=sample_paper_data)
        create_resp = await create_paper(create_req)
        paper_id = json.loads(create_resp.body)['data']['id']

        # Get outline
        from src.agents_v2.api.paper_api import get_outline
        get_req = mock_request(method='GET', match_info={'id': paper_id})
        response = await get_outline(get_req)
        data = json.loads(response.body)

        assert response.status == 200
        assert data['success'] is True
        assert isinstance(data['data'], list)
        assert len(data['data']) == 3  # 3 sections in sample data

    @pytest.mark.asyncio
    async def test_get_outline_empty_paper(self, mock_request, clean_storage):
        """Test getting outline for paper without outline"""
        # Create a paper without outline
        paper_data = {"title": "Test", "topic": "Test"}
        create_req = mock_request(method='POST', body=paper_data)
        create_resp = await create_paper(create_req)
        paper_id = json.loads(create_resp.body)['data']['id']

        from src.agents_v2.api.paper_api import get_outline
        get_req = mock_request(method='GET', match_info={'id': paper_id})
        response = await get_outline(get_req)
        data = json.loads(response.body)

        assert response.status == 200
        assert data['success'] is True
        assert data['data'] == []


# ============ Settings Tests ============

class TestSettingsOperations:
    """Test settings operations"""

    @pytest.mark.asyncio
    async def test_get_settings(self, mock_request, clean_storage):
        """Test getting current settings"""
        request = mock_request(method='GET')

        response = await get_settings(request)
        data = json.loads(response.body)

        assert response.status == 200
        assert data['success'] is True
        assert 'language' in data['data']
        assert 'theme' in data['data']
        assert 'autoSave' in data['data']

    @pytest.mark.asyncio
    async def test_update_settings(self, mock_request, clean_storage):
        """Test updating settings"""
        update_data = {
            "language": "en-US",
            "theme": "dark",
            "autoSave": False,
        }
        request = mock_request(method='PUT', body=update_data)

        response = await update_settings(request)
        data = json.loads(response.body)

        assert response.status == 200
        assert data['success'] is True
        assert data['data']['language'] == "en-US"
        assert data['data']['theme'] == "dark"
        assert data['data']['autoSave'] is False


# ============ Chat Tests ============

class TestChatOperations:
    """Test chat-related operations"""

    @pytest.mark.asyncio
    async def test_get_chat_history_empty(self, mock_request, clean_storage):
        """Test getting chat history when empty"""
        request = mock_request(
            method='GET',
            query={'user_id': 'test_user', 'session_id': 'test_session'},
            match_info={'paperId': 'test_paper'}
        )

        response = await get_chat_history(request)
        data = json.loads(response.body)

        assert response.status == 200
        assert data['success'] is True
        assert data['data']['messages'] == []
        assert data['data']['count'] == 0

    @pytest.mark.asyncio
    async def test_chat_session_management(self, clean_storage):
        """Test chat session context management"""
        # Simulate adding messages to session
        session_key = ("test_user", "test_session")
        CHAT_SESSIONS[session_key] = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]

        assert len(CHAT_SESSIONS[session_key]) == 2
        assert CHAT_SESSIONS[session_key][0]["role"] == "user"
        assert CHAT_SESSIONS[session_key][1]["role"] == "assistant"


# ============ Literature Tests ============

class TestLiteratureOperations:
    """Test literature-related operations"""

    @pytest.mark.asyncio
    async def test_add_literature_to_paper(self, mock_request, clean_storage, sample_paper_data, sample_literature_data):
        """Test adding literature to a paper"""
        # Create a paper first
        create_req = mock_request(method='POST', body=sample_paper_data)
        create_resp = await create_paper(create_req)
        paper_id = json.loads(create_resp.body)['data']['id']

        # Add literature
        from src.agents_v2.api.paper_api import add_literature
        lit_req = mock_request(method='POST', body=sample_literature_data, match_info={'paperId': paper_id})
        response = await add_literature(lit_req)
        data = json.loads(response.body)

        assert response.status == 201
        assert data['success'] is True
        assert data['data']['title'] == sample_literature_data['title']
        assert 'id' in data['data']

    @pytest.mark.asyncio
    async def test_get_literature(self, mock_request, clean_storage, sample_literature_data):
        """Test getting literature by ID"""
        # Add literature directly to storage
        lit_id = str(uuid.uuid4())
        LITERATURE_STORAGE[lit_id] = {
            "id": lit_id,
            **sample_literature_data,
            "cited": False,
            "added_at": datetime.now().isoformat(),
        }

        from src.agents_v2.api.paper_api import get_literature
        request = mock_request(method='GET', match_info={'id': lit_id})
        response = await get_literature(request)
        data = json.loads(response.body)

        assert response.status == 200
        assert data['success'] is True
        assert data['data']['id'] == lit_id
        assert data['data']['title'] == sample_literature_data['title']

    @pytest.mark.asyncio
    async def test_get_literature_not_found(self, mock_request, clean_storage):
        """Test getting non-existent literature"""
        from src.agents_v2.api.paper_api import get_literature
        request = mock_request(method='GET', match_info={'id': 'non-existent'})

        response = await get_literature(request)
        data = json.loads(response.body)

        assert response.status == 404
        assert data['success'] is False

    @pytest.mark.asyncio
    async def test_get_citation(self, mock_request, clean_storage, sample_literature_data):
        """Test getting citation in different formats"""
        # Add literature to storage
        lit_id = str(uuid.uuid4())
        LITERATURE_STORAGE[lit_id] = {
            "id": lit_id,
            **sample_literature_data,
            "cited": False,
            "added_at": datetime.now().isoformat(),
        }

        from src.agents_v2.api.paper_api import get_citation

        # Test APA format
        request = mock_request(method='GET', query={'style': 'apa'}, match_info={'id': lit_id})
        response = await get_citation(request)
        data = json.loads(response.body)

        assert response.status == 200
        assert data['success'] is True
        assert 'citation' in data['data']
        assert data['data']['style'] == 'apa'

        # Test MLA format
        request = mock_request(method='GET', query={'style': 'mla'}, match_info={'id': lit_id})
        response = await get_citation(request)
        data = json.loads(response.body)

        assert response.status == 200
        assert data['data']['style'] == 'mla'

        # Test IEEE format
        request = mock_request(method='GET', query={'style': 'ieee'}, match_info={'id': lit_id})
        response = await get_citation(request)
        data = json.loads(response.body)

        assert response.status == 200
        assert data['data']['style'] == 'ieee'


# ============ Knowledge Graph Tests ============

class TestKnowledgeGraphOperations:
    """Test knowledge graph operations"""

    @pytest.mark.asyncio
    async def test_get_literature_graph_empty(self, mock_request, clean_storage):
        """Test getting knowledge graph when no literature exists"""
        from src.agents_v2.api.paper_api import get_literature_graph
        request = mock_request(method='GET')

        response = await get_literature_graph(request)
        data = json.loads(response.body)

        assert response.status == 200
        assert data['success'] is True
        assert data['data']['nodes'] == []
        assert data['data']['edges'] == []
        assert data['data']['stats']['totalEntities'] == 0

    @pytest.mark.asyncio
    async def test_get_literature_graph_with_data(self, mock_request, clean_storage, sample_literature_data):
        """Test getting knowledge graph with literature data"""
        # Add literature with keywords
        lit_id = str(uuid.uuid4())
        LITERATURE_STORAGE[lit_id] = {
            "id": lit_id,
            **sample_literature_data,
            "keywords": ["deep learning", "NLP", "transformers"],
            "cited": False,
            "added_at": datetime.now().isoformat(),
        }

        from src.agents_v2.api.paper_api import get_literature_graph
        request = mock_request(method='GET')

        response = await get_literature_graph(request)
        data = json.loads(response.body)

        assert response.status == 200
        assert data['success'] is True
        assert len(data['data']['nodes']) > 0
        assert data['data']['stats']['totalEntities'] > 0

    @pytest.mark.asyncio
    async def test_generate_literature_graph(self, mock_request, clean_storage, sample_literature_data):
        """Test generating knowledge graph from literature IDs"""
        # Add literature
        lit_id = str(uuid.uuid4())
        LITERATURE_STORAGE[lit_id] = {
            "id": lit_id,
            **sample_literature_data,
            "cited": False,
            "added_at": datetime.now().isoformat(),
        }

        from src.agents_v2.api.paper_api import generate_literature_graph
        request = mock_request(method='POST', body={"literatureIds": [lit_id]})

        response = await generate_literature_graph(request)
        data = json.loads(response.body)

        assert response.status == 200
        assert data['success'] is True
        assert data['data']['generated'] is True
        assert len(data['data']['nodes']) > 0


# ============ Edge Cases and Error Handling ============

class TestEdgeCases:
    """Test edge cases and error handling"""

    @pytest.mark.asyncio
    async def test_create_paper_with_minimal_data(self, mock_request, clean_storage):
        """Test creating paper with minimal required data"""
        request = mock_request(method='POST', body={})

        response = await create_paper(request)
        data = json.loads(response.body)

        assert response.status == 201
        assert data['success'] is True
        assert data['data']['title'] == "Untitled Paper"  # Default title
        assert data['data']['status'] == "draft"

    @pytest.mark.asyncio
    async def test_update_paper_partial(self, mock_request, clean_storage, sample_paper_data):
        """Test partial update of paper (only some fields)"""
        # Create paper
        create_req = mock_request(method='POST', body=sample_paper_data)
        create_resp = await create_paper(create_req)
        paper_id = json.loads(create_resp.body)['data']['id']

        # Partial update - only title
        update_req = mock_request(method='PUT', body={"title": "New Title Only"}, match_info={'id': paper_id})
        response = await update_paper(update_req)
        data = json.loads(response.body)

        assert response.status == 200
        assert data['data']['title'] == "New Title Only"
        assert data['data']['topic'] == sample_paper_data['topic']  # Unchanged

    @pytest.mark.asyncio
    async def test_list_papers_pagination(self, mock_request, clean_storage, sample_paper_data):
        """Test pagination in paper listing"""
        # Create multiple papers
        for i in range(5):
            paper_data = {**sample_paper_data, "title": f"Paper {i+1}"}
            create_req = mock_request(method='POST', body=paper_data)
            await create_paper(create_req)

        # Test first page
        list_req = mock_request(method='GET', query={'page': '1', 'pageSize': '2'})
        response = await list_papers(list_req)
        data = json.loads(response.body)

        assert response.status == 200
        assert len(data['data']) == 2
        assert data['total'] == 5
        assert data['page'] == 1
        assert data['pageSize'] == 2

        # Test second page
        list_req = mock_request(method='GET', query={'page': '2', 'pageSize': '2'})
        response = await list_papers(list_req)
        data = json.loads(response.body)

        assert len(data['data']) == 2

    @pytest.mark.asyncio
    async def test_storage_persistence_simulation(self, clean_storage, sample_paper_data):
        """Test that storage operations maintain data integrity"""
        # Create paper
        paper_id = str(uuid.uuid4())
        paper = {
            "id": paper_id,
            **sample_paper_data,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "literature_ids": [],
            "versions": [],
        }
        PAPERS_STORAGE[paper_id] = paper

        # Verify storage
        assert paper_id in PAPERS_STORAGE
        assert PAPERS_STORAGE[paper_id]['title'] == sample_paper_data['title']

        # Update
        PAPERS_STORAGE[paper_id]['title'] = "Updated Title"
        assert PAPERS_STORAGE[paper_id]['title'] == "Updated Title"

        # Delete
        del PAPERS_STORAGE[paper_id]
        assert paper_id not in PAPERS_STORAGE


# ============ Integration-style Tests ============

class TestIntegrationScenarios:
    """Test realistic usage scenarios"""

    @pytest.mark.asyncio
    async def test_full_paper_lifecycle(self, mock_request, clean_storage, sample_paper_data, sample_literature_data):
        """Test complete paper lifecycle: create -> update -> add literature -> delete"""
        # 1. Create paper
        create_req = mock_request(method='POST', body=sample_paper_data)
        create_resp = await create_paper(create_req)
        paper_data = json.loads(create_resp.body)['data']
        paper_id = paper_data['id']

        assert paper_data['title'] == sample_paper_data['title']

        # 2. Update paper
        update_req = mock_request(method='PUT', body={"title": "Final Title"}, match_info={'id': paper_id})
        update_resp = await update_paper(update_req)
        updated_data = json.loads(update_resp.body)['data']

        assert updated_data['title'] == "Final Title"

        # 3. Add literature
        from src.agents_v2.api.paper_api import add_literature
        lit_req = mock_request(method='POST', body=sample_literature_data, match_info={'paperId': paper_id})
        lit_resp = await add_literature(lit_req)
        lit_data = json.loads(lit_resp.body)['data']

        assert lit_data['title'] == sample_literature_data['title']

        # 4. Verify paper has literature reference
        get_req = mock_request(method='GET', match_info={'id': paper_id})
        get_resp = await get_paper(get_req)
        final_paper = json.loads(get_resp.body)['data']

        assert lit_data['id'] in final_paper.get('literature_ids', [])

        # 5. Delete paper
        delete_req = mock_request(method='DELETE', match_info={'id': paper_id})
        delete_resp = await delete_paper(delete_req)

        assert json.loads(delete_resp.body)['success'] is True

        # 6. Verify deletion
        verify_resp = await get_paper(get_req)
        assert verify_resp.status == 404

    @pytest.mark.asyncio
    async def test_multiple_papers_management(self, mock_request, clean_storage):
        """Test managing multiple papers simultaneously"""
        papers = []

        # Create 3 papers
        for i in range(3):
            paper_data = {
                "title": f"Paper {i+1}",
                "topic": f"Topic {i+1}",
                "status": "draft",
            }
            create_req = mock_request(method='POST', body=paper_data)
            resp = await create_paper(create_req)
            papers.append(json.loads(resp.body)['data'])

        # Verify all papers exist
        list_req = mock_request(method='GET', query={'page': '1', 'pageSize': '10'})
        list_resp = await list_papers(list_req)
        list_data = json.loads(list_resp.body)

        assert list_data['total'] == 3
        assert len(list_data['data']) == 3

        # Update one paper
        update_req = mock_request(
            method='PUT',
            body={"status": "reviewing"},
            match_info={'id': papers[1]['id']}
        )
        await update_paper(update_req)

        # Verify update
        get_req = mock_request(method='GET', match_info={'id': papers[1]['id']})
        get_resp = await get_paper(get_req)
        assert json.loads(get_resp.body)['data']['status'] == 'reviewing'

        # Delete one paper
        delete_req = mock_request(method='DELETE', match_info={'id': papers[0]['id']})
        await delete_paper(delete_req)

        # Verify remaining papers
        list_resp = await list_papers(list_req)
        list_data = json.loads(list_resp.body)

        assert list_data['total'] == 2


# ============ Run Tests ============

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
