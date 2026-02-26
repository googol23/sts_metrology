"""
This module defines the Marker data model.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Marker:
    """
    Represents a marker in the metrology database.

    Attributes:
        marker_id: The unique identifier for the marker.
        description: A description of the marker.
    """
    marker_id: int
    description: str
