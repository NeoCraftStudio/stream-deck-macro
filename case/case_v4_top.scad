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

// ---- Crest split (prints separately from the top mount, less PLA on the
// bevel's mostly-flat top surface, and each half can sit closer to flat on
// the bed than one combined 73mm-tall tilted piece). Joined by 4 pins,
// same 0.25mm-per-side clearance convention as case_v4_bottom.scad's
// fit_clearance, so the fit tolerance is consistent across the project. ----
pin_d               = 1.5;    // pin shaft diameter
pin_clearance       = 0.25;   // per-side clearance for the mating hole (FDM fit)
mount_pin_engagement = 5;     // how far the STRAIGHT segment reaches into the mount — plenty of
                               // material there, mount's wall doesn't taper like the collar does
crest_pin_engagement = 1.6;   // how far the ANGLED segment reaches into the crest. Raised from 0.6mm
                               // — verified available depth along the actual angled direction (not a
                               // vertical guess) was 2.39-2.61mm across the hole's full diameter, so
                               // 1.6mm leaves a real ~0.8mm margin even at the worst-measured point.

collar_bottom_z = rim_height - bevel_height; // interface height, unsheared reference

pin_offset = 3.75; // distance from the wall's outer edge to each pin's center. Reported: pins were
                    // sitting at the wall's INNER edge (old value 6.0), visibly poking into the open
                    // cavity instead of sitting inside the wall. Moved back toward true wall-center
                    // (border/2 = 3), but not exactly on it — measured via ray-cast probe: a flat
                    // plateau of ~1.21mm material thickness runs from x=3.0 to x=4.5, but drops off
                    // sharply below x=3.0 (down to ~0.2mm by x=2.0). 3.75 sits centered in that
                    // plateau, as close to true center as the collar's taper allows while keeping
                    // the pin's full diameter inside consistently-thick material.

// One pin position per straight wall midpoint (front/back/left/right),
// centered along the wall's length — avoids the chamfered corners, where
// the wall band's shape is diagonal and more fiddly to center in.
pin_positions = [
    [plate_w/2, pin_offset],              // front
    [plate_w/2, plate_d - pin_offset],    // back
    [pin_offset, plate_d/2],              // left
    [plate_w - pin_offset, plate_d/2],    // right
];

function seam_z(py) = collar_bottom_z + shear_factor * py;
// World Z of the crest/mount interface at a given y — still sheared
// (tilted front-to-back), same as everything else.

// Straight-hole tradeoff, MOUNT SIDE ONLY: a flat-ended vertical cylinder
// cutting into a locally-sloped surface leaves a small gap unless widened
// — the actual seam height varies across the hole's own diameter, not
// just its center point. slope_margin covers that variation. The mount
// hole stays straight (plenty of margin either way, and no reason to
// angle the mount-facing end — it's the crest side that needed it).
slope_margin = (pin_d/2 + pin_clearance) * shear_factor;

module pin_hole_mount(px, py) {
    breach = 0.3 + slope_margin;
    z0 = seam_z(py);
    translate([px, py, z0 - mount_pin_engagement])
        cylinder(d = pin_d + 2*pin_clearance, h = mount_pin_engagement + breach, $fn = 24);
}

module pin_hole_crest(px, py) {
    // Angled to match the crest's local slope (rotate by tilt_angle_deg
    // about X, same rotation wedge_cutter() itself uses) — requested
    // directly, with a reference photo of a bent-dowel shape. Unlike the
    // straight mount hole, this needs no slope_margin: rotating the hole
    // to be perpendicular to the sloped surface means its flat entry face
    // is already coplanar with that surface, so there's no gap to cover.
    breach = 0.3;
    z0 = seam_z(py);
    translate([px, py, z0])
        rotate([tilt_angle_deg, 0, 0])
            translate([0, 0, -breach])
                cylinder(d = pin_d + 2*pin_clearance, h = crest_pin_engagement + breach, $fn = 24);
}

module mount_pin_holes() {
    for (p = pin_positions) pin_hole_mount(p[0], p[1]);
}

module crest_pin_holes() {
    for (p = pin_positions) pin_hole_crest(p[0], p[1]);
}

module crest_piece() {
    // The bevel alone (wedge_top_collar()), still needs its own
    // inner_hollow cut — the collar's own taper only insets by
    // bevel_inset (3mm), less than border (6mm), so without this cut it
    // would be a solid tapered cap rather than an open frame. No longer
    // includes crest_pins() — pins are now their own standalone print
    // (pins_piece()), inserted into both crest and mount after printing.
    difference() {
        wedge_top_collar();
        translate([border, border, -1])
            linear_extrude(height = back_height + 2)
                chamfered_rect(plate_w - 2*border, plate_d - 2*border, corner_chamfer * 0.6);
        crest_pin_holes();
    }
}

