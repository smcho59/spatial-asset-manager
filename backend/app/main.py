import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

import psycopg2
import psycopg2.extras
from fastapi import Body, FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse


DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("POSTGRES_DB", "spatial_asset_manager")
DB_USER = os.getenv("POSTGRES_USER", "sam")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "sam_password")
STAC_BASE_PATH = os.getenv("STAC_BASE_PATH", "/stac")


app = FastAPI(
    title="Spatial Asset Manager STAC API",
    docs_url="/docs",
    redoc_url=None,
    openapi_url=f"{STAC_BASE_PATH}/openapi.json",
)

CONFORMANCE_CLASSES = [
    "https://api.stacspec.org/v1.0.0/core",
    "https://api.stacspec.org/v1.0.0/collections",
    "https://api.stacspec.org/v1.0.0/item-search",
]

def get_conn():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )


def parse_box(extent: Optional[str]) -> Optional[List[float]]:
    if not extent:
        return None
    match = re.match(r"BOX\\(([-\\d\\.]+) ([-\\d\\.]+),([-\\d\\.]+) ([-\\d\\.]+)\\)", extent)
    if not match:
        return None
    minx, miny, maxx, maxy = map(float, match.groups())
    return [minx, miny, maxx, maxy]


def format_datetime(value: Optional[datetime]) -> Optional[str]:
    if value is None:
        return None
    return value.replace(tzinfo=None).isoformat() + "Z"


