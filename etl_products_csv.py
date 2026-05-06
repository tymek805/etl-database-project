import argparse
import csv
import sys
from dataclasses import dataclass, field
from pathlib import Path


DEFAULT_INPUT_FILE = Path("data/products_feed.csv")
DEFAULT_REJECTS_FILE = Path("data/products_rejected.csv")

ACTIVE_VALUES = {"tak", "true", "1", "yes", "y"}


@dataclass
class ProductRecord:
    row_number: int
    nazwa: str
    cena: int
    stanmagazynowy: int
    kategoria: str
    producent: str
    kraj_producenta: str
    wartosc_magazynu: int
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
    loaded: int = 0
    inserted: int = 0
    updated: int = 0
    categories_created: int = 0
    producers_created: int = 0
    skipped: int = 0
    rejected_file: str | None = None
    total_inventory_value: int = 0


def extract_products(csv_path):
    csv_path = Path(csv_path)
    with csv_path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        return list(reader)


def normalize_text(value):
    return " ".join(str(value or "").strip().split())


def normalize_key(value):
    return normalize_text(value).casefold()


def parse_int(value, field_name, row_number):
    try:
        return int(str(value).strip())
    except (TypeError, ValueError) as error:
        raise ValueError(f"field '{field_name}' must be an integer") from error


def reject(row_number, reason, source, rejected):
    rejected.append(RejectedRow(row_number=row_number, reason=reason, source=dict(source)))


def transform_products(rows):
    rejected = []
    products_by_key = {}

    for row_number, row in enumerate(rows, start=2):
        is_active = normalize_key(row.get("aktywny")) in ACTIVE_VALUES
        if not is_active:
            reject(row_number, "inactive product", row, rejected)
            continue

        try:
            name = normalize_text(row.get("nazwa"))
            category = normalize_text(row.get("kategoria"))
            producer = normalize_text(row.get("producent"))
            producer_country = normalize_text(row.get("kraj_producenta"))
            price = parse_int(row.get("cena"), "cena", row_number)
            stock = parse_int(row.get("stanmagazynowy"), "stanmagazynowy", row_number)
        except ValueError as error:
            reject(row_number, str(error), row, rejected)
            continue

        validation_errors = []
        if not name:
            validation_errors.append("missing product name")
        if not category:
            validation_errors.append("missing category")
        if not producer:
            validation_errors.append("missing producer")
        if price <= 0:
            validation_errors.append("price must be greater than zero")
        if stock < 0:
            validation_errors.append("stock cannot be negative")

        if validation_errors:
            reject(row_number, "; ".join(validation_errors), row, rejected)
            continue

        key = (normalize_key(name), normalize_key(producer))
        if key in products_by_key:
            product = products_by_key[key]
            product.cena = price
            product.stanmagazynowy += stock
            product.wartosc_magazynu = product.cena * product.stanmagazynowy
            product.source_rows.append(row_number)
            continue

        products_by_key[key] = ProductRecord(
            row_number=row_number,
            nazwa=name,
            cena=price,
            stanmagazynowy=stock,
            kategoria=category,
            producent=producer,
            kraj_producenta=producer_country,
            wartosc_magazynu=price * stock,
            source_rows=[row_number],
        )

    products = list(products_by_key.values())
    return products, rejected


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


def get_or_create_category(session, name):
    from sqlalchemy import text

    category_id = fetch_one_id(
        session,
        text("select kategoriaid from kategoria where lower(nazwa) = lower(:name) limit 1"),
        {"name": name},
    )
    if category_id:
        return category_id, False

    return fetch_one_id(
        session,
        text(
            """
            insert into kategoria (kategoriaid, nazwa)
            values ((select coalesce(max(kategoriaid), 0) + 1 from kategoria), :name)
            returning kategoriaid
            """
        ),
        {"name": name},
    ), True


def get_or_create_producer(session, name, country):
    from sqlalchemy import text

    producer_id = fetch_one_id(
        session,
        text("select producentid from producent where lower(nazwa) = lower(:name) limit 1"),
        {"name": name},
    )
    if producer_id:
        return producer_id, False

    return fetch_one_id(
        session,
        text(
            """
            insert into producent (producentid, nazwa, kraj)
            values ((select coalesce(max(producentid), 0) + 1 from producent), :name, :country)
            returning producentid
            """
        ),
        {"name": name, "country": country or None},
    ), True


