from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String
from .base import Base


class Marker(Base):
    __tablename__ = "markers"

    id: Mapped[int] = mapped_column(primary_key=True)
    description: Mapped[str] = mapped_column(String)

    measurements: Mapped[list["Measurement"]] = relationship(back_populates="marker")