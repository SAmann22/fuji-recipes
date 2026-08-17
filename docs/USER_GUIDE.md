# FujiRecipeVault — User Guide

A complete walkthrough of every feature. FujiRecipeVault runs entirely on your own computer. Open
it with a launcher (see the [README](../README.md)) or with `python3 app.py`, then browse to
<http://127.0.0.1:8765>. The whole interface is in English.

The window has two halves:

- **Left** — the recipe list, plus search, filters, sorting and favorites.
- **Right** — with no recipe selected, the **camera slots (C1–C7)**; with a recipe selected, the
  **editor**.

![Recipe library and camera slots](screenshot-library.png)

---

## 1. Choosing a camera

Top-left, next to the logo, is the **camera selector**. It controls everything you see:

- Only recipes belonging to that camera appear in the list.
- The editor offers only that camera's film simulations and parameters.
- The slots panel shows that camera's custom banks.

A fresh install starts with a single default **X-T3**. Add more cameras via the **⚙ gear**
(section 8).

---

## 2. Creating and editing a recipe

On a brand-new install the library is empty. You can either click **Load example recipes** (shown
in the empty list) to drop in a few starter recipes and see how everything looks, or start from
scratch with **+ New recipe**. The examples are just a starting point — edit or delete them freely.

- **+ New recipe** (top-left) opens a blank editor for the current camera.
- Click a recipe in the list to open it; **click it again to close** it (back to the slots view).

![The recipe editor](screenshot-editor.png)

Fields are grouped into **Basics**, **Tone & color**, **Effects**, **White balance** and
**Exposure & extras**. Every parameter has a small **?** — **tap it** (don't hover) to read what it
does and whether your camera supports it.

- **Name** — free text (the camera itself allows only 12 characters for a custom name).
- **Short code** — top-right of the editor, e.g. `KG+4-5`: 2–4 letters plus the red/blue
  white-balance shift. It exists because the camera does **not** store the WB shift per custom bank,
  so the code reminds you what to dial in.
- **White balance** holds the mode; the **red/blue shift** has its own fields.
- Press **Save** to store. New recipes are saved for the currently selected camera.

---

## 3. Camera slots and drag & drop

With no recipe open, the right side lists your camera's custom banks (**C1–C7**, or however many
that camera has).

- **Assign:** drag a recipe from the list on the left onto a slot.
- **Open:** click a filled slot's name to edit that recipe.
- **Clear:** click the **✕** on a filled slot.
- One recipe per slot; dropping a new recipe replaces the previous one.
- Slots are **per camera** — the same recipe can sit in different banks on different cameras.

Inside the editor, the **Slot on this camera** dropdown assigns the open recipe directly.

---

## 4. Example photos

Open a recipe → the **Sample photos** strip at the top.

- **+ Photo** uploads one or more images.
- Images keep the same height and scroll **horizontally**.
- **Click** an image to view it large; **right-click → Remove image** to delete it.

Photos are stored locally in `images/` and never leave your computer.

---

## 5. Search, filters, sorting, favorites

- **Search** matches name, short code and creator.
- The **film-simulation filter** and the **All / Color / B&W** switch narrow the list.
- **Sort**: newest, oldest, A–Z, Z–A, favorites first, or by film simulation.
- **♥ (heart)** toggles a favorite — on each list row or in the editor. The **♥ toggle** next to the
  sort menu shows favorites only.

---

## 6. Original vs. changes

When you edit a saved recipe, its **original** is kept in the background.

- **Changes** (in the editor) opens a comparison of what you changed versus the original. Editing
  only the short code, creator or notes does **not** count as a change.
- **Reset to original** loads the original values back into the form (then Save to apply).
- **Set current as new original** makes the current state the new baseline.

---

## 7. Assigning a recipe to several cameras

At the bottom of the editor, **Which cameras?** shows a chip per camera. The current camera is
fixed; tick another compatible camera to make the recipe appear there too.

---

## 8. Managing cameras (⚙ gear)

The gear opens the camera manager. At the top, pick which camera to edit (or delete it). Below, you
can change everything about it:

![The camera manager](screenshot-cameras.png)

- **Name** and **number of custom slots**.
- **Film simulations** — one per line; add or remove any.
- **Optional parameters** — enable or disable *Clarity*, *Color Chrome FX Blue* and *Grain size*.
- **Allowed parameter values** — edit the options of each dropdown (Dynamic range, D-Range priority,
  Grain effect, Grain size, Color Chrome Effect, Color Chrome FX Blue), one value per line. Handy
  when a newer body adds a value.
- **Custom parameters** — add your own fields (a key, a label, and either a text field or a
  dropdown with options), then **Save camera**. They appear in the recipe editor under
  *More parameters*.

**Add a new camera** at the bottom: type a name, pick a **template** to copy settings from, choose
the number of slots, and click **Add**.

Deleting a camera keeps your recipes; they simply lose that camera's assignment.

---

## 9. Backup

All your data lives in plain files inside the app folder and stays on your computer. These files are
**not** part of the project's Git repository, so back them up yourself by copying them somewhere
safe:

```bash
cp recipes.csv cameras.json /path/to/backup/
cp -R images /path/to/backup/
```

`recipes.csv` opens in Numbers or Excel, and `cameras.json` is plain text — both are easy to keep in
your own private backup or file sync.

---

## 10. Quitting

Because the app starts without a visible window, stop the server with the **⏻ Quit** button, top
right. You can then close the browser tab. Start it again any time with the launcher.

---

## 11. Troubleshooting

- **Nothing happens when I double-click the launcher.** Python is probably not installed (most
  common on Windows) — get it from [python.org](https://www.python.org/downloads/) and tick
  *"Add Python to PATH"*. Or run `python app.py` (Windows) / `python3 app.py` (macOS/Linux) from a
  terminal in the folder.
- **macOS says the file "cannot be opened".** Right-click the launcher → **Open** → **Open**. Only
  needed the first time.
- **The browser doesn't open by itself.** Open it manually at <http://127.0.0.1:8765>.
- **"Address already in use" / won't start.** The app is already running — open
  <http://127.0.0.1:8765>. To force-stop it: `lsof -ti tcp:8765 | xargs kill -9` (macOS/Linux).

---

> **Disclaimer:** FujiRecipeVault is an independent, unofficial hobby project and is **not
> affiliated with, authorized, sponsored, or endorsed by FUJIFILM Corporation**. Camera model names
> are trademarks of their respective owners and are used only to describe compatibility.
