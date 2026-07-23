// Stream Deck Macro — top plate v4
// Outer shell style inspired by "MisteRdeck / Ocreeb DIY Macro Keypad"
// (printables.com) — fresh parametric geometry: chamfered-corner rim with a
// tapered top edge, and a recessed inner deck (like the original) for the
// switches, hollow underneath for switch body clearance.

include <case_params.scad>

module rim_shell() {
    // straight body
    linear_extrude(height = rim_height - bevel_height)
        chamfered_rect(plate_w, plate_d, corner_chamfer);
    // tapered top collar — centered before scaling so all 4 sides bevel evenly
    translate([plate_w/2, plate_d/2, rim_height - bevel_height])
        linear_extrude(height = bevel_height,
                       scale = [(plate_w - 2*bevel_inset) / plate_w,
                                (plate_d - 2*bevel_inset) / plate_d])
            translate([-plate_w/2, -plate_d/2])
                chamfered_rect(plate_w, plate_d, corner_chamfer);
}

module inner_hollow() {
    // full-depth opening inside the rim border, plus extra above/below to
    // guarantee clean cuts
    translate([border, border, -1])
        linear_extrude(height = rim_height + 2)
            chamfered_rect(plate_w - 2*border, plate_d - 2*border, corner_chamfer * 0.6);
}

module switch_deck() {
    // Slightly larger than the hollow it sits in, overlapping the wall by
    // `overlap` on every side — a flush, knife-edge touch is numerically
    // fragile for CSG union (esp. once one side gets a multmatrix applied
    // to it) and can leave the deck as a disconnected floating volume.
    overlap = 0.5;
    translate([border - overlap, border - overlap, rim_height - deck_recess - deck_thickness])
        linear_extrude(height = deck_thickness)
            chamfered_rect(plate_w - 2*border + 2*overlap, plate_d - 2*border + 2*overlap, corner_chamfer * 0.6);
}

module new_switch_grid(origin_x, origin_y) {
    for (row = [0 : grid_rows - 1])
        for (col = [0 : grid_cols - 1])
            translate([origin_x + col*switch_pitch, origin_y + row*switch_pitch, -2])
                linear_extrude(height = rim_height + 4)
                    square(switch_hole, center = true);
}

module new_encoder_column(origin_x, origin_y, grid_height) {
    spacing = grid_height / (encoder_count - 1);
    for (i = [0 : encoder_count - 1])
        translate([origin_x, origin_y + i*spacing, -2])
            linear_extrude(height = rim_height + 4)
                circle(d = encoder_d, $fn = 48);
}

grid_origin_x = margin + switch_hole/2;
grid_origin_y = margin + switch_hole/2;
grid_height_span = (grid_rows - 1) * switch_pitch;
encoder_x = grid_origin_x + (grid_cols - 1)*switch_pitch + switch_hole/2 + encoder_gap;

module case_top() {
    difference() {
        union() {
            difference() {
                rim_shell();
                inner_hollow();
            }
            switch_deck();
        }
        new_switch_grid(grid_origin_x, grid_origin_y);
        new_encoder_column(encoder_x, grid_origin_y, grid_height_span);
    }
}

// ---- Wedge tilt: flat bottom everywhere, walls + deck grow taller toward
// the back.
tilt_angle_deg = 30;
riser_height = plate_d * tan(tilt_angle_deg);   // ~54.93mm extra height at the back
shear_factor = riser_height / plate_d;
back_height = rim_height + riser_height;
deck_mid_z = rim_height - deck_recess - deck_thickness/2;   // flat-design deck centerline

module wedge_cutter(front_h) {
    // Half-space block whose top face is the plane z = y*shear_factor + front_h
    // — passes through (y=0, z=front_h).
    translate([0, 0, front_h])
        rotate([tilt_angle_deg, 0, 0])
            translate([-1000, -1000, -2000])
                cube([plate_w + 2000, plate_d + 2000, 2000]);
}

module wedge_straight_body() {
    // Front height stays at rim_height - bevel_height (same as the flat
    // design's straight body, below where its tapered collar used to start)
    // so it can never dip low enough to cut into the deck. +0.3 overlap into
    // the collar above, so the two pieces have real shared volume, not just
    // a knife-edge touch.
    intersection() {
        linear_extrude(height = back_height)
            chamfered_rect(plate_w, plate_d, corner_chamfer);
        wedge_cutter(rim_height - bevel_height + 0.3);
    }
}

module wedge_top_collar() {
    // Same tapered-collar shape as the flat design's rim_shell() bevel,
    // sheared by the same slope as everything else so it sits flush on top
    // of wedge_straight_body() at every y — thin (bevel_height=3mm), so the
    // shear reads as a clean taper here, not a stretched parallelogram like
    // it did on the full 20mm+ wall.
    // Uses offset() (a constant inward shrink per edge) instead of the flat
    // design's non-uniform X/Y scale — scaling by different factors in X and
    // Y (since plate_w != plate_d) skews the 45 degree corner chamfer at the
    // top out of alignment with the same chamfer below it, which reads as a
    // disconnected/kinked edge right where the collar meets the body.
    sheared()
    hull() {
        translate([0, 0, rim_height - bevel_height])
            linear_extrude(height = 0.01)
                chamfered_rect(plate_w, plate_d, corner_chamfer);
        translate([0, 0, rim_height])
            linear_extrude(height = 0.01)
                offset(delta = -bevel_inset)
                    chamfered_rect(plate_w, plate_d, corner_chamfer);
    }
}

module wedge_outer_shell() {
    difference() {
        union() {
            wedge_straight_body();
            wedge_top_collar();
        }
        translate([border, border, -1])
            linear_extrude(height = back_height + 2)
                chamfered_rect(plate_w - 2*border, plate_d - 2*border, corner_chamfer * 0.6);
    }
}

module sheared() {
    multmatrix([
        [1, 0, 0, 0],
        [0, 1, 0, 0],
        [0, shear_factor, 1, 0],
        [0, 0, 0, 1]
    ])
    children();
}

module tilted_hole(px, py) {
    // Places children (a vertical, centered hole prism) at (px, py) on the
    // deck's tilted surface, then rotates it in place so its axis is
    // perpendicular to the deck face — matching how a plate-mount switch or
    // encoder actually clips in, instead of punching straight down through a
    // slanted plate at an angle.
    translate([px, py, deck_mid_z + shear_factor * py])
        rotate([tilt_angle_deg, 0, 0])
            children();
}

module tilted_switch_grid(origin_x, origin_y) {
    for (row = [0 : grid_rows - 1])
        for (col = [0 : grid_cols - 1])
            tilted_hole(origin_x + col*switch_pitch, origin_y + row*switch_pitch)
                linear_extrude(height = 20, center = true)
                    square(switch_hole, center = true);
}

module tilted_encoder_column(origin_x, origin_y, grid_height) {
    spacing = grid_height / (encoder_count - 1);
    for (i = [0 : encoder_count - 1])
        tilted_hole(origin_x, origin_y + i*spacing)
            linear_extrude(height = 20, center = true)
                circle(d = encoder_d, $fn = 48);
}

module case_top_tilted() {
    difference() {
        union() {
            wedge_outer_shell();
            sheared() switch_deck();
        }
        tilted_switch_grid(grid_origin_x, grid_origin_y);
        tilted_encoder_column(encoder_x, grid_origin_y, grid_height_span);
    }
}

case_top_tilted();
