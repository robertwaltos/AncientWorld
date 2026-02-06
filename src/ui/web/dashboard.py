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
    LARGE_STORAGE_ROOT,
    get_config,
    update_config,
    reload_config
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

    # Reload config for fresh values
    reload_config()
    from config import storage_config
    max_storage_gb = storage_config.MAX_STORAGE_GB

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
                 f"{(total_gb/max_storage_gb)*100:.1f}% of cap")

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
        title={'text': f"Storage (GB) / {max_storage_gb:,} GB Cap"},
        gauge={
            'axis': {'range': [None, max_storage_gb]},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [0, max_storage_gb * 0.7], 'color': "lightgray"},
                {'range': [max_storage_gb * 0.7, max_storage_gb * 0.9], 'color': "yellow"},
                {'range': [max_storage_gb * 0.9, max_storage_gb], 'color': "red"}
            ],
        }
    ))
    st.plotly_chart(fig, use_container_width=True)

    # Storage requirement estimation
    st.markdown("---")
    st.subheader("📊 Storage Requirements Estimate")

    # Show current storage cap prominently
    st.info(f"💾 **Current Storage Cap:** {max_storage_gb:,} GB ({max_storage_gb/1024:.1f} TB)")

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
                help=f"{(total_estimated_gb/max_storage_gb)*100:.1f}% of {max_storage_gb:,} GB cap"
            )

        # Warning if exceeds cap
        if total_estimated_gb > max_storage_gb:
            excess_gb = total_estimated_gb - max_storage_gb
            st.warning(
                f"⚠️ **Storage Alert:** Estimated total ({total_estimated_gb:.1f} GB) "
                f"exceeds current cap ({max_storage_gb:,} GB) by {excess_gb:.1f} GB. "
                f"Go to Settings page to increase storage allocation."
            )
        else:
            remaining_gb = max_storage_gb - total_estimated_gb
            st.success(
                f"✅ **Storage OK:** {remaining_gb:.1f} GB will remain available "
                f"after downloading all pending images."
            )


