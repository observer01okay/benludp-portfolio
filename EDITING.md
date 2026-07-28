# Editing your portfolio

This site is **static**. Content lives in files; you rebuild HTML when something changes.

```
data/site.json          ← titles, years, awards, video IDs, layout
assets/work/            ← Work-page thumbnails
assets/projects/<slug>/ ← stills for each film
assets/videos/          ← local MP4s (optional)
scripts/build.py        ← turns the above into dist/
```

You do **not** need a website builder. Two good ways to add work:

1. **Ask Cursor** — “Add a project called Night Drive, stills in this folder, Vimeo 123, Dir. Jane Doe”
2. **One command** — `scripts/add_project.py` (below)

---

## Add a new film (typical)

### 1. Gather files on your laptop

Put stills in a folder, e.g. `~/Desktop/night-drive-stills/`  
Optional: a promo `.mp4`, or a Vimeo / YouTube id.

### 2. Run the helper

```bash
cd /Users/ben/Projects/benludp-portfolio

python3 scripts/add_project.py \
  --title "Night Drive" \
  --year 2026 \
  --images ~/Desktop/night-drive-stills/ \
  --vimeo 123456789 \
  --award "Dir. Jane Doe" \
  --award "Sundance Film Festival — 2026"
```

What that does:

- Creates `assets/projects/night-drive/00.jpg`, `01.jpg`, …
- Copies the first still to `assets/work/night-drive.jpg` (Work grid thumb)
- Appends a project block at the **top** of `data/site.json`
- Detects still aspect ratio and uses a 3-column grid when you have 3+ images
- Runs `build.py` so `dist/` is ready

### 3. Preview

```bash
python3 scripts/serve.py
```

Open http://127.0.0.1:8765 — Work should show **Night Drive** first; click through to check stills, video, credits.

### 4. Deploy

Push / sync `dist/` (or the whole repo) to Cloudflare Pages / Vercel / GitHub Pages the same way you always deploy.

---

## Other common cases

**Password-protected (like Grossness of Closeness)**

```bash
python3 scripts/add_project.py \
  --title "Client Cut" \
  --year 2026 \
  --images ~/Desktop/client-stills/ \
  --password
```

Site-wide password is `private_password` in `data/site.json` (currently `goc2025`).

**Local video file instead of Vimeo**

```bash
python3 scripts/add_project.py \
  --title "Night Drive" \
  --year 2026 \
  --images ~/Desktop/stills/ \
  --video ~/Desktop/night-drive-promo.mp4
```

Prefer a web-ready H.264 `.mp4` with faststart (same as Wabi Sabi). For a `.mov`, convert first or ask Cursor to encode it.

**YouTube**

```bash
python3 scripts/add_project.py \
  --title "Night Drive" \
  --year 2026 \
  --images ~/Desktop/stills/ \
  --youtube dQw4w9WgXcQ
```

**Put it at the bottom of Work instead of the top**

```bash
python3 scripts/add_project.py ... --position bottom
```

---

## Edit an existing film

Open `data/site.json`, find the project by `"slug"`, change what you need:

| Want to change | Edit |
|---|---|
| Title / year | `"title"`, `"year"` |
| Credits / awards | `"awards": ["…", "…"]` |
| Add/remove stills | files in `assets/projects/<slug>/` + the `"images"` list |
| Vimeo / YouTube | `"videos"` entries with `"provider"` + `"id"` |
| Password on/off | `"password": true/false` |
| Grid gap / aspect | `"grid_gap"`, `"aspect"` (only if layout is `"grid"`) |

Then:

```bash
python3 scripts/build.py
python3 scripts/serve.py
```

Or tell Cursor: “On Night Drive, add this award line and swap still 03.”

---

## Telling Cursor about layout (best habits)

You don’t need a builder UI. The most humane way to describe a new film page:

1. **Drop a screenshot** of the reference (Adobe, a mock, or another site).
2. **Name the pattern in one line**, e.g.:
   - `3-col` — three equal stills per row (most projects)
   - `two-one` — two smaller on top, one full-width below (Kissinger)
   - `last-full` — 3-col grid, last still full-width (American Body)
   - `fill-last-two` — 3-col rows, last pair spans full width (Child in Winter)
   - `stack` — one still per row, large
3. **Add the extras** in the same message: stills folder, Vimeo/YouTube id, awards lines, password yes/no.

Example message that works great:

> New film “Night Drive”, 2026. Stills in ~/Desktop/night-drive/.  
> Layout like Kissinger (two-one). Vimeo 123456789.  
> Awards: Dir. Jane Doe / Sundance 2026.  
> [screenshot attached]

That’s enough — no need to invent pixel numbers unless something looks wrong after.

Supported `layout` values in `site.json` today:

| `layout` | Meaning |
|---|---|
| `"grid"` | Equal columns (default 3) |
| `"two-one"` | 2 on top, 1 full width under |
| `"last-full"` | Equal columns, last still spans full width |
| `"fill-last-two"` | 3-col rows; last row of 2 spans full width |
| `"stack"` | Vertical stack of large stills |

---

## What you should *not* do

- Don’t hand-edit files inside `dist/` — they get overwritten on every build.
- Don’t build a custom CMS unless you start updating weekly and hate JSON; this portfolio doesn’t need it.
- Don’t cancel Adobe until you’ve deployed this site and clicked through every project once.

---

## Cheat sheet

```bash
# add film
python3 scripts/add_project.py --title "…" --year 2026 --images ~/path/to/stills/

# rebuild + preview
python3 scripts/build.py && python3 scripts/serve.py
```
