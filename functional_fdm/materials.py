"""Conservative material assumptions for early functional checks."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MaterialProfile:
    name: str
    elastic_modulus_mpa: float
    reusable_snap_strain: float
    one_time_snap_strain: float
    creep_sensitive: bool
    heat_caution_c: float
    notes: tuple[str, ...]


_MATERIALS = {
    "PLA": MaterialProfile(
        "PLA", 3000, 0.008, 0.012, True, 50,
        ("Rigid and dimensionally stable.", "Avoid repeated flexing and warm service."),
    ),
    "PETG": MaterialProfile(
        "PETG", 2000, 0.015, 0.025, True, 65,
        ("Useful default for tough functional parts.", "Check creep under permanent snap load."),
    ),
    "ABS": MaterialProfile(
        "ABS", 1900, 0.015, 0.025, True, 85,
        ("Tough and heat resistant.", "Account for shrinkage and warping."),
    ),
    "ASA": MaterialProfile(
        "ASA", 2000, 0.015, 0.025, True, 90,
        ("Good for UV and outdoor exposure.", "Account for shrinkage and warping."),
    ),
    "PA": MaterialProfile(
        "PA", 1500, 0.025, 0.040, True, 90,
        ("Tough and fatigue resistant.", "Dry before precision or mechanical printing."),
    ),
    "PC": MaterialProfile(
        "PC", 2300, 0.020, 0.035, True, 105,
        ("Strong and heat resistant.", "Requires controlled printing conditions."),
    ),
    "TPU": MaterialProfile(
        "TPU", 50, 0.100, 0.180, True, 55,
        ("Use for compliant mechanisms.", "Beam formulas for rigid plastics are only rough guides."),
    ),
}


def material_profile(name: str) -> MaterialProfile:
    key = name.upper().split("-")[0]
    if key == "NYLON":
        key = "PA"
    if key not in _MATERIALS:
        raise ValueError(f"No conservative material profile for {name!r}; provide measured properties.")
    return _MATERIALS[key]


def material_names() -> tuple[str, ...]:
    return tuple(_MATERIALS)
