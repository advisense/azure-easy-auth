# azure-easy-auth

Simple library to enable the "Easy" in Azure Easy Authentication.

Parses the headers injected by [Azure App Service authentication](https://learn.microsoft.com/en-us/azure/app-service/configure-authentication-user-identities) into a clean Python object — no external dependencies required.

## Requirements

- Python 3.9+
- An Azure App Service with the **Authentication** module enabled

## Installation

```bash
pip install git+https://github.com/advisense/azure-easy-auth.git
```

Or with `uv`:

```bash
uv add git+https://github.com/advisense/azure-easy-auth.git
```

## How it works

When App Service authentication is enabled, Azure injects several HTTP headers into every authenticated request before it reaches your application:

| Header | Description |
|---|---|
| `X-MS-CLIENT-PRINCIPAL` | Base64-encoded JSON with all identity claims |
| `X-MS-CLIENT-PRINCIPAL-NAME` | User's display name |
| `X-MS-CLIENT-PRINCIPAL-ID` | User's object/subject ID |
| `X-MS-CLIENT-PRINCIPAL-IDP` | Identity provider (`aad`, `google`, etc.) |

`azure-easy-auth` decodes these headers and exposes the data through a simple `EasyAuthUser` object.

## Usage

### Basic

```python
from azure_easy_auth import from_headers, is_authenticated

# Pass any mapping of request headers
user = from_headers(request.headers)

if user.is_authenticated:
    print(user.name)       # "Jane Doe"
    print(user.email)      # "jane@example.com"
    print(user.object_id)  # "aaaa-bbbb-cccc"
    print(user.provider)   # "aad"
    print(user.roles)      # ["Reader", "Writer"]
```

### Quick boolean check

```python
from azure_easy_auth import is_authenticated

if not is_authenticated(request.headers):
    return "Unauthorized", 401
```

### Working with claims

All claims from the `X-MS-CLIENT-PRINCIPAL` token are available:

```python
user = from_headers(request.headers)

# Get the first value for a claim type
tenant = user.get_claim("tid")

# Get all values (for multi-value claims like roles or groups)
roles = user.get_claims("roles")
groups = user.get_claims("groups")
```

### Flask

```python
from flask import Flask, request, jsonify
from azure_easy_auth import from_headers

app = Flask(__name__)

@app.route("/me")
def me():
    user = from_headers(request.headers)
    if not user.is_authenticated:
        return "Unauthorized", 401
    return jsonify(name=user.name, email=user.email, roles=user.roles)
```

### FastAPI

Install with the FastAPI extra:

```bash
pip install "git+https://github.com/advisense/azure-easy-auth.git#egg=azure-easy-auth[fastapi]"
```

Then use the built-in dependency type aliases — no boilerplate required:

```python
from fastapi import FastAPI
from azure_easy_auth.fastapi import AuthenticatedUser, CurrentUser

app = FastAPI()

# Raises HTTP 401 automatically if not authenticated
@app.get("/me")
def me(user: AuthenticatedUser):
    return {"name": user.name, "email": user.email, "roles": user.roles}

# Works for both authenticated and anonymous users
@app.get("/public")
def public(user: CurrentUser):
    greeting = f"Hello, {user.name}" if user.is_authenticated else "Hello, stranger"
    return {"message": greeting}
```

| Type alias | Behaviour |
|---|---|
| `AuthenticatedUser` | Injects `EasyAuthUser`, raises `HTTP 401` if not authenticated |
| `CurrentUser` | Injects `EasyAuthUser`, never raises — check `.is_authenticated` yourself |

### Django

```python
from azure_easy_auth import from_headers

def my_view(request):
    user = from_headers(request.META)  # Django uses META for headers
    ...
```

> **Note:** Django stores headers in `request.META` with `HTTP_` prefixes and uppercased names (e.g. `HTTP_X_MS_CLIENT_PRINCIPAL_NAME`). `azure-easy-auth` handles the normalisation automatically.

## API Reference

### `from_headers(headers) -> EasyAuthUser`

Parses a headers mapping and returns an `EasyAuthUser`. Works with any `Mapping[str, str]` — header name casing is ignored.

### `is_authenticated(headers) -> bool`

Returns `True` if Easy Auth headers are present. Shorthand for `from_headers(headers).is_authenticated`.

### `EasyAuthUser`

| Attribute / Property | Type | Description |
|---|---|---|
| `is_authenticated` | `bool` | `True` when Easy Auth headers are present |
| `name` | `str \| None` | Display name (`X-MS-CLIENT-PRINCIPAL-NAME`) |
| `principal_id` | `str \| None` | Object/subject ID (`X-MS-CLIENT-PRINCIPAL-ID`) |
| `provider` | `str \| None` | Identity provider (`X-MS-CLIENT-PRINCIPAL-IDP`) |
| `email` | `str \| None` | `preferred_username` or email address claim |
| `object_id` | `str \| None` | Azure AD object ID (`oid` claim) |
| `roles` | `list[str]` | App role assignments |
| `groups` | `list[str]` | Group membership claims |
| `claims` | `list[Claim]` | All decoded claims |
| `get_claim(typ)` | `str \| None` | First value for a claim type |
| `get_claims(typ)` | `list[str]` | All values for a claim type |

### `Claim`

A simple frozen dataclass with two fields: `typ` (claim type) and `val` (claim value).

## Local development

```bash
git clone https://github.com/advisense/azure-easy-auth
cd azure-easy-auth
uv sync --extra dev
pytest
```
