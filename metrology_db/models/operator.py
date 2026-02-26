"""
This module defines the Operator data model.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Operator:
    """
    Represents an operator in the metrology database.

    Attributes:
        operator_id: The unique identifier for the operator.
        name: The name of the operator.
    """

    operator_id: int
    name: str
