# invoice-extract

Reads scanned vendor invoices and produces the spreadsheet the 3rd-party
accounting team uploads to m3 — vendor, invoice number, GL account and amount —
so nobody has to key them by hand.

Point it at a folder of scans; it writes an `.xlsx` with three sheets:

| Sheet | What's on it |
|---|---|
| **Invoices** | The upload sheet. Only invoices that passed every check. |
| **Exceptions** | Everything held back, with the reason and the scan it came from. |
| **Audit** | Every booked field with the text it was read from and the confidence, for spot-checking. |

## Why it holds invoices back

Accuracy here means never quietly writing a wrong number into the accounting
system. An invoice reaches the upload sheet only if all of the following hold:

1. **Two independent reads agree.** Every scan is read twice with different
   prompts, and the second read never sees the first. If they disagree on
   vendor, invoice number, date or amount, the invoice is held. This is the
   main guard, because a misread that survives one pass rarely survives two.
2. **The value matches the characters it came from.** Each field is returned
   with the exact text quoted off the page; if the normalized value no longer
   matches that text, the invoice is held.
3. **The invoice's own numbers add up.** Subtotal + tax + freight + other
   − discount must equal the stated total, within a configurable tolerance.
4. **The date is plausible.** Not in the future, not older than the configured
   window — that is where a misread year or a swapped day/month shows up.
5. **The invoice hasn't been submitted before.** Same vendor and invoice
   number, in this batch or any earlier run, is held. Duplicate payments are
   the most expensive AP error and batch scanning invites them.
6. **A GL account could be assigned from the rules.** Never guessed — see
   below.
7. **The model said it could read it.** Anything marked low-confidence, or
   flagged as a statement / quote / packing slip rather than an invoice, is
   held.

Exit code is `0` when everything passed, `1` when something needs a person, and
`2` when the run itself failed — so it can gate an automated step.

## The GL account

The GL account is the one required field that is **not printed on an invoice**.
It is your coding decision, so it comes from `gl_accounts.yaml`, not from the
page. Resolution order, first match wins:

1. a keyword under the matched vendor (e.g. Sysco + "wine" → beverage)
2. that vendor's default account
3. a global keyword
4. `fallback_account`, if you set one

If nothing matches, the invoice goes to the exceptions sheet with the vendor
name, so someone can add the rule once and every future invoice from that
vendor codes itself. Account codes referenced by rules must exist in the
`accounts:` chart — a typo fails at startup rather than reaching m3.

## Install

```bash
cd invoice-extract
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
```

Credentials resolve the way the Anthropic SDK expects — set
`ANTHROPIC_API_KEY`, or run `ant auth login` once. No key is read or stored by
this tool.

## Use

```bash
cp config/config.example.yaml config/config.yaml
cp config/gl_accounts.example.yaml config/gl_accounts.yaml
# edit both for your chart of accounts and upload template

invoice-extract scans/2026-08/ \
  --config config/config.yaml \
  --gl config/gl_accounts.yaml \
  --out uploads/2026-08.xlsx \
  --ledger uploads/submitted.sqlite
```

```
Reading 42 scan(s) with claude-opus-5...

Read 42 file(s).
  39 invoice(s) ready to upload -> 'Invoices' sheet in uploads/2026-08.xlsx
  3 invoice(s) held for review -> 'Exceptions' sheet

Held for review:
  scan-0117.pdf — Grainger 9481773265
      [no-gl-account] could not assign a GL account: vendor 'Grainger' has a
      rule but no default account, and no keyword matched this invoice's line items
  scan-0124.pdf — Sysco Corporation 4471-9928
      [verify-total] the two reads disagree on the amount: 1,412.09 vs 1,412.99
  scan-0131.pdf — City Water & Power 88-201466
      [duplicate] already submitted on 2026-07-08 from scan-0092.pdf for 2,204.16
```

Useful flags:

| Flag | Effect |
|---|---|
| `--list` | Show which files would be read, then stop. |
| `--include-review` | Put held invoices on the main sheet too (off by default). |
| `--no-verify` | Skip the second read. Halves cost, removes guard #1. |
| `--no-record` | Check the duplicate ledger but don't add this run to it. |
| `--jobs N` | Scans read concurrently (default 4). |

**Keep the ledger file between runs.** It is the only thing that catches an
invoice already submitted in an earlier batch; delete it and duplicate
detection resets to within-batch only.

## Matching your upload template

The `columns:` block in `config.yaml` is the column layout — keys are fields
this tool produces, values are the header text your template expects, and the
order of the block is the order of the columns. Rename, reorder and drop rows
until it matches the sheet the accounting team sends you.

Dates are written as `YYYY-MM-DD` text and amounts as numbers formatted to two
decimals. If m3's importer wants something else, say so and it's a small change
in `workbook.py`.

## Input formats

PDF (scanned or native), PNG, JPG, GIF, WEBP. Files up to ~22 MB; a file
holding several invoices is fine — each one comes out as its own row.

## Cost

Each scan is two API calls (one if `--no-verify`). The system prompt is cached,
so every scan after the first in a run reads it at cache rates. The run prints
its token usage at the end; price it against your own rate before committing to
a monthly volume.

## Tests

```bash
pip install -e ".[dev]"
pytest
```

The suite covers parsing, validation, consensus, GL resolution, duplicate
detection, export and the CLI end-to-end with the API stubbed out. It does not
measure extraction accuracy — that needs a labelled set of your own invoices,
which is the right next step before this runs unattended (see below).

## Before running this unattended

Two things this cannot tell you on its own:

- **Measured accuracy on your invoices.** Hand-key 50–100 representative scans,
  run them through, and compare. That gives you the real auto-pass rate and
  shows which vendors need rules. The design holds anything doubtful, so the
  expected failure mode is too many exceptions rather than wrong data — but
  that should be verified, not assumed.
- **A reconciliation step.** The tool guarantees each row is faithful to its
  scan. It cannot tell you a scan is missing from the batch. Tie the batch
  total and count back to whatever you count invoices against today.
