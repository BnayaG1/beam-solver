# -*- coding: utf-8 -*-
"""Static beam calculations: pin at A, roller at B (R_Bx = 0). y up, kN, m.

Internal convention: Fy and w are negative when the load acts downward (y-axis up).
"""
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

Number = Union[int, float]


def beam_plot_x_coords(L: float, positions: List[float]) -> np.ndarray:
    """x samples from beam origin (0) to L, including supports and load points."""
    Lf = float(L)
    dense = np.linspace(0.0, Lf, 600, dtype=float)
    pts = np.asarray(positions, dtype=float)
    xs = np.sort(np.unique(np.concatenate([dense, pts])))
    if xs.size == 0 or float(xs[0]) > 1e-9:
        xs = np.insert(xs, 0, 0.0)
    return xs


def format_number(num: float) -> Number:
    rounded = round(num, 2)
    if rounded == int(rounded):
        return int(rounded)
    return rounded


def downward_magnitude_to_fy(value: float) -> float:
    """Positive UI magnitude = downward load -> internal Fy < 0 (y up)."""
    return -abs(float(value))


def point_magnitude_to_fy(value: float, direction: str = "down") -> float:
    """Point-load UI magnitude with explicit direction -> internal signed Fy."""
    mag = abs(float(value))
    return mag if direction == "up" else -mag


def downward_intensity_to_w(value: float) -> float:
    """Positive UI magnitude = downward distributed intensity -> internal w < 0."""
    return -abs(float(value))


def _moment_from_udl_about_cut(w: float, x1: float, x2: float, x: float) -> float:
    if x <= x1:
        return 0.0
    if x < x2:
        a = x - x1
        return w * a * a / 2.0
    span = x2 - x1
    centroid = (x1 + x2) / 2.0
    return w * span * (x - centroid)


def compute_reactions(
    loads: List[dict], L: float, ra_pos: float, rb_pos: float
) -> Tuple[float, float, float, float]:
    """
    Pin at A, roller at B: R_Ax, R_Ay, R_By; R_Bx = 0.
    Equilibrium: Sum Fy=0, Sum Fx=0, Sum M_A=0.
    """
    sum_fx = 0.0
    sum_fy = 0.0
    moment_about_ra = 0.0
    for load in loads:
        if load["type"] == "point":
            sum_fy += load["Fy"]
            sum_fx += float(load.get("Fx", 0.0))
            moment_about_ra -= load["Fy"] * (load["x"] - ra_pos)
        elif load["type"] == "distributed":
            span = load["x2"] - load["x1"]
            resultant = load["w"] * span
            centroid = (load["x1"] + load["x2"]) / 2
            sum_fy += resultant
            moment_about_ra -= resultant * (centroid - ra_pos)
        elif load["type"] == "moment":
            moment_about_ra += load["M"]
        elif load["type"] == "inclined":
            sum_fx += load["Fx"]
            sum_fy += load["Fy"]
            moment_about_ra -= load["Fy"] * (load["x"] - ra_pos)
    if L <= 0:
        raise ValueError("אורך הקורה חייב להיות חיובי.")
    if abs(rb_pos - ra_pos) < 1e-9:
        raise ValueError("מיקומי הסמכים חייבים להיות שונים.")
    arm_b = rb_pos - ra_pos
    rb_y = moment_about_ra / arm_b
    ra_y = -sum_fy - rb_y
    ra_x = -sum_fx
    rb_x = 0.0
    return ra_x, ra_y, rb_x, rb_y


def bending_moment(
    x: float,
    loads: List[dict],
    ra_y: float,
    rb_y: float,
    ra_pos: float,
    rb_pos: float,
) -> float:
    M = 0.0
    if x >= ra_pos:
        M += ra_y * (x - ra_pos)
    if x >= rb_pos:
        M += rb_y * (x - rb_pos)
    for load in loads:
        if load["type"] == "point":
            if x >= load["x"]:
                M += load["Fy"] * (x - load["x"])
        elif load["type"] == "distributed":
            M += _moment_from_udl_about_cut(load["w"], load["x1"], load["x2"], x)
        elif load["type"] == "moment":
            if x >= load["x"]:
                M += load["M"]
        elif load["type"] == "inclined":
            if x >= load["x"]:
                M += load["Fy"] * (x - load["x"])
    return M


