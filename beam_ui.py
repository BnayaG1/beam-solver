# -*- coding: utf-8 -*-
"""Streamlit UI: beam board component, session state, vision upload, diagrams."""
from __future__ import annotations

import base64
import json
import math
import random
import ssl
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
import streamlit as st

import beam_notebook
import solver

LOAD_TYPE_LABELS = {
    "point": "עומס נקודתי (Fy; אופציונלי Fx לאורך הקורה)",
    "distributed": "עומס מפולג (מפורס)",
    "moment": "מומנט טהור (זוג כוחות)",
    "inclined": "עומס אלכסוני (Fx, Fy)",
}

VISION_PROMPT = (
    "You read a statics beam exercise image. Output JSON only: keys L, ra_pos, rb_pos, loads. "
    "loads is array of objects. type must be one of: point, distributed, moment, inclined. "
    "point: x (m), Fy (kN, POSITIVE magnitude for downward load from above), optional Fx (kN, +x to the right). "
    "distributed: x1, x2, w (kN/m, POSITIVE magnitude for downward load). moment: x, M (kN*m). "
    "inclined: x, Fx (kN along +x), Fy (kN, POSITIVE magnitude for downward vertical component). "
    "SI only. If supports not marked: A at left x=0, B at x=L."
)


def inject_ui_styles() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Rubik:wght@400;500;600;700&family=Heebo:wght@400;500;600;700&display=swap');

        :root {
            --beam-bg: #eef2f8;
            --beam-card: #ffffff;
            --beam-border: #e2e8f0;
            --beam-text: #0f172a;
            --beam-muted: #64748b;
            --beam-primary: #0f766e;
            --beam-primary-soft: #ccfbf1;
            --beam-shadow: 0 12px 32px rgba(15, 23, 42, 0.07);
            --beam-radius: 20px;
        }

        html, body, [class*="css"], .stApp, .stApp * {
            font-family: 'Rubik', 'Heebo', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important;
        }

        .stApp {
            background:
                radial-gradient(circle at 12% 0%, rgba(20, 184, 166, 0.12), transparent 28rem),
                radial-gradient(circle at 88% 8%, rgba(37, 99, 235, 0.08), transparent 24rem),
                linear-gradient(180deg, #f8fafc 0%, var(--beam-bg) 100%);
            color: var(--beam-text);
        }

        .block-container {
            padding-top: 1.25rem;
            padding-bottom: 2.5rem;
            max-width: none;
            width: 100%;
            padding-left: 1.5rem;
            padding-right: 1.5rem;
        }

        section[data-testid="stSidebar"] {
            display: none !important;
        }

        /* —— Sidebar: light tablet panel (hidden; styles kept for optional future use) —— */
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
            border-left: 1px solid var(--beam-border);
        }

        section[data-testid="stSidebar"] > div {
            padding: 1rem 0.85rem 2rem;
        }

        section[data-testid="stSidebar"] h1,
        section[data-testid="stSidebar"] h2,
        section[data-testid="stSidebar"] h3,
        section[data-testid="stSidebar"] label,
        section[data-testid="stSidebar"] p,
        section[data-testid="stSidebar"] span,
        section[data-testid="stSidebar"] small {
            color: var(--beam-text) !important;
        }

        .beam-sidebar-heading {
            margin: 0 0 0.35rem 0;
            font-size: 1.05rem;
            font-weight: 700;
            color: #0f172a !important;
            letter-spacing: -0.02em;
        }

        .beam-sidebar-caption {
            margin: 0 0 1rem 0;
            font-size: 0.82rem;
            color: var(--beam-muted) !important;
            line-height: 1.45;
        }

        section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlockBorderWrapper"] {
            background: var(--beam-card);
            border: 1px solid var(--beam-border) !important;
            border-radius: var(--beam-radius);
            padding: 0.85rem 0.9rem 1rem;
            margin-bottom: 0.85rem;
            box-shadow: 0 4px 14px rgba(15, 23, 42, 0.04);
        }

        section[data-testid="stSidebar"] [data-testid="stNumberInput"],
        section[data-testid="stSidebar"] [data-testid="stSelectbox"] {
            margin-bottom: 0.65rem;
        }

        section[data-testid="stSidebar"] [data-testid="stNumberInput"] label p,
        section[data-testid="stSidebar"] [data-testid="stSelectbox"] label p {
            font-size: 0.84rem !important;
            font-weight: 600 !important;
            margin-bottom: 0.25rem !important;
        }

        section[data-testid="stSidebar"] div[data-baseweb="input"] > div,
        section[data-testid="stSidebar"] div[data-baseweb="select"] > div {
            border-radius: 12px !important;
            min-height: 2.65rem;
            background: #f8fafc !important;
            border-color: #cbd5e1 !important;
        }

        section[data-testid="stSidebar"] [data-testid="stExpander"] {
            background: var(--beam-card);
            border: 1px solid var(--beam-border) !important;
            border-radius: var(--beam-radius);
            margin-bottom: 0.65rem;
            box-shadow: 0 4px 14px rgba(15, 23, 42, 0.04);
            overflow: hidden;
        }

        section[data-testid="stSidebar"] [data-testid="stExpander"] details {
            border: none;
        }

        section[data-testid="stSidebar"] [data-testid="stExpander"] summary {
            padding: 0.75rem 0.9rem;
            font-weight: 700;
        }

        /* Hide broken Material icon text (keyboard_arrow_down) on expanders */
        section[data-testid="stSidebar"] [data-testid="stExpander"] summary svg {
            flex-shrink: 0;
        }

        section[data-testid="stSidebar"] [data-testid="stExpander"] summary > div > div > div:last-child {
            font-size: 0 !important;
            width: 1.1rem;
            min-width: 1.1rem;
            overflow: hidden;
        }

        section[data-testid="stSidebar"] [data-testid="stExpander"] summary > div > div > div:last-child::before {
            content: '▾';
            font-size: 0.95rem;
            color: #64748b;
            font-family: 'Rubik', 'Heebo', sans-serif !important;
        }

        section[data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stVerticalBlock"] {
            padding: 0 0.85rem 0.9rem;
        }

        .beam-hero {
            padding: 1.35rem 1.6rem;
            border-radius: 22px;
            background:
                linear-gradient(135deg, rgba(15, 118, 110, 0.95), rgba(30, 64, 175, 0.92));
            box-shadow: var(--beam-shadow);
            color: white;
            margin-bottom: 1rem;
        }

        .beam-hero h1 {
            margin: 0 0 4px 0;
            font-size: 1.65rem;
            font-weight: 700;
            letter-spacing: -0.03em;
        }

        .beam-hero p {
            margin: 0;
            max-width: 720px;
            color: rgba(255,255,255,0.88);
            font-size: 0.92rem;
            line-height: 1.5;
        }

        .beam-section-title {
            margin: 1rem 0 0.35rem 0;
            font-weight: 700;
            font-size: 1.2rem;
            color: #0f172a;
            letter-spacing: -0.02em;
        }

        .beam-subtle {
            color: var(--beam-muted);
            font-size: 0.88rem;
            line-height: 1.45;
            margin: 0 0 0.75rem 0;
        }

        .beam-panel {
            background: var(--beam-card);
            border: 1px solid var(--beam-border);
            border-radius: var(--beam-radius);
            padding: 1rem 1.1rem 1.15rem;
            box-shadow: var(--beam-shadow);
            margin-bottom: 1rem;
        }

        .beam-board-shell {
            margin-top: 0.25rem;
        }

        .beam-board-shell [data-testid="stCustomComponentV1"],
        .beam-board-shell iframe {
            border-radius: 18px;
            overflow: hidden;
        }

        div[data-testid="stMetric"] {
            background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
            border: 1px solid var(--beam-border);
            border-radius: 16px;
            padding: 14px 16px 12px;
            box-shadow: 0 6px 18px rgba(15, 23, 42, 0.05);
        }

        div[data-testid="stMetricLabel"] p {
            color: var(--beam-muted) !important;
            font-weight: 600 !important;
            font-size: 0.82rem !important;
        }

        div[data-testid="stMetricValue"] {
            color: var(--beam-text);
            font-weight: 700;
        }

        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background: rgba(15, 23, 42, 0.04);
            border-radius: 14px;
            padding: 6px;
        }

        .stTabs [data-baseweb="tab"] {
            border-radius: 10px;
            padding: 8px 14px;
            font-weight: 600;
        }

        .stButton > button,
        div[data-testid="stFormSubmitButton"] button {
            border-radius: 12px;
            font-weight: 600;
        }

        div[data-baseweb="input"] > div,
        div[data-baseweb="select"] > div,
        textarea {
            border-radius: 12px !important;
        }

        [data-testid="stFileUploader"] {
            border-radius: 14px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.components.v1.html(
        """
        <style>
            html, body {
                width: 0;
                height: 0;
                margin: 0;
                padding: 0;
                overflow: hidden;
            }
        </style>
        <script async src="https://www.googletagmanager.com/gtag/js?id=G-JXG9XLBXL3"></script>
        <script>
          window.dataLayer = window.dataLayer || [];
          function gtag(){dataLayer.push(arguments);}
          gtag('js', new Date());
          gtag('config', 'G-JXG9XLBXL3');
        </script>
        """,
        height=0,
        scrolling=False,
    )


def _clear_load_session_keys(max_slots: int = 20) -> None:
    for i in range(max_slots):
        for key in (
            f"load_type_{i}",
            f"point_x_{i}",
            f"point_Fy_{i}",
            f"point_dir_{i}",
            f"point_Fx_{i}",
            f"dist_x1_{i}",
            f"dist_x2_{i}",
            f"dist_w_{i}",
            f"moment_x_{i}",
            f"moment_M_{i}",
            f"inclined_x_{i}",
            f"inclined_Fx_{i}",
            f"inclined_Fy_{i}",
        ):
            st.session_state.pop(key, None)


def canvas_notebook_ready() -> bool:
    """מחברת וחישובי תוצאות מלאים רק אחרי Apply changes בלוח."""
    return bool(st.session_state.get("beam_canvas_applied", True))


def _apply_analysis_loads_to_session(
    L: float,
    loads: List[dict],
    *,
    commit_for_notebook: bool = True,
    ra: Optional[float] = None,
    rb: Optional[float] = None,
) -> None:
    """כותב עומסים ל-session + מסנכרן ללוח. commit_for_notebook=False אחרי תרגיל אקראי (דורש Apply)."""
    Lm = max(0.1, float(L))
    _clear_load_session_keys()
    st.session_state["beam_L"] = Lm
    support_mode = str(st.session_state.get("beam_support_mode", "simple")).lower()
    if support_mode == "fixed":
        st.session_state["beam_ra_pos"] = 0.0
        st.session_state["beam_rb_pos"] = Lm
    else:
        if ra is None or rb is None:
            st.session_state["beam_ra_pos"] = 0.0
            st.session_state["beam_rb_pos"] = Lm
        else:
            ra_v = max(0.0, min(Lm, float(ra)))
            rb_v = max(0.0, min(Lm, float(rb)))
            if rb_v < ra_v:
                ra_v, rb_v = rb_v, ra_v
            st.session_state["beam_ra_pos"] = ra_v
            st.session_state["beam_rb_pos"] = rb_v

    n = max(0, min(len(loads), 20))
    st.session_state["beam_load_count"] = n
    for i in range(n):
        ld = loads[i]
        t = str(ld.get("type", "point"))
        st.session_state[f"load_type_{i}"] = t
        if t == "point":
            fy_val = float(ld.get("Fy", -10.0))
            st.session_state[f"point_x_{i}"] = max(0.0, min(Lm, float(ld.get("x", Lm / 2))))
            st.session_state[f"point_dir_{i}"] = "up" if fy_val > 0 else "down"
            st.session_state[f"point_Fy_{i}"] = abs(fy_val)
            st.session_state[f"point_Fx_{i}"] = float(ld.get("Fx", 0.0))
        elif t == "distributed":
            x1 = max(0.0, min(Lm, float(ld.get("x1", 0.0))))
            x2 = max(0.0, min(Lm, float(ld.get("x2", Lm))))
            if x2 < x1:
                x1, x2 = x2, x1
            st.session_state[f"dist_x1_{i}"] = x1
            st.session_state[f"dist_x2_{i}"] = x2
            st.session_state[f"dist_w_{i}"] = abs(float(ld.get("w", -1.0)))
        elif t == "moment":
            st.session_state[f"moment_x_{i}"] = max(0.0, min(Lm, float(ld.get("x", Lm / 2))))
            st.session_state[f"moment_M_{i}"] = float(ld.get("M", 10.0))
        else:
            fy_val = float(ld.get("Fy", -10.0))
            st.session_state[f"inclined_x_{i}"] = max(0.0, min(Lm, float(ld.get("x", Lm / 2))))
            st.session_state[f"inclined_Fx_{i}"] = float(ld.get("Fx", 0.0))
            st.session_state[f"inclined_Fy_{i}"] = abs(fy_val)

    snap_pts: List[float] = []
    for ld in loads:
        t = ld.get("type")
        if t == "point" or t == "moment" or t == "inclined":
            snap_pts.append(max(0.0, min(Lm, float(ld.get("x", 0.0)))))
        elif t == "distributed":
            snap_pts.append(max(0.0, min(Lm, float(ld.get("x1", 0.0)))))
            snap_pts.append(max(0.0, min(Lm, float(ld.get("x2", 0.0)))))
    st.session_state["beam_snap_points"] = sorted(set(round(x, 3) for x in snap_pts))

    session_loads = loads_from_sidebar_session(Lm, n)
    st.session_state["_beam_canvas_last_export"] = internal_loads_to_canvas_items(session_loads)
    st.session_state["_beam_board_nonce"] = time.time_ns()
    if commit_for_notebook:
        st.session_state["beam_canvas_loads"] = session_loads
        st.session_state["beam_canvas_applied"] = True
    else:
        st.session_state.pop("beam_canvas_loads", None)
        st.session_state["beam_canvas_applied"] = False


MIN_LOAD_POINT_SPACING = 0.9


def _beam_station_bounds(L: float) -> Tuple[float, float]:
    """טווח מותר לנקודות עומס: לפחות 0.9 m מכל קצה קורה."""
    Lm = max(MIN_LOAD_POINT_SPACING, float(L))
    c = MIN_LOAD_POINT_SPACING
    if Lm < 2.0 * c - 1e-9:
        return 0.0, Lm
    return c, Lm - c


def _clamp_station_on_beam(x: float, L: float, *, decimals: Optional[int]) -> float:
    lo, hi = _beam_station_bounds(L)
    return _round_to_decimals(max(lo, min(hi, float(x))), decimals)


def _round_to_decimals(x: float, decimals: Optional[int]) -> float:
    if decimals is None:
        return float(x)
    if decimals <= 0:
        return float(int(round(float(x))))
    return round(float(x), int(decimals))


def _enforce_min_station_spacing(
    L: float, loads: List[dict], *, min_spacing: float = MIN_LOAD_POINT_SPACING, decimals: Optional[int]
) -> List[dict]:
    """אכיפה: לא יהיה מרחק קטן מ-min_spacing בין אף שתי נקודות מישור (x, x1, x2)."""
    Lm = max(0.1, float(L))
    # refs contains load-stations plus fixed beam ends (0, L)
    refs: List[Tuple[int, str]] = [(-1, "beam_left"), (-2, "beam_right")]
    for i, ld in enumerate(loads):
        t = str(ld.get("type", ""))
        if t == "distributed":
            refs.append((i, "x1"))
            refs.append((i, "x2"))
        elif t in ("point", "moment", "inclined"):
            refs.append((i, "x"))

    def get_val(ref: Tuple[int, str]) -> float:
        i, k = ref
        if i == -1:
            return 0.0
        if i == -2:
            return float(Lm)
        return float(loads[i].get(k, 0.0))

    def set_val(ref: Tuple[int, str], v: float) -> None:
        i, k = ref
        if i < 0:
            return
        vv = max(0.0, min(Lm, float(v)))
        loads[i][k] = _round_to_decimals(vv, decimals)

    # Normalize first (clamp + order for distributed)
    for i, ld in enumerate(loads):
        t = str(ld.get("type", ""))
        if t == "distributed":
            x1 = max(0.0, min(Lm, float(ld.get("x1", 0.0))))
            x2 = max(0.0, min(Lm, float(ld.get("x2", Lm))))
            if x2 < x1:
                x1, x2 = x2, x1
            ld["x1"] = _round_to_decimals(x1, decimals)
            ld["x2"] = _round_to_decimals(x2, decimals)
            if float(ld["x2"]) - float(ld["x1"]) < min_spacing:
                x2n = min(Lm, float(ld["x1"]) + min_spacing)
                x1n = float(ld["x1"])
                if x2n - x1n < min_spacing:
                    x1n = max(0.0, Lm - min_spacing)
                    x2n = Lm
                ld["x1"] = _round_to_decimals(x1n, decimals)
                ld["x2"] = _round_to_decimals(x2n, decimals)
        elif t in ("point", "moment", "inclined"):
            ld["x"] = _round_to_decimals(max(0.0, min(Lm, float(ld.get("x", Lm / 2)))), decimals)

    if len(refs) < 3:
        return loads

    # Iteratively enforce spacing (forward/backward sweeps)
    for _ in range(6):
        def _ref_sort_key(r: Tuple[int, str]) -> Tuple[float, int]:
            v = get_val(r)
            # Tie-breaker so beam ends behave as immovable extremes:
            # - left end comes before any load at x=0
            # - right end comes after any load at x=L
            if r[0] == -1:
                pr = 0
            elif r[0] == -2:
                pr = 2
            else:
                pr = 1
            return (v, pr)

        refs_sorted = sorted(refs, key=_ref_sort_key)
        # Forward sweep
        prev = get_val(refs_sorted[0])
        for r in refs_sorted[1:]:
            v = get_val(r)
            if v < prev + min_spacing - 1e-12:
                v = prev + min_spacing
                set_val(r, v)
            prev = get_val(r)

        # Backward if overflow
        refs_sorted = sorted(refs, key=_ref_sort_key)
        for j in range(len(refs_sorted) - 2, -1, -1):
            nxt = get_val(refs_sorted[j + 1])
            v = get_val(refs_sorted[j])
            if v > nxt - min_spacing + 1e-12:
                set_val(refs_sorted[j], nxt - min_spacing)

        # Re-normalize distributed spans after moves
        for i, ld in enumerate(loads):
            if str(ld.get("type", "")) != "distributed":
                continue
            x1 = max(0.0, min(Lm, float(ld.get("x1", 0.0))))
            x2 = max(0.0, min(Lm, float(ld.get("x2", Lm))))
            if x2 < x1:
                x1, x2 = x2, x1
            if x2 - x1 < min_spacing:
                x2 = min(Lm, x1 + min_spacing)
                if x2 - x1 < min_spacing:
                    x1 = max(0.0, Lm - min_spacing)
                    x2 = Lm
            ld["x1"] = _round_to_decimals(x1, decimals)
            ld["x2"] = _round_to_decimals(x2, decimals)

    return loads


def _enforce_beam_end_clearance(
    L: float,
    loads: List[dict],
    *,
    clearance: float = MIN_LOAD_POINT_SPACING,
    decimals: Optional[int],
) -> List[dict]:
    """לפחות clearance בין קצה קורה (0, L) לכל נקודת מישור."""
    Lm = max(MIN_LOAD_POINT_SPACING, float(L))
    lo_b, hi_b = _beam_station_bounds(Lm)
    for ld in loads:
        t = str(ld.get("type", ""))
        if t == "distributed":
            x1 = float(ld.get("x1", 0.0))
            x2 = float(ld.get("x2", Lm))
            if x2 < x1:
                x1, x2 = x2, x1
            if x1 < lo_b - 1e-9:
                x1 = lo_b
            if x2 > hi_b + 1e-9:
                x2 = hi_b
            if x2 - x1 < clearance:
                if x1 + clearance <= hi_b + 1e-9:
                    x2 = min(hi_b, x1 + clearance)
                elif x2 - clearance >= lo_b - 1e-9:
                    x1 = max(lo_b, x2 - clearance)
            ld["x1"] = _round_to_decimals(x1, decimals)
            ld["x2"] = _round_to_decimals(x2, decimals)
        elif t in ("point", "moment", "inclined"):
            ld["x"] = _clamp_station_on_beam(float(ld.get("x", Lm / 2)), Lm, decimals=decimals)
    return loads


def _dedupe_same_type_same_station(
    loads: List[dict], *, decimals: Optional[int]
) -> List[dict]:
    """
    מוודא שלא יהיו שני עומסים מאותו type בדיוק על אותה תחנה (אחרי עיגול).
    זה אמור להיות נדיר בגלל כלל ה-0.9, אבל משמש כרשת ביטחון.
    """

    def q(v: float) -> float:
        return _round_to_decimals(float(v), decimals)

    seen: set = set()
    out: List[dict] = []
    for ld in loads:
        t = str(ld.get("type", ""))
        if t == "distributed":
            x1 = q(ld.get("x1", 0.0))
            x2 = q(ld.get("x2", 0.0))
            key = (t, min(x1, x2), max(x1, x2))
        else:
            x = q(ld.get("x", 0.0))
            # עבור point / inclined / moment: אותו type + אותו x נחשב "אותו מקום"
            key = (t, x)
        if key in seen:
            continue
        seen.add(key)
        out.append(ld)
    return out


def _station_xs_from_loads(loads: List[dict]) -> List[float]:
    pts: List[float] = []
    for ld in loads:
        pts.extend(_station_xs_from_load(ld))
    return pts


def _fix_vertical_down_on_distributed_edges(
    rng: random.Random,
    L: float,
    loads: List[dict],
    *,
    decimals: int,
) -> List[dict]:
    """עומס אנכי יורד לא יישב על קצה של מפורס (אחרי תזוזות/עיגול)."""
    Lm = max(0.1, float(L))
    for ld in loads:
        if str(ld.get("type", "")) != "point":
            continue
        if float(ld.get("Fy", 0.0)) >= 0:
            continue
        x0 = _round_to_decimals(float(ld.get("x", 0.0)), decimals)
        if not _on_distributed_edge(x0, loads, decimals=decimals):
            continue
        others = [s for s in _station_xs_from_loads(loads) if abs(s - x0) > 1e-9]
        if decimals == 1:
            new_x = _pick_spaced_x_medium(rng, Lm, others, loads)
            ld["x"] = _quantize_medium_x(new_x)
        else:
            new_x = _pick_spaced_x(rng, Lm, others, decimals=decimals)
            ld["x"] = _quantize_hard_x(new_x)
    return loads


def _rand_x(rng: random.Random, L: float, margin: float = 0.12) -> float:
    lo = max(0.0, L * margin)
    hi = max(lo + 0.2, L * (1.0 - margin))
    return max(0.0, min(L, rng.uniform(lo, hi)))


def _rnd_dec1(rng: random.Random, lo: float, hi: float) -> float:
    return round(rng.uniform(lo, hi), 1)


def _rnd_dec2(rng: random.Random, lo: float, hi: float) -> float:
    return round(rng.uniform(lo, hi), 2)


def _quantize_hard_x(x: float) -> float:
    """קשה (Master): עד שתי ספרות אחרי הנקודה."""
    return round(float(x), 2)


def _quantize_medium_x(x: float) -> float:
    """בינוני: עד ספרה אחת אחרי הנקודה."""
    return round(round(float(x) * 10) / 10.0, 1)


def _rand_x_dec1(rng: random.Random, L: float, margin: float = 0.12) -> float:
    return round(_rand_x(rng, L, margin), 1)


def _inside_distributed_span(x: float, loads: List[dict]) -> bool:
    """בתוך עומס מפורס (לא על הקצה)."""
    xv = float(x)
    for ld in loads:
        if str(ld.get("type", "")) != "distributed":
            continue
        lo = min(float(ld["x1"]), float(ld["x2"]))
        hi = max(float(ld["x1"]), float(ld["x2"]))
        if lo + 1e-9 < xv < hi - 1e-9:
            return True
    return False


def _on_distributed_edge(x: float, loads: List[dict], *, decimals: int) -> bool:
    """האם x יושב בדיוק על קצה (x1/x2) של עומס מפורס (אחרי עיגול)."""
    xv = round(float(x), decimals)
    for ld in loads:
        if str(ld.get("type", "")) != "distributed":
            continue
        x1 = round(float(ld.get("x1", 0.0)), decimals)
        x2 = round(float(ld.get("x2", 0.0)), decimals)
        if xv == x1 or xv == x2:
            return True
    return False


def _random_vertical_fy(rng: random.Random, mag: float, *, up_prob: float) -> float:
    """מייצר Fy לעומס אנכי עם סיכוי ל'עולה'."""
    direction = "up" if rng.random() < float(up_prob) else "down"
    return float(solver.point_magnitude_to_fy(float(mag), direction))


def _distributed_spans_overlap(ld_a: dict, ld_b: dict) -> bool:
    """חפיפה אמיתית בין שני מפורסים (לא רק מגע בקצה)."""
    if str(ld_a.get("type", "")) != "distributed" or str(ld_b.get("type", "")) != "distributed":
        return False
    lo1 = min(float(ld_a["x1"]), float(ld_a["x2"]))
    hi1 = max(float(ld_a["x1"]), float(ld_a["x2"]))
    lo2 = min(float(ld_b["x1"]), float(ld_b["x2"]))
    hi2 = max(float(ld_b["x1"]), float(ld_b["x2"]))
    return min(hi1, hi2) - max(lo1, lo2) > 1e-9


def _pick_spaced_x_medium(
    rng: random.Random,
    L: float,
    stations: List[float],
    loads: List[dict],
    *,
    margin: float = 0.12,
    max_tries: int = 120,
) -> float:
    Lm = max(MIN_LOAD_POINT_SPACING, float(L))
    lo_end, hi_end = _beam_station_bounds(Lm)
    lo = max(lo_end, Lm * margin)
    hi = min(hi_end, Lm * (1.0 - margin))
    if hi - lo < MIN_LOAD_POINT_SPACING:
        lo, hi = lo_end, hi_end
    for _ in range(max_tries):
        x = _quantize_medium_x(_clamp_on_beam(rng.uniform(lo, hi), Lm))
        if _too_close_to_stations(x, stations):
            continue
        if _inside_distributed_span(x, loads):
            continue
        return x
    n_slots = max(2, int(Lm / MIN_LOAD_POINT_SPACING) + 1)
    for k in range(n_slots):
        cand = _quantize_medium_x(k * Lm / (n_slots - 1) if n_slots > 1 else Lm / 2)
        if not _too_close_to_stations(cand, stations) and not _inside_distributed_span(
            cand, loads
        ):
            return cand
    return _quantize_medium_x(Lm / 2)


def _add_distributed_load_medium(
    rng: random.Random,
    L: float,
    loads: List[dict],
    stations: List[float],
    *,
    w_lo: float = 1.0,
    w_hi: float = 4.5,
) -> bool:
    Lm = max(MIN_LOAD_POINT_SPACING, float(L))
    span_lo = max(MIN_LOAD_POINT_SPACING, 0.25 * Lm)
    for _ in range(80):
        lo_end, hi_end = _beam_station_bounds(Lm)
        x1 = _pick_spaced_x_medium(rng, Lm, stations, loads, margin=0.08)
        span = _rnd_dec1(rng, max(MIN_LOAD_POINT_SPACING, 0.25 * Lm), max(MIN_LOAD_POINT_SPACING + 0.1, 0.65 * Lm))
        x2 = _quantize_medium_x(min(hi_end, x1 + span))
        if x2 > Lm or x2 - x1 < MIN_LOAD_POINT_SPACING:
            continue
        if _too_close_to_stations(x2, stations):
            continue
        candidate = {"type": "distributed", "x1": x1, "x2": x2, "w": 0.0}
        if any(_distributed_spans_overlap(candidate, ld) for ld in loads):
            continue
        loads.append(
            {
                "type": "distributed",
                "x1": x1,
                "x2": x2,
                "w": _quantize_medium_x(
                    solver.downward_intensity_to_w(_rnd_dec1(rng, w_lo, w_hi))
                ),
            }
        )
        stations.extend([x1, x2])
        return True
    return False


def _medium_inclined_load(
    rng: random.Random, x: float, *, mag: Optional[float] = None
) -> dict:
    """עומס אלכסוני: זווית ורכיבים עד ספרה אחת אחרי הנקודה."""
    angle_deg = _rnd_dec1(rng, 20.0, 70.0)
    m = _rnd_dec1(rng, 4.0, 12.0) if mag is None else _quantize_medium_x(mag)
    incl_dir = "dl" if rng.random() < 0.5 else "dr"
    rad = math.radians(angle_deg)
    c, s = math.cos(rad), math.sin(rad)
    fx = (-m * c) if incl_dir == "dl" else (m * c)
    return {
        "type": "inclined",
        "x": _quantize_medium_x(x),
        "Fx": _quantize_medium_x(fx),
        "Fy": _quantize_medium_x(-m * s),
        "inclAngle": _quantize_medium_x(angle_deg),
        "inclDir": incl_dir,
    }


def _hard_inclined_load(rng: random.Random, x: float) -> dict:
    """עומס אלכסוני (Master): עד שתי ספרות אחרי הנקודה."""
    angle_deg = _rnd_dec2(rng, 20.0, 70.0)
    m = _rnd_dec2(rng, 4.0, 12.0)
    incl_dir = "dl" if rng.random() < 0.5 else "dr"
    rad = math.radians(angle_deg)
    c, s = math.cos(rad), math.sin(rad)
    fx = (-m * c) if incl_dir == "dl" else (m * c)
    return {
        "type": "inclined",
        "x": _quantize_hard_x(x),
        "Fx": _quantize_hard_x(fx),
        "Fy": _quantize_hard_x(-m * s),
        "inclAngle": _quantize_hard_x(angle_deg),
        "inclDir": incl_dir,
    }


def _hard_axial_point(rng: random.Random, x: float) -> dict:
    """עומס צירי (Master): Fx בלבד, עד שתי ספרות."""
    fx_mag = _rnd_dec2(rng, 2.0, 14.0)
    fx_sign = -1.0 if rng.random() < 0.5 else 1.0
    return {
        "type": "point",
        "x": _quantize_hard_x(x),
        "Fy": 0.0,
        "Fx": _quantize_hard_x(fx_sign * fx_mag),
    }


def _clamp_on_beam(x: float, L: float) -> float:
    return max(0.0, min(float(L), float(x)))


def _station_xs_from_load(ld: dict) -> List[float]:
    t = str(ld.get("type", ""))
    if t == "distributed":
        return [float(ld["x1"]), float(ld["x2"])]
    if t in ("point", "moment", "inclined"):
        return [float(ld["x"])]
    return []


def _too_close_to_stations(x: float, stations: List[float]) -> bool:
    for s in stations:
        if abs(float(x) - float(s)) < MIN_LOAD_POINT_SPACING - 1e-9:
            return True
    return False


def _pick_spaced_x(
    rng: random.Random,
    L: float,
    stations: List[float],
    *,
    decimals: int = 1,
    margin: float = 0.12,
    max_tries: int = 100,
    loads: Optional[List[dict]] = None,
) -> float:
    """מיקום על הקורה [0,L], לפחות 0.9 m מכל נקודת מישור קיימת."""
    Lm = max(MIN_LOAD_POINT_SPACING, float(L))
    lo_end, hi_end = _beam_station_bounds(Lm)
    lo = max(lo_end, Lm * margin)
    hi = min(hi_end, Lm * (1.0 - margin))
    if hi - lo < MIN_LOAD_POINT_SPACING:
        lo, hi = lo_end, hi_end
    for _ in range(max_tries):
        raw = rng.uniform(lo, hi)
        x = int(round(raw)) if decimals == 0 else round(raw, decimals)
        x = _clamp_station_on_beam(x, Lm, decimals=decimals if decimals else None)
        if decimals == 0:
            x = int(round(x))
        if _too_close_to_stations(x, stations):
            continue
        if loads is not None and _inside_distributed_span(x, loads):
            continue
        return x
    n_slots = max(2, int(Lm / MIN_LOAD_POINT_SPACING) + 1)
    for k in range(n_slots):
        cand = k * Lm / (n_slots - 1) if n_slots > 1 else Lm / 2
        cand = int(round(cand)) if decimals == 0 else round(cand, decimals)
        cand = _clamp_on_beam(cand, Lm)
        if not _too_close_to_stations(cand, stations) and (
            loads is None or not _inside_distributed_span(cand, loads)
        ):
            return cand
    return _clamp_on_beam(Lm / 2, Lm)


def _add_distributed_load(
    rng: random.Random,
    L: float,
    loads: List[dict],
    stations: List[float],
    *,
    decimals: int,
    w_lo: float,
    w_hi: float,
    span_lo: Optional[float] = None,
    span_hi: Optional[float] = None,
) -> bool:
    Lm = max(MIN_LOAD_POINT_SPACING, float(L))
    span_lo = span_lo if span_lo is not None else max(MIN_LOAD_POINT_SPACING, 0.25 * Lm)
    span_hi = span_hi if span_hi is not None else max(span_lo + 0.1, 0.65 * Lm)
    for _ in range(80):
        span = _rnd_dec1(rng, span_lo, span_hi) if decimals else float(
            rng.randint(int(max(1, span_lo)), int(max(span_lo + 1, span_hi)))
        )
        lo_end, hi_end = _beam_station_bounds(Lm)
        x1 = _pick_spaced_x(rng, Lm, stations, decimals=decimals, margin=0.08)
        x2 = round(min(hi_end, x1 + span), decimals) if decimals else float(
            int(min(hi_end, x1 + span))
        )
        if x2 > hi_end:
            x2 = hi_end
            x1 = round(max(lo_end, x2 - span), decimals) if decimals else float(
                int(max(lo_end, x2 - span))
            )
        x1 = _clamp_station_on_beam(x1, Lm, decimals=decimals if decimals else None)
        x2 = _clamp_station_on_beam(x2, Lm, decimals=decimals if decimals else None)
        if decimals == 0:
            x1, x2 = int(round(x1)), int(round(x2))
        if x2 < x1:
            x1, x2 = x2, x1
        if x2 - x1 < MIN_LOAD_POINT_SPACING:
            continue
        if _too_close_to_stations(x2, stations):
            continue
        w_mag = _rnd_dec1(rng, w_lo, w_hi) if decimals else float(rng.randint(int(w_lo), int(w_hi)))
        loads.append(
            {
                "type": "distributed",
                "x1": x1,
                "x2": x2,
                "w": solver.downward_intensity_to_w(w_mag),
            }
        )
        stations.extend([x1, x2])
        return True
    return False


def _sanitize_random_load_geometry(L: float, loads: List[dict]) -> List[dict]:
    """עומסים בתוך הקורה בלבד; מרווח מינימלי בין נקודות מישור."""
    Lm = max(0.1, float(L))
    out: List[dict] = []
    stations: List[float] = []
    for ld in loads:
        t = str(ld.get("type", ""))
        if t == "distributed":
            x1 = _clamp_on_beam(float(ld["x1"]), Lm)
            x2 = _clamp_on_beam(float(ld["x2"]), Lm)
            if x2 < x1:
                x1, x2 = x2, x1
            if x2 - x1 < MIN_LOAD_POINT_SPACING:
                x2 = min(Lm, x1 + MIN_LOAD_POINT_SPACING)
            fixed = {**ld, "x1": x1, "x2": x2}
        elif t in ("point", "moment", "inclined"):
            x = _clamp_on_beam(float(ld["x"]), Lm)
            if _too_close_to_stations(x, stations):
                x = _clamp_on_beam(x + MIN_LOAD_POINT_SPACING, Lm)
                if _too_close_to_stations(x, stations):
                    x = _clamp_on_beam(x - 2 * MIN_LOAD_POINT_SPACING, Lm)
            fixed = {**ld, "x": x}
        else:
            fixed = dict(ld)
        out.append(fixed)
        stations.extend(_station_xs_from_load(fixed))
    return out


def _build_easy_loads(rng: random.Random, L: float) -> List[dict]:
    """קל: L=10, שני עומסים נקודתיים בלבד, מיקומים וגדלים שלמים; סיכוי 1/3 לעומס צירי אחד."""
    Lm = max(2, int(round(L)))
    stations: List[float] = []
    xs: List[float] = []
    for _ in range(2):
        xs.append(_pick_spaced_x(rng, float(Lm), stations, decimals=0, margin=0.05))
        stations.append(xs[-1])
    xs.sort()
    axial_idx = rng.randint(0, 1) if rng.random() < (1.0 / 3.0) else -1
    loads: List[dict] = []
    for i, x in enumerate(xs):
        if i == axial_idx:
            fx_mag = rng.randint(2, 12)
            fx_sign = -1.0 if rng.random() < 0.5 else 1.0
            loads.append(
                {
                    "type": "point",
                    "x": int(x),
                    "Fy": 0.0,
                    "Fx": fx_sign * float(fx_mag),
                }
            )
        else:
            mag = rng.randint(2, 12)
            loads.append(
                {
                    "type": "point",
                    "x": int(x),
                    "Fy": solver.point_magnitude_to_fy(float(mag), "down"),
                }
            )
    return loads


def _build_medium_loads(rng: random.Random, L: float) -> List[dict]:
    """בינוני (Professor): 4 עומסים; כל ערך עומס/מיקום/זווית עד ספרה אחת אחרי הנקודה."""
    kinds = [rng.choice(["point", "distributed", "moment", "inclined"]) for _ in range(4)]
    loads: List[dict] = []
    stations: List[float] = []
    for kind in kinds:
        if kind == "point":
            x = _pick_spaced_x_medium(rng, L, stations, loads)
            stations.append(x)
            mag = _rnd_dec1(rng, 3.0, 14.0)
            fy = _quantize_medium_x(_random_vertical_fy(rng, mag, up_prob=0.4))
            # עומס אנכי יורד לא יישב בדיוק על קצה של מפורס
            if fy < 0 and _on_distributed_edge(x, loads, decimals=1):
                x = _pick_spaced_x_medium(rng, L, stations, loads)
            loads.append(
                {
                    "type": "point",
                    "x": x,
                    "Fy": fy,
                }
            )
        elif kind == "distributed":
            if not _add_distributed_load_medium(rng, L, loads, stations):
                x = _pick_spaced_x_medium(rng, L, stations, loads)
                stations.append(x)
                mag = _rnd_dec1(rng, 3.0, 14.0)
                fy = _quantize_medium_x(_random_vertical_fy(rng, mag, up_prob=0.4))
                if fy < 0 and _on_distributed_edge(x, loads, decimals=1):
                    x = _pick_spaced_x_medium(rng, L, stations, loads)
                loads.append(
                    {
                        "type": "point",
                        "x": x,
                        "Fy": fy,
                    }
                )
        elif kind == "moment":
            x = _pick_spaced_x_medium(rng, L, stations, loads)
            stations.append(x)
            loads.append(
                {
                    "type": "moment",
                    "x": x,
                    "M": _quantize_medium_x(
                        _rnd_dec1(rng, 4.0, 18.0) * rng.choice([-1.0, 1.0])
                    ),
                }
            )
        else:
            x = _pick_spaced_x_medium(rng, L, stations, loads)
            stations.append(x)
            loads.append(_medium_inclined_load(rng, x))
    return loads


def _sanitize_medium_load_geometry(L: float, loads: List[dict]) -> List[dict]:
    """בינוני: עיגול לספרה אחת אחרי הנקודה על ציר הקורה."""
    out = _sanitize_random_load_geometry(L, loads)
    fixed: List[dict] = []
    for ld in out:
        t = str(ld.get("type", ""))
        if t == "distributed":
            x1 = _quantize_medium_x(_clamp_on_beam(float(ld["x1"]), L))
            x2 = _quantize_medium_x(_clamp_on_beam(float(ld["x2"]), L))
            if x2 < x1:
                x1, x2 = x2, x1
            if x2 - x1 < MIN_LOAD_POINT_SPACING:
                x2 = _quantize_medium_x(min(float(L), x1 + MIN_LOAD_POINT_SPACING))
            fixed.append(
                {
                    **ld,
                    "x1": x1,
                    "x2": x2,
                    "w": _quantize_medium_x(float(ld.get("w", 0.0))),
                }
            )
        elif t == "point":
            fixed.append(
                {
                    **ld,
                    "x": _quantize_medium_x(_clamp_on_beam(float(ld["x"]), L)),
                    "Fy": _quantize_medium_x(float(ld.get("Fy", 0.0))),
                }
            )
            if "Fx" in ld:
                fixed[-1]["Fx"] = _quantize_medium_x(float(ld["Fx"]))
        elif t == "moment":
            fixed.append(
                {
                    **ld,
                    "x": _quantize_medium_x(_clamp_on_beam(float(ld["x"]), L)),
                    "M": _quantize_medium_x(float(ld.get("M", 0.0))),
                }
            )
        elif t == "inclined":
            item = {
                **ld,
                "x": _quantize_medium_x(_clamp_on_beam(float(ld["x"]), L)),
                "Fx": _quantize_medium_x(float(ld.get("Fx", 0.0))),
                "Fy": _quantize_medium_x(float(ld.get("Fy", 0.0))),
                "inclAngle": _quantize_medium_x(float(ld.get("inclAngle", 45.0))),
            }
            fixed.append(item)
        else:
            fixed.append(ld)
    return fixed


def _build_hard_loads(rng: random.Random, L: float) -> List[dict]:
    """קשה (Master): מפורס + עומסים מעורבים כולל אנכי, אלכסוני וצירי."""
    loads: List[dict] = []
    stations: List[float] = []
    if not _add_distributed_load(
        rng,
        L,
        loads,
        stations,
        decimals=2,
        w_lo=1.5,
        w_hi=5.5,
        span_lo=max(MIN_LOAD_POINT_SPACING, 0.35 * L),
        span_hi=max(MIN_LOAD_POINT_SPACING + 0.1, 0.75 * L),
    ):
        _add_distributed_load(rng, L, loads, stations, decimals=2, w_lo=1.5, w_hi=5.5)
    n_extra = rng.randint(4, 6)
    kinds = ["point", "moment", "inclined", "axial"]
    while len(kinds) < n_extra:
        kinds.append(rng.choice(["point", "moment", "inclined", "axial"]))
    rng.shuffle(kinds)
    for kind in kinds[:n_extra]:
        x = _pick_spaced_x(rng, L, stations, decimals=2, loads=loads)
        if kind == "moment":
            stations.append(x)
            m_val = _quantize_hard_x(_rnd_dec2(rng, 4.0, 18.0) * rng.choice([-1.0, 1.0]))
            loads.append({"type": "moment", "x": _quantize_hard_x(x), "M": m_val})
        elif kind == "inclined":
            stations.append(x)
            loads.append(_hard_inclined_load(rng, x))
        elif kind == "axial":
            stations.append(x)
            loads.append(_hard_axial_point(rng, x))
        else:
            mag = _rnd_dec2(rng, 4.0, 22.0)
            fy = _quantize_hard_x(_random_vertical_fy(rng, mag, up_prob=0.4))
            if fy < 0 and _on_distributed_edge(x, loads, decimals=2):
                x = _pick_spaced_x(rng, L, stations, decimals=2, loads=loads)
            stations.append(x)
            loads.append(
                {
                    "type": "point",
                    "x": _quantize_hard_x(x),
                    "Fy": fy,
                }
            )
    return loads


def generate_random_exercise(level: str, support_mode: Optional[str] = None) -> None:
    """יוצר תרגיל אקראי לפי רמת קושי וסוג קורה (סמכים / ריתום)."""
    lvl = str(level or "easy").lower().strip()
    if lvl not in ("easy", "medium", "hard"):
        lvl = "easy"
    sm = str(support_mode or st.session_state.get("beam_support_mode", "simple")).lower().strip()
    if sm != "fixed":
        sm = "simple"
    st.session_state["beam_support_mode"] = sm
    st.session_state["random_exercise_beam_type"] = sm
    rng = random.Random()

    if lvl == "easy":
        L = 10.0
        loads = _build_easy_loads(rng, L)
        loads = _sanitize_random_load_geometry(L, loads)
        loads = _enforce_beam_end_clearance(L, loads, decimals=0)
        loads = _enforce_min_station_spacing(L, loads, decimals=0)
        loads = _dedupe_same_type_same_station(loads, decimals=0)
        loads = _enforce_beam_end_clearance(L, loads, decimals=0)
        loads = _enforce_min_station_spacing(L, loads, decimals=0)
    elif lvl == "medium":
        L = _quantize_medium_x(rng.uniform(6.0, 10.0))
        loads = _build_medium_loads(rng, L)
        loads = _sanitize_medium_load_geometry(L, loads)
        loads = _enforce_min_station_spacing(L, loads, decimals=1)
        loads = _dedupe_same_type_same_station(loads, decimals=1)
        loads = _enforce_min_station_spacing(L, loads, decimals=1)
        loads = _fix_vertical_down_on_distributed_edges(rng, L, loads, decimals=1)
        loads = _enforce_beam_end_clearance(L, loads, decimals=1)
        loads = _enforce_min_station_spacing(L, loads, decimals=1)
    else:
        L = round(rng.uniform(7.0, 16.0), 1)
        loads = _build_hard_loads(rng, L)
        loads = _sanitize_random_load_geometry(L, loads)
        loads = _enforce_min_station_spacing(L, loads, decimals=2)
        loads = _dedupe_same_type_same_station(loads, decimals=2)
        loads = _enforce_min_station_spacing(L, loads, decimals=2)
        loads = _fix_vertical_down_on_distributed_edges(rng, L, loads, decimals=2)
        loads = _enforce_beam_end_clearance(L, loads, decimals=2)
        loads = _enforce_min_station_spacing(L, loads, decimals=2)

    st.session_state["random_exercise_level"] = lvl
    ra = rb = None
    if lvl == "hard" and sm == "simple":
        # בסמכים (simple): הסמכים לא יהיו בקצוות 0 ו-L
        min_sep = max(2.2, 2.0 * MIN_LOAD_POINT_SPACING)
        for _ in range(80):
            ra_c = round(rng.uniform(0.05 * L, 0.35 * L), 1)
            rb_c = round(rng.uniform(0.65 * L, 0.95 * L), 1)
            if rb_c - ra_c >= min_sep:
                ra, rb = ra_c, rb_c
                break
        if ra is None:
            ra, rb = round(0.2 * L, 1), round(0.8 * L, 1)
    _apply_analysis_loads_to_session(L, loads, commit_for_notebook=False, ra=ra, rb=rb)
    st.session_state["_random_challenge_toast"] = True


def ensure_beam_session_defaults() -> None:
    if "beam_L" not in st.session_state:
        st.session_state.beam_L = 10.0
    if "beam_ra_pos" not in st.session_state:
        st.session_state.beam_ra_pos = 0.0
    if "beam_rb_pos" not in st.session_state:
        st.session_state.beam_rb_pos = float(st.session_state.beam_L)
    if "beam_load_count" not in st.session_state:
        st.session_state.beam_load_count = 0
    if "beam_chain_marks" not in st.session_state:
        st.session_state.beam_chain_marks = []
    if "beam_snap_points" not in st.session_state:
        st.session_state.beam_snap_points = []
    if "beam_support_mode" not in st.session_state:
        st.session_state.beam_support_mode = "simple"
    if "random_exercise_level" not in st.session_state:
        st.session_state.random_exercise_level = "easy"
    if "random_exercise_beam_type" not in st.session_state:
        st.session_state.random_exercise_beam_type = ""
    if "beam_canvas_applied" not in st.session_state:
        st.session_state.beam_canvas_applied = True
    pending_canvas_scene = st.session_state.pop("_beam_canvas_pending_scene", None)
    if isinstance(pending_canvas_scene, dict):
        apply_canvas_scene_to_session(pending_canvas_scene)


def migrate_vertical_inputs_to_positive_magnitude() -> None:
    for i in range(20):
        point_key = f"point_Fy_{i}"
        if point_key in st.session_state and float(st.session_state[point_key]) < 0:
            st.session_state[f"point_dir_{i}"] = "up"
            st.session_state[point_key] = abs(float(st.session_state[point_key]))
        for prefix in ("dist_w_", "inclined_Fy_"):
            k = f"{prefix}{i}"
            if k in st.session_state and float(st.session_state[k]) < 0:
                st.session_state[k] = abs(float(st.session_state[k]))


def get_openai_api_key() -> str:
    v = (st.session_state.get("vision_api_key_input") or "").strip()
    if v:
        return v
    try:
        s = getattr(st, "secrets", None)
        if s is not None and "OPENAI_API_KEY" in s:
            return str(s["OPENAI_API_KEY"]).strip()
    except Exception:
        pass
    return ""


def _parse_json_from_llm_text(content: str) -> Dict[str, Any]:
    t = content.strip()
    if t.startswith("```"):
        parts = t.split("```")
        chunk = parts[1].strip() if len(parts) > 1 else t
        if chunk.lower().startswith("json"):
            chunk = chunk[4:].lstrip()
        t = chunk
    return json.loads(t)


def extract_beam_from_image(
    image_bytes: bytes,
    mime_type: str,
    api_key: str,
    model: str = "gpt-4o-mini",
    api_base: str = "https://api.openai.com/v1",
) -> Dict[str, Any]:
    if not api_key:
        raise ValueError("הגדר מפתח API או OPENAI_API_KEY ב-.streamlit/secrets.toml")
    if mime_type == "image/jpg":
        mime_type = "image/jpeg"
    if mime_type not in ("image/png", "image/jpeg", "image/webp"):
        mime_type = "image/png"
    b64 = base64.standard_b64encode(image_bytes).decode("ascii")
    url = f"{api_base.rstrip('/')}/chat/completions"
    body: Dict[str, Any] = {
        "model": model,
        "temperature": 0.05,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": VISION_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime_type};base64,{b64}"},
                    },
                ],
            }
        ],
        "response_format": {"type": "json_object"},
    }

    def _post(b: Dict[str, Any]) -> Dict[str, Any]:
        r = urllib.request.Request(
            url,
            data=json.dumps(b).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            method="POST",
        )
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(r, timeout=120, context=ctx) as resp:
            return json.loads(resp.read().decode("utf-8"))

    try:
        raw = _post(body)
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        if e.code == 400 and "response_format" in body:
            del body["response_format"]
            raw = _post(body)
        else:
            raise RuntimeError(f"API {e.code}: {err}") from e
    content = raw["choices"][0]["message"]["content"]
    return _parse_json_from_llm_text(content)


