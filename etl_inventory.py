import argparse
import csv
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd


DEFAULT_INPUT_FILE = Path("data/inventory_updates_feed.xlsx")
DEFAULT_REJECTS_FILE = Path("data/inventory_updates_rejected.csv")


@dataclass
class InventoryUpdateRecord:
    row_number: int
    nazwa: str
    producent: str
    zmiana_stanu: int
    powod: str
    source_rows: list[int] = field(default_factory=list)


@dataclass
class RejectedRow:
    row_number: int
    reason: str
    source: dict


@dataclass
class EtlResult:
    extracted: int = 0
    transformed: int = 0
    validated: int = 0
    loaded: int = 0
    updated: int = 0
    skipped: int = 0
    rejected_file: str | None = None
    total_stock_delta: int = 0

    def summary(self):
        lines = [
            f"Extracted rows:          {self.extracted}",
            f"Transformed updates:     {self.transformed}",
            f"Valid inventory updates: {self.validated}",
            f"Skipped rows:            {self.skipped}",
            f"Total stock delta:       {self.total_stock_delta}",
        ]

        if self.loaded:
            lines.extend([
                f"Loaded updates:          {self.loaded}",
                f"Updated products:        {self.updated}",
            ])

        if self.rejected_file:
            lines.append("")
            lines.append(
                f"Rejected rows report saved to:\n{self.rejected_file}"
            )

        return lines


def extract_inventory_updates(file_path):
    file_path = Path(file_path)

    if file_path.suffix.lower() == ".xlsx":
        try:
            dataframe = pd.read_excel(file_path, sheet_name=0)
        except ImportError as error:
            raise RuntimeError(
                "Reading .xlsx files requires openpyxl. "
                "Install dependencies with: pip install -r requirements.txt"
            ) from error

        return dataframe.to_dict(orient="records")

    if file_path.suffix.lower() == ".json":
        with file_path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, list):
            raise ValueError("JSON input must contain a list of records")

        return data

    if file_path.suffix.lower() == ".csv":
        with file_path.open("r", encoding="utf-8", newline="") as file:
            reader = csv.DictReader(file)
            return list(reader)

    raise ValueError(
        f"Unsupported file type: {file_path.suffix}. Supported: .xlsx"
    )


def normalize_text(value):
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass

    if value is None:
        return ""

    return " ".join(str(value).strip().split())


def normalize_key(value):
    return normalize_text(value).casefold()


def get_value(row, *field_names):
    for field_name in field_names:
        if field_name in row:
            return row.get(field_name)

    return None


def parse_int(value, field_name):
    if normalize_text(value) == "":
        raise ValueError(f"field '{field_name}' is required")

    if isinstance(value, bool):
        raise ValueError(f"field '{field_name}' must be an integer")

    if isinstance(value, int):
        return value

    if isinstance(value, float):
        if value.is_integer():
            return int(value)

        raise ValueError(f"field '{field_name}' must be an integer")

    try:
        return int(str(value).strip())
    except (TypeError, ValueError) as error:
        raise ValueError(f"field '{field_name}' must be an integer") from error


def reject(row_number, reason, source, rejected):
    rejected.append(
        RejectedRow(
            row_number=row_number,
            reason=reason,
            source=dict(source)
        )
    )


def transform_inventory_updates(rows):
    rejected = []
    updates_by_key = {}

    for row_number, row in enumerate(rows, start=2):
        try:
            name = normalize_text(
                get_value(row, "nazwa", "produkt", "product")
            )
            producer = normalize_text(
                get_value(row, "producent", "producer")
            )
            reason = normalize_text(
                get_value(row, "powod", "reason")
            )
            stock_delta = parse_int(
                get_value(
                    row,
                    "zmiana_stanu",
                    "zmiana",
                    "delta",
                    "ilosc"
                ),
                "zmiana_stanu"
            )
        except ValueError as error:
            reject(row_number, str(error), row, rejected)
            continue

        validation_errors = []

        if not name:
            validation_errors.append("missing product name")

        if not producer:
            validation_errors.append("missing producer")

        if stock_delta == 0:
            validation_errors.append("stock delta cannot be zero")

        if validation_errors:
            reject(row_number, "; ".join(validation_errors), row, rejected)
            continue

        key = (normalize_key(name), normalize_key(producer))

        if key in updates_by_key:
            update = updates_by_key[key]
            update.zmiana_stanu += stock_delta
            update.source_rows.append(row_number)

            if reason:
                update.powod = (
                    f"{update.powod}; {reason}"
                    if update.powod
                    else reason
                )

            continue

        updates_by_key[key] = InventoryUpdateRecord(
            row_number=row_number,
            nazwa=name,
            producent=producer,
            zmiana_stanu=stock_delta,
            powod=reason,
            source_rows=[row_number],
        )

    return list(updates_by_key.values()), rejected


