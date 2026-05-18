# -*- coding: utf-8 -*-
"""Streamlit UI: beam board component, session state, vision upload, diagrams."""
from __future__ import annotations

import base64
import json
import ssl
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
import streamlit as st

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
        @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@300;400;600;700;800&display=swap');

        :root {
            --beam-bg: #f5f7fb;
            --beam-card: rgba(255, 255, 255, 0.94);
            --beam-border: #dbe4f0;
            --beam-text: #0f172a;
            --beam-muted: #64748b;
            --beam-primary: #0f766e;
            --beam-primary-soft: #ccfbf1;
            --beam-blue: #2563eb;
            --beam-orange: #ea580c;
            --beam-shadow: 0 16px 40px rgba(15, 23, 42, 0.08);
        }

        html, body, [class*="css"], .stApp {
            font-family: 'Assistant', 'Segoe UI', Arial, sans-serif;
        }

        .stApp {
            background:
                radial-gradient(circle at top left, rgba(20, 184, 166, 0.14), transparent 32rem),
                linear-gradient(180deg, #f8fafc 0%, var(--beam-bg) 100%);
            color: var(--beam-text);
        }

        .block-container {
            padding-top: 2rem;
            padding-bottom: 3rem;
            max-width: 1280px;
        }

        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0f172a 0%, #111827 100%);
            border-left: 1px solid rgba(255, 255, 255, 0.08);
        }

        section[data-testid="stSidebar"] * {
            font-family: 'Assistant', 'Segoe UI', Arial, sans-serif;
        }

        section[data-testid="stSidebar"] h1,
        section[data-testid="stSidebar"] h2,
        section[data-testid="stSidebar"] h3,
        section[data-testid="stSidebar"] label,
        section[data-testid="stSidebar"] p {
            color: #e5e7eb !important;
        }

        section[data-testid="stSidebar"] [data-testid="stExpander"] {
            background: rgba(255, 255, 255, 0.07);
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 18px;
            box-shadow: none;
            overflow: hidden;
        }

        .beam-hero {
            padding: 28px 32px;
            border-radius: 28px;
            background:
                linear-gradient(135deg, rgba(15, 118, 110, 0.96), rgba(30, 64, 175, 0.94)),
                radial-gradient(circle at 85% 20%, rgba(255,255,255,0.22), transparent 18rem);
            box-shadow: var(--beam-shadow);
            color: white;
            margin-bottom: 1.2rem;
        }

        .beam-hero h1 {
            margin: 0 0 8px 0;
            font-size: 2.25rem;
            font-weight: 800;
            letter-spacing: -0.03em;
        }

        .beam-hero p {
            margin: 0;
            max-width: 820px;
            color: rgba(255,255,255,0.86);
            font-size: 1.05rem;
            line-height: 1.55;
        }

        .beam-section-title {
            margin: 1.2rem 0 0.6rem 0;
            font-weight: 800;
            color: #0f172a;
            letter-spacing: -0.02em;
        }

        .beam-subtle {
            color: var(--beam-muted);
            font-size: 0.95rem;
            line-height: 1.5;
        }

        .beam-panel {
            background: var(--beam-card);
            border: 1px solid var(--beam-border);
            border-radius: 24px;
            padding: 18px 20px;
            box-shadow: var(--beam-shadow);
            margin-bottom: 1rem;
        }

        .beam-kpi {
            background: var(--beam-card);
            border: 1px solid var(--beam-border);
            border-radius: 22px;
            padding: 18px;
            box-shadow: var(--beam-shadow);
        }

        div[data-testid="stMetric"] {
            background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
            border: 1px solid var(--beam-border);
            border-radius: 20px;
            padding: 18px 18px 16px;
            box-shadow: 0 10px 30px rgba(15, 23, 42, 0.06);
        }

        div[data-testid="stMetricLabel"] p {
            color: var(--beam-muted) !important;
            font-weight: 700;
        }

        div[data-testid="stMetricValue"] {
            color: var(--beam-text);
            font-weight: 800;
        }

        .stTabs [data-baseweb="tab-list"] {
            gap: 10px;
            background: rgba(15, 23, 42, 0.04);
            border-radius: 18px;
            padding: 8px;
        }

        .stTabs [data-baseweb="tab"] {
            border-radius: 14px;
            padding: 10px 18px;
            font-weight: 800;
        }

        .stButton > button,
        div[data-testid="stFormSubmitButton"] button {
            border-radius: 14px;
            border: 0;
            font-weight: 800;
            box-shadow: 0 10px 22px rgba(15, 118, 110, 0.18);
        }

        div[data-baseweb="input"] > div,
        div[data-baseweb="select"] > div,
        textarea {
            border-radius: 14px !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


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
            items.append(
                {
                    "id": oid,
                    "type": "incl",
                    "x": float(ld["x"]),
                    "fx": fx_val,
                    "fy": fy_mag,
                    "inclMag": mag if mag > 1e-9 else 10.0,
                    "inclDir": "dl" if fx_val < 0 else "dr",
                }
            )
    return items


def apply_canvas_scene_to_session(result: Dict[str, Any]) -> None:
    Lm = max(0.1, float(result.get("L", 10.0)))
    st.session_state["beam_L"] = Lm
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


@st.cache_resource
def _beam_canvas_component_ctor(root_str: str, _mtime: float):  # type: ignore[misc]
    import streamlit.components.v1 as components

    return components.declare_component("beam_solver_beam_board", path=root_str)


def get_beam_canvas_component():
    root = Path(__file__).resolve().parent / "beam_canvas_component"
    html = root / "index.html"
    if not html.is_file():
        return None
    try:
        mt = float(html.stat().st_mtime)
    except OSError:
        mt = 0.0
    return _beam_canvas_component_ctor(str(root.resolve()), mt)


def render_geometry_sidebar() -> Tuple[float, float, float, int]:
    with st.sidebar:
        st.markdown("### Beam Setup")
        st.caption("הגדרת גיאומטריה, סמכים ומספר עומסים")
        L = float(
            st.number_input(
                "אורך קורה L [m]", min_value=0.1, step=0.1, format="%.2f", key="beam_L"
            )
        )
    if st.session_state.beam_ra_pos > L:
        st.session_state.beam_ra_pos = L
    if st.session_state.beam_rb_pos > L:
        st.session_state.beam_rb_pos = L
    with st.sidebar:
        c1, c2 = st.columns(2)
        with c1:
            ra_pos = float(
                st.number_input(
                    "סמך A [m]", min_value=0.0, max_value=L, step=0.1, format="%.2f", key="beam_ra_pos"
                )
            )
        with c2:
            rb_pos = float(
                st.number_input(
                    "סמך B [m]", min_value=0.0, max_value=L, step=0.1, format="%.2f", key="beam_rb_pos"
                )
            )
        load_count = int(
            st.number_input(
                "מספר עומסים", min_value=0, max_value=20, step=1, key="beam_load_count"
            )
        )
    return L, ra_pos, rb_pos, load_count


def render_load_expanders(L: float, load_count: int) -> None:
    st.sidebar.markdown("### Loads")
    for i in range(load_count):
        with st.sidebar.expander(f"עומס {i + 1}", expanded=(i == 0)):
            lt = st.selectbox(
                "סוג",
                list(LOAD_TYPE_LABELS.keys()),
                format_func=lambda k: LOAD_TYPE_LABELS[k],
                key=f"load_type_{i}",
            )
            if lt == "point":
                c1, c2 = st.columns(2)
                with c1:
                    st.number_input(
                        "x [m]",
                        min_value=0.0,
                        max_value=float(L),
                        value=float(L) / 2,
                        step=0.1,
                        format="%.2f",
                        key=f"point_x_{i}",
                    )
                with c2:
                    st.number_input(
                        "גודל Fy [kN]",
                        min_value=0.0,
                        value=10.0,
                        step=1.0,
                        format="%.2f",
                        key=f"point_Fy_{i}",
                    )
                st.selectbox(
                    "כיוון Fy",
                    ["down", "up"],
                    format_func=lambda v: "Downward — כלפי מטה" if v == "down" else "Upward — כלפי מעלה",
                    key=f"point_dir_{i}",
                )
                st.number_input(
                    "Fx [kN] (אופציונלי, + = כיוון +x לאורך הקורה)",
                    value=0.0,
                    step=1.0,
                    format="%.2f",
                    key=f"point_Fx_{i}",
                )
            elif lt == "distributed":
                c1, c2 = st.columns(2)
                with c1:
                    st.number_input(
                        "x1 [m]", 0.0, float(L), 0.0, 0.1, format="%.2f", key=f"dist_x1_{i}"
                    )
                with c2:
                    st.number_input(
                        "x2 [m]", 0.0, float(L), float(L), 0.1, format="%.2f", key=f"dist_x2_{i}"
                    )
                st.number_input(
                    "עוצמה w [kN/m] (חיובי = כלפי מטה)",
                    min_value=0.0,
                    value=1.0,
                    step=0.1,
                    format="%.2f",
                    key=f"dist_w_{i}",
                )
            elif lt == "moment":
                c1, c2 = st.columns(2)
                with c1:
                    st.number_input(
                        "x [m]", 0.0, float(L), float(L) / 2, 0.1, format="%.2f", key=f"moment_x_{i}"
                    )
                with c2:
                    st.number_input(
                        "M [kN·m]", value=10.0, step=1.0, format="%.2f", key=f"moment_M_{i}"
                    )
            else:
                c1, c2 = st.columns(2)
                with c1:
                    st.number_input(
                        "x [m]", 0.0, float(L), float(L) / 2, 0.1, format="%.2f", key=f"inclined_x_{i}"
                    )
                with c2:
                    st.number_input(
                        "Fx [kN] (+ = כיוון +x)",
                        value=0.0,
                        step=1.0,
                        format="%.2f",
                        key=f"inclined_Fx_{i}",
                    )
                st.number_input(
                    "גודל רכיב אנכי [kN] (חיובי = כלפי מטה)",
                    min_value=0.0,
                    value=10.0,
                    step=1.0,
                    format="%.2f",
                    key=f"inclined_Fy_{i}",
                )


def render_beam_board(L: float, ra_pos: float, rb_pos: float, loads: List[dict]) -> None:
    st.subheader("לוח שרטוט — גרירה")
    board_root = Path(__file__).resolve().parent / "beam_canvas_component"
    st.caption(
        "**כלי עומסים:** בשורה הכחולה מעל הקורה — לוחצים על כלי ואז **לוחצים על הקורה** (לא גרירה של אייקון מהמסך). "
        "**סמכים:** גוררים את המשולשים ▲ לאורך הקורה. בסוף: **החל שינויים (Apply)** בתוך הלוח. "
        f"נתיב רכיב: `{board_root}`"
    )
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
                key="beam_board",
                default=None,
                height=760,
            )
        except Exception as ex:
            st.warning("רכיב לוח: " + str(ex))
            result = None
        if isinstance(result, dict) and result.get("applied"):
            ts = result.get("ts")
            if ts != st.session_state.get("_beam_canvas_last_ts"):
                st.session_state["_beam_canvas_last_ts"] = ts
                st.session_state["_beam_canvas_pending_scene"] = result
                st.rerun()
    else:
        st.info("חסר `beam_canvas_component/index.html` ליד הקובץ — העתק את התיקייה מהפרויקט (או ממסמכים).")


def render_vision_section() -> None:
    st.subheader("תמונת התרגיל (Vision)")
    st.caption("לאחר העלאה — לחץ על הכפתור. נדרש מפתח OpenAI (או secrets).")
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

    t1, t2, t3 = st.tabs(["דיאגרמות", "שלבי חישוב / JSON", "נקודות בדיקה"])
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
