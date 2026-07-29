#!/usr/bin/env python3
"""Build static HTML site from data/site.json."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "site.json"
DIST = ROOT / "dist"
SITE_URL = "https://benludp.com"
DEFAULT_DESC = (
    "Ben Nurhaci Lu — cinematographer based in Los Angeles. "
    "Narrative, commercial, and documentary cinematography."
)
DEFAULT_OG = f"{SITE_URL}/assets/work/the-grossness-of-closeness.jpg"


def esc(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def pwd_hash(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


NAV = [
    ("", "Work"),  # home — resolves to / or ../ without index.html
    ("reel.html", "Reel"),
    ("stills.html", "Stills"),
    ("info.html", "Info"),
    ("contact.html", "Contact"),
]


def home_href(prefix: str = "") -> str:
    """Clean homepage URL: / on root pages, ../ from project pages."""
    return f"{prefix}" if prefix else "/"


def header(active: str, brand: str, prefix: str = "") -> str:
    links = []
    home = home_href(prefix)
    for href, label in NAV:
        target = home if href == "" else f"{prefix}{href}"
        cls = ' class="is-active"' if label.lower() == active.lower() else ""
        links.append(f'<a href="{target}"{cls}>{label}</a>')
    return f"""<header class="site-header">
  <nav class="nav">{"".join(links)}</nav>
  <a class="brand" href="{home}">{esc(brand)}</a>
</header>"""


def site_footer(text: str = "呂尚睿. 努爾哈赤") -> str:
    return f"""<footer class="site-footer">
  <div class="footer-text">{esc(text)}</div>
</footer>"""


def layout(
    title: str,
    body: str,
    brand: str,
    active: str,
    prefix: str = "",
    extra_head: str = "",
    footer_text: str | None = "呂尚睿. 努爾哈赤",
    path: str = "/",
    description: str | None = None,
    og_image: str | None = None,
) -> str:
    footer = site_footer(footer_text) if footer_text else ""
    desc = description or DEFAULT_DESC
    canonical = f"{SITE_URL}{path}"
    image = og_image or DEFAULT_OG
    if image.startswith("/"):
        image = f"{SITE_URL}{image}"
    elif not image.startswith("http"):
        image = f"{SITE_URL}/{image.lstrip('./')}"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(desc)}" />
  <meta name="author" content="Ben Nurhaci Lu" />
  <link rel="canonical" href="{esc(canonical)}" />
  <meta property="og:type" content="website" />
  <meta property="og:site_name" content="Ben Nurhaci Lu Cinematographer" />
  <meta property="og:title" content="{esc(title)}" />
  <meta property="og:description" content="{esc(desc)}" />
  <meta property="og:url" content="{esc(canonical)}" />
  <meta property="og:image" content="{esc(image)}" />
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:title" content="{esc(title)}" />
  <meta name="twitter:description" content="{esc(desc)}" />
  <meta name="twitter:image" content="{esc(image)}" />
  <meta name="theme-color" content="#f7f7f7" />
  <link rel="stylesheet" href="{prefix}styles.css" />
  {extra_head}
</head>
<body>
{header(active, brand, prefix)}
<main>
{body}
{footer}
</main>
<script src="{prefix}site.js"></script>
</body>
</html>
"""


