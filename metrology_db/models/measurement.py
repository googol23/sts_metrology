"""
This module defines the Measurement data model.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional


@dataclass(frozen=True)
class Measurement:
    """
    Represents a single measurement in the metrology database.

    Attributes:
        marker_id: The unique identifier for the marker.
        operator_id: The unique identifier for the operator.
        x: The x-coordinate of the measurement.
        y: The y-coordinate of the measurement.
        z: The z-coordinate of the measurement.
        dx: The uncertainty in the x-coordinate.
        dy: The uncertainty in the y-coordinate.
        dz: The uncertainty in the z-coordinate.
        unit_id: The unique identifier for the unit.
        uncertainty_model_id: The unique identifier for the uncertainty model.
        measured_at: The timestamp of when the measurement was taken.
        raw_file_id: The unique identifier for the raw file associated with the measurement.
        uncertainty_parameters: A dictionary of uncertainty parameters.
        notes: Any notes associated with the measurement.
    """

    marker_id: int
    operator_id: int

    x: float
    y: float
    z: float

    dx: float
    dy: float
    dz: float

    unit_id: int
    uncertainty_model_id: int

    measured_at: datetime
    raw_file_id: Optional[int] = None
    uncertainty_parameters: Optional[Dict] = None
    notes: Optional[str] = None
