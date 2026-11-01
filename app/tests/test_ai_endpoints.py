import shutil
import tempfile
import unittest

import numpy as np
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from app.models import AIQueryLog, Document, DocumentChunk, UserSession
from app.services import container
from app.tests.fakes import FakeEmbeddingService, FakeLLMService, InMemoryVectorStore

DOC_TEXT = (
    "The billing service runs nightly at 02:00 UTC and reconciles invoices with the payment gateway. "
    "Billing failures are retried three times before an alert pages the billing on-call engineer.\n\n"
    "The authentication service issues opaque tokens that expire after seven days. Tokens are "
    "stored hashed and revoked immediately when a user changes their password.\n\n"
    "Search is powered by an Elasticsearch cluster with three data nodes. Index mappings are "
    "versioned in git and rolled out with a blue/green alias swap to avoid downtime.\n\n"
    "Application logs are shipped to a central Loki instance and retained for thirty days. "
    "Dashboards in Grafana visualise latency percentiles, error budgets and saturation.\n\n"
    "Deployments go through GitHub Actions: lint, unit tests, container build, staging smoke "
    "tests and finally a canary release that receives five percent of production traffic.\n\n"
    "Database backups are taken every six hours, encrypted with KMS keys, copied to a second "
    "region and restored weekly into a scratch environment to verify integrity."
)


class AIEndpointTests(TestCase):
    def setUp(self):
        self.llm = FakeLLMService(reply="It runs at 02:00 UTC [1:0].")
        self.store = InMemoryVectorStore()
        container.override(llm_service=self.llm, embedding_service=FakeEmbeddingService(), vector_store=self.store)
        self.addCleanup(container.reset)

        self.alice = User.objects.create_user("alice", password="pw")
        self.bob = User.objects.create_user("bob", password="pw")
        self.client = self._client_for(self.alice)
        self.doc = Document.objects.create(title="Ops Handbook", content=DOC_TEXT, owner=self.alice)

    @staticmethod
    def _client_for(user):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Token {UserSession.create_session(user).token}")
        return client

    # ------------------------------------------------------------ auth filter
    def test_endpoints_require_token(self):
        anon = APIClient()
        for method, url in [("post", "/api/ask-ai"), ("post", "/api/rag-query"),
                            ("post", "/api/ingest-doc"), ("get", "/api/query-history")]:
            self.assertEqual(getattr(anon, method)(url, {}, format="json").status_code, 401, url)

    # ----------------------------------------------------------------- ask-ai
    def test_ask_ai_uses_prompt_template(self):
        res = self.client.post("/api/ask-ai", {"prompt": "What is FAISS?"}, format="json")
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(res.data["response"], self.llm.reply)
        self.assertEqual(res.data["prompt_template"], "ask_ai_v1")
        sent = self.llm.calls[0]["messages"][0]["content"]
        self.assertIn("<user_question>\nWhat is FAISS?\n</user_question>", sent)
        self.assertNotEqual(sent, "What is FAISS?")
        self.assertTrue(self.llm.calls[0]["system"])
        self.assertEqual(AIQueryLog.objects.filter(user=self.alice, query_type="ask_ai").count(), 1)

    def test_ask_ai_validation(self):
        self.assertEqual(self.client.post("/api/ask-ai", {}, format="json").status_code, 400)
        self.assertEqual(self.client.post("/api/ask-ai", {"prompt": "   "}, format="json").status_code, 400)
        self.assertEqual(self.client.post("/api/ask-ai/", {"prompt": "x" * 5000}, format="json").status_code, 400)
        self.assertEqual(self.llm.calls, [])

    # ------------------------------------------------------------- ingest-doc
    def test_ingest_doc_chunks_and_stores_embeddings(self):
        res = self.client.post("/api/ingest-doc", {"document_id": self.doc.id}, format="json")
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(res.data["status"], "ingested")
        self.assertGreater(res.data["chunk_count"], 1)
        self.assertEqual(res.data["chunk_size"], 800)
        self.assertEqual(res.data["chunk_overlap"], 150)
        self.assertEqual(res.data["vector_store"], "faiss")
        self.assertEqual(DocumentChunk.objects.filter(document=self.doc).count(), res.data["chunk_count"])
        self.assertEqual(self.store.count(f"user_{self.alice.id}"), res.data["chunk_count"])
        self.doc.refresh_from_db()
        self.assertEqual(self.doc.ingestion_status, Document.STATUS_INGESTED)

    def test_reingest_replaces_previous_chunks(self):
        first = self.client.post("/api/ingest-doc", {"document_id": self.doc.id}, format="json").data
        second = self.client.post("/api/ingest-doc", {"document_id": self.doc.id}, format="json").data
        self.assertEqual(second["replaced_chunks"], first["chunk_count"])
        self.assertEqual(self.store.count(f"user_{self.alice.id}"), second["chunk_count"])

    def test_ingest_other_users_document_is_404(self):
        res = self._client_for(self.bob).post("/api/ingest-doc", {"document_id": self.doc.id}, format="json")
        self.assertEqual(res.status_code, 404)

    def test_ingest_validation_and_empty_document(self):
        self.assertEqual(self.client.post("/api/ingest-doc", {}, format="json").status_code, 400)
        self.assertEqual(self.client.post("/api/ingest-doc", {"document_id": "abc"}, format="json").status_code, 400)
        self.assertEqual(self.client.post("/api/ingest-doc", {"document_id": 99999}, format="json").status_code, 404)
        empty = Document.objects.create(title="Empty", content="  \n ", owner=self.alice)
        res = self.client.post("/api/ingest-doc", {"document_id": empty.id}, format="json")
        self.assertEqual(res.status_code, 422)
        empty.refresh_from_db()
        self.assertEqual(empty.ingestion_status, Document.STATUS_FAILED)

    # -------------------------------------------------------------- rag-query
    def test_rag_query_returns_answer_and_source_chunks(self):
        self.client.post("/api/ingest-doc", {"document_id": self.doc.id}, format="json")
        res = self.client.post("/api/rag-query", {"query": "When does the billing service reconcile invoices?"},
                               format="json")
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(res.data["answer"], self.llm.reply)
        self.assertGreaterEqual(len(res.data["sources"]), 1)
        top = res.data["sources"][0]
        self.assertEqual(top["document_id"], self.doc.id)
        self.assertIn("billing service", top["chunk_text"])
        # retrieved chunks are what the LLM saw
        sent = self.llm.calls[0]["messages"][0]["content"]
        self.assertIn("<context>", sent)
        self.assertIn(top["chunk_text"], sent)
        log = AIQueryLog.objects.get(id=res.data["id"])
        self.assertEqual(log.sources[0]["document_id"], self.doc.id)

    def test_rag_query_without_ingested_docs_skips_llm(self):
        res = self.client.post("/api/rag-query", {"query": "billing"}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["sources"], [])
        self.assertEqual(self.llm.calls, [])

    def test_rag_query_is_isolated_per_user(self):
        self.client.post("/api/ingest-doc", {"document_id": self.doc.id}, format="json")
        res = self._client_for(self.bob).post("/api/rag-query", {"query": "billing service invoices"}, format="json")
        self.assertEqual(res.data["sources"], [])

    def test_deleting_document_purges_vectors(self):
        self.client.post("/api/ingest-doc", {"document_id": self.doc.id}, format="json")
        self.assertEqual(self.client.delete(f"/api/documents/{self.doc.id}/").status_code, 204)
        self.assertEqual(self.store.count(f"user_{self.alice.id}"), 0)

    # ---------------------------------------------------------- query-history
    def test_query_history_is_paginated_and_scoped(self):
        for i in range(12):
            self.client.post("/api/ask-ai", {"prompt": f"question {i}"}, format="json")
        self._client_for(self.bob).post("/api/ask-ai", {"prompt": "bob's question"}, format="json")

        res = self.client.get("/api/query-history?page=1&page_size=5")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["count"], 12)
        self.assertEqual(len(res.data["results"]), 5)
        self.assertIsNotNone(res.data["next"])
        self.assertIsNone(res.data["previous"])
        self.assertEqual(res.data["results"][0]["input_text"], "question 11")  # newest first

        default = self.client.get("/api/query-history")
        self.assertEqual(len(default.data["results"]), 10)
        self.assertEqual(self.client.get("/api/query-history?page=99").status_code, 404)


