# CLAUDE.md — FujiRecipeVault

Guidance for Claude (and other agents) when working on this project.

## What this is
**FujiRecipeVault** is a small, **100 % local** web app to store and manage film-simulation
recipes (JPEG settings) for mirrorless cameras such as the X-T3. It runs a tiny local
HTTP server (Python standard library only — **no third-party packages**) and a single-file
web UI. No cloud, no login, no internet needed.

> **Branding/legal — no affiliation with Fujifilm.** FujiRecipeVault is an independent, unofficial
> project, **not affiliated with, authorized, sponsored, or endorsed by FUJIFILM Corporation**. Do
> **not** use the FUJIFILM wordmark/logo or imply endorsement. Camera model names (X-T3, X-T4, …)
> are trademarks of their owners, used only as factual compatibility references (nominative use).
> The logo is a **line-art Mount Fuji** (the mountain, white) on a black rounded tile —
> user-provided, stored as `ICON.png`; it is **not** a Fujifilm brand mark. Because "Fuji" is in
> the name, keep the disclaimer prominent (README + user guide carry a clean non-affiliation note).

## Working conventions (important)
- **User is not a professional developer, communicates in German.** Keep code simple and
  **well-commented in German** (code comments stay German). **All user-facing text is English** —
  the entire UI in `index.html` and every runtime/error message in `app.py`. README + user guide
  are English too.
