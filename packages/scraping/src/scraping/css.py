"""scraping.css — canonical CSS parser for the monorepo.

Backed by tinycss2 (CSS Syntax Module Level 3 tokenizer; tolerant, preserves
positions). Exposes two functions:

- iter_css_refs(text) -> list[CssRef]
    Every @import, url(...) and @font-face src: url(...) in a stylesheet,
    with 1-indexed line numbers.

CssRef.kind ∈ {"import", "url", "font"}.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import tinycss2


__all__ = ["CssRef", "iter_css_refs"]


CssRefKind = Literal["import", "url", "font"]


@dataclass(frozen=True)
class CssRef:
    kind: CssRefKind
    url: str
    line: int   # 1-indexed
    col: int    # 1-indexed


def _url_from_function(fn: tinycss2.ast.FunctionBlock) -> str | None:
    """Extract the URL from a `url(...)` FunctionBlock; returns None if dynamic/empty."""
    for tok in fn.arguments:
        t = tok.type
        if t == "string":
            return tok.value
        if t == "ident":
            return tok.value
        if t == "url":  # bare url() token with no quotes
            return tok.value  # tinycss2 exposes .value for url tokens
    return None


def _url_from_url_token(tok) -> str | None:
    # tinycss2 URLToken carries .value
    v = getattr(tok, "value", None)
    if isinstance(v, str) and v:
        return v
    return None


def _walk_tokens(tokens, line_base: int = 0):
    """Yield (token, absolute_line, absolute_col). tinycss2 reports 1-indexed
    source_line/source_column on top-level tokens; for nested FunctionBlock
    children, the positions are relative to the function itself — we flatten."""
    for tok in tokens:
        line = getattr(tok, "source_line", None)
        col = getattr(tok, "source_column", None)
        if line is None:
            line = line_base
        yield tok, int(line or 0), int(col or 0)


def iter_css_refs(text: str) -> list[CssRef]:
    """Return every external reference in a stylesheet text."""
    out: list[CssRef] = []
    rules = tinycss2.parse_stylesheet(
        text, skip_comments=True, skip_whitespace=True,
    )
    for rule in rules:
        if rule.type == "at-rule":
            name = (rule.at_keyword or "").lower()
            # @import <url> <media>;    or   @import "url" ...;
            if name == "import":
                for tok, line, _col in _walk_tokens(rule.prelude or []):
                    if tok.type == "url":
                        u = _url_from_url_token(tok)
                        if u:
                            out.append(CssRef("import", u, line, _col))
                            break
                    elif tok.type == "string":
                        out.append(CssRef("import", tok.value, line, _col))
                        break
                    elif tok.type == "function" and (tok.lower_name == "url"):
                        u = _url_from_function(tok)
                        if u:
                            out.append(CssRef("import", u, line, _col))
                            break
            elif name == "font-face":
                # Look inside the block for src: url(...)
                block = rule.content or []
                for tok, line, col in _walk_tokens(block):
                    if tok.type == "url":
                        u = _url_from_url_token(tok)
                        if u:
                            out.append(CssRef("font", u, line, col))
                    elif tok.type == "function" and tok.lower_name == "url":
                        u = _url_from_function(tok)
                        if u:
                            out.append(CssRef("font", u, line, col))
            else:
                # other at-rules (e.g. @namespace url(...), @supports) — still worth capturing
                for tok, line, col in _walk_tokens(rule.prelude or []):
                    if tok.type == "url":
                        u = _url_from_url_token(tok)
                        if u:
                            out.append(CssRef("url", u, line, col))
                    elif tok.type == "function" and tok.lower_name == "url":
                        u = _url_from_function(tok)
                        if u:
                            out.append(CssRef("url", u, line, col))
                # and inside its body (if it has one)
                for tok, line, col in _walk_tokens(rule.content or []):
                    if tok.type == "url":
                        u = _url_from_url_token(tok)
                        if u:
                            out.append(CssRef("url", u, line, col))
                    elif tok.type == "function" and tok.lower_name == "url":
                        u = _url_from_function(tok)
                        if u:
                            out.append(CssRef("url", u, line, col))
        elif rule.type == "qualified-rule":
            # regular selector { decl; decl; } — scan declarations for url(...)
            for tok, line, col in _walk_tokens(rule.content or []):
                if tok.type == "url":
                    u = _url_from_url_token(tok)
                    if u:
                        out.append(CssRef("url", u, line, col))
                elif tok.type == "function" and tok.lower_name == "url":
                    u = _url_from_function(tok)
                    if u:
                        out.append(CssRef("url", u, line, col))
    return out
