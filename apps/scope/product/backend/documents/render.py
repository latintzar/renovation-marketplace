"""Jinja2 template env + ``render_html`` + ``render_pdf`` (WeasyPrint).

Design refs:

- D4 — ``jinja2.PackageLoader("documents", "templates")`` +
  ``ChoiceLoader`` for an optional ``override_dir`` (per-region legal
  wording).
- D4 — ``autoescape=select_autoescape(["html", "html.j2"])`` +
  ``undefined=StrictUndefined`` + ``trim_blocks=False,
  lstrip_blocks=False`` (whitespace load-bearing for consent hash).
- D5 — WeasyPrint runs inside
  :func:`core.resilience.shared_thread_pool`; lazy import so the
  package imports on systems missing Pango/Cairo.
- D16 — library reads no env; ``base_url`` is a function arg.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import List, Optional, Union

from jinja2 import (
    ChoiceLoader,
    Environment,
    FileSystemLoader,
    PackageLoader,
    StrictUndefined,
    select_autoescape,
)

from core.resilience import shared_thread_pool

__all__ = ["render_html", "render_pdf", "PDFRenderError", "set_override_dir"]


class PDFRenderError(Exception):
    """Raised when WeasyPrint is unavailable or the render fails.

    The app-layer handler in ``apps/scope-backend/routes/documents.py``
    catches this and maps to HTTP 500 ``{"ok": false, "error": …,
    "code": "PDF_RENDER_FAILED"}``.
    """


_override_dir: Optional[Path] = None
_env: Optional[Environment] = None


def set_override_dir(path: Optional[Path]) -> None:
    """Register a per-app template override directory, or clear it.

    Files in ``path`` take precedence over the package-bundled
    templates. Used for per-region legal wording. Passing ``None``
    clears the override.

    Resets the cached environment so the next render picks up the
    change.
    """

    global _override_dir, _env
    _override_dir = path
    _env = None


def _build_env() -> Environment:
    loaders = []
    if _override_dir is not None and _override_dir.is_dir():
        loaders.append(FileSystemLoader(str(_override_dir)))
    loaders.append(PackageLoader("documents", "templates"))
    return Environment(
        loader=ChoiceLoader(loaders),
        autoescape=select_autoescape(["html", "html.j2"]),
        trim_blocks=False,
        lstrip_blocks=False,
        undefined=StrictUndefined,
    )


def _get_env() -> Environment:
    global _env
    if _env is None:
        _env = _build_env()
    return _env


def render_html(template_name: str, context: dict) -> str:
    """Render a Jinja2 template to HTML string.

    Raises :class:`jinja2.TemplateNotFound` if the template is missing
    and :class:`jinja2.UndefinedError` on any missing context variable.
    The latter is the structural fix for the ``scope_token`` silent
    blank bug.
    """

    tmpl = _get_env().get_template(template_name)
    return tmpl.render(**context)


async def render_pdf(
    html: str,
    *,
    base_url: Optional[str] = None,
    stylesheets: Optional[List[Union[str, Path]]] = None,
) -> bytes:
    """Convert HTML to PDF bytes via WeasyPrint.

    Sync-only WeasyPrint is offloaded to
    :func:`core.resilience.shared_thread_pool` so the event loop keeps
    serving. ``base_url`` is passed to WeasyPrint for relative-URL
    resolution; the library reads no env (the app shell is expected to
    pass ``APP_BASE_URL`` explicitly per D16).

    :raises PDFRenderError: WeasyPrint not installed or render failed.
    """

    loop = asyncio.get_running_loop()

    def _do_convert() -> bytes:
        try:
            from weasyprint import CSS, HTML
        except ImportError as exc:
            raise PDFRenderError("weasyprint not available") from exc
        try:
            extra = []
            if stylesheets:
                for s in stylesheets:
                    extra.append(CSS(filename=str(s)) if Path(str(s)).exists() else CSS(string=str(s)))
            return HTML(string=html, base_url=base_url).write_pdf(stylesheets=extra or None)
        except PDFRenderError:
            raise
        except Exception as exc:
            raise PDFRenderError(f"PDF render failed: {exc}") from exc

    return await loop.run_in_executor(shared_thread_pool(), _do_convert)
