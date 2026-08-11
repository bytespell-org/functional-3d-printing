// Portable functional FDM part template.
// Units: millimeters. Intended print face: Z = 0.

$fn = 96;
part = "test"; // [test,part]

nominal_width = 20;
nominal_depth = 12;
nominal_height = 8;
sliding_clearance = 0.25;
press_interference = 0.10;
wall = 1.8;
epsilon = 0.02; // Positive Boolean overlap. Do not use this as fit clearance.

assert(wall > 0, "wall must be positive");
assert(sliding_clearance >= 0, "sliding_clearance must not be negative");

module hardware_envelope(clearance = 0) {
  cube([
    nominal_width + 2 * clearance,
    nominal_depth + 2 * clearance,
    nominal_height + clearance
  ]);
}

module functional_part() {
  difference() {
    cube([
      nominal_width + 2 * (wall + sliding_clearance),
      nominal_depth + 2 * (wall + sliding_clearance),
      nominal_height + wall
    ]);
    translate([wall, wall, wall])
      hardware_envelope(sliding_clearance);
  }
}

module fit_test() {
  coupon_depth = min(nominal_depth, 8);
  intersection() {
    functional_part();
    cube([nominal_width + 2 * (wall + sliding_clearance), coupon_depth, nominal_height + wall]);
  }
}

if (part == "test") {
  fit_test();
} else if (part == "part") {
  functional_part();
} else {
  assert(false, str("Unknown part: ", part));
}
