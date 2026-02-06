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


@st.cache_resource(ttl=60)  # Cache for 60 seconds to pick up config changes
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

    # Storage requirement estimation
    st.markdown("---")
    st.subheader("📊 Storage Requirements Estimate")

    # Show current storage cap prominently
    st.info(f"💾 **Current Storage Cap:** {MAX_STORAGE_GB:,} GB ({MAX_STORAGE_GB/1024:.1f} TB)")

    con = get_db_connection()
    if con:
        # Count pending images
        pending_count = con.execute(
            "SELECT COUNT(*) FROM candidates WHERE status='pending'"
        ).fetchone()[0]

        # Average image size estimation (based on downloaded samples)
        avg_size_result = con.execute("""
            SELECT AVG(downloaded_bytes)
            FROM candidates
            WHERE status='downloaded' AND downloaded_bytes > 0
        """).fetchone()

        avg_size_mb = (avg_size_result[0] / 1024**2) if avg_size_result[0] else 2.5  # Default 2.5MB

        # Calculate total estimated storage
        estimated_pending_gb = (pending_count * avg_size_mb) / 1024
        current_gb = stats.get("total_downloaded_bytes", 0) / 1024**3
        total_estimated_gb = current_gb + estimated_pending_gb

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "Pending Images",
                f"{pending_count:,}",
                help="Number of discovered images not yet downloaded"
            )

        with col2:
            st.metric(
                "Estimated Storage Needed",
                f"{estimated_pending_gb:.1f} GB",
                help=f"Based on average image size of {avg_size_mb:.2f} MB"
            )

        with col3:
            st.metric(
                "Total Estimated (Current + Pending)",
                f"{total_estimated_gb:.1f} GB",
                help=f"{(total_estimated_gb/MAX_STORAGE_GB)*100:.1f}% of {MAX_STORAGE_GB} GB cap"
            )

        # Warning if exceeds cap
        if total_estimated_gb > MAX_STORAGE_GB:
            excess_gb = total_estimated_gb - MAX_STORAGE_GB
            st.warning(
                f"⚠️ **Storage Alert:** Estimated total ({total_estimated_gb:.1f} GB) "
                f"exceeds current cap ({MAX_STORAGE_GB} GB) by {excess_gb:.1f} GB. "
                f"Consider increasing storage allocation in config/storage_config.py"
            )
        else:
            remaining_gb = MAX_STORAGE_GB - total_estimated_gb
            st.success(
                f"✅ **Storage OK:** {remaining_gb:.1f} GB will remain available "
                f"after downloading all pending images."
            )