def validate_database_privileges(session):
    from sqlalchemy import text

    required_privileges = {
        "public.produkt": ["SELECT", "INSERT", "UPDATE"],
        "public.kategoria": ["SELECT", "INSERT"],
        "public.producent": ["SELECT", "INSERT"],
    }
    missing_privileges = []

    for table_name, privileges in required_privileges.items():
        for privilege in privileges:
            has_privilege = fetch_one_id(
                session,
                text("select has_table_privilege(current_user, :table_name, :privilege)"),
                {"table_name": table_name, "privilege": privilege},
            )
            if not has_privilege:
                missing_privileges.append(f"{privilege} on {table_name}")

    if missing_privileges:
        missing = ", ".join(missing_privileges)
        raise RuntimeError(
            "Brak uprawnien do pelnego scenariusza ETL: "
            f"{missing}. Nadaj uprawnienia w PostgreSQL, np. "
            "GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO etl_user;"
        )


def load_products(products):
    from sqlalchemy import text

    from db import SessionLocal

    session = SessionLocal()
    result = EtlResult(transformed=len(products))

    try:
        validate_database_privileges(session)

        for product in products:
            category_id, category_created = get_or_create_category(session, product.kategoria)
            producer_id, producer_created = get_or_create_producer(
                session,
                product.producent,
                product.kraj_producenta,
            )

            existing_product_id = fetch_one_id(
                session,
                text(
                    """
                    select produktid
                    from produkt
                    where lower(nazwa) = lower(:name)
                      and producentid = :producer_id
                    limit 1
                    """
                ),
                {"name": product.nazwa, "producer_id": producer_id},
            )

            if existing_product_id:
                session.execute(
                    text(
                        """
                        update produkt
                        set cena = :price,
                            stanmagazynowy = :stock,
                            kategoriaid = :category_id,
                            producentid = :producer_id
                        where produktid = :product_id
                        """
                    ),
                    {
                        "price": product.cena,
                        "stock": product.stanmagazynowy,
                        "category_id": category_id,
                        "producer_id": producer_id,
                        "product_id": existing_product_id,
                    },
                )
                result.updated += 1
            else:
                session.execute(
                    text(
                        """
                        insert into produkt (
                            produktid,
                            nazwa,
                            cena,
                            stanmagazynowy,
                            kategoriaid,
                            producentid
                        )
                        values (
                            (select coalesce(max(produktid), 0) + 1 from produkt),
                            :name,
                            :price,
                            :stock,
                            :category_id,
                            :producer_id
                        )
                        """
                    ),
                    {
                        "name": product.nazwa,
                        "price": product.cena,
                        "stock": product.stanmagazynowy,
                        "category_id": category_id,
                        "producer_id": producer_id,
                    },
                )
                result.inserted += 1

            result.categories_created += int(category_created)
            result.producers_created += int(producer_created)

        session.commit()
        result.loaded = result.inserted + result.updated
        return result
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def run_etl(csv_path=DEFAULT_INPUT_FILE, dry_run=False, rejects_file=DEFAULT_REJECTS_FILE):
    rows = extract_products(csv_path)
    products, rejected = transform_products(rows)

    result = EtlResult(
        extracted=len(rows),
        transformed=len(products),
        skipped=len(rejected),
        total_inventory_value=sum(product.wartosc_magazynu for product in products),
    )

    if rejected:
        result.rejected_file = str(write_rejected_rows(rejected, rejects_file))

    if not dry_run:
        load_result = load_products(products)
        result.loaded = load_result.loaded
        result.inserted = load_result.inserted
        result.updated = load_result.updated
        result.categories_created = load_result.categories_created
        result.producers_created = load_result.producers_created

    return result


def main():
    parser = argparse.ArgumentParser(description="ETL: zaawansowany import produktow z CSV.")
    parser.add_argument("--file", default=DEFAULT_INPUT_FILE, help="Sciezka do pliku CSV z produktami.")
    parser.add_argument("--dry-run", action="store_true", help="Wykonaj extract i transform bez zapisu do bazy.")
    parser.add_argument(
        "--rejects-file",
        default=DEFAULT_REJECTS_FILE,
        help="Sciezka do raportu odrzuconych rekordow.",
    )
    args = parser.parse_args()

    try:
        result = run_etl(args.file, args.dry_run, args.rejects_file)
    except RuntimeError as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)

    print("ETL scenario: zaawansowany import produktow z CSV")
    print(f"Extracted rows: {result.extracted}")
    print(f"Transformed products: {result.transformed}")
    print(f"Skipped rows: {result.skipped}")
    print(f"Loaded products: {result.loaded}")
    print(f"Inserted products: {result.inserted}")
    print(f"Updated products: {result.updated}")
    print(f"Created categories: {result.categories_created}")
    print(f"Created producers: {result.producers_created}")
    print(f"Total inventory value: {result.total_inventory_value}")
    if result.rejected_file:
        print(f"Rejected rows report: {result.rejected_file}")


if __name__ == "__main__":
    main()
