import argparse
import csv
import json
import sqlite3
from pathlib import Path

from .ledger import import_csv, initialize
from .report import summarize


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Analyze a local transaction ledger.")
    parser.add_argument("--db", type=Path, default=Path("cerebro.sqlite3"), help="SQLite database path")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init", help="Initialize a ledger database")
    importer = commands.add_parser("import-csv", help="Import entries from a normalized CSV file")
    importer.add_argument("source", type=Path)
    report = commands.add_parser("report", help="Print a unit economics report as JSON")
    report.add_argument("--currency", required=True)
    report.add_argument("--campaign")
    args = parser.parse_args(argv)

    try:
        if args.command == "init":
            initialize(args.db)
            result = {"database": str(args.db)}
        elif args.command == "import-csv":
            result = {"inserted": import_csv(args.db, args.source)}
        else:
            result = summarize(args.db, args.currency, args.campaign)
    except (ValueError, OSError, csv.Error, sqlite3.Error) as exc:
        parser.exit(1, f"cerebro: {exc}\n")

    print(json.dumps(result, indent=2))
    return 0
