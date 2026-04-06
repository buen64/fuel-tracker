from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Session

import config

engine = create_engine(
    f"sqlite:///{config.DB_PATH}",
    connect_args={"check_same_thread": False},
)


class Base(DeclarativeBase):
    pass


class Station(Base):
    """Stammdaten einer Tankstelle (einmalig geladen, täglich aktualisiert)."""
    __tablename__ = "stations"

    id           = Column(String, primary_key=True)   # Tankerkönig UUID
    name         = Column(String)
    brand        = Column(String)
    street       = Column(String)
    house_number = Column(String)
    post_code    = Column(String)
    place        = Column(String)
    lat          = Column(Float)
    lng          = Column(Float)
    dist_km      = Column(Float)   # Entfernung zu Tostedt-Mitte


class Price(Base):
    """Einzelner Preissatz, viertelstündlich erfasst."""
    __tablename__ = "prices"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    station_id  = Column(String, ForeignKey("stations.id"), nullable=False, index=True)
    e5          = Column(Float)
    e10         = Column(Float)
    diesel      = Column(Float)
    recorded_at = Column(DateTime, nullable=False, index=True, default=datetime.now)


def init_db() -> None:
    Base.metadata.create_all(engine)


def get_session() -> Session:
    return Session(engine)
