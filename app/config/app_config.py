class AppConfigConstants:
    DEFAULT_PAGE_SIZE = 10
    MAX_PAGE_SIZE = 100
    MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
    ALLOWED_EXTENSIONS = [".txt", ".pdf", ".docx", ".csv", ".json"]
    TOKEN_EXPIRY_DAYS = 7
    PUBLIC_URL_PREFIXES = [
        "/api/auth/register",
        "/api/auth/login",
        "/api/schema",
        "/api/docs",
        "/api/redoc",
        "/admin",
    ]


class AIConfigConstants:
    """
    Environment-agnostic constants for the AI / RAG layer (Assignment 3A).
    Secrets and environment-specific values (API key, model id, index path)
    live in settings.py and are read from the environment / .env file.
    """

    # ---- Chunking (documented in README -> "Chunking Strategy") ----
    # Measured in characters. ~800 chars ≈ 150-200 tokens, comfortably below the
    # 256 word-piece input limit of all-MiniLM-L6-v2, so no chunk gets truncated
    # by the embedding model.
    CHUNK_SIZE = 800
    # ~19% overlap so a sentence that straddles a boundary is fully present in
    # at least one chunk.
    CHUNK_OVERLAP = 150
    # Hard upper bound to protect the embedding step from pathological inputs.
    MAX_CHUNKS_PER_DOCUMENT = 2000

    # ---- Embeddings ----
    EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION = 384
    EMBEDDING_BATCH_SIZE = 32

    # ---- Vector store ----
    VECTOR_STORE_BACKEND = "faiss"
    VECTOR_INDEX_TYPE = "IndexIDMap2(IndexFlatIP)"  # cosine similarity on L2-normalised vectors

    # ---- Retrieval ----
    RAG_TOP_K = 4
    # Chunks scoring below this cosine similarity are treated as irrelevant.
    RAG_MIN_SIMILARITY = 0.20

    # ---- LLM ----
    LLM_PROVIDER = "anthropic"
    LLM_MAX_TOKENS = 1024
    LLM_TIMEOUT_SECONDS = 60

    # ---- Input limits ----
    MAX_PROMPT_CHARS = 4000
    MAX_QUERY_CHARS = 2000

    # ---- Query types persisted in AIQueryLog ----
    QUERY_TYPE_ASK_AI = "ask_ai"
    QUERY_TYPE_RAG = "rag_query"
