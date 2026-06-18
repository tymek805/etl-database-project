from sqlalchemy import func
from models import Produkt, Kategoria, Producent, Klient, AdrKlienta


def get_category_by_name(session, name):
    return (
        session.query(Kategoria)
        .filter(func.lower(Kategoria.nazwa) == name.lower())
        .first()
    )


def create_category(session, name):
    category = Kategoria(nazwa=name)
    session.add(category)
    session.flush()
    return category


def get_or_create_category(session, name):
    category = get_category_by_name(session, name)

    if category:
        return category, False

    category = create_category(session, name)
    return category, True


def get_producer_by_name(session, name):
    return (
        session.query(Producent)
        .filter(func.lower(Producent.nazwa) == name.lower())
        .first()
    )


def create_producer(session, name, country):
    producer = Producent(
        nazwa=name,
        kraj=country
    )

    session.add(producer)
    session.flush()

    return producer


def get_or_create_producer(session, name, country):
    producer = get_producer_by_name(session, name)

    if producer:
        return producer, False

    producer = create_producer(session, name, country)

    return producer, True


def get_existing_product(session, name, producer_id):
    return (
        session.query(Produkt)
        .filter(
            func.lower(Produkt.nazwa) == name.lower(),
            Produkt.producentid == producer_id
        )
        .first()
    )


def get_product_by_name_and_producer_name(session, product_name, producer_name):
    return (
        session.query(Produkt)
        .join(Producent, Produkt.producentid == Producent.producentid)
        .filter(
            func.lower(Produkt.nazwa) == product_name.lower(),
            func.lower(Producent.nazwa) == producer_name.lower()
        )
        .first()
    )


def get_existing_address(
    session,
    city,
    street,
    postal_code,
    country
):
    return (
        session.query(AdrKlienta)
        .filter(
            func.lower(AdrKlienta.miejscowosck) == city.lower(),
            func.lower(AdrKlienta.ulica) == street.lower(),
            func.lower(AdrKlienta.krajk) == country.lower(),
            AdrKlienta.kodpocztowyk == postal_code
        )
        .first()
    )


def create_address(
    session,
    city,
    street,
    postal_code,
    country
):
    address = AdrKlienta(
        miejscowosck=city,
        ulica=street,
        kodpocztowyk=postal_code,
        krajk=country
    )

    session.add(address)
    session.flush()

    return address


def get_customer_by_email(session, email):
    return (
        session.query(Klient)
        .filter(
            func.lower(Klient.email) == email.lower()
        )
        .first()
    )
