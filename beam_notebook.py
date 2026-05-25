# -*- coding: utf-8 -*-
"""תצוגת דף מחברת — מבוסס על תרגיל פתור ידני (שרטוט + דיאגרמות + חישובים)."""
from __future__ import annotations

import base64
import html as html_lib
import io
import re
import sys
import ssl
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
from matplotlib.patches import Arc, Polygon
import numpy as np
from matplotlib.lines import Line2D
import streamlit as st
import streamlit.components.v1 as components

import solver

# צבעי «דיו» כמו בתמונת הדוגמה
_INK = "#1a1a1b"
_GREEN = "#188038"
_BLUE = "#0056b3"
_RED = "#d93025"
_PAPER = "#fdf5e6"
_GRID = "#c8c0b0"
_HEADER = "#1e3a5f"
_CHARCOAL = "#2c3e50"
_HIGHLIGHT_ANSWER = "#e2f0d9"
_HIGHLIGHT_ANSWER_BORDER = "#8fad7a"
_ORANGE_NOTE = "#c2410c"
_BRIGHT_GREEN = "#16a34a"
# משבצת אחת בנייר (11px) — בקואורדינטות שרטוט הקורה
_NOTEBOOK_GRID_Y = 0.11
_U_FORCE = "t"
_U_MOMENT = "tm"
_UI_FONT_CSS = "'Rubik', 'Heebo', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif"
_FONT_DIR = Path(__file__).resolve().parent / ".notebook_fonts"
_HEEBO_TTF = _FONT_DIR / "Heebo-Regular.ttf"
_HEEBO_URLS = (
    "https://raw.githubusercontent.com/google/fonts/main/ofl/heebo/Heebo-Regular.ttf",
    "https://fonts.gstatic.com/s/heebo/v28/NGs6v5NKh0bT0JCd-1Dh.woff2",
)
_MPL_FONT_FAMILY = "Heebo"
_FONT_READY = False
# גדלי כתב — דיגיטלי וקריא על דף A4 (matplotlib, pt)
_FS_TINY = 8.0
_FS_SMALL = 8.5
_FS_BODY = 9.5
_FS_LABEL = 10.0
_FS_SIGN = 11.0
_FS_TITLE = 10.5

# A4 (210×297 mm) — גובה iframe בפיקסלים (~96 DPI)
_A4_IFRAME_HEIGHT_PX = 1160


_NOTEBOOK_IFRAME_CSS = f"""
@import url('https://fonts.googleapis.com/css2?family=Rubik:wght@400;500;600&family=Heebo:wght@400;500;600&display=swap');
* {{ box-sizing: border-box; }}
html, body {{
  margin: 0; padding: 0;
  background: #2e2820;
  font-family: {_UI_FONT_CSS};
}}
.nb-outer {{
  display: flex;
  justify-content: center;
  padding: 8px;
}}
.nb-page {{
  width: 210mm;
  height: 297mm;
  max-width: calc(100vw - 24px);
  max-height: 297mm;
  padding: 6mm 7mm 7mm;
  color: {_INK};
  background-color: {_PAPER};
  background-image:
    linear-gradient({_GRID} 1px, transparent 1px),
    linear-gradient(90deg, {_GRID} 1px, transparent 1px);
  background-size: 11px 11px;
  border: 1px solid rgba(90, 70, 40, 0.4);
  box-shadow: 0 10px 28px rgba(0,0,0,0.28);
  overflow: hidden;
  font-family: {_UI_FONT_CSS};
}}
.nb-page *:not(img) {{
  font-family: {_UI_FONT_CSS};
  font-weight: 400;
}}
.nb-row {{
  display: flex;
  flex-direction: row;
  flex-wrap: nowrap;
  align-items: stretch;
  gap: 6px;
  width: 100%;
  height: calc(297mm - 14mm);
  max-height: calc(297mm - 14mm);
  direction: ltr;
}}
.nb-col-left {{
  flex: 0 0 50%;
  width: 50%;
  min-width: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: transparent;
}}
.nb-beam-zone {{
  flex: 1 1 auto;
  min-height: 0;
  height: 100%;
  width: 100%;
  overflow: hidden;
  background: transparent;
}}
.nb-beam-zone img {{
  width: 100%;
  height: 100%;
  object-fit: contain;
  object-position: center top;
  display: block;
  background: transparent;
}}
.nb-col-calc {{
  flex: 0 0 50%;
  width: 50%;
  min-width: 0;
  height: 100%;
  max-height: 100%;
  overflow-x: hidden;
  overflow-y: auto;
  direction: rtl;
  unicode-bidi: plaintext;
  text-align: right;
  font-family: {_UI_FONT_CSS};
  font-size: 10.5pt;
  line-height: 2.15;
  letter-spacing: 0.02em;
  -webkit-font-smoothing: antialiased;
  text-rendering: optimizeLegibility;
  font-variant-numeric: tabular-nums;
  padding: 10px 14px 14px 18px;
  border-left: none;
  align-self: stretch;
  background: transparent;
}}
.nb-flow {{
  display: flex;
  flex-direction: column;
  gap: 0;
  min-height: 100%;
}}
.nb-block {{
  margin-bottom: 22px;
  padding: 0 2px;
}}
.nb-block:last-child {{
  margin-bottom: 0;
}}
.nb-calc-title {{
  margin: 0 0 18px 0;
  padding: 0 0 8px 0;
  font-size: 14pt;
  font-weight: 700;
  color: {_HEADER};
  border-bottom: 2px solid rgba(30, 58, 95, 0.2);
  line-height: 1.4;
  letter-spacing: -0.02em;
}}
.nb-block-label {{
  margin: 20px 0 12px 0;
  font-size: 11pt;
  font-weight: 700;
  letter-spacing: 0.04em;
  line-height: 1.5;
}}
.nb-block-label.nb-lbl-green {{ color: {_BRIGHT_GREEN}; }}
.nb-block-label.nb-lbl-blue {{ color: {_BLUE}; }}
.nb-block-label.nb-lbl-red {{ color: {_RED}; }}
.nb-line {{
  margin: 5px 0;
  padding: 2px 0;
  line-height: 2.2;
  word-spacing: 0.08em;
  font-variant-numeric: tabular-nums;
}}
.nb-line.nb-gap {{
  margin: 14px 0;
  min-height: 8px;
  line-height: 0.4;
}}
.nb-line.nb-eq {{
  color: {_CHARCOAL};
  font-weight: 500;
}}
.nb-line.nb-eq-start {{
  margin-top: 20px;
  font-weight: 700;
  color: {_INK};
}}
.nb-line.nb-eq-start:first-child {{
  margin-top: 6px;
}}
.nb-sub {{
  margin: 8px 0 6px;
  font-weight: 700;
  font-size: 10pt;
  color: {_CHARCOAL};
  line-height: 2;
}}
.nb-line.nb-delta {{
  color: {_BRIGHT_GREEN};
  font-weight: 600;
  font-size: 10.5pt;
}}
.nb-line.nb-shear {{
  color: {_BLUE};
  font-weight: 600;
}}
.nb-line.nb-moment {{
  color: {_RED};
  font-weight: 600;
}}
.nb-line.nb-note {{
  color: {_ORANGE_NOTE};
  font-size: 9pt;
  font-weight: 500;
  line-height: 2.05;
  margin-top: 10px;
  padding-right: 4px;
  opacity: 0.95;
}}
.nb-sym {{
  font-family: 'Rubik', 'Times New Roman', serif;
  font-weight: 600;
  font-size: 1.05em;
  line-height: 1;
  vertical-align: -0.06em;
}}
.nb-sym-svg {{
  display: inline-block;
  vertical-align: -0.15em;
  margin-inline: 1px;
}}
.nb-black {{ color: {_INK}; }}
.nb-sub.nb-black {{ color: {_CHARCOAL}; }}
.nb-box {{
  display: inline-block;
  border: 1px solid rgba(30, 58, 95, 0.35);
  padding: 4px 12px;
  margin: 6px 0 10px;
  font-weight: 700;
  line-height: 1.65;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.35);
  box-decoration-break: clone;
  -webkit-box-decoration-break: clone;
}}
.nb-box.nb-box-answer {{
  background: rgba(226, 240, 217, 0.42);
  border: 1px solid rgba(143, 173, 122, 0.75);
  color: {_CHARCOAL};
}}
.nb-xzero-card {{
  margin-top: 24px;
  padding: 12px 14px;
  border-radius: 8px;
  border: 1px dashed rgba(217, 48, 37, 0.45);
  background: rgba(255, 255, 255, 0.28);
  text-align: right;
}}
.nb-xzero-card .nb-line {{
  color: {_RED};
  font-weight: 700;
  font-size: 11pt;
  line-height: 2.35;
}}
.nb-xzero-title {{
  margin: 0 0 8px 0;
  font-size: 10pt;
  font-weight: 700;
  color: {_RED};
  opacity: 0.9;
}}
.nb-col-calc .nb-line,
.nb-col-calc .nb-sub,
.nb-col-calc .nb-box {{
  font-family: inherit;
}}
.nb-line sub,
.nb-line sup {{
  font-size: 0.82em;
  line-height: 0;
  font-weight: 600;
}}
"""


def _embedded_ui_font_face_css() -> str:
    """Heebo מוטמע ל-iframe — עברית ומספרים חדים גם ללא רשת."""
    if not _HEEBO_TTF.is_file() or _HEEBO_TTF.stat().st_size < 8000:
        return ""
    data = base64.b64encode(_HEEBO_TTF.read_bytes()).decode("ascii")
    return (
        "@font-face{font-family:'Heebo';src:url(data:font/truetype;charset=utf-8;"
        f"base64,{data}) format('truetype');font-weight:400;font-style:normal;}}"
    )