module pin_bent_local() {
    // Straight segment (mount side) starting at local z=0, then an angled
    // segment (crest side) continuing from where the straight one ends —
    // built in local coordinates so it can be placed anywhere (print
    // layout or true case position) with a single translate.
    //
    // Joined by a sphere at the bend point: without it, the straight
    // cylinder's flat top (horizontal) and the angled cylinder's flat
    // bottom (tilted, since it's rotated) only share their exact center
    // point — everywhere else on the circle's edge they diverge, leaving
    // a thin, notched, "broken"-looking joint (reported directly, with a
    // photo). A first attempt fixed this by extending each cylinder past
    // the bend point instead — but extending the ANGLED one backward
    // drifts it sideways as it's rotated (confirmed: ~0.235mm^3 new
    // interference against the mount's straight hole, at all 4 pins,
    // since the drift pushed it outside the hole's clearance radius). A
    // sphere at the exact junction can't drift off-axis — same radius as
    // the pin in every direction — so it fills the notch without creating
    // a new one.
    cylinder(d = pin_d, h = mount_pin_engagement, $fn = 24);
    translate([0, 0, mount_pin_engagement])
        sphere(d = pin_d, $fn = 24);
    translate([0, 0, mount_pin_engagement])
        rotate([tilt_angle_deg, 0, 0])
            cylinder(d = pin_d, h = crest_pin_engagement, $fn = 24);
}

module pins_piece() {
    // 4 identical bent dowels, standalone print — not positioned at their
    // case coordinates (no reason to; they're inserted by hand after
    // printing), laid out in a simple row instead.
    spacing = pin_d + 10;
    for (i = [0 : len(pin_positions) - 1])
        translate([i * spacing, 0, 0])
            pin_bent_local();
}


module switch_deck_flush() {
    // Same as switch_deck(), but capped at the collar-bottom interface
    // height (unsheared z = rim_height - bevel_height = 17) instead of its
    // normal top (rim_height - deck_recess = 17.5). switch_deck()'s top
    // normally pokes 0.5mm above that interface — harmless, even helpful,
    // when deck and collar are CSG-unioned into one printed piece (same
    // fusing logic as its own 0.5mm XY overlap). Now that the collar is a
    // separate print (crest_piece()), that same 0.5mm becomes real
    // solid-solid interference between the two parts — confirmed via
    // trimesh boolean intersection (94.65mm^3 overlap before this fix).
    // deck_thickness itself is untouched, a confirmed design dimension —
    // this only trims the exposed top face that would otherwise collide.
    intersection() {
        switch_deck();
        translate([-1, -1, -1])
            cube([plate_w + 2, plate_d + 2, (rim_height - bevel_height) + 1]);
    }
}

module wedge_straight_body_flush() {
    // Same as wedge_straight_body(), but WITHOUT its +0.3mm overlap — that
    // overlap exists so wedge_straight_body() and wedge_top_collar() share
    // real volume when CSG-unioned into one printed piece. Now that the
    // mount and crest are two separate prints meeting at a butt joint,
    // that same 0.3mm becomes a 0.3mm interference at the mating surface
    // instead of a helpful union overlap — the mount's top would sit
    // 0.3mm proud of where the crest expects to seat. This variant clips
    // exactly at rim_height - bevel_height, flush with the crest's actual
    // bottom face.
    intersection() {
        linear_extrude(height = back_height)
            chamfered_rect(plate_w, plate_d, corner_chamfer);
        wedge_cutter(rim_height - bevel_height);
    }
}

module top_mount_piece() {
    // FIX: the previous version unioned the wall and deck together, THEN
    // applied the inner_hollow cut to that union. The hollow cut's
    // footprint is almost identical to the deck's own footprint, so it
    // stripped the deck back out again — confirmed via cross-section: at
    // z=16 (deck height) only 2 loops existed (wall outer + hollow inner),
    // meaning zero deck material was actually present, despite watertight/
    // component-count checks passing (a hollow frame is still validly
    // watertight — those checks don't catch "missing the right geometry",
    // only "is what's there a valid solid"). Fixed by cutting the hollow
    // into the wall BEFORE anything is unioned onto it, same order the
    // original working case_top_tilted()/wedge_outer_shell() always used.
    //
    // The deck itself is no longer unioned in at all — it's now
    // deck_piece(), a separate print. This module cuts matching square
    // notches (deck_slots()) for its tabs.
    difference() {
        wedge_straight_body_flush();
        translate([border, border, -1])
            linear_extrude(height = back_height + 2)
                chamfered_rect(plate_w - 2*border, plate_d - 2*border, corner_chamfer * 0.6);
        mount_pin_holes();
        deck_slots();
        usb_cable_cutout();
    }
}

