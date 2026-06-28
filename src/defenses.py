"""Defense layers applied to retrieved chunks or the final prompt.

WEEK 0 STATUS: stubs. Each defense is identity (returns input unchanged) so the
matrix runner can already loop over all of them. Real implementations land in
week 2-3.
"""
from __future__ import annotations
from typing import Callable

# Each defense: (chunks: list[str], question: str) -> (chunks: list[str], system_prompt_suffix: str)
DefenseFn = Callable[[list[str], str], tuple[list[str], str]]


def _none(chunks, question):
    return chunks, ""


def _input_sanitize(chunks, question):
    # TODO week 2: strip imperative sentences via regex
    return chunks, ""


def _delimiter_fencing(chunks, question):
    # TODO week 2: wrap each chunk in <context>...</context> with data-only hint
    return chunks, ""


def _provenance_tag(chunks, question):
    # TODO week 2: prefix [source: filename] (needs metadata wiring first)
    return chunks, ""


def _instruction_defense(chunks, question):
    # TODO week 2: append guard to system prompt
    return chunks, ""


def _top_k_rerank(chunks, question):
    # TODO week 3: cross-encoder rerank, drop low-confidence
    return chunks, ""


def _stack(chunks, question):
    # TODO week 3: apply all of the above in sequence
    return chunks, ""


DEFENSES: dict[str, DefenseFn] = {
    "none": _none,
    "input-sanitize": _input_sanitize,
    "delimiter-fencing": _delimiter_fencing,
    "provenance-tag": _provenance_tag,
    "instruction-defense": _instruction_defense,
    "top-k-rerank": _top_k_rerank,
    "stack": _stack,
}
