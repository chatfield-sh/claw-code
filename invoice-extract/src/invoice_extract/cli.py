"""Command line entry point."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from . import workbook
from .config import Config, ConfigError, GLConfig
from .documents import UnsupportedDocument, discover
from .extract import Extractor
from .ledger import Ledger
from .pipeline import RunReport, run

EXIT_OK = 0
EXIT_REVIEW = 1  # ran fine, but something needs a human before upload
EXIT_ERROR = 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="invoice-extract",
        description=(
            "Read vendor, invoice number, GL account and amount from scanned "
            "invoices and write the accounting upload sheet."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Exit codes: 0 = every invoice passed; 1 = some invoices need "
            "review; 2 = the run failed."
        ),
    )
    parser.add_argument(
        "paths",
        nargs="+",
        type=Path,
        help="scan files or directories of scans (PDF, PNG, JPG, GIF, WEBP)",
    )
    parser.add_argument(
        "-o",
        "--out",
        type=Path,
        default=Path("invoices.xlsx"),
        help="workbook to write (default: invoices.xlsx)",
    )
    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        help="path to config.yaml (see config/config.example.yaml)",
    )
    parser.add_argument(
        "-g",
        "--gl",
        type=Path,
        help="path to gl_accounts.yaml (see config/gl_accounts.example.yaml)",
    )
    parser.add_argument(
        "--ledger",
        type=Path,
        default=Path("submitted.sqlite"),
        help=(
            "duplicate-detection database (default: submitted.sqlite). "
            "Keep this file between runs — it is what catches an invoice that "
            "was already submitted."
        ),
    )
    parser.add_argument(
        "--no-ledger",
        action="store_true",
        help="disable cross-run duplicate detection entirely",
    )
    parser.add_argument(
        "--no-record",
        action="store_true",
        help="check the ledger but do not add this run's invoices to it",
    )
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help=(
            "skip the second, independent read. Halves the API cost and "
            "removes the main guard against a silent misread."
        ),
    )
    parser.add_argument(
        "--include-review",
        action="store_true",
        help=(
            "put held invoices on the main upload sheet as well as the "
            "exceptions sheet. Off by default so nothing unverified is uploaded."
        ),
    )
    parser.add_argument(
        "--no-recurse",
        action="store_true",
        help="do not descend into subdirectories",
    )
    parser.add_argument(
        "-j",
        "--jobs",
        type=int,
        default=4,
        help="how many scans to read concurrently (default: 4)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="list the scans that would be read, then stop",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="log each file as it is read",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s %(message)s",
    )

    try:
        config = Config.load(args.config)
        gl_config = GLConfig.load(args.gl)
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_ERROR

    if args.no_verify:
        config.verify = False

    try:
        paths = discover(args.paths, recursive=not args.no_recurse)
    except UnsupportedDocument as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_ERROR

    if not paths:
        print("error: no scannable files found", file=sys.stderr)
        return EXIT_ERROR

    if args.list:
        for path in paths:
            print(path)
        print(f"\n{len(paths)} file(s).")
        return EXIT_OK

    if args.jobs < 1:
        print("error: --jobs must be at least 1", file=sys.stderr)
        return EXIT_ERROR

    known_vendors = [rule.label for rule in gl_config.vendor_rules.values()]
    extractor = Extractor(config=config, known_vendors=known_vendors)

    ledger_path = None if args.no_ledger else args.ledger
    with Ledger(ledger_path) as ledger:
        print(f"Reading {len(paths)} scan(s) with {config.model}...", file=sys.stderr)
        report = run(
            paths=paths,
            config=config,
            gl_config=gl_config,
            ledger=ledger,
            extractor=extractor,
            jobs=args.jobs,
        )

        exported = report.results if args.include_review else report.auto
        recorded = 0
        if exported and not args.no_record:
            recorded = ledger.record(exported)

    workbook.write(
        args.out,
        report.results,
        config,
        include_review_in_main=args.include_review,
    )

    _print_report(report, args.out, extractor, recorded, ledger_path is not None)

    if report.failures or report.review:
        return EXIT_REVIEW
    return EXIT_OK


def _print_report(
    report: RunReport,
    out: Path,
    extractor: Extractor,
    recorded: int,
    ledger_on: bool,
) -> None:
    print(file=sys.stderr)
    print(f"Read {report.files_read} file(s).", file=sys.stderr)
    print(
        f"  {len(report.auto)} invoice(s) ready to upload -> "
        f"'Invoices' sheet in {out}",
        file=sys.stderr,
    )
    if report.review:
        print(
            f"  {len(report.review)} invoice(s) held for review -> "
            f"'Exceptions' sheet",
            file=sys.stderr,
        )
    if report.failures:
        print(f"  {len(report.failures)} file(s) could not be read:", file=sys.stderr)
        for failure in report.failures:
            print(f"      {failure.path.name}: {failure.reason}", file=sys.stderr)

    if report.review:
        print("\nHeld for review:", file=sys.stderr)
        for result in report.review:
            label = result.invoice_number or "(no invoice number)"
            vendor = result.vendor_name or "(no vendor)"
            print(f"  {result.source_file} — {vendor} {label}", file=sys.stderr)
            for finding in result.findings:
                if finding.severity == "blocker":
                    print(f"      {finding}", file=sys.stderr)

    if ledger_on and recorded:
        print(f"\nRecorded {recorded} invoice(s) for duplicate detection.", file=sys.stderr)
    if not ledger_on:
        print(
            "\nDuplicate detection was off — an invoice already submitted in an "
            "earlier run would not have been caught.",
            file=sys.stderr,
        )

    print(f"\n{extractor.usage.summary()}", file=sys.stderr)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
