#!/usr/bin/env python3
"""
Geometry validation harness for the Stream Deck Macro case.

Runs after any OpenSCAD -> STL export. Checks two classes of problem:

  1. Structural validity (watertight, single component, real interference)
     — the same class of bug already caught by the trimesh watertight check.
  2. Dimensional drift against case_params.scad (the single source of truth
     for every number) — catches a future edit to case_params.scad silently
     changing a dimension that was supposed to be locked.

FIXED_DIMENSIONS below are off-the-shelf part dimensions (switch cutout,
encoder shaft) confirmed by physical measurement. Per project rule, these
must never be treated as tunable — if case_params.scad drifts from them,
that's a hard fail, not a warning, because it means a fixed part dimension
was edited without a matching physical re-confirmation.

Usage:
    xvfb-run -a openscad -o case_v4_top.stl case_v4_top.scad
    xvfb-run -a openscad -o case_v4_bottom.stl case_v4_bottom.scad
    python3 validate_case.py case_v4_top.stl case_v4_bottom.stl
"""

import re
import sys
import ast
import operator
from pathlib import Path

import trimesh

PARAMS_FILE = Path(__file__).parent / "case_params.scad"

# ---- Off-the-shelf dimensions confirmed by physical measurement. ----
# Do not adjust these values here to "fix" a failing check — if one of
# these fails, case_params.scad has drifted from a confirmed physical part
# and that needs a real re-measurement, not a code edit.
FIXED_DIMENSIONS = {
    "switch_hole": 14,    # Outemu plate-mount switch, clip-in cutout
    "encoder_d": 7,       # EC11 encoder shaft/bushing, confirmed via calipers
}

_ALLOWED_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.USub: operator.neg,
}


def _safe_eval(expr, names):
    """Evaluate a restricted arithmetic expression using only +-*/ and
    already-parsed names. Refuses anything else (no calls, no attributes)."""
    node = ast.parse(expr, mode="eval").body

    def _eval(n):
        if isinstance(n, ast.Constant):
            return n.value
        if isinstance(n, ast.Name):
            if n.id not in names:
                raise ValueError(f"unknown name '{n.id}' in expression '{expr}'")
            return names[n.id]
        if isinstance(n, ast.BinOp) and type(n.op) in _ALLOWED_OPS:
            return _ALLOWED_OPS[type(n.op)](_eval(n.left), _eval(n.right))
        if isinstance(n, ast.UnaryOp) and type(n.op) in _ALLOWED_OPS:
            return _ALLOWED_OPS[type(n.op)](_eval(n.operand))
        raise ValueError(f"unsupported expression element in '{expr}'")

    return _eval(node)


def parse_params(path=PARAMS_FILE):
    """Parse `name = expr;` assignments from case_params.scad in order,
    evaluating each expression against previously parsed names. This keeps
    case_params.scad as the only place these numbers are ever written."""
    text = path.read_text()
    # strip // line comments before parsing
    text = re.sub(r"//.*", "", text)

    names = {}
    for match in re.finditer(r"^\s*(\w+)\s*=\s*([^;]+);", text, re.MULTILINE):
        name, expr = match.group(1), match.group(2).strip()
        try:
            names[name] = _safe_eval(expr, names)
        except ValueError:
            # not a plain numeric expression (e.g. references a module) — skip
            continue
    return names


def check_fixed_dimensions(params):
    results = []
    for name, expected in FIXED_DIMENSIONS.items():
        actual = params.get(name)
        ok = actual == expected
        results.append((
            f"fixed dimension: {name}",
            ok,
            f"expected {expected}mm (confirmed physical), got {actual}mm from case_params.scad"
        ))
    return results


def check_structural(stl_path):
    results = []
    m = trimesh.load(stl_path)
    results.append((
        f"{stl_path.name}: watertight",
        bool(m.is_watertight),
        f"is_watertight={m.is_watertight}"
    ))
    comps = m.split(only_watertight=False)
    results.append((
        f"{stl_path.name}: single component",
        len(comps) == 1,
        f"{len(comps)} component(s) found"
    ))
    return results, m


def check_footprint(stl_mesh, params, expected_w_key, expected_d_key, label):
    results = []
    bounds = stl_mesh.bounds
    actual_w = bounds[1][0] - bounds[0][0]
    actual_d = bounds[1][1] - bounds[0][1]
    expected_w = params.get(expected_w_key)
    expected_d = params.get(expected_d_key)
    tol = 0.05  # mm
    results.append((
        f"{label}: footprint width vs {expected_w_key}",
        expected_w is not None and abs(actual_w - expected_w) <= tol,
        f"expected {expected_w}mm, got {actual_w:.3f}mm"
    ))
    results.append((
        f"{label}: footprint depth vs {expected_d_key}",
        expected_d is not None and abs(actual_d - expected_d) <= tol,
        f"expected {expected_d}mm, got {actual_d:.3f}mm"
    ))
    return results


def check_interference(top_mesh, bottom_mesh):
    results = []
    try:
        inter = top_mesh.intersection(bottom_mesh, engine="manifold")
        overlap_vol = 0.0 if (inter is None or inter.is_empty) else inter.volume
    except Exception as e:
        results.append(("top/bottom interference", False, f"check failed to run: {e}"))
        return results
    results.append((
        "top/bottom interference",
        overlap_vol < 1.0,  # mm^3 — allow negligible numerical noise
        f"overlap volume = {overlap_vol:.3f} mm^3"
    ))
    return results


def report(results):
    passed = 0
    for name, ok, detail in results:
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {name} — {detail}")
        passed += ok
    print(f"\n{passed}/{len(results)} checks passed.\n")
    return passed == len(results)


def main():
    if len(sys.argv) < 2:
        print("Usage: validate_case.py <top.stl> [bottom.stl]")
        sys.exit(2)

    params = parse_params()
    all_results = []

    all_results += check_fixed_dimensions(params)

    top_path = Path(sys.argv[1])
    top_results, top_mesh = check_structural(top_path)
    all_results += top_results
    all_results += check_footprint(top_mesh, params, "plate_w", "plate_d", top_path.name)

    if len(sys.argv) >= 3:
        bottom_path = Path(sys.argv[2])
        bottom_results, bottom_mesh = check_structural(bottom_path)
        all_results += bottom_results
        all_results += check_interference(top_mesh, bottom_mesh)

    print("CASE VALIDATION REPORT")
    print("=" * 60)
    ok = report(all_results)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