def apply_vision_result_to_session_state(data: Dict[str, Any]) -> None:
    L = max(0.1, float(data.get("L", st.session_state.get("beam_L", 10.0))))
    ra = max(0.0, min(L, float(data.get("ra_pos", 0.0))))
    rb = max(0.0, min(L, float(data.get("rb_pos", L))))
    if abs(rb - ra) < 1e-6:
        rb = min(L, ra + max(0.1, 0.1 * L))
    st.session_state["beam_L"] = L
    st.session_state["beam_ra_pos"] = ra
    st.session_state["beam_rb_pos"] = rb
    loads = data.get("loads")
    if not isinstance(loads, list):
        loads = []
    n = max(0, min(len(loads), 20))
    st.session_state["beam_load_count"] = n
    for i in range(n):
        item = loads[i] if isinstance(loads[i], dict) else {}
        t = str(item.get("type", "point")).lower().strip()
        if t not in ("point", "distributed", "moment", "inclined"):
            t = "point"
        st.session_state[f"load_type_{i}"] = t
        if t == "point":
            st.session_state[f"point_x_{i}"] = max(0.0, min(L, float(item.get("x", L / 2))))
            fy_raw = float(item.get("Fy", 10.0))
            point_dir = str(item.get("direction", item.get("dir", "down"))).lower()
            st.session_state[f"point_dir_{i}"] = "up" if point_dir.startswith("up") or fy_raw < 0 else "down"
            st.session_state[f"point_Fy_{i}"] = abs(fy_raw) if fy_raw < 0 else fy_raw
            st.session_state[f"point_Fx_{i}"] = float(item.get("Fx", 0.0))
        elif t == "distributed":
            st.session_state[f"dist_x1_{i}"] = max(0.0, min(L, float(item.get("x1", 0.0))))
            st.session_state[f"dist_x2_{i}"] = max(0.0, min(L, float(item.get("x2", L))))
            w_raw = float(item.get("w", 1.0))
            st.session_state[f"dist_w_{i}"] = abs(w_raw) if w_raw < 0 else w_raw
        elif t == "moment":
            st.session_state[f"moment_x_{i}"] = max(0.0, min(L, float(item.get("x", L / 2))))
            st.session_state[f"moment_M_{i}"] = float(item.get("M", 0.0))
        else:
            st.session_state[f"inclined_x_{i}"] = max(0.0, min(L, float(item.get("x", L / 2))))
            st.session_state[f"inclined_Fx_{i}"] = float(item.get("Fx", 0.0))
            fy2 = float(item.get("Fy", 10.0))
            st.session_state[f"inclined_Fy_{i}"] = abs(fy2) if fy2 < 0 else fy2


