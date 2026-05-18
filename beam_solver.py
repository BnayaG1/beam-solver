# -*- coding: utf-8 -*-
"""Beam Solver — Streamlit entry: geometry, loads, reactions, diagrams."""
from __future__ import annotations

import subprocess
import sys
import threading
import time
import webbrowser

import streamlit as st

import beam_ui
import solver


def _running_inside_streamlit() -> bool:
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx

        return get_script_run_ctx() is not None
    except Exception:
        return False


def main() -> None:
    st.set_page_config(page_title="פותר קורות", layout="wide")
    beam_ui.inject_ui_styles()
    st.markdown(
        """
        <div class="beam-hero">
            <h1>פותר קורות — Beam Solver</h1>
            <p>
                סביבת חישוב ושרטוט אינטראקטיבית לסטטיקה: סמכים, עומסים, ריאקציות,
                ודיאגרמות כוחות פנימיים בממשק נקי לסטודנטים להנדסה.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    beam_ui.ensure_beam_session_defaults()
    beam_ui.migrate_vertical_inputs_to_positive_magnitude()
    if st.session_state.pop("vision_flash_ok", False):
        st.success("הנתונים מהתמונה הוזנו לשדות בסרגל.")

    L, ra_pos, rb_pos, load_count = beam_ui.render_geometry_sidebar()
    beam_ui.render_load_expanders(L, load_count)
    loads = beam_ui.loads_from_sidebar_session(L, load_count)

    beam_ui.render_beam_board(L, ra_pos, rb_pos, loads)

    if ra_pos == rb_pos:
        st.error("יש להפריד בין מיקומי הסמכים.")
        return

    ra_x, ra_y, rb_x, rb_y = solver.compute_reactions(loads, L, ra_pos, rb_pos)
    beam_ui.render_results(loads, L, ra_pos, rb_pos, ra_x, ra_y, rb_x, rb_y)
    beam_ui.render_vision_section()


if __name__ == "__main__":
    if _running_inside_streamlit():
        main()
    else:

        def _ob() -> None:
            time.sleep(2.0)
            webbrowser.open("http://localhost:8501", new=1)

        threading.Thread(target=_ob, daemon=True).start()
        subprocess.run(
            [
                sys.executable,
                "-m",
                "streamlit",
                "run",
                __file__,
                "--server.headless",
                "true",
            ],
            check=False,
        )