def discovery_page():
    """Discovery management page."""
    st.title("🔍 Discovery Management")

    st.markdown("""
    Discovery phase: Catalog images before downloading.
    This allows building a large candidate pool to prioritize downloads.
    """)

    # Show current counts
    con = get_db_connection()
    if con:
        (candidates_count,) = con.execute("SELECT COUNT(*) FROM candidates").fetchone()
        try:
            (manifests_count,) = con.execute("SELECT COUNT(*) FROM manifests").fetchone()
        except:
            manifests_count = 0

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Image Candidates", f"{candidates_count:,}")
        with col2:
            st.metric("IIIF Manifests", f"{manifests_count:,}")
        with col3:
            try:
                (pending_manifests,) = con.execute(
                    "SELECT COUNT(*) FROM manifests WHERE status='pending'"
                ).fetchone()
            except:
                pending_manifests = 0
            st.metric("Pending Manifests", f"{pending_manifests:,}")

    st.markdown("---")
    st.subheader("MediaWiki Sources")

    if st.button("🏛️ Wikimedia Commons", use_container_width=True):
        with st.spinner("Starting Wikimedia Commons discovery..."):
            try:
                scrapy_dir = ROOT / "ancientgeo"
                result = subprocess.run(
                    ["python", "-m", "scrapy", "crawl", "commons_discover"],
                    cwd=str(scrapy_dir),
                    capture_output=True,
                    text=True,
                    timeout=300
                )

                if result.returncode == 0:
                    st.success("✅ Discovery completed!")
                    with st.expander("View output"):
                        st.code(result.stdout)
                    st.rerun()
                else:
                    st.error(f"❌ Failed with return code {result.returncode}")
                    with st.expander("View error"):
                        st.code(result.stderr)
            except subprocess.TimeoutExpired:
                st.warning("⏱️ Still running (timeout after 5 minutes)")
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")

    st.markdown("---")
    st.subheader("Museum & Institution APIs")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🖼️ Met Museum", use_container_width=True):
            with st.spinner("Discovering Met Museum images..."):
                try:
                    result = subprocess.run(
                        ["python", "tools/met_discover.py"],
                        cwd=str(ROOT),
                        capture_output=True,
                        text=True,
                        timeout=600
                    )
                    if result.returncode == 0:
                        st.success("✅ Met discovery completed!")
                        with st.expander("View results"):
                            st.code(result.stdout)
                        st.rerun()
                    else:
                        st.error(f"❌ Failed: {result.stderr}")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")

        if st.button("🇪🇺 Europeana", use_container_width=True):
            st.info("⚠️ Requires EUROPEANA_API_KEY environment variable")
            with st.spinner("Discovering Europeana images..."):
                try:
                    result = subprocess.run(
                        ["python", "tools/europeana_discover.py"],
                        cwd=str(ROOT),
                        capture_output=True,
                        text=True,
                        timeout=600
                    )
                    if result.returncode == 0:
                        st.success("✅ Europeana discovery completed!")
                        with st.expander("View results"):
                            st.code(result.stdout)
                        st.rerun()
                    else:
                        st.error(f"❌ Failed: {result.stderr}")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")

    with col2:
        if st.button("🇫🇷 Gallica (BnF)", use_container_width=True):
            with st.spinner("Discovering Gallica manifests..."):
                try:
                    result = subprocess.run(
                        ["python", "tools/gallica_discover.py"],
                        cwd=str(ROOT),
                        capture_output=True,
                        text=True,
                        timeout=600
                    )
                    if result.returncode == 0:
                        st.success("✅ Gallica discovery completed!")
                        with st.expander("View results"):
                            st.code(result.stdout)
                        st.rerun()
                    else:
                        st.error(f"❌ Failed: {result.stderr}")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")

        if st.button("📚 Internet Archive", use_container_width=True):
            with st.spinner("Discovering Internet Archive items..."):
                try:
                    result = subprocess.run(
                        ["python", "tools/archive_org_discover.py"],
                        cwd=str(ROOT),
                        capture_output=True,
                        text=True,
                        timeout=600
                    )
                    if result.returncode == 0:
                        st.success("✅ Archive.org discovery completed!")
                        with st.expander("View results"):
                            st.code(result.stdout)
                        st.rerun()
                    else:
                        st.error(f"❌ Failed: {result.stderr}")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")

    st.markdown("---")
    st.subheader("Alternative & Additional Sources")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🎨 Gallica Direct Images", type="primary", use_container_width=True):
            st.info("Uses direct .highres URLs instead of blocked IIIF")
            with st.spinner("Discovering Gallica direct images..."):
                try:
                    result = subprocess.run(
                        ["python", "tools/gallica_direct_images.py"],
                        cwd=str(ROOT),
                        capture_output=True,
                        text=True,
                        timeout=900
                    )
                    if result.returncode == 0:
                        st.success("✅ Gallica direct discovery completed!")
                        with st.expander("View results"):
                            st.code(result.stdout)
                        st.rerun()
                    else:
                        st.error(f"❌ Failed: {result.stderr}")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")

        if st.button("🇳🇱 Rijksmuseum", use_container_width=True):
            st.info("⚠️ Requires RIJKSMUSEUM_API_KEY environment variable")
            with st.spinner("Discovering Rijksmuseum images..."):
                try:
                    result = subprocess.run(
                        ["python", "tools/rijksmuseum_discover.py"],
                        cwd=str(ROOT),
                        capture_output=True,
                        text=True,
                        timeout=300
                    )
                    if result.returncode == 0:
                        st.success("✅ Rijksmuseum discovery completed!")
                        with st.expander("View results"):
                            st.code(result.stdout)
                        st.rerun()
                    else:
                        st.error(f"❌ Failed: {result.stderr}")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")

    with col2:
        if st.button("🏛️ Smithsonian", use_container_width=True):
            st.info("⚠️ Requires SMITHSONIAN_API_KEY environment variable")
            with st.spinner("Discovering Smithsonian images..."):
                try:
                    result = subprocess.run(
                        ["python", "tools/smithsonian_discover.py"],
                        cwd=str(ROOT),
                        capture_output=True,
                        text=True,
                        timeout=300
                    )
                    if result.returncode == 0:
                        st.success("✅ Smithsonian discovery completed!")
                        with st.expander("View results"):
                            st.code(result.stdout)
                        st.rerun()
                    else:
                        st.error(f"❌ Failed: {result.stderr}")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")

        if st.button("🚀 Run All Enhanced", use_container_width=True):
            st.info("Runs all sources with expanded queries")
            with st.spinner("Running all enhanced discovery sources..."):
                try:
                    result = subprocess.run(
                        ["python", "tools/run_all_discovery_enhanced.py"],
                        cwd=str(ROOT),
                        capture_output=True,
                        text=True,
                        timeout=1800
                    )
                    if result.returncode == 0:
                        st.success("✅ All enhanced discovery completed!")
                        with st.expander("View results"):
                            st.code(result.stdout)
                        st.rerun()
                    else:
                        st.error(f"❌ Failed: {result.stderr}")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")

    st.markdown("---")
    st.subheader("IIIF Manifest Processing")

    if st.button("🎨 Process IIIF Manifests", type="primary", use_container_width=True):
        with st.spinner("Harvesting images from IIIF manifests..."):
            try:
                result = subprocess.run(
                    ["python", "tools/iiif_harvest_manifest.py"],
                    cwd=str(ROOT),
                    capture_output=True,
                    text=True,
                    timeout=600
                )
                if result.returncode == 0:
                    st.success("✅ IIIF harvesting completed!")
                    with st.expander("View results"):
                        st.code(result.stdout)
                    st.rerun()
                else:
                    st.error(f"❌ Failed: {result.stderr}")
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")

    st.caption("IIIF manifests from Gallica, Archive.org, and Europeana must be processed to extract individual images.")


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
    st.subheader("Failed Downloads")

    # Show failed count
    con = get_db_connection()
    if con:
        (failed_count,) = con.execute(
            "SELECT COUNT(*) FROM candidates WHERE status='failed'"
        ).fetchone()

        if failed_count > 0:
            st.warning(f"⚠️ {failed_count} downloads failed (likely due to rate limiting)")

            if st.button("🔄 Retry Failed Downloads", use_container_width=True):
                with st.spinner("Resetting failed downloads to pending..."):
                    try:
                        result = subprocess.run(
                            ["python", "tools/retry_failed.py"],
                            cwd=str(ROOT),
                            capture_output=True,
                            text=True,
                            input="y\n",  # Auto-confirm
                            timeout=60
                        )

                        if result.returncode == 0:
                            st.success("✅ Failed downloads reset to pending!")
                            with st.expander("View results"):
                                st.code(result.stdout)
                            st.rerun()
                        else:
                            st.error(f"❌ Reset failed: {result.stderr}")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
        else:
            st.info("✓ No failed downloads")

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
    """Image viewer page with pagination and caching."""
    st.title("🖼️ Image Viewer")

    con = get_db_connection()
    if not con:
        st.error("Database not initialized")
        return

    # Get total count
    (total_images,) = con.execute("""
        SELECT COUNT(*)
        FROM candidates
        WHERE status='downloaded' AND local_path IS NOT NULL
    """).fetchone()

    if total_images == 0:
        st.info("No images downloaded yet")
        return

    st.markdown(f"**Total Downloaded Images:** {total_images:,}")

    # Initialize session state for pagination
    if 'page_num' not in st.session_state:
        st.session_state.page_num = 0

    if 'image_cache' not in st.session_state:
        st.session_state.image_cache = {}

    IMAGES_PER_PAGE = 20
    total_pages = (total_images + IMAGES_PER_PAGE - 1) // IMAGES_PER_PAGE
    current_page = st.session_state.page_num

    # Page navigation controls
    col1, col2, col3, col4, col5 = st.columns([1, 1, 2, 1, 1])

    with col1:
        if st.button("⏮️ First", use_container_width=True):
            st.session_state.page_num = 0
            st.rerun()

    with col2:
        if st.button("◀️ Back", use_container_width=True, disabled=(current_page == 0)):
            st.session_state.page_num = max(0, current_page - 1)
            st.rerun()

    with col3:
        st.markdown(f"<div style='text-align: center; padding-top: 8px;'>**Page {current_page + 1} of {total_pages}**</div>", unsafe_allow_html=True)

    with col4:
        if st.button("Next ▶️", use_container_width=True, disabled=(current_page >= total_pages - 1)):
            st.session_state.page_num = min(total_pages - 1, current_page + 1)
            st.rerun()

    with col5:
        if st.button("Last ⏭️", use_container_width=True):
            st.session_state.page_num = total_pages - 1
            st.rerun()

    st.markdown("---")

    # Fetch current page images
    offset = current_page * IMAGES_PER_PAGE
    rows = con.execute("""
        SELECT id, title, local_path, width, height, source
        FROM candidates
        WHERE status='downloaded' AND local_path IS NOT NULL
        ORDER BY id DESC
        LIMIT ? OFFSET ?
    """, (IMAGES_PER_PAGE, offset)).fetchall()

    # Pre-cache next page images in background
    if current_page < total_pages - 1:
        next_offset = (current_page + 1) * IMAGES_PER_PAGE
        next_rows = con.execute("""
            SELECT id, local_path
            FROM candidates
            WHERE status='downloaded' AND local_path IS NOT NULL
            ORDER BY id DESC
            LIMIT ? OFFSET ?
        """, (IMAGES_PER_PAGE, next_offset)).fetchall()

        # Store next page paths in cache
        for cid, local_path in next_rows:
            if cid not in st.session_state.image_cache:
                st.session_state.image_cache[cid] = local_path

    # Display current page images in a 4-column grid
    cols = st.columns(4)

    for idx, (cid, title, local_path, width, height, source) in enumerate(rows):
        col = cols[idx % 4]

        path = Path(local_path)
        if path.exists():
            with col:
                try:
                    # Check cache first
                    if cid in st.session_state.image_cache and Path(st.session_state.image_cache[cid]).exists():
                        img = Image.open(st.session_state.image_cache[cid])
                    else:
                        img = Image.open(path)
                        st.session_state.image_cache[cid] = str(path)

                    st.image(img, use_container_width=True)

                    # Metadata
                    with st.expander(f"📄 {title[:30] if title else 'Untitled'}..."):
                        st.caption(f"**ID:** {cid}")
                        st.caption(f"**Dimensions:** {width}×{height}")
                        st.caption(f"**Source:** {source}")
                        st.caption(f"**Path:** {path.name}")

                except Exception as e:
                    st.error(f"Error loading image {cid}: {str(e)[:50]}")
        else:
            with col:
                st.warning(f"Missing:\n{cid}")

    # Clean cache if too large (keep only current and next page)
    cache_threshold = IMAGES_PER_PAGE * 3
    if len(st.session_state.image_cache) > cache_threshold:
        # Keep only recent IDs
        all_ids = {row[0] for row in rows}
        if current_page < total_pages - 1:
            next_ids = {row[0] for row in next_rows}
            all_ids.update(next_ids)

        # Remove old entries
        old_keys = [k for k in st.session_state.image_cache.keys() if k not in all_ids]
        for k in old_keys:
            del st.session_state.image_cache[k]

    st.markdown("---")

    # Bottom navigation (same as top)
    col1, col2, col3, col4, col5 = st.columns([1, 1, 2, 1, 1])

    with col1:
        if st.button("⏮️ First ", key="first2", use_container_width=True):
            st.session_state.page_num = 0
            st.rerun()

    with col2:
        if st.button("◀️ Back ", key="back2", use_container_width=True, disabled=(current_page == 0)):
            st.session_state.page_num = max(0, current_page - 1)
            st.rerun()

    with col3:
        # Jump to page
        page_input = st.number_input(
            "Jump to page:",
            min_value=1,
            max_value=total_pages,
            value=current_page + 1,
            step=1,
            key="page_jump"
        )
        if st.button("Go", use_container_width=True):
            st.session_state.page_num = page_input - 1
            st.rerun()

    with col4:
        if st.button("Next ▶️ ", key="next2", use_container_width=True, disabled=(current_page >= total_pages - 1)):
            st.session_state.page_num = min(total_pages - 1, current_page + 1)
            st.rerun()

    with col5:
        if st.button("Last ⏭️ ", key="last2", use_container_width=True):
            st.session_state.page_num = total_pages - 1
            st.rerun()


