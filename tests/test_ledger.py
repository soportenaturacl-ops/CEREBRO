from pathlib import Path

import pytest

from cerebro.ledger import CSV_COLUMNS, import_csv, initialize
from cerebro.report import summarize


EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "ledger.csv"


@pytest.fixture
def database(tmp_path):
    path = tmp_path / "ledger.sqlite3"
    initialize(path)
    return path


def write_csv(tmp_path, *rows):
    path = tmp_path / "import.csv"
    path.write_text("\n".join([",".join(CSV_COLUMNS), *rows]) + "\n", encoding="utf-8")
    return path


def test_net_margin_deducts_fees_partial_refunds_and_spend_once(database):
    assert import_csv(database, EXAMPLE) == 4
    assert summarize(database, "USD", "example-campaign") == {
        "currency": "USD",
        "campaign": "example-campaign",
        "transactions": 1,
        "gross_minor": 10000,
        "fees_minor": 300,
        "refunds_minor": 2000,
        "spend_minor": 2000,
        "net_minor": 5700,
        "net_margin_pct": "57.00",
    }


def test_reimport_is_idempotent_and_currencies_are_separate(database, tmp_path):
    assert import_csv(database, EXAMPLE) == 4
    assert import_csv(database, EXAMPLE) == 0
    source = write_csv(tmp_path, "transaction,example-eur,EUR,200,20,,")
    assert import_csv(database, source) == 1
    assert summarize(database, "EUR")["net_minor"] == 180
    assert summarize(database, "USD")["net_minor"] == 5700


def test_foreign_currency_refund_rolls_back_the_import(database, tmp_path):
    source = write_csv(tmp_path,
        "refund,example-refund,EUR,10,,example-order,",
        "transaction,example-order,USD,100,1,,",
    )
    with pytest.raises(ValueError, match="FOREIGN KEY constraint failed"):
        import_csv(database, source)
    assert summarize(database, "USD")["transactions"] == 0


def test_conflicting_duplicate_rolls_back_the_import(database, tmp_path):
    import_csv(database, EXAMPLE)
    source = write_csv(tmp_path,
        "transaction,example-new,USD,50,0,,",
        "transaction,example-order,USD,99,0,,",
    )
    with pytest.raises(ValueError, match="ID already has different values"):
        import_csv(database, source)
    assert summarize(database, "USD")["net_minor"] == 5700


def test_refunds_cannot_exceed_transaction_amount(database, tmp_path):
    import_csv(database, EXAMPLE)
    source = write_csv(tmp_path, "refund,example-excess,USD,8001,,example-order,")
    with pytest.raises(ValueError, match="refunds exceed the original transaction amount"):
        import_csv(database, source)
    assert summarize(database, "USD")["refunds_minor"] == 2000


def test_margin_is_undefined_when_spend_precedes_revenue(database, tmp_path):
    source = write_csv(tmp_path, "campaign,example-campaign,USD,100,,,")
    import_csv(database, source)
    report = summarize(database, "USD")
    assert report["net_minor"] == -100
    assert report["net_margin_pct"] is None
