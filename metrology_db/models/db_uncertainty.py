from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Text
from .base import Base


class UncertaintyModel(Base):
    __tablename__ = "uncertainty_models"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    measurements: Mapped[list["Measurement"]] = relationship(back_populates="uncertainty_model")