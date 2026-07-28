#!/usr/bin/env python3
"""Scrape benludp.com (Adobe Portfolio) into local JSON + image assets."""

from __future__ import annotations

import json
import re
import shutil
import ssl
import time
import urllib.request
from html import unescape
from pathlib import Path

SSL_CTX = ssl._create_unverified_context()

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
ASSETS = ROOT / "assets"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
BASE = "https://benludp.com"

PROJECTS = [
    ("the-grossness-of-closeness", "Grossness of Closeness", 2025),
    ("bisonte", "Bisonte", 2025),
    ("kissinger-takes-paris", "Kissinger Takes Paris", 2024),
    ("wabi-sabi", "Wabi Sabi", 2024),
    ("sparkle-pets", "Sparkle Pets", 2024),
    ("american-body", "American Body", 2023),
    ("enlightenment", "Enlightenment", 2022),
    ("ping-tung-commercial-fest", "Ping Tung Commercial fest", 2022),
    ("child-in-winter", "Child in Winter", 2021),
    ("as-usaul", "As Usual", 2021),
    ("90", "90 後的修羅之路", 2021),
    ("copy-of-bisonte", "Partner", 2025),
    ("safe-and-sound", "Safe and Sound", 2020),
    ("blowing-in-the-wind", "Blowing in the Wind", 2019),
    ("cactus", "Cactus", 2018),
    ("cave", "Cave", 2018),
    ("a-kind-after-sale-service", "A Kind After Sale Service", 2019),
    ("reason", "Reason", 2017),
    ("scattered-over-night", "Scattered Over Night", 2018),
    ("black-friday", "Black Friday", 2017),
]

SKIP_SLUGS = {
    "work",
    "reel",
    "info",
    "contact",
    "stills-for-website",
    "dist/css/main.css",
}

INFO_TEXT = """Ben Nurhaci Lu is a cinematographer whose work carries the quiet gravity of someone who listens closely — to light, to spaces, to the human heart.

Based in LA, by way of Taiwan, Ben’s approach to the image is less about imposing a style, and more about revealing the soul of a story. His eye is endlessly versatile — shifting from the tender to the raw, the grand to the intimate — yet his work always holds a throughline of honesty and restraint. Every frame feels lived-in, textured, alive.

There is no showboating here, no need to announce the hand behind the camera. Instead, Ben folds seamlessly into the fabric of the world he helps create, guiding the audience with an invisible hand. Light, shadow, color, composition — all are treated as instruments in service of something larger: emotion, connection, memory.

His greatest gift lies not just in his technical command — which is considerable — but in his ability to disappear into a story while sharpening its emotional impact. Directors trust him not only for his craft, but for his intuition; for knowing when an image should roar, and when it should whisper.

Ben Nurhaci Lu’s cinematography is not designed to dazzle at first glance — it lingers, unfolding quietly, leaving an imprint you carry long after the screen fades to black."""


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60, context=SSL_CTX) as resp:
        return resp.read().decode("utf-8", errors="replace")


def fetch_bytes(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120, context=SSL_CTX) as resp:
        return resp.read()


def asset_id(url: str) -> str | None:
    m = re.search(r"/([0-9a-f\-]{36})_(?:rwc_|rw_)", url)
    return m.group(1) if m else None


def best_cdn_urls(html: str) -> list[str]:
    """Extract ordered unique CDN image URLs (prefer _rw_1920 / large crops)."""
    ordered: list[str] = []
    seen: set[str] = set()

    # Prefer large explicit img src first (Adobe embeds gallery imgs in <script> templates)
    patterns = [
        r'src="(https://cdn\.myportfolio\.com/[^"]+_rw_1920\.[^"]+)"',
        r'src="(https://cdn\.myportfolio\.com/[^"]+_rw_1200\.[^"]+)"',
        r'src="(https://cdn\.myportfolio\.com/[^"]+_rwc_[^"]+x(?:1280|1366|1419|1449|1451|1464|1522|1703|1783|1916|1920)\.[^"]+)"',
        r'src="(https://cdn\.myportfolio\.com/[^"]+\.(?:jpg|jpeg|png|JPG|JPEG|PNG)\?h=[^"]+)"',
    ]
    for pat in patterns:
        for m in re.finditer(pat, html):
            url = unescape(m.group(1))
            aid = asset_id(url)
            if not aid or aid in seen:
                continue
            if re.search(r"_rw_(?:32|600)\.|x32\.", url):
                continue
            seen.add(aid)
            ordered.append(url)
    return ordered


def ext_from_url(url: str) -> str:
    m = re.search(r"\.(jpe?g|png|JPG|JPEG|PNG)\?", url)
    if not m:
        return ".jpg"
    e = m.group(1).lower()
    return ".jpg" if e in ("jpg", "jpeg") else ".png"


def download(url: str, dest: Path, force: bool = False) -> str | None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not force and dest.exists() and dest.stat().st_size > 1000:
        return str(dest.relative_to(ROOT))
    try:
        data = fetch_bytes(url)
        dest.write_bytes(data)
        print(f"  saved {dest.relative_to(ROOT)} ({len(data) // 1024}KB)")
        return str(dest.relative_to(ROOT))
    except Exception as e:
        print(f"  FAIL {url[:90]}… → {e}")
        return None