def run_vision_on_bytes(raw: bytes, mime: str, api_key: str, model: str, base: str) -> None:
    parsed = extract_beam_from_image(raw, mime, api_key, model=model, api_base=base)
    apply_vision_result_to_session_state(parsed)
    st.session_state["vision_last_json"] = json.dumps(parsed, ensure_ascii=False, indent=2)
    st.session_state["vision_flash_ok"] = True
    st.rerun()


def loads_from_sidebar_session(L: float, load_count: int) -> List[dict]:
    loads: List[dict] = []
    for i in range(load_count):
        lt = st.session_state.get(f"load_type_{i}", "point")
        if lt == "point":
            x = float(st.session_state.get(f"point_x_{i}", L / 2))
            fy_ui = float(st.session_state.get(f"point_Fy_{i}", 10.0))
            point_dir = str(st.session_state.get(f"point_dir_{i}", "down"))
            fx = float(st.session_state.get(f"point_Fx_{i}", 0.0))
            d = {"type": "point", "x": x, "Fy": solver.point_magnitude_to_fy(fy_ui, point_dir)}
            if abs(fx) > 1e-12:
                d["Fx"] = fx
            loads.append(d)
        elif lt == "distributed":
            x1 = float(st.session_state.get(f"dist_x1_{i}", 0.0))
            x2 = float(st.session_state.get(f"dist_x2_{i}", L))
            w_ui = float(st.session_state.get(f"dist_w_{i}", 1.0))
            if x2 < x1:
                x1, x2 = x2, x1
            loads.append(
                {
                    "type": "distributed",
                    "x1": x1,
                    "x2": x2,
                    "w": solver.downward_intensity_to_w(w_ui),
                }
            )
        elif lt == "moment":
            x = float(st.session_state.get(f"moment_x_{i}", L / 2))
            mm = float(st.session_state.get(f"moment_M_{i}", 10.0))
            loads.append({"type": "moment", "x": x, "M": mm})
        else:
            x = float(st.session_state.get(f"inclined_x_{i}", L / 2))
            fx = float(st.session_state.get(f"inclined_Fx_{i}", 0.0))
            fy_ui = float(st.session_state.get(f"inclined_Fy_{i}", 10.0))
            loads.append(
                {
                    "type": "inclined",
                    "x": x,
                    "Fx": fx,
                    "Fy": solver.downward_magnitude_to_fy(fy_ui),
                }
            )
    return loads


