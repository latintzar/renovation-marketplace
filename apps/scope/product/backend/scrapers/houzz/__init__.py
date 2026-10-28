"""scrapers.houzz — Houzz directory adapter (scope scrapers).

robots-policy: **respect**. Houzz is a public directory with a
genuine robots.txt. Our :func:`search` consults it and returns
empty results on disallow rather than bypassing.

Session semantics: none (public directory).

Wave-9 scope: public surface declared, implementation scaffolded.
Audit Smell H reversed here — ``workflows.contractor_discovery``
imports from this module rather than owning its own search.
"""
from __future__ import annotations

from .search import build_query, search

__all__ = ["search", "build_query"]
