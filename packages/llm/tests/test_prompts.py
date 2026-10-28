"""Tests for :mod:`llm.prompts`."""

from __future__ import annotations

from pathlib import Path

import pytest
from jinja2 import UndefinedError

from llm.errors import PromptNotFound
from llm.prompts import (
    PROMPTS,
    Prompt,
    PromptRegistry,
    get_prompt,
    list_prompts,
    load_prompt,
    render_prompt,
)


class TestPromptDataclass:
    def test_construct_minimal(self):
        p = Prompt(id="x", version=1, body="hello")
        assert p.id == "x"
        assert p.version == 1
        assert p.render() == "hello"

    def test_render_with_variables(self):
        p = Prompt(id="x", version=1, body="Hello {{ name }}!")
        assert p.render({"name": "Peter"}) == "Hello Peter!"

    def test_render_strict_undefined(self):
        p = Prompt(id="x", version=1, body="Hello {{ missing }}!")
        with pytest.raises(UndefinedError):
            p.render({})


class TestLoadPrompt:
    def test_load_valid(self, tmp_path: Path):
        f = tmp_path / "t.md"
        f.write_text(
            "---\nid: my_test\nversion: 1\nmodel: anthropic/claude-haiku-4.5\n---\nHello {{ who }}!\n",
            encoding="utf-8",
        )
        p = load_prompt(f)
        assert p.id == "my_test"
        assert p.version == 1
        assert p.model == "anthropic/claude-haiku-4.5"
        assert p.render({"who": "world"}).strip() == "Hello world!"

    def test_load_missing_file_raises(self, tmp_path: Path):
        with pytest.raises(PromptNotFound):
            load_prompt(tmp_path / "nope.md")

    def test_load_missing_id_raises(self, tmp_path: Path):
        f = tmp_path / "t.md"
        f.write_text("---\nversion: 1\n---\nbody\n", encoding="utf-8")
        with pytest.raises(PromptNotFound):
            load_prompt(f)

    def test_load_missing_version_raises(self, tmp_path: Path):
        f = tmp_path / "t.md"
        f.write_text("---\nid: x\n---\nbody\n", encoding="utf-8")
        with pytest.raises(PromptNotFound):
            load_prompt(f)


class TestPromptRegistry:
    def test_register_and_get(self):
        reg = PromptRegistry()
        p = Prompt(id="greeting", version=1, body="Hello {{ name }}!")
        reg.register(p)
        assert reg.get("greeting") is p

    def test_unknown_raises(self):
        reg = PromptRegistry()
        # Use a root that doesn't exist so loading is a no-op.
        reg = PromptRegistry(root=Path("/does/not/exist"))
        with pytest.raises(PromptNotFound):
            reg.get("unknown")

    def test_language_filter(self):
        reg = PromptRegistry(root=Path("/does/not/exist"))
        reg.register(Prompt(id="x", version=1, body="en", language="en"))
        reg.register(Prompt(id="x", version=1, body="es", language="es"))
        assert reg.get("x", language="en").body.strip() == "en"
        assert reg.get("x", language="es").body.strip() == "es"

    def test_version_highest_default(self):
        reg = PromptRegistry(root=Path("/does/not/exist"))
        reg.register(Prompt(id="x", version=1, body="v1"))
        reg.register(Prompt(id="x", version=2, body="v2"))
        assert reg.get("x").body.strip() == "v2"
        assert reg.get("x", version=1).body.strip() == "v1"

    def test_list_prompts(self):
        reg = PromptRegistry(root=Path("/does/not/exist"))
        reg.register(Prompt(id="a", version=1, body="A"))
        reg.register(Prompt(id="b", version=1, body="B"))
        assert reg.list() == ["a", "b"]


class TestBuiltInTemplates:
    """Exercises the six migrated templates shipped under ``templates/``."""

    def test_concern_classifier_es(self):
        out = render_prompt(
            "concern_classifier",
            variables={"message": "tengo un problema"},
            language="es",
        )
        assert "tengo un problema" in out
        assert "issue" in out

    def test_concern_classifier_en(self):
        out = render_prompt(
            "concern_classifier",
            variables={"message": "I have a problem"},
            language="en",
        )
        assert "I have a problem" in out

    def test_parse_media_structure_no_variables(self):
        out = render_prompt("parse_media_structure")
        assert "Markdown" in out

    def test_variation_extraction_es(self):
        out = render_prompt(
            "variation_extraction",
            variables={"conversation": "Hello Mrs."},
            language="es",
        )
        assert "Hello Mrs." in out

    def test_i18n_translate(self):
        out = render_prompt(
            "i18n_translate",
            variables={
                "target_language": "Spanish",
                "source": "Hello",
                "context": "greeting",
            },
        )
        assert "Spanish" in out
        assert "Hello" in out

    def test_profile_import_extract(self):
        out = render_prompt(
            "profile_import_extract",
            variables={"raw_content": "<html>Trusted</html>"},
        )
        assert "<html>Trusted</html>" in out

    def test_sales_tracker_enrich(self):
        out = render_prompt(
            "sales_tracker_enrich",
            variables={"lead_json": '{"name":"John"}'},
        )
        assert "John" in out

    def test_get_prompt_returns_raw(self):
        p = get_prompt("concern_classifier", language="es")
        assert isinstance(p, Prompt)
        assert p.id == "concern_classifier"
        assert p.language == "es"

    def test_list_prompts_contains_all_six(self):
        names = list_prompts()
        assert "concern_classifier" in names
        assert "variation_extraction" in names
        assert "parse_media_structure" in names
        assert "i18n_translate" in names
        assert "profile_import_extract" in names
        assert "sales_tracker_enrich" in names
