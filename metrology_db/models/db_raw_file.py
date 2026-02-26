from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey, DateTime, Text
from .base import Base


class RawMeasurementFile(Base):
    __tablename__ = "raw_measurement_files"

    id: Mapped[int] = mapped_column(primary_key=True)
    uri: Mapped[str]
    sha256: Mapped[str]
    file_format: Mapped[str]

    created_at: Mapped[datetime] = mapped_column(DateTime)
    ingested_at: Mapped[datetime] = mapped_column(DateTime)

    operator_id: Mapped[int | None] = mapped_column(ForeignKey("operators.id"))
    notes: Mapped[str | None] = mapped_column(Text)

    operator: Mapped["Operator"] = relationship(back_populates="raw_files")
    measurements: Mapped[list["Measurement"]] = relationship(back_populates="raw_file")