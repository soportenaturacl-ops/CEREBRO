import csv
import re
import sqlite3
from contextlib import closing
from importlib.resources import files
from pathlib import Path


APPLICATION_ID = 0x43455242
SCHEMA_VERSION = 1
CSV_COLUMNS = ("kind", "id", "currency", "amount_minor", "fee_minor", "transaction_id", "campaign_id")
TABLES = {
    "campaign": ("campaigns", ("currency", "spend_minor")),
    "transaction": ("transactions", ("currency", "gross_minor", "fee_minor", "campaign_id")),
    "refund": ("refunds", ("currency", "amount_minor", "transaction_id")),
}


def connect(path: Path, mode: str) -> sqlite3.Connection:
    db = sqlite3.connect(f"{path.resolve().as_uri()}?mode={mode}", uri=True)
    db.execute("PRAGMA foreign_keys = ON")
    return db


def initialize(path: Path) -> None:
    with closing(connect(path, "rwc")) as db:
        if db.execute("PRAGMA application_id").fetchone()[0] == APPLICATION_ID:
            check_schema(db)
            return
        if db.execute("SELECT 1 FROM sqlite_master LIMIT 1").fetchone():
            raise ValueError("database already contains a different schema")

        schema = files("cerebro").joinpath("schema.sql").read_text(encoding="utf-8")
        db.executescript(
            "BEGIN IMMEDIATE;\n" + schema
            + f"\nPRAGMA application_id = {APPLICATION_ID};"
            + f"\nPRAGMA user_version = {SCHEMA_VERSION};\nCOMMIT;"
        )


def check_schema(db: sqlite3.Connection) -> None:
    if db.execute("PRAGMA application_id").fetchone()[0] != APPLICATION_ID:
        raise ValueError("initialize a CEREBRO database first")
    if db.execute("PRAGMA user_version").fetchone()[0] != SCHEMA_VERSION:
        raise ValueError("unsupported CEREBRO schema version")


def currency_code(value: str) -> str:
    code = value.upper()
    if not re.fullmatch(r"[A-Z]{3}", code):
        raise ValueError("currency must be a three-letter code")
    return code


def minor_units(value: str, field: str) -> int:
    if not re.fullmatch(r"[0-9]{1,19}", value) or int(value) > 2**63 - 1:
        raise ValueError(f"{field} must be a nonnegative integer in SQLite range")
    return int(value)


def parse_row(row: dict[str, str]) -> tuple[str, str, tuple]:
    kind, identifier, currency, amount, fee, transaction_id, campaign_id = (
        row[name].strip() for name in CSV_COLUMNS
    )
    if not identifier:
        raise ValueError("id is required")
    currency = currency_code(currency)
    amount = minor_units(amount, "amount_minor")

    if kind == "campaign" and not (fee or transaction_id or campaign_id):
        return kind, identifier, (currency, amount)
    if kind == "transaction" and not transaction_id and amount > 0:
        return kind, identifier, (currency, amount, minor_units(fee, "fee_minor"), campaign_id or None)
    if kind == "refund" and transaction_id and not (fee or campaign_id) and amount > 0:
        return kind, identifier, (currency, amount, transaction_id)
    raise ValueError("invalid kind, amount or fields for this entry")


def read_entries(path: Path) -> dict[str, list[tuple]]:
    entries: dict[str, list[tuple]] = {kind: [] for kind in TABLES}
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, strict=True)
        if tuple(reader.fieldnames or ()) != CSV_COLUMNS:
            raise ValueError("CSV header must be: " + ",".join(CSV_COLUMNS))
        for row in reader:
            line = reader.line_num
            if None in row or None in row.values():
                raise ValueError(f"CSV line {line}: wrong number of cells")
            try:
                kind, identifier, values = parse_row(row)
            except ValueError as exc:
                raise ValueError(f"CSV line {line}: {exc}") from exc
            entries[kind].append((line, identifier, values))
    return entries


def import_csv(database: Path, source: Path) -> int:
    entries = read_entries(source)
    inserted = 0
    with closing(connect(database, "rw")) as db, db:
        check_schema(db)
        db.execute("BEGIN IMMEDIATE")
        for kind, (table, columns) in TABLES.items():
            column_list = ", ".join(columns)
            placeholders = ", ".join("?" for _ in range(len(columns) + 1))
            for line, identifier, values in entries[kind]:
                existing = db.execute(
                    f"SELECT {column_list} FROM {table} WHERE id = ?", (identifier,)
                ).fetchone()
                if existing == values:
                    continue
                if existing is not None:
                    raise ValueError(f"CSV line {line}: {kind} ID already has different values")
                try:
                    db.execute(
                        f"INSERT INTO {table} (id, {column_list}) VALUES ({placeholders})",
                        (identifier, *values),
                    )
                except sqlite3.IntegrityError as exc:
                    raise ValueError(f"CSV line {line}: {exc}") from exc
                inserted += 1
    return inserted