module usb_cable_cutout() {
    // Clears the back wall so a USB cable can reach the Arduino's port
    // from outside — position shared with the pocket in
    // case_v4_bottom.scad (arduino_x_center) so they're guaranteed to
    // line up. Well below the tilt-affected region (usb_cutout_z0..+h is
    // under 12mm; the wedge_cutter clipping doesn't start narrowing the
    // wall until much higher), so a plain flat cut is correct here — no
    // shear or rotation needed.
    translate([arduino_x_center - usb_cutout_w/2, plate_d - border - 1, usb_cutout_z0])
        cube([usb_cutout_w, border + 2, usb_cutout_h]);
}

// ---- Deck split (prints separately from the mount, square tab-and-slot
// mounting instead of round pins — matches the flat, non-cylindrical
// profile of a plate that's dropped in from above rather than pressed in
// from the side). Tabs live on the deck; matching notches are cut into the
// mount's wall. Same 0.25mm-per-side clearance convention as the pins and
// case_v4_bottom.scad's fit_clearance. ----
tab_w           = 10;    // tab width along the wall
tab_protrusion  = 3;     // how far the tab reaches into the wall, measured from the wall's border edge
tab_clearance   = 0.25;  // per-side clearance for the mating notch (FDM fit)
deck_fit        = 0.15;  // deck body clearance from the mount opening. Was 0.25 (also duplicated
                          // as a separate local `fit` inside switch_deck_standalone() — consolidated
                          // to this one shared constant so there's a single source of truth).
                          // Reduced to close the visible gap reported between deck and mount; 0.15mm
                          // per side is still printable FDM clearance, just tighter.
tab_overlap     = 0.5;   // extra reach past the deck's (now-smaller) edge, for a solid CSG fuse — same
                          // pattern as switch_deck()'s own 0.5mm overlap, sized the same for consistency

deck_bottom_z    = rim_height - deck_recess - deck_thickness; // 15, unsheared
deck_flush_top_z = rim_height - bevel_height;                 // 17, same cap as switch_deck_flush()
deck_tab_h       = deck_flush_top_z - deck_bottom_z;           // 2mm

// 2 tabs on the long front/back walls (offset from center to avoid the
// existing round pin hole there), 1 each on the shorter left/right walls,
// also offset from center for the same reason — crest_pins() already
// occupies exactly (border/2, plate_d/2) and (plate_w-border/2, plate_d/2)
// on those walls. Confirmed via direct vertex comparison: an un-offset
// left/right tab landed exactly on the pin's position, 12.1mm^3 overlap.
tab_offset = 25;
tab_specs = [
    // [x, y, direction]
    [plate_w/2 - tab_offset, border,                  "front"],
    [plate_w/2 + tab_offset, border,                  "front"],
    [plate_w/2 - tab_offset, plate_d - border,        "back"],
    [plate_w/2 + tab_offset, plate_d - border,        "back"],
    [border,                 plate_d/2 - tab_offset,  "left"],
    [plate_w - border,       plate_d/2 - tab_offset,  "right"],
];

module deck_tab_flat(px, py, dir) {
    // Built directly in WORLD coordinates (not inside deck_piece()'s
    // sheared() wrapper like before) with a flat bottom at z_flat — the
    // exact world height the deck's underside reaches AT THIS TAB'S OWN y.
    //
    // The previous version was built in local/unsheared coordinates and
    // sheared along with everything else — fine for the main deck slab,
    // but a tab has real width (10mm) across the shear direction (Y for
    // the left/right tabs), so shearing it made its BOTTOM face tilt by
    // up to 5.8mm across its own width instead of sitting flat — reported
    // directly, with a photo, as "the bottom part of this slider part"
    // needing to be flat. It also meant deck_slots()' floor (a constant,
    // unsheared Z) was matching against a tab that had actually moved
    // — by as much as 13mm at the left/right tabs' y-position — which is
    // why the floor added last time was "too low" to ever be touched.
    //
    // The top is intentionally left sloped (per request): the block is
    // built tall, then clipped by collar_interface_cap() — the same
    // sheared boundary the deck body's own top uses — so where the tab
    // merges into the deck, it naturally follows the deck's real
    // (sloped) underside instead of ending in a flat step.
    z_flat = deck_bottom_z + shear_factor * py;
    reach = tab_protrusion + deck_fit + tab_overlap;
    tall = 40; // generous — always reaches past the deck's sheared underside
               // at this tab's y before collar_interface_cap() clips it back
    intersection() {
        if (dir == "front")
            translate([px - tab_w/2, border - tab_protrusion, z_flat])
                cube([tab_w, reach, tall]);
        else if (dir == "back")
            translate([px - tab_w/2, plate_d - border + tab_protrusion - reach, z_flat])
                cube([tab_w, reach, tall]);
        else if (dir == "left")
            translate([px - tab_protrusion, py - tab_w/2, z_flat])
                cube([reach, tab_w, tall]);
        else if (dir == "right")
            translate([plate_w - border + tab_protrusion - reach, py - tab_w/2, z_flat])
                cube([reach, tab_w, tall]);
        collar_interface_cap();
    }
}

