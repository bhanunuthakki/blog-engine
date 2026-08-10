"""Catch mechanical signs that public copy has drifted from Bhanu's plain style."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Literal, TypedDict

Severity = Literal["error", "warning"]


class Finding(TypedDict):
    code: str
    severity: Severity
    message: str


class Report(TypedDict):
    word_count: int
    sentence_count: int
    paragraph_count: int
    word_budget: int | None
    findings: list[Finding]


WORD_BUDGETS = {
    "homepage": 100,
    "project-card": 180,
    "project-page": 350,
    "book-theme": 120,
    "linkedin": 220,
    "investing-note": 450,
    "build-log": 800,
}

MACHINE_TICS = (
    r"\blet['\u2019]s dive in\b",
    r"\bit['\u2019]s worth noting that\b",
    r"\bin today['\u2019]s world\b",
    r"\bat the end of the day\b",
    r"\bin an era of\b",
    r"\ba testament to\b",
    r"\bit['\u2019]s not just\b.+\bit['\u2019]s\b",
    r"\bdelv(?:e|es|ed|ing)\b",
    r"\butiliz(?:e|es|ed|ing|ation)\b",
    r"\bthus\b",
    r"\btapestry\b",
)

INTENSIFIERS = (
    "massive",
    "highly",
    "exceptional",
    "exceptionally",
    "explosive",
    "robust",
    "seamless",
    "drastically",
    "fundamentally",
    "asymmetric",
)

_WORD_RE = re.compile(r"\b[\w]+(?:[\u2019'-][\w]+)*\b", flags=re.UNICODE)
_SENTENCE_RE = re.compile(r"[^.!?]+[.!?]+|[^.!?]+$", flags=re.MULTILINE)
_LIST_LINE_RE = re.compile(r"^\s*(?:[-*+]|\d+\.)\s+")


def _words(text: str) -> list[str]:
    return _WORD_RE.findall(text)


def _plain_sentences(text: str) -> list[str]:
    return [
        match.group(0).strip() for match in _SENTENCE_RE.finditer(text) if match.group(0).strip()
    ]


def _paragraphs(text: str) -> list[str]:
    paragraphs: list[str] = []
    for part in re.split(r"\n\s*\n", text):
        if not part.strip():
            continue
        lines = [line.strip() for line in part.splitlines() if line.strip()]
        if lines and all(_LIST_LINE_RE.match(line) for line in lines):
            paragraphs.extend(lines)
        else:
            paragraphs.append(part.strip())
    return paragraphs


def analyze_text(text: str, *, format_name: str | None = None) -> Report:
    """Return deterministic findings; voice still requires human judgment."""

    words = _words(text)
    sentences = _plain_sentences(text)
    paragraphs = _paragraphs(text)
    findings: list[Finding] = []
    budget = WORD_BUDGETS.get(format_name) if format_name else None

    if format_name and budget is None:
        allowed = ", ".join(sorted(WORD_BUDGETS))
        raise ValueError(f"Unknown format {format_name!r}. Choose one of: {allowed}")

    if budget is not None and len(words) > budget:
        findings.append(
            {
                "code": "word_budget",
                "severity": "error",
                "message": f"{len(words)} words exceeds the {budget}-word {format_name} ceiling.",
            }
        )

    lower = text.casefold()
    for pattern in MACHINE_TICS:
        match = re.search(pattern, lower, flags=re.DOTALL)
        if match:
            findings.append(
                {
                    "code": "machine_tic",
                    "severity": "error",
                    "message": f"Rewrite machine-like phrase: {match.group(0)!r}.",
                }
            )

    for sentence in sentences:
        count = len(_words(sentence))
        if count > 28:
            excerpt = " ".join(sentence.split())[:100]
            findings.append(
                {
                    "code": "long_sentence",
                    "severity": "warning",
                    "message": f"Split the {count}-word sentence starting: {excerpt!r}.",
                }
            )

    for paragraph in paragraphs:
        count = len(_words(paragraph))
        if count > 90:
            excerpt = " ".join(paragraph.split())[:100]
            findings.append(
                {
                    "code": "long_paragraph",
                    "severity": "warning",
                    "message": f"Break up the {count}-word paragraph starting: {excerpt!r}.",
                }
            )

    normalized_words = [word.casefold() for word in words]
    repeated = [word for word in INTENSIFIERS if normalized_words.count(word) > 1]
    if repeated:
        findings.append(
            {
                "code": "repeated_intensifier",
                "severity": "warning",
                "message": "Replace repeated intensifier(s) with facts: "
                + ", ".join(repeated)
                + ".",
            }
        )

    return {
        "word_count": len(words),
        "sentence_count": len(sentences),
        "paragraph_count": len(paragraphs),
        "word_budget": budget,
        "findings": findings,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", default="-", help="Markdown/text path, or - for stdin")
    parser.add_argument("--format", choices=sorted(WORD_BUDGETS), dest="format_name")
    parser.add_argument("--json", action="store_true", help="Print the complete report as JSON")
    parser.add_argument(
        "--fail-on",
        choices=("error", "warning", "never"),
        default="error",
        help="Choose which findings produce a non-zero exit code",
    )
    return parser


def _read(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8")


def _should_fail(findings: list[Finding], threshold: str) -> bool:
    if threshold == "never":
        return False
    if threshold == "warning":
        return bool(findings)
    return any(finding["severity"] == "error" for finding in findings)


def main() -> int:
    args = _parser().parse_args()
    report = analyze_text(_read(args.path), format_name=args.format_name)

    if args.json:
        print(json.dumps(report, indent=2))
    elif report["findings"]:
        for finding in report["findings"]:
            print(f"{finding['severity'].upper()} {finding['code']}: {finding['message']}")
    else:
        print(f"OK: {report['word_count']} words; no mechanical findings.")

    return 1 if _should_fail(report["findings"], args.fail_on) else 0


if __name__ == "__main__":
    raise SystemExit(main())
