"""
AncientWorld Streamlit Dashboard

Comprehensive GUI for managing the ancient buildings image analysis platform.
"""

import sqlite3
import subprocess
import sys
from pathlib import Path

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from PIL import Image

# Add paths
ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT))

from config.storage_config import (
    DB_PATH,
    IMAGES_ROOT,
    MAX_STORAGE_GB,
    MAX_STORAGE_BYTES,
    LARGE_STORAGE_ROOT
)

# Page configuration
st.set_page_config(
    page_title="AncientWorld Dashboard",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_resource
def get_db_connection():
    """Get cached database connection."""
    db_path = Path(DB_PATH)
    if not db_path.exists():
        return None
    return sqlite3.connect(db_path, check_same_thread=False)


def get_stats():
    """Get statistics from database."""
    con = get_db_connection()
    if not con:
        return None

    stats = dict(con.execute("SELECT k, v FROM stats").fetchall())

    counts = con.execute("""
        SELECT status, COUNT(*) as count
        FROM candidates
        GROUP BY status
    """).fetchall()
    status_counts = dict(counts)

    return {
        "stats": stats,
        "status": status_counts,
    }


def sidebar():
    """Render sidebar navigation."""
    st.sidebar.title("🏛️ AncientWorld")
    st.sidebar.markdown("---")

    page = st.sidebar.radio(
        "Navigation",
        [
            "Dashboard",
            "Discovery",
            "Download",
            "Database Browser",
            "Image Viewer",
            "Analysis",
            "Settings",
        ],
        index=0,
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown("### Quick Stats")

    data = get_stats()
    if data:
        stats = data["stats"]
        total_gb = stats.get("total_downloaded_bytes", 0) / 1024**3
        st.sidebar.metric(
            "Downloaded",
            f"{total_gb:.2f} GB",
            f"{(total_gb/MAX_STORAGE_GB)*100:.1f}%"
        )

        st.sidebar.metric(
            "Files",
            f"{stats.get('total_files_downloaded', 0):,}"
        )

        pending = data["status"].get("pending", 0)
        st.sidebar.metric("Pending", f"{pending:,}")

    return page


def dashboard_page():
    """Main dashboard page."""
    st.title("🏛️ AncientWorld Dashboard")
    st.markdown("Comprehensive ancient buildings image analysis platform")

    data = get_stats()
    if not data:
        st.error("⚠️ Database not initialized. Run init_database.py first.")
        return

    stats = data["stats"]
    status_counts = data["status"]

    # Top metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total_gb = stats.get("total_downloaded_bytes", 0) / 1024**3
        st.metric("Downloaded", f"{total_gb:.1f} GB",
                 f"{(total_gb/MAX_STORAGE_GB)*100:.1f}% of cap")

    with col2:
        files = stats.get("total_files_downloaded", 0)
        st.metric("Files", f"{files:,}")

    with col3:
        pending = status_counts.get("pending", 0)
        st.metric("Pending", f"{pending:,}")

    with col4:
        failed = stats.get("total_failed", 0)
        st.metric("Failed", f"{failed:,}")

    st.markdown("---")

    # Storage gauge
    used_gb = stats.get("total_downloaded_bytes", 0) / 1024**3
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=used_gb,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': f"Storage (GB) / {MAX_STORAGE_GB} GB Cap"},
        gauge={
            'axis': {'range': [None, MAX_STORAGE_GB]},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [0, MAX_STORAGE_GB * 0.7], 'color': "lightgray"},
                {'range': [MAX_STORAGE_GB * 0.7, MAX_STORAGE_GB * 0.9], 'color': "yellow"},
                {'range': [MAX_STORAGE_GB * 0.9, MAX_STORAGE_GB], 'color': "red"}
            ],
        }
    ))
    st.plotly_chart(fig, use_container_width=True)


def discovery_page():
    """Discovery management page."""
    st.title("🔍 Discovery Management")

    st.markdown("""
    Discovery phase: Catalog images before downloading.
    This allows building a large candidate pool to prioritize downloads.
    """)

    col1, col2 = st.columns([3, 1])

    with col1:
        if st.button("🚀 Start Wikimedia Discovery", type="primary", use_container_width=True):
            with st.spinner("Starting discovery spider..."):
                try:
                    # Run spider in subprocess
                    import os
                    scrapy_dir = ROOT / "ancientgeo"
                    result = subprocess.run(
                        ["python", "-m", "scrapy", "crawl", "commons_discover"],
                        cwd=str(scrapy_dir),
                        capture_output=True,
                        text=True,
                        timeout=300  # 5 minute timeout for initial start
                    )

                    if result.returncode == 0:
                        st.success("✅ Discovery spider completed successfully!")
                        st.expander("View output").code(result.stdout)
                    else:
                        st.error(f"❌ Spider failed with return code {result.returncode}")
                        st.expander("View error").code(result.stderr)
                except subprocess.TimeoutExpired:
                    st.warning("⏱️ Spider is still running (timeout after 5 minutes). Check terminal for progress.")
                except Exception as e:
                    st.error(f"❌ Error starting spider: {str(e)}")

    with col2:
        if st.button("📊 Refresh Stats", use_container_width=True):
            st.rerun()


