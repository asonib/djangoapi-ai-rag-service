# CLAUDE.md - Django Enterprise Layered Architecture Guide

Guidelines, coding conventions, and architectural contracts for development within this codebase.

## Architectural Principles

This codebase enforces strict separation of concerns across clean architectural boundaries:

```text
Request -> Middleware (Filter Layer) -> Controller (View) -> Service Interface -> Service Implementation -> Models (ORM)
```

1. **Controllers (`app/controllers/`)**:
   - Thin REST dispatchers extending DRF `APIView`.
   - Sole responsibility: parse inputs, validate DTOs via serializers, call appropriate service method, and return HTTP status responses.
   - **No direct ORM queries or database transactions inside controllers.**

2. **Services (`app/services/`)**:
   - **`interfaces/`**: Define business contracts using Python's `abc.ABC` and `@abstractmethod`.
   - **`implementations/`**: Encapsulate all business validation, external integrations, and ORM persistence operations.
   - Inject dependencies through constructors where applicable.

3. **Models (`app/models/`)**:
   - Pure Django ORM models representing persistent relational schemas.
   - Models must be exposed in `app/models/__init__.py` for migration autodetection.

4. **Filter / Middleware Layer (`app/middlewares/`)**:
   - Authenticate incoming requests in the filter layer *before* reaching controllers.
   - Whitelist public endpoints defined in `AppConfigConstants.PUBLIC_URL_PREFIXES`.
   - Attach verified `user` and `session` instances directly to `request.user` and `request.user_session`.

5. **Config & Exceptions (`app/config/`, `app/exceptions/`)**:
   - Centralize environment-agnostic constants (page limits, size limits, allowed extensions) in `app_config.py`.
   - Extend DRF `APIException` with explicit `status_code` and `default_detail` for predictable HTTP mapping.

6. **AI / RAG Layer (Assignment 3A)**:
   - Infrastructure contracts live in `app/services/interfaces/` (`ILLMService`, `IEmbeddingService`, `IVectorStore`, `ITextChunker`); business contracts are `IDocumentIngestionService` and `IAIQueryService`.
   - Controllers obtain wired services from `app/services/container.py` (composition root). Never instantiate the Anthropic client, embedding model or FAISS index inside a controller.
   - Never send raw user input to the LLM: render it through a `PromptTemplate` in `app/prompts/templates.py`. Bump the template name (`_v2`) when changing prompt semantics.
   - FAISS vector ids == `DocumentChunk.pk`; one index per user (`user_<id>` namespace). Chunk size/overlap live only in `AIConfigConstants` and must stay documented in README.
   - Tests must stay offline: use `container.override(...)` with the fakes in `app/tests/fakes.py`.
   - Secrets (`ANTHROPIC_API_KEY`) come from `.env`; never commit `key.txt` or `.env`.

---

## Critical Django & DRF Traps & Conventions

### 1. The `AnonymousUser` Bridge Trap
Django's WSGI middleware initializes `request.user`. However, DRF's `APIView` wraps standard Django requests in a DRF `Request` instance and can revert `request.user` to `AnonymousUser` if DRF's authentication classes are left blank or unset.
- **Rule**: Always include `FilterPassthroughAuthentication` in `REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES']` so DRF references the user authenticated by the middleware.

### 2. CSRF on Token-Based APIs
If DRF defaults fall back to `SessionAuthentication`, any `POST`, `PUT`, or `DELETE` call without a CSRF cookie triggers `403 CSRF token missing`.
- **Rule**: Never leave `SessionAuthentication` enabled for purely token-authenticated endpoints. Rely on the custom passthrough class and bearer/token headers.

### 3. File Uploads & Constraints
- Validate file size against `AppConfigConstants.MAX_FILE_SIZE_BYTES` (raise `PayloadTooLargeException` -> `HTTP 413`).
- Validate file extension against `AppConfigConstants.ALLOWED_EXTENSIONS` (raise `UnsupportedFileTypeException` -> `HTTP 400`).

---

## Development & Test Commands

- **Run Dev Server**: `python manage.py runserver 8000`
- **Make Migrations**: `python manage.py makemigrations app`
- **Apply Migrations**: `python manage.py migrate`
- **Run Tests**: `python manage.py test`
- **OpenAPI Schema Generation**: Accessible at `/api/schema/`, Swagger UI at `/api/docs/`, ReDoc at `/api/redoc/`.