module collar_interface_cap() {
    // Half-space capping at the collar/deck interface height
    // (rim_height - bevel_height, same reference switch_deck_flush() and
    // switch_deck_standalone_flush() cap at) — sheared so the cap itself
    // is the correct sloped plane in world space, not a flat one. Used to
    // clip deck_tab_flat()'s tall block so its top never sticks out above
    // where the deck's own material naturally ends.
    sheared()
        translate([-1000, -1000, -2000])
            cube([plate_w + 2000, plate_d + 2000, 2000 + (rim_height - bevel_height)]);
}

module deck_tabs() {
    for (t = tab_specs) deck_tab_flat(t[0], t[1], t[2]);
}

module deck_slots() {
    // z_floor computed PER TAB using the same z_flat formula deck_tab_flat()
    // uses — previously this was a single unsheared constant, which didn't
    // match any tab except the one at y=0 (none of them are). Reported
    // directly: "the bottom of the slot is too low, bring it up to where
    // the deck bottom will touch the floor". Matching the same formula
    // both places (not just a number that happens to look close) means the
    // floor and the tab's actual flat bottom land at the exact same height.
    //
    // Still open at the TOP (up to back_height+2) so the deck can be
    // lowered straight down into the mount from above without a ceiling
    // blocking the tab partway.
    c = tab_clearance;
    w = tab_w + 2*c;
    d = tab_protrusion + c + 1; // +1mm so it fully breaches to open air
    seat_clearance = 0.1; // minimal — close enough to "touching" for a
                           // flush seat, while leaving just enough room
                           // for real FDM print tolerance to not jam.
    for (t = tab_specs) {
        px = t[0]; py = t[1]; dir = t[2];
        z_floor = (deck_bottom_z + shear_factor * py) - seat_clearance;
        h = (back_height + 2) - z_floor;
        if (dir == "front")
            translate([px - w/2, border - d, z_floor])
                cube([w, d + 1, h]);
        else if (dir == "back")
            translate([px - w/2, plate_d - border - 1, z_floor])
                cube([w, d + 1, h]);
        else if (dir == "left")
            translate([border - d, py - w/2, z_floor])
                cube([d + 1, w, h]);
        else if (dir == "right")
            translate([plate_w - border - 1, py - w/2, z_floor])
                cube([d + 1, w, h]);
    }
}

module switch_deck_standalone() {
    // Unlike switch_deck(), no XY overlap padding. switch_deck()'s 0.5mm
    // oversize exists to fuse solidly with a wall it's CSG-unioned with —
    // correct for the monolithic design, but now that the deck is its own
    // print (deck_piece()), that same oversize pokes into both the mount's
    // wall and the crest's ring instead of fusing with anything. Confirmed
    // via trimesh: 315.6mm^3 overlap with mount, 12.1mm^3 with crest,
    // before this fix. This variant is undersized by `fit` instead —
    // same 0.25mm-per-side clearance convention as case_v4_bottom.scad's
    // fit_clearance and the pin/tab clearances above — so it actually
    // fits inside the mount's hollow opening rather than jamming into it.
    translate([border + deck_fit, border + deck_fit, rim_height - deck_recess - deck_thickness])
        linear_extrude(height = deck_thickness)
            chamfered_rect(plate_w - 2*(border + deck_fit), plate_d - 2*(border + deck_fit), corner_chamfer * 0.6);
}