def canvas_export_to_loads(raw_loads: List[Any], L: float) -> List[dict]:
    """ממיר עומסים מייצוא לוח השרטוט לפורמט solver."""
    loads: List[dict] = []
    if not isinstance(raw_loads, list):
        return loads
    for lu in raw_loads:
        if not isinstance(lu, dict):
            continue
        t = str(lu.get("type", "point")).lower()
        if t == "point":
            fy_raw = float(lu.get("fy", lu.get("Fy", 10.0)))
            fx = float(lu.get("fx", lu.get("Fx", 0.0)))
            d: Dict[str, Any] = {
                "type": "point",
                "x": max(0.0, min(L, float(lu.get("x", L / 2)))),
                "Fy": fy_raw if fy_raw < 0 else -abs(fy_raw),
            }
            if abs(fx) > 1e-12:
                d["Fx"] = fx
            loads.append(d)
        elif t == "distributed":
            x1 = max(0.0, min(L, float(lu.get("x1", 0.0))))
            x2 = max(0.0, min(L, float(lu.get("x2", L))))
            if x2 < x1:
                x1, x2 = x2, x1
            if x2 - x1 < MIN_LOAD_POINT_SPACING - 1e-9:
                if x1 + MIN_LOAD_POINT_SPACING <= L + 1e-9:
                    x2 = min(L, x1 + MIN_LOAD_POINT_SPACING)
                elif x2 - MIN_LOAD_POINT_SPACING >= -1e-9:
                    x1 = max(0.0, x2 - MIN_LOAD_POINT_SPACING)
                else:
                    continue
            w_mag = max(0.0, float(lu.get("w", 1.0)))
            loads.append(
                {
                    "type": "distributed",
                    "x1": x1,
                    "x2": x2,
                    "w": -w_mag,
                }
            )
        elif t == "moment":
            loads.append(
                {
                    "type": "moment",
                    "x": max(0.0, min(L, float(lu.get("x", L / 2)))),
                    "M": float(lu.get("M", 0.0)),
                }
            )
        elif t in ("inclined", "incl"):
            loads.append(
                {
                    "type": "inclined",
                    "x": max(0.0, min(L, float(lu.get("x", L / 2)))),
                    "Fx": float(lu.get("fx", lu.get("Fx", 0.0))),
                    "Fy": float(lu.get("fy", lu.get("Fy", 10.0))),
                }
            )
    return loads


