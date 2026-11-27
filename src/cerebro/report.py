from contextlib import closing
from decimal import Decimal
from pathlib import Path

from .ledger import check_schema, connect, currency_code


def summarize(database: Path, currency: str, campaign: str | None = None) -> dict:
    currency = currency_code(currency)
    with closing(connect(database, "ro")) as db, db:
        check_schema(db)
        db.execute("BEGIN")
        spend_minor = 0
        if campaign is not None:
            record = db.execute(
                "SELECT spend_minor FROM campaigns WHERE currency = ? AND id = ?", (currency, campaign)
            ).fetchone()
            if record is None:
                raise ValueError("campaign does not exist for the requested currency")
            spend_minor = record[0]
        else:
            spend_minor = sum(row[0] for row in db.execute(
                "SELECT spend_minor FROM campaigns WHERE currency = ?", (currency,)
            ))

        gross_minor = fees_minor = refunds_minor = transactions = 0
        metrics = db.execute(
            """SELECT gross_minor, fee_minor, refund_minor FROM unit_economics_metrics
               WHERE currency = ? AND (? IS NULL OR campaign_id = ?)""",
            (currency, campaign, campaign),
        )
        for gross, fee, refunded in metrics:
            transactions += 1
            gross_minor += gross
            fees_minor += fee
            refunds_minor += refunded

    net_minor = gross_minor - fees_minor - refunds_minor - spend_minor
    margin_pct = f"{Decimal(net_minor) * 100 / gross_minor:.2f}" if gross_minor else None
    return {
        "currency": currency,
        "campaign": campaign,
        "transactions": transactions,
        "gross_minor": gross_minor,
        "fees_minor": fees_minor,
        "refunds_minor": refunds_minor,
        "spend_minor": spend_minor,
        "net_minor": net_minor,
        "net_margin_pct": margin_pct,
    }
