"""Vercel Python entrypoint. See [tool.vercel] in pyproject.toml."""

from backend.main import app

__all__ = ["app"]