def analysis_page():
    """Analysis page with geometry and scale features."""
    st.title("🔬 Analysis")

    # Get database connection
    con = get_db_connection()
    if not con:
        st.error("Database not initialized")
        return

    # Stats overview
    st.subheader("Analysis Status")
    stats = pd.read_sql_query("""
      SELECT
        (SELECT COUNT(*) FROM candidates WHERE status='downloaded') AS downloaded,
        (SELECT COUNT(*) FROM image_features) AS featurized,
        (SELECT COUNT(*) FROM embeddings) AS embedded,
        (SELECT COUNT(*) FROM tda_features) AS tda_done
    """, con)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Downloaded Images", f"{stats['downloaded'][0]:,}")
    with col2:
        st.metric("Geometry Features", f"{stats['featurized'][0]:,}")
    with col3:
        st.metric("CLIP Embeddings", f"{stats['embedded'][0]:,}")
    with col4:
        st.metric("TDA Features", f"{stats['tda_done'][0]:,}")

    st.markdown("---")

    # Feature extraction tools
    st.subheader("🛠️ Feature Extraction Tools")

    col_a, col_b, col_c, col_d = st.columns(4)

    with col_a:
        if st.button("🔷 Extract Geometry", use_container_width=True, help="Extract lines, circles, symmetry features"):
            with st.spinner("Extracting geometry features..."):
                try:
                    result = subprocess.run(
                        [sys.executable, "tools/extract_geometry_features.py"],
                        capture_output=True,
                        text=True,
                        timeout=300,
                        cwd=str(ROOT)
                    )
                    if result.returncode == 0:
                        st.success(result.stdout)
                        st.rerun()
                    else:
                        st.error(f"Error: {result.stderr}")
                except subprocess.TimeoutExpired:
                    st.error("Timeout after 5 minutes")
                except Exception as e:
                    st.error(f"Error: {e}")

    with col_b:
        if st.button("📐 Extract Scale", use_container_width=True, help="Analyze door/window aspect ratios"):
            with st.spinner("Extracting scale features..."):
                try:
                    result = subprocess.run(
                        [sys.executable, "tools/extract_scale_features.py"],
                        capture_output=True,
                        text=True,
                        timeout=300,
                        cwd=str(ROOT)
                    )
                    if result.returncode == 0:
                        st.success(result.stdout)
                        st.rerun()
                    else:
                        st.error(f"Error: {result.stderr}")
                except subprocess.TimeoutExpired:
                    st.error("Timeout after 5 minutes")
                except Exception as e:
                    st.error(f"Error: {e}")

    with col_c:
        if st.button("🖼️ CLIP Embeddings", use_container_width=True, help="Generate semantic embeddings (optional, requires GPU)"):
            with st.spinner("Generating CLIP embeddings... (this may take a while)"):
                try:
                    result = subprocess.run(
                        [sys.executable, "tools/clip_embed_images.py"],
                        capture_output=True,
                        text=True,
                        timeout=1800,  # 30 min
                        cwd=str(ROOT)
                    )
                    if result.returncode == 0:
                        st.success(result.stdout)
                        st.rerun()
                    else:
                        st.error(f"Error: {result.stderr}")
                except subprocess.TimeoutExpired:
                    st.error("Timeout after 30 minutes")
                except Exception as e:
                    st.error(f"Error: {e}")

    with col_d:
        if st.button("🔬 TDA Features", use_container_width=True, help="Topological data analysis (optional, experimental)"):
            with st.spinner("Extracting TDA features..."):
                try:
                    result = subprocess.run(
                        [sys.executable, "tools/extract_tda_features.py"],
                        capture_output=True,
                        text=True,
                        timeout=600,  # 10 min
                        cwd=str(ROOT)
                    )
                    if result.returncode == 0:
                        st.success(result.stdout)
                        st.rerun()
                    else:
                        st.error(f"Error: {result.stderr}")
                except subprocess.TimeoutExpired:
                    st.error("Timeout after 10 minutes")
                except Exception as e:
                    st.error(f"Error: {e}")

    # Show guidance if no features
    if stats['downloaded'][0] == 0:
        st.info("💡 Download some images first from the Download page")
        return

    if stats['featurized'][0] == 0:
        st.info("💡 Click '🔷 Extract Geometry' above to start analyzing your images")
        return

    st.markdown("---")

    # Load feature data
    feats = pd.read_sql_query("""
      SELECT f.candidate_id, f.edge_density, f.line_count, f.radialness,
             f.opening_count, f.door_window_aspect_mean, f.door_window_aspect_p90,
             c.local_path, c.page_url, c.source, c.title
      FROM image_features f
      JOIN candidates c ON c.id = f.candidate_id
      ORDER BY f.candidate_id DESC
      LIMIT 5000
    """, con)

    if feats.empty:
        st.warning("No feature data available")
        return

    # Distributions
    st.subheader("Feature Distributions")

    tab1, tab2, tab3 = st.tabs(["Radialness", "Edge Density", "Lines"])

    with tab1:
        st.write("**Radialness** - Measures circular/radial patterns")
        st.bar_chart(feats["radialness"].value_counts(bins=20, sort=False))
        st.caption(f"Mean: {feats['radialness'].mean():.3f}, Median: {feats['radialness'].median():.3f}")

    with tab2:
        st.write("**Edge Density** - Measures detail/complexity")
        st.bar_chart(feats["edge_density"].value_counts(bins=20, sort=False))
        st.caption(f"Mean: {feats['edge_density'].mean():.3f}, Median: {feats['edge_density'].median():.3f}")

    with tab3:
        st.write("**Line Count** - Number of detected straight lines")
        st.bar_chart(feats["line_count"].value_counts(bins=20, sort=False))
        st.caption(f"Mean: {feats['line_count'].mean():.1f}, Median: {feats['line_count'].median():.1f}")

    st.markdown("---")

    # Most radial candidates
    st.subheader("🎯 Most Radial Candidates")
    st.caption("Images with strong circular/radial patterns (rose windows, domes, etc.)")

    top = feats.sort_values("radialness", ascending=False).head(24)
    cols = st.columns(4)

    for i, row in enumerate(top.itertuples()):
        with cols[i % 4]:
            path = Path(row.local_path)
            if path.exists():
                st.image(str(path), caption=f"radial={row.radialness:.2f}", use_container_width=True)
                if row.title:
                    st.caption(row.title[:50])
                if row.page_url:
                    st.link_button("View Source", row.page_url, use_container_width=True)


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
