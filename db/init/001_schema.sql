-- Spatial Asset Manager: PostGIS schema for STAC Collections/Items.
-- This script is designed to run via docker-entrypoint-initdb.d on first boot.

CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS collections (
  id TEXT PRIMARY KEY,
  title TEXT,
  description TEXT,
  stac_version TEXT NOT NULL DEFAULT '1.0.0',
  stac_extensions TEXT[] NOT NULL DEFAULT '{}'::TEXT[],
  license TEXT,
  keywords TEXT[] NOT NULL DEFAULT '{}'::TEXT[],
  providers JSONB,
  extent JSONB, -- STAC extent object (spatial/temporal)
  extent_geom GEOMETRY(POLYGON, 4326), -- derived from extent.spatial.bbox
  links JSONB,
  extra_fields JSONB,
  nas_root TEXT, -- optional NAS root path for the collection
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS items (
  id TEXT PRIMARY KEY,
  collection_id TEXT NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
  title TEXT,
  description TEXT,
  stac_version TEXT NOT NULL DEFAULT '1.0.0',
  stac_extensions TEXT[] NOT NULL DEFAULT '{}'::TEXT[],
  datetime TIMESTAMPTZ, -- STAC Item datetime (instant)
  start_datetime TIMESTAMPTZ, -- STAC Item start_datetime (range)
  end_datetime TIMESTAMPTZ, -- STAC Item end_datetime (range)
  geom GEOMETRY(GEOMETRY, 4326) NOT NULL, -- STAC Item geometry
  bbox DOUBLE PRECISION[] CHECK (
    bbox IS NULL OR array_length(bbox, 1) IN (4, 6)
  ),
  properties JSONB NOT NULL DEFAULT '{}'::JSONB,
  assets JSONB NOT NULL DEFAULT '{}'::JSONB, -- STAC assets with hrefs
  links JSONB,
  nas_path TEXT, -- primary NAS file path (optional convenience field)
  extra_fields JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (
    datetime IS NOT NULL
    OR (start_datetime IS NOT NULL AND end_datetime IS NOT NULL)
  )
);

-- Indexes for common STAC query patterns.
CREATE INDEX IF NOT EXISTS items_geom_gix ON items USING GIST (geom);
CREATE INDEX IF NOT EXISTS items_datetime_idx ON items (datetime);
CREATE INDEX IF NOT EXISTS items_collection_idx ON items (collection_id);
CREATE INDEX IF NOT EXISTS items_properties_gin ON items USING GIN (properties);
CREATE INDEX IF NOT EXISTS items_assets_gin ON items USING GIN (assets);
CREATE INDEX IF NOT EXISTS items_nas_path_idx ON items (nas_path) WHERE nas_path IS NOT NULL;
CREATE INDEX IF NOT EXISTS items_nas_path_pattern_idx
  ON items (nas_path text_pattern_ops) WHERE nas_path IS NOT NULL;
CREATE INDEX IF NOT EXISTS collections_extent_gix ON collections USING GIST (extent_geom);
