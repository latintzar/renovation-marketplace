"""Package-specific stopword sets passed to ``fulltext.tokenize``.

The Spanish stopword base lives in ``fulltext.stopwords``. These are the
extra filler tokens that show up in CYPE and pricing corpora (CYPE
item descriptions are verbose: "*colocado con mortero de cemento...*")
and should not influence FTS ranking.

``fulltext.tokenize(text, extra_stopwords=CYPE_FILLERS, ...)`` merges
these with the base Spanish set.
"""

from __future__ import annotations

from typing import Final, FrozenSet


CYPE_FILLERS: Final[FrozenSet[str]] = frozenset(
    "colocado colocada instalado instalada formado formada incluido incluida "
    "mediante segun incluso recibido recibida suministrado suministrada "
    "realizado realizada montado montada"
    .split()
)


PRICE_FILLERS: Final[FrozenSet[str]] = frozenset(
    "precio precios coste costes gasto gastos presupuesto presupuestos "
    "tarifa tarifas importe importes"
    .split()
)


__all__ = ["CYPE_FILLERS", "PRICE_FILLERS"]
