from models import Produkt

from repositories import (
    get_or_create_category,
    get_or_create_producer,
    get_existing_product,
)


def synchronize_product(session, product_record):
    stats = {
        "inserted": 0,
        "updated": 0,
        "category_created": 0,
        "producer_created": 0,
    }

    category, category_created = get_or_create_category(
        session,
        product_record.kategoria
    )

    stats["category_created"] = int(category_created)

    producer, producer_created = get_or_create_producer(
        session,
        product_record.producent,
        product_record.kraj_producenta,
    )

    stats["producer_created"] = int(producer_created)

    existing_product = get_existing_product(
        session,
        product_record.nazwa,
        producer.producentid
    )

    # UPDATE
    if existing_product:

        existing_product.cena = product_record.cena
        existing_product.stanmagazynowy = (
            product_record.stanmagazynowy
        )

        existing_product.kategoriaid = (
            category.kategoriaid
        )

        existing_product.producentid = (
            producer.producentid
        )

        stats["updated"] = 1

        return stats

    # INSERT
    new_product = Produkt(
        nazwa=product_record.nazwa,
        cena=product_record.cena,
        stanmagazynowy=product_record.stanmagazynowy,
        kategoriaid=category.kategoriaid,
        producentid=producer.producentid,
    )

    session.add(new_product)

    stats["inserted"] = 1

    return stats
