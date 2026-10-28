"""Public-API contract tests for :mod:`storage`.

These guard the top-level import surface. If a symbol disappears from
``storage.__all__``, a downstream caller breaks. The test shape mirrors
``packages/core/tests/test_public_api.py`` and
``packages/llm/tests/test_public_api.py`` so the three suites share
conventions.

As of Phase 5 Wave 3, storage is a pure-engine package (mem0 + pgvector).
Scope-specific record schemas (Lead, Proposal, Contractor, Message) live
in ``apps/scope/product/backend/records/`` and are tested there.
"""
from __future__ import annotations

import importlib

import storage


EXPECTED_TOP_LEVEL = {
    # types (4 — engines only)
    "Memory",
    "MigrationResult",
    "Embedding",
    "EmbeddingMatch",
    # semantic (7)
    "remember",
    "recall",
    "forget",
    "migrate_user",
    "format_memories_for_prompt",
    "get_user_context",
    "is_mem0_configured",
    # embeddings (7 — 5 fns + 2 constants)
    "index_text",
    "index_batch",
    "search_similar",
    "delete_chunk",
    "prune_embeddings",
    "EMBED_DIM",
    "EMBED_MODEL",
}


class TestPackagePublicSurface:
    def test_all_list_matches_expected(self) -> None:
        assert set(storage.__all__) == EXPECTED_TOP_LEVEL

    def test_no_duplicates_in_all(self) -> None:
        assert len(storage.__all__) == len(set(storage.__all__))

    def test_every_symbol_in_all_is_reachable(self) -> None:
        missing = [name for name in storage.__all__ if not hasattr(storage, name)]
        assert missing == []

    def test_symbol_count_matches_engine_shape(self) -> None:
        """After Wave 3's scope-schema extraction, storage is pure engines
        (4 types + 7 semantic fns + 7 embedding exports = 18 symbols)."""

        assert len(storage.__all__) == 18


class TestSubmoduleAccess:
    """Advanced callers can still reach into submodules."""

    def test_semantic_module_importable(self) -> None:
        mod = importlib.import_module("storage.semantic")
        assert callable(mod.remember)
        assert callable(mod.recall)
        assert callable(mod.migrate_user)

    def test_embeddings_module_importable(self) -> None:
        mod = importlib.import_module("storage.embeddings")
        assert callable(mod.index_text)
        assert callable(mod.search_similar)

    def test_types_module_importable(self) -> None:
        mod = importlib.import_module("storage.types")
        assert hasattr(mod, "Memory")
        assert hasattr(mod, "Embedding")

    def test_scope_schemas_not_in_storage(self) -> None:
        """Wave 3 invariant: scope-specific record shapes must not leak
        back into the shared storage package."""

        for scope_symbol in ("Lead", "Proposal", "Contractor", "Message",
                             "save_lead", "store_proposal",
                             "get_or_create_contractor", "add_message"):
            assert not hasattr(storage, scope_symbol), (
                f"{scope_symbol} belongs in apps/scope/product/backend/records/, "
                f"not in packages/storage"
            )

    def test_scope_submodules_not_in_storage(self) -> None:
        """Wave 3 invariant: storage no longer ships leads/proposals/
        dossier/conversations submodules."""

        for scope_submodule in ("leads", "proposals", "dossier", "conversations"):
            try:
                importlib.import_module(f"storage.{scope_submodule}")
            except ImportError:
                continue
            raise AssertionError(
                f"storage.{scope_submodule} is still importable — it should "
                "have moved to apps/scope/product/backend/records/"
            )

    def test_private_state_not_re_exported(self) -> None:
        """Module-private state (``_mem0_client``) must not leak to the
        top-level namespace."""

        assert not hasattr(storage, "_mem0_client")
        assert not hasattr(storage, "_mem0_init_failed")