def get_loads_for_analysis(L: float, load_count: int) -> List[dict]:
    """עומסים לחישובים ולמחברת — מסרגל, מ-Apply אחרון, או מייצוא לוח אחרון."""
    loads = loads_from_sidebar_session(L, load_count)
    if loads:
        return loads
    if not canvas_notebook_ready():
        return []
    cached = st.session_state.get("beam_canvas_loads")
    if isinstance(cached, list) and cached:
        return list(cached)
    exp = st.session_state.get("_beam_canvas_last_export")
    if isinstance(exp, list) and exp:
        converted = canvas_export_to_loads(exp, L)
        if converted:
            return converted
    return []


def internal_loads_to_canvas_items(loads: List[dict]) -> List[dict]:
    items: List[dict] = []
    for i, ld in enumerate(loads):
        oid = str(i)
        if ld["type"] == "point":
            items.append(
                {
                    "id": oid,
                    "type": "point",
                    "x": float(ld["x"]),
                    "fy": -float(ld["Fy"]),
                    "fx": float(ld.get("Fx", 0.0)),
                }
            )
        elif ld["type"] == "distributed":
            w_mag = max(0.0, -float(ld["w"]))
            items.append(
                {
                    "id": oid,
                    "type": "distributed",
                    "x1": float(ld["x1"]),
                    "x2": float(ld["x2"]),
                    "w": w_mag,
                }
            )
        elif ld["type"] == "moment":
            items.append({"id": oid, "type": "moment", "x": float(ld["x"]), "M": float(ld["M"])})
        else:
            fx_val = float(ld["Fx"])
            fy_mag = max(0.0, -float(ld["Fy"]))
            mag = (fx_val * fx_val + fy_mag * fy_mag) ** 0.5
            incl_dir = str(ld.get("inclDir", "dl" if fx_val < 0 else "dr"))
            if incl_dir not in ("dl", "dr"):
                incl_dir = "dl" if fx_val < 0 else "dr"
            incl_item: Dict[str, Any] = {
                "id": oid,
                "type": "incl",
                "x": float(ld["x"]),
                "fx": fx_val,
                "fy": fy_mag,
                "inclMag": mag if mag > 1e-9 else 10.0,
                "inclDir": incl_dir,
            }
            if ld.get("inclAngle") is not None:
                incl_item["inclAngle"] = _quantize_medium_x(float(ld["inclAngle"]))
            incl_item["inclMag"] = _quantize_medium_x(float(incl_item["inclMag"]))
            incl_item["fx"] = _quantize_medium_x(float(incl_item["fx"]))
            incl_item["fy"] = _quantize_medium_x(float(incl_item["fy"]))
            items.append(incl_item)
    return items


