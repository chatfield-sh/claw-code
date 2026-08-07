"""Reading invoices with Claude.

Each scan gets one extraction call and, unless verification is disabled, one
independent verification call. The two calls never see each other's output —
`consensus.py` compares them afterwards.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TypeVar

import anthropic
from pydantic import BaseModel

from . import prompts
from .config import Config
from .documents import content_blocks
from .models import ExtractedDocument, VerificationDocument

log = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class ExtractionError(RuntimeError):
    """A scan could not be read. Carries a message fit for the run report."""


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    calls: int = 0

    def add(self, usage: Any) -> None:
        self.calls += 1
        self.input_tokens += getattr(usage, "input_tokens", 0) or 0
        self.output_tokens += getattr(usage, "output_tokens", 0) or 0
        self.cache_read_tokens += getattr(usage, "cache_read_input_tokens", 0) or 0
        self.cache_write_tokens += getattr(usage, "cache_creation_input_tokens", 0) or 0

    def summary(self) -> str:
        return (
            f"{self.calls} API call(s); "
            f"{self.input_tokens:,} input + {self.cache_read_tokens:,} cached "
            f"+ {self.output_tokens:,} output tokens"
        )


@dataclass
class Extractor:
    config: Config
    known_vendors: list[str] = field(default_factory=list)
    client: anthropic.Anthropic | None = None
    usage: Usage = field(default_factory=Usage)

    def __post_init__(self) -> None:
        if self.client is None:
            # Credentials resolve from ANTHROPIC_API_KEY, ANTHROPIC_AUTH_TOKEN,
            # or an `ant auth login` profile — no key is read or stored here.
            self.client = anthropic.Anthropic(max_retries=4, timeout=600.0)
        hint = prompts.vendor_hint(self.known_vendors)
        self._extraction_system = self._system(prompts.EXTRACTION_SYSTEM + hint)
        self._verification_system = self._system(prompts.VERIFICATION_SYSTEM + hint)

    @staticmethod
    def _system(text: str) -> list[dict[str, Any]]:
        # One breakpoint on the only system block: the whole prefix is stable
        # across every invoice in the run, so each scan after the first reads
        # it from cache.
        return [
            {
                "type": "text",
                "text": text,
                "cache_control": {"type": "ephemeral"},
            }
        ]

    def read(self, path: Path) -> ExtractedDocument:
        """First pass: full structured extraction."""
        return self._call(
            system=self._extraction_system,
            instruction=prompts.EXTRACTION_USER,
            path=path,
            output_format=ExtractedDocument,
        )

    def verify(self, path: Path) -> VerificationDocument:
        """Second pass: independent read of the four booked fields."""
        return self._call(
            system=self._verification_system,
            instruction=prompts.VERIFICATION_USER,
            path=path,
            output_format=VerificationDocument,
        )

    def _call(
        self,
        *,
        system: list[dict[str, Any]],
        instruction: str,
        path: Path,
        output_format: type[T],
    ) -> T:
        assert self.client is not None
        blocks = content_blocks(path)
        blocks.append({"type": "text", "text": instruction})

        try:
            response = self.client.messages.parse(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                system=system,
                messages=[{"role": "user", "content": blocks}],
                output_config={"effort": self.config.effort},
                output_format=output_format,
            )
        except anthropic.APIStatusError as exc:
            raise ExtractionError(
                f"API error {exc.status_code} reading {path.name}: {exc.message}"
            ) from exc
        except anthropic.APIConnectionError as exc:
            raise ExtractionError(
                f"could not reach the API while reading {path.name}: {exc}"
            ) from exc

        self.usage.add(response.usage)

        if response.stop_reason == "refusal":
            detail = getattr(response.stop_details, "explanation", None)
            raise ExtractionError(
                f"the model declined to process {path.name}"
                + (f": {detail}" if detail else "")
            )
        if response.stop_reason == "max_tokens":
            raise ExtractionError(
                f"{path.name}: response hit the {self.config.max_tokens} token "
                "limit and was truncated. Raise `max_tokens` in the config, or "
                "split a file containing many invoices."
            )

        parsed = response.parsed_output
        if parsed is None:
            raise ExtractionError(
                f"{path.name}: the model returned no parseable result "
                f"(stop_reason={response.stop_reason})"
            )
        return parsed
