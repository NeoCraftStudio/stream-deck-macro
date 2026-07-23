// Stream Deck Macro — shared case dimensions (included by top/bottom/assembly)

// ---- Our target layout ----
switch_hole   = 14;
switch_pitch  = 19.05;
grid_cols     = 4;
grid_rows     = 4;
grid_span     = (grid_cols - 1) * switch_pitch + switch_hole; // 71.15

encoder_d     = 7;       // placeholder — confirm with calipers before printing final
encoder_count = 3;
encoder_gap   = 15;

margin = 12;

// ---- Shell style ----
corner_chamfer = 6;    // diagonal cut on each of the 4 corners
rim_height     = 20;   // total wall height (top to bottom), 2cm per feedback
bevel_height   = 3;    // top tapered collar height
bevel_inset    = 3;    // how far the top face is inset from the outer wall
border         = 6;    // rim wall thickness (outer edge to inner hollow)
deck_recess    = 2.5;  // how far below the rim top the switch deck sits
deck_thickness = 2.5;  // thickness of the switch deck floor

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
