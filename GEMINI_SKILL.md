---
name: django-service-layer-pattern
description: Architecture guide and pattern reference for building enterprise Django REST Framework services using Controller, Service Interfaces and Implementations, Models, Custom Exceptions, and Filter Layer Middleware Authentication.
---

# Django Layered Service Architecture Skill

A blueprint for implementing modular, production-grade enterprise backend services in Django / Django REST Framework (DRF) following separation of concerns.

## When to Use

- Structuring Django REST APIs with enterprise design patterns (Controller, Service Interface + Implementation, Model, Exceptions, Config).
- Implementing pre-controller filter authentication using custom Django Middleware.
- Preventing common DRF traps such as CSRF enforcement on token APIs and AnonymousUser bridge failures across middleware.

## Core Architectural Layers

1. **Config Layer (`app/config/app_config.py`)**: Centralizes application constants, file upload constraints, pagination defaults, and URL whitelists.
2. **Filter / Middleware Layer (`app/middlewares/auth_filter_middleware.py`)**: Authenticates custom bearer/session tokens before requests hit controllers. Returns early 401 JSON responses on missing or expired credentials.
3. **DRF Bridge Authentication (`app/middlewares/drf_passthrough_auth.py`)**: Bridges `request._request.user` into DRF's `request.user` to avoid AnonymousUser reassignment errors.
4. **Controllers Layer (`app/controllers/`)**: Thin APIViews that parse parameters, invoke service methods, and return serialized responses.
5. **Services Layer (`app/services/`)**:
   - `interfaces/`: Abstract Base Classes (ABCs) specifying business contracts.
   - `implementations/`: Concrete classes executing business rules and ORM queries.
6. **Models Layer (`app/models/`)**: Standard Django ORM persistence models.
7. **Exceptions Layer (`app/exceptions/custom_exceptions.py`)**: Custom domain exceptions mapped to standard HTTP status codes (e.g., 413, 403, 404).

## Critical Implementation Rules

- **CSRF Suppression on Token Endpoints**: When using token auth rather than browser session cookies, set `DEFAULT_AUTHENTICATION_CLASSES = ['app.middlewares.drf_passthrough_auth.FilterPassthroughAuthentication']` in `settings.py` to prevent default SessionAuthentication from triggering 403 CSRF token missing errors.
- **Middleware Whitelist**: Always check `request.path_info` against public routes before validating token headers.
