"""Fail when personal paths, durable document IDs, or private corpus files are tracked."""

from __future__ import annotations

from pathlib import Path

from blog_engine.public_boundary import violations

if __name__ == "__main__":
    bad = violations(Path(__file__).resolve().parents[1])
    if bad:
        raise SystemExit("Public-boundary violations: " + ", ".join(bad))
