"""Typed input, policy, and interval contracts."""

from dataclasses import dataclass
from datetime import datetime
from math import isfinite


@dataclass(frozen=True)
class Config:
    max_gap_s: float = 5.0
    moving_threshold_kmh: float = 1.0
    minimum_voltage_v: float = 1.0
    shutdown_voltage_v: float = 10.0
    window_s: float = 60.0
    minimum_window_coverage: float = 0.9
    acceleration_threshold_mps2: float = 0.5
    seed: int = 42

    def __post_init__(self) -> None:
        positive = (self.max_gap_s, self.minimum_voltage_v, self.shutdown_voltage_v, self.window_s,
                    self.acceleration_threshold_mps2)
        if any(not isfinite(v) or v <= 0 for v in positive):
            raise ValueError("Gap, voltage, window and acceleration thresholds must be positive.")
        if not isfinite(self.moving_threshold_kmh) or self.moving_threshold_kmh < 0:
            raise ValueError("Moving threshold must be finite and nonnegative.")
        if not 0 < self.minimum_window_coverage <= 1:
            raise ValueError("Window coverage must be in (0, 1].")


@dataclass(frozen=True)
class Sample:
    source_row: int
    timestamp: datetime
    speed_kmh: float
    trip_km: float
    voltage_v: float
    current_a: float
    power_w: float
    latitude: float
    longitude: float
    timestamp_original: str
    retroceso_detectado: str
    segmento: str


@dataclass(frozen=True)
class Interval:
    left: Sample
    right: Sample
    start_s: float
    end_s: float
    valid: bool
    reasons: tuple[str, ...]
    moving_threshold_kmh: float
    # Fractions locate clipped windows within the original interval.
    fraction_start: float = 0.0
    fraction_end: float = 1.0

    @property
    def duration_s(self) -> float:
        return self.end_s - self.start_s

    def value(self, field: str, fraction: float, *, consumption: bool = False) -> float:
        a, b = getattr(self.left, field), getattr(self.right, field)
        if consumption:
            a, b = max(a, 0.0), max(b, 0.0)
        return a + (b - a) * fraction
