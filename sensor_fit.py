from dataclasses import asdict, dataclass

import numpy as np


@dataclass(frozen=True)
class SensorFit:
    """
    It hold the result of fitting a set of sensor measurements to a SensorShape, including:
        - resulting SensorShape
        - residuals
        - alignment (residuals respect to nominal)
    """

    shape: SensorShape
    residuals: list[Point3D]
