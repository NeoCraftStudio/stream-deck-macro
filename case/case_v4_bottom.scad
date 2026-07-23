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
        }
}

case_bottom();