def build() -> None:
    site = json.loads(DATA.read_text(encoding="utf-8"))
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)
    shutil.copy2(ROOT / "styles.css", DIST / "styles.css")
    shutil.copy2(ROOT / "site.js", DIST / "site.js")
    # Custom domain for GitHub Pages
    (DIST / "CNAME").write_text("benludp.com\n", encoding="utf-8")

    # Copy assets into dist
    assets_src = ROOT / "assets"
    if assets_src.exists():
        shutil.copytree(assets_src, DIST / "assets")

    brand = site["brand"]
    private_hash = pwd_hash(site.get("private_password", "private"))
    footer_name = site.get("contact_chinese") or site.get("site_footer") or "呂尚睿. 努爾哈赤"

    # WORK
    cards = []
    for p in site["projects"]:
        thumb = p.get("thumb") or (p["images"][0] if p.get("images") else None)
        if not thumb:
            continue
        cards.append(
            f"""<a class="work-card" href="projects/{esc(p['slug'])}.html">
  <img src="{esc(thumb)}" alt="{esc(p['title'])}" loading="lazy" />
  <span class="work-meta"><span class="work-title">{esc(p['title'])}</span><span class="work-year">{p['year']}</span></span>
</a>"""
        )
    work_body = f'<section class="work-grid">\n{"".join(cards)}\n</section>'
    home_jsonld = {
        "@context": "https://schema.org",
        "@type": "Person",
        "name": "Ben Nurhaci Lu",
        "alternateName": "Ben Lu",
        "url": SITE_URL,
        "jobTitle": "Cinematographer",
        "email": site.get("email"),
        "sameAs": [s for s in [site.get("instagram")] if s],
        "worksFor": {"@type": "Organization", "name": "Ben Nurhaci Lu Cinematographer"},
    }
    home_extra = (
        f'<script type="application/ld+json">{json.dumps(home_jsonld, ensure_ascii=False)}</script>'
    )
    (DIST / "index.html").write_text(
        layout(
            f"{site['name']} — Cinematographer",
            work_body,
            brand,
            "Work",
            footer_text=footer_name,
            path="/",
            description=DEFAULT_DESC,
            extra_head=home_extra,
        ),
        encoding="utf-8",
    )

    # REEL
    reel_body = f"""<section class="reel">
  <div class="reel-frame">
    <iframe src="https://player.vimeo.com/video/{esc(site['reel_vimeo_id'])}?badge=0&autopause=0"
      allow="autoplay; fullscreen; picture-in-picture" allowfullscreen></iframe>
  </div>
  <p class="reel-credit">{esc(site['reel_credit'])}</p>
</section>"""
    (DIST / "reel.html").write_text(
        layout(
            f"{site['name']} — Reel",
            reel_body,
            brand,
            "Reel",
            path="/reel.html",
            description="Selected cinematography reel by Ben Nurhaci Lu.",
        ),
        encoding="utf-8",
    )

    # STILLS
    still_imgs = "\n".join(
        f'<img src="{esc(src)}" alt="" loading="lazy" />' for src in site.get("stills", [])
    )
    stills_body = f'<section class="stills-stack">\n{still_imgs}\n</section>'
    (DIST / "stills.html").write_text(
        layout(
            f"{site['name']} — Stills",
            stills_body,
            brand,
            "Stills",
            path="/stills.html",
            description="Still photography and frame grabs by cinematographer Ben Nurhaci Lu.",
        ),
        encoding="utf-8",
    )

    # INFO
    paras = "".join(f"<p>{esc(p)}</p>" for p in site["info_text"].split("\n\n") if p.strip())
    info_img = ""
    info_og = None
    if site.get("info_images"):
        info_og = site["info_images"][0]
        info_img = f'<img class="info-portrait" src="{esc(site["info_images"][0])}" alt="{esc(brand)}" />'
    info_body = f'<section class="info">\n{info_img}\n<div class="info-copy">{paras}</div>\n</section>'
    (DIST / "info.html").write_text(
        layout(
            f"{site['name']} — Info",
            info_body,
            brand,
            "Info",
            path="/info.html",
            description="About cinematographer Ben Nurhaci Lu — based in Los Angeles, by way of Taiwan.",
            og_image=info_og,
        ),
        encoding="utf-8",
    )

    # CONTACT — Adobe: 655px column, 100px icons in two halves, 25px tagline
    contact_body = f"""<section class="contact">
  <h1 class="contact-tagline">{esc(site['contact_tagline'])}</h1>
  <div class="contact-links">
    <a class="icon-link instagram" href="{esc(site['instagram'])}" target="_blank" rel="noopener" aria-label="Instagram">
      <svg viewBox="0 0 30 24" aria-hidden="true">
        <defs>
          <linearGradient id="ig-grad" x1="0%" y1="100%" x2="100%" y2="0%">
            <stop offset="0%" stop-color="#f58529"/>
            <stop offset="50%" stop-color="#dd2a7b"/>
            <stop offset="100%" stop-color="#8134af"/>
          </linearGradient>
        </defs>
        <g fill="url(#ig-grad)">
          <path d="M15,5.4c2.1,0,2.4,0,3.2,0c0.8,0,1.2,0.2,1.5,0.3c0.4,0.1,0.6,0.3,0.9,0.6c0.3,0.3,0.5,0.5,0.6,0.9c0.1,0.3,0.2,0.7,0.3,1.5c0,0.8,0,1.1,0,3.2s0,2.4,0,3.2c0,0.8-0.2,1.2-0.3,1.5c-0.1,0.4-0.3,0.6-0.6,0.9c-0.3,0.3-0.5,0.5-0.9,0.6c-0.3,0.1-0.7,0.2-1.5,0.3c-0.8,0-1.1,0-3.2,0s-2.4,0-3.2,0c-0.8,0-1.2-0.2-1.5-0.3c-0.4-0.1-0.6-0.3-0.9-0.6c-0.3-0.3-0.5-0.5-0.6-0.9c-0.1-0.3-0.2-0.7-0.3-1.5c0-0.8,0-1.1,0-3.2s0-2.4,0-3.2c0-0.8,0.2-1.2,0.3-1.5c0.1-0.4,0.3-0.6,0.6-0.9c0.3-0.3,0.5-0.5,0.9-0.6c0.3-0.1,0.7-0.2,1.5-0.3C12.6,5.4,12.9,5.4,15,5.4 M15,4c-2.2,0-2.4,0-3.3,0c-0.9,0-1.4,0.2-1.9,0.4c-0.5,0.2-1,0.5-1.4,0.9C7.9,5.8,7.6,6.2,7.4,6.8C7.2,7.3,7.1,7.9,7,8.7C7,9.6,7,9.8,7,12s0,2.4,0,3.3c0,0.9,0.2,1.4,0.4,1.9c0.2,0.5,0.5,1,0.9,1.4c0.4,0.4,0.9,0.7,1.4,0.9c0.5,0.2,1.1,0.3,1.9,0.4c0.9,0,1.1,0,3.3,0s2.4,0,3.3,0c0.9,0,1.4-0.2,1.9-0.4c0.5-0.2,1-0.5,1.4-0.9c0.4-0.4,0.7-0.9,0.9-1.4c0.2-0.5,0.3-1.1,0.4-1.9c0-0.9,0-1.1,0-3.3s0-2.4,0-3.3c0-0.9-0.2-1.4-0.4-1.9c-0.2-0.5-0.5-1-0.9-1.4c-0.4-0.4-0.9-0.7-1.4-0.9c-0.5-0.2-1.1-0.3-1.9-0.4C17.4,4,17.2,4,15,4L15,4L15,4z"/>
          <path d="M15,7.9c-2.3,0-4.1,1.8-4.1,4.1s1.8,4.1,4.1,4.1s4.1-1.8,4.1-4.1S17.3,7.9,15,7.9L15,7.9z M15,14.7c-1.5,0-2.7-1.2-2.7-2.7c0-1.5,1.2-2.7,2.7-2.7s2.7,1.2,2.7,2.7C17.7,13.5,16.5,14.7,15,14.7L15,14.7z"/>
          <path d="M20.2,7.7c0,0.5-0.4,1-1,1s-1-0.4-1-1s0.4-1,1-1S20.2,7.2,20.2,7.7L20.2,7.7z"/>
        </g>
      </svg>
    </a>
    <a class="icon-link email" href="mailto:{esc(site['email'])}" aria-label="Email">
      <svg viewBox="0 0 30 24" aria-hidden="true">
        <path fill="#92bbe8" d="M15,13L7.1,7.1c0-0.5,0.4-1,1-1h13.8c0.5,0,1,0.4,1,1L15,13z M15,14.8l7.9-5.9v8.1c0,0.5-0.4,1-1,1H8.1c-0.5,0-1-0.4-1-1V8.8L15,14.8z"/>
      </svg>
    </a>
  </div>
</section>"""
    (DIST / "contact.html").write_text(
        layout(
            f"{site['name']} — Contact",
            contact_body,
            brand,
            "Contact",
            footer_text=footer_name,
            path="/contact.html",
            description="Contact cinematographer Ben Nurhaci Lu.",
        ),
        encoding="utf-8",
    )

    # PROJECT PAGES
    projects_dir = DIST / "projects"
    projects_dir.mkdir(exist_ok=True)

    def project_inner(p: dict, img_prefix: str) -> str:
        heading = f'<h1 class="project-title">{esc(p["title"])}</h1>'
        layout_mode = p.get("layout", "stack")
        aspect = p.get("aspect", "16 / 9")
        gap = p.get("grid_gap", "var(--gap)")

        imgs = "".join(
            f'<img src="{img_prefix}{esc(src)}" alt="" loading="lazy" />'
            for src in p.get("images", [])
        )
        gallery = ""
        if imgs:
            if layout_mode in ("grid", "two-one", "last-full", "fill-last-two"):
                # grid = N equal cols; two-one = 2 on top, 1 full-width below;
                # last-full = N-col with final still full width;
                # fill-last-two = 3-col rows, leftover pair spans full width
                layout_class = "project-grid"
                if layout_mode == "two-one":
                    layout_class += " layout-two-one"
                elif layout_mode == "last-full":
                    layout_class += " layout-last-full"
                elif layout_mode == "fill-last-two":
                    layout_class += " layout-fill-last-two"
                cols = p.get(
                    "columns",
                    3 if layout_mode in ("grid", "last-full", "fill-last-two") else 2,
                )
                gallery = (
                    f'<div class="{layout_class}" style="--project-gap:{esc(gap)};'
                    f'--project-aspect:{esc(aspect)};--project-cols:{int(cols)}">'
                    f"{imgs}</div>"
                )
            else:
                gallery = f'<div class="project-gallery">{imgs}</div>'

        videos = ""
        if p.get("videos"):
            embeds = []
            for v in p["videos"]:
                provider = v.get("provider", "vimeo")
                vtitle = esc(v.get("title", "Video"))
                if provider == "local":
                    src = f"{img_prefix}{esc(v['src'])}"
                    poster_src = (
                        f"{img_prefix}{esc(v['poster'])}" if v.get("poster") else ""
                    )
                    poster_attr = f' poster="{poster_src}"' if poster_src else ""
                    aspect = v.get("aspect")
                    fit = v.get("object_fit", "cover" if aspect == "1 / 1" else "contain")
                    position = v.get("object_position")
                    style_bits = []
                    if aspect:
                        style_bits.append(f"--local-video-aspect:{esc(aspect)}")
                    if fit:
                        style_bits.append(f"--local-video-fit:{esc(fit)}")
                    if position:
                        style_bits.append(f"--local-video-position:{esc(position)}")
                    aspect_style = (
                        f' style="{";".join(style_bits)}"' if style_bits else ""
                    )
                    embeds.append(
                        f"""<div class="project-video project-video-local">
  <div class="local-video-shell"{aspect_style}>
    <video playsinline preload="metadata"{poster_attr} title="{vtitle}">
      <source src="{src}" type="video/mp4" />
    </video>
    <button type="button" class="local-video-play" aria-label="Play {vtitle}">
      <span class="local-video-play-icon" aria-hidden="true"></span>
    </button>
  </div>
  <p class="video-caption">{vtitle}</p>
</div>"""
                    )
                else:
                    vid = esc(v["id"])
                    if provider == "youtube":
                        src = f"https://www.youtube.com/embed/{vid}"
                    else:
                        src = f"https://player.vimeo.com/video/{vid}?badge=0&autopause=0"
                    embeds.append(
                        f"""<div class="project-video">
  <iframe src="{src}"
    allow="autoplay; fullscreen; picture-in-picture" allowfullscreen
    title="{vtitle}"></iframe>
</div>"""
                    )
            videos = f'<div class="project-videos">{"".join(embeds)}</div>'

        awards = ""
        award_lines = p.get("awards") or []
        if award_lines:
            lines = "".join(f"<p>{esc(line)}</p>" for line in award_lines)
            awards = f'<section class="project-awards">{lines}</section>'

        return f"{heading}\n{gallery}\n{videos}\n{awards}"

    for p in site["projects"]:
        inner = project_inner(p, "../")
        if p.get("password"):
            body = f"""<section class="password-gate" data-hash="{private_hash}" data-slug="{esc(p['slug'])}">
  <form class="password-form">
    <label for="pw-{esc(p['slug'])}">Enter password…</label>
    <input id="pw-{esc(p['slug'])}" type="password" name="password" autocomplete="current-password" required />
    <button type="submit">Submit</button>
    <p class="password-error" hidden>Incorrect password</p>
  </form>
  <div class="password-content" hidden>
{inner}
  </div>
</section>"""
        else:
            body = f'<section class="project">\n{inner}\n</section>'

        og = p.get("thumb") or (p["images"][0] if p.get("images") else None)
        proj_desc = f"{p['title']} ({p['year']}) — cinematography by Ben Nurhaci Lu."
        (projects_dir / f"{p['slug']}.html").write_text(
            layout(
                f"{site['name']} — {p['title']}",
                body,
                brand,
                "Work",
                prefix="../",
                footer_text=footer_name,
                path=f"/projects/{p['slug']}.html",
                description=proj_desc,
                og_image=og,
            ),
            encoding="utf-8",
        )

    # SEO: robots.txt + sitemap.xml
    (DIST / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n",
        encoding="utf-8",
    )
    urls = [
        ("/", "1.0"),
        ("/reel.html", "0.8"),
        ("/stills.html", "0.8"),
        ("/info.html", "0.7"),
        ("/contact.html", "0.6"),
    ]
    for p in site["projects"]:
        if p.get("password"):
            continue
        urls.append((f"/projects/{p['slug']}.html", "0.7"))
    url_xml = "\n".join(
        f"""  <url>
    <loc>{SITE_URL}{path}</loc>
    <changefreq>monthly</changefreq>
    <priority>{priority}</priority>
  </url>"""
        for path, priority in urls
    )
    (DIST / "sitemap.xml").write_text(
        f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{url_xml}
</urlset>
""",
        encoding="utf-8",
    )

    print(f"Built {DIST} ({len(site['projects'])} projects)")


if __name__ == "__main__":
    build()
