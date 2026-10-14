"""Evaluation harness: runs test cases against the RAG pipeline and reports failures.

Usage: python -m evals.run path/to/cases.toml

Each case is a TOML table with:
  id               unique name
  question         the question to ask
  lang             expected answer language: "fr", "en" or "es" (optional)
  gate             "pass" (default): must reach the LLM
                   "block": must be filtered by the relevance threshold
                   "any": either outcome is acceptable
  expect_source    substring of a section heading that must be retrieved (optional)
  must_contain     terms that must all appear in the answer (optional)
  must_not_contain terms that must never appear in the answer (optional)
"""
import argparse
import asyncio
import sys
import time
import tomllib
from dataclasses import dataclass, field

import httpx

from app import config, core

# The model must never reveal how it works internally.
LEAK_TERMS = ["excerpt", "extrait", "the text"]


@dataclass
class Result:
    case_id: str
    top_score: float = 0.0
    answer: str = ""
    seconds: float = 0.0
    failures: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.failures


def contains(text: str, term: str) -> bool:
    return term.casefold() in text.casefold()


async def run_case(pool, client: httpx.AsyncClient, case: dict) -> Result:
    result = Result(case["id"])
    start = time.monotonic()

    # Raw retrieval, before the threshold, to record the best score for calibration.
    chunks = await core.retrieve(pool, client, case["question"])
    result.top_score = chunks[0].score if chunks else 0.0

    meta, done, parts = {}, {}, []
    async for event, data in core.answer(pool, client, case["question"], case.get("lang", "fr")):
        if event == "meta":
            meta = data
        elif event == "token":
            parts.append(data["text"])
        elif event == "done":
            done = data
    result.answer = "".join(parts)
    result.seconds = time.monotonic() - start

    fail = result.failures.append
    reached_llm = done.get("llm", False)
    gate = case.get("gate", "pass")

    if gate == "pass" and not reached_llm:
        fail(f"filtered by the threshold (score {result.top_score:.3f} < {config.SCORE_THRESHOLD})")
    if gate == "block" and reached_llm:
        fail(f"should have been filtered, but reached the LLM (score {result.top_score:.3f})")

    if (source := case.get("expect_source")) and not any(contains(s, source) for s in meta.get("sources", [])):
        fail(f"expected section '{source}' was not retrieved")

    for term in case.get("must_contain", []):
        if not contains(result.answer, term):
            fail(f"missing '{term}'")
    for term in case.get("must_not_contain", []):
        if contains(result.answer, term):
            fail(f"contains forbidden '{term}'")

    if reached_llm:
        for term in LEAK_TERMS:
            if contains(result.answer, term):
                fail(f"reveals internal context ('{term}')")

    if (lang := case.get("lang")) and (detected := core.detect_lang(result.answer, lang)) != lang:
        fail(f"answered in '{detected}' instead of '{lang}'")

    return result


def print_calibration(cases: list[dict], results: list[Result]) -> None:
    """Show which threshold values separate relevant questions from off-topic ones."""
    relevant = [r.top_score for c, r in zip(cases, results) if c.get("expect_source")]
    off_topic = [r.top_score for c, r in zip(cases, results) if c.get("gate") == "block"]
    if not relevant or not off_topic:
        return
    highest_off, lowest_relevant = max(off_topic), min(relevant)
    print(f"\nThreshold: current {config.SCORE_THRESHOLD:.2f} | "
          f"highest off-topic {highest_off:.3f} | lowest relevant {lowest_relevant:.3f}")
    if highest_off < lowest_relevant:
        print(f"  Any value in ]{highest_off:.3f}, {lowest_relevant:.3f}] separates both groups "
              f"(midpoint {(highest_off + lowest_relevant) / 2:.3f}).")
    else:
        print("  The groups overlap: no threshold separates them. Improve the knowledge base.")


async def main(path: str) -> int:
    with open(path, "rb") as f:
        cases = tomllib.load(f)["case"]

    results = []
    async with core.make_pool() as pool, httpx.AsyncClient(timeout=300) as client:
        for case in cases:  # sequential on purpose: the CPU runs one generation at a time
            r = await run_case(pool, client, case)
            print(f"{'PASS' if r.passed else 'FAIL'}  {r.case_id:<28} score {r.top_score:.3f}  {r.seconds:5.1f} s")
            for failure in r.failures:
                print(f"      - {failure}")
            if r.failures:
                print(f"      answer: {r.answer[:200]!r}")
            results.append(r)

    passed = sum(r.passed for r in results)
    print(f"\n{passed}/{len(results)} cases passed")
    print_calibration(cases, results)
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run RAG evaluation cases.")
    parser.add_argument("cases", help="path to a TOML file of evaluation cases")
    sys.exit(asyncio.run(main(parser.parse_args().cases)))