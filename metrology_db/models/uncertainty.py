"""
This module defines the UncertaintyModel data model.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class UncertaintyModel:
    """
    Represents an uncertainty model in the metrology database.

    Attributes:
        model_id: The unique identifier for the model.
        name: The name of the model (e.g., ISO-GUM, MonteCarlo, Gaussian).
        description: A description of the model.
    """

    model_id: int
    name: str  # ISO-GUM, MonteCarlo, Gaussian
    description: Optional[str] = None
