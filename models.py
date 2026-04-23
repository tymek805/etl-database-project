from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Produkt(Base):
    __tablename__ = "produkt"

    produktid = Column(Integer, primary_key=True)
    nazwa = Column(String(255))
    cena = Column(Integer)
    stanmagazynowy = Column(Integer)
    kategoriaid = Column(Integer)
    producentid = Column(Integer)