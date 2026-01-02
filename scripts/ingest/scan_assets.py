#!/usr/bin/env python3
import argparse
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator, List, Optional, Sequence, Tuple

try:
    from dotenv import load_dotenv
except ImportError:  # optional
    load_dotenv = None

import geopandas as gpd
import psycopg2
import psycopg2.extras
import rasterio
from rasterio.warp import transform_bounds
from shapely.geometry import box


EXTENSIONS = {".tif", ".tiff", ".shp", ".geojson", ".gpkg"}
PROJ_EXTENSION = "https://stac-extensions.github.io/projection/v1.0.0/schema.json"
FILE_EXTENSION = "https://stac-extensions.github.io/file/v2.1.0/schema.json"


def load_env(project_root: Path) -> None:
    env_path = project_root / ".env"
    if load_dotenv and env_path.exists():
        load_dotenv(env_path)
        return
    if not env_path.exists():
        return
    with env_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            os.environ.setdefault(key, value)


def iter_asset_paths(root: Path) -> Iterator[Path]:
    for dirpath, _, filenames in os.walk(root):
        for name in filenames:
            ext = Path(name).suffix.lower()
            if ext in EXTENSIONS:
                yield Path(dirpath) / name


def chunked(items: Iterable[Path], size: int) -> Iterator[List[Path]]:
    batch: List[Path] = []
    for item in items:
        batch.append(item)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch


