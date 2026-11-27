# CEREBRO

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)
![SQLite](https://img.shields.io/badge/Storage-SQLite-003B57.svg)
![Status: Active Development](https://img.shields.io/badge/Status-Active%20Development-orange.svg)

An open-source, local-first Python and SQLite analytics engine and CLI toolkit for unit economics, transaction log ingestion, and self-hosted financial telemetry for solo maintainers and independent builders.

## Overview & Architecture

CEREBRO imports normalized transaction, refund, and acquisition-spend records from CSV into a local SQLite ledger. The CLI reads local files and prints JSON reports. The application makes no network requests and uses the Python standard library at runtime.

Each import runs in one database transaction. Re-importing identical entries is safe. Reusing an ID with different values or supplying an invalid row rolls back the import. Stable record IDs and SQLite foreign keys link refunds and acquisition spend to the underlying transactions.

Reports use integer minor units and group results by currency. Net contribution is gross transaction proceeds minus processing fees, refunds, and recorded acquisition spend. Net margin is net contribution divided by gross proceeds, expressed as a percentage. A zero gross amount produces a null margin. The current report covers all recorded entries in the selected currency, optionally filtered by campaign. It excludes taxes and other costs outside the input fields and performs no currency conversion.

## Database Schema

The schema is bundled with the package in [`src/cerebro/schema.sql`](src/cerebro/schema.sql).

| Object | Role |
| --- | --- |
| `transactions` | Gross amount and processing fee for each transaction, with an optional campaign ID. |
| `campaigns` | One acquisition-spend amount per campaign ID and its currency. |
| `refunds` | Refund events linked to the original transaction. Several partial refunds are supported up to the gross transaction amount. |
| `unit_economics_metrics` | A view with one row per transaction, including total refunds, for aggregation without duplicate revenue. |

## Quickstart & Installation

Use Python 3.10 or later with SQLite support. Clone the public repository from GitHub, or clone the supplied Git bundle for offline use.

```sh
git clone https://github.com/soportenaturacl-ops/CEREBRO.git
# For the offline bundle, use: git clone cerebro-analytics.bundle CEREBRO
cd CEREBRO
python -m venv .venv
# On Windows PowerShell, run .\.venv\Scripts\Activate.ps1
# On macOS or Linux, run source .venv/bin/activate
python -m pip install -r requirements.txt
cerebro --db demo.sqlite3 init
cerebro --db demo.sqlite3 import-csv examples/ledger.csv
cerebro --db demo.sqlite3 report --currency USD
python -m pytest -q
```

The example imports synthetic data and returns `net_minor: 5700` and `net_margin_pct: "57.00"`. To limit the report to the example campaign, add `--campaign example-campaign`. `python -m cerebro` is equivalent to the `cerebro` entry point.

### CSV format

Use the header and order in [`examples/ledger.csv`](examples/ledger.csv). Use stable opaque IDs, a three-letter currency code, and nonnegative integer amounts in the currency's minor unit. Keep unused fields empty.

| `kind` | `amount_minor` | Additional fields |
| --- | --- | --- |
| `campaign` | Acquisition spend | All remaining fields empty. |
| `transaction` | Positive gross amount | `fee_minor` is required. `campaign_id` is optional. |
| `refund` | Positive amount returned | `transaction_id` is required. |

Use one ledger for each reporting period you want to compare. Keep source exports and SQLite databases out of version control. Use synthetic records when reporting an issue.

## Roadmap & Contributing

- Add CSV and JSON adapters for payment processors and acquisition platforms, using public schemas and synthetic fixtures.
- Expand the `pytest` suite to cover adapter parsing, export formats, and additional reconciliation cases.
- Add dated reporting windows and CSV report exports alongside JSON output.

Pull requests are welcome. Include a small reproducible example and a test for behavior changes. Run `python -m pytest -q` before submitting.
