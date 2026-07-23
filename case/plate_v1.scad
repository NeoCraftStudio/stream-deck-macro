// Stream Deck Macro — top plate, v1
// Inspired by MisteRdeck (printables.com/model/134529) layout concept only —
// no files/geometry copied, built fresh for our own parts.

// === Parameters (all adjustable) ===
switch_hole    = 14;     // Outemu plate-mount square cutout, mm
switch_pitch   = 19.05;  // standard MX-compatible keycap spacing, mm
grid_cols      = 4;
grid_rows      = 4;

encoder_hole_d = 7;      // EC11 threaded bushing diameter — PLACEHOLDER, measure real part
encoder_count  = 3;
encoder_gap    = 30;     // gap from switch grid edge to encoder column, mm

margin         = 12;     // plate edge margin, mm
plate_thickness = 3;     // mm

screw_hole_d   = 2.8;    // M3 self-tapping pilot hole, mm
screw_inset    = 7;      // distance from plate edge to screw center, mm

// === Derived ===
grid_width  = (grid_cols - 1) * switch_pitch;
grid_height = (grid_rows - 1) * switch_pitch;

plate_width  = grid_width + switch_hole + encoder_gap + encoder_hole_d + margin * 2;
plate_height = grid_height + switch_hole + margin * 2;

module switch_grid() {
    for (row = [0 : grid_rows - 1])
        for (col = [0 : grid_cols - 1])
            translate([col * switch_pitch, row * switch_pitch])
                square(switch_hole, center = true);
}

module encoder_column() {
    x = grid_width + switch_hole / 2 + encoder_gap;
    spacing = grid_height / (encoder_count - 1);
    for (i = [0 : encoder_count - 1])
        translate([x, i * spacing])
            circle(d = encoder_hole_d, $fn = 48);
}

module screw_holes() {
    x0 = -margin + screw_inset;
    x1 = grid_width + switch_hole + encoder_gap + encoder_hole_d + margin - screw_inset;
    y0 = -margin + screw_inset;
    y1 = grid_height + margin - screw_inset;
    positions = [[x0, y0], [x1, y0], [x0, y1], [x1, y1]];
    for (p = positions)
        translate(p) circle(d = screw_hole_d, $fn = 32);
}

module plate_outline() {
    translate([-margin, -margin])
        square([plate_width, plate_height]);
}

module plate_2d() {
    difference() {
        plate_outline();
        switch_grid();
        encoder_column();
        screw_holes();
    }
}

linear_extrude(height = plate_thickness)
    plate_2d();
