from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    ForeignKey,
    TIMESTAMP
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class AdrPracownikow(Base):
    __tablename__ = "AdrPracownikow"

    AdrPracownikID = Column(Integer, primary_key=True)

    MiejsocoscP = Column(Text)
    UlicaP = Column(Text)

    # ! extra space in column name
    KodPocztowyP = Column("KodPocztowyP ", Text)

    pracownicy = relationship("Pracownicy", back_populates="adres")



class AdrKlienta(Base):
    __tablename__ = "adrklienta"

    adrklientaid = Column(Integer, primary_key=True)

    miejscowosck = Column(String(50), nullable=False)
    ulica = Column(String(50), nullable=False)
    kodpocztowyk = Column(String(10))
    krajk = Column(String(20))

    klienci = relationship("Klient", back_populates="adres")


class Kategoria(Base):
    __tablename__ = "kategoria"

    kategoriaid = Column(Integer, primary_key=True)

    nazwa = Column(String(50))

    produkty = relationship("Produkt", back_populates="kategoria")


class Producent(Base):
    __tablename__ = "producent"

    producentid = Column(Integer, primary_key=True)

    nazwa = Column(String(50))
    kraj = Column(String(50))

    produkty = relationship("Produkt", back_populates="producent")


class Produkt(Base):
    __tablename__ = "produkt"

    produktid = Column(Integer, primary_key=True)

    nazwa = Column(String(255))
    cena = Column(Integer)
    stanmagazynowy = Column(Integer)

    kategoriaid = Column(
        Integer,
        ForeignKey("kategoria.kategoriaid")
    )

    producentid = Column(
        Integer,
        ForeignKey("producent.producentid")
    )

    kategoria = relationship("Kategoria", back_populates="produkty")

    producent = relationship("Producent", back_populates="produkty")

    zamowienie_produkty = relationship(
        "ZamowienieProdukty",
        back_populates="produkt"
    )


class Klient(Base):
    __tablename__ = "klient"

    klientid = Column(Integer, primary_key=True)

    adrklientid = Column(
        Integer,
        ForeignKey("adrklienta.adrklientaid")
    )

    imie = Column(String(50))
    nazwisko = Column(String(50))
    email = Column(String(30))
    telefon = Column(Integer)

    adres = relationship("AdrKlienta", back_populates="klienci")

    zamowienia = relationship("Zamowienie", back_populates="klient")


class Pracownicy(Base):
    __tablename__ = "pracownicy"

    pracownikid = Column(Integer, primary_key=True)

    imieprac = Column(String(50), nullable=False)
    nazwiskoprac = Column(String(50), nullable=False)

    adrpracownikid = Column(
        Integer,
        ForeignKey('AdrPracownikow.AdrPracownikID')
    )

    adres = relationship(
        "AdrPracownikow",
        back_populates="pracownicy"
    )

    zamowienia = relationship(
        "Zamowienie",
        back_populates="pracownik"
    )


class Platnosc(Base):
    __tablename__ = "platnosc"

    platnoscid = Column(Integer, primary_key=True)

    metoda = Column(String(50))
    status = Column(String(50))
    kwota = Column(Integer)

    zamowienieid = Column(
        Integer,
        ForeignKey("zamowienie.zamowienieid")
    )

    zamowienie = relationship(
        "Zamowienie",
        foreign_keys=[zamowienieid]
    )


class Zamowienie(Base):
    __tablename__ = "zamowienie"

    zamowienieid = Column(Integer, primary_key=True)

    klientid = Column(
        Integer,
        ForeignKey("klient.klientid")
    )

    data = Column(TIMESTAMP)

    status = Column(String(50))

    platnoscid = Column(
        Integer,
        ForeignKey("platnosc.platnoscid")
    )

    pracownikid = Column(
        Integer,
        ForeignKey("pracownicy.pracownikid")
    )

    klient = relationship(
        "Klient",
        back_populates="zamowienia"
    )

    pracownik = relationship(
        "Pracownicy",
        back_populates="zamowienia"
    )

    platnosc = relationship(
        "Platnosc",
        foreign_keys=[platnoscid]
    )

    produkty = relationship(
        "ZamowienieProdukty",
        back_populates="zamowienie"
    )


class ZamowienieProdukty(Base):
    __tablename__ = "zamowienie_produkty"

    zamowienieproduktid = Column(Integer, primary_key=True)

    ilosc = Column(Integer)

    produktid = Column(
        Integer,
        ForeignKey("produkt.produktid")
    )

    zamowienieid = Column(
        Integer,
        ForeignKey("zamowienie.zamowienieid")
    )

    produkt = relationship(
        "Produkt",
        back_populates="zamowienie_produkty"
    )

    zamowienie = relationship(
        "Zamowienie",
        back_populates="produkty"
    )
