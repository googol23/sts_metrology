from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String
from .base import Base
from .measurement import Measurement
from .db_raw_file import RawMeasurementFile

class Operator(Base):
    __tablename__ = "operators"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)

    measurements: Mapped[list["Measurement"]] = relationship(back_populates="operator")
    raw_files: Mapped[list["RawMeasurementFile"]] = relationship(back_populates="operator")