def shear_force(
    x: float,
    loads: List[dict],
    ra_y: float,
    rb_y: float,
    ra_pos: float,
    rb_pos: float,
) -> float:
    V = 0.0
    if x >= ra_pos:
        V += ra_y
    if x >= rb_pos:
        V += rb_y
    for load in loads:
        if load["type"] == "point":
            if x >= load["x"]:
                V += load["Fy"]
        elif load["type"] == "distributed":
            x1, x2, w = load["x1"], load["x2"], load["w"]
            if x >= x1:
                V += w * (min(x, x2) - x1)
        elif load["type"] == "inclined":
            if x >= load["x"]:
                V += load["Fy"]
    return V


def normal_force(x: float, loads: List[dict], ra_x: float, ra_pos: float) -> float:
    N = 0.0
    if x >= ra_pos:
        N += ra_x
    for load in loads:
        if load["type"] == "inclined" and x >= load["x"]:
            N += load["Fx"]
        if load["type"] == "point" and x >= load["x"]:
            N += float(load.get("Fx", 0.0))
    return N


def get_calculation_steps(
    loads: List[dict],
    L: float,
    ra_pos: float,
    rb_pos: float,
    ra_x: float,
    ra_y: float,
    rb_x: float,
    rb_y: float,
) -> List[str]:
    lines: List[str] = []
    arm_b = rb_pos - ra_pos
    lines.append(
        "מודל: סמכת צמד ב-A, גליל ב-B. בממשק: גודל חיובי = עומס כלפי מטה (מלמעלה). "
        "בחישוב פנימי: Fy,w שליליים = כלפי מטה (ציר y כלפי מעלה)."
    )
    lines.append(f"L={L:g} m, x_A={ra_pos:g}, x_B={rb_pos:g}, מרווח B-A={arm_b:g} m.")
    sum_fx = sum_fy = moment_about_ra = 0.0
    for i, load in enumerate(loads, 1):
        if load["type"] == "point":
            fy = load["Fy"]
            fx = float(load.get("Fx", 0.0))
            m = fy * (load["x"] - ra_pos)
            sum_fy += fy
            sum_fx += fx
            moment_about_ra += m
            lines.append(f"עומס {i} נקודתי: Fx={fx:g}, Fy={fy:g} kN; תרומה ל-M_A={m:g} kN·m.")
        elif load["type"] == "distributed":
            span = load["x2"] - load["x1"]
            w = load["w"]
            r = w * span
            xc = (load["x1"] + load["x2"]) / 2
            m = r * (xc - ra_pos)
            sum_fy += r
            moment_about_ra += m
            lines.append(f"עומס {i} מפולג: w={w:g}, M_A={m:g} kN·m.")
        elif load["type"] == "moment":
            moment_about_ra += load["M"]
            lines.append(f"עומס {i} מומנט טהור M={load['M']:g} kN·m.")
        elif load["type"] == "inclined":
            fx, fy = load["Fx"], load["Fy"]
            m = fy * (load["x"] - ra_pos)
            sum_fx += fx
            sum_fy += fy
            moment_about_ra += m
            lines.append(f"עומס {i} אלכסוני: Fx={fx:g}, Fy={fy:g}; M_A={m:g} kN·m.")
    lines.append(f"ΣFy (עומסים)={sum_fy:g} kN; ΣFx (עומסים)={sum_fx:g} kN; ΣM_A={moment_about_ra:g} kN·m.")
    lines.append(f"R_By = -ΣM_A/(x_B-x_A) = {rb_y:g} kN.")
    lines.append(f"R_Ay = -ΣFy - R_By = {ra_y:g} kN.")
    lines.append(f"R_Ax = -ΣFx = {ra_x:g} kN; R_Bx = {rb_x:g} kN (גליל).")
    return lines


def build_ai_explanation_payload(
    loads: List[dict],
    L: float,
    ra_pos: float,
    rb_pos: float,
    ra_x: float,
    ra_y: float,
    rb_x: float,
    rb_y: float,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    p: Dict[str, Any] = {
        "schema": "beam_solver.v2_pin_roller",
        "model": {"A": "pin", "B": "roller_no_Rbx"},
        "geometry": {"L_m": L, "x_A": ra_pos, "x_B": rb_pos},
        "loads": loads,
        "reactions_kN": {
            "R_Ax": ra_x,
            "R_Ay": ra_y,
            "R_Bx": rb_x,
            "R_By": rb_y,
        },
        "calculation_steps": get_calculation_steps(
            loads, L, ra_pos, rb_pos, ra_x, ra_y, rb_x, rb_y
        ),
    }
    if extra:
        p["extra"] = extra
    return p
