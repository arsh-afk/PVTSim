"""Water quality sensors module.

Per P7-3: Sensor models for water quality monitoring.
"""

from __future__ import annotations

import random
from typing import Any, Dict, List, Optional


class WaterQualitySensor:
    """Base water quality sensor model."""

    def __init__(
        self,
        parameter: str,
        detection_limit: float,
        noise_percent: float,
        range_min: float = float("0.0"),
        range_max: float = float("1000.0"),
        drift_per_day: float = float("0.0"),
    ):
        self.parameter = parameter
        self.detection_limit = detection_limit
        self.noise_percent = noise_percent
        self.range_min = range_min
        self.range_max = range_max
        self.drift_per_day = drift_per_day
        self.days_since_calibration = float("0.0")
        self.bias = float("0.0")

    def read(self, true_value: float) -> float:
        """Simulate sensor reading."""
        # Apply drift
        self.bias += self.drift_per_day * self.days_since_calibration / float("365.0")

        # Detection limit
        if true_value < self.detection_limit:
            return self.detection_limit / float("2.0")

        # Add noise
        noise = random.gauss(float("0.0"), true_value * self.noise_percent / float("100.0"))
        reading = true_value + noise + self.bias

        # Clamp to range
        return max(self.range_min, min(self.range_max, reading))

    def calibrate(self, reference_value: float) -> None:
        """Calibrate sensor against reference."""
        self.bias = 0.0
        self.days_since_calibration = 0.0

    def advance_time(self, dt_days: float) -> None:
        """Advance time for drift accumulation."""
        self.days_since_calibration += dt_days


def create_sensor_suite(config: Dict[str, Any]) -> Dict[str, WaterQualitySensor]:
    """Create a suite of sensors from configuration."""
    sensors = {}

    for param, spec in config.items():
        sensors[param] = WaterQualitySensor(
            parameter=param,
            detection_limit=spec.get("detection_limit", float("0.0")),
            noise_percent=spec.get("noise_percent", float("5.0")),
            range_min=spec.get("range_min", float("0.0")),
            range_max=spec.get("range_max", float("1000.0")),
            drift_per_day=spec.get("drift_per_day", float("0.01")),
        )

    return sensors


def read_sensor_suite(
    sensors: Dict[str, WaterQualitySensor],
    true_quality: Dict[str, float],
) -> Dict[str, float]:
    """Read all sensors in suite."""
    readings = {}
    for param, sensor in sensors.items():
        if param in true_quality:
            readings[param] = sensor.read(true_quality[param])
    return readings


def calibrate_sensor_suite(
    sensors: Dict[str, WaterQualitySensor],
    reference_quality: Dict[str, float],
) -> Dict[str, float]:
    """Calibrate all sensors against reference values."""
    offsets = {}
    for param, sensor in sensors.items():
        if param in reference_quality:
            sensor.calibrate(reference_quality[param])
            offsets[param] = sensor.bias
    return offsets


def sensor_health_check(
    sensors: Dict[str, WaterQualitySensor],
    thresholds: Dict[str, Dict[str, float]],
) -> Dict[str, Dict[str, Any]]:
    """Check sensor health against thresholds."""
    health = {}
    for param, sensor in sensors.items():
        if param in thresholds:
            thresh = thresholds[param]
            health[param] = {
                "days_since_cal": sensor.days_since_calibration,
                "bias": sensor.bias,
                "needs_calibration": sensor.days_since_calibration > thresh.get("max_days", float("30.0")),
                "bias_exceeds": abs(sensor.bias) > thresh.get("max_bias", float("0.1")),
            }
    return health


def simulate_sensor_fouling(
    sensor: WaterQualitySensor,
    quality: Dict[str, float],
    dt_days: float,
    fouling_rate: float = float("0.001"),
) -> None:
    """Simulate sensor fouling increasing detection limit and noise."""
    # Fouling increases detection limit and noise over time
    sensor.detection_limit *= (1.0 + fouling_rate * dt_days)
    sensor.noise_percent *= (1.0 + fouling_rate * dt_days)
    sensor.drift_per_day *= (1.0 + fouling_rate * dt_days)
