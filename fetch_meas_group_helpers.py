"""Helper utilities for grouping measurement points to sensor shapes.

This file is created as a small companion module with pure helpers so it's easy to
unit test independently from the main file. If you prefer I can inline these into
`fetch_meas.py` instead.
"""
from __future__ import annotations
import math
from typing import List
import numpy as np
from matplotlib.patches import Rectangle
from fetch_meas import SensorShape


def distance_point_to_rect_2d(px: float, py: float, rect_ll: tuple[float,float], width: float, height: float) -> float:
    """Compute shortest distance between a 2D point and an axis-aligned rectangle.

    Returns 0.0 if the point lies inside the rectangle.
    """
    x0, y0 = rect_ll
    rx0, rx1 = x0, x0 + width
    ry0, ry1 = y0, y0 + height
    dx = 0.0
    if px < rx0:
        dx = rx0 - px
    elif px > rx1:
        dx = px - rx1
    dy = 0.0
    if py < ry0:
        dy = ry0 - py
    elif py > ry1:
        dy = py - ry1
    return math.hypot(dx, dy)


def assign_points_to_sensor_shapes(points: np.ndarray, sensor_shapes: List[SensorShape]) -> dict[int, list[np.ndarray]]:
    """Assign each 3D point to the index of the nearest sensor shape in XY plane.

    Parameters:
        points: (N,3) numpy array of XYZ points
        sensor_shapes: list of SensorShape instances

    Returns:
        dict mapping sensor index -> list of points (each as numpy array)
    """
    if points is None or len(points) == 0:
        return {i: [] for i in range(len(sensor_shapes))}

    assigned: dict[int, list[np.ndarray]] = {i: [] for i in range(len(sensor_shapes))}
    for p in points:
        px, py = float(p[0]), float(p[1])
        best_idx = None
        best_dist = float('inf')
        for i, s in enumerate(sensor_shapes):
            ll = s.lower_left
            d = distance_point_to_rect_2d(px, py, ll, s.width, s.height)
            if d < best_dist:
                best_dist = d
                best_idx = i
        # best_idx will always be set when sensor_shapes non-empty
        assigned[best_idx].append(p)
    return assigned
