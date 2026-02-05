import os
import re
import time
import sqlite3
import requests
from pathlib import Path

DB_PATH = Path(r"E:\ancientgeo\db\assets.sqlite3")
OUT_DIR = Path(r"E:\ancientgeo\images")

CAP_GB = 500
CAP_BYTES = CAP_GB * 1024**3

BATCH = 200
SLEEP_BETWEEN = 0.1
TIMEOUT = 60

UA = "ancientgeo/1.0 (research downloader; contact: local)"

def safe_ext(mime: str, url: str) -> str:
    if mime:
        mime = mime.lower()
        if "jpeg" in mime: return ".jpg"
        if "png" in mime: return ".png"
        if "tiff" in mime or "tif" in mime: return ".tif"
        if "webp" in mime: return ".webp"
    # fallback from URL
    m = re.search(r"\.(jpg|jpeg|png|tif|tiff|webp)(\?|$)", url, re.I)
    if m:
        return "." + m.group(1).lower().replace("jpeg", "jpg").replace("tiff", "tif")
    return ".bin"

def ensure_prefix_path(filename: str) -> Path:
    # filename should be a hash-ish string; create ab/cd/ directories
    p1 = filename[:2] if len(filename) >= 2 else "xx"
    p2 = filename[2:4] if len(filename) >= 4 else "yy"
    d = OUT_DIR / p1 / p2
    d.mkdir(parents=True, exist_ok=True)
    return d

def get_total(con) -> int:
    (v,) = con.execute("SELECT v FROM stats WHERE k='total_downloaded_bytes'").fetchone()
    return int(v)

def set_total(con, v: int) -> None:
    con.execute("UPDATE stats SET v=? WHERE k='total_downloaded_bytes'", (int(v),))
    con.commit()

def pick_batch(con):
    return con.execute("""
        SELECT id, image_url, mime, sha1
        FROM candidates
        WHERE status='pending'
        ORDER BY id ASC
        LIMIT ?
    """, (BATCH,)).fetchall()

def mark(con, cid: int, status: str, **fields):
    cols = ["status=?", "updated_at=datetime('now')"]
    vals = [status]
    for k, v in fields.items():
        cols.append(f"{k}=?")
        vals.append(v)
    vals.append(cid)
    con.execute(f"UPDATE candidates SET {', '.join(cols)} WHERE id=?", vals)

def head_size(session: requests.Session, url: str):
    try:
        r = session.head(url, allow_redirects=True, timeout=TIMEOUT, headers={"User-Agent": UA})
        cl = r.headers.get("Content-Length")
        return r.status_code, int(cl) if cl and cl.isdigit() else None
    except Exception:
        return None, None

def download_file(session: requests.Session, url: str, dest: Path):
    dest_tmp = dest.with_suffix(dest.suffix + ".part")
    bytes_written = 0
    with session.get(url, stream=True, timeout=TIMEOUT, headers={"User-Agent": UA}) as r:
        r.raise_for_status()
        with open(dest_tmp, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 256):
                if not chunk:
                    continue
                f.write(chunk)
                bytes_written += len(chunk)
    os.replace(dest_tmp, dest)
    return bytes_written, r.status_code

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA journal_mode=WAL;")
    con.execute("PRAGMA synchronous=NORMAL;")
    total = get_total(con)

    session = requests.Session()

    print(f"Cap: {CAP_GB} GB ({CAP_BYTES} bytes)")
    print(f"Already downloaded (tracked): {total / 1024**3:.2f} GB")

    while total < CAP_BYTES:
        batch = pick_batch(con)
        if not batch:
            print("No more pending candidates.")
            break

        for cid, url, mime, sha1 in batch:
            if total >= CAP_BYTES:
                break

            mark(con, cid, "downloading")
            con.commit()

            # Prefer sha1-based naming when available
            name_base = sha1.lower() if sha1 else f"id{cid}"
            ext = safe_ext(mime, url)
            out_dir = ensure_prefix_path(name_base)
            dest = out_dir / (name_base + ext)

            # Skip if file already exists
            if dest.exists():
                mark(con, cid, "downloaded", local_path=str(dest), downloaded_bytes=dest.stat().st_size)
                con.commit()
                continue

            # HEAD pre-check: if it pushes us beyond cap, stop
            status, cl = head_size(session, url)
            if cl is not None and total + cl > CAP_BYTES:
                mark(con, cid, "skipped", http_status=status, content_length=cl, error="would exceed cap")
                con.commit()
                print("Stopping: next file would exceed cap.")
                total = CAP_BYTES  # force exit
                break

            try:
                bytes_written, http_status = download_file(session, url, dest)
                total += bytes_written
                set_total(con, total)
                mark(con, cid, "downloaded",
                     http_status=http_status,
                     content_length=cl,
                     downloaded_bytes=bytes_written,
                     local_path=str(dest))
                con.commit()

                if (cid % 50) == 0:
                    print(f"Total: {total / 1024**3:.2f} GB")

            except Exception as e:
                mark(con, cid, "failed", error=str(e))
                con.commit()

            time.sleep(SLEEP_BETWEEN)

    print(f"Done. Total downloaded: {total / 1024**3:.2f} GB")
    con.close()

if __name__ == "__main__":
    main()
