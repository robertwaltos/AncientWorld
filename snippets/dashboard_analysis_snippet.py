"""
Dashboard Analysis Snippet (Streamlit)

Integrate into src/ui/web/dashboard.py routing.
Uses canonical DB path from config/storage_config.py.
"""
import sqlite3
from pathlib import Path
import pandas as pd
import streamlit as st

from config.storage_config import DB_PATH

DB = Path(DB_PATH)

def _df(q, params=()):
    con = sqlite3.connect(DB)
    df = pd.read_sql_query(q, con, params=params)
    con.close()
    return df

def analysis_page():
    st.header("Analysis")

    stats = _df("""
      SELECT
        (SELECT COUNT(*) FROM candidates WHERE status='downloaded') AS downloaded,
        (SELECT COUNT(*) FROM image_features) AS featurized,
        (SELECT COUNT(*) FROM embeddings) AS embedded,
        (SELECT COUNT(*) FROM tda_features) AS tda_done
    """)
    st.dataframe(stats, use_container_width=True)

    feats = _df("""
      SELECT f.candidate_id, f.edge_density, f.line_count, f.radialness,
             f.opening_count, f.door_window_aspect_mean, f.door_window_aspect_p90,
             c.local_path, c.page_url, c.source
      FROM image_features f
      JOIN candidates c ON c.id = f.candidate_id
      ORDER BY f.candidate_id DESC
      LIMIT 5000
    """)

    if feats.empty:
        st.info("No features yet. Run: python tools/extract_geometry_features.py")
        return

    st.subheader("Distributions")
    st.write("Radialness")
    st.bar_chart(feats["radialness"].value_counts(bins=20, sort=False))
    st.write("Edge density")
    st.bar_chart(feats["edge_density"].value_counts(bins=20, sort=False))

    st.subheader("Most radial candidates")
    top = feats.sort_values("radialness", ascending=False).head(24)
    cols = st.columns(4)
    for i, row in enumerate(top.itertuples()):
        with cols[i % 4]:
            st.image(str(row.local_path), caption=f"radial={row.radialness:.2f}", use_container_width=True)
            if row.page_url:
                st.link_button("Source", row.page_url)
