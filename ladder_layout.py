import numpy as np
from dataclasses import dataclass, asdict
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import itertools

import psycopg2
from psycopg2.extras import RealDictCursor

from cf_support import CF_SUPPORT_TYPE
from sensor_type import SensorType
from generate_ladder_layout import get_latest_modules_for_ladder, get_conn_from_env

SENSOR_OVERLAP_Y = 4.2

@dataclass
class LadderLayout:
    """
    It holds the sensor types sorted bottom to top
    """
    sensor_types: list[SensorType]
    cutout_size: float = 0
    
    @property
    def n_sensors(self)->int:
        return len(self.sensor_types)
    
    @property
    def ladder_size_xy(self)->tuple[float, float]:
        ladder_size = np.sum(self.sensors_size_xy(), axis=0)
        return ladder_size[0], ladder_size[1] + self.cutout_size
        
    def sensors_size_xy(self)->np.ndarray:
        return np.array([s.size_xy() for s in self.sensor_types], dtype=np.float32)
    
    def sensor_positions(self) -> np.ndarray:
        """
        It calculate the nominal sensor positions based on nominal sensor overlap along y-axis.
        """
        sizes_t = self.sensors_size_xy()[int(0.5*self.n_sensors):]
        
        positions_y =  np.empty(shape=(self.n_sensors), dtype=np.float32)
        offset_y = 0.5 * self.cutout_size + 0.5*SENSOR_OVERLAP_Y if self.cutout_size > 0.2 else 0
        for idx in range(int(0.5*self.n_sensors)):
            y = offset_y + 0.5 * (sizes_t[idx][1] - SENSOR_OVERLAP_Y)
            offset_y = y + 0.5 * (sizes_t[idx][1] - SENSOR_OVERLAP_Y)

            positions_y[idx] = y
            positions_y[int(0.5*self.n_sensors) + idx] = -y
            
        positions_y.sort()
        return positions_y
    
    def draw(self) -> None:
        """
        Draw the ladder layout.
        """
        # Constants
        PLOT_DPI = 300
        
        COLOR_BY_SIZE = {
            22 : 'green',
            42 : 'cyan',
            62 : 'blue',
            124 : 'purple'
        }
            
        aspect_ratio = self.ladder_size_xy[1] / self.ladder_size_xy[0]
        
        # Create figure with proper dimensions
        fig_width_pxl = 3000  # Base width in inches
        fig_height_pxl = fig_width_pxl * aspect_ratio
        fig = plt.figure(figsize=(fig_width_pxl / PLOT_DPI, fig_height_pxl / PLOT_DPI), dpi=PLOT_DPI)
        plt.rcParams['axes.axisbelow'] = True

        # Create axes with proper dimensions
        ax = fig.add_subplot(111)
        ax.set_aspect('equal', 'box')
        ax.set_xlim(-2.5*self.ladder_size_xy[0], 2.5*self.ladder_size_xy[0])
        ax.set_ylim(-1.5*self.ladder_size_xy[1], 1.5*self.ladder_size_xy[1])
        ax.grid(True, which='both', color='gray', linestyle='--', linewidth=0.5, zorder=0)
        
        for spine in ax.spines.values():
            spine.set_linewidth(3)
        
        ax.tick_params(
            direction='in',      # ticks point inward
            length=6, width=1,   # optional tick size
            top=True,         # ticks on top
            right=True,       # ticks on right
            labelbottom=True,    # x-axis labels on bottom
            labeltop=True,      # x-axis labels on top
            labelleft=True,      # y-axis labels on left
            labelright=True,    # y-axis labels on right
            pad=-30              # negative padding moves labels inward
        )
                
        sizes = self.sensors_size_xy()
        positions_y = self.sensor_positions()

        for y, (w, h) in zip(positions_y, sizes):
            rect = Rectangle(
                (0 - 0.5 * w, y - 0.5 * h),
                w,
                h,
                fill=True,
                edgecolor='black',
                facecolor=COLOR_BY_SIZE[abs(h)],
                alpha=0.3
            )
            ax.add_patch(rect)
        
        ax.set_aspect('equal')
        ax.autoscale()
         
def sort_tb(values: list[str]) -> list[str]:
    def key(s: str):
        letter = s[5]
        digit = int(s[6])
        # print(letter, digit)
        if letter == "B":
            return (0, -digit)   # B first, descending digit
        else:  # T
            return (1, digit)    # T after, ascending digit

    return sorted(values, key=key)
        
def ladder_layout(ladder: str, conn: psycopg2.extensions.connection | None = None) -> LadderLayout:
    if conn is None:
        conn = get_conn_from_env()

    modules = get_latest_modules_for_ladder(ladder, conn)
    # Ensure sorting of modules from bottom to top
    modules = sort_tb(modules)
    
    if len(modules) % 2 != 0:
        raise ValueError(f"Ladder {ladder} module list is not symmetric")

    sensors: list[SensorType] = []

    with conn.cursor() as cur:
        for m in modules:
            if len(m) < 6:
                raise ValueError(f"Invalid module name length: {m}")
            
            cur.execute("""
                SELECT sensor_name
                FROM public.sts_module
                WHERE name = %s;
            """, (m,))
            row = cur.fetchone()
            # print(row["sensor_name"][-1])
            if not row:
                raise ValueError(f"Missing sensor size for module {m}")
            
            sensors.append(SensorType(int(row["sensor_name"][-1])))
    
    cf_support_type = int(ladder[-2:])
    return LadderLayout(sensors, cutout_size=CF_SUPPORT_TYPE[cf_support_type][4])

        
if __name__ == "__main__":
    l = LadderLayout([SensorType(3),SensorType(2),SensorType(0),SensorType(0),SensorType(2), SensorType(3)])
    l.draw()
    # print(l.ladder_size_xy)
    