from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String
from .base import Base


class Unit(Base):
    __tablename__ = "units"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    symbol: Mapped[str]
    quantity: Mapped[str]

    measurements: Mapped[list["Measurement"]] = relationship(back_populates="unit")