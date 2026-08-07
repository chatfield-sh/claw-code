"""Run the whole thing: read scans, check them, code them, export.

Reading is IO-bound and runs in parallel; everything after it runs in file
order so that duplicate detection and the report are deterministic regardless
of which scan happened to finish first.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

from . import consensus, gl as gl_module, validate
from .config import Config, GLConfig
from .documents import UnsupportedDocument
from .extract import Extractor, ExtractionError
from .ledger import Ledger
from .models import ExtractedDocument, InvoiceResult, VerificationDocument

log = logging.getLogger(__name__)


@dataclass
class FileFailure:
    path: Path
    reason: str


@dataclass
class RunReport:
    results: list[InvoiceResult] = field(default_factory=list)
    failures: list[FileFailure] = field(default_factory=list)
    files_read: int = 0

    @property
    def auto(self) -> list[InvoiceResult]:
        return [r for r in self.results if r.status == "auto"]

    @property
    def review(self) -> list[InvoiceResult]:
        return [r for r in self.results if r.status == "review"]


@dataclass
class _Read:
    """What one file's API calls produced, before post-processing."""

    path: Path
    document: ExtractedDocument | None = None
    verification: VerificationDocument | None = None
    error: str | None = None


def run(
    paths: list[Path],
    config: Config,
    gl_config: GLConfig,
    ledger: Ledger,
    extractor: Extractor,
    jobs: int = 4,
) -> RunReport:
    report = RunReport()
    if not paths:
        return report

    reads = _read_all(paths, config, extractor, jobs)

    for read in reads:
        report.files_read += 1
        if read.error is not None:
            report.failures.append(FileFailure(read.path, read.error))
            continue

        assert read.document is not None
        if not read.document.invoices:
            report.failures.append(
                FileFailure(read.path, "no invoice was found in this file")
            )
            continue

        results = [
            validate.build(read.path.name, extracted, config)
            for extracted in read.document.invoices
        ]

        if read.verification is not None:
            consensus.attach(results, read.verification)
        elif config.verify:
            for result in results:
                result.add(
                    "verify-failed",
                    "the second, independent read did not complete, so the "
                    "values could not be cross-checked",
                )

        for result in results:
            gl_module.assign(result, gl_config, config)
            ledger.check(result)

        report.results.extend(results)

    return report


def _read_all(
    paths: list[Path], config: Config, extractor: Extractor, jobs: int
) -> list[_Read]:
    """Read every file, in parallel, returning results in input order."""
    workers = max(1, min(jobs, len(paths)))
    if workers == 1:
        return [_read_one(path, config, extractor) for path in paths]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(lambda p: _read_one(p, config, extractor), paths))


def _read_one(path: Path, config: Config, extractor: Extractor) -> _Read:
    read = _Read(path=path)
    try:
        read.document = extractor.read(path)
    except (ExtractionError, UnsupportedDocument) as exc:
        read.error = str(exc)
        return read

    if config.verify:
        try:
            read.verification = extractor.verify(path)
        except (ExtractionError, UnsupportedDocument) as exc:
            # Not fatal: the extraction succeeded, so the invoice is still
            # exportable — just not cross-checked, which `run` turns into a
            # blocker so it lands in review rather than the upload sheet.
            log.warning("verification pass failed for %s: %s", path.name, exc)
    return read
