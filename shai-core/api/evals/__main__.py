"""CLI: python -m evals — run the eval suite and report pass/fail."""

from __future__ import annotations

from .harness import run_evals


def main() -> int:
    results = run_evals()
    for r in results:
        print(f"[{'PASS' if r.passed else 'FAIL'}] {r.name}: {r.detail}")
    passed = sum(r.passed for r in results)
    print(f"\n{passed}/{len(results)} evals passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
