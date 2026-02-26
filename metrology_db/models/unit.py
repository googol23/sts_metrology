"""
This module defines the Unit data model.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Unit:
    """
    Represents a unit in the metrology database.

    Attributes:
        unit_id: The unique identifier for the unit.
        name: The name of the unit (e.g., millimeter).
        symbol: The symbol of the unit (e.g., mm).
        quantity: The quantity the unit measures (e.g., length).
    """

    unit_id: int
    name: str  # e.g. millimeter
    symbol: str  # e.g. mm
    quantity: str  # e.g. length
