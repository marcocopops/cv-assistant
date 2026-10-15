"""Evaluation harness: runs test cases against the RAG pipeline and reports results.

Usage: python -m evals.run path/to/cases.toml

The full report (every question and answer) is printed, and also written next to the
cases file as evals-report.txt, overwriting the previous one. The written report has no
timings, so two runs can be compared with a plain diff.

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
  expected_failure true for a known, accepted failure: reported but not blocking (optional)
"""
import argparse
import asyncio
import sys
import time
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

import httpx

from app import config, core

# The model must never reveal how it works internally.
LEAK_TERMS = ["excerpt", "extrait", "the text"]

# Not a .md file on purpose: every .md file in the knowledge directory is indexed as content.
REPORT_NAME = "evals-report.txt"


@dataclass
class Result:
    case_id: str
    question: str
    top_score: float = 0.0
    answer: str = ""
    seconds: float = 0.0
    failures: list[str] = field(default_factory=list)
    expected_failure: bool = False

    @property
    def passed(self) -> bool:
        return not self.failures

    @property
    def status(self) -> str:
        if self.expected_failure:
            return "XPASS" if self.passed else "XFAIL"
        return "PASS" if self.passed else "FAIL"


def contains(text: str, term: str) -> bool:
    return term.casefold() in text.casefold()


async def run_case(pool, client: httpx.AsyncClient, case: dict) -> Result:
    result = Result(case["id"], case["question"])
    result.expected_failure = case.get("expected_failure", False)
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


def format_result(r: Result, with_timing: bool) -> list[str]:
    """Render one case: status, full question, full answer, then any failures."""
    timing = f"  {r.seconds:.1f} s" if with_timing else ""
    lines = [
        f"{r.status}  {r.case_id}  score {r.top_score:.3f}{timing}",
        f"  Q: {r.question}",
        "  A: " + r.answer.replace("\n", "\n     "),
    ]
    lines += [f"  - {failure}" for failure in r.failures]
    return lines + [""]


def calibration_lines(cases: list[dict], results: list[Result]) -> list[str]:
    """Show which threshold values separate relevant questions from off-topic ones."""
    relevant = [r.top_score for c, r in zip(cases, results) if c.get("expect_source")]
    off_topic = [r.top_score for c, r in zip(cases, results) if c.get("gate") == "block"]
    if not relevant or not off_topic:
        return []
    highest_off, lowest_relevant = max(off_topic), min(relevant)
    lines = [f"Threshold: current {config.SCORE_THRESHOLD:.2f} | "
             f"highest off-topic {highest_off:.3f} | lowest relevant {lowest_relevant:.3f}"]
    if highest_off < lowest_relevant:
        lines.append(f"  Any value in ]{highest_off:.3f}, {lowest_relevant:.3f}] separates both groups "
                     f"(midpoint {(highest_off + lowest_relevant) / 2:.3f}).")
    else:
        lines.append("  The groups overlap: no threshold separates them. Improve the knowledge base.")
    return lines


async def main(path: str) -> int:
    cases_file = Path(path)
    with cases_file.open("rb") as f:
        cases = tomllib.load(f)["case"]

    results = []
    async with core.make_pool() as pool, httpx.AsyncClient(timeout=300) as client:
        for case in cases:  # sequential on purpose: the CPU runs one generation at a time
            r = await run_case(pool, client, case)
            print("\n".join(format_result(r, with_timing=True)), flush=True)
            results.append(r)

    passed = sum(r.passed for r in results)
    counts = {s: sum(r.status == s for r in results) for s in ("PASS", "FAIL", "XFAIL", "XPASS")}
    summary = [f"{counts['PASS']} passed, {counts['FAIL']} failed, "
               f"{counts['XFAIL']} known failures, {counts['XPASS']} known failures now passing",
               *calibration_lines(cases, results)]
    print("\n".join(summary))

    # Deterministic report (no timings), overwritten on each run so successive runs can be diffed.
    report = [line for r in results for line in format_result(r, with_timing=False)] + summary
    report_file = cases_file.with_name(REPORT_NAME)
    report_file.write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"\nReport written to {report_file}")

    # A known failure that now passes also blocks: its expected_failure flag must be removed.
    return 1 if counts["FAIL"] or counts["XPASS"] else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run RAG evaluation cases.")
    parser.add_argument("cases", help="path to a TOML file of evaluation cases")
    sys.exit(asyncio.run(main(parser.parse_args().cases)))