# GitHub Copilot & Coding Agent Instructions

## Scope & Target Stack
- Framework: Django 5.x / Django REST Framework 3.15+
- Pattern: Enterprise Layered Architecture (Controller -> Service Interface/Impl -> Model)
- Authentication: Pre-controller Middleware Token Authentication with DRF Passthrough

## Architecture Constraints

When proposing code modifications or adding features, adhere to these rules:

1. **Layer Separation**:
   - Put routing endpoints in `app/controllers/<feature>_controller.py`. Use classes extending `rest_framework.views.APIView`.
   - Define service contracts in `app/services/interfaces/<feature>_service_interface.py` using `abc.ABC`.
   - Implement concrete business logic and ORM transactions in `app/services/implementations/<feature>_service_impl.py`.
   - Controllers must never call `Model.objects` directly; delegate all data queries to the service implementation.

2. **Middleware & Authentication Layer**:
   - Custom authentication filter executes in `app/middlewares/auth_filter_middleware.py`.
   - Never remove or bypass `app.middlewares.drf_passthrough_auth.FilterPassthroughAuthentication` in `REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES']`. It ensures `request.user` set in middleware carries over into DRF request instances.
   - If adding new public endpoints, append their path prefix to `AppConfigConstants.PUBLIC_URL_PREFIXES` in `app/config/app_config.py`.

3. **Error Handling**:
   - Do not catch generic `Exception` inside controllers without raising or returning standard DRF error responses.
   - Throw custom exceptions from `app/exceptions/custom_exceptions.py` inside service implementations.
   - Enforce HTTP 413 for payload limit overages, HTTP 403 for ownership permission issues, and HTTP 404 when resources do not belong to the requesting user.

4. **Model Imports**:
   - When adding new models under `app/models/`, always export them in `app/models/__init__.py` to ensure `makemigrations` tracks them properly.
