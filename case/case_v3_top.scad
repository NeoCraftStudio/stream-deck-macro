// Stream Deck Macro — top plate v3
// Outer shell style inspired by "MisteRdeck / Ocreeb DIY Macro Keypad"
// (printables.com) — rebuilt as fresh parametric geometry (not scaled from
// their mesh) so the corner chamfer / edge bevel stays a clean, uniform
// angle instead of distorting under non-uniform stretching.

// ---- Our target layout ----
switch_hole   = 14;
switch_pitch  = 19.05;
grid_cols     = 4;
grid_rows     = 4;
grid_span     = (grid_cols - 1) * switch_pitch + switch_hole; // 71.15

encoder_d     = 7;       // placeholder — confirm with calipers before printing final
encoder_count = 3;
encoder_gap   = 30;

margin = 12;

// ---- Shell style ----
corner_chamfer = 6;   // diagonal cut on each of the 4 corners
body_height    = 14;  // main straight wall height
bevel_height   = 4;   // top tapered collar height
bevel_inset    = 4;   // how far the top face is inset from the outer wall

plate_w = margin*2 + grid_span + encoder_gap + encoder_d;
plate_d = margin*2 + grid_span;

module chamfered_rect(w, d, c) {
    polygon(points = [
        [c, 0], [w - c, 0],
        [w, c], [w, d - c],
        [w - c, d], [c, d],
        [0, d - c], [0, c]
    ]);
}

module shell() {
    // straight body
    linear_extrude(height = body_height)
        chamfered_rect(plate_w, plate_d, corner_chamfer);
    // tapered top collar (the "angular smoothing" edge)
    translate([0, 0, body_height])
        linear_extrude(height = bevel_height,
                       scale = [(plate_w - 2*bevel_inset) / plate_w,
                                (plate_d - 2*bevel_inset) / plate_d])
            chamfered_rect(plate_w, plate_d, corner_chamfer);
}

module new_switch_grid(origin_x, origin_y) {
    for (row = [0 : grid_rows - 1])
        for (col = [0 : grid_cols - 1])
            translate([origin_x + col*switch_pitch, origin_y + row*switch_pitch, -2])
                linear_extrude(height = body_height + bevel_height + 4)
                    square(switch_hole, center = true);
}

module new_encoder_column(origin_x, origin_y, grid_height) {
    spacing = grid_height / (encoder_count - 1);
    for (i = [0 : encoder_count - 1])
        translate([origin_x, origin_y + i*spacing, -2])
            linear_extrude(height = body_height + bevel_height + 4)
                circle(d = encoder_d, $fn = 48);
}

grid_origin_x = margin + switch_hole/2;
grid_origin_y = margin + switch_hole/2;
grid_height_span = (grid_rows - 1) * switch_pitch;
encoder_x = grid_origin_x + (grid_cols - 1)*switch_pitch + switch_hole/2 + encoder_gap;

difference() {
    shell();
    new_switch_grid(grid_origin_x, grid_origin_y);
    new_encoder_column(encoder_x, grid_origin_y, grid_height_span);
}
