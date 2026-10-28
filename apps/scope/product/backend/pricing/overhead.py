"""Autónomo overhead model — contractor-facing rate explainer.

Loads ``autonomo_overhead_model.json`` (bundled) once. Used in
contractor-facing explanations of why their hourly rate is what it is:
base wage + social security + materials margin + equipment amortization
+ risk premium.

Public entry:

- :func:`overhead_model` — returns the full dict. Cached after first read.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from . import config
from .errors import IndexNotFoundError

logger = logging.getLogger(__name__)

__all__ = ["overhead_model"]


_model_cache: Optional[Dict[str, Any]] = None


def _clear_cache() -> None:
    global _model_cache
    _model_cache = None


def overhead_model() -> Dict[str, Any]:
    """Return the autónomo overhead model.

    Raises :class:`IndexNotFoundError` if the bundled JSON is unreadable.
    Empty dict if the file is missing outright (graceful for callers that
    just want to render a placeholder).
    """

    global _model_cache
    if _model_cache is not None:
        return _model_cache

    path = config.overhead_model_path()
    if path is None or not path.exists():
        logger.warning("autonomo_overhead_model.json not found")
        _model_cache = {}
        return _model_cache

    try:
        with path.open(encoding="utf-8") as f:
            _model_cache = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        raise IndexNotFoundError(
            f"Could not load overhead model from {path!s}: {exc}"
        ) from exc

    return _model_cache
