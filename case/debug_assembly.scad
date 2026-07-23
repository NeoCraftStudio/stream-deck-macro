include <case_params.scad>
use <case_v4_top.scad>
use <case_v4_bottom.scad>

echo("plate_w=", plate_w, "plate_d=", plate_d, "border=", border);

case_top();
case_bottom();
