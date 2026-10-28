"""Constants exposed at the top of the :mod:`pricing` public API.

These are importable as ``from pricing import MODIFIERS, REGIONAL_MULTIPLIERS,
IVA_RATES, DEFAULT_SERVICE_FEE_PERCENT, DEFAULT_IVA_RATE``. Each is a
``Final`` frozen mapping/number — read-only at the type level; runtime
immutability enforced by ``MappingProxyType`` where applicable.

Sources:

- Modifier values (1.20×, 1.15×, …) are the values that existed in
  ``leo_agent/price_engine.py::MODIFIERS`` — preserved verbatim.
- Regional multipliers are seeded from INE's regional cost-of-living
  index; see ``design.md`` D13.
- IVA rates mirror ``domain.constants.IVA_GENERAL`` /
  ``IVA_RESIDENTIAL_RENOVATION`` — re-exposed here for in-package
  readability.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Final, Mapping


MODIFIERS: Final[Mapping[str, float]] = MappingProxyType({
    "access_difficult":  1.20,
    "peak_season":       1.15,
    "occupied_property": 1.10,
    "urgent":            1.25,
    "heritage_building": 1.30,
    # NOTE: the legacy "rural" modifier was dropped (D13). Callers pass
    # ``city=`` to ``estimate_cost`` instead; regional resolution is
    # applied automatically via ``regional_multiplier``. The pricing
    # package accepts ``"rural"`` silently for back-compat (it maps to
    # 1.0 and emits a DeprecationWarning — see
    # ``pricing.modifiers.apply_modifiers``).
})


REGIONAL_MULTIPLIERS: Final[Mapping[str, float]] = MappingProxyType({
    # Seed values from INE regional cost-of-living indexes. Override via
    # ``pricing.configure(regional_multipliers={...})`` without a code
    # change.
    "madrid":       1.15,
    "barcelona":    1.12,
    "marbella":     1.20,
    "ibiza":        1.25,
    "bilbao":       1.08,
    "sansebastian": 1.10,
    "valencia":     1.00,
    "sevilla":      0.98,
    "granada":      0.95,
    "zaragoza":     0.97,
    "malaga":       1.05,
    "palma":        1.10,
    "lascoruna":    0.98,
    "vigo":         0.97,
    "oviedo":       0.98,
    "salamanca":    0.95,
    "alicante":     1.00,
    "murcia":       0.95,
    "toledo":       0.95,
    "santander":    1.02,
    "pamplona":     1.05,
    "vitoria":      1.03,
    "cordoba":      0.95,
    "valladolid":   0.95,
    # sentinels
    "_rural_default": 0.95,
    "_default":       1.00,
})


IVA_RATES: Final[Mapping[str, float]] = MappingProxyType({
    "general":                0.21,
    "residential-renovation": 0.10,
    "reduced":                0.10,
})


DEFAULT_SERVICE_FEE_PERCENT: Final[float] = 5.0
DEFAULT_IVA_RATE:            Final[float] = 0.10


CYPE_TO_INE_CATEGORY: Final[Mapping[str, str]] = MappingProxyType({
    "mt19":  "ceramica",
    "mt37":  "plasticos",
    "mt37b": "cobre",
    "mt07":  "acero",
    "mt26":  "aluminio",
    "mt22":  "madera",
    "mt09":  "ligantes",
    "mt10":  "cemento",
    "mt21":  "vidrio",
    "mt27":  "quimicos",
    "mt01":  "aridos",
    "mt34":  "luminarias",
    "mt35":  "electronicos",
})


KEYWORD_TO_INE_CATEGORY: Final[Mapping[str, str]] = MappingProxyType({
    "tile":        "ceramica",
    "tiling":      "ceramica",
    "ceramica":    "ceramica",
    "azulejo":     "ceramica",
    "pipe":        "plasticos",
    "tubo":        "plasticos",
    "fontaneria":  "plasticos",
    "copper":      "cobre",
    "cobre":       "cobre",
    "steel":       "acero",
    "acero":       "acero",
    "hierro":      "acero",
    "aluminium":   "aluminio",
    "aluminio":    "aluminio",
    "ventana":     "aluminio",
    "wood":        "madera",
    "madera":      "madera",
    "puerta":      "madera",
    "cement":      "cemento",
    "cemento":     "cemento",
    "mortar":      "ligantes",
    "glass":       "vidrio",
    "vidrio":      "vidrio",
    "paint":       "quimicos",
    "pintura":     "quimicos",
    "adhesivo":    "quimicos",
    "sand":        "aridos",
    "arena":       "aridos",
    "electric":    "electronicos",
    "electricidad": "electronicos",
    "cable":       "electronicos",
})


MATERIAL_FRACTION_DEFAULT: Final[float] = 0.50


__all__ = [
    "MODIFIERS",
    "REGIONAL_MULTIPLIERS",
    "IVA_RATES",
    "DEFAULT_SERVICE_FEE_PERCENT",
    "DEFAULT_IVA_RATE",
    "CYPE_TO_INE_CATEGORY",
    "KEYWORD_TO_INE_CATEGORY",
    "MATERIAL_FRACTION_DEFAULT",
]