def parse_work_thumbs(html: str) -> dict[str, str]:
    """Map project slug → thumbnail CDN url from homepage grid."""
    out: dict[str, str] = {}
    for m in re.finditer(
        r'<a[^>]+href="/(?P<slug>[^"]+)"[^>]*>[\s\S]*?<img[^>]+src="(?P<src>https://cdn\.myportfolio\.com[^"]+)"',
        html,
        flags=re.I,
    ):
        slug = m.group("slug").strip("/")
        if slug in SKIP_SLUGS:
            continue
        out[slug] = unescape(m.group("src"))

    # Upgrade to a mid/large crop when available
    for slug, src in list(out.items()):
        aid = asset_id(src)
        if not aid:
            continue
        candidates = re.findall(
            rf"https://cdn\.myportfolio\.com/[^\"'\s]+/{aid}_rwc_[^\"'\s,]+\.(?:jpg|jpeg|png|JPG|JPEG|PNG)\?h=[0-9a-f]+",
            html,
        )
        best, best_w = src, 0
        for c in candidates:
            wm = re.search(r"x(\d+)\.(?:jpg|jpeg|png|JPG|JPEG|PNG)\?", c)
            w = int(wm.group(1)) if wm else 0
            if 640 <= w <= 2000 and w >= best_w:
                best, best_w = c, w
        out[slug] = best
    return out


def is_password_page(html: str) -> bool:
    return "Password Protected" in html or "Enter password" in html


def scrape() -> None:
    DATA.mkdir(parents=True, exist_ok=True)

    # Fresh image dirs so galleries aren't stuck with a single old file
    for sub in ("work", "stills", "info", "projects"):
        p = ASSETS / sub
        if p.exists():
            shutil.rmtree(p)
        p.mkdir(parents=True, exist_ok=True)

    print("Fetching homepage…")
    home = fetch(f"{BASE}/")
    (DATA / "home.html").write_text(home, encoding="utf-8")
    thumbs = parse_work_thumbs(home)
    print(f"  thumbs found: {len(thumbs)}")

    projects = []
    for slug, title, year in PROJECTS:
        print(f"Project /{slug} …")
        local_thumb = None
        if slug in thumbs:
            local_thumb = download(
                thumbs[slug],
                ASSETS / "work" / f"{slug}{ext_from_url(thumbs[slug])}",
                force=True,
            )
        try:
            page = fetch(f"{BASE}/{slug}")
            time.sleep(0.25)
        except Exception as e:
            print(f"  page fetch failed: {e}")
            projects.append(
                {
                    "slug": slug,
                    "title": title,
                    "year": year,
                    "thumb": local_thumb,
                    "password": True,
                    "images": [],
                }
            )
            continue

        protected = is_password_page(page)
        images: list[str] = []
        if not protected:
            (DATA / f"project-{slug}.html").write_text(page, encoding="utf-8")
            urls = best_cdn_urls(page)
            print(f"  gallery urls: {len(urls)}")
            for i, url in enumerate(urls):
                path = download(
                    url,
                    ASSETS / "projects" / slug / f"{i:02d}{ext_from_url(url)}",
                    force=True,
                )
                if path:
                    images.append(path)
                time.sleep(0.08)
            # If no gallery images, at least use thumb as cover
            if not images and local_thumb:
                images = [local_thumb]
        else:
            print("  password protected")

        projects.append(
            {
                "slug": slug,
                "title": title,
                "year": year,
                "thumb": local_thumb,
                "password": protected,
                "images": images,
            }
        )

    print("Fetching stills…")
    stills_html = fetch(f"{BASE}/stills-for-website")
    (DATA / "stills.html").write_text(stills_html, encoding="utf-8")
    still_urls = best_cdn_urls(stills_html)
    print(f"  still urls: {len(still_urls)}")
    still_paths = []
    for i, url in enumerate(still_urls):
        path = download(url, ASSETS / "stills" / f"{i:02d}{ext_from_url(url)}", force=True)
        if path:
            still_paths.append(path)
        time.sleep(0.08)

    print("Fetching info…")
    info_html = fetch(f"{BASE}/info")
    (DATA / "info.html").write_text(info_html, encoding="utf-8")
    info_images = []
    for i, url in enumerate(best_cdn_urls(info_html)):
        path = download(url, ASSETS / "info" / f"{i:02d}{ext_from_url(url)}", force=True)
        if path:
            info_images.append(path)

    print("Fetching reel…")
    reel_html = fetch(f"{BASE}/reel")
    (DATA / "reel.html").write_text(reel_html, encoding="utf-8")
    vimeo = re.search(r"vimeo\.com/(?:video/)?(\d+)", reel_html)
    vimeo_id = vimeo.group(1) if vimeo else "1096158361"

    site = {
        "brand": "Ben Nurhaci Lu Cinematographer",
        "name": "Ben Lu",
        "email": "benludp@gmail.com",
        "instagram": "https://www.instagram.com/benludp/",
        "contact_tagline": "What's the Hesitant?",
        "contact_chinese": "呂尚睿.努爾哈赤",
        "reel_vimeo_id": vimeo_id,
        "reel_credit": "Editor/sound designer: Shannon O'Shea",
        "info_text": INFO_TEXT,
        "info_images": info_images,
        "stills": still_paths,
        "projects": projects,
        "private_password": "private",
    }
    (DATA / "site.json").write_text(json.dumps(site, indent=2, ensure_ascii=False), encoding="utf-8")
    print(
        f"\nDone. {len(projects)} projects, {len(still_paths)} stills, "
        f"{sum(1 for p in projects if p['password'])} private → data/site.json"
    )


if __name__ == "__main__":
    scrape()
