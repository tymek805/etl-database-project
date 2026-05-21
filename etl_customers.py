import csv
import json
from dataclasses import dataclass
from pathlib import Path

from db import SessionLocal
from services import synchronize_customer


DEFAULT_INPUT_FILE = Path("data/customers_feed.csv")
DEFAULT_REJECTS_FILE = Path("data/customers_rejected.csv")


@dataclass
class CustomerRecord:
    row_number: int

    imie: str
    nazwisko: str
    email: str
    telefon: int

    miejscowosck: str
    ulica: str
    kodpocztowyk: str
    krajk: str


@dataclass
class EtlResult:
    extracted: int = 0
    transformed: int = 0
    loaded: int = 0
    inserted: int = 0
    updated: int = 0
    skipped: int = 0

    def summary(self):

        lines = [
            f"Extracted rows:        {self.extracted}",
            f"Transformed customers: {self.transformed}",
            f"Skipped rows:          {self.skipped}",
        ]

        if self.loaded:
            lines.extend([
                f"Loaded customers:      {self.loaded}",
                f"Inserted customers:    {self.inserted}",
                f"Updated customers:     {self.updated}",
            ])

        return lines


def extract_customers(file_path):
    file_path = Path(file_path)

    if file_path.suffix.lower() == ".json":

        with open(
            file_path,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

            return data

    elif file_path.suffix.lower() == ".csv":

        with open(
            file_path,
            "r",
            encoding="utf-8",
            newline=""
        ) as file:

            reader = csv.DictReader(file)

            return list(reader)

    else:

        raise ValueError(
            f"Unsupported file type: {file_path.suffix}"
        )


def transform_customers(rows):

    customers = []

    for row_number, row in enumerate(rows, start=2):

        try:

            customer = CustomerRecord(
                row_number=row_number,

                imie=row["imie"].strip(),
                nazwisko=row["nazwisko"].strip(),
                email=row["email"].strip(),

                telefon=int(row["telefon"]),

                miejscowosck=row["miejscowosck"].strip(),
                ulica=row["ulica"].strip(),
                kodpocztowyk=row["kodpocztowyk"].strip(),
                krajk=row["krajk"].strip(),
            )

            customers.append(customer)

        except Exception as e:

            print(
                f"Skipping row {row_number}: {e}"
            )

    return customers


def load_customers(customers):

    session = SessionLocal()

    result = EtlResult(
        transformed=len(customers)
    )

    try:

        for customer in customers:

            stats = synchronize_customer(
                session,
                customer
            )

            result.inserted += stats["inserted"]
            result.updated += stats["updated"]

        session.commit()

        result.loaded = (
            result.inserted +
            result.updated
        )

        return result

    except Exception:

        session.rollback()
        raise

    finally:

        session.close()


def run_etl(
    file_path=DEFAULT_INPUT_FILE,
    dry_run=False,
    rejects_file=None
):

    rows = extract_customers(file_path)

    customers = transform_customers(rows)

    result = EtlResult(
        extracted=len(rows),
        transformed=len(customers),
    )

    if not dry_run:

        load_result = load_customers(
            customers
        )

        result.loaded = load_result.loaded
        result.inserted = load_result.inserted
        result.updated = load_result.updated

    return result