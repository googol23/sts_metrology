# 1. Load all files in source directory
# 
# 2. Check for new files
# 2.1 Make a db loaded files list
# 2.2 Make diff vs current state
# 
# 3. Split current state folders files in up_to_date, modified, new
# 
# 4. Push new files measurements.
# 


import os
import logging
from pathlib import Path
from datetime import datetime
from tomllib import load
from typing import Optional, Tuple, Dict, List

import pandas as pd
from sqlalchemy.orm import Session

from models.db_raw_file import RawMeasurementFile
from models.db_measurement import Measurement
from models.db_marker import Marker
from utils.hashing import sha256_file

# ===== LOGGING SETUP =====
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===== CONFIG =====
SOURCE_PATH = Path(__file__).parent.parent / "sources"
MEASUREMENT_FILE_PATTERNS = {"_sensor", "_marker", "_surface"}

UNIT_FACE = ["D", "U"]
UNIT_SIDE = ["R", "L"]
def is_valid_ladder_name(name: str) -> bool:
    return (
        len(name) == 10
        and name[0].upper() == "L"
        and name[1].isdigit()
        and name[2] in UNIT_FACE
        and name[3] in UNIT_SIDE
        and name[4:].isnumeric()
    )

def list_files(source_path: str | os.PathLike) -> List[str]:
    """
    List all measurement files in the source directory.
    
    Scans the provided source directory and returns paths to all files
    with supported extensions that match measurement file patterns.
    
    Args:
        source_path: Path to the source directory (str or PathLike)
        
    Returns:
        List of full file paths to measurement files
        
    Raises:
        FileNotFoundError: If source_path does not exist
    """

    source_path = Path(source_path)
    
    if not source_path.exists():
        raise FileNotFoundError(f"Source path does not exist: {source_path}")
    
    if not source_path.is_dir():
        raise NotADirectoryError(f"Source path is not a directory: {source_path}")
    
    files = []
    
    try:
        for filepath in source_path.iterdir():
            if not filepath.is_file():
                continue
            
            # Check if filename matches measurement file patterns
            if any(pattern in filepath.name for pattern in MEASUREMENT_FILE_PATTERNS):
                
                # Ensure valid ladder name                
                if is_valid_ladder_name(filepath.name.split('_')[0]):
                    files.append(str(filepath))
                    logger.info(f"Found measurement file: {filepath.name}")
        
        logger.info(f"Found {len(files)} measurement file(s) in {source_path}")
        return sorted(files)
    
    except Exception as e:
        logger.error(f"Error listing files in {source_path}: {e}")
        raise

files = list_files(SOURCE_PATH)

COLUMN_NAMES = ["dx", "dy", "dz", "psi", "theta", "phi", "dx_err", "dy_err", "dz_err", "psi_err", "theta_err", "phi_err"]

def load_sensor_offsets(file: str) -> pd.DataFrame:
    with open(file) as f:
        l = f.readline()
        column_names = l.strip().split(":")
        print(column_names)

    df = pd.read_csv(file)
    
    print(df.head())
    return df
    
for f in files:
    if "_sensor" in f:
        load_sensor_offsets(f)
    
    
    