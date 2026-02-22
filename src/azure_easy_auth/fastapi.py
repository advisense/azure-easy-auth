"""FastAPI integration for azure-easy-auth.

Provides two ready-made dependency type aliases:

- :data:`CurrentUser` — injects an ``EasyAuthUser``, authenticated or not.
- :data:`AuthenticatedUser` — injects an ``EasyAuthUser`` and raises
  ``HTTP 401`` when the Easy Auth headers are absent.

Usage::

    from fastapi import FastAPI
    from azure_easy_auth.fastapi import AuthenticatedUser, CurrentUser

    app = FastAPI()

    @app.get("/me")
    def me(user: AuthenticatedUser):
        return {"name": user.name, "email": user.email, "roles": user.roles}

    @app.get("/public")
    def public(user: CurrentUser):
        greeting = f"Hello, {user.name}" if user.is_authenticated else "Hello, stranger"
        return {"message": greeting}
"""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request

from ._auth import EasyAuthUser, from_headers


def _get_user(request: Request) -> EasyAuthUser:
    return from_headers(request.headers)


def _require_user(user: Annotated[EasyAuthUser, Depends(_get_user)]) -> EasyAuthUser:
    if not user.is_authenticated:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


CurrentUser = Annotated[EasyAuthUser, Depends(_get_user)]
"""Dependency that resolves to an :class:`~azure_easy_auth.EasyAuthUser`.

The user may or may not be authenticated — check :attr:`~azure_easy_auth.EasyAuthUser.is_authenticated`
if your route serves both authenticated and anonymous users.
"""

AuthenticatedUser = Annotated[EasyAuthUser, Depends(_require_user)]
"""Dependency that resolves to an authenticated :class:`~azure_easy_auth.EasyAuthUser`.

Raises ``HTTP 401`` automatically when the Easy Auth headers are absent.
"""