def _wrap_iframe_document(body: str) -> str:
    _ensure_notebook_font()
    css = _embedded_ui_font_face_css() + _NOTEBOOK_IFRAME_CSS
    return f"""<!DOCTYPE html>
<html lang="he">
<head><meta charset="utf-8"><style>{css}</style></head>
<body><div class="nb-outer"><article class="nb-page">{body}</article></div></body>
</html>"""


def station_labels(
    loads: List[dict], L: float, ra_pos: float, rb_pos: float
) -> List[Tuple[float, str]]:
    xs = solver.critical_x_positions(loads, L, ra_pos, rb_pos)
    labels: Dict[float, str] = {}
    labels[round(ra_pos, 6)] = "A"
    labels[round(rb_pos, 6)] = "B"
    letters = "CDEGHIJKLMNOPQRSTUVWXYZ"
    li = 0
    for x in xs:
        k = round(x, 6)
        if k not in labels:
            labels[k] = letters[li] if li < len(letters) else f"P{li}"
            li += 1
    return [(x, labels[round(x, 6)]) for x in xs]


def _values_at_stations(
    loads: List[dict],
    L: float,
    ra_pos: float,
    rb_pos: float,
    ra_x: float,
    ra_y: float,
    rb_x: float,
    rb_y: float,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for x, label in station_labels(loads, L, ra_pos, rb_pos):
        f = solver.internal_forces_at_x(
            x, L, loads, ra_pos, rb_pos, ra_x, ra_y, rb_y
        )
        m_use = f["M_right"] if abs(f["M_right"]) >= abs(f["M_left"]) else f["M_left"]
        n_use = f["N_right"]
        v_use = f["V_right"]
        rows.append(
            {
                "x": x,
                "label": label,
                "N": n_use,
                "Q": v_use,
                "M": m_use,
                **f,
            }
        )
    return rows


def _load_fx_term(ld: dict) -> float:
    if ld["type"] == "point":
        return float(ld.get("Fx", 0.0))
    if ld["type"] == "inclined":
        return float(ld["Fx"])
    return 0.0


def _load_fy_term(ld: dict) -> float:
    if ld["type"] == "point":
        return float(ld["Fy"])
    if ld["type"] == "distributed":
        return float(ld["w"] * (ld["x2"] - ld["x1"]))
    if ld["type"] == "inclined":
        return float(ld["Fy"])
    return 0.0


def _equilibrium_sections(
    loads: List[dict],
    ra_pos: float,
    rb_pos: float,
    ra_x: float,
    ra_y: float,
    rb_y: float,
) -> Dict[str, Any]:
    sums = solver.equilibrium_load_sums(loads, ra_pos, rb_pos)
    arm_b = rb_pos - ra_pos
    arm_a = ra_pos - rb_pos
    fx_lines: List[str] = []
    ma_lines: List[str] = []
    mb_lines: List[str] = []
    for i, ld in enumerate(loads, 1):
        fx = _load_fx_term(ld)
        if abs(fx) > 1e-9:
            fx_lines.append(f"Fx_{i}={solver.format_number(fx)}")
        ma = solver.equilibrium_load_sums([ld], ra_pos, rb_pos)["moment_about_ra"]
        mb = solver.equilibrium_load_sums([ld], ra_pos, rb_pos)["moment_about_rb"]
        if abs(ma) > 1e-9:
            ma_lines.append(f"M_{i}={solver.format_number(ma)}")
        if abs(mb) > 1e-9:
            mb_lines.append(f"M_{i}={solver.format_number(mb)}")
    return {
        "sums": sums,
        "arm_b": arm_b,
        "arm_a": arm_a,
        "fx_lines": fx_lines,
        "ma_lines": ma_lines,
        "mb_lines": mb_lines,
        "fy_check": sums["sum_fy"] + ra_y + rb_y,
        "ra_x": ra_x,
        "ra_y": ra_y,
        "rb_y": rb_y,
    }


def _shear_zero_notes(
    loads: List[dict],
    L: float,
    ra_pos: float,
    rb_pos: float,
    ra_y: float,
    rb_y: float,
) -> List[str]:
    """נקודות שבהן Q=0 תחת מפולג (כמו x=Q/q בתמונה)."""
    notes: List[str] = []
    eps = 1e-6
    for i, ld in enumerate(loads, 1):
        if ld["type"] != "distributed":
            continue
        x1, x2, w = float(ld["x1"]), float(ld["x2"]), float(ld["w"])
        if abs(w) < 1e-9 or x2 - x1 < 1e-9:
            continue
        v_start = solver.shear_force(x1 + eps, loads, ra_y, rb_y, ra_pos, rb_pos)
        q_mag = abs(w)
        if abs(v_start) < 1e-9:
            xz = x1
        else:
            xz = x1 - v_start / w
        if x1 - 0.01 <= xz <= x2 + 0.01:
            notes.append(
                f"קטע מפולג {i}: x = Q/q = {solver.format_number(abs(v_start))}/{solver.format_number(q_mag)} "
                f"= {solver.format_number(xz)} m  (Q=0)"
            )
    if not notes:
        xs = np.linspace(0, L, 400)
        shears = [solver.shear_force(x, loads, ra_y, rb_y, ra_pos, rb_pos) for x in xs]
        for j in range(len(xs) - 1):
            if shears[j] * shears[j + 1] < 0:
                xz = float(xs[j])
                notes.append(f"חיתוך Q=0 בערך x = {solver.format_number(xz)} m")
                break
    return notes


def _download_heebo_ttf() -> None:
    """מוריד Heebo ל-matplotlib ול-iframe (עברית + נוסחאות)."""
    if _HEEBO_TTF.is_file() and _HEEBO_TTF.stat().st_size > 8000:
        return
    _FONT_DIR.mkdir(parents=True, exist_ok=True)
    ctx = ssl.create_default_context()
    try:
        import certifi

        ctx = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        pass
    urls = list(_HEEBO_URLS)
    try:
        req = urllib.request.Request(
            "https://fonts.googleapis.com/css2?family=Heebo:wght@400&display=swap",
            headers={"User-Agent": "BeamSolver/1.0"},
        )
        with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
            css = resp.read().decode("utf-8", errors="replace")
        m = re.search(r"url\((https://fonts\.gstatic\.com/[^)]+\.ttf)\)", css)
        if m:
            urls.insert(0, m.group(1))
    except (urllib.error.URLError, OSError, TimeoutError):
        pass
    last_err: Exception | None = None
    for url in urls:
        if url.endswith(".woff2"):
            continue
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "BeamSolver/1.0"})
            with urllib.request.urlopen(req, context=ctx, timeout=45) as resp:
                data = resp.read()
            if len(data) > 8000:
                _HEEBO_TTF.write_bytes(data)
                return
        except (urllib.error.URLError, OSError, TimeoutError) as exc:
            last_err = exc
    if last_err is not None:
        raise last_err


def _ensure_notebook_font() -> str:
    """טוען Heebo/Rubik ל-matplotlib — טקסט נקי על שרטוט ודיאגרמות."""
    global _FONT_READY, _MPL_FONT_FAMILY
    if _FONT_READY:
        return _MPL_FONT_FAMILY
    try:
        _download_heebo_ttf()
        from matplotlib import font_manager

        font_manager.fontManager.addfont(str(_HEEBO_TTF))
        _MPL_FONT_FAMILY = font_manager.FontProperties(fname=str(_HEEBO_TTF)).get_name()
    except Exception:
        _MPL_FONT_FAMILY = "Segoe UI"
    _FONT_READY = True
    return _MPL_FONT_FAMILY


def _notebook_mpl_rc() -> None:
    family = _ensure_notebook_font()
    plt.rcParams.update(
        {
            "font.family": family,
            "font.sans-serif": [family, "Heebo", "Rubik", "Segoe UI", "Tahoma", "DejaVu Sans"],
            "font.size": _FS_BODY,
            "axes.unicode_minus": False,
        }
    )


def _prep_figure_transparent(fig: Any) -> None:
    """רקע שקוף — השרטוט נראה צבוע ישירות על נייר המחברת."""
    fig.patch.set_facecolor("none")
    fig.patch.set_alpha(0.0)


def _prep_axis_on_paper(ax: Any, *, grid: bool = False) -> None:
    ax.set_facecolor("none")
    ax.patch.set_alpha(0.0)
    if grid:
        ax.grid(True, color=_GRID, alpha=0.45, linewidth=0.45)
        ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#b8b0a0")
    ax.spines["bottom"].set_color("#b8b0a0")
    ax.tick_params(colors="#555", labelsize=6, length=2)


def _draw_station_x_at(
    ax: Any, x: float, y: float, color: str, *, half: float = 0.038
) -> None:
    ax.plot(
        [x - half, x + half],
        [y + half, y - half],
        color=color,
        linewidth=0.9,
        solid_capstyle="round",
        zorder=6,
    )
    ax.plot(
        [x - half, x + half],
        [y - half, y + half],
        color=color,
        linewidth=0.9,
        solid_capstyle="round",
        zorder=6,
    )


def _draw_beam_station_x(ax: Any, x: float, *, half: float = 0.038) -> None:
    """איקס קטן על הקורה בנקודה שמעליה סימון במידה."""
    _draw_station_x_at(ax, x, 0.0, _INK, half=half)


def _draw_arrow(ax: Any, x: float, y0: float, y1: float, color: str, lw: float = 1.3) -> None:
    ax.annotate(
        "",
        xy=(x, y1),
        xytext=(x, y0),
        arrowprops=dict(arrowstyle="-|>", color=color, lw=lw, mutation_scale=10),
    )


def _draw_arrow_h(
    ax: Any, x_tail: float, x_tip: float, y: float, color: str, lw: float = 1.1
) -> None:
    """חץ אופקי — קצה (ראש) ב־x_tip."""
    ax.annotate(
        "",
        xy=(x_tip, y),
        xytext=(x_tail, y),
        arrowprops=dict(arrowstyle="-|>", color=color, lw=lw, mutation_scale=9),
        zorder=5,
    )


# סמכים — משולש סגור, קווים דקים (×1.5 מהגודל הקודם)
_SUPPORT_TRI_H = 0.45
_SUPPORT_TRI_W = 0.36
_SUPPORT_LW = 0.9
_SUPPORT_DETAIL_LW = 0.55
_ROLLER_CIRCLE_R = 0.042 * 1.5
_ROLLER_CIRCLE_LW = 3.0
_PIN_HATCH_LW = 2.0
_PIN_HATCH_LEN = 0.26
_PIN_HATCH_LEAN = 0.24
_DIM_LINE_OFFSET = 0.30
_SCHEMATIC_BOTTOM_PAD = 0.16
_N_BELOW_MARGIN = 0.36


_AXIS_GAP_MULT = 1.5


def _notebook_layout() -> Dict[str, float]:
    """מיקומים אנכיים: קורה → מידות → N (2×d) → Q (1.5×d) → M (1.5×d)."""
    beam_to_dim = _SUPPORT_TRI_H + _DIM_LINE_OFFSET + _NOTEBOOK_GRID_Y
    y_dim = -beam_to_dim
    y_lab = y_dim - 0.14
    y_bottom = y_lab - _SCHEMATIC_BOTTOM_PAD
    axis_gap = _AXIS_GAP_MULT * beam_to_dim
    y_n = y_bottom - 2.0 * beam_to_dim
    y_q = y_n - axis_gap
    y_m = y_q - axis_gap
    return {
        "beam_to_dim": beam_to_dim,
        "y_dim": y_dim,
        "y_lab": y_lab,
        "y_bottom": y_bottom,
        "axis_gap": axis_gap,
        "y_n": y_n,
        "y_q": y_q,
        "y_m": y_m,
        "y_top": 0.72,
        "y_fig_bottom": y_m - _N_BELOW_MARGIN,
    }


_DIM_LW = 1.5
_DIAG_LW = 1.5
_BASELINE_COLOR = "#9a9a9a"
_BASELINE_LW = 0.8
_BASELINE_ALPHA = 0.5
_FILL_ALPHA = 0.12


def _notebook_diagram_scale(values: np.ndarray) -> float:
    """מקדם כוח→שטח שרטוט סביב ציר דיאגרמה (כמו _beam_diagram_ylim)."""
    yr = float(max(np.max(np.abs(values)), 0.5))
    pad = 0.34 * yr
    return 0.28 / (yr + pad)


def _notebook_diagram_extent_bottom(y_ref: float, values: np.ndarray, scale: float) -> float:
    yr = float(max(np.max(np.abs(values)), 0.5))
    pad = 0.34 * yr
    return y_ref - scale * (yr + pad) - 0.08


def _notebook_diagram_series(
    L: float,
    loads: List[dict],
    ra_pos: float,
    rb_pos: float,
    ra_x: float,
    ra_y: float,
    rb_y: float,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, List[Tuple[float, str]]]:
    positions = solver.critical_x_positions(loads, L, ra_pos, rb_pos)
    xs = solver.beam_plot_x_coords(L, positions)
    normals = np.array([solver.normal_force(x, loads, ra_x, ra_pos) for x in xs])
    shears = np.array([solver.shear_force(x, loads, ra_y, rb_y, ra_pos, rb_pos) for x in xs])
    moments = np.array([solver.bending_moment(x, loads, ra_y, rb_y, ra_pos, rb_pos) for x in xs])
    crit = station_labels(loads, L, ra_pos, rb_pos)
    return xs, normals, shears, moments, crit


def _draw_diagram_zero_line(ax: Any, L: float, y_axis: float) -> None:
    """קו אפס עדין — בסיס לדיאגרמה (לא בצבע הדיו)."""
    ax.plot(
        [0.0, float(L)],
        [y_axis, y_axis],
        color=_BASELINE_COLOR,
        linewidth=_BASELINE_LW,
        alpha=_BASELINE_ALPHA,
        solid_capstyle="round",
        zorder=1,
    )


def _diagram_titles_on_axis(
    ax: Any,
    L: float,
    y_axis: float,
    color: str,
    title_hebrew: str,
    title_symbol: str,
) -> None:
    Lf = float(L)
    pad_x = max(0.2, 0.055 * Lf)
    ax.text(
        -pad_x,
        y_axis,
        title_hebrew,
        ha="right",
        va="center",
        fontsize=_FS_SMALL,
        fontweight="600",
        color=color,
        zorder=8,
        clip_on=False,
    )
    ax.text(
        Lf + pad_x * 0.25,
        y_axis,
        title_symbol,
        ha="left",
        va="center",
        fontsize=_FS_TINY,
        fontweight="500",
        color=color,
        zorder=8,
        clip_on=False,
    )


def _annotate_step_notebook(
    ax: Any,
    xs: np.ndarray,
    values: np.ndarray,
    y_ref: float,
    scale: float,
    crit: List[Tuple[float, str]],
    color: str,
    *,
    positive_down: bool,
) -> None:
    """ערכים בנקודות קריטיות + במרכז מדרגות ארוכות — בלי חפיפה."""
    xs = np.asarray(xs, dtype=float)
    values = np.asarray(values, dtype=float)
    Lspan = float(xs[-1] - xs[0]) if len(xs) > 1 else float(xs[-1]) or 1.0
    amp = float(max(np.max(np.abs(values)), 0.5)) * scale
    pad_y = max(0.06, 0.28 * amp)

    def _y(v: float) -> float:
        return y_ref - v * scale if positive_down else y_ref + v * scale

    crit_x = [float(x) for x, _ in crit]

    def _place_label(x: float, v: float, *, slot: int) -> None:
        y = _y(v)
        side = 1 if slot % 2 == 0 else -1
        if positive_down:
            ty = y - pad_y if v >= 0 else y + pad_y
            va = "bottom" if v >= 0 else "top"
        else:
            ty = y + pad_y if v >= 0 else y - pad_y
            va = "bottom" if v >= 0 else "top"
        ty += side * 0.03
        ax.text(
            x,
            ty,
            solver.format_number(v),
            ha="center",
            va=va,
            fontsize=_FS_TINY,
            color=color,
            fontweight="500",
            zorder=7,
            clip_on=False,
        )

    for slot, x in enumerate(crit_x):
        idx = int(np.argmin(np.abs(xs - x)))
        _place_label(x, float(values[idx]), slot=slot)

    for i in range(len(xs) - 1):
        seg = float(xs[i + 1] - xs[i])
        if seg < 0.08 * Lspan:
            continue
        if abs(float(values[i + 1] - values[i])) > 1e-6:
            continue
        xm = 0.5 * (float(xs[i]) + float(xs[i + 1]))
        if any(abs(xm - cx) < 0.06 * Lspan for cx in crit_x):
            continue
        _place_label(xm, float(values[i]), slot=i + len(crit_x))


def _annotate_shear_signs_notebook(
    ax: Any, xs: np.ndarray, shears: np.ndarray, y_ref: float, scale: float
) -> None:
    xs = np.asarray(xs, dtype=float)
    shears = np.asarray(shears, dtype=float)
    i = 0
    while i < len(xs) - 1:
        sign = 1 if shears[i] >= 0 else -1
        j = i + 1
        while j < len(xs) - 1 and (shears[j] >= 0) == (sign >= 0):
            j += 1
        x0, x1 = xs[i], xs[j]
        if x1 - x0 > 1e-6:
            xm = 0.5 * (x0 + x1)
            ym = y_ref + 0.5 * (float(shears[i]) + float(shears[j])) * scale
            ax.text(
                xm,
                ym,
                "+" if sign >= 0 else "−",
                ha="center",
                va="center",
                fontsize=_FS_TINY,
                color=_BLUE,
                fontweight="500",
                zorder=5,
            )
        i = j


def _mark_shear_zero_notebook(
    ax: Any, xs: np.ndarray, shears: np.ndarray, y_ref: float
) -> None:
    for j in range(len(xs) - 1):
        v0, v1 = float(shears[j]), float(shears[j + 1])
        if v0 * v1 < 0:
            x0, x1 = float(xs[j]), float(xs[j + 1])
            xz = x0 - v0 * (x1 - x0) / (v1 - v0)
            ax.plot(
                [xz, xz],
                [y_ref - 0.04, y_ref + 0.04],
                color=_BLUE,
                linewidth=0.9,
                alpha=0.65,
                zorder=4,
            )
            ax.text(
                xz,
                y_ref + 0.1,
                f"x={solver.format_number(xz)}",
                ha="center",
                va="bottom",
                fontsize=_FS_TINY,
                color=_BLUE,
                fontweight="500",
                zorder=7,
                clip_on=False,
            )
            return


def _draw_diagram_base(
    ax: Any,
    L: float,
    y_axis: float,
    color: str,
    crit: List[Tuple[float, str]],
) -> None:
    _draw_diagram_zero_line(ax, L, y_axis)


def _draw_n_schematic(
    ax: Any,
    L: float,
    xs: np.ndarray,
    normals: np.ndarray,
    crit: List[Tuple[float, str]],
    layout: Dict[str, float],
) -> float:
    """N(x) במחברת — step + vlines + ערכים (כמו _plot_n_on_beam)."""
    Lf = float(L)
    y_n = layout["y_n"]
    scale = _notebook_diagram_scale(normals)
    ys = y_n - normals * scale

    _draw_diagram_base(ax, L, y_n, _GREEN, crit)
    ax.fill_between(
        xs, ys, y_n, step="post", color=_GREEN, alpha=_FILL_ALPHA, zorder=2
    )
    ax.step(xs, ys, where="post", color=_GREEN, linewidth=_DIAG_LW, zorder=3)
    _annotate_step_notebook(
        ax, xs, normals, y_n, scale, crit, _GREEN, positive_down=True
    )
    _diagram_titles_on_axis(
        ax, L, y_n, _GREEN, "כוחות ציריים", f"N(x) [{_U_FORCE}]"
    )
    return _notebook_diagram_extent_bottom(y_n, normals, scale)


def _draw_q_schematic(
    ax: Any,
    L: float,
    xs: np.ndarray,
    shears: np.ndarray,
    crit: List[Tuple[float, str]],
    layout: Dict[str, float],
) -> float:
    """Q(x) במחברת — step + vlines + סימני גזירה (כמו _plot_q_on_beam)."""
    Lf = float(L)
    y_q = layout["y_q"]
    scale = _notebook_diagram_scale(shears)
    ys = y_q + shears * scale

    _draw_diagram_base(ax, L, y_q, _BLUE, crit)
    ax.fill_between(
        xs, y_q, ys, step="post", color=_BLUE, alpha=_FILL_ALPHA, zorder=2
    )
    ax.step(xs, ys, where="post", color=_BLUE, linewidth=_DIAG_LW, zorder=3)
    _annotate_step_notebook(
        ax, xs, shears, y_q, scale, crit, _BLUE, positive_down=False
    )
    _annotate_shear_signs_notebook(ax, xs, shears, y_q, scale)
    _mark_shear_zero_notebook(ax, xs, shears, y_q)
    _diagram_titles_on_axis(ax, L, y_q, _BLUE, "גזירה", f"Q(x) [{_U_FORCE}]")
    return _notebook_diagram_extent_bottom(y_q, shears, scale)


def _annotate_moment_notebook(
    ax: Any,
    xs: np.ndarray,
    moments: np.ndarray,
    y_ref: float,
    scale: float,
    crit: List[Tuple[float, str]],
    color: str,
) -> None:
    xs = np.asarray(xs, dtype=float)
    moments = np.asarray(moments, dtype=float)
    amp = float(max(np.max(np.abs(moments)), 0.5)) * scale
    pad_y = max(0.05, 0.26 * amp)
    for slot, (x, _lab) in enumerate(crit):
        idx = int(np.argmin(np.abs(xs - x)))
        v = float(moments[idx])
        y = y_ref - v * scale
        dy = pad_y if slot % 2 == 0 else -pad_y
        ax.text(
            x,
            y - dy if v >= 0 else y + dy,
            solver.format_number(v),
            ha="center",
            va="bottom" if v >= 0 else "top",
            fontsize=_FS_TINY,
            color=color,
            fontweight="500",
            zorder=7,
            clip_on=False,
        )


def _draw_m_schematic(
    ax: Any,
    L: float,
    xs: np.ndarray,
    moments: np.ndarray,
    crit: List[Tuple[float, str]],
    layout: Dict[str, float],
) -> float:
    """M(x) במחברת — עקומה + ערכים (כמו _plot_m_on_beam)."""
    y_m = layout["y_m"]
    scale = _notebook_diagram_scale(moments)
    ys = y_m - moments * scale

    _draw_diagram_base(ax, L, y_m, _RED, crit)
    ax.fill_between(xs, ys, y_m, color=_RED, alpha=_FILL_ALPHA, zorder=2)
    ax.plot(xs, ys, color=_RED, linewidth=_DIAG_LW, zorder=3, solid_capstyle="round")
    _annotate_moment_notebook(ax, xs, moments, y_m, scale, crit, _RED)
    imx = int(np.argmax(np.abs(moments)))
    amp = float(max(np.max(np.abs(moments)), 0.5)) * scale
    pad_y = max(0.05, 0.26 * amp)
    ax.text(
        float(xs[imx]),
        float(ys[imx]) - pad_y * 1.15,
        solver.format_number(float(moments[imx])),
        ha="center",
        va="bottom",
        fontsize=_FS_TINY,
        color=_RED,
        fontweight="600",
        zorder=7,
        clip_on=False,
    )
    _diagram_titles_on_axis(
        ax, L, y_m, _RED, "מומנטים", f"M(x) [{_U_MOMENT}]"
    )
    return _notebook_diagram_extent_bottom(y_m, moments, scale)


def _draw_support_triangle(ax: Any, x: float, tri_h: float, tri_w: float) -> float:
    """משולש סגור (קודקוד על הקורה y=0). מחזיר y של הבסיס."""
    y_base = -tri_h
    ax.add_patch(
        Polygon(
            [(x - tri_w, y_base), (x, 0.0), (x + tri_w, y_base)],
            closed=True,
            fill=False,
            edgecolor=_INK,
            linewidth=_SUPPORT_LW,
            joinstyle="round",
            zorder=4,
        )
    )
    return y_base


def _draw_pin_support(
    ax: Any,
    x: float,
    tri_h: float = _SUPPORT_TRI_H,
    tri_w: float = _SUPPORT_TRI_W,
) -> None:
    """סמך שמאל (ציר): 5 קווי קרקע — לאורך הבסיס, נוטים שמאלה."""
    y_base = _draw_support_triangle(ax, x, tri_h, tri_w)
    y_ground = y_base - _PIN_HATCH_LEN
    for xa in (
        x + tri_w,
        x + tri_w * 0.5,
        x,
        x - tri_w * 0.5,
        x - tri_w,
    ):
        (ln,) = ax.plot(
            [xa - _PIN_HATCH_LEAN, xa],
            [y_ground, y_base],
            color=_INK,
            linewidth=_PIN_HATCH_LW,
            solid_capstyle="round",
            zorder=5,
        )
        ln.set_clip_on(False)


def _draw_roller_support(
    ax: Any,
    x: float,
    tri_h: float = _SUPPORT_TRI_H,
    tri_w: float = _SUPPORT_TRI_W,
) -> None:
    """סמך ימין (גלגל): שני עיגולים ×1.5 מתחת לפינות המשולש."""
    y_base = _draw_support_triangle(ax, x, tri_h, tri_w)
    r = _ROLLER_CIRCLE_R
    for xa in (x - tri_w, x + tri_w):
        circ = plt.Circle(
            (xa, y_base - r),
            r,
            fill=False,
            edgecolor=_INK,
            linewidth=_ROLLER_CIRCLE_LW,
            zorder=6,
        )
        circ.set_clip_on(False)
        ax.add_patch(circ)


def _draw_udl_line(ax: Any, x1: float, x2: float, q_label: str | None = None) -> None:
    """מפולג: קו עליון, חצים אנכיים לנקודות הקצה, 3 חצים קטנים למטה מהקו."""
    y_top = 0.28
    y_tip = 0.02
    arr_mid = 0.07
    ax.plot([x1, x2], [y_top, y_top], color=_RED, linewidth=1.5, zorder=5)
    _draw_arrow(ax, x1, y_top, y_tip, _RED, lw=1.0)
    _draw_arrow(ax, x2, y_top, y_tip, _RED, lw=1.0)
    span = x2 - x1
    if span > 1e-9:
        for frac in (0.25, 0.5, 0.75):
            xc = x1 + frac * span
            _draw_arrow(ax, xc, y_top, y_top - arr_mid, _RED, lw=0.85)
    if q_label:
        ax.text(
            (x1 + x2) / 2,
            y_top + 0.1,
            q_label,
            ha="center",
            va="bottom",
            fontsize=_FS_BODY,
            color=_RED,
            fontweight="normal",
            zorder=6,
        )


def _draw_moment_arc(
    ax: Any, x: float, m: float, scale: float = 0.22, *, show_value: bool = True
) -> None:
    """קשת ממורכזת בנקודה על הקורה; ראש חץ בסוף הקשת."""
    rad = scale
    t1, t2 = (20, 200) if m >= 0 else (200, 20)
    ax.add_patch(
        Arc((x, 0.0), rad * 2, rad * 2, angle=0, theta1=t1, theta2=t2, color=_RED, lw=1.4, zorder=5)
    )
    t2_rad = np.deg2rad(t2)
    xe = x + rad * np.cos(t2_rad)
    ye = rad * np.sin(t2_rad)
    tx = -rad * np.sin(t2_rad)
    ty = rad * np.cos(t2_rad)
    tlen = float(np.hypot(tx, ty)) or 1.0
    ah = 0.055
    ax.annotate(
        "",
        xy=(xe, ye),
        xytext=(xe - tx / tlen * ah * 2.2, ye - ty / tlen * ah * 2.2),
        arrowprops=dict(arrowstyle="-|>", color=_RED, lw=1.2, mutation_scale=9),
        zorder=6,
    )
    if show_value:
        ax.text(
            x + 0.06 * (1 if m >= 0 else -1),
            rad + 0.14,
            f"{solver.format_number(abs(m))}",
            fontsize=_FS_BODY,
            color=_RED,
            fontweight="normal",
            ha="left" if m >= 0 else "right",
            zorder=6,
        )


