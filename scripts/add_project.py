#!/usr/bin/env python3
"""Add a new film/project to the portfolio.

Examples:
  # Stills only
  python3 scripts/add_project.py \\
    --title "Night Drive" --year 2026 \\
    --images ~/Desktop/night-drive-stills/

  # With Vimeo + credits
  python3 scripts/add_project.py \\
    --title "Night Drive" --year 2026 \\
    --images ~/Desktop/night-drive-stills/ \\
    --vimeo 123456789 \\
    --award "Dir. Jane Doe" \\
    --award "Sundance Film Festival — 2026"

  # Password-protected
  python3 scripts/add_project.py \\
    --title "Client Reel" --year 2026 \\
    --images ~/Desktop/client/ \\
    --password

  # Local MP4 promo
  python3 scripts/add_project.py \\
    --title "Night Drive" --year 2026 \\
    --images ~/Desktop/stills/ \\
    --video ~/Desktop/night-drive-promo.mp4
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from collections import Counter
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "site.json"
WORK = ROOT / "assets" / "work"
PROJECTS = ROOT / "assets" / "projects"
VIDEOS = ROOT / "assets" / "videos"

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".webm"}


def slugify(title: str) -> str:
    s = title.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-") or "project"


def ar_to_css(ar: float) -> str:
    snaps = [
        (16 / 9, "16 / 9"),
        (2.0, "2 / 1"),
        (2.2, "2.2 / 1"),
        (2.35, "2.35 / 1"),
        (2.39, "2.39 / 1"),
        (2.4, "2.4 / 1"),
        (8 / 3, "8 / 3"),
        (2.43, "2.43 / 1"),
    ]
    best = min(snaps, key=lambda t: abs(ar - t[0]))
    if abs(ar - best[0]) <= 0.025:
        return best[1]
    return f"{ar:.3f} / 1"


def collect_images(src: Path) -> list[Path]:
    if src.is_file():
        if src.suffix.lower() not in IMAGE_EXTS:
            raise SystemExit(f"Not an image: {src}")
        return [src]
    if not src.is_dir():
        raise SystemExit(f"Images path not found: {src}")
    files = sorted(
        p for p in src.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTS
    )
    if not files:
        raise SystemExit(f"No images found in {src}")
    return files


def mode_aspect(paths: list[Path]) -> str:
    ratios = []
    for p in paths:
        w, h = Image.open(p).size
        if h:
            ratios.append(round(w / h, 3))
    if not ratios:
        return "16 / 9"
    mode = Counter(ratios).most_common(1)[0][0]
    return ar_to_css(mode)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--title", required=True, help='Project title, e.g. "Night Drive"')
    ap.add_argument("--year", type=int, required=True, help="Year, e.g. 2026")
    ap.add_argument("--images", required=True, type=Path, help="Folder (or single file) of stills")
    ap.add_argument("--slug", help="URL slug (default: from title)")
    ap.add_argument("--vimeo", action="append", default=[], help="Vimeo video id (repeatable)")
    ap.add_argument("--youtube", action="append", default=[], help="YouTube video id (repeatable)")
    ap.add_argument("--video", type=Path, help="Local promo video (.mp4/.mov) to copy into assets/videos")
    ap.add_argument("--award", action="append", default=[], help="Credit/award line (repeatable)")
    ap.add_argument("--password", action="store_true", help="Require site private_password to view")
    ap.add_argument("--position", choices=("top", "bottom"), default="top", help="Where to insert on Work page")
    ap.add_argument("--gap", default="8px", help='Grid gap, e.g. "8px" or "10px"')
    ap.add_argument("--no-build", action="store_true", help="Only update JSON/assets; skip build.py")
    args = ap.parse_args()

    site = json.loads(DATA.read_text(encoding="utf-8"))
    slug = args.slug or slugify(args.title)
    if any(p["slug"] == slug for p in site["projects"]):
        raise SystemExit(f"Slug already exists: {slug}")

    src_images = collect_images(args.images.resolve())
    dest_dir = PROJECTS / slug
    dest_dir.mkdir(parents=True, exist_ok=False)

    copied_images: list[str] = []
    for i, src in enumerate(src_images):
        ext = src.suffix.lower().replace(".jpeg", ".jpg")
        dest = dest_dir / f"{i:02d}{ext}"
        shutil.copy2(src, dest)
        copied_images.append(f"assets/projects/{slug}/{dest.name}")

    # Work thumb = first still
    WORK.mkdir(parents=True, exist_ok=True)
    thumb_ext = Path(copied_images[0]).suffix
    thumb_name = f"{slug}{thumb_ext}"
    shutil.copy2(ROOT / copied_images[0], WORK / thumb_name)
    thumb = f"assets/work/{thumb_name}"

    videos: list[dict] = []
    for vid in args.vimeo:
        videos.append({"provider": "vimeo", "id": vid, "title": args.title})
    for vid in args.youtube:
        videos.append({"provider": "youtube", "id": vid, "title": args.title})

    if args.video:
        vsrc = args.video.resolve()
        if not vsrc.is_file() or vsrc.suffix.lower() not in VIDEO_EXTS:
            raise SystemExit(f"Bad --video path: {vsrc}")
        VIDEOS.mkdir(parents=True, exist_ok=True)
        vdest = VIDEOS / f"{slug}-promo{vsrc.suffix.lower()}"
        # Remux/copy; leave encode to user for quality control
        shutil.copy2(vsrc, vdest)
        videos.append(
            {
                "provider": "local",
                "src": f"assets/videos/{vdest.name}",
                "title": f"{args.title} Promo",
                "poster": thumb,
            }
        )

    aspect = mode_aspect([ROOT / p for p in copied_images])
    layout = "grid" if len(copied_images) >= 3 else "stack"

    project = {
        "slug": slug,
        "title": args.title,
        "year": args.year,
        "thumb": thumb,
        "password": bool(args.password),
        "images": copied_images,
        "layout": layout,
        "videos": videos,
        "awards_footer": "呂尚睿. 努爾哈赤",
        "video_status": "ok" if videos else "none",
        "awards": list(args.award),
    }
    if layout == "grid":
        project["aspect"] = aspect
        project["grid_gap"] = args.gap
        project["columns"] = 3

    if args.position == "top":
        site["projects"].insert(0, project)
    else:
        site["projects"].append(project)

    DATA.write_text(json.dumps(site, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Added project “{args.title}”")
    print(f"  slug:    {slug}")
    print(f"  stills:  {len(copied_images)} → assets/projects/{slug}/")
    print(f"  thumb:   {thumb}")
    print(f"  layout:  {layout}" + (f"  aspect={aspect}  gap={args.gap}" if layout == "grid" else ""))
    print(f"  videos:  {len(videos)}")
    print(f"  awards:  {args.award or '(none)'}")
    print(f"  password:{' yes' if args.password else ' no'}")

    if not args.no_build:
        import subprocess

        subprocess.check_call(["python3", str(ROOT / "scripts" / "build.py")], cwd=ROOT)
        print("Built dist/. Preview with:  python3 scripts/serve.py")


if __name__ == "__main__":
    main()
