"""Reusable functional FDM feature primitives."""

from .enclosure import enclosure_shell, screw_lid, snap_lid
from .fasteners import (
    captive_nut_hole,
    clearance_hole,
    heat_set_insert_hole,
    heat_set_insert_boss,
    pcb_standoff,
    printed_thread_pair,
    self_tapping_boss,
)
from .fits import fit_coupon, fit_pair
from .joints import (
    annular_snap_pair,
    cantilever_snap,
    dovetail_pair,
    living_hinge,
    pin_hinge_pair,
    sliding_rail_pair,
    tongue_and_groove_pair,
    u_snap,
)
from .magnets import magnet_pocket

__all__ = [
    "annular_snap_pair",
    "cantilever_snap",
    "captive_nut_hole",
    "clearance_hole",
    "dovetail_pair",
    "enclosure_shell",
    "fit_coupon",
    "fit_pair",
    "heat_set_insert_hole",
    "heat_set_insert_boss",
    "living_hinge",
    "magnet_pocket",
    "pcb_standoff",
    "printed_thread_pair",
    "pin_hinge_pair",
    "self_tapping_boss",
    "screw_lid",
    "sliding_rail_pair",
    "snap_lid",
    "tongue_and_groove_pair",
    "u_snap",
]
