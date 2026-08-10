"""Behavior checks for the repo-local plain-writing skill linter."""

from __future__ import annotations

import json
import runpy
import subprocess
import sys
from pathlib import Path
from typing import Any

SCRIPT = Path(".agents/skills/plain-writing/scripts/check_plain_writing.py")
SKILL = Path(".agents/skills/plain-writing/SKILL.md")
VOICE_CORPUS = Path(".agents/skills/plain-writing/references/voice-corpus.md")
PROJECT_RULES = Path("AGENTS.md")


def _analyze(text: str, *, format_name: str | None = None) -> dict[str, Any]:
    namespace = runpy.run_path(str(SCRIPT), run_name="plain_writing_linter")
    return namespace["analyze_text"](text, format_name=format_name)


def _codes(report: dict[str, Any]) -> set[str]:
    return {finding["code"] for finding in report["findings"]}


def test_skill_is_complete_and_compatibility_entry_exists() -> None:
    content = SKILL.read_text(encoding="utf-8")

    assert "[TODO" not in content
    assert "references/voice-corpus.md" in content
    assert "check_plain_writing.py" in content
    assert Path(".claude/skills/plain-writing/SKILL.md").is_file()


def test_skill_encodes_lessons_from_user_edits() -> None:
    skill = SKILL.read_text(encoding="utf-8")
    corpus = VOICE_CORPUS.read_text(encoding="utf-8")
    project_rules = PROJECT_RULES.read_text(encoding="utf-8")
    normalized_skill = " ".join(skill.split())

    assert "Latest user revision outranks" in skill
    assert "Do not restore a true detail merely for completeness" in skill
    assert "Do not force a design choice, status note, risk, or closing lesson" in normalized_skill
    assert "Keep familiar or incidental shorthand" in skill
    assert "Content selection matters more than sentence polish" in corpus
    assert "Do not expand an acronym when the expansion does not help the reader" in project_rules


def test_short_concrete_copy_passes_without_findings() -> None:
    report = _analyze(
        "I built this because my broker showed a return without explaining the math. "
        "It now matches every deposit to the day the money moved."
    )

    assert report["word_count"] == 24
    assert report["findings"] == []


def test_flags_machine_tic_long_sentence_and_repeated_intensifier() -> None:
    report = _analyze(
        "Let's dive in. This highly flexible system uses a highly differentiated architecture "
        "to create a massive structural advantage for operators who need to reconcile many "
        "sources, review every exception, produce a decision, and explain the result before "
        "the reporting deadline arrives."
    )

    assert {"machine_tic", "long_sentence", "repeated_intensifier"} <= _codes(report)


def test_smart_apostrophe_machine_tic_is_flagged() -> None:
    report = _analyze("It\u2019s worth noting that the result changed.")

    assert "machine_tic" in _codes(report)


def test_format_budget_is_enforced() -> None:
    report = _analyze("word " * 181, format_name="project-card")

    assert "word_budget" in _codes(report)
    assert report["word_budget"] == 180


def test_multi_project_page_has_a_tighter_page_budget() -> None:
    report = _analyze("word " * 351, format_name="project-page")

    assert "word_budget" in _codes(report)
    assert report["word_budget"] == 350


def test_competitive_landscape_is_not_forbidden_by_itself() -> None:
    report = _analyze("I am trying to understand the AI wearable competitive landscape.")

    assert "machine_tic" not in _codes(report)


def test_short_markdown_list_items_are_not_one_long_paragraph() -> None:
    report = _analyze(
        "\n".join(f"- Item {number} has a short explanation." for number in range(20))
    )

    assert "long_paragraph" not in _codes(report)


def test_cli_reads_stdin_and_returns_json() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--json", "-"],
        input="The point comes first. The proof follows.",
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["word_count"] == 7
    assert payload["findings"] == []
