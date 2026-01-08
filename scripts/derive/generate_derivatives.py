#!/usr/bin/env python3
import argparse
import os
from pathlib import Path
from typing import Iterator, Tuple

import numpy as np
import rasterio
from rasterio.enums import Resampling


def iter_tifs(root: Path, skip_root: Path) -> Iterator[Path]:
    for path in root.rglob("*.tif"):
        if skip_root in path.parents:
            continue
        yield path


def max_size_to_shape(width: int, height: int, max_size: int) -> Tuple[int, int]:
    if width >= height:
        out_width = max_size
        out_height = max(1, int(round(height * max_size / width)))
    else:
        out_height = max_size
        out_width = max(1, int(round(width * max_size / height)))
    return out_width, out_height


def pad_to_square(data: np.ndarray, size: int, fill: int = 0) -> np.ndarray:
    bands, height, width = data.shape
    if height == size and width == size:
        return data
    out = np.full((bands, size, size), fill, dtype=data.dtype)
    y_offset = max(0, (size - height) // 2)
    x_offset = max(0, (size - width) // 2)
    out[:, y_offset : y_offset + height, x_offset : x_offset + width] = data
    return out


def stretch_to_uint8(data: np.ndarray) -> np.ndarray:
    bands, height, width = data.shape
    if bands == 1:
        data = np.repeat(data, 3, axis=0)
        bands = 3
    if bands > 3:
        data = data[:3, :, :]
        bands = 3

    out = np.zeros((bands, height, width), dtype=np.uint8)
    for idx in range(bands):
        band = data[idx].astype("float32")
        if np.isnan(band).all():
            continue
        vmin = np.nanpercentile(band, 2)
        vmax = np.nanpercentile(band, 98)
        if vmax <= vmin:
            vmin = np.nanmin(band)
            vmax = np.nanmax(band)
        if vmax <= vmin:
            vmax = vmin + 1.0
        scaled = (band - vmin) / (vmax - vmin) * 255.0
        out[idx] = np.clip(scaled, 0, 255).astype("uint8")
    return out


def write_jpeg(path: Path, data: np.ndarray) -> None:
    bands, height, width = data.shape
    profile = {
        "driver": "JPEG",
        "height": height,
        "width": width,
        "count": bands,
        "dtype": "uint8",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(data)


def process_asset(
    src_path: Path,
    thumb_path: Path,
    thumb_size: int,
    overwrite: bool,
    thumb_square: bool,
) -> None:
    with rasterio.open(src_path) as src:
        if src.crs is None:
            return
        if overwrite or not thumb_path.exists():
            out_width, out_height = max_size_to_shape(src.width, src.height, thumb_size)
            data = src.read(
                out_shape=(src.count, out_height, out_width), resampling=Resampling.bilinear
            )
            data = stretch_to_uint8(data)
            if thumb_square:
                data = pad_to_square(data, thumb_size, fill=0)
            write_jpeg(thumb_path, data)

        return


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate thumbnails.")
    parser.add_argument("--root", default=os.getenv("NAS_DATA_ROOT"), help="NAS root path")
    parser.add_argument(
        "--output-root",
        default=os.getenv("DERIV_ROOT"),
        help="Output root for thumbnails",
    )
    parser.add_argument("--thumb-size", type=int, default=512)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument(
        "--thumb-square",
        action="store_true",
        help="Pad thumbnails to a fixed square size (default off).",
    )
    args = parser.parse_args()

    if not args.root:
        raise SystemExit("NAS_DATA_ROOT is not set.")

    root = Path(args.root).expanduser().resolve()
    output_root = Path(args.output_root or (root / "result")).expanduser().resolve()
    thumb_root = output_root / "thumb"
    if thumb_root.exists() and thumb_root.is_file():
        thumb_root.unlink()
    thumb_root.mkdir(parents=True, exist_ok=True)
    for path in iter_tifs(root, output_root):
        rel = path.relative_to(root)
        thumb_path = thumb_root / rel.with_suffix(".jpg")
        process_asset(
            path,
            thumb_path,
            args.thumb_size,
            args.overwrite,
            args.thumb_square,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
