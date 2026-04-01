from dataclasses import dataclass

STS_SENSOR_SIZE: dict[int, tuple[float, float]] = {
    0: (62, 22),
    1: (62, 22),
    2: (62, 42),
    3: (62, 62),
    4: (62, 124),
}

@dataclass(frozen=True)
class SensorType:
    """
    It holds the related information to a sensor type
    """
    id: int
    
    def size_xy(self)->tuple[float,float]:
        return STS_SENSOR_SIZE[int(self.id)]

if __name__ == "__main__":
    print(SensorType(3).size_xy())