def download_page():
    """Download management page."""
    st.title("⬇️ Download Management")

    data = get_stats()
    if not data:
        st.error("Database not initialized")
        return

    stats = data["stats"]
    used_gb = stats.get("total_downloaded_bytes", 0) / 1024**3
    remaining_gb = MAX_STORAGE_GB - used_gb

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Used", f"{used_gb:.2f} GB")
    with col2:
        st.metric("Remaining", f"{remaining_gb:.2f} GB")

    st.progress(min(used_gb / MAX_STORAGE_GB, 1.0))

    if st.button("🚀 Start Download", type="primary", use_container_width=True):
        with st.spinner("Starting download process..."):
            try:
                result = subprocess.run(
                    ["python", "tools/download_capped.py"],
                    cwd=str(ROOT),
                    capture_output=True,
                    text=True,
                    timeout=600  # 10 minute timeout
                )

                if result.returncode == 0:
                    st.success("✅ Download completed successfully!")
                    with st.expander("View output"):
                        st.code(result.stdout)
                    st.rerun()  # Refresh stats
                else:
                    st.error(f"❌ Download failed with return code {result.returncode}")
                    with st.expander("View error"):
                        st.code(result.stderr)
            except subprocess.TimeoutExpired:
                st.warning("⏱️ Download is still running (timeout after 10 minutes). Check terminal for progress.")
            except Exception as e:
                st.error(f"❌ Error starting download: {str(e)}")

    st.markdown("---")
    st.subheader("Deduplication")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ Remove Exact Duplicates", use_container_width=True):
            with st.spinner("Running exact deduplication..."):
                try:
                    result = subprocess.run(
                        ["python", "tools/dedupe_exact.py"],
                        cwd=str(ROOT),
                        capture_output=True,
                        text=True,
                        timeout=300
                    )

                    if result.returncode == 0:
                        st.success("✅ Exact deduplication completed!")
                        with st.expander("View results"):
                            st.code(result.stdout)
                        st.rerun()
                    else:
                        st.error(f"❌ Deduplication failed: {result.stderr}")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")

    with col2:
        if st.button("🔍 Remove Near-Duplicates", use_container_width=True):
            with st.spinner("Running perceptual deduplication..."):
                try:
                    result = subprocess.run(
                        ["python", "tools/dedupe_perceptual.py"],
                        cwd=str(ROOT),
                        capture_output=True,
                        text=True,
                        timeout=600
                    )

                    if result.returncode == 0:
                        st.success("✅ Perceptual deduplication completed!")
                        with st.expander("View results"):
                            st.code(result.stdout)
                        st.rerun()
                    else:
                        st.error(f"❌ Deduplication failed: {result.stderr}")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")


def database_browser_page():
    """Database browser page."""
    st.title("🗄️ Database Browser")

    con = get_db_connection()
    if not con:
        st.error("Database not initialized")
        return

    search = st.text_input("Search title/description")

    query = "SELECT id, title, source, width, height, status, created_at FROM candidates "
    query += "WHERE title LIKE ? OR description LIKE ? ORDER BY id DESC LIMIT 1000"

    df = pd.read_sql_query(query, con, params=[f"%{search}%", f"%{search}%"])

    st.dataframe(df, use_container_width=True, height=600)
    st.markdown(f"Showing {len(df)} results")


def image_viewer_page():
    """Image viewer page."""
    st.title("🖼️ Image Viewer")

    con = get_db_connection()
    if not con:
        st.error("Database not initialized")
        return

    rows = con.execute("""
        SELECT id, title, local_path, width, height
        FROM candidates
        WHERE status='downloaded' AND local_path IS NOT NULL
        ORDER BY RANDOM()
        LIMIT 20
    """).fetchall()

    if not rows:
        st.info("No images downloaded yet")
        return

    cols = st.columns(4)

    for idx, (cid, title, local_path, width, height) in enumerate(rows):
        col = cols[idx % 4]

        path = Path(local_path)
        if path.exists():
            with col:
                try:
                    img = Image.open(path)
                    st.image(img, caption=title[:40], use_column_width=True)
                    st.caption(f"{width}×{height}")
                except Exception as e:
                    st.error(f"Error: {e}")


def analysis_page():
    """Analysis tools page."""
    st.title("🔬 Analysis Tools")

    st.subheader("Geometry Detection")
    st.markdown("Detect circles, lines, and geometric features")

    uploaded = st.file_uploader("Upload image", type=["jpg", "jpeg", "png"])

    if uploaded:
        img = Image.open(uploaded)
        st.image(img, caption="Uploaded Image", use_column_width=True)

        if st.button("Run Geometry Analysis"):
            st.info("Analysis integration coming soon!")


def settings_page():
    """Settings page."""
    st.title("⚙️ Settings")

    st.subheader("Storage Configuration")
    st.code(f"Storage root: {LARGE_STORAGE_ROOT}")
    st.code(f"Database: {DB_PATH}")
    st.code(f"Images: {IMAGES_ROOT}")
    st.code(f"Max storage: {MAX_STORAGE_GB} GB")

    st.info("💡 To change settings, edit config/storage_config.py")


def main():
    """Main application."""
    page = sidebar()

    if page == "Dashboard":
        dashboard_page()
    elif page == "Discovery":
        discovery_page()
    elif page == "Download":
        download_page()
    elif page == "Database Browser":
        database_browser_page()
    elif page == "Image Viewer":
        image_viewer_page()
    elif page == "Analysis":
        analysis_page()
    elif page == "Settings":
        settings_page()


if __name__ == "__main__":
    main()
