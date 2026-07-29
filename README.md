# Ben Nurhaci Lu — Portfolio

Static rebuild of [benludp.com](https://benludp.com) (formerly Adobe Portfolio).

## Local preview

```bash
python3 scripts/scrape.py   # pull images from live Adobe site (run before canceling Adobe)
python3 scripts/build.py
python3 scripts/serve.py    # http://127.0.0.1:8765 — supports video seeking (Range requests)
```

Do not use `python3 -m http.server` for local preview — it ignores byte ranges, so scrubbing local MP4s will not work.

## Adding / editing films

See **[EDITING.md](EDITING.md)**. Short version:

```bash
python3 scripts/add_project.py \
  --title "Night Drive" \
  --year 2026 \
  --images ~/Desktop/night-drive-stills/ \
  --vimeo 123456789 \
  --award "Dir. Jane Doe"
```

Or ask Cursor to add the project for you.

## Free hosting (GitHub Pages)

Site deploys from `dist/` via `.github/workflows/pages.yml`.

**Custom domain DNS (Hostinger):** delete old Adobe/host records for `@` and `www`, then add:

| Type | Name | Value |
|------|------|-------|
| A | `@` | `185.199.108.153` |
| A | `@` | `185.199.109.153` |
| A | `@` | `185.199.110.153` |
| A | `@` | `185.199.111.153` |
| CNAME | `www` | `observer01okay.github.io` |

In the repo: Settings → Pages → Custom domain = `benludp.com` → enable **Enforce HTTPS** after DNS is green.

## Private projects

Default password is `private` (change `private_password` in `data/site.json`, then rebuild).
Client-side password gates are privacy-only, not strong security.