try:
    import faiss  # noqa: F401
    HAS_FAISS = True
except ImportError:
    HAS_FAISS = False


@unittest.skipUnless(HAS_FAISS, "faiss-cpu not installed")
class FaissVectorStoreTests(TestCase):
    def setUp(self):
        from app.services.implementations.faiss_vector_store_impl import FaissVectorStore
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        FaissVectorStore._cache.clear()
        self.store = FaissVectorStore(base_dir=self.tmp, dimension=4)

    def test_add_search_remove_and_persist(self):
        from app.services.implementations.faiss_vector_store_impl import FaissVectorStore
        vecs = np.eye(4, dtype=np.float32)
        self.store.add("user_1", [10, 11, 12, 13], vecs)
        hits = self.store.search("user_1", vecs[2], top_k=2)
        self.assertEqual(hits[0][0], 12)
        self.assertAlmostEqual(hits[0][1], 1.0, places=5)
        self.assertEqual(self.store.remove("user_1", [12]), 1)
        self.assertNotIn(12, [i for i, _ in self.store.search("user_1", vecs[2], top_k=4)])
        self.assertEqual(self.store.search("user_2", vecs[0], top_k=4), [])

        FaissVectorStore._cache.clear()  # force reload from disk
        self.assertEqual(FaissVectorStore(base_dir=self.tmp, dimension=4).count("user_1"), 3)
