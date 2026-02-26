from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, DateTime, Float, Text
from .base import Base


class Measurement(Base):
    __tablename__ = "measurements"

    id: Mapped[int] = mapped_column(primary_key=True)

    marker_id: Mapped[int] = mapped_column(ForeignKey("markers.id"))
    operator_id: Mapped[int] = mapped_column(ForeignKey("operators.id"))
    unit_id: Mapped[int] = mapped_column(ForeignKey("units.id"))
    uncertainty_model_id: Mapped[int] = mapped_column(
        ForeignKey("uncertainty_models.id")
    )
    raw_file_id: Mapped[int | None] = mapped_column(
        ForeignKey("raw_measurement_files.id")
    )

    x: Mapped[float] = mapped_column(Float)
    y: Mapped[float] = mapped_column(Float)
    z: Mapped[float] = mapped_column(Float)

    dx: Mapped[float]
    dy: Mapped[float]
    dz: Mapped[float]

    measured_at: Mapped[datetime] = mapped_column(DateTime)

    notes: Mapped[str | None] = mapped_column(Text)

    # Relationships
    marker: Mapped["Marker"] = relationship(back_populates="measurements")
    operator: Mapped["Operator"] = relationship(back_populates="measurements")
    unit: Mapped["Unit"] = relationship(back_populates="measurements")
    uncertainty_model: Mapped["UncertaintyModel"] = relationship(back_populates="measurements")
    raw_file: Mapped["RawMeasurementFile"] = relationship(back_populates="measurements")