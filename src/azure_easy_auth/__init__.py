"""azure-easy-auth — helpers for Azure App Service Easy Auth."""

from ._auth import Claim, EasyAuthUser, from_headers, is_authenticated

__all__ = ["Claim", "EasyAuthUser", "from_headers", "is_authenticated"]