def write_rejected_rows(rejected_rows, output_path=DEFAULT_REJECTS_FILE):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = sorted(
        {field for rejected in rejected_rows for field in rejected.source.keys()}
        | {"row_number", "reason"}
    )

    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

        for rejected in rejected_rows:
            row = dict(rejected.source)
            row["row_number"] = rejected.row_number
            row["reason"] = rejected.reason
            writer.writerow(row)

    return output_path


def fetch_one_id(session, query, params):
    result = session.execute(query, params).fetchone()
    return result[0] if result else None


def validate_database_privileges(session):
    from sqlalchemy import text

    required_privileges = {
        "public.produkt": ["SELECT", "UPDATE"],
        "public.producent": ["SELECT"],
    }
    missing_privileges = []

    for table_name, privileges in required_privileges.items():
        for privilege in privileges:
            has_privilege = fetch_one_id(
                session,
                text(
                    "select has_table_privilege("
                    "current_user, :table_name, :privilege)"
                ),
                {"table_name": table_name, "privilege": privilege},
            )

            if not has_privilege:
                missing_privileges.append(f"{privilege} on {table_name}")

    if missing_privileges:
        missing = ", ".join(missing_privileges)
        raise RuntimeError(
            "Brak uprawnien do aktualizacji stanow magazynowych: "
            f"{missing}. Nadaj uprawnienia w PostgreSQL, np. "
            "GRANT SELECT, UPDATE ON produkt TO etl_user;"
        )


def record_to_source(record):
    return {
        "nazwa": record.nazwa,
        "producent": record.producent,
        "zmiana_stanu": record.zmiana_stanu,
        "powod": record.powod,
        "source_rows": ",".join(str(row) for row in record.source_rows),
    }


def apply_inventory_updates(updates, dry_run=False):
    from db import SessionLocal
    from services import synchronize_inventory_update

    session = SessionLocal()

    result = EtlResult(
        transformed=len(updates)
    )
    rejected = []

    try:
        validate_database_privileges(session)

        for update in updates:
            try:
                stats = synchronize_inventory_update(
                    session,
                    update,
                    dry_run=dry_run
                )
            except ValueError as error:
                reject(
                    update.row_number,
                    str(error),
                    record_to_source(update),
                    rejected
                )
                continue

            result.validated += 1
            result.total_stock_delta += update.zmiana_stanu

            if not dry_run:
                result.updated += stats["updated"]

        if dry_run:
            session.rollback()
        else:
            session.commit()
            result.loaded = result.updated

        return result, rejected

    except Exception:
        session.rollback()
        raise

    finally:
        session.close()


def run_etl(
    file_path=DEFAULT_INPUT_FILE,
    dry_run=False,
    rejects_file=DEFAULT_REJECTS_FILE
):
    rows = extract_inventory_updates(file_path)
    updates, rejected = transform_inventory_updates(rows)

    result = EtlResult(
        extracted=len(rows),
        transformed=len(updates),
    )

    if updates:
        load_result, load_rejected = apply_inventory_updates(
            updates,
            dry_run=dry_run
        )

        result.validated = load_result.validated
        result.loaded = load_result.loaded
        result.updated = load_result.updated
        result.total_stock_delta = load_result.total_stock_delta
        rejected.extend(load_rejected)

    result.skipped = len(rejected)

    if rejected:
        result.rejected_file = str(
            write_rejected_rows(rejected, rejects_file)
        )

    return result


def main():
    parser = argparse.ArgumentParser(
        description="ETL: aktualizacja stanow magazynowych z pliku XLSX."
    )
    parser.add_argument(
        "--file",
        default=DEFAULT_INPUT_FILE,
        help="Sciezka do pliku .xlsx z korektami stanow.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Zweryfikuj korekty bez zapisu zmian do bazy.",
    )
    parser.add_argument(
        "--rejects-file",
        default=DEFAULT_REJECTS_FILE,
        help="Sciezka do raportu odrzuconych rekordow.",
    )
    args = parser.parse_args()

    try:
        result = run_etl(args.file, args.dry_run, args.rejects_file)
    except Exception as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)

    print("ETL scenario: aktualizacja stanow magazynowych")
    print(f"Extracted rows: {result.extracted}")
    print(f"Transformed updates: {result.transformed}")
    print(f"Valid inventory updates: {result.validated}")
    print(f"Skipped rows: {result.skipped}")
    print(f"Total stock delta: {result.total_stock_delta}")

    if args.dry_run:
        print(f"Products that would be updated: {result.validated}")
    else:
        print(f"Loaded updates: {result.loaded}")
        print(f"Updated products: {result.updated}")

    if result.rejected_file:
        print(f"Rejected rows report: {result.rejected_file}")


if __name__ == "__main__":
    main()
