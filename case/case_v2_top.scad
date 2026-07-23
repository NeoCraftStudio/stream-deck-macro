// Stream Deck Macro — top plate v2
// Shell reused from "MisteRdeck / Ocreeb DIY Macro Keypad" (printables.com),
// CC BY-SA — stretched, old holes filled, re-cut for our own 4x4+3-encoder layout.

// ---- Original reference dimensions (measured from the STL bounding box) ----
orig_min = [-3.5125, -3.4943];
orig_max = [84.5125, 90.5125];
orig_top_w = orig_max[0] - orig_min[0]; // 88.03
orig_top_d = orig_max[1] - orig_min[1]; // 94.01

// ---- Our new target layout ----
switch_hole   = 14;
switch_pitch  = 19.05;
grid_cols     = 4;
grid_rows     = 4;
grid_span     = (grid_cols - 1) * switch_pitch + switch_hole; // 71.15

encoder_d     = 7;       // placeholder — confirm with calipers before printing final
encoder_count = 3;
encoder_gap   = 30;

margin = 12;

new_top_w = margin*2 + grid_span + encoder_gap + encoder_d;
new_top_d = margin*2 + grid_span;

scale_x = new_top_w / orig_top_w;
scale_y = new_top_d / orig_top_d;

plug_inset = 3; // how far in from the original outer bounds the fill region starts

module scaled_shell() {
    scale([scale_x, scale_y, 1])
        import("reference/Case_Top.stl");
}

module deck_plug() {
    min_pt = [orig_min[0]*scale_x + plug_inset, orig_min[1]*scale_y + plug_inset];
    max_pt = [orig_max[0]*scale_x - plug_inset, orig_max[1]*scale_y - plug_inset];
    size = [max_pt[0]-min_pt[0], max_pt[1]-min_pt[1]];
    translate([min_pt[0], min_pt[1], -5])
        cube([size[0], size[1], 25]);
}

module new_switch_grid(origin_x, origin_y) {
    for (row = [0 : grid_rows - 1])
        for (col = [0 : grid_cols - 1])
            translate([origin_x + col*switch_pitch, origin_y + row*switch_pitch, -2])
                linear_extrude(height = 24)
                    square(switch_hole, center = true);
}

module new_encoder_column(origin_x, origin_y, grid_height) {
    spacing = grid_height / (encoder_count - 1);
    for (i = [0 : encoder_count - 1])
        translate([origin_x, origin_y + i*spacing, -2])
            linear_extrude(height = 24)
                circle(d = encoder_d, $fn = 48);
}

// ---- Assemble ----
grid_origin_x = margin + switch_hole/2;
grid_origin_y = margin + switch_hole/2;
grid_height_span = (grid_rows - 1) * switch_pitch;
encoder_x = grid_origin_x + (grid_cols - 1)*switch_pitch + switch_hole/2 + encoder_gap;

difference() {
    union() {
        scaled_shell();
        deck_plug();
    }
    new_switch_grid(grid_origin_x, grid_origin_y);
    new_encoder_column(encoder_x, grid_origin_y, grid_height_span);
}
