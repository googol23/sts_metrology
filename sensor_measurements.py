import numpy as np
from dataclasses import dataclass, asdict
import json

@dataclass(frozen=True)
class Point3D:
    """
    Represents a single 3D point measuremnt
    """
    x: float
    y: float
    z: float
    x_err: float
    y_err: float
    z_err: float
    
    # ============ Serialization Methods ============
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Point3D':
        """Create from dictionary"""
        return cls(**data)
    
    def to_json(self) -> str:
        """Serialize to JSON string"""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Point3D':
        """Deserialize from JSON string"""
        return cls.from_dict(json.loads(json_str))
    
    def to_numpy(self) -> np.ndarray:
        """Convert to numpy array [x, y, z, x_err, y_err, z_err]"""
        return np.array([self.x, self.y, self.z, self.x_err, self.y_err, self.z_err])
    
    @classmethod
    def from_numpy(cls, arr: np.ndarray) -> 'Point3D':
        """Create from numpy array"""
        return cls(*arr)
    
    def to_bytes(self) -> bytes:
        """Convert to binary format (numpy binary)"""
        return self.to_numpy().tobytes()
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'Point3D':
        """Create from binary data"""
        arr = np.frombuffer(data, dtype=np.float64, count=6)
        return cls.from_numpy(arr)
        
   
@dataclass(frozen=True)
class SensorMeasurements:
    """
    Represents a set of metrology measurement for a sensor onto a ladder.

    It holds:
        - surface measurements
        - markers measurements
    """
    markers: list[Point3D]
    surface: list[Point3D]
    
    # ============ Array Conversion ============
    def markers_np_array(self) -> np.ndarray:
        """Convert markers to numpy array using vectorized stack"""
        if not self.markers:
            return np.empty((0, 6), dtype=np.float64)
        return np.column_stack([
            [p.x for p in self.markers],
            [p.y for p in self.markers],
            [p.z for p in self.markers],
            [p.x_err for p in self.markers],
            [p.y_err for p in self.markers],
            [p.z_err for p in self.markers]
        ])
    
    def surface_np_array(self) -> np.ndarray:
        """Convert surface points to numpy array using vectorized stack"""
        if not self.surface:
            return np.empty((0, 6), dtype=np.float64)
        return np.column_stack([
            [p.x for p in self.surface],
            [p.y for p in self.surface],
            [p.z for p in self.surface],
            [p.x_err for p in self.surface],
            [p.y_err for p in self.surface],
            [p.z_err for p in self.surface]
        ])
    
    def all_points_np_array(self) -> np.ndarray:
        """Combine all points (markers + surface) into single array"""
        markers_arr = self.markers_np_array()
        surface_arr = self.surface_np_array()
        return np.vstack([markers_arr, surface_arr]) if len(surface_arr) > 0 else markers_arr
