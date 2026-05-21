from sqlalchemy import func
from models import Produkt, Kategoria, Producent


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
