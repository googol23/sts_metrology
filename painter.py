# Constants
PLOT_DPI = 300
PLOT_X_LIMITS = (-80, 80) # in mm

COLOR_BY_SIZE = {
    22 : 'green',
    42 : 'cyan',
    62 : 'blue',
    124 : 'purple'
}

DATA_PATH = "/u/dlmeas/STS/"

import logging
from pathlib import Path
from typing import List, Tuple, Optional

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from fetch_meas import fetch_ladders, fetch_measurements
import db_api as dbapi

import clustering as clu

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def paint_sensor(position: tuple[float,float] | None = (0, 0), size_x: float = 0, size_y: float = 0,ax: Axes | None = None) -> None:
    """Paint rectangle representing sensor edges and fill color based on size.

    Parameters:
        size_x (float): Width of the sensor in mm.
        size_y (float): Height of the sensor in mm.
        offset_x (float, optional): X offset of the sensor center from origin. Defaults to 0.
        offset_y (float, optional): Y offset of the sensor center from origin. Defaults to 0.
        ax (Optional[Axes], optional): Matplotlib Axes object. If None, uses current axes.

    Returns:
        None
    """
    if ax is None:
        ax = plt.gca()

    rect = Rectangle(
        position,
        size_x,
        size_y,
        fill=True,
        edgecolor='black',
        facecolor=COLOR_BY_SIZE[abs(size_y)],
        alpha=0.3,
    )
    ax.add_patch(rect)

def paint_module_group(modules: List[str], inverted: bool = False, ax: Axes | None = None) -> None:
    """Paint a group of modules with consistent spacing.

    Args:
        modules: List of module IDs to paint
        inverted: If True, paint modules inverted (for bottom modules)
    """
    sign = -1 if inverted else 1
    offset_y = -sign * 0.5*dbapi.SENSOR_OVERLAP

    for module in modules:
        size = dbapi.STS_SENSOR_SIZE[dbapi.get_module_sensor(module)[-1]]
        position = (-0.5*size[0], offset_y)

        paint_sensor(position, size[0], sign * size[1], ax=ax)
        offset_y += sign * (size[1] - dbapi.SENSOR_OVERLAP)

def paint_ladder(ladder_id:str):
    """
    Paint the sensors of a ladder and save the plot as an image.
    Parameters:
        ladder_id (str): ID of the ladder to paint.
    Returns:
        matplotlib axis
    """
    try:
        modules = dbapi.get_ladder_modules(ladder_id, sorted=True)
        n_of_modules = len(modules)
        top_modules, bot_modules = modules[:n_of_modules // 2][::-1], modules[n_of_modules // 2:]

        if n_of_modules % 2 != 0:
            raise ValueError(f"Ladder {ladder_id} has an odd number of modules: {len(modules)}")

        ladder_size_y = dbapi.compute_ladder_size_xy(ladder_id)[1]

        # Calculate data aspect ratio
        aspect_ratio = ladder_size_y / (PLOT_X_LIMITS[1] - PLOT_X_LIMITS[0])

        # Create figure with proper dimensions
        fig_width_pxl = 800  # Base width in inches
        fig_height_pxl = fig_width_pxl * aspect_ratio
        fig = plt.figure(figsize=(fig_width_pxl / PLOT_DPI, fig_height_pxl / PLOT_DPI), dpi=PLOT_DPI)
        plt.rcParams['axes.axisbelow'] = True

        # Create axes with proper dimensions
        ax = fig.add_subplot(111)
        ax.set_aspect('equal', 'box')
        ax.set_xlim(*PLOT_X_LIMITS)
        ax.set_ylim(-0.5*ladder_size_y, 0.5*ladder_size_y)
        ax.grid(True, which='both', color='gray', linestyle='--', linewidth=0.5, zorder=0)
        for spine in ax.spines.values():
            spine.set_linewidth(3)  # change 2 to whatever thickness you want
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

        # Paint modules
        paint_module_group(top_modules, ax=ax)
        paint_module_group(bot_modules, inverted=True, ax=ax)

        return n_of_modules
    except Exception as e:
        logger.error(f"Error painting ladder {ladder_id}: {repr(e)}")

    return None

def process_ladder(ladder_id: str, folder: Path) -> None:
    """Process a single ladder and generate its sensor visualization.

    Parameters:
        ladder_id (str): ID of the ladder to process.
        folder (Path): Path to the ladder data folder.

    Returns:
        None
    """
    try:
        # Paint ladder sensors
        paint_ladder(ladder_id)

        # Retrieve data
        measurements = fetch_measurements(ladder_id, folder, use_markers=True, use_surface=False)

        # Paint points
        for module_id, pts in measurements.items():
            plt.scatter(pts[:, 0], pts[:, 1], marker='s', s=10, label=module_id, zorder=10)
            plt.scatter(pts[:, 0], pts[:, 1], marker='+', s= 8, label=module_id, zorder=10, color='black', linewidth=0.2)
        # plt.legend(markerscale=2, fontsize=8)
        plt.savefig(f"{ladder_id}_sensors.png", bbox_inches='tight', pad_inches=0.01)
        logger.info(f"Generated plot for ladder {ladder_id}")
        plt.close()

    except Exception as e:
        logger.error(f"Error processing ladder {ladder_id}: {repr(e)}")


if __name__ == "__main__":
    try:
        for ladder_id, folder in fetch_ladders(DATA_PATH, True):
            logger.info(f"Processing ladder {ladder_id} in folder {folder}")
            process_ladder(ladder_id, folder)
            break

    except Exception as e:
        logger.error(f"Fatal error in main execution: {str(e)}")