def _draw_beam_schematic(
    ax: Any,
    L: float,
    loads: List[dict],
    ra_pos: float,
    rb_pos: float,
    ra_x: float,
    ra_y: float,
    rb_y: float,
    *,
    show_values: bool = False,
    set_limits: bool = True,
) -> None:
    """שרטוט קורה + עומסים. show_values=False: רק אותיות נקודות על קו מידות (A,B,C…)."""
    Lf = float(L)
    ax.plot([0, Lf], [0, 0], color=_INK, linewidth=2.2, zorder=2, solid_capstyle="round")

    if abs(ra_pos - rb_pos) < 1e-9:
        _draw_pin_support(ax, ra_pos)
    else:
        if ra_pos <= rb_pos:
            _draw_pin_support(ax, ra_pos)
            _draw_roller_support(ax, rb_pos)
        else:
            _draw_pin_support(ax, rb_pos)
            _draw_roller_support(ax, ra_pos)

    load_scale = max(0.28, 0.05 * max(abs(ra_y), abs(rb_y), 8.0))

    for ld in loads:
        if ld["type"] == "point":
            x = float(ld["x"])
            fy = float(ld["Fy"])
            fx = float(ld.get("Fx", 0.0))
            if abs(fy) > 1e-9:
                mag = load_scale
                if fy < 0:
                    _draw_arrow(ax, x, 0.42, 0.42 - mag, _RED, lw=1.2)
                    if show_values:
                        ax.text(
                            x + 0.04,
                            0.44,
                            f"{solver.format_number(abs(fy))}",
                            fontsize=_FS_BODY,
                            color=_RED,
                            fontweight="normal",
                        )
                else:
                    _draw_arrow(ax, x, -0.36, -0.36 + mag, _RED, lw=1.2)
                    if show_values:
                        ax.text(
                            x + 0.04,
                            -0.2,
                            f"{solver.format_number(abs(fy))}",
                            fontsize=_FS_BODY,
                            color=_RED,
                            fontweight="normal",
                        )
            if abs(fx) > 1e-9:
                magx = load_scale * 0.85
                y0 = 0.05
                if fx > 0:
                    _draw_arrow_h(ax, x - magx, x, y0, _RED, lw=1.1)
                    if show_values:
                        ax.text(
                            x - magx - 0.12,
                            y0 + 0.06,
                            f"{solver.format_number(abs(fx))}",
                            fontsize=_FS_BODY,
                            color=_RED,
                        )
                else:
                    _draw_arrow_h(ax, x + magx, x, y0, _RED, lw=1.1)
                    if show_values:
                        ax.text(
                            x + magx + 0.03,
                            y0 + 0.06,
                            f"{solver.format_number(abs(fx))}",
                            fontsize=_FS_BODY,
                            color=_RED,
                        )
        elif ld["type"] == "distributed":
            x1, x2 = float(ld["x1"]), float(ld["x2"])
            q_lbl = (
                f"{solver.format_number(abs(float(ld['w'])))}" if show_values else None
            )
            _draw_udl_line(ax, x1, x2, q_lbl)
        elif ld["type"] == "moment":
            _draw_moment_arc(ax, float(ld["x"]), float(ld["M"]), show_value=show_values)
        elif ld["type"] == "inclined":
            x = float(ld["x"])
            fx, fy = float(ld["Fx"]), float(ld["Fy"])
            mag = (fx * fx + fy * fy) ** 0.5
            if mag > 1e-9:
                ux, uy = fx / mag, fy / mag
                Larr = load_scale * 1.05
                ax.annotate(
                    "",
                    xy=(x + ux * Larr, uy * Larr),
                    xytext=(x, 0),
                    arrowprops=dict(arrowstyle="-|>", color=_RED, lw=1.3),
                    zorder=5,
                )
                if show_values:
                    ax.text(
                        x + ux * Larr * 0.55,
                        uy * Larr * 0.55 + 0.08,
                        f"{solver.format_number(mag)}",
                        fontsize=_FS_BODY,
                        color=_RED,
                        fontweight="normal",
                        ha="center",
                    )

    if show_values:
        if abs(ra_y) > 1e-9:
            ax.text(
                ra_pos + 0.05,
                0.28,
                f"{solver.format_number(ra_y)} = Ay",
                fontsize=_FS_SMALL,
                color=_INK,
                fontweight="normal",
            )
        if abs(rb_y) > 1e-9:
            ax.text(
                rb_pos - 0.05,
                0.28,
                f"By = {solver.format_number(rb_y)}",
                fontsize=_FS_SMALL,
                color=_INK,
                fontweight="normal",
                ha="right",
            )
        if abs(ra_x) > 1e-9:
            magx = 0.22
            if ra_x > 0:
                ax.annotate(
                    "",
                    xy=(ra_pos + magx, 0.04),
                    xytext=(ra_pos, 0.04),
                    arrowprops=dict(arrowstyle="-|>", color=_INK, lw=1.1),
                )
                ax.text(
                    ra_pos + magx + 0.02,
                    0.1,
                    f"{solver.format_number(ra_x)} = Ax",
                    fontsize=_FS_SMALL,
                    color=_INK,
                )
            else:
                ax.annotate(
                    "",
                    xy=(ra_pos - magx, 0.04),
                    xytext=(ra_pos, 0.04),
                    arrowprops=dict(arrowstyle="-|>", color=_INK, lw=1.1),
                )
                ax.text(
                    ra_pos - magx - 0.2,
                    0.1,
                    f"{solver.format_number(ra_x)} = Ax",
                    fontsize=_FS_SMALL,
                    color=_INK,
                )

    # קו מידות + אותיות נקודות (A, C, D, …)
    stations = station_labels(loads, L, ra_pos, rb_pos)
    layout = _notebook_layout()
    y_dim = layout["y_dim"]
    y_lab = layout["y_lab"]
    for i in range(len(stations) - 1):
        x0, _ = stations[i]
        x1, _ = stations[i + 1]
        xm = (x0 + x1) / 2
        ax.plot([x0, x1], [y_dim, y_dim], color=_INK, lw=_DIM_LW, zorder=2)
        ax.plot([x0, x0], [y_dim - 0.03, y_dim + 0.03], color=_INK, lw=_DIM_LW)
        ax.plot([x1, x1], [y_dim - 0.03, y_dim + 0.03], color=_INK, lw=_DIM_LW)
        if show_values:
            seg = x1 - x0
            if seg > 0.02:
                ax.text(
                    xm,
                    y_dim - 0.1,
                    solver.format_number(seg),
                    ha="center",
                    fontsize=_FS_SMALL,
                    color=_INK,
                )
    for x, lab in stations:
        _draw_beam_station_x(ax, x)
        ax.text(x, y_lab, lab, ha="center", fontsize=_FS_LABEL, fontweight="normal", color=_INK)

    pad_x = max(0.15, 0.04 * Lf)
    ax.set_xlim(-pad_x, Lf + pad_x)
    if set_limits:
        ax.set_ylim(layout["y_bottom"], layout["y_top"])
    ax.axis("off")


def _beam_x_pad(Lf: float) -> float:
    return max(0.04, 0.015 * float(Lf))


def _beam_diagram_ylim(values: np.ndarray, *, floor: float = 0.5) -> Tuple[float, float]:
    """טווח אנכי סביב הקורה (y=0) — לא ציר קרטזי."""
    yr = float(max(np.max(np.abs(np.asarray(values, dtype=float))), floor))
    pad = 0.34 * yr
    return -yr - pad, yr + pad


def _configure_beam_diagram_ax(
    ax: Any,
    Lf: float,
    x_pad: float,
    values: np.ndarray,
    *,
    transparent: bool = True,
    paper: bool = False,
) -> Tuple[float, float]:
    """מגדיר מערכת צירים: x לאורך הקורה, y לגודל הכוח — ללא רשת."""
    if transparent and not paper:
        ax.set_facecolor("none")
        ax.patch.set_alpha(0.0)
    elif paper:
        ax.set_facecolor(_PAPER)
    ymin, ymax = _beam_diagram_ylim(values)
    ax.set_xlim(-x_pad, Lf + x_pad)
    ax.set_ylim(ymin, ymax)
    return ymin, ymax


def _draw_beam_reference(
    ax: Any,
    Lf: float,
    crit: List[Tuple[float, str]],
    ymin: float,
    ymax: float,
) -> None:
    """קו הקורה — בסיס לדיאגרמה; סימוני נקודות על הקורה בלבד."""
    ax.plot([0, Lf], [0, 0], color=_INK, linewidth=1.6, zorder=5, solid_capstyle="round")
    ax.axis("off")


def _plot_zero_baseline_cartesian(ax: Any, Lf: float) -> None:
    ax.axhline(
        0.0,
        color=_BASELINE_COLOR,
        linewidth=_BASELINE_LW,
        alpha=_BASELINE_ALPHA,
        zorder=1,
    )


