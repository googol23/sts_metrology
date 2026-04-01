# ===== LOGGING SETUP =====
import logging
import os
import sys
from pathlib import Path


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from ladder_measurement import LadderMeasurement
from ladder_name import is_valid_ladder_name

global source_path
source_path = Path(__file__).parent.parent / "sources"

MEASUREMENT_FILE_PATTERNS = {"_sensor", "_marker", "_surface"}


def list_files(
    source_path: str | os.PathLike,
) -> tuple[Path | None, Path | None, Path | None]:
    """
    List all measurement files in the source directory.
    """
    source_path = Path(source_path)

    if not source_path.exists():
        raise FileNotFoundError(f"Source path does not exist: {source_path}")

    if not source_path.is_dir():
        raise NotADirectoryError(f"Source path is not a directory: {source_path}")

    markers_file: Path | None = None
    surface_file: Path | None = None
    sensor_file: Path | None = None

    try:
        for filepath in source_path.iterdir():
            if not filepath.is_file():
                continue

            if not is_valid_ladder_name(filepath.stem.split("_")[0]):
                continue

            if "_marker" in filepath.name:
                markers_file = filepath
            elif "_surface" in filepath.name:
                surface_file = filepath
            elif "_sensor" in filepath.name:
                sensor_file = filepath

    except Exception as e:
        logger.error(f"Error listing files in {source_path}: {e}")
        raise

    return markers_file, surface_file, sensor_file


def find_ladder_folders(source_path: str | os.PathLike) -> list[str] | None:
    source_path = Path(source_path)

    if not source_path.exists():
        raise FileNotFoundError(f"Source path does not exist: {source_path}")

    if not source_path.is_dir():
        raise NotADirectoryError(f"Source path is not a directory: {source_path}")

    ladders_sources_paths = []
    try:
        for filepath in source_path.iterdir():
            if not filepath.is_dir():
                continue

            # Check if directory name matches a valid ladder name pattern
            if is_valid_ladder_name(filepath.name):
                ladders_sources_paths.append(filepath)

        return sorted(ladders_sources_paths)

    except Exception as e:
        logger.error(f"Error listing files in {source_path}: {e}")
        raise


def make_ladder_folder(folder_name: str | Path) -> Path:
    path = Path(folder_name)
    path.mkdir(parents=True, exist_ok=True)
    return path


if __name__ == "__main__":
    global output_path

    source_path = Path("/u/dlmeas/STS/")
    output_path = Path("output")

    ladder_folders = find_ladder_folders(source_path)

    if ladder_folders is None:
        logger.info(f"No ladder folders found at {source_path}")
        sys.exit()

    for folder in ladder_folders[:30]:
        folder = Path(folder)
        files = list_files(folder)

        if any(f is None for f in files):
            logger.debug(f"Incomplete data set for {folder}")
            continue

        print(f"{folder}: {files}\n")

        # Create empty folder to store temporal
        ladder_output_folder = output_path / folder.name
        make_ladder_folder(ladder_output_folder)

        markers, surface, sensor = files

        assert markers is not None
        assert surface is not None
        assert sensor is not None

        lm = LadderMeasurement.load(folder.name, markers, surface)
        _ = lm.sensor_measurements(ladder_output_folder)