def apply_canvas_scene_to_session(result: Dict[str, Any]) -> None:
    Lm = max(0.1, float(result.get("L", 10.0)))
    st.session_state["beam_L"] = Lm
    support_mode = str(result.get("supportMode", "simple")).lower()
    st.session_state["beam_support_mode"] = "fixed" if support_mode == "fixed" else "simple"
    ra = max(0.0, min(Lm, float(result.get("ra", 0.0))))
    rb = max(0.0, min(Lm, float(result.get("rb", Lm))))
    st.session_state["beam_ra_pos"] = ra
    st.session_state["beam_rb_pos"] = rb
    raw_loads = result.get("loads")
    if not isinstance(raw_loads, list):
        raw_loads = []
    n = max(0, min(len(raw_loads), 20))
    st.session_state["beam_load_count"] = n
    for i in range(n):
        lu = raw_loads[i] if isinstance(raw_loads[i], dict) else {}
        t = str(lu.get("type", "point")).lower()
        if t not in ("point", "distributed", "moment", "inclined"):
            t = "point"
        st.session_state[f"load_type_{i}"] = t
        if t == "point":
            st.session_state[f"point_x_{i}"] = max(0.0, min(Lm, float(lu.get("x", Lm / 2))))
            fy_canvas = float(lu.get("fy", 10.0))
            st.session_state[f"point_dir_{i}"] = "up" if fy_canvas < 0 else "down"
            st.session_state[f"point_Fy_{i}"] = abs(fy_canvas)
            st.session_state[f"point_Fx_{i}"] = float(lu.get("fx", 0.0))
        elif t == "distributed":
            x1 = max(0.0, min(Lm, float(lu.get("x1", 0.0))))
            x2 = max(0.0, min(Lm, float(lu.get("x2", Lm))))
            if x2 < x1:
                x1, x2 = x2, x1
            st.session_state[f"dist_x1_{i}"] = x1
            st.session_state[f"dist_x2_{i}"] = x2
            st.session_state[f"dist_w_{i}"] = max(0.0, float(lu.get("w", 1.0)))
        elif t == "moment":
            st.session_state[f"moment_x_{i}"] = max(0.0, min(Lm, float(lu.get("x", Lm / 2))))
            st.session_state[f"moment_M_{i}"] = float(lu.get("M", 10.0))
        else:
            st.session_state[f"inclined_x_{i}"] = max(0.0, min(Lm, float(lu.get("x", Lm / 2))))
            st.session_state[f"inclined_Fx_{i}"] = float(lu.get("fx", 0.0))
            st.session_state[f"inclined_Fy_{i}"] = max(0.0, float(lu.get("fy", 10.0)))
    cm = result.get("chainMarks")
    if isinstance(cm, list):
        st.session_state["beam_chain_marks"] = [
            {
                "seg": float(m.get("seg", 0)),
                "x": max(0.0, min(Lm, float(m.get("x", 0)))),
            }
            for m in cm
            if isinstance(m, dict)
        ]
    sp = result.get("snapPoints")
    if isinstance(sp, list):
        snap_points = []
        for x in sp:
            try:
                snap_points.append(max(0.0, min(Lm, float(x))))
            except (TypeError, ValueError):
                continue
        st.session_state["beam_snap_points"] = sorted(set(snap_points))
    st.session_state["beam_canvas_loads"] = loads_from_sidebar_session(Lm, n)
    st.session_state["beam_canvas_applied"] = True


@st.cache_resource
def _beam_canvas_component_ctor(root_str: str):  # type: ignore[misc]
    import streamlit.components.v1 as components

    return components.declare_component("beam_solver_beam_board", path=root_str)


def get_beam_canvas_component():
    root = Path(__file__).resolve().parent / "beam_canvas_component"
    html = root / "index.html"
    if not html.is_file():
        return None
    try:
        mt = int(html.stat().st_mtime_ns)
    except OSError:
        mt = 0
    st.session_state["_beam_canvas_component_mtime_ns"] = mt
    return _beam_canvas_component_ctor(str(root.resolve()))


def render_geometry_sidebar() -> Tuple[float, float, float, int]:
    with st.sidebar:
        st.markdown('<p class="beam-sidebar-heading">הגדרת קורה</p>', unsafe_allow_html=True)
        st.markdown(
            '<p class="beam-sidebar-caption">אורך, מיקומי סמכים ומספר עומסים לעריכה בסרגל.</p>',
            unsafe_allow_html=True,
        )
        with st.container(border=True):
            L = float(
                st.number_input(
                    "אורך קורה L [m]",
                    min_value=0.1,
                    step=0.1,
                    format="%.2f",
                    key="beam_L",
                    help="אורך הקורה במטרים — ציר x מ-0 עד L.",
                )
            )
    if st.session_state.beam_ra_pos > L:
        st.session_state.beam_ra_pos = L
    if st.session_state.beam_rb_pos > L:
        st.session_state.beam_rb_pos = L
    with st.sidebar:
        with st.container(border=True):
            c1, c2 = st.columns(2)
            with c1:
                ra_pos = float(
                    st.number_input(
                        "סמך A [m]",
                        min_value=0.0,
                        max_value=L,
                        step=0.1,
                        format="%.2f",
                        key="beam_ra_pos",
                        help="מיקום סמך הציר (משולש) לאורך הקורה.",
                    )
                )
            with c2:
                rb_pos = float(
                    st.number_input(
                        "סמך B [m]",
                        min_value=0.0,
                        max_value=L,
                        step=0.1,
                        format="%.2f",
                        key="beam_rb_pos",
                        help="מיקום סמך הגליל (B) — ניתן לגרור גם על הלוח.",
                    )
                )
            load_count = int(
                st.number_input(
                    "מספר עומסים",
                    min_value=0,
                    max_value=20,
                    step=1,
                    key="beam_load_count",
                    help="כמה בלוקי עומס לפתוח בסרגל (0–20).",
                )
            )
    return L, ra_pos, rb_pos, load_count