def _plot_n_on_beam(
    ax: Any,
    xs: np.ndarray,
    normals: np.ndarray,
    Lf: float,
    x_pad: float,
    crit: List[Tuple[float, str]],
    *,
    transparent: bool = True,
    paper: bool = False,
) -> None:
    _configure_beam_diagram_ax(ax, Lf, x_pad, normals, transparent=transparent, paper=paper)
    _plot_zero_baseline_cartesian(ax, Lf)
    ax.fill_between(
        xs, normals, 0, step="post", color=_GREEN, alpha=_FILL_ALPHA, zorder=2
    )
    ax.step(xs, normals, where="post", color=_GREEN, linewidth=_DIAG_LW, zorder=3)
    ax.invert_yaxis()
    ymin, ymax = ax.get_ylim()
    _draw_beam_reference(ax, Lf, crit, ymin, ymax)
    _annotate_step_blocks(ax, xs, normals, _GREEN, crit, invert_y=True)


def _plot_q_on_beam(
    ax: Any,
    xs: np.ndarray,
    shears: np.ndarray,
    Lf: float,
    x_pad: float,
    crit: List[Tuple[float, str]],
    *,
    transparent: bool = True,
    paper: bool = False,
) -> None:
    _configure_beam_diagram_ax(ax, Lf, x_pad, shears, transparent=transparent, paper=paper)
    _plot_zero_baseline_cartesian(ax, Lf)
    ax.fill_between(
        xs, shears, 0, step="post", color=_BLUE, alpha=_FILL_ALPHA, zorder=2
    )
    ax.step(xs, shears, where="post", color=_BLUE, linewidth=_DIAG_LW, zorder=3)
    ymin, ymax = ax.get_ylim()
    _draw_beam_reference(ax, Lf, crit, ymin, ymax)
    _annotate_step_blocks(ax, xs, shears, _BLUE, crit)
    _annotate_shear_signs(ax, xs, shears)
    _mark_shear_zero(ax, xs, shears, Lf)


def _plot_m_on_beam(
    ax: Any,
    xs: np.ndarray,
    moments: np.ndarray,
    Lf: float,
    x_pad: float,
    crit: List[Tuple[float, str]],
    *,
    transparent: bool = True,
    paper: bool = False,
) -> None:
    _configure_beam_diagram_ax(ax, Lf, x_pad, moments, transparent=transparent, paper=paper)
    _plot_zero_baseline_cartesian(ax, Lf)
    ax.fill_between(xs, moments, 0, color=_RED, alpha=_FILL_ALPHA, zorder=2)
    ax.plot(xs, moments, color=_RED, linewidth=_DIAG_LW, zorder=3, solid_capstyle="round")
    ax.invert_yaxis()
    ymin, ymax = ax.get_ylim()
    _draw_beam_reference(ax, Lf, crit, ymin, ymax)
    for slot, (x, _lab) in enumerate(crit):
        idx = int(np.argmin(np.abs(xs - x)))
        v = float(moments[idx])
        amp = float(max(np.max(np.abs(moments)), 0.5))
        pad_y = max(0.05, 0.24 * amp)
        dy = pad_y if slot % 2 == 0 else -pad_y
        ax.text(
            x,
            v - dy,
            solver.format_number(v),
            ha="center",
            va="bottom",
            fontsize=_FS_TINY,
            color=_RED,
            fontweight="500",
            zorder=7,
            clip_on=False,
        )
    imx = int(np.argmax(np.abs(moments)))
    yr = float(max(np.max(np.abs(moments)), 0.5))
    pad_y = max(0.05, 0.26 * yr)
    ax.text(
        float(xs[imx]),
        float(moments[imx]) - pad_y,
        solver.format_number(float(moments[imx])),
        ha="center",
        va="bottom",
        fontsize=_FS_TINY,
        color=_RED,
        fontweight="600",
        zorder=7,
    )


def _diagram_titles(fig: Any, ax: Any, hebrew: str, symbol: str, color: str) -> None:
    """כותרות בעברית משמאל וסימון N(x)/Q(x)/M(x) מימין — מרווח מציר Y."""
    bb = ax.get_position()
    fig.text(
        bb.x0 - 0.018,
        bb.y0 + bb.height / 2,
        hebrew,
        ha="right",
        va="center",
        fontsize=_FS_SMALL,
        fontweight="600",
        color=color,
    )
    fig.text(
        bb.x1 + 0.006,
        bb.y0 + bb.height / 2,
        symbol,
        ha="left",
        va="center",
        fontsize=_FS_TINY,
        fontweight="500",
        color=color,
    )


def _annotate_step_blocks(
    ax: Any,
    xs: np.ndarray,
    ys: np.ndarray,
    color: str,
    crit: Optional[List[Tuple[float, str]]] = None,
    *,
    invert_y: bool = False,
) -> None:
    """ערכים בנקודות קריטיות ובמדרגות ארוכות — ללא כפילות."""
    xs = np.asarray(xs, dtype=float)
    ys = np.asarray(ys, dtype=float)
    values = ys
    Lspan = float(xs[-1] - xs[0]) if len(xs) > 1 else float(xs[-1]) or 1.0
    amp = float(max(np.max(np.abs(values)), 0.5))
    pad_y = max(0.06, 0.22 * amp)
    crit_x = [float(x) for x, _ in (crit or [])]

    def _label_y(v: float, slot: int) -> float:
        side = 1 if slot % 2 == 0 else -1
        off = pad_y * (1 if v >= 0 else -1)
        if invert_y:
            off = -off
        return v + off + side * 0.02 * amp

    for slot, x in enumerate(crit_x):
        idx = int(np.argmin(np.abs(xs - x)))
        v = float(values[idx])
        ax.text(
            x,
            _label_y(v, slot),
            solver.format_number(v),
            ha="center",
            va="bottom" if v >= 0 else "top",
            fontsize=_FS_TINY,
            color=color,
            fontweight="500",
            zorder=7,
            clip_on=False,
        )

    for i in range(len(xs) - 1):
        seg = float(xs[i + 1] - xs[i])
        if seg < 0.08 * Lspan:
            continue
        if abs(float(values[i + 1] - values[i])) > 1e-6:
            continue
        xm = 0.5 * (float(xs[i]) + float(xs[i + 1]))
        if any(abs(xm - cx) < 0.06 * Lspan for cx in crit_x):
            continue
        v = float(values[i])
        ax.text(
            xm,
            _label_y(v, i + len(crit_x)),
            solver.format_number(v),
            ha="center",
            va="bottom" if v >= 0 else "top",
            fontsize=_FS_TINY,
            color=color,
            fontweight="500",
            zorder=7,
            clip_on=False,
        )


def _annotate_at_critical_x(
    ax: Any,
    xs: np.ndarray,
    ys: np.ndarray,
    crit: List[Tuple[float, str]],
    color: str,
    *,
    y_offset: float = 0.0,
) -> None:
    """ערך בכל נקודה קריטית (על הקו)."""
    for x, _lab in crit:
        idx = int(np.argmin(np.abs(xs - x)))
        v = float(ys[idx])
        ax.annotate(
            solver.format_number(v),
            (x, v),
            textcoords="offset points",
            xytext=(0, y_offset),
            ha="center",
            va="bottom",
            fontsize=_FS_TINY,
            color=color,
            fontweight="500",
            zorder=6,
        )


def _annotate_shear_signs(ax: Any, xs: np.ndarray, shears: np.ndarray) -> None:
    """סימני + / − באזורי גזירה חיוביים/שליליים."""
    xs = np.asarray(xs, dtype=float)
    shears = np.asarray(shears, dtype=float)
    i = 0
    while i < len(xs) - 1:
        sign = 1 if shears[i] >= 0 else -1
        j = i + 1
        while j < len(xs) - 1 and (shears[j] >= 0) == (sign >= 0):
            j += 1
        x0, x1 = xs[i], xs[j]
        if x1 - x0 > 1e-6:
            xm = 0.5 * (x0 + x1)
            ym = 0.5 * (float(shears[i]) + float(shears[j]))
            label = "+" if sign >= 0 else "−"
            ax.text(
                xm,
                ym,
                label,
                ha="center",
                va="center",
                fontsize=_FS_TINY,
                color=_BLUE,
                fontweight="500",
                zorder=5,
            )
        i = j


def _mark_shear_zero(ax: Any, xs: np.ndarray, shears: np.ndarray, Lf: float) -> None:
    for j in range(len(xs) - 1):
        v0, v1 = float(shears[j]), float(shears[j + 1])
        if v0 * v1 < 0:
            x0, x1 = float(xs[j]), float(xs[j + 1])
            xz = x0 - v0 * (x1 - x0) / (v1 - v0)
            yr = float(max(np.max(np.abs(shears)), 0.5))
            tick = 0.04 * yr
            ax.plot(
                [xz, xz],
                [-tick, tick],
                color=_BLUE,
                linewidth=0.9,
                alpha=0.65,
                zorder=4,
            )
            ax.text(
                xz,
                tick * 1.8,
                f"x={solver.format_number(xz)}",
                ha="center",
                va="bottom",
                fontsize=_FS_TINY,
                color=_BLUE,
                fontweight="500",
                zorder=7,
            )
            return