module switch_deck_standalone_flush() {
    // Same z-cap logic as switch_deck_flush(), applied to the
    // clearance-fit standalone deck instead of the overlap-fit one.
    intersection() {
        switch_deck_standalone();
        translate([-1, -1, -1])
            cube([plate_w + 2, plate_d + 2, (rim_height - bevel_height) + 1]);
    }
}

module deck_ribs() {
    // Reinforcement on the deck's own underside, replacing the earlier
    // mount-side rib/wedges (removed) — this time built into the deck
    // itself. Positioned entirely in the gaps BETWEEN switches, never
    // under a switch or encoder hole, so it can't collide with the
    // switch/encoder bodies mounted from the top.
    //
    // Outemu (and MX-compatible switches generally) have a body that
    // sits roughly 5mm below the mounting plate. rib_depth=3mm stays
    // safely inside that clearance. rib_w=2.5mm fits the 5.05mm gap
    // between adjacent switch holes (switch_pitch - switch_hole) with
    // ~1.3mm clearance to the nearest hole edge on each side.
    //
    // 3 ribs running the long way (between switch columns) + 3 the other
    // way (between switch rows) — a waffle grid across the whole switch
    // area, confined to the switch grid's own bounding box (checked
    // against the encoder holes and all 6 deck tabs — none fall inside
    // this footprint, front/back tabs sit outside the grid's Y-range,
    // left/right tabs sit outside its X-range).
    //
    // Built in the deck's own local/unsheared frame, same as the deck
    // body — since both are subject to the identical per-point shear
    // (which only depends on Y, applied equally to both), the vertical
    // (Z) distance between the rib's bottom and the deck's own bottom
    // stays exactly rib_depth everywhere after shearing, not just at one
    // reference point. No separate flat-vs-sloped handling needed here,
    // unlike the tabs (which had to match a FLAT floor cut in the mount
    // — a different geometric constraint that doesn't apply to a rib
    // that only ever needs to stay parallel to the deck itself).
    rib_w = 2.5;
    rib_depth = 3;
    margin = 2;
    grid_x0 = grid_origin_x - switch_hole/2 - margin;
    grid_x1 = grid_origin_x + (grid_cols-1)*switch_pitch + switch_hole/2 + margin;
    grid_y0 = grid_origin_y - switch_hole/2 - margin;
    grid_y1 = grid_origin_y + (grid_rows-1)*switch_pitch + switch_hole/2 + margin;
    z0 = deck_bottom_z - rib_depth;

    for (i = [0 : grid_cols - 2]) {
        x = grid_origin_x + (i + 0.5) * switch_pitch;
        translate([x - rib_w/2, grid_y0, z0])
            cube([rib_w, grid_y1 - grid_y0, rib_depth]);
    }
    for (i = [0 : grid_rows - 2]) {
        y = grid_origin_y + (i + 0.5) * switch_pitch;
        translate([grid_x0, y - rib_w/2, z0])
            cube([grid_x1 - grid_x0, rib_w, rib_depth]);
    }
}

module deck_piece() {
    difference() {
        union() {
            sheared()
                union() {
                    switch_deck_standalone_flush();
                    deck_ribs();
                }
            deck_tabs();
        }
        tilted_switch_grid(grid_origin_x, grid_origin_y);
        tilted_encoder_column(encoder_x, grid_origin_y, grid_height_span);
    }
}

module pins_inserted() {
    // Same 4 bent pins as pins_piece(), positioned at their actual
    // (px, py, seam_z) locations instead of laid out for printing — used
    // only by the "assembly" preview render below, so a fit-check in the
    // user's own OpenSCAD GUI shows a realistic assembled state rather
    // than pins sitting off to the side in their print layout.
    for (p = pin_positions)
        translate([p[0], p[1], seam_z(p[1]) - mount_pin_engagement])
            pin_bent_local();
}

// Select which piece to export:
//   openscad -D 'render_part="crest"' -o crest.stl case_v4_top.scad
//   openscad -D 'render_part="mount"' -o mount.stl case_v4_top.scad
//   openscad -D 'render_part="deck"'  -o deck.stl  case_v4_top.scad
//   openscad -D 'render_part="pins"'  -o pins.stl  case_v4_top.scad
// Default ("assembly") renders all four together (pins shown inserted at
// their real position, not their print layout), for a fit-check preview
// only — not meant to be printed as one piece.
render_part = "assembly";

if (render_part == "crest")
    crest_piece();
else if (render_part == "mount")
    top_mount_piece();
else if (render_part == "deck")
    deck_piece();
else if (render_part == "pins")
    pins_piece();
else
    union() {
        top_mount_piece();
        crest_piece();
        deck_piece();
        pins_inserted();
    }
