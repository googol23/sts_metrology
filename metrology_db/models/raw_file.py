"""
This module defines the RawMeasurementFile data model.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class RawMeasurementFile:
    """
    Represents a raw measurement file in the metrology database.

    Attributes:
        file_id: The unique identifier for the file.
        uri: The URI of the file.
        sha256: The SHA256 hash of the file.
        file_format: The format of the file.
        created_at: The timestamp of when the file was created.
        ingested_at: The timestamp of when the file was ingested.
        operator_id: The unique identifier for the operator who ingested the file.
        notes: Any notes associated with the file.
    """

    file_id: int
    uri: str
    sha256: str
    file_format: str
    created_at: datetime
    ingested_at: datetime
    operator_id: Optional[int] = None
    notes: Optional[str] = None