def build_beam_figure(
    L: float,
    loads: List[dict],
    ra_pos: float,
    rb_pos: float,
    ra_x: float,
    ra_y: float,
    rb_x: float,
    rb_y: float,
) -> Any:
    """קורה + N/Q/M — מרווחים: מידות→N (2×d), N→Q (1.5×d), Q→M (1.5×d)."""
    layout = _notebook_layout()
    y_span_beam = layout["y_top"] - layout["y_bottom"]
    xs, normals, shears, moments, crit = _notebook_diagram_series(
        L, loads, ra_pos, rb_pos, ra_x, ra_y, rb_y
    )
    n_bottom = _notebook_diagram_extent_bottom(
        layout["y_n"], normals, _notebook_diagram_scale(normals)
    )
    q_bottom = _notebook_diagram_extent_bottom(
        layout["y_q"], shears, _notebook_diagram_scale(shears)
    )
    m_bottom = _notebook_diagram_extent_bottom(
        layout["y_m"], moments, _notebook_diagram_scale(moments)
    )
    fig_bottom = min(n_bottom, q_bottom, m_bottom, layout["y_fig_bottom"])
    y_span_all = layout["y_top"] - fig_bottom
    fig_h = 2.15 * (y_span_all / y_span_beam)
    _notebook_mpl_rc()
    fig, ax = plt.subplots(1, 1, figsize=(7.8, fig_h), facecolor="none")
    _prep_figure_transparent(fig)
    _prep_axis_on_paper(ax, grid=False)
    _draw_beam_schematic(
        ax, L, loads, ra_pos, rb_pos, ra_x, ra_y, rb_y, set_limits=False
    )
    n_bottom = _draw_n_schematic(ax, L, xs, normals, crit, layout)
    q_bottom = _draw_q_schematic(ax, L, xs, shears, crit, layout)
    m_bottom = _draw_m_schematic(ax, L, xs, moments, crit, layout)
    pad_x = max(0.22, 0.055 * float(L))
    ax.set_xlim(-pad_x, float(L) + pad_x)
    ax.set_ylim(min(n_bottom, q_bottom, m_bottom, layout["y_fig_bottom"]), layout["y_top"])
    fig.subplots_adjust(left=0.09, right=0.99, top=0.98, bottom=0.06)
    return fig


def build_forces_figure(
    L: float,
    loads: List[dict],
    ra_pos: float,
    rb_pos: float,
    ra_x: float,
    ra_y: float,
    rb_x: float,
    rb_y: float,
) -> Any:
    """דיאגרמות N, Q, M — מתחת לקורה בשמאל."""
    positions = solver.critical_x_positions(loads, L, ra_pos, rb_pos)
    xs = solver.beam_plot_x_coords(L, positions)
    moments = np.array([solver.bending_moment(x, loads, ra_y, rb_y, ra_pos, rb_pos) for x in xs])
    shears = np.array([solver.shear_force(x, loads, ra_y, rb_y, ra_pos, rb_pos) for x in xs])
    normals = np.array([solver.normal_force(x, loads, ra_x, ra_pos) for x in xs])
    _notebook_mpl_rc()
    fig = plt.figure(figsize=(7.8, 4.6), facecolor="none")
    _prep_figure_transparent(fig)
    gs = fig.add_gridspec(
        3, 1, height_ratios=[1.0, 1.0, 1.0], hspace=0.16, left=0.2, right=0.94, top=0.98, bottom=0.08
    )
    ax_n = fig.add_subplot(gs[0])
    Lf = float(L)
    x_pad = _beam_x_pad(Lf)
    crit = station_labels(loads, L, ra_pos, rb_pos)

    _plot_n_on_beam(ax_n, xs, normals, Lf, x_pad, crit, transparent=True)
    _diagram_titles(fig, ax_n, "כוחות ציריים", f"N(x) [{_U_FORCE}]", _GREEN)

    ax_v = fig.add_subplot(gs[1], sharex=ax_n)
    _plot_q_on_beam(ax_v, xs, shears, Lf, x_pad, crit, transparent=True)
    _diagram_titles(fig, ax_v, "גזירה", f"Q(x) [{_U_FORCE}]", _BLUE)

    ax_m = fig.add_subplot(gs[2], sharex=ax_n)
    _plot_m_on_beam(ax_m, xs, moments, Lf, x_pad, crit, transparent=True)
    _diagram_titles(fig, ax_m, "מומנטים", f"M(x) [{_U_MOMENT}]", _RED)

    return fig


def build_diagram_figure(
    L: float,
    loads: List[dict],
    ra_pos: float,
    rb_pos: float,
    ra_x: float,
    ra_y: float,
    rb_x: float,
    rb_y: float,
) -> Any:
    """תמונה משולבת להורדה (קורה + דיאגרמות)."""
    _notebook_mpl_rc()
    fig = plt.figure(figsize=(7.8, 6.5), facecolor=_PAPER)
    gs = fig.add_gridspec(
        4, 1, height_ratios=[0.95, 0.88, 0.88, 0.88], hspace=0.12, left=0.14, right=0.995, top=0.98, bottom=0.06
    )
    ax_beam = fig.add_subplot(gs[0])
    ax_beam.set_facecolor(_PAPER)
    _draw_beam_schematic(ax_beam, L, loads, ra_pos, rb_pos, ra_x, ra_y, rb_y)
    positions = solver.critical_x_positions(loads, L, ra_pos, rb_pos)
    xs = solver.beam_plot_x_coords(L, positions)
    moments = np.array([solver.bending_moment(x, loads, ra_y, rb_y, ra_pos, rb_pos) for x in xs])
    shears = np.array([solver.shear_force(x, loads, ra_y, rb_y, ra_pos, rb_pos) for x in xs])
    normals = np.array([solver.normal_force(x, loads, ra_x, ra_pos) for x in xs])
    Lf = float(L)
    x_pad = _beam_x_pad(Lf)
    crit = station_labels(loads, L, ra_pos, rb_pos)

    ax_n = fig.add_subplot(gs[1])
    _plot_n_on_beam(ax_n, xs, normals, Lf, x_pad, crit, transparent=False, paper=True)
    _diagram_titles(fig, ax_n, "כוחות ציריים", f"N(x) [{_U_FORCE}]", _GREEN)

    ax_v = fig.add_subplot(gs[2], sharex=ax_n)
    _plot_q_on_beam(ax_v, xs, shears, Lf, x_pad, crit, transparent=False, paper=True)
    _diagram_titles(fig, ax_v, "גזירה", f"Q(x) [{_U_FORCE}]", _BLUE)

    ax_m = fig.add_subplot(gs[3], sharex=ax_n)
    _plot_m_on_beam(ax_m, xs, moments, Lf, x_pad, crit, transparent=False, paper=True)
    _diagram_titles(fig, ax_m, "מומנטים", f"M(x) [{_U_MOMENT}]", _RED)

    return fig


def _build_moment_panel_html(rows: List[Dict[str, Any]], loads: List[dict], L: float,
                             ra_pos: float, rb_pos: float, ra_y: float, rb_y: float) -> str:
    """רשימת מומנטים אדומה מתחת לדיאגרמות — כמו בתחתית השמאל בתמונה."""
    lines: List[str] = [
        '<div class="nb-m-panel">',
        "<h5>חישוב מומנטים בנקודות</h5>",
    ]
    stations = [(r["x"], r["label"], r["M"]) for r in rows]
    for x, lab, m_val in stations:
        lines.append(
            f'<p class="nb-line nb-red">M_{lab} = {solver.format_number(m_val)} {_U_MOMENT}</p>'
        )
    lines.append("</div>")
    return "\n".join(lines)


def _nb_line(text: str, css: str = "nb-black") -> str:
    if not str(text).strip():
        return '<p class="nb-line nb-black nb-gap">&nbsp;</p>'
    return f'<p class="nb-line {css}">{html_lib.escape(str(text))}</p>'


def _esc_num(value: float) -> str:
    """format_number → str → html.escape (escape expects str, not int/float)."""
    return html_lib.escape(str(solver.format_number(value)))


def _sym_sigma() -> str:
    return '<span class="nb-sym" aria-label="Sigma">Σ</span>'


def _sym_delta() -> str:
    return '<span class="nb-sym" aria-label="Delta">Δ</span>'


def _nb_step(text: str, css: str = "nb-eq") -> str:
    if not str(text).strip():
        return '<p class="nb-line nb-gap">&nbsp;</p>'
    return f'<p class="nb-line {css}">{html_lib.escape(str(text))}</p>'


def _nb_step_html(inner_html: str, css: str = "nb-eq") -> str:
    """שורת חישוב עם HTML בטוח (Σ, Δ, sub) — ללא escape על התוכן."""
    return f'<p class="nb-line {css}">{inner_html}</p>'


def _nb_answer_box(inner_html: str) -> str:
    return f'<p class="nb-line nb-eq"><span class="nb-box nb-box-answer">{inner_html}</span></p>'


def _shear_zero_card_html(
    loads: List[dict],
    L: float,
    ra_pos: float,
    rb_pos: float,
    ra_y: float,
    rb_y: float,
) -> str:
    """כרטיס תחתון: X = Q/q = … (מיקום מומנט מקסימלי תחת מפולג)."""
    eps = 1e-6
    for i, ld in enumerate(loads, 1):
        if ld["type"] != "distributed":
            continue
        x1, x2, w = float(ld["x1"]), float(ld["x2"]), float(ld["w"])
        if abs(w) < 1e-9 or x2 - x1 < 1e-9:
            continue
        v_start = solver.shear_force(x1 + eps, loads, ra_y, rb_y, ra_pos, rb_pos)
        q_mag = abs(w)
        v_abs = abs(v_start)
        if abs(v_start) < 1e-9:
            xz = x1
        else:
            xz = x1 - v_start / w
        if x1 - 0.01 <= xz <= x2 + 0.01:
            return (
                '<div class="nb-xzero-card">'
                '<p class="nb-xzero-title">מיקום מומנט מקסימלי — Q = 0</p>'
                f'<p class="nb-line nb-moment">X = Q/q = '
                f"{html_lib.escape(str(solver.format_number(v_abs)))}/"
                f"{html_lib.escape(str(solver.format_number(q_mag)))} = "
                f"{html_lib.escape(str(solver.format_number(xz)))} m</p>"
                "</div>"
            )
    return ""


