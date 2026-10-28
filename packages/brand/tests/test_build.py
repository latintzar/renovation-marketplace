"""Determinism + drift-guard tests for ``brand.build``.

Running the builder twice must produce byte-identical output (no ordering
wobble). The ``--check`` mode must exit 0 on a clean tree and nonzero when
a derived file drifts from ``tokens.py``.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from brand import build


def test_emitters_are_deterministic() -> None:
    for filename, emit in build.ARTIFACTS.items():
        a = emit()
        b = emit()
        assert a == b, f"{filename} emitter returned different output on consecutive calls"


def test_check_passes_on_clean_repo() -> None:
    rc = build.main(["--check"])
    assert rc == 0, "brand.build --check must pass on a clean repo"


def test_check_flags_drift() -> None:
    gen = build.GENERATED
    tokens_json = gen / "tokens.json"
    original = tokens_json.read_bytes()
    try:
        tokens_json.write_text(original.decode() + "\n# DRIFT MARKER\n")
        rc = build.main(["--check"])
        assert rc != 0, "brand.build --check must reject a drifted tokens.json"
    finally:
        tokens_json.write_bytes(original)


def test_module_is_runnable_as_script() -> None:
    src_root = Path(__file__).resolve().parents[1] / "src"
    res = subprocess.run(
        [sys.executable, "-m", "brand.build", "--check"],
        cwd=src_root,
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, (
        f"`python -m brand.build --check` must pass from src root; "
        f"stdout:\n{res.stdout}\nstderr:\n{res.stderr}"
    )


def test_themes_emit_into_vars_css() -> None:
    """Every theme in tokens.THEMES must produce a `[data-theme="<name>"]`
    block in vars.css, and every overridden colour key must appear there
    with its override value prefixed as a bare CSS custom property."""
    from brand import tokens as T

    body = build._emit_vars_css()
    for theme_name, groups in T.THEMES.items():
        selector = f'[data-theme="{theme_name}"]'
        assert selector in body, (
            f"vars.css missing [data-theme=\"{theme_name}\"] block"
        )
        for category, overrides in groups.items():
            if category == "colors":
                for key, value in overrides.items():
                    kebab = key.replace("_", "-")
                    expected = f"--{kebab}: {value};"
                    assert expected in body, (
                        f"vars.css theme \"{theme_name}\" missing {expected}"
                    )


def test_themes_emit_into_tokens_css() -> None:
    """Every theme in tokens.THEMES must produce a `[data-theme="<name>"]`
    block in tokens.css (Tailwind @theme consumers), using the
    `--color-<kebab>` / `--radius-<k>` / `--shadow-<kebab>` / `--font-<k>`
    prefixed names expected by Tailwind v4."""
    from brand import tokens as T

    body = build._emit_tokens_css()
    for theme_name, groups in T.THEMES.items():
        selector = f'[data-theme="{theme_name}"]'
        assert selector in body, (
            f"tokens.css missing [data-theme=\"{theme_name}\"] block"
        )
        for category, overrides in groups.items():
            if category == "colors":
                prefix = "--color-"
                for key, value in overrides.items():
                    kebab = key.replace("_", "-")
                    expected = f"{prefix}{kebab}: {value};"
                    assert expected in body, (
                        f"tokens.css theme \"{theme_name}\" missing {expected}"
                    )


def test_themes_exported_to_typescript() -> None:
    """BRAND_THEMES must show up as a typed const export in tokens.ts so
    JS/TS consumers (canvas shaders, Node scripts, email renderers) can
    inspect themes programmatically."""
    body = build._emit_tokens_ts()
    assert "export const BRAND_THEMES = {" in body
    assert "themes:     BRAND_THEMES," in body


def test_themes_exported_to_json() -> None:
    """tokens.json must carry a `themes` field that mirrors THEMES in
    camelCase keys (matching the rest of the JSON surface)."""
    import json as _json

    from brand import tokens as T

    payload = _json.loads(build._emit_tokens_json())
    assert "themes" in payload
    assert set(payload["themes"].keys()) == set(T.THEMES.keys())
