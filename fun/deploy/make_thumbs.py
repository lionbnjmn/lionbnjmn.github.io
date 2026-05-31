#!/usr/bin/env python3
"""Generate spin-animation thumbnails for items in lottery_index.json.

Reads /lottery/lottery_index.json, extracts a thumbnail for each item with
type "image" or "video", and writes it to /lottery/lottery_thumbs/<id>.jpg.

Idempotent: skips thumbs that already exist (use --force to regenerate).
Requires ffmpeg on PATH.

Usage:
  python3 lottery/deploy/make_thumbs.py            # generate missing thumbs
  python3 lottery/deploy/make_thumbs.py --force    # regenerate all
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
LOTTERY_DIR = REPO_ROOT / "lottery"
INDEX_PATH = LOTTERY_DIR / "lottery_index.json"
THUMBS_DIR = LOTTERY_DIR / "lottery_thumbs"
THUMB_WIDTH = 320  # px; height auto, preserves aspect ratio
JPEG_QUALITY = 5  # ffmpeg -q:v scale (2 = best, 31 = worst); 5 ≈ ~80% quality


def find_ffmpeg() -> str | None:
    """Return path to an ffmpeg binary, trying several sources."""
    # 1. system PATH
    found = shutil.which("ffmpeg")
    if found:
        return found
    # 2. imageio-ffmpeg pip package (bundles a binary)
    try:
        import imageio_ffmpeg  # type: ignore
        return imageio_ffmpeg.get_ffmpeg_exe()
    except (ImportError, Exception):
        pass
    # 3. static-ffmpeg pip package
    try:
        import static_ffmpeg  # type: ignore
        static_ffmpeg.add_paths()
        return shutil.which("ffmpeg")
    except (ImportError, Exception):
        pass
    return None


FFMPEG: str = ""  # set in main()


def run(cmd: list[str]) -> None:
    """Run a command. Raises RuntimeError on nonzero exit."""
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"command failed: {' '.join(cmd)}\n{result.stderr}"
        )


def make_video_thumb(src: Path, dst: Path) -> None:
    run([
        FFMPEG, "-y",
        "-ss", "0.5",
        "-i", str(src),
        "-frames:v", "1",
        "-vf", f"scale={THUMB_WIDTH}:-2",
        "-q:v", str(JPEG_QUALITY),
        str(dst),
    ])


def make_image_thumb(src: Path, dst: Path) -> None:
    # downsize but never upsize tiny images
    run([
        FFMPEG, "-y",
        "-i", str(src),
        "-vf", f"scale='min({THUMB_WIDTH},iw)':-2",
        "-q:v", str(JPEG_QUALITY),
        str(dst),
    ])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force", action="store_true",
        help="regenerate thumbs that already exist",
    )
    args = parser.parse_args()

    global FFMPEG
    ffmpeg_path = find_ffmpeg()
    if not ffmpeg_path:
        sys.stderr.write("error: ffmpeg not found\n")
        sys.stderr.write("install one of:\n")
        sys.stderr.write("  brew install ffmpeg\n")
        sys.stderr.write("  pip install imageio-ffmpeg\n")
        sys.stderr.write("  pip install static-ffmpeg\n")
        return 1
    FFMPEG = ffmpeg_path
    print(f"using ffmpeg: {FFMPEG}")

    if not INDEX_PATH.exists():
        sys.stderr.write(f"error: {INDEX_PATH} not found\n")
        return 1

    THUMBS_DIR.mkdir(exist_ok=True)

    with INDEX_PATH.open() as f:
        data = json.load(f)

    generated = 0
    skipped = 0
    missing = 0
    failed = 0

    for item in data.get("items", []):
        item_id = item.get("id")
        item_type = item.get("type")
        item_src = item.get("src")

        if item_type not in ("image", "video"):
            continue
        if item_id is None or item_src is None:
            sys.stderr.write(f"warn: item missing id or src: {item!r}\n")
            continue

        src_path = LOTTERY_DIR / item_src
        if not src_path.exists():
            sys.stderr.write(f"warn: source missing: {src_path}\n")
            missing += 1
            continue

        dst_path = THUMBS_DIR / f"{item_id}.jpg"
        if dst_path.exists() and not args.force:
            skipped += 1
            continue

        try:
            if item_type == "video":
                make_video_thumb(src_path, dst_path)
            else:
                make_image_thumb(src_path, dst_path)
            generated += 1
            print(f"  ok  id={item_id}  {item_src} -> {dst_path.name}")
        except RuntimeError as e:
            failed += 1
            sys.stderr.write(f"  FAIL id={item_id}  {item_src}\n{e}\n")

    print(f"\ngenerated: {generated}, skipped: {skipped}, missing source: {missing}, failed: {failed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