def render_load_expanders(L: float, load_count: int) -> None:
    if load_count < 1:
        return
    st.sidebar.markdown('<p class="beam-sidebar-heading">עומסים</p>', unsafe_allow_html=True)
    st.sidebar.markdown(
        '<p class="beam-sidebar-caption">פרמטרים לכל עומס — או צייר ישירות על הלוח.</p>',
        unsafe_allow_html=True,
    )
    for i in range(load_count):
        with st.sidebar.expander(f"עומס {i + 1}", expanded=(i == 0)):
            lt = st.selectbox(
                "סוג עומס",
                list(LOAD_TYPE_LABELS.keys()),
                format_func=lambda k: LOAD_TYPE_LABELS[k],
                key=f"load_type_{i}",
                help="בחר סוג — השדות למטה יתעדכנו בהתאם.",
            )
            if lt == "point":
                c1, c2 = st.columns(2)
                with c1:
                    st.number_input(
                        "מיקום x [m]",
                        min_value=0.0,
                        max_value=float(L),
                        value=float(L) / 2,
                        step=0.1,
                        format="%.2f",
                        key=f"point_x_{i}",
                        help="מיקום העומס לאורך הקורה.",
                    )
                with c2:
                    st.number_input(
                        "גודל Fy [kN]",
                        min_value=0.0,
                        value=10.0,
                        step=1.0,
                        format="%.2f",
                        key=f"point_Fy_{i}",
                        help="גודל העומס האנכי (ערך חיובי).",
                    )
                st.selectbox(
                    "כיוון Fy",
                    ["down", "up"],
                    format_func=lambda v: "כלפי מטה" if v == "down" else "כלפי מעלה",
                    key=f"point_dir_{i}",
                    help="כיוון הפעלת העומס האנכי.",
                )
                st.number_input(
                    "Fx [kN]",
                    value=0.0,
                    step=1.0,
                    format="%.2f",
                    key=f"point_Fx_{i}",
                    help="רכיב צירי אופציונלי (+x ימינה).",
                )
            elif lt == "distributed":
                c1, c2 = st.columns(2)
                with c1:
                    st.number_input(
                        "התחלה x1 [m]",
                        0.0,
                        float(L),
                        0.0,
                        0.1,
                        format="%.2f",
                        key=f"dist_x1_{i}",
                        help="קצה שמאלי של המפולג.",
                    )
                with c2:
                    st.number_input(
                        "סוף x2 [m]",
                        0.0,
                        float(L),
                        float(L),
                        0.1,
                        format="%.2f",
                        key=f"dist_x2_{i}",
                        help="קצה ימני של המפולג.",
                    )
                st.number_input(
                    "עוצמה w [kN/m]",
                    min_value=0.0,
                    value=1.0,
                    step=0.1,
                    format="%.2f",
                    key=f"dist_w_{i}",
                    help="עומס מפולג אחיד (חיובי = כלפי מטה).",
                )
            elif lt == "moment":
                c1, c2 = st.columns(2)
                with c1:
                    st.number_input(
                        "מיקום x [m]",
                        0.0,
                        float(L),
                        float(L) / 2,
                        0.1,
                        format="%.2f",
                        key=f"moment_x_{i}",
                        help="נקודת הפעלת המומנט.",
                    )
                with c2:
                    st.number_input(
                        "M [kN·m]",
                        value=10.0,
                        step=1.0,
                        format="%.2f",
                        key=f"moment_M_{i}",
                        help="גודל המומנט (חיובי / שלילי לפי כיוון).",
                    )
            else:
                c1, c2 = st.columns(2)
                with c1:
                    st.number_input(
                        "מיקום x [m]",
                        0.0,
                        float(L),
                        float(L) / 2,
                        0.1,
                        format="%.2f",
                        key=f"inclined_x_{i}",
                        help="נקודת התחלה של העומס האלכסוני.",
                    )
                with c2:
                    st.number_input(
                        "Fx [kN]",
                        value=0.0,
                        step=1.0,
                        format="%.2f",
                        key=f"inclined_Fx_{i}",
                        help="רכיב אופקי (+x ימינה).",
                    )
                st.number_input(
                    "רכיב אנכי [kN]",
                    min_value=0.0,
                    value=10.0,
                    step=1.0,
                    format="%.2f",
                    key=f"inclined_Fy_{i}",
                    help="גודל הרכיב האנכי (חיובי = כלפי מטה).",
                )


def render_canvas_dashboard_controls() -> Tuple[float, float, float, int]:
    L = max(0.1, float(st.session_state.get("beam_L", 10.0)))
    if st.session_state.beam_ra_pos > L:
        st.session_state.beam_ra_pos = L
    if st.session_state.beam_rb_pos > L:
        st.session_state.beam_rb_pos = L
    return (
        L,
        float(st.session_state.beam_ra_pos),
        float(st.session_state.beam_rb_pos),
        int(st.session_state.beam_load_count),
    )


def render_beam_board(L: float, ra_pos: float, rb_pos: float, loads: List[dict]) -> None:
    st.markdown('<h2 class="beam-section-title">לוח שרטוט</h2>', unsafe_allow_html=True)
    st.markdown(
        '<p class="beam-subtle">רחף על כפתור בשורת הכלים לקבלת הסבר קצר.</p>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="beam-panel beam-board-shell">', unsafe_allow_html=True)
    comp = get_beam_canvas_component()
    if comp is not None:
        items = internal_loads_to_canvas_items(loads)
        chain_marks = st.session_state.get("beam_chain_marks", [])
        if not isinstance(chain_marks, list):
            chain_marks = []
        snap_points = st.session_state.get("beam_snap_points", [])
        if not isinstance(snap_points, list):
            snap_points = []
        try:
            result = comp(
                L=float(L),
                ra=float(ra_pos),
                rb=float(rb_pos),
                items=items,
                chainMarks=chain_marks,
                snapPoints=snap_points,
                supportMode=st.session_state.get("beam_support_mode", "simple"),
                randomExerciseLevel=str(
                    st.session_state.get("random_exercise_level", "easy")
                ),
                randomExerciseBeamType=str(
                    st.session_state.get("random_exercise_beam_type", "")
                ),
                key=(
                    f"beam_board_{st.session_state.get('_beam_board_nonce', 0)}_"
                    f"{st.session_state.get('_beam_canvas_component_mtime_ns', 0)}"
                ),
                default=None,
                height=980,
            )
        except Exception as ex:
            st.warning("רכיב לוח: " + str(ex))
            result = None
        if isinstance(result, dict):
            rnd = result.get("randomGenerate")
            if rnd:
                rnd_ts = result.get("ts")
                if rnd_ts != st.session_state.get("_random_exercise_last_ts"):
                    st.session_state["_random_exercise_last_ts"] = rnd_ts
                    generate_random_exercise(
                        str(rnd), support_mode=result.get("supportMode")
                    )
                    if st.session_state.pop("_random_challenge_toast", False):
                        st.toast("Challenge Accepted! 🎯", icon="✅")
                    st.rerun()
            raw_lds = result.get("loads")
            if isinstance(raw_lds, list):
                st.session_state["_beam_canvas_last_export"] = raw_lds
            # שינוי אורך קורה בלוח בלי Apply — רק אחרי Apply רשמי (לא בתצוגת תרגיל אקראי).
            if (
                not result.get("applied")
                and canvas_notebook_ready()
                and "L" in result
            ):
                new_l = max(0.1, float(result.get("L", st.session_state.get("beam_L", 10.0))))
                old_l = float(st.session_state.get("beam_L", 10.0))
                if abs(new_l - old_l) > 1e-6:
                    st.session_state["beam_L"] = new_l
                    st.session_state["beam_ra_pos"] = max(
                        0.0, min(new_l, float(result.get("ra", st.session_state.get("beam_ra_pos", 0.0))))
                    )
                    st.session_state["beam_rb_pos"] = max(
                        0.0, min(new_l, float(result.get("rb", st.session_state.get("beam_rb_pos", new_l))))
                    )
                    st.session_state["_beam_canvas_l_sync_ts"] = result.get("ts")
                    st.rerun()
                elif abs(new_l - old_l) <= 1e-6:
                    st.session_state["beam_ra_pos"] = max(
                        0.0, min(new_l, float(result.get("ra", st.session_state.get("beam_ra_pos", 0.0))))
                    )
                    st.session_state["beam_rb_pos"] = max(
                        0.0, min(new_l, float(result.get("rb", st.session_state.get("beam_rb_pos", new_l))))
                    )
            if result.get("applied"):
                ts = result.get("ts")
                if ts != st.session_state.get("_beam_canvas_last_ts"):
                    st.session_state["_beam_canvas_last_ts"] = ts
                    st.session_state["_beam_canvas_pending_scene"] = result
                    st.rerun()
    else:
        board_root = Path(__file__).resolve().parent / "beam_canvas_component"
        st.info(f"חסר `beam_canvas_component/index.html` — נתיב: `{board_root}`")
    st.markdown("</div>", unsafe_allow_html=True)


def render_vision_section() -> None:
    st.markdown('<h2 class="beam-section-title">תמונת התרגיל (Vision)</h2>', unsafe_allow_html=True)
    st.markdown(
        '<p class="beam-subtle">העלה צילום תרגיל — הניתוח ימלא את הסרגל. נדרש מפתח OpenAI.</p>',
        unsafe_allow_html=True,
    )
    c_u1, c_u2, c_u3 = st.columns([2, 1, 1])
    with c_u1:
        up_main = st.file_uploader(
            "גרור תמונה או בחר קובץ",
            type=["png", "jpg", "jpeg", "webp"],
            key="exercise_photo_main",
        )
    with c_u2:
        if up_main is not None:
            st.image(up_main, caption="תצוגה מקדימה", use_container_width=True)
    with c_u3:
        st.text_input("מפתח API", type="password", key="vision_api_key_input")
        st.text_input("מודל", value="gpt-4o-mini", key="vision_model_name")
        st.text_input("Base URL", value="https://api.openai.com/v1", key="vision_api_base")
        go = st.button("נתח תמונה ומלא שדות", type="primary", key="analyze_main_btn")
    if go:
        if up_main is None:
            st.warning("העלה תמונה לפני ניתוח.")
        else:
            try:
                mime = getattr(up_main, "type", "") or ""
                if not mime or mime == "application/octet-stream":
                    nm = (getattr(up_main, "name", "") or "").lower()
                    mime = "image/png"
                    if nm.endswith((".jpg", ".jpeg")):
                        mime = "image/jpeg"
                    elif nm.endswith(".webp"):
                        mime = "image/webp"
                if mime == "image/jpg":
                    mime = "image/jpeg"
                key = get_openai_api_key()
                model = (st.session_state.get("vision_model_name") or "gpt-4o-mini").strip()
                base = (st.session_state.get("vision_api_base") or "https://api.openai.com/v1").strip()
                with st.spinner("שולח ל־AI ומחלץ עומסים..."):
                    run_vision_on_bytes(up_main.getvalue(), mime, key, model, base)
            except Exception as e:
                st.error(str(e))
    if st.session_state.get("vision_last_json"):
        with st.expander("JSON אחרון מהתמונה"):
            st.code(st.session_state["vision_last_json"], language="json")


def build_internal_force_figure(
    L: float,
    loads: List[dict],
    ra_pos: float,
    rb_pos: float,
    ra_x: float,
    ra_y: float,
    rb_x: float,
    rb_y: float,
) -> Tuple[Any, float, int, np.ndarray]:
    positions = [0.0, L, ra_pos, rb_pos]
    for ld in loads:
        if ld["type"] in ("point", "moment", "inclined"):
            positions.append(ld["x"])
        else:
            positions.extend([ld["x1"], ld["x2"]])
    positions = sorted(set(positions))
    xs = solver.beam_plot_x_coords(L, positions)
    moments = [solver.bending_moment(x, loads, ra_y, rb_y, ra_pos, rb_pos) for x in xs]
    shears = [solver.shear_force(x, loads, ra_y, rb_y, ra_pos, rb_pos) for x in xs]
    normals_plot = [solver.normal_force(x, loads, ra_x, ra_pos) for x in xs]
    mmx = max(moments, key=abs)
    ix = moments.index(mmx)
    try:
        plt.style.use("seaborn-v0_8-whitegrid")
    except OSError:
        pass
    fig, (ax0, ax1, ax2) = plt.subplots(3, 1, figsize=(11.5, 11), sharex=True)
    fig.patch.set_facecolor("#f8fafc")
    Lf = float(L)
    x_pad = max(0.05, 0.02 * Lf)

    def polish_axis(ax: Any) -> None:
        ax.set_facecolor("#ffffff")
        ax.grid(True, color="#94a3b8", alpha=0.22, linewidth=0.8)
        ax.set_axisbelow(True)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color("#cbd5e1")
        ax.spines["bottom"].set_color("#cbd5e1")
        ax.tick_params(colors="#475569", labelsize=10)

    ax0.step(xs, normals_plot, where="post", color="#0f766e", linewidth=2.3)
    ax0.fill_between(xs, normals_plot, 0, step="post", color="#0f766e", alpha=0.14)
    ax0.vlines([0.0, Lf], [0.0, 0.0], [normals_plot[0], normals_plot[-1]], color="#0f766e", linewidth=2.3)
    ax0.axhline(0, color="#020617", linestyle="-", linewidth=2.0)
    ax0.invert_yaxis()
    ax0.set_ylabel("Nx [kN]")
    ax0.set_title(
        "דיאגרמת כוח צירי Nx — ערך שלילי בעומס אופקי מוצג כלפי מעלה, וחיובי כלפי מטה"
    )
    ax0.set_xlim(-x_pad, Lf + x_pad)
    ax1.step(xs, shears, where="post", color="#2563eb", linewidth=2.3)
    ax1.fill_between(xs, shears, 0, step="post", color="#2563eb", alpha=0.13)
    ax1.vlines([0.0, Lf], [0.0, 0.0], [shears[0], shears[-1]], color="#2563eb", linewidth=2.3)
    ax1.axhline(0, color="#020617", linestyle="-", linewidth=2.0)
    ax1.set_ylabel("V [kN]")
    ax1.set_title("דיאגרמת כוח אנכי — כוחות במישור (ציר Y)")
    ax1.set_xlim(-x_pad, Lf + x_pad)
    ax2.plot(xs, moments, color="#dc2626", linewidth=2.5)
    ax2.fill_between(xs, moments, 0, color="#dc2626", alpha=0.12)
    ax2.axhline(0, color="#020617", linestyle="-", linewidth=2.0)
    ax2.invert_yaxis()
    ax2.set_ylabel("M [kN·m]")
    ax2.set_xlabel("x [m] (מקור ב־0 — תחילת הקורה)")
    ax2.set_title("דיאגרמת מומנט כפיפה M")
    ax2.set_xlim(-x_pad, Lf + x_pad)
    for ax in (ax0, ax1, ax2):
        polish_axis(ax)
    plt.tight_layout()
    return fig, mmx, ix, xs