def detect_media_type(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in {".tif", ".tiff"}:
        return "image/tiff; application=geotiff"
    if ext == ".shp":
        return "application/vnd.shp"
    if ext == ".geojson":
        return "application/geo+json"
    if ext == ".gpkg":
        return "application/geopackage+sqlite3"
    return "application/octet-stream"


def to_bbox_wkt(bounds: Sequence[float]) -> Tuple[List[float], str]:
    minx, miny, maxx, maxy = bounds
    geom = box(minx, miny, maxx, maxy)
    return [minx, miny, maxx, maxy], geom.wkt


def raster_metadata(path: Path) -> Optional[Tuple[List[float], str, Optional[int]]]:
    with rasterio.open(path) as dataset:
        if dataset.crs is None:
            return None
        epsg = dataset.crs.to_epsg()
        bounds = dataset.bounds
        if dataset.crs.to_epsg() != 4326:
            bounds = transform_bounds(dataset.crs, "EPSG:4326", *bounds, densify_pts=21)
        bbox, geom_wkt = to_bbox_wkt(bounds)
        return bbox, geom_wkt, epsg


def vector_metadata(path: Path) -> Optional[Tuple[List[float], str, Optional[int]]]:
    gdf = gpd.read_file(path)
    if gdf.empty or gdf.crs is None:
        return None
    epsg = gdf.crs.to_epsg()
    minx, miny, maxx, maxy = gdf.total_bounds.tolist()
    if not all(map(lambda v: v == v, [minx, miny, maxx, maxy])):
        return None
    if gdf.crs.to_epsg() != 4326:
        minx, miny, maxx, maxy = transform_bounds(
            gdf.crs, "EPSG:4326", minx, miny, maxx, maxy, densify_pts=21
        )
    bbox, geom_wkt = to_bbox_wkt((minx, miny, maxx, maxy))
    return bbox, geom_wkt, epsg


def fetch_existing_paths(conn, paths: Sequence[str]) -> set:
    if not paths:
        return set()
    with conn.cursor() as cur:
        cur.execute("SELECT nas_path FROM items WHERE nas_path = ANY(%s)", (list(paths),))
        rows = cur.fetchall()
    return {row[0] for row in rows}


def ensure_collection(conn, collection_id: str, title: str, description: str, nas_root: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO collections (
              id, title, description, stac_version, stac_extensions, keywords, links, extra_fields, nas_root
            )
            VALUES (%s, %s, %s, '1.0.0', %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
            """,
            (
                collection_id,
                title,
                description,
                [],
                [],
                psycopg2.extras.Json([]),
                psycopg2.extras.Json({}),
                nas_root,
            ),
        )
    conn.commit()


def insert_items(conn, rows: List[Tuple]) -> None:
    if not rows:
        return
    query = """
        INSERT INTO items (
          id, collection_id, title, description, stac_version, stac_extensions,
          datetime, geom, bbox, properties, assets, links, nas_path, extra_fields
        )
        VALUES %s
        ON CONFLICT (id) DO NOTHING
    """
    template = (
        "(%s, %s, %s, %s, %s, %s, %s, ST_GeomFromText(%s, 4326), %s, %s, %s, %s, %s, %s)"
    )
    with conn.cursor() as cur:
        psycopg2.extras.execute_values(cur, query, rows, template=template, page_size=200)
    conn.commit()


def build_item_row(
    path: Path,
    rel_path: str,
    nas_path: str,
    collection_id: str,
    bbox: List[float],
    geom_wkt: str,
    epsg: Optional[int],
) -> Tuple:
    stat = path.stat()
    media_type = detect_media_type(path)
    stac_extensions = []
    properties = {}
    if epsg is not None:
        properties["proj:epsg"] = epsg
        stac_extensions.append(PROJ_EXTENSION)
    properties["file:size"] = stat.st_size
    stac_extensions.append(FILE_EXTENSION)

    assets = {
        "data": {
            "href": rel_path,
            "type": media_type,
            "roles": ["data"],
        }
    }
    item_id = f"nas-{hash_path(nas_path)}"
    title = path.name
    description = f"Indexed asset at {rel_path}"
    dt = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
    return (
        item_id,
        collection_id,
        title,
        description,
        "1.0.0",
        stac_extensions,
        dt,
        geom_wkt,
        bbox,
        psycopg2.extras.Json(properties),
        psycopg2.extras.Json(assets),
        psycopg2.extras.Json([]),
        nas_path,
        psycopg2.extras.Json({}),
    )


def hash_path(path: str) -> str:
    import hashlib

    return hashlib.sha1(path.encode("utf-8")).hexdigest()


def main() -> int:
    project_root = Path(__file__).resolve().parents[2]
    load_env(project_root)

    parser = argparse.ArgumentParser(description="Scan NAS assets and index metadata into PostGIS.")
    parser.add_argument("--root", help="NAS root path to scan")
    parser.add_argument("--db-host", default=os.getenv("DB_HOST", "localhost"))
    parser.add_argument("--db-port", default=os.getenv("DB_PORT", "5433"))
    parser.add_argument("--db-name", default=os.getenv("POSTGRES_DB", "spatial_asset_manager"))
    parser.add_argument("--db-user", default=os.getenv("POSTGRES_USER", "sam"))
    parser.add_argument("--db-password", default=os.getenv("POSTGRES_PASSWORD", "sam_password"))
    parser.add_argument("--collection-id", default=os.getenv("COLLECTION_ID", "nas-assets"))
    parser.add_argument("--batch-size", type=int, default=200, help="DB existence check batch size")
    parser.add_argument("--insert-batch-size", type=int, default=100, help="Insert batch size")
    parser.add_argument("--dry-run", action="store_true", help="Scan and report without inserting")
    args = parser.parse_args()

    root = Path(args.root or os.getenv("NAS_DATA_ROOT", "")).expanduser().resolve()
    if not root or not root.exists():
        raise SystemExit("NAS_DATA_ROOT is not set or path does not exist.")
    nas_host_root = os.getenv("NAS_HOST_ROOT", str(root))

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.info("Scanning %s", root)

    conn = psycopg2.connect(
        host=args.db_host,
        port=int(args.db_port),
        dbname=args.db_name,
        user=args.db_user,
        password=args.db_password,
    )

    ensure_collection(
        conn,
        args.collection_id,
        title="NAS Assets",
        description="Assets indexed from NAS storage.",
        nas_root=str(root),
    )

    total_scanned = 0
    total_inserted = 0
    total_skipped = 0

    pending_rows: List[Tuple] = []

    for batch in chunked(iter_asset_paths(root), args.batch_size):
        batch_paths = [str(path) for path in batch]
        existing = fetch_existing_paths(conn, batch_paths)
        for path in batch:
            total_scanned += 1
            if str(path) in existing:
                total_skipped += 1
                continue

            rel_path_raw = os.path.relpath(path, root)
            if rel_path_raw.startswith(".."):
                rel_path_raw = path.name
            rel_path = Path(rel_path_raw).as_posix()
            nas_path = str(Path(nas_host_root) / rel_path)
            try:
                if path.suffix.lower() in {".tif", ".tiff"}:
                    meta = raster_metadata(path)
                else:
                    meta = vector_metadata(path)
                if meta is None:
                    logging.warning("Skipping (missing CRS or bounds): %s", path)
                    continue
                bbox, geom_wkt, epsg = meta
                row = build_item_row(
                    path, rel_path, nas_path, args.collection_id, bbox, geom_wkt, epsg
                )
            except Exception as exc:
                logging.exception("Failed to read metadata for %s: %s", path, exc)
                continue

            if args.dry_run:
                total_inserted += 1
                continue

            pending_rows.append(row)
            if len(pending_rows) >= args.insert_batch_size:
                insert_items(conn, pending_rows)
                total_inserted += len(pending_rows)
                pending_rows.clear()

    if not args.dry_run and pending_rows:
        insert_items(conn, pending_rows)
        total_inserted += len(pending_rows)

    logging.info(
        "Done. scanned=%s inserted=%s skipped=%s",
        total_scanned,
        total_inserted,
        total_skipped,
    )
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
