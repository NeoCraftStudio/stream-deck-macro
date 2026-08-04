// Stream Deck Macro — shared case dimensions (included by top/bottom/assembly)

// ---- Our target layout ----
switch_hole   = 14;
switch_pitch  = 19.05;
grid_cols     = 4;
grid_rows     = 4;
grid_span     = (grid_cols - 1) * switch_pitch + switch_hole; // 71.15

encoder_d     = 7;       // CONFIRMED two ways: caliper-measured on the actual purchased part,
                          // and matches the encoder's own spec — Keszoox's EC11 datasheet states
                          // "Panel Mount — M7 thread fits standard 7mm panel holes with included
                          // nut" for this exact family (EC11, 15mm shaft, half/D-shaft — matches
                          // the purchased "G 15mm Half handle" spec). No longer a placeholder.
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

// switch_hole (14mm) and switch_pitch (19.05mm) are the universal Cherry
// MX-compatible plate-mount standard — every mechanical switch
// manufacturer uses this same spacing, Outemu (the purchased switch,
// "Dustproof Brown") included. Not brand-specific, so there's nothing to
// confirm against the specific part the way encoder_d needed — this was
// already correct.

plate_w = margin*2 + grid_span + encoder_gap + encoder_d;
plate_d = margin*2 + grid_span;

// ---- Arduino Pro Micro mount (off-the-shelf part) ----
// CONFIRMED (AliExpress order, seller A+A+A Store): "MICRO/MINI/TYPE-C USB
// Pro Micro para arduino ATmega32U4", ordered as TYPE-C USB 5V/16MHz — NOT
// Micro-USB, correcting an earlier assumption this file was built around.
// Board size still web-sourced, not caliper-measured: multiple listings
// (Probots, Envistia Mall, Makers Electronics) cite ~33x18mm for this
// family; Keebio notes the USB-C variant specifically runs ~3mm longer
// than the Micro-USB version (~36mm) because of the connector footprint.
// arduino_l=38 already covers that with ~2mm to spare. Confirm with
// calipers before printing final — same convention as encoder_d.
//
// USB-C connector: standard panel-mount cutout per connector datasheets is
// 12mm x 8.4mm (the bare plug shell is ~8.4mm wide x 2.6-2.9mm tall, but
// the cable's outer sleeve needs the fuller cutout to actually pass
// through). usb_cutout_w/h below (12x9) already satisfy that with a
// little extra margin on height — no change needed now that the
// connector type is confirmed, this is just the correct citation for why
// those numbers work, replacing the old Micro-USB-based reasoning.
arduino_l          = 37;   // pocket length (Y) — tightened from a generic 38mm margin. Better
                            // data now: base Pro Micro is ~33mm, and Keebio (who sells the exact
                            // USB-C variant) states it specifically runs ~3mm longer than the
                            // Micro-USB version because of the connector footprint = ~36mm for
                            // this board. 37mm leaves 1mm clearance, tighter than before because
                            // this number is better-reasoned now, not because the underlying
                            // uncertainty (calipers not yet done) has changed.
arduino_w          = 21;   // pocket width (X) — board's ~18-18.4mm wide edge + margin. Width
                            // doesn't vary between Micro-USB/USB-C variants (only length does,
                            // from the connector), so no equivalent tightening applies here.
arduino_wall_t     = 1.5;  // retaining wall thickness (bottom tray)
arduino_wall_h     = 2.5;  // retaining wall height — keeps the board from sliding sideways
arduino_standoff_h = 1;    // corner standoff height — lifts the board off the floor slightly,
                            // clearing any solder blobs on the underside

usb_cutout_w  = 12;  // wall cutout width — matches the standard USB-C panel cutout width
usb_cutout_h  = 9;   // wall cutout height — standard USB-C panel cutout is 8.4mm; 9mm keeps
                      // a small margin above that
usb_cutout_z0 = 2;   // wall cutout bottom, world Z — still an ESTIMATE (~5.5mm port center
                      // above the tray floor), not measured against the actual board's port
                      // height. This is unrelated to the Micro-USB/USB-C question and still
                      // needs a test-fit or caliper check before printing final.

// Board centered in X, pushed to the BACK (max Y) of the case, USB port
// facing the back wall so the cable exits there — position shared between
// case_v4_bottom.scad (the pocket) and case_v4_top.scad (the wall cutout)
// so they're guaranteed to align, rather than two separately-guessed numbers.
arduino_x_center = plate_w / 2;
arduino_y_back   = plate_d - border - 4.25; // The tray's own inner cavity back boundary sits at
                            // plate_d - border - fit_clearance(0.25) - wall_thickness(2) = 86.9,
                            // not plate_d - border(89.15) — those extra two values belong to
                            // case_v4_bottom.scad specifically. Using -4.25 here (2mm safety
                            // margin past that real boundary) keeps the pocket safely inside the
                            // tray's actual cavity instead of overlapping its own back wall.

module chamfered_rect(w, d, c) {
    polygon(points = [
        [c, 0], [w - c, 0],
        [w, c], [w, d - c],
        [w - c, d], [c, d],
        [0, d - c], [0, c]
    ]);
}