def collection_extent(conn, collection_id: str) -> Dict[str, Any]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT ST_Extent(geom) AS bbox,
                   MIN(datetime) AS min_dt,
                   MAX(datetime) AS max_dt
            FROM items
            WHERE collection_id = %s
            """,
            (collection_id,),
        )
        row = cur.fetchone()
    bbox = parse_box(row[0]) if row else None
    min_dt = format_datetime(row[1]) if row else None
    max_dt = format_datetime(row[2]) if row else None
    if not bbox:
        bbox = [-180.0, -90.0, 180.0, 90.0]
    return {
        "spatial": {"bbox": [bbox]},
        "temporal": {"interval": [[min_dt, max_dt]]},
    }


def row_to_collection(conn, row: Dict[str, Any]) -> Dict[str, Any]:
    extent = row.get("extent")
    if not extent:
        extent = collection_extent(conn, row["id"])
    return {
        "type": "Collection",
        "id": row["id"],
        "title": row.get("title"),
        "description": row.get("description") or "",
        "stac_version": row.get("stac_version", "1.0.0"),
        "stac_extensions": row.get("stac_extensions") or [],
        "license": row.get("license") or "proprietary",
        "extent": extent,
        "links": row.get("links") or [],
    }


def row_to_item(row: Dict[str, Any]) -> Dict[str, Any]:
    geom = json.loads(row["geom"]) if row.get("geom") else None
    properties = row.get("properties") or {}
    if not properties.get("datetime") and row.get("datetime"):
        properties["datetime"] = format_datetime(row["datetime"])
    return {
        "type": "Feature",
        "stac_version": row.get("stac_version", "1.0.0"),
        "stac_extensions": row.get("stac_extensions") or [],
        "id": row["id"],
        "collection": row["collection_id"],
        "geometry": geom,
        "bbox": row.get("bbox"),
        "properties": properties,
        "assets": row.get("assets") or {},
        "links": row.get("links") or [],
    }


def build_landing(base: str, api_path: str) -> Dict[str, Any]:
    child_links: List[Dict[str, Any]] = []
    try:
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute("SELECT id FROM collections ORDER BY id")
            for (cid,) in cur.fetchall():
                child_links.append(
                    {
                        "rel": "child",
                        "href": f"{base}{api_path}/collections/{cid}",
                        "type": "application/json",
                    }
                )
    except Exception:
        child_links = []
    return {
        "type": "Catalog",
        "stac_version": "1.0.0",
        "id": "spatial-asset-manager",
        "title": "Spatial Asset Manager",
        "description": "STAC API for NAS COG assets.",
        "conformsTo": CONFORMANCE_CLASSES,
        "links": [
            {
                "rel": "self",
                "href": f"{base}{api_path}",
                "type": "application/json",
            },
            {
                "rel": "root",
                "href": f"{base}{api_path}",
                "type": "application/json",
            },
            {
                "rel": "conformance",
                "href": f"{base}{api_path}/conformance",
                "type": "application/json",
            },
            {
                "rel": "data",
                "href": f"{base}{api_path}/collections",
                "type": "application/json",
            },
            {
                "rel": "search",
                "href": f"{base}{api_path}/search",
                "type": "application/geo+json",
            },
            {
                "rel": "service-desc",
                "href": f"{base}{api_path}/openapi.json",
                "type": "application/vnd.oai.openapi+json;version=3.0",
            },
            {
                "rel": "service-doc",
                "href": f"{base}/docs",
                "type": "text/html",
            },
        ]
        + child_links,
    }


@app.get(STAC_BASE_PATH)
def landing(request: Request) -> Dict[str, Any]:
    base = str(request.base_url).rstrip("/")
    return build_landing(base, STAC_BASE_PATH)


@app.get(f"{STAC_BASE_PATH}/", include_in_schema=False)
def landing_slash(request: Request) -> Dict[str, Any]:
    return landing(request)


@app.get("/", include_in_schema=False)
def landing_root(request: Request) -> Dict[str, Any]:
    base = str(request.base_url).rstrip("/")
    return build_landing(base, "")


@app.get(f"{STAC_BASE_PATH}/conformance")
def conformance() -> Dict[str, Any]:
    return {"conformsTo": CONFORMANCE_CLASSES}


@app.get("/conformance", include_in_schema=False)
def conformance_root() -> Dict[str, Any]:
    return conformance()


@app.get("/openapi.json", include_in_schema=False)
def openapi_root() -> JSONResponse:
    return JSONResponse(app.openapi())


@app.get(f"{STAC_BASE_PATH}/collections")
def list_collections(request: Request) -> Dict[str, Any]:
    with get_conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT id, title, description, stac_version, stac_extensions, links, extent FROM collections")
        rows = cur.fetchall()
        collections = []
        for row in rows:
            collection = row_to_collection(conn, row)
            collections.append(collection)
    base = str(request.base_url).rstrip("/")
    for collection in collections:
        cid = collection["id"]
        collection["links"] = (collection.get("links") or []) + [
            {
                "rel": "self",
                "href": f"{base}{STAC_BASE_PATH}/collections/{cid}",
                "type": "application/json",
            },
            {
                "rel": "items",
                "href": f"{base}{STAC_BASE_PATH}/collections/{cid}/items",
                "type": "application/geo+json",
            },
            {
                "rel": "parent",
                "href": f"{base}{STAC_BASE_PATH}",
                "type": "application/json",
            },
        ]
    return {
        "collections": collections,
        "links": [
            {
                "rel": "self",
                "href": f"{base}{STAC_BASE_PATH}/collections",
                "type": "application/json",
            },
            {
                "rel": "root",
                "href": f"{base}{STAC_BASE_PATH}",
                "type": "application/json",
            },
        ],
    }


@app.get("/collections", include_in_schema=False)
def list_collections_root(request: Request) -> Dict[str, Any]:
    return list_collections(request)


@app.get(f"{STAC_BASE_PATH}/collections/{{collection_id}}")
def get_collection(request: Request, collection_id: str) -> Dict[str, Any]:
    with get_conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            "SELECT id, title, description, stac_version, stac_extensions, links, extent FROM collections WHERE id = %s",
            (collection_id,),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Collection not found")
        collection = row_to_collection(conn, row)
    base = str(request.base_url).rstrip("/")
    collection["links"] = collection.get("links", []) + [
        {"rel": "self", "href": f"{base}{STAC_BASE_PATH}/collections/{collection_id}"},
        {"rel": "items", "href": f"{base}{STAC_BASE_PATH}/collections/{collection_id}/items"},
    ]
    return collection


@app.get("/collections/{collection_id}", include_in_schema=False)
def get_collection_root(request: Request, collection_id: str) -> Dict[str, Any]:
    return get_collection(request, collection_id)


def apply_filters(
    cur,
    where: List[str],
    params: List[Any],
    year: Optional[str],
    region: Optional[str],
    zone: Optional[str],
    bbox: Optional[List[float]],
):
    if year:
        where.append("properties->>'year' = %s")
        params.append(str(year))
    if region:
        where.append("properties->>'region' ILIKE %s")
        params.append(region)
    if zone is not None:
        where.append("properties->>'zone' = %s")
        params.append(zone)
    if bbox:
        where.append("geom && ST_MakeEnvelope(%s, %s, %s, %s, 4326)")
        params.extend(bbox)


def query_items(
    collection_id: Optional[str],
    year: Optional[str],
    region: Optional[str],
    zone: Optional[str],
    bbox: Optional[List[float]],
    limit: int,
) -> List[Dict[str, Any]]:
    where = []
    params: List[Any] = []
    if collection_id:
        where.append("collection_id = %s")
        params.append(collection_id)
    apply_filters(None, where, params, year, region, zone, bbox)
    clause = f"WHERE {' AND '.join(where)}" if where else ""
    sql = f"""
        SELECT id, collection_id, stac_version, datetime,
               ST_AsGeoJSON(geom) AS geom,
               bbox, properties, assets, links
        FROM items
        {clause}
        ORDER BY id
        LIMIT %s
    """
    params.append(limit)
    with get_conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
    return [row_to_item(row) for row in rows]


@app.get(f"{STAC_BASE_PATH}/collections/{{collection_id}}/items")
def list_collection_items(
    request: Request,
    collection_id: str,
    year: Optional[str] = Query(default=None),
    region: Optional[str] = Query(default=None),
    zone: Optional[str] = Query(default=None),
    bbox: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
) -> Dict[str, Any]:
    bbox_vals = [float(x) for x in bbox.split(",")] if bbox else None
    items = query_items(collection_id, year, region, zone, bbox_vals, limit)
    base = str(request.base_url).rstrip("/")
    for item in items:
        item_id = item["id"]
        item_links = item.get("links") or []
        item_links.extend(
            [
                {
                    "rel": "self",
                    "href": f"{base}{STAC_BASE_PATH}/collections/{collection_id}/items/{item_id}",
                    "type": "application/geo+json",
                },
                {
                    "rel": "collection",
                    "href": f"{base}{STAC_BASE_PATH}/collections/{collection_id}",
                    "type": "application/json",
                },
                {
                    "rel": "root",
                    "href": f"{base}{STAC_BASE_PATH}",
                    "type": "application/json",
                },
            ]
        )
        item["links"] = item_links
    return {
        "type": "FeatureCollection",
        "features": items,
        "links": [
            {
                "rel": "self",
                "href": f"{base}{STAC_BASE_PATH}/collections/{collection_id}/items",
                "type": "application/geo+json",
            },
            {
                "rel": "root",
                "href": f"{base}{STAC_BASE_PATH}",
                "type": "application/json",
            },
        ],
    }


@app.get("/collections/{collection_id}/items", include_in_schema=False)
def list_collection_items_root(
    request: Request,
    collection_id: str,
    year: Optional[str] = Query(default=None),
    region: Optional[str] = Query(default=None),
    zone: Optional[str] = Query(default=None),
    bbox: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
) -> Dict[str, Any]:
    return list_collection_items(
        request, collection_id, year=year, region=region, zone=zone, bbox=bbox, limit=limit
    )


def parse_search_body(body: Dict[str, Any]) -> Dict[str, Any]:
    collections = body.get("collections") or []
    bbox = body.get("bbox")
    limit = int(body.get("limit", 100))
    query = body.get("query") or {}
    year = None
    region = None
    zone = None
    if isinstance(query, dict):
        if "year" in query and isinstance(query["year"], dict):
            year = query["year"].get("eq")
        if "region" in query and isinstance(query["region"], dict):
            region = query["region"].get("eq")
        if "zone" in query and isinstance(query["zone"], dict):
            zone = query["zone"].get("eq")
    return {
        "collections": collections,
        "bbox": bbox,
        "limit": limit,
        "year": year,
        "region": region,
        "zone": zone,
    }


@app.post(f"{STAC_BASE_PATH}/search")
def search_items(body: Dict[str, Any] = Body(default=None)) -> Dict[str, Any]:
    body = body or {}
    parsed = parse_search_body(body)
    collection_id = parsed["collections"][0] if parsed["collections"] else None
    items = query_items(
        collection_id,
        parsed["year"],
        parsed["region"],
        parsed["zone"],
        parsed["bbox"],
        parsed["limit"],
    )
    base = None
    if "base_url" in body:
        base = str(body["base_url"]).rstrip("/")
    return {
        "type": "FeatureCollection",
        "features": items,
        "links": [],
    }


@app.post("/search", include_in_schema=False)
def search_items_root(body: Dict[str, Any] = Body(default=None)) -> Dict[str, Any]:
    return search_items(body)


@app.get(f"{STAC_BASE_PATH}/search")
def search_items_get(
    request: Request,
    year: Optional[str] = Query(default=None),
    region: Optional[str] = Query(default=None),
    zone: Optional[str] = Query(default=None),
    bbox: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    collections: Optional[str] = Query(default=None),
) -> Dict[str, Any]:
    bbox_vals = [float(x) for x in bbox.split(",")] if bbox else None
    collection_id = collections.split(",")[0] if collections else None
    items = query_items(collection_id, year, region, zone, bbox_vals, limit)
    base = str(request.base_url).rstrip("/")
    return {
        "type": "FeatureCollection",
        "features": items,
        "links": [
            {
                "rel": "self",
                "href": f"{base}{STAC_BASE_PATH}/search",
                "type": "application/geo+json",
            },
            {
                "rel": "root",
                "href": f"{base}{STAC_BASE_PATH}",
                "type": "application/json",
            },
        ],
    }


@app.get("/search", include_in_schema=False)
def search_items_get_root(
    request: Request,
    year: Optional[str] = Query(default=None),
    region: Optional[str] = Query(default=None),
    zone: Optional[str] = Query(default=None),
    bbox: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    collections: Optional[str] = Query(default=None),
) -> Dict[str, Any]:
    return search_items_get(
        request,
        year=year,
        region=region,
        zone=zone,
        bbox=bbox,
        limit=limit,
        collections=collections,
    )
