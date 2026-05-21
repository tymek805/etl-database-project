from models import Produkt, Klient

from repositories import (
    # products
    get_or_create_category,
    get_or_create_producer,
    get_existing_product,
    # customers
    get_existing_address,
    create_address,
    get_customer_by_email,
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


def synchronize_customer(
    session,
    customer_record
):

    stats = {
        "inserted": 0,
        "updated": 0,
    }

    address = get_existing_address(
        session,
        customer_record.miejscowosck,
        customer_record.ulica,
        customer_record.kodpocztowyk,
        customer_record.krajk,
    )

    if not address:

        address = create_address(
            session,
            customer_record.miejscowosck,
            customer_record.ulica,
            customer_record.kodpocztowyk,
            customer_record.krajk,
        )

    existing_customer = get_customer_by_email(
        session,
        customer_record.email
    )

    # UPDATE
    if existing_customer:

        existing_customer.imie = (
            customer_record.imie
        )

        existing_customer.nazwisko = (
            customer_record.nazwisko
        )

        existing_customer.telefon = (
            customer_record.telefon
        )

        existing_customer.adrklientid = (
            address.adrklientaid
        )

        stats["updated"] = 1

        return stats

    # INSERT
    new_customer = Klient(

        imie=customer_record.imie,

        nazwisko=customer_record.nazwisko,

        email=customer_record.email,

        telefon=customer_record.telefon,

        adrklientid=address.adrklientaid
    )

    session.add(new_customer)

    stats["inserted"] = 1

    return stats
