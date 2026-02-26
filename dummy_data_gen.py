import pandas as pd
from .sensor_shape import SensorShape

COLUMN_NAMES = ["dx", "dy", "dz", "psi", "theta", "phi", "dx_err", "dy_err", "dz_err", "psi_err", "theta_err", "phi_err"]

def gen_ladder_data()->list(SensorShape)