def render_results(
    loads: List[dict],
    L: float,
    ra_pos: float,
    rb_pos: float,
    ra_x: float,
    ra_y: float,
    rb_x: float,
    rb_y: float,
) -> None:
    steps = solver.get_calculation_steps(loads, L, ra_pos, rb_pos, ra_x, ra_y, rb_x, rb_y)
    payload = solver.build_ai_explanation_payload(loads, L, ra_pos, rb_pos, ra_x, ra_y, rb_x, rb_y)

    st.markdown("---")
    st.markdown('<h2 class="beam-section-title">תוצאות חישוב</h2>', unsafe_allow_html=True)
    st.markdown(
        '<p class="beam-subtle">ריאקציות, דיאגרמות כוחות פנימיים ושלבי חישוב מלאים לפי מודל סמכת צמד ב-A וגליל ב-B.</p>',
        unsafe_allow_html=True,
    )
    r1, r2, r3, r4 = st.columns(4)
    r1.metric("R_Ax (צירי)", solver.format_number(ra_x))
    r2.metric("R_Ay (אנכי)", solver.format_number(ra_y))
    r3.metric("R_Bx (צירי)", solver.format_number(rb_x))
    r4.metric("R_By (אנכי)", solver.format_number(rb_y))
    st.caption("במודל גליל ב־B: R_Bx = 0 תמיד.")

    fig, mmx, ix, xs = build_internal_force_figure(
        L, loads, ra_pos, rb_pos, ra_x, ra_y, rb_x, rb_y
    )

    t1, t2, t3, t4 = st.tabs(
        ["דיאגרמות", "שלבי חישוב / JSON", "נקודות בדיקה", "פתרון מחברת"]
    )
    with t1:
        try:
            st.pyplot(fig, use_container_width=True)
        except TypeError:
            st.pyplot(fig)
        plt.close(fig)
        st.metric(
            "|M| מקסימלי (בדגימה)",
            solver.format_number(mmx),
            delta=f"x = {solver.format_number(xs[ix])} m",
        )
        st.caption(
            "ציר x בכל הגרפים מתחיל ב־0 (תחילת הקורה) ומסתיים ב־L. "
            "בגרף Nx: עומס אופקי שלילי מוצג מעל קו האפס; עומס אופקי חיובי מוצג מתחת."
        )
    with t2:
        c1, c2 = st.columns(2)
        c1.text_area("שלבים", "\n".join(steps), height=400)
        c2.text_area("JSON", json.dumps(payload, ensure_ascii=False, indent=2), height=400)
    with t3:
        for xv in (0.0, L * 0.25, L * 0.5, L * 0.75, L):
            st.text(
                f"x={solver.format_number(xv)}  M={solver.format_number(solver.bending_moment(xv, loads, ra_y, rb_y, ra_pos, rb_pos))}"
            )
        cx = float(
            st.number_input(
                "x מותאם [m]",
                min_value=0.0,
                max_value=float(L),
                value=0.0,
                step=0.1,
                format="%.2f",
                key="tab_custom_moment_x",
            )
        )
        st.info(
            f"M ב־x={solver.format_number(cx)}: **{solver.format_number(solver.bending_moment(cx, loads, ra_y, rb_y, ra_pos, rb_pos))}** kN·m"
        )
    with t4:
        if not canvas_notebook_ready():
            st.info(
                "תרגיל אקראי מוצג בלוח — לחץ **Apply changes** כדי לקבל כאן פתרון מחברת מדויק."
            )
            st.caption("עד אז אפשר לערוך עומסים בלוח; המחברת תתעדכן רק אחרי Apply.")
        else:
            beam_notebook.render_solved_notebook(
                loads, L, ra_pos, rb_pos, ra_x, ra_y, rb_x, rb_y
            )


def render_cantilever_results(loads: List[dict], L: float, result: Dict[str, Any]) -> None:
    steps = solver.get_cantilever_calculation_steps(loads, L, result)
    payload: Dict[str, Any] = {
        "schema": "beam_solver.v1_cantilever_fixed_left",
        "model": {"A": "fixed", "free_end": "right"},
        "geometry": {"L_m": L, "x_A": 0.0},
        "loads": loads,
        "reactions": {
            "R_Ax": result["R_Ax"],
            "R_Ay": result["R_Ay"],
            "M_A": result["M_A"],
        },
        "calculation_steps": steps,
    }
    xs = result["xs"]
    normals = result["normal"]
    shears = result["shear"]
    moments = result["moment"]
    mmx = float(moments[int(np.argmax(np.abs(moments)))]) if len(moments) else 0.0
    imx = int(np.argmax(np.abs(moments))) if len(moments) else 0

    try:
        plt.style.use("seaborn-v0_8-whitegrid")
    except OSError:
        pass
    fig, (ax0, ax1, ax2) = plt.subplots(3, 1, figsize=(11.5, 11), sharex=True)
    fig.patch.set_facecolor("#f8fafc")
    x_pad = max(0.05, 0.02 * float(L))

    def polish_axis(ax: Any) -> None:
        ax.set_facecolor("#ffffff")
        ax.grid(True, color="#94a3b8", alpha=0.22, linewidth=0.8)
        ax.set_axisbelow(True)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color("#cbd5e1")
        ax.spines["bottom"].set_color("#cbd5e1")
        ax.tick_params(colors="#475569", labelsize=10)

    ax0.step(xs, normals, where="post", color="#0f766e", linewidth=2.3)
    ax0.fill_between(xs, normals, 0, step="post", color="#0f766e", alpha=0.14)
    ax0.axhline(0, color="#020617", linestyle="-", linewidth=2.0)
    ax0.invert_yaxis()
    ax0.set_ylabel("Nx [kN]")
    ax0.set_title("דיאגרמת כוח צירי Nx — זיז רתום משמאל")
    ax0.set_xlim(-x_pad, float(L) + x_pad)

    ax1.step(xs, shears, where="post", color="#2563eb", linewidth=2.3)
    ax1.fill_between(xs, shears, 0, step="post", color="#2563eb", alpha=0.13)
    ax1.axhline(0, color="#020617", linestyle="-", linewidth=2.0)
    ax1.set_ylabel("V [kN]")
    ax1.set_title("דיאגרמת גזירה V — תנאי שפה: קצה חופשי ב-x=L")
    ax1.set_xlim(-x_pad, float(L) + x_pad)

    ax2.plot(xs, moments, color="#dc2626", linewidth=2.5)
    ax2.fill_between(xs, moments, 0, color="#dc2626", alpha=0.12)
    ax2.axhline(0, color="#020617", linestyle="-", linewidth=2.0)
    ax2.invert_yaxis()
    ax2.set_ylabel("M [kN·m]")
    ax2.set_xlabel("x [m] (מקור ב־0 — הריתום)")
    ax2.set_title("דיאגרמת מומנט כפיפה M — זיז")
    ax2.set_xlim(-x_pad, float(L) + x_pad)
    for ax in (ax0, ax1, ax2):
        polish_axis(ax)
    plt.tight_layout()

    st.markdown("---")
    st.markdown('<h2 class="beam-section-title">תוצאות חישוב — זיז רתום</h2>', unsafe_allow_html=True)
    st.markdown(
        '<p class="beam-subtle">מודל נפרד: ריתום ב־x=0 וקצה חופשי ב־x=L.</p>',
        unsafe_allow_html=True,
    )
    r1, r2, r3 = st.columns(3)
    r1.metric("R_Ax (צירי)", solver.format_number(float(result["R_Ax"])))
    r2.metric("R_Ay (אנכי)", solver.format_number(float(result["R_Ay"])))
    r3.metric("M_A (מומנט ריתום)", solver.format_number(float(result["M_A"])))

    t1, t2, t3, t4 = st.tabs(["דיאגרמות", "שלבי חישוב / JSON", "נקודות בדיקה", "פתרון מחברת"])
    with t1:
        try:
            st.pyplot(fig, use_container_width=True)
        except TypeError:
            st.pyplot(fig)
        plt.close(fig)
        st.metric(
            "|M| מקסימלי (בדגימה)",
            solver.format_number(mmx),
            delta=f"x = {solver.format_number(float(xs[imx]))} m" if len(xs) else "x = 0 m",
        )
    with t2:
        c1, c2 = st.columns(2)
        c1.text_area("שלבים", "\n".join(steps), height=400)
        c2.text_area("JSON", json.dumps(payload, ensure_ascii=False, indent=2), height=400)
    with t3:
        fixed_moment = float(result["diagram_fixed_moment"])
        ry = float(result["R_Ay"])
        for xv in (0.0, L * 0.25, L * 0.5, L * 0.75, L):
            st.text(
                f"x={solver.format_number(xv)}  "
                f"V={solver.format_number(solver.cantilever_shear_force(xv, loads, ry))}  "
                f"M={solver.format_number(solver.cantilever_bending_moment(xv, loads, ry, fixed_moment))}"
            )
    with t4:
        if not canvas_notebook_ready():
            st.info(
                "תרגיל אקראי מוצג בלוח — לחץ **Apply changes** כדי לקבל כאן פתרון מחברת מדויק."
            )
            st.caption("עד אז אפשר לערוך עומסים בלוח; המחברת תתעדכן רק אחרי Apply.")
        elif hasattr(beam_notebook, "_load_live_notebook_module"):
            nb = beam_notebook._load_live_notebook_module()
            if hasattr(nb, "render_cantilever_notebook"):
                nb.render_cantilever_notebook(loads, L, result)
            else:
                st.info("מחברת ריתום עדיין לא זמינה בקובץ הנוכחי.")
        else:
            st.info("מחברת ריתום עדיין לא זמינה בקובץ הנוכחי.")
