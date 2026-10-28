"""Public stopword pools, split by concern (D5).

Grammar-only. Domain-specific filler (``precio``, ``presupuesto``,
CYPE auxiliaries) belongs in the consuming package (``pricing.stopwords``).

Exposed as ``frozenset[str]`` for identity + immutability.
"""
from __future__ import annotations

__all__ = ["SPANISH_GENERAL", "ENGLISH_GENERAL"]

SPANISH_GENERAL: frozenset[str] = frozenset(
    (
        "de en el la los las un una unos unas y o a al del que es por con para"
        " se su sus no lo le les mas pero como ya muy este esta estos estas ese"
        " esa esos esas todo toda todos todas otro otra otros otras ser estar"
        " haber tener hacer poder decir ir ver dar saber querer llegar pasar"
        " deber poner venir seguir encontrar llamar volver pensar salir creer"
        " conocer cuanto cuanta cuantos cuantas cual cuales donde cuando"
        " entre sin hasta desde durante ante mediante segun contra tras"
    ).split()
)

ENGLISH_GENERAL: frozenset[str] = frozenset(
    (
        "the a an is are was were be been being have has had do does did"
        " will would shall should may might can could of to in for on with"
        " at by from as into through about up out if or and but not this"
        " that these those it its he she they them their we you your my"
        " how what when where who which why so very also just more"
        " than most some any each every all both few many no such too"
    ).split()
)