def _moment_handwriting_note() -> str:
    return _nb_step(
        "חישוב מהלך שרטוט מומנט: גזירה חיובית (למטה) → מומנט מתעקל כלפי מטה; "
        "בנקודה שבה Q = 0 המומנט שואף למקסימום.",
        "nb-note",
    )


def _build_calc_html(
    loads: List[dict],
    L: float,
    ra_pos: float,
    rb_pos: float,
    ra_x: float,
    ra_y: float,
    rb_x: float,
    rb_y: float,
) -> str:
    eq = _equilibrium_sections(loads, ra_pos, rb_pos, ra_x, ra_y, rb_y)
    rows = _values_at_stations(loads, L, ra_pos, rb_pos, ra_x, ra_y, rb_x, rb_y)
    s = eq["sums"]
    parts: List[str] = [
        '<div class="nb-col-calc nb-flow">',
        '<div class="nb-block">',
        '<h2 class="nb-calc-title">מציאת ריאקציות — כוחות תגובה בסמכים</h2>',
    ]
    parts.append(_nb_step_html(f"{_sym_sigma()}F<sub>x</sub> = 0", "nb-eq nb-eq-start"))
    if eq["fx_lines"]:
        parts.append(
            _nb_step(
                " + ".join(eq["fx_lines"]) + f" = {solver.format_number(s['sum_fx'])}",
                "nb-eq",
            )
        )
    parts.append(
        _nb_step(
            f"Ax = −ΣFx = −({solver.format_number(s['sum_fx'])}) = "
            f"{solver.format_number(ra_x)} {_U_FORCE}",
            "nb-eq",
        )
    )
    if abs(ra_x) > 1e-9:
        parts.append(_nb_answer_box(f"Ax = {_esc_num(ra_x)} {_U_FORCE}"))
    parts.append(_nb_step(""))
    parts.append(_nb_step_html(f"{_sym_sigma()}M<sub>A</sub> = 0", "nb-eq nb-eq-start"))
    parts.append(_nb_step("סכום המומנטים סביב A:", "nb-sub nb-black"))
    if eq["ma_lines"]:
        parts.append(
            _nb_step(
                " + ".join(eq["ma_lines"])
                + f" = {solver.format_number(s['moment_about_ra'])}",
                "nb-eq",
            )
        )
    parts.append(
        _nb_step(
            f"By = {solver.format_number(s['moment_about_ra'])}/{solver.format_number(eq['arm_b'])} "
            f"= {solver.format_number(rb_y)} {_U_FORCE}",
            "nb-eq",
        )
    )
    parts.append(_nb_answer_box(f"By = {_esc_num(rb_y)} {_U_FORCE}"))
    parts.append(_nb_step(""))
    parts.append(_nb_step_html(f"{_sym_sigma()}M<sub>B</sub> = 0", "nb-eq nb-eq-start"))
    parts.append(_nb_step("סכום המומנטים סביב B:", "nb-sub nb-black"))
    if eq["mb_lines"]:
        parts.append(
            _nb_step(
                " + ".join(eq["mb_lines"])
                + f" = {solver.format_number(s['moment_about_rb'])}",
                "nb-eq",
            )
        )
    parts.append(
        _nb_step(
            f"Ay = −({solver.format_number(s['moment_about_rb'])}) / "
            f"({solver.format_number(eq['arm_a'])}) = {solver.format_number(ra_y)} {_U_FORCE}",
            "nb-eq",
        )
    )
    parts.append(_nb_answer_box(f"Ay = {_esc_num(ra_y)} {_U_FORCE}"))
    parts.append(
        _nb_step_html(
            f"{_sym_sigma()}F<sub>y</sub> + Ay + By = {solver.format_number(eq['fy_check'])}",
            "nb-eq",
        )
    )
    parts.append("</div>")

    parts.append('<div class="nb-block">')
    parts.append('<p class="nb-block-label nb-lbl-green">בדיקות חתך — כוח צירי (Δ)</p>')
    for r in rows:
        lab = r["label"]
        n_val = float(r["N"])
        n_l = float(r.get("N_left", n_val))
        n_r = float(r.get("N_right", n_val))
        if abs(n_l - n_r) > 1e-4:
            parts.append(
                _nb_step_html(
                    f"{_sym_delta()}<sub>{lab}</sub>: N<sub>L</sub> = {solver.format_number(n_l)}, "
                    f"N<sub>R</sub> = {solver.format_number(n_r)} {_U_FORCE}",
                    "nb-delta",
                )
            )
        else:
            parts.append(
                _nb_step_html(
                    f"{_sym_delta()}<sub>{lab}</sub> — N<sub>{lab}</sub> = "
                    f"{solver.format_number(n_val)} {_U_FORCE}",
                    "nb-delta",
                )
            )

    parts.append('<p class="nb-block-label nb-lbl-blue">גזירה Q</p>')
    for r in rows:
        parts.append(
            _nb_step_html(
                f"Q<sub>{r['label']}</sub> = {solver.format_number(r['Q'])} {_U_FORCE}",
                "nb-shear",
            )
        )

    parts.append('<p class="nb-block-label nb-lbl-red">מומנטים M</p>')
    for r in rows:
        parts.append(
            _nb_step_html(
                f"M<sub>{r['label']}</sub> = {solver.format_number(r['M'])} {_U_MOMENT}",
                "nb-moment",
            )
        )
    parts.append(_moment_handwriting_note())
    xzero = _shear_zero_card_html(loads, L, ra_pos, rb_pos, ra_y, rb_y)
    if xzero:
        parts.append(xzero)
    else:
        for zn in _shear_zero_notes(loads, L, ra_pos, rb_pos, ra_y, rb_y):
            parts.append(_nb_step(zn, "nb-shear"))
    parts.append("</div></div>")
    return "\n".join(parts)


def _fig_to_png_bytes(fig: Any, *, on_paper: bool = True, pad_inches: float = 0.01) -> bytes:
    """on_paper=True: PNG שקוף — משתלב בנייר המחברת; False: רקע קרם להורדה."""
    buf = io.BytesIO()
    if on_paper:
        fig.savefig(
            buf,
            format="png",
            dpi=110,
            transparent=True,
            facecolor="none",
            edgecolor="none",
            bbox_inches="tight",
            pad_inches=pad_inches,
        )
    else:
        fig.savefig(buf, format="png", dpi=110, facecolor=_PAPER, bbox_inches="tight", pad_inches=0.04)
    buf.seek(0)
    return buf.getvalue()


def build_page_html(
    loads: List[dict],
    L: float,
    ra_pos: float,
    rb_pos: float,
    ra_x: float,
    ra_y: float,
    rb_x: float,
    rb_y: float,
) -> Tuple[str, bytes]:
    fig_beam = build_beam_figure(L, loads, ra_pos, rb_pos, ra_x, ra_y, rb_x, rb_y)
    png_beam = _fig_to_png_bytes(fig_beam, on_paper=True, pad_inches=0.08)
    plt.close(fig_beam)
    png_download = png_beam
    b64_beam = base64.b64encode(png_beam).decode("ascii")
    calc = _build_calc_html(loads, L, ra_pos, rb_pos, ra_x, ra_y, rb_x, rb_y)
    body = f"""
<div class="nb-row">
  <div class="nb-col-left">
    <div class="nb-beam-zone">
      <img src="data:image/png;base64,{b64_beam}" alt="שרטוט קורה ודיאגרמות N Q M"/>
    </div>
  </div>
  {calc}
</div>
"""
    return _wrap_iframe_document(body), png_download


def _load_live_notebook_module():
    """טוען beam_notebook מחדש מהדיסק — עוקף מטמון מודול ישן של Streamlit."""
    import importlib.util

    path = Path(__file__).resolve()
    name = "beam_notebook_live"
    mod = sys.modules.get(name)
    if mod is None:
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None:
            raise ImportError(f"cannot load {path}")
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
    else:
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None:
            raise ImportError(f"cannot load {path}")
        spec.loader.exec_module(mod)
    return mod


def render_solved_notebook(
    loads: List[dict],
    L: float,
    ra_pos: float,
    rb_pos: float,
    ra_x: float,
    ra_y: float,
    rb_x: float,
    rb_y: float,
) -> None:
    if not loads:
        st.info("הוסף עומסים על הקורה (בסרגל או בלוח) כדי לראות כאן תרגיל פתור במחברת.")
        return
    nb = _load_live_notebook_module()
    nb_path = Path(nb.__file__).resolve()
    st.caption(f"דף **A4** (חצי־חצי) · קובץ: `{nb_path.name}`")
    page_html, png_bytes = nb.build_page_html(
        loads, L, ra_pos, rb_pos, ra_x, ra_y, rb_x, rb_y
    )
    try:
        st.html(page_html, width="stretch")
    except Exception:
        components.html(page_html, height=_A4_IFRAME_HEIGHT_PX, scrolling=False)
    st.download_button(
        "הורדת שרטוט קורה (PNG)",
        data=png_bytes,
        file_name="beam-solved-notebook.png",
        mime="image/png",
        key="notebook_png_download",
    )