- Do one coherent change at a time; explain what changed.
- **Never reset `recipes.csv`** (it holds the user's data). Migrations must transform in place.
  Earlier data loss happened from `rm recipes.csv` + re-import — don't do that.
- **User data is local & git-ignored:** `recipes.csv`, `cameras.json` and `images/` are in
  `.gitignore`, so a fresh clone starts empty (app bootstraps an empty CSV + a default X-T3).
  Keep the local files; never commit them.
- Design: dark theme, near-black/greys, white text, **red accent `#ff453a`**. Keep it clean/pro.

## Files
| File | Purpose |
|---|---|
| `app.py` | Local HTTP server (stdlib): serves `index.html`, JSON API, images, shutdown. |
| `index.html` | Entire UI in one file (embedded CSS + vanilla JS). |
| `recipes.csv` | All recipes (one row each). Columns = `FIELDNAMES` in `app.py`. **git-ignored** (user data, local only). |
| `cameras.json` | Cameras with capabilities + per-camera slot map. **git-ignored** (app recreates a default X-T3 if missing). |
| `images/` | Uploaded example photos, `images/<recipeId>/<file>`. **git-ignored.** |
| `FujiRecipeVault starten.command` / `… (Windows).vbs` / `… (Linux).sh` | Launchers (start hidden). |
| `ICON.png` | App icon — user-provided line-art Mount Fuji (white) on a black rounded tile, transparent corners. Served at `/ICON.png`; used as favicon + header logo in `index.html`. |
| `examples/starter-recipes.csv` | Bundled, generic starter recipes (X-T3-compatible). Loaded via the "Load example recipes" button on the empty view. **Committed** (not user data). |
| `LICENSE` | MIT license. |
| `README.md` | English overview + install + manual link + troubleshooting. |
| `docs/` | English user guide + real PNG screenshots (`screenshot-library/-editor/-cameras.png`). |

## Run & test
- Start (foreground, dev): `python3 app.py` → serves `http://127.0.0.1:8765`, opens browser.
- Start **without** opening a browser (for testing): `APP_NO_BROWSER=1 python3 app.py`.
- Stop cleanly: `POST /api/shutdown` (the in-app "⏻ Quit" button does this), or Ctrl+C.
- Always `python3 -m py_compile app.py` after editing.
- After restarting the server, the browser tab must be **reloaded** (hard reload) to get new `index.html`.
- Port already in use: `lsof -ti tcp:8765 | xargs kill -9`.

## Data model
### Recipe (row in `recipes.csv`, keys = `FIELDNAMES`)
Content fields (used for the "modified vs original" diff via `EDITABLE_FIELDS` / JS `DIFF_KEYS`):
`name, short_code (Kürzel), film_simulation, dynamic_range, d_range_priority, grain_effect,
grain_size, color_chrome_effect, color_chrome_effect_blue, white_balance, wb_kelvin,
wb_shift_red, wb_shift_blue, bw_adj_warm_cool, highlight_tone, shadow_tone, color, sharpness,
noise_reduction, clarity, iso, exposure_compensation, creator, notes`.
Meta fields (NOT part of the diff — see `META_FIELDS`): `id, images (JSON list), cameras
(comma-separated camera ids), custom (JSON of custom-param values), liked ("1"/""),
original_json (snapshot of content fields), created_at`.
- **Kürzel** encodes the WB shift because the camera doesn't store WB shift per custom bank.
- `original_json` is the baseline for the "Changes" view; `set_original=1` on PUT rewrites it.
- `short_code`, `creator`, `notes` are **excluded** from "modified" detection on purpose.

### Camera (object in `cameras.json`)
`{ id, name, slots (int), features {clarity, color_chrome_effect_blue, grain_size},
film_sims [..], param_options { dynamic_range:[..], d_range_priority:[..], grain_effect:[..],
grain_size:[..], color_chrome_effect:[..], color_chrome_effect_blue:[..] },
hidden [param keys], custom_params [{key,label,type('select'|'text'),options[]}], slotmap {C1:recipeId,..} }`
- Built-in presets: `CAMERA_PRESETS` (xt3/xt4/xpro3/x100v/xt5). `_camera_from_preset` + `_normalize_camera`.
- Slot assignments live **on the camera** (`slotmap`), so a recipe can sit in different slots on
  different cameras. A recipe belongs to one or more cameras via its `cameras` field.

## API (all JSON unless noted)
- `GET /` → index.html; `GET /ICON.png` → app icon; `GET /images/<id>/<file>` → image (chunked; robust to large files).
- `GET /api/recipes` · `POST /api/recipes` · `PUT /api/recipes?id=&set_original=0|1` · `DELETE /api/recipes?id=`
- `POST /api/images?id=&name=` (raw body) · `DELETE /api/images?id=&name=`
- `POST /api/examples?camera=<id>` → loads the bundled `examples/starter-recipes.csv` into that camera (each row gets a fresh id + original snapshot).
- `GET /api/cameras` · `POST /api/cameras` · `PUT /api/cameras?id=` · `DELETE /api/cameras?id=`
- `PUT /api/cameras/slot?camera=&slot=&recipe=` (empty `recipe` clears the slot)
- `POST /api/shutdown`

## Gotchas / invariants
- **All file access is serialized** via `threading.RLock` + `@synchronized` (fast repeated
  clicks, e.g. favorites, would otherwise clobber each other in the full-file rewrite).
- **Migration order matters:** `migrate_cameras()` runs **before** `migrate()` in `main()`,
  so the old `camera_slot` column is captured into the camera `slotmap` before the recipe
  migration rewrites the CSV (which drops removed columns).
- `write_recipes` writes exactly `FIELDNAMES`; removed columns disappear on next write.
- `_send_file` streams in 64 KB chunks and swallows client-disconnect errors (large images
  previously caused `OSError: [Errno 55]` and could break serving).
- Frontend: `index.html` is served fresh each GET, so editing it doesn't need a server restart
  (only `app.py` changes do). `applyCameraToEditor(r)` runs **before** `fillForm(r)` so dynamic
  dropdown options exist before values are set.

## Known limitations / possible next steps
- Uploaded images are stored full-resolution; the band can load slowly. Could add downscaled
  thumbnails (macOS `sips`, or Pillow if a dependency is acceptable — currently stdlib-only).
- `hidden` param list exists in the model but has no dedicated UI yet.
- Camera capability tables are best-effort; the user can correct them in the gear dialog.
