"""Tests for RAG service layer — IngestService and VectorStoreRepository."""

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.documents import Document

from app.repository.vector_store import VectorStoreRepository
from app.service.ingest import IngestService


class TestIngestService:
    """IngestService orchestrates load → split → store."""

    @pytest.fixture
    def mock_repo(self):
        return MagicMock(spec=VectorStoreRepository)

    @pytest.fixture
    def service(self, mock_repo):
        return IngestService(vector_store_repo=mock_repo)

    def test_ingest_no_documents(self, service, mock_repo):
        with patch("rag.service.ingest.LenovoDocumentLoader") as MockLoader:
            MockLoader.return_value.load.return_value = []
            service.ingest([1])
        mock_repo.add_documents.assert_not_called()

    def test_ingest_calls_add_documents(self, service, mock_repo):
        fake_docs = [Document(page_content="hello world", metadata={"source": "test"})]
        with patch("rag.service.ingest.LenovoDocumentLoader") as MockLoader:
            MockLoader.return_value.load.return_value = fake_docs
            service.ingest([1])
        mock_repo.add_documents.assert_called_once_with(documents=fake_docs)

    def test_ingest_strips_empty_content(self, service, mock_repo):
        fake_docs = [
            Document(page_content="valid", metadata={}),
            Document(page_content="   ", metadata={}),
            Document(page_content="also valid", metadata={}),
        ]
        with patch("rag.service.ingest.LenovoDocumentLoader") as MockLoader:
            MockLoader.return_value.load.return_value = fake_docs
            service.ingest([1])
        called_docs = mock_repo.add_documents.call_args[1]["documents"]
        assert len(called_docs) == 2
        assert called_docs[0].page_content == "valid"
        assert called_docs[1].page_content == "also valid"

    def test_ingest_knowledge_no_passed_to_loader(self, service):
        with patch("rag.service.ingest.LenovoDocumentLoader") as MockLoader:
            MockLoader.return_value.load.return_value = []
            service.ingest([10, 20, 30])
        MockLoader.assert_called_once_with(knowledge_no_list=[10, 20, 30])


class TestVectorStoreRepository:
    """VectorStoreRepository stores documents into Milvus."""

    @pytest.fixture
    def mock_embedding(self):
        emb = MagicMock()
        emb.embed_documents.return_value = [[0.1] * 128, [0.2] * 128]
        return emb

    @pytest.fixture
    def milvus_config(self):
        cfg = MagicMock()
        cfg.milvus_uri = "http://localhost:19530"
        cfg.milvus_user = ""
        cfg.milvus_password = ""
        cfg.milvus_db = ""
        cfg.milvus_timeout = 3
        return cfg

    def test_add_documents(self, mock_embedding, milvus_config):
        client = MagicMock()
        client.has_collection.return_value = True
        client.insert.return_value = {"insert_count": 2}

        with patch("rag.repository.vector_store.MilvusClient", return_value=client):
            repo = VectorStoreRepository(
                embedding=mock_embedding,
                milvus_config=milvus_config,
            )
            docs = [
                Document(page_content="doc a", metadata={"source": "a"}),
                Document(page_content="doc b", metadata={"source": "b"}),
            ]
            n = repo.add_documents(docs)

        assert n == 2
        client.insert.assert_called_once()
        call_data = client.insert.call_args[1]["data"]
        assert len(call_data) == 2
        assert call_data[0]["text"] == "doc a"
        assert call_data[0]["source"] == "a"

    def test_add_documents_empty(self, mock_embedding, milvus_config):
        with patch("rag.repository.vector_store.MilvusClient", return_value=MagicMock()):
            repo = VectorStoreRepository(
                embedding=mock_embedding,
                milvus_config=milvus_config,
            )
            n = repo.add_documents([])
        assert n == 0

    def test_add_documents_auto_creates_collection(self, mock_embedding, milvus_config):
        client = MagicMock()
        client.has_collection.return_value = False
        client.insert.return_value = {"insert_count": 1}

        with patch("rag.repository.vector_store.MilvusClient", return_value=client):
            repo = VectorStoreRepository(
                embedding=mock_embedding,
                milvus_config=milvus_config,
            )
            docs = [Document(page_content="hello", metadata={})]
            repo.add_documents(docs)

        client.create_schema.assert_called_once()
        client.prepare_index_params.assert_called_once()
        client.create_collection.assert_called_once()