def discovery_page():
    """Discovery management page with unified parallel execution."""
    st.title("🔍 Discovery Management")

    st.markdown("""
    Discovery phase: Catalog images before downloading.
    Run all sources in parallel to build a large candidate pool.
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

    # Single unified discovery button
    if st.button("🚀 Run All Discovery Sources", type="primary", use_container_width=True):
        st.info("Running all sources in parallel...")

        # Import the discovery orchestrator
        sys.path.insert(0, str(ROOT / "tools"))
        from run_all_discovery_parallel import DISCOVERY_SOURCES, run_discovery_source

        # Create progress containers for each source
        source_status = {}
        for name, _ in DISCOVERY_SOURCES:
            with st.container():
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"**{name}**")
                with col2:
                    status_placeholder = st.empty()
                    status_placeholder.info("Queued")
                source_status[name] = status_placeholder

        # Run discovery in parallel using multiprocessing
        import multiprocessing as mp
        import time

        work_items = [(name, script) for name, script in DISCOVERY_SOURCES]

        # Update status to "Searching..."
        for name in source_status:
            source_status[name].warning("Searching...")

        # Run all in parallel
        with mp.Pool(processes=len(DISCOVERY_SOURCES)) as pool:
            async_results = pool.starmap_async(run_discovery_source, work_items)

            # Poll for completion
            while not async_results.ready():
                time.sleep(1)

            # Get results
            results = async_results.get()

        # Update final status for each source
        for name, success, message, elapsed in results:
            if success:
                source_status[name].success(f"Completed ({elapsed:.1f}s)")
            else:
                source_status[name].error(f"Failed: {message}")

        # Overall summary
        successful = sum(1 for _, s, _, _ in results if s)
        failed = len(results) - successful

        if failed == 0:
            st.success(f"All {successful} sources completed successfully!")
            st.balloons()
        else:
            st.warning(f"{successful} succeeded, {failed} failed")

        st.rerun()

    st.markdown("---")
    st.subheader("Available Discovery Sources")

    # List all sources
    sources_info = [
        ("Met Museum", "Metropolitan Museum of Art API"),
        ("Europeana", "European cultural heritage aggregator"),
        ("Smithsonian", "Smithsonian Institution collections"),
        ("Getty", "Getty Museum collections"),
        ("Archive.org", "Internet Archive image collections"),
        ("British Library", "British Library collections"),
        ("Gallica (API)", "French National Library IIIF API"),
        ("Gallica (Direct)", "Direct Gallica image URLs"),
    ]

    for name, description in sources_info:
        st.write(f"- **{name}**: {description}")

    st.markdown("---")
    st.subheader("IIIF Manifest Processing")

    if st.button("🎨 Process IIIF Manifests", type="secondary", use_container_width=True):
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
                    st.success("IIIF harvesting completed!")
                    with st.expander("View results"):
                        st.code(result.stdout)
                    st.rerun()
                else:
                    st.error(f"Failed: {result.stderr}")
            except Exception as e:
                st.error(f"Error: {str(e)}")

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

    st.info("💡 Click buttons below to extract features from downloaded images. Results appear automatically below.")

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
                        st.success(f"✅ {result.stdout.strip()}")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error(f"❌ Error: {result.stderr}")
                except subprocess.TimeoutExpired:
                    st.error("⏱️ Timeout after 5 minutes")
                except Exception as e:
                    st.error(f"❌ Error: {e}")

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
                        st.success(f"✅ {result.stdout.strip()}")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error(f"❌ Error: {result.stderr}")
                except subprocess.TimeoutExpired:
                    st.error("⏱️ Timeout after 5 minutes")
                except Exception as e:
                    st.error(f"❌ Error: {e}")

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
                        st.success(f"✅ {result.stdout.strip()}")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error(f"❌ Error: {result.stderr}")
                except subprocess.TimeoutExpired:
                    st.error("⏱️ Timeout after 30 minutes")
                except Exception as e:
                    st.error(f"❌ Error: {e}")

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
                        st.success(f"✅ {result.stdout.strip()}")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error(f"❌ Error: {result.stderr}")
                except subprocess.TimeoutExpired:
                    st.error("⏱️ Timeout after 10 minutes")
                except Exception as e:
                    st.error(f"❌ Error: {e}")

    st.markdown("---")

    # Show guidance if no downloaded images
    if stats['downloaded'][0] == 0:
        st.warning("💡 Download some images first from the Download page, then come back here to analyze them")
        return

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
        st.info("📊 **No feature data yet** - Click '🔷 Extract Geometry' above to start analyzing your images")
        return

    st.success(f"✅ **{len(feats):,} images** have been analyzed. Results below:")

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
    """Settings page - fully GUI-driven configuration."""
    st.title("⚙️ Settings")

    # Reload config to get fresh values
    reload_config()
    config = get_config()

    st.markdown("Configure all application settings from this page. Changes are saved immediately.")

    st.markdown("---")

    # Storage Configuration
    st.subheader("💾 Storage Configuration")

    with st.form("storage_form"):
        storage_root = st.text_input(
            "Storage Root Directory",
            value=config['LARGE_STORAGE_ROOT'],
            help="Base directory for all data (database, images, logs)"
        )

        max_storage_gb = st.number_input(
            "Maximum Storage (GB)",
            min_value=100,
            max_value=10000,
            value=config['MAX_STORAGE_GB'],
            step=100,
            help="Maximum disk space to use (current: 2000 GB = 2 TB)"
        )

        col1, col2 = st.columns(2)
        with col1:
            min_width = st.number_input(
                "Minimum Image Width (px)",
                min_value=300,
                max_value=2000,
                value=config['MIN_IMAGE_WIDTH'],
                step=50,
                help="Skip images narrower than this"
            )

        with col2:
            min_height = st.number_input(
                "Minimum Image Height (px)",
                min_value=300,
                max_value=2000,
                value=config['MIN_IMAGE_HEIGHT'],
                step=50,
                help="Skip images shorter than this"
            )

        storage_submit = st.form_submit_button("💾 Save Storage Settings", use_container_width=True)

        if storage_submit:
            try:
                update_config(
                    LARGE_STORAGE_ROOT=storage_root,
                    MAX_STORAGE_GB=max_storage_gb,
                    MIN_IMAGE_WIDTH=min_width,
                    MIN_IMAGE_HEIGHT=min_height
                )
                st.success("✅ Storage settings saved successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error saving settings: {e}")

    st.markdown("---")

    # Download Configuration
    st.subheader("⬇️ Download Configuration")

    with st.form("download_form"):
        batch_size = st.number_input(
            "Batch Size",
            min_value=10,
            max_value=1000,
            value=config['BATCH_SIZE'],
            step=10,
            help="Number of candidates to process per batch"
        )

        sleep_time = st.number_input(
            "Sleep Between Downloads (seconds)",
            min_value=0.1,
            max_value=10.0,
            value=config['SLEEP_BETWEEN_DOWNLOADS'],
            step=0.1,
            format="%.1f",
            help="Delay between downloads to respect rate limits"
        )

        col1, col2 = st.columns(2)
        with col1:
            timeout = st.number_input(
                "Request Timeout (seconds)",
                min_value=10,
                max_value=300,
                value=config['REQUEST_TIMEOUT'],
                step=10,
                help="Maximum time to wait for a response"
            )

        with col2:
            max_retries = st.number_input(
                "Maximum Retries",
                min_value=1,
                max_value=10,
                value=config['MAX_RETRIES'],
                step=1,
                help="Number of retry attempts for failed downloads"
            )

        download_submit = st.form_submit_button("💾 Save Download Settings", use_container_width=True)

        if download_submit:
            try:
                update_config(
                    BATCH_SIZE=batch_size,
                    SLEEP_BETWEEN_DOWNLOADS=sleep_time,
                    REQUEST_TIMEOUT=timeout,
                    MAX_RETRIES=max_retries
                )
                st.success("✅ Download settings saved successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error saving settings: {e}")

    st.markdown("---")

    # Deduplication Configuration
    st.subheader("🔍 Deduplication Configuration")

    with st.form("dedup_form"):
        perceptual_threshold = st.slider(
            "Perceptual Hash Threshold",
            min_value=0,
            max_value=20,
            value=config['PERCEPTUAL_HASH_THRESHOLD'],
            step=1,
            help="Hamming distance for near-duplicate detection (lower = stricter)"
        )

        dedup_submit = st.form_submit_button("💾 Save Deduplication Settings", use_container_width=True)

        if dedup_submit:
            try:
                update_config(PERCEPTUAL_HASH_THRESHOLD=perceptual_threshold)
                st.success("✅ Deduplication settings saved successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error saving settings: {e}")

    st.markdown("---")

    # Feature Extraction Configuration
    st.subheader("🔬 Automatic Feature Extraction")

    with st.form("extraction_form"):
        st.markdown("Configure which features to extract automatically after downloading new images.")

        auto_extract = st.checkbox(
            "Enable Automatic Feature Extraction",
            value=config['AUTO_EXTRACT_FEATURES'],
            help="Run feature extraction after each download batch completes"
        )

        st.markdown("**Feature Types:**")

        col1, col2 = st.columns(2)

        with col1:
            auto_geometry = st.checkbox(
                "Geometry Features (fast)",
                value=config['AUTO_EXTRACT_GEOMETRY'],
                help="Lines, circles, symmetry, radialness, orientation",
                disabled=not auto_extract
            )

            auto_scale = st.checkbox(
                "Scale Features (fast)",
                value=config['AUTO_EXTRACT_SCALE'],
                help="Door/window aspect ratios and opening counts",
                disabled=not auto_extract
            )

        with col2:
            auto_embeddings = st.checkbox(
                "CLIP Embeddings (slow, GPU recommended)",
                value=config['AUTO_EXTRACT_EMBEDDINGS'],
                help="Semantic embeddings for image search and clustering",
                disabled=not auto_extract
            )

            auto_tda = st.checkbox(
                "TDA Features (slow)",
                value=config['AUTO_EXTRACT_TDA'],
                help="Topological data analysis (persistent homology)",
                disabled=not auto_extract
            )

        extraction_submit = st.form_submit_button("💾 Save Extraction Settings", use_container_width=True)

        if extraction_submit:
            try:
                update_config(
                    AUTO_EXTRACT_FEATURES=auto_extract,
                    AUTO_EXTRACT_GEOMETRY=auto_geometry,
                    AUTO_EXTRACT_SCALE=auto_scale,
                    AUTO_EXTRACT_EMBEDDINGS=auto_embeddings,
                    AUTO_EXTRACT_TDA=auto_tda
                )
                st.success("✅ Feature extraction settings saved successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error saving settings: {e}")

    st.markdown("---")

    # Current Configuration Summary
    st.subheader("📋 Current Configuration")

    reload_config()
    from config import storage_config

    col1, col2 = st.columns(2)

    with col1:
        st.code(f"Storage Root: {storage_config.LARGE_STORAGE_ROOT}")
        st.code(f"Database: {storage_config.DB_PATH}")
        st.code(f"Images: {storage_config.IMAGES_ROOT}")
        st.code(f"Max Storage: {storage_config.MAX_STORAGE_GB:,} GB ({storage_config.MAX_STORAGE_GB/1024:.1f} TB)")
        st.code(f"Batch Size: {storage_config.BATCH_SIZE}")

    with col2:
        st.code(f"Min Width: {storage_config.MIN_IMAGE_WIDTH} px")
        st.code(f"Min Height: {storage_config.MIN_IMAGE_HEIGHT} px")
        st.code(f"Sleep Time: {storage_config.SLEEP_BETWEEN_DOWNLOADS}s")
        st.code(f"Timeout: {storage_config.REQUEST_TIMEOUT}s")
        st.code(f"Max Retries: {storage_config.MAX_RETRIES}")
        st.code(f"Perceptual Hash Threshold: {storage_config.PERCEPTUAL_HASH_THRESHOLD}")

    st.markdown("**Auto-Extraction:**")
    extraction_status = "✅ Enabled" if storage_config.AUTO_EXTRACT_FEATURES else "❌ Disabled"
    st.code(f"Auto Extract: {extraction_status}")
    if storage_config.AUTO_EXTRACT_FEATURES:
        features = []
        if storage_config.AUTO_EXTRACT_GEOMETRY:
            features.append("Geometry")
        if storage_config.AUTO_EXTRACT_SCALE:
            features.append("Scale")
        if storage_config.AUTO_EXTRACT_EMBEDDINGS:
            features.append("Embeddings")
        if storage_config.AUTO_EXTRACT_TDA:
            features.append("TDA")
        st.code(f"  Features: {', '.join(features) if features else 'None'}")

    st.info("💡 All settings are automatically applied. Restart any running download processes to use new settings.")


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
