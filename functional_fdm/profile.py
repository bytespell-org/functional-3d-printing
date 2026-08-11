"""Printer and material fit calibration profiles."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal


FitClass = Literal[
    "clearance",
    "loose-sliding",
    "close-sliding",
    "locating",
    "friction",
    "press",
]


@dataclass
class FitProfile:
    process: str = "FDM"
    printer: str = "unknown"
    nozzle_mm: float = 0.4
    material: str = "unknown"
    characterized: bool = False
    source: str = "conservative heuristic; use an approved small test for critical fits"
    clearance_per_side_mm: float = 0.30
    loose_sliding_per_side_mm: float = 0.25
    close_sliding_per_side_mm: float = 0.18
    locating_per_side_mm: float = 0.12
    friction_per_side_mm: float = 0.06
    press_interference_per_side_mm: float = 0.03
    hole_diameter_compensation_mm: float = 0.15
    external_dimension_compensation_mm: float = 0.0
    elephant_foot_allowance_mm: float = 0.20
    snap_clearance_per_side_mm: float = 0.30

    def __post_init__(self) -> None:
        if self.process.upper() != "FDM":
            raise ValueError("This profile supports only FDM.")
        if self.nozzle_mm <= 0:
            raise ValueError("nozzle_mm must be positive.")
        nonnegative = (
            "clearance_per_side_mm",
            "loose_sliding_per_side_mm",
            "close_sliding_per_side_mm",
            "locating_per_side_mm",
            "friction_per_side_mm",
            "press_interference_per_side_mm",
            "elephant_foot_allowance_mm",
            "snap_clearance_per_side_mm",
        )
        for name in nonnegative:
            if getattr(self, name) < 0:
                raise ValueError(f"{name} must not be negative.")

    def gap_per_side(self, fit: FitClass) -> float:
        return {
            "clearance": self.clearance_per_side_mm,
            "loose-sliding": self.loose_sliding_per_side_mm,
            "close-sliding": self.close_sliding_per_side_mm,
            "locating": self.locating_per_side_mm,
            "friction": self.friction_per_side_mm,
            "press": -self.press_interference_per_side_mm,
        }[fit]

    def mating_dimensions(self, nominal_mm: float, fit: FitClass) -> tuple[float, float]:
        """Return modeled male and female dimensions for a planar or diametral fit."""
        if nominal_mm <= 0:
            raise ValueError("nominal_mm must be positive.")
        male = nominal_mm + self.external_dimension_compensation_mm
        female = (
            nominal_mm
            + 2 * self.gap_per_side(fit)
            + self.hole_diameter_compensation_mm
        )
        if female <= 0:
            raise ValueError("The profile creates a non-positive female dimension.")
        return male, female

    def coupon_gaps(self, center_mm: float | None = None) -> list[float]:
        center = self.close_sliding_per_side_mm if center_mm is None else center_mm
        return [round(max(0.0, center + offset), 3) for offset in (-0.10, -0.05, 0, 0.05, 0.10)]

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2, sort_keys=True) + "\n", encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "FitProfile":
        return cls(**json.loads(path.read_text(encoding="utf-8")))

    def assumptions(self) -> dict[str, object]:
        return {
            "process": self.process,
            "printer": self.printer,
            "nozzle_mm": self.nozzle_mm,
            "material": self.material,
            "characterized": self.characterized,
            "source": self.source,
        }
