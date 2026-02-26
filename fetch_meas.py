import os
import re
from pathlib import Path
from typing import Iterator, Tuple, Dict, Any

import db_api as dbapi
import numpy as np

from matplotlib.patches import Rectangle

import clustering as clu


def fetch_ladders(source_dir: str = "", only_with_data: bool = True) -> Iterator[Tuple[str, Path]]:
    """Yield ladder measurement folders found in `source_dir`.

    Each yielded item is a tuple (ladder_name, Path(ladder_folder)).
    If ``only_with_data`` is True the generator yields only folders that contain
    both the ``<name>_marker.txt`` and ``<name>_surface.txt`` files. This
    avoids building large lists in memory and lets callers consume results
    lazily.
    """
    if source_dir == "":
        print("No source directory provided, using current working directory")
        source_dir = os.getcwd()

    src = Path(source_dir)
    pat = re.compile(r"^L\d[UD]L\d{6}$")
    ladder_folders = (p for p in src.iterdir() if p.is_dir() and pat.fullmatch(p.name))

    if not only_with_data:
        for ladder_folder in ladder_folders:
            yield (os.path.basename(ladder_folder), ladder_folder)
        return

    for ladder_folder in ladder_folders:
        l_name = os.path.basename(ladder_folder)
        meas_marker = os.path.join(ladder_folder, f"{l_name}_marker.txt")
        meas_surface = os.path.join(ladder_folder, f"{l_name}_surface.txt")
        if os.path.isfile(meas_marker) and os.path.isfile(meas_surface):
            yield (l_name, ladder_folder)

def validate_marker_file(path: Path) -> bool:
    """Validate the contents of a marker file.
    """
    if not path.is_file():
        return False
    if path.stat().st_size == 0:
        return False
    # Additional validation logic can be added here
    return True

def load_marker_data(path: Path) -> np.array:
    """Load marker data from a marker file.
    Assumptions:
    - File contains N rows
    - First row is a header
    - Each row contains 6 columns: X, Y, Z, DX, DY, DZ
    Returns:
    Numpy array of shape (N-1, 6) containing marker points data
    """
    if not validate_marker_file(path):
        raise ValueError(f"Invalid marker file: {path}")
    data = np.loadtxt(path, skiprows=1)
    if data.ndim == 1:
        data = data.reshape(1, -1)
    if data.shape[1] != 6:
        raise ValueError(f"Marker file {path} does not have 6 columns")
    return data

def validate_surface_file(path: Path) -> bool:
    """Validate the contents of a surface file.
    """
    if not path.is_file():
        return False
    if path.stat().st_size == 0:
        return False
    # Additional validation logic can be added here
    return True

def load_surface_data(path: Path):
    """"
    Load surface data from surface file.
    Assumptions:
    - File contains N rows
    - First row is a header: X/D:Y:Z:Zd
    - Each row contains 4 columns: X,Y,Z,DZ
    Returns:
    Numpy array of shape (N-1, 4) containing surface points data
    """
    if not validate_marker_file(path):
        raise ValueError(f"Invalid marker file: {path}")
    data = np.loadtxt(path, skiprows=1)

    if data.ndim == 1:
        data = data.reshape(1, -1)

    if data.shape[1] != 4:
        raise ValueError(f"Marker file {path} does not have 6 columns")
    return data

def fetch_measurements(ladder_id:str, folder:Path, use_markers:bool|None = True, use_surface:bool|None = False) -> dict[str,np.array]:
    """
    Fetch the measurement of a given ladder at the provided folder
    It organizes the measurements group by modules, facilitating the post-processing
    of individual sensor dataset.
    Parameters:
        ladder_id (str): ID of the ladder to process.
        folder (Path): Path to the ladder data folder.
    Returns:
        dict:
            key - modules_id
            val - np.array (shape N,3) of 3D points associated to markers and/or surface points measurements
    """
    # Get modules sorted from top to bottom
    modules = dbapi.get_ladder_modules(ladder_id, sorted=True)
    n_of_modules = len(modules)

    points = np.empty(shape=(0,3))

    if use_markers:
        validate_marker_file(folder / f"{ladder_id}_marker.txt")
        markers = load_marker_data(folder / f"{ladder_id}_marker.txt")

        # Calculate absolute marker position by adding nominal[:3] + relative[3:]
        m_points = markers[:, :3] + markers[:, 3:]

        points = np.vstack((points,m_points))

    if use_surface:
        validate_surface_file(folder / f"{ladder_id}_surface.txt")
        surface = load_surface_data(folder / f"{ladder_id}_surface.txt")

        # Calculate absolute surface measurements by adding Z deviation to nominal
        s_points = np.column_stack((surface[:, :2], surface[:, 2] + surface[:, 3]))

        points = np.vstack((points,s_points))

    # Swap x-y axis (table frame to CBM frame)
    points[:, [0, 1]] = points[:, [1, 0]]

    # Clustering
    labels, centers, _ = clu.constrained_agglomerative(points, n_of_cluster=n_of_modules, y_max=20)

    # sort labels by y coordinate of the cluster center
    cluster_ids = np.unique(labels)
    def y_sorted(m):
        return -centers[m][1]
    cluster_ids = sorted(cluster_ids, key=y_sorted)

    measurements: dict[str, np.ndarray] = {}
    for idx,cluster_id in enumerate(cluster_ids):
        module_id = modules[idx]
        data = points[labels == cluster_id]
        measurements[module_id] = data  # (n_points_in_cluster, 3)
    return measurements


if __name__ == "__main__":
    for ladder_id, folder in fetch_ladders("/u/dlmeas/STS/", True):
        print(ladder_id, folder)

        print(len(fetch_measurements(ladder_id, folder, True, True)))


