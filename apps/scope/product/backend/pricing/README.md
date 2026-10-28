# `pricing` — scope-app price intelligence

Every euro number that the scope app produces: **quotes**, **cost estimates**, **market lookups**, **product catalog**, **IVA math**, **markup rules**. Lives at `apps/scope/product/backend/pricing/` (demoted from `packages/pricing/` in Phase 5 Wave 4 — see below).

## Why it's not a shared package

Everything inside is Spanish-construction-market policy, not reusable capability:

| Concern | What's bundled / hardcoded |
|---|---|
| CYPE database | 9 MB SQLite FTS5 index of 2,151 Spanish construction prices (`data/cype_prices.db`). |
| INE drift | 120-month Spanish construction cost-of-inputs series (`data/ine_material_index.json`). |
| Autónomo overhead | Spanish self-employed tax + social-security model (`data/autonomo_overhead_model.json`). |
| Residential recipes | Spanish bathroom/kitchen/renovation templates (`data/residential_recipes.json`). |
| Markup rules | Spanish chapter-level margin defaults (`DEFAULT_MARKUP_BY_CHAPTER`). |
| IVA rates | `DEFAULT_IVA_RATE = 0.10` (residential renovation), plus `IVA_RATES` table. |
| Regional multipliers | Spanish provinces (`REGIONAL_MULTIPLIERS`). |
| Data sources | Habitissimo + CronoShare scrapers, Leroy Merlin product DB. |

If the scope app were deleted tomorrow, nothing of this is useful to any other Leo product. That's the test — capabilities stay in `packages/`, scope-policy lives here.

The one thing that *is* a generic capability — the FTS5 + BM25 search engine — stayed in `packages/fulltext/` (via `DomainIndex`), and `pricing.cype_index` imports it from there.

## Two bright-line entry points

```python
from pricing import compute_quote, estimate_cost

quote = compute_quote(draft)             # pure math, no I/O, golden-vector tested
est   = estimate_cost(query="bathroom")  # multi-layer: historical → recipe → CYPE → market
```

Everything else is either a building block these two call internally or a narrow helper. See `__init__.py` for the full ~40-symbol public surface.

## Canonical imports

```python
# Headline APIs
from pricing import compute_quote, estimate_cost, Estimate, Quote, QuoteDraft

# Building blocks (when the 2 entry points aren't enough)
from pricing import (
    search_cype, lookup_market, lookup_product, search_historical,
    markup_for_chapter, find_recipe, compute_ine_material_drift,
    apply_modifiers, regional_multiplier, overhead_model,
)

# Constants
from pricing import (
    DEFAULT_IVA_RATE, IVA_RATES, DEFAULT_MARKUP_BY_CHAPTER,
    REGIONAL_MULTIPLIERS, CYPE_TO_INE_CATEGORY,
)

# Config (test setup, path overrides)
from pricing import configure, close_connections
```

The `from pricing import ...` spelling continues to work because `apps/scope/product/backend/` is on `PYTHONPATH` for the scope backend — the import system finds this folder automatically.

## Submodule layout

```
apps/scope/product/backend/pricing/
  __init__.py              # curated public API (48 symbols)
  types.py                 # dataclasses: Quote, QuoteDraft, Line, Estimate, Recipe, CypeItem, ...
  quote.py                 # compute_quote, compute_line — deterministic arithmetic
  estimate.py              # estimate_cost — multi-layer orchestrator
  cype_index.py            # FTS5 query over cype_prices.db (uses fulltext.tokenize)
  historical.py            # Supabase-backed historical job lookup
  price_lookup.py          # Habitissimo + CronoShare market prices
  product_lookup.py        # Leroy Merlin product catalog (~199K rows)
  recipes.py               # residential renovation recipe templates
  ine_drift.py             # INE 120-month material cost drift
  ine_categories.py        # CYPE chapter → INE category mapping
  markup.py                # chapter-level markup rules + fallback
  materials.py             # live materials price lookup
  modifiers.py             # access_difficult / peak_season / urgent / etc. modifiers
  overhead.py              # autónomo overhead model
  stopwords.py             # Spanish-specific stopwords for tokenization
  config.py                # path resolution + test reset hooks
  constants.py             # IVA rates, regional multipliers, CYPE↔INE mapping
  errors.py                # PricingError hierarchy
  data/                    # bundled artifacts (9 MB CYPE DB + 3 JSON files)
```

## Testing

```bash
cd /root/leo
PYTHONPATH="apps/scope/product/backend:packages/core/src:packages/fulltext/src:packages/llm/src:packages/storage/src" \
    /root/leo/apps/scope/product/backend/venv/bin/python3 \
    -m pytest apps/scope/product/backend/tests/pricing/
```

Scope backend already wires this `PYTHONPATH` via its `venv`, so from inside the backend:

```bash
cd /root/leo/apps/scope/product/backend
./venv/bin/python3 -m pytest tests/pricing/
```

## Changelog

- **Phase 5 Wave 4**: demoted from `packages/pricing/` to `apps/scope/product/backend/pricing/`. Rationale: every number in here is Spanish-construction-market policy, not reusable capability. The `packages/pricing` wrapper was deleted; `from pricing import ...` continues to work because scope backend is on `PYTHONPATH`. One existing caller — the stranded `packages/messaging/src/messaging/leo_agent/tools/pricing.py` — needed no changes because it was already using `from pricing...` imports. That tool file itself will move to `apps/scope/product/backend/messaging/` in Wave 6.
