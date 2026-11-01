# Django AI / RAG Backend Service (Assignment 3A)

This project extends the Assignment 2 Django backend ([djangoapi-mgmt-service](https://github.com/asonib/djangoapi-mgmt-service)) with AI endpoints for LLM Q&A, document ingestion and chunking into a FAISS vector store, retrieval-augmented question answering, and a paginated AI query history.

The original layered architecture is kept unchanged:

```text
Request -> Middleware (token filter) -> Controller (APIView) -> Service Interface -> Service Implementation -> Models / FAISS / LLM
```

## Python Version: `3.12.x` / `3.13.x`

## New Endpoints (Assignment 3A)

| Method | Path                 | Description                                   |
|--------|----------------------|-----------------------------------------------|
| POST   | `/api/ask-ai`        | LLM Q&A with prompt templates                 |
| POST   | `/api/rag-query`     | RAG-based document query (answer + source chunks) |
| POST   | `/api/ingest-doc`    | Ingest and chunk a document into the vector store |
| GET    | `/api/query-history` | Paginated AI query history of the requester   |

All four endpoints need the same `Authorization: Token <token>` header as the Assignment 2 endpoints. The trailing slash is optional (`/api/ask-ai` and `/api/ask-ai/` both work).

## Technology Choices

| Concern      | Choice | Where |
|--------------|--------|-------|
| LLM          | Anthropic Claude via the official `anthropic` SDK (Messages API). Model is set with `ANTHROPIC_MODEL` (default `claude-sonnet-4-5`). Max tokens is 1024. No `temperature` is sent: anthropic SDK 2.x removed sampling parameters, so answer style is controlled by the prompt templates. | `app/services/implementations/anthropic_llm_service_impl.py` |
| Embeddings   | `sentence-transformers/all-MiniLM-L6-v2` runs locally and gives 384-dimensional vectors. Vectors are L2-normalised. No API key is needed. | `app/services/implementations/sentence_transformer_embedding_service_impl.py` |
| Vector store | **FAISS** (`faiss-cpu`) is used for every vector operation in this project. | `app/services/implementations/faiss_vector_store_impl.py` |
| Prompting    | Versioned prompt templates (`ask_ai_v1`, `rag_query_v1`) | `app/prompts/templates.py` |

### Vector Store: FAISS

* **Index type:** `IndexIDMap2(IndexFlatIP(384))`. It does an exact nearest-neighbour search using inner product. Because the vectors are L2-normalised, the inner product equals **cosine similarity**. A flat (exact) index is accurate and fast enough for the document volumes in this assignment, and it needs no training step.
* **IDs:** Each vector's FAISS id is the primary key of its `DocumentChunk` row. This means:
  * a search hit maps directly back to `document_id` and `chunk_text` in the database, and
  * re-ingesting or deleting a document removes exactly the right vectors with `remove_ids()`.
* **Tenant isolation:** Each user has their own index, stored at `vector_store/user_<id>.faiss`. A RAG query searches only the requester's index, so it can never return another user's chunks. As a second safeguard, retrieved ids are re-checked against `document__owner = request.user`.
* **Persistence:** The index is written to disk after every change. It is first written to a temporary file and then atomically renamed (`os.replace`), so a crash cannot leave a half-written index. Indexes are cached in memory and access is guarded by a process-wide lock. The folder is set by `VECTOR_STORE_DIR` (default `<project>/vector_store/`, which is git-ignored).
* **Consistency:** FAISS writes run inside the same database transaction that replaces the chunk rows. If FAISS fails, the chunk rows are rolled back and the document is marked `failed`. When a document is deleted through `DELETE /api/documents/<id>/`, its vectors are removed as well.

## Chunking Strategy (chunk size and overlap)

| Parameter       | Value | Constant |
|-----------------|-------|----------|
| `CHUNK_SIZE`    | **800 characters** | `AIConfigConstants.CHUNK_SIZE` |
| `CHUNK_OVERLAP` | **150 characters** (about 19%) | `AIConfigConstants.CHUNK_OVERLAP` |
| `RAG_TOP_K`     | 4 chunks | `AIConfigConstants.RAG_TOP_K` |
| `RAG_MIN_SIMILARITY` | 0.20 cosine | `AIConfigConstants.RAG_MIN_SIMILARITY` |

**Algorithm** (`RecursiveCharacterTextChunker`, in `app/services/implementations/text_chunker_impl.py`):

1. Normalise whitespace: unify line endings, collapse runs of spaces, and allow at most one blank line in a row.
2. Take a window of up to 800 characters. Then look backwards, but never past the middle of the window, for the strongest natural break. The order of preference is: paragraph (`\n\n`), line (`\n`), sentence (`. ` `? ` `! `), clause (`; ` `, `), and finally any space. If no break is found, the text is cut at exactly 800 characters.
3. Start the next window 150 characters before the previous window ended, moved forward to the start of a word, so chunks never begin in the middle of a word.
4. Each chunk is stored with its `chunk_index` and its `start_char`/`end_char` position in the normalised text.

**Why these values:**

* 800 characters is roughly 150–200 tokens. That fits within the 256 word-piece input limit of `all-MiniLM-L6-v2`, so the embedding model never silently cuts off part of a chunk.
* A chunk of that size usually holds one or two paragraphs. That is enough context for the LLM to answer, while staying specific enough for retrieval to be precise.
* The 150-character overlap means a sentence that crosses a chunk boundary still appears whole in at least one chunk.
* Four chunks of 800 characters add only about 3.2k characters of context per RAG call, which keeps latency and cost low.

All of these values are defined in one place, `app/config/app_config.py`, and every `ingest-doc` response echoes them back.

## Prompt Templates (no raw user input to the model)

User text is never passed to the model unchanged. Every call goes through a template that has a **system prompt** (role and rules) and a **user message** where the untrusted input is wrapped in delimiters:

* `ask_ai_v1`: the input goes inside `<user_question>…</user_question>`. The system prompt tells the model to treat that content as data and to ignore instructions inside it that try to change its role or reveal the prompt.
* `rag_query_v1`: retrieved chunks go inside `<context><source document_id=… chunk_index=…>…</source></context>` and the question goes inside `<question>…</question>`. The model must answer **only** from the context, cite sources as `[document_id:chunk_index]`, and reply *"I could not find the answer in the provided documents."* when the context does not contain the answer.
* If user text tries to close a delimiter (`</user_question>`), it is neutralised. Braces in user text (`{…}`) are never treated as template placeholders.
* If retrieval finds no chunk above the similarity threshold, the API returns the "could not find" answer **without calling the LLM**. This saves cost and stops the model from answering from its general training knowledge.

The template name is saved with every request (`prompt_template` in `AIQueryLog`), so answers can be traced back to the template version that produced them.

## New Project Files

```text
app/
├── config/app_config.py                 # + AIConfigConstants (chunking, retrieval, LLM, limits)
├── controllers/
│   ├── ai_controller.py                 # AskAI / RagQuery / IngestDoc / AIQueryHistory controllers
│   └── pagination.py                    # shared StandardResultsPagination (Assignment 2 pattern)
├── exceptions/custom_exceptions.py      # + 422 EmptyDocument, 502 LLMService, 503 LLMNotConfigured/Embedding, 500 VectorStore
├── migrations/0002_ai_rag_layer.py
├── models/
│   ├── document.py                      # + ingestion_status, chunk_count, ingested_at
│   ├── document_chunk.py                # chunk text + offsets (pk == FAISS vector id)
│   └── ai_query_log.py                  # ask-ai / rag-query audit trail with sources and token usage
├── prompts/templates.py                 # PromptTemplate + ask_ai_v1 / rag_query_v1
├── serializers/ai_serializers.py        # request DTOs + response shapes
├── services/
│   ├── container.py                     # composition root (dependency injection)
│   ├── interfaces/                      # ILLMService, IEmbeddingService, IVectorStore, ITextChunker,
│   │                                    # IDocumentIngestionService, IAIQueryService
│   └── implementations/                 # Anthropic, SentenceTransformer, FAISS, chunker,
│                                        # DocumentIngestionServiceImpl, AIQueryServiceImpl
└── tests/                               # 23 tests, offline (fake LLM, fake embeddings, in-memory store)
samples/engineering-handbook.txt         # sample document for trying RAG
```

## Environment Variables

Copy `.env.example` to `.env` and fill it in. **Never commit API keys.** `.env` and `key.txt` are git-ignored.

```bash
SECRET_KEY=your-django-secret-key
DEBUG=True
ALLOWED_HOSTS=*

ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-4-5
# VECTOR_STORE_DIR=./vector_store
# EMBEDDING_CACHE_DIR=./.hf_cache
```

## Setup

```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 8000
```

> The first call to `ingest-doc` or `rag-query` downloads the embedding model (about 90 MB) from Hugging Face. After that, the model is cached locally.

## Running Tests

```bash
python manage.py test
```

The test suite runs fully offline. It injects a fake LLM, a hashing-based fake embedder and an in-memory vector store through `app.services.container.override(...)`. When `faiss-cpu` is installed, a separate test also checks the real FAISS store (add, search, remove, and persist/reload).

## API cURL Examples: AI / RAG

***1. Ask AI (prompt template)***
```bash
curl --location 'http://localhost:8000/api/ask-ai' \
--header 'Authorization: Token <YOUR_AUTH_TOKEN>' \
--header 'Content-Type: application/json' \
--data '{ "prompt": "Explain retrieval-augmented generation in two sentences." }'
```
```json
{
  "id": 1,
  "prompt": "Explain retrieval-augmented generation in two sentences.",
  "response": "Retrieval-augmented generation (RAG) ...",
  "prompt_template": "ask_ai_v1",
  "model": "claude-sonnet-4-5",
  "usage": { "input_tokens": 182, "output_tokens": 64 },
  "latency_ms": 1432,
  "created_at": "2026-11-01T10:00:00Z"
}
```

***2. Upload a document, then ingest it***
```bash
curl --location 'http://localhost:8000/api/documents/' \
--header 'Authorization: Token <YOUR_AUTH_TOKEN>' \
--form 'title="Engineering Handbook"' \
--form 'file=@"samples/engineering-handbook.txt"'

curl --location 'http://localhost:8000/api/ingest-doc' \
--header 'Authorization: Token <YOUR_AUTH_TOKEN>' \
--header 'Content-Type: application/json' \
--data '{ "document_id": 1 }'
```
```json
{
  "document_id": 1,
  "title": "Engineering Handbook",
  "status": "ingested",
  "chunk_count": 3,
  "chunk_size": 800,
  "chunk_overlap": 150,
  "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
  "vector_store": "faiss",
  "replaced_chunks": 0,
  "ingested_at": "2026-11-01T10:01:00Z"
}
```

***3. RAG query (answer + source chunks)***
```bash
curl --location 'http://localhost:8000/api/rag-query' \
--header 'Authorization: Token <YOUR_AUTH_TOKEN>' \
--header 'Content-Type: application/json' \
--data '{ "query": "When does billing reconciliation run?" }'
```
```json
{
  "id": 2,
  "query": "When does billing reconciliation run?",
  "answer": "Billing reconciliation runs nightly at 02:00 UTC [1:0].",
  "sources": [
    {
      "document_id": 1,
      "chunk_text": "# Acme Platform Engineering Handbook\n\n## Billing\nThe billing service runs nightly at 02:00 UTC ...",
      "document_title": "Engineering Handbook",
      "chunk_id": 1,
      "chunk_index": 0,
      "score": 0.6123
    }
  ],
  "prompt_template": "rag_query_v1",
  "model": "claude-sonnet-4-5",
  "usage": { "input_tokens": 905, "output_tokens": 21 },
  "latency_ms": 1610,
  "created_at": "2026-11-01T10:02:00Z"
}
```

***4. AI query history (same pagination as Assignment 2)***
```bash
curl --location 'http://localhost:8000/api/query-history?page=1&page_size=10' \
--header 'Authorization: Token <YOUR_AUTH_TOKEN>'
```
```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    { "id": 2, "query_type": "rag_query", "input_text": "When does billing reconciliation run?", "response_text": "...", "sources": [ ... ], "prompt_template": "rag_query_v1", "model_name": "claude-sonnet-4-5", "input_tokens": 905, "output_tokens": 21, "latency_ms": 1610, "created_at": "..." },
    { "id": 1, "query_type": "ask_ai", "input_text": "Explain retrieval-augmented generation ...", "response_text": "...", "sources": [], "...": "..." }
  ]
}
```

### Error Responses

| Status | When |
|--------|------|
| 400 | Missing or blank `prompt`/`query`/`document_id`, prompt longer than 4000 characters, query longer than 2000 characters |
| 401 | Missing, invalid or expired token (raised by the middleware filter) |
| 404 | Document does not exist **or belongs to another user**; page number out of range |
| 422 | Document has no extractable text |
| 502 | Anthropic API error or rate limit |
| 503 | `ANTHROPIC_API_KEY` missing or rejected, or the embedding model could not be loaded |
| 500 | FAISS read/write failure (the document is marked `failed`) |

## Assignment 2 Endpoints (unchanged)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/register/` | Register and receive a token |
| POST | `/api/auth/login/` | Log in and receive a token |
| POST / GET | `/api/documents/` | Upload (JSON or multipart) / list documents (paginated) |
| GET / DELETE | `/api/documents/<id>/` | Retrieve / delete a document (also removes its vectors) |
| POST | `/api/query/` | Log a query |
| GET | `/api/queries/` | Query log history (paginated) |

A Postman collection with all endpoints, including the new **AI / RAG** folder, is in `_.postman_collection.json`. Uploading a JSON document automatically fills in the `document_id` variable used by *Ingest Document*.

## Swagger & ReDoc Documentation

- **Swagger UI**: http://localhost:8000/api/docs/
- **ReDoc**: http://localhost:8000/api/redoc/
- **OpenAPI Schema**: http://localhost:8000/api/schema/

## Known Limitations

* Uploaded files are decoded as UTF-8 text, as in Assignment 2. PDF and DOCX uploads are not parsed into text yet, so ingesting them gives poor-quality chunks. Use `.txt`, `.csv` or `.json` for RAG.
* Ingestion runs synchronously inside the request. That is fine for documents up to the 5 MB upload limit, but a production system would move it to a background worker such as Celery.
* Each user's FAISS index is held in memory by the Django process. Running several worker processes would need a shared vector store (for example pgvector or a FAISS server) or per-process index reloads.
