// Stream Deck Macro — bottom plate v4 (tray with sliding wall)
// Slides up into the top piece's inner cavity from below. The tray's outer
// wall matches the top's inner hollow, minus a small per-side clearance so
// it can actually slide in once printed.

include <case_params.scad>

fit_clearance    = 0.25; // per-side gap for a sliding fit
floor_thickness  = 3;    // tray floor thickness
wall_thickness   = 2;    // tray's own perimeter wall thickness
wall_height      = 10;   // how tall the tray wall is (slides into the top's cavity)

bottom_w = (plate_w - 2*border) - 2*fit_clearance;
bottom_d = (plate_d - 2*border) - 2*fit_clearance;
bottom_chamfer = corner_chamfer * 0.6;

module arduino_mount() {
    // 3-sided retaining wall — left, right, and the far (low-Y) side —
    // left OPEN on the back (high-Y) side facing the USB cutout, so
    // there's nothing blocking cable clearance or sliding the board in
    // from that direction. Corner standoffs lift the board slightly off
    // the floor.
    z0 = floor_thickness;
    x0 = arduino_x_center - arduino_w/2;
    y0 = arduino_y_back - arduino_l;
    translate([x0 - arduino_wall_t, y0, z0])
        cube([arduino_wall_t, arduino_l, arduino_wall_h]);
    translate([x0 + arduino_w, y0, z0])
        cube([arduino_wall_t, arduino_l, arduino_wall_h]);
    translate([x0 - arduino_wall_t, y0 - arduino_wall_t, z0])
        cube([arduino_w + 2*arduino_wall_t, arduino_wall_t, arduino_wall_h]);
    standoff_size = 3;
    for (dx = [0, arduino_w - standoff_size])
        for (dy = [0, arduino_l - standoff_size])
            translate([x0 + dx, y0 + dy, z0])
                cube([standoff_size, standoff_size, arduino_standoff_h]);
}

module case_bottom() {
    translate([border + fit_clearance, border + fit_clearance, 0])
        difference() {
            linear_extrude(height = wall_height)
                chamfered_rect(bottom_w, bottom_d, bottom_chamfer);
            translate([wall_thickness, wall_thickness, floor_thickness])
                linear_extrude(height = wall_height)
                    chamfered_rect(bottom_w - 2*wall_thickness,
                                   bottom_d - 2*wall_thickness,
                                   max(bottom_chamfer - wall_thickness, 0.1));
            // USB cable notch through the TRAY'S OWN back wall — without
            // this, the wall added a few lines above (wall_thickness
            // thick) sits directly between the Arduino pocket and the
            // matching cutout in the mount's back wall, blocking the
            // cable path entirely. Reported directly: "the hole for the
            // cable is blocked for the back wall of the bottom."
            // bottom_w/2 in this LOCAL frame is exactly arduino_x_center
            // in world coordinates (border+fit_clearance cancels out),
            // so this lines up with the mount's cutout without needing
            // to duplicate that math.
            translate([bottom_w/2 - usb_cutout_w/2, bottom_d - wall_thickness - 1, floor_thickness])
                cube([usb_cutout_w, wall_thickness + 2, wall_height - floor_thickness + 1]);
        }
    arduino_mount();
}

case_bottom();
