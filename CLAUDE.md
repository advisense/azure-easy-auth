# CLAUDE.md

## Project Overview
Python library that makes it easy to get authentication info from users authenticated through Azure Easy Auth (Azure App Service authentication/authorization module).

## Purpose
Applications running on Azure App Service with the authentication module enabled receive identity headers on every request. This library parses those headers into a clean `EasyAuthUser` object, exposing user info and claims without any external dependencies.

## Key Features
- Parse `X-MS-CLIENT-PRINCIPAL` (base64-encoded claims JWT) and related headers
- Convenience properties for common identity fields: `email`, `object_id`, `roles`, `groups`
- Arbitrary claim lookup via `get_claim()` / `get_claims()`
- Case-insensitive header handling — works with Flask, FastAPI, Django out of the box
- Zero external dependencies (stdlib only)

## Tech Stack
- Python 3.9+
- `uv` for dependency management and virtual environments
- `uv_build` as the build backend
- `pytest` for tests

## Architecture
Single-module library under `src/azure_easy_auth/`:

- `_auth.py` — all implementation: `_decode_principal()`, `EasyAuthUser` dataclass, `from_headers()`, `is_authenticated()`
- `__init__.py` — re-exports the public API: `Claim`, `EasyAuthUser`, `from_headers`, `is_authenticated`

No framework integration code is included; the library accepts any `Mapping[str, str]`, so it works with any framework's headers object.

## Development

### Prerequisites
- Python 3.9+
- [uv](https://docs.astral.sh/uv/)

### Getting started
```bash
git clone https://github.com/advisense/azure-easy-auth
cd azure-easy-auth
uv sync --extra dev
```

### Building
```bash
uv build
```

### Testing
```bash
pytest
```

Tests live in `tests/test_auth.py`. Use `_make_principal()` helper in the test file to construct realistic `X-MS-CLIENT-PRINCIPAL` payloads for new test cases.

## Branching
- `main` — stable, production-ready
- `develop` — active development, PRs target this branch

## API Reference
See [README.md](README.md) for the full public API reference and usage examples.

## Additional Resources
- [Azure App Service authentication user identities](https://learn.microsoft.com/en-us/azure/app-service/configure-authentication-user-identities)
- [uv documentation](https://docs.astral.sh/uv/)
