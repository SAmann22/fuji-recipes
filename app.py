#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FujiRecipeVault – kleine, lokale App zum Speichern von Film-Simulations-Rezepten
für spiegellose Kameras (z. B. Modelle wie X-T3). Nicht mit Fujifilm verbunden.

Diese App läuft zu 100 % lokal auf deinem Mac:
- Sie startet einen kleinen Webserver, der NUR auf deinem Computer erreichbar ist
  (Adresse 127.0.0.1 – nicht aus dem Netzwerk/Internet erreichbar).
- Die Rezepte werden in der Datei "recipes.csv" im selben Ordner gespeichert.
- Beispielbilder liegen lokal im Ordner "images/".
- Zum Bedienen öffnet sich automatisch dein Browser.

Starten:  python3 app.py   (oder "FujiRecipeVault starten.command" doppelklicken)
Beenden:  im Terminal  Strg + C  drücken
"""

import csv
import json
import mimetypes
import os
import re
import shutil
import threading
import time
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs, unquote


# --- Konfiguration ---------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "recipes.csv")
CAMERAS_PATH = os.path.join(BASE_DIR, "cameras.json")   # Kameras + ihre Custom-Plätze
HTML_PATH = os.path.join(BASE_DIR, "index.html")
IMAGES_DIR = os.path.join(BASE_DIR, "images")     # hier liegen die Beispielbilder
EXAMPLES_PATH = os.path.join(BASE_DIR, "examples", "starter-recipes.csv")  # mitgelieferte Beispiel-Rezepte

HOST = "127.0.0.1"   # nur lokal – nicht aus dem Netzwerk erreichbar
PORT = 8765          # Adresse im Browser: http://127.0.0.1:8765

MAX_IMAGE_BYTES = 40 * 1024 * 1024   # max. 40 MB pro Bild
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".heic", ".heif", ".tif", ".tiff", ".bmp"}

# Spalten der CSV-Datei. Reihenfolge hier = Reihenfolge in der Datei.
FIELDNAMES = [
    "id",                        # eindeutige Nummer (automatisch)
    "name",                      # voller Name des Rezepts
    "short_code",                # Kürzel für die Kamera (2–4 Buchstaben + ±R±B)
    "film_simulation",           # Filmsimulation (z. B. Classic Chrome)
    "dynamic_range",             # Dynamikumfang (DR100/DR200/DR400)
    "d_range_priority",          # D-Range-Priorität (OFF/WEAK/STRONG/AUTO)
    "grain_effect",              # Körnungseffekt-Stärke (OFF/WEAK/STRONG)
    "grain_size",                # Korn-Größe (SMALL/LARGE) – erst ab X-T4
    "color_chrome_effect",       # Color-Chrome-Effekt (OFF/WEAK/STRONG)
    "color_chrome_effect_blue",  # Color Chrome FX Blue (X-T4/X-T5 – X-T3 hat das nicht)
    "white_balance",             # Weißabgleich (z. B. AUTO, Daylight, Kelvin)
    "wb_kelvin",                 # Kelvin-Wert (falls Weißabgleich = Kelvin)
    "wb_shift_red",              # Weißabgleich-Verschiebung Rot (z. B. -1, +4)
    "wb_shift_blue",             # Weißabgleich-Verschiebung Blau (z. B. -3, +2)
    "bw_adj_warm_cool",          # S/W-Abstimmung warm/kühl (nur ACROS/Monochrom)
    "highlight_tone",            # Lichter / Highlight Tone (-2..+4)
    "shadow_tone",               # Schatten / Shadow Tone (-2..+4)
    "color",                     # Farbe / Color (-4..+4)
    "sharpness",                 # Schärfe / Sharpness (-4..+4)
    "noise_reduction",           # Rauschreduzierung / Noise Reduction (-4..+4)
    "clarity",                   # Clarity (X-T4/X-T5 – X-T3 hat das nicht)
    "iso",                       # empfohlene ISO (freier Text)
    "exposure_compensation",     # Belichtungskorrektur (freier Text)
    "creator",                   # Ersteller/Quelle des Rezepts (kann leer sein)
    "notes",                     # eigene Notizen (nur eigene Ergänzungen)
    "images",                    # Beispielbilder (JSON-Liste von Dateinamen)
    "cameras",                   # zugeordnete Kameras (kommagetrennte IDs, z. B. "xt3,xt4")
    "custom",                    # Werte eigener (kamera-spezifischer) Parameter (JSON)
    "liked",                     # Favorit? ("1" = ja, sonst leer)
    "original_json",             # Originalzustand als JSON (für "Änderungen anzeigen")
    "created_at",                # Speicherdatum (automatisch)
]

# Verwaltungsfelder – NICHT Teil des eigentlichen Rezept-Inhalts.
META_FIELDS = {"id", "liked", "original_json", "created_at", "images", "cameras", "custom"}
# Inhaltliche Felder (werden im Original gesichert und für den Vergleich genutzt).
EDITABLE_FIELDS = [k for k in FIELDNAMES if k not in META_FIELDS]

# Ein Schloss serialisiert alle Datei-Zugriffe, damit schnelle Klicks (z. B. mehrere
# Favoriten kurz hintereinander) sich nicht gegenseitig überschreiben.
_LOCK = threading.RLock()


def synchronized(fn):
    """Lässt die dekorierte Funktion immer nur von einem Aufruf gleichzeitig laufen."""
    def wrapper(*args, **kwargs):
        with _LOCK:
            return fn(*args, **kwargs)
    return wrapper


# --- CSV-Hilfsfunktionen ---------------------------------------------------

def ensure_csv():
    """Legt die CSV-Datei mit Kopfzeile an, falls sie noch nicht existiert."""
    if not os.path.exists(CSV_PATH):
        with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=FIELDNAMES).writeheader()


@synchronized
def read_recipes():
    """Liest alle Rezepte aus der CSV und gibt eine Liste von Dictionaries zurück."""
    ensure_csv()
    with open(CSV_PATH, "r", newline="", encoding="utf-8") as f:
        return [row for row in csv.DictReader(f)]


@synchronized
def write_recipes(recipes):
    """Schreibt die komplette Liste von Rezepten zurück in die CSV-Datei."""
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for r in recipes:
            writer.writerow({key: r.get(key, "") for key in FIELDNAMES})


@synchronized
def add_recipe(data):
    """Fügt ein neues Rezept hinzu, speichert es und gibt es zurück."""
    recipes = read_recipes()
    new_recipe = {key: str(data.get(key, "")).strip() for key in FIELDNAMES}
    new_recipe["id"] = str(int(time.time() * 1000))            # eindeutige ID via Zeitstempel
    new_recipe["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    new_recipe["liked"] = str(data.get("liked", "")).strip()
    new_recipe["images"] = "[]"
    # Originalzustand (nur Inhalt) sichern – für "Änderungen anzeigen".
    snapshot = {k: new_recipe.get(k, "") for k in EDITABLE_FIELDS}
    new_recipe["original_json"] = json.dumps(snapshot, ensure_ascii=False)
    recipes.append(new_recipe)
    write_recipes(recipes)
    return new_recipe


@synchronized
def load_examples(camera_id):
    """Fügt die mitgelieferten Beispiel-Rezepte der angegebenen Kamera hinzu.

    Wird vom „Load example recipes"-Knopf im leeren Zustand aufgerufen, damit ein
    frisch heruntergeladener Start nicht komplett leer ist. Gibt die neu angelegten
    Rezepte zurück (leere Liste, wenn keine Beispiel-Datei vorhanden ist).
    """
    if not camera_id or not os.path.exists(EXAMPLES_PATH):
        return []
    recipes = read_recipes()
    added = []
    base_id = int(time.time() * 1000)   # eindeutige IDs: Basiszeit + fortlaufender Index
    with open(EXAMPLES_PATH, "r", newline="", encoding="utf-8") as f:
        for i, row in enumerate(csv.DictReader(f)):
            rec = {key: str(row.get(key, "")).strip() for key in FIELDNAMES}
            rec["id"] = str(base_id + i)
            rec["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            rec["images"] = "[]"
            rec["cameras"] = camera_id          # Beispiel gehört zur aktuell gewählten Kamera
            rec["liked"] = ""
            snapshot = {k: rec.get(k, "") for k in EDITABLE_FIELDS}   # Originalstand sichern
            rec["original_json"] = json.dumps(snapshot, ensure_ascii=False)
            recipes.append(rec)
            added.append(rec)
    if added:
        write_recipes(recipes)
    return added


@synchronized
def update_recipe(recipe_id, data, set_original=False):
    """Ändert ein bestehendes Rezept (nur die mitgeschickten Felder).

    ID, Datum, Bilder und der Originalstand bleiben unangetastet.
    """
    recipes = read_recipes()
    for r in recipes:
        if r.get("id") == recipe_id:
            for key in FIELDNAMES:
                if key in ("id", "created_at", "original_json", "images"):
                    continue
                if key in data:                       # nur übergebene Felder ändern
                    r[key] = str(data.get(key, "")).strip()
            if set_original:
                # aktuellen Stand als neuen Originalzustand festschreiben
                snap = {k: r.get(k, "") for k in EDITABLE_FIELDS}
                r["original_json"] = json.dumps(snap, ensure_ascii=False)
            write_recipes(recipes)
            return r
    return None


@synchronized
def delete_recipe(recipe_id):
    """Löscht das Rezept mit der angegebenen ID (samt seiner Bilder)."""
    recipes = read_recipes()
    recipes = [r for r in recipes if r.get("id") != recipe_id]
    write_recipes(recipes)
    if recipe_id and recipe_id.isdigit():
        folder = os.path.join(IMAGES_DIR, recipe_id)
        if os.path.isdir(folder):
            try:
                shutil.rmtree(folder)
            except OSError:
                pass


def migrate():
    """Ergänzt bei bestehenden Rezepten fehlende Spalten und den Originalstand."""
    if not os.path.exists(CSV_PATH):
        return
    recipes = read_recipes()
    changed = False
    for r in recipes:
        for key in FIELDNAMES:
            if key not in r:
                changed = True
        if not r.get("original_json"):
            snapshot = {k: r.get(k, "") for k in EDITABLE_FIELDS}
            r["original_json"] = json.dumps(snapshot, ensure_ascii=False)
            changed = True
        if not r.get("images"):
            r["images"] = "[]"
            changed = True
    if changed:
        write_recipes(recipes)


# --- Bilder ----------------------------------------------------------------

def ensure_images_dir():
    """Legt den Bilder-Ordner an, falls er fehlt."""
    os.makedirs(IMAGES_DIR, exist_ok=True)


def save_image(recipe_id, orig_name, ctype, data):
    """Speichert ein hochgeladenes Bild und gibt den neuen Dateinamen zurück (oder None)."""
    if not recipe_id.isdigit():
        return None
    ext = os.path.splitext(orig_name)[1].lower()
    ct = (ctype or "").split(";")[0].strip().lower()
    if ext not in IMAGE_EXTS:
        if ct.startswith("image/"):
            ext = mimetypes.guess_extension(ct) or ".jpg"
        else:
            return None      # kein Bild
    # Dateinamen säubern (nur harmlose Zeichen) und eindeutig machen.
    base = os.path.splitext(os.path.basename(orig_name))[0]
    base = re.sub(r"[^A-Za-z0-9_-]+", "-", base).strip("-") or "bild"
    fname = f"{int(time.time() * 1000)}_{base}{ext}"
    folder = os.path.join(IMAGES_DIR, recipe_id)
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, fname), "wb") as f:
        f.write(data)
    return fname


@synchronized
def add_image_to_recipe(recipe_id, filename):
    """Hängt einen Bild-Dateinamen an ein Rezept an und gibt das Rezept zurück."""
    recipes = read_recipes()
    for r in recipes:
        if r.get("id") == recipe_id:
            imgs = json.loads(r.get("images") or "[]")
            imgs.append(filename)
            r["images"] = json.dumps(imgs, ensure_ascii=False)
            write_recipes(recipes)
            return r
    return None


@synchronized
def remove_image_from_recipe(recipe_id, filename):
    """Entfernt ein Bild aus einem Rezept und löscht die Datei."""
    filename = os.path.basename(filename)     # Sicherheit: kein Pfad
    recipes = read_recipes()
    for r in recipes:
        if r.get("id") == recipe_id:
            imgs = json.loads(r.get("images") or "[]")
            if filename in imgs:
                imgs.remove(filename)
                r["images"] = json.dumps(imgs, ensure_ascii=False)
                write_recipes(recipes)
            break
    path = os.path.join(IMAGES_DIR, recipe_id, filename)
    try:
        if os.path.isfile(path):
            os.remove(path)
    except OSError:
        pass


# --- Kameras ---------------------------------------------------------------

# Filmsimulations-Listen je Sensor-Generation (nach bestem Wissen; anpassbar).
_SIMS_XT3 = [
    "PROVIA / STANDARD", "Velvia / VIVID", "ASTIA / SOFT", "CLASSIC CHROME",
    "CLASSIC NEG.", "PRO Neg. Hi", "PRO Neg. Std", "ETERNA / CINEMA",
    "ACROS", "ACROS +Ye", "ACROS +R", "ACROS +G",
    "MONOCHROME", "MONOCHROME +Ye", "MONOCHROME +R", "MONOCHROME +G", "SEPIA",
]
_SIMS_XT4 = _SIMS_XT3[:8] + ["ETERNA BLEACH BYPASS"] + _SIMS_XT3[8:]
_SIMS_XT5 = _SIMS_XT4[:9] + ["Nostalgic Negative"] + _SIMS_XT4[9:]

# Vorlagen für gängige Modelle (Nutzer kann anpassen/ergänzen).
CAMERA_PRESETS = {
    "xt3":   {"name": "X-T3",   "slots": 7, "features": {"clarity": False, "color_chrome_effect_blue": False, "grain_size": False}, "film_sims": _SIMS_XT3},
    "xt4":   {"name": "X-T4",   "slots": 7, "features": {"clarity": True,  "color_chrome_effect_blue": True,  "grain_size": True},  "film_sims": _SIMS_XT4},
    "xpro3": {"name": "X-Pro3", "slots": 7, "features": {"clarity": True,  "color_chrome_effect_blue": True,  "grain_size": True},  "film_sims": _SIMS_XT4},
    "x100v": {"name": "X100V",  "slots": 7, "features": {"clarity": True,  "color_chrome_effect_blue": True,  "grain_size": True},  "film_sims": _SIMS_XT4},
    "xt5":   {"name": "X-T5",   "slots": 7, "features": {"clarity": True,  "color_chrome_effect_blue": True,  "grain_size": True},  "film_sims": _SIMS_XT5},
}


# Standard-Auswahlwerte der eingebauten Parameter (pro Kamera editierbar).
DEFAULT_DROPDOWNS = {
    "dynamic_range": ["AUTO", "DR100", "DR200", "DR400"],
    "d_range_priority": ["OFF", "WEAK", "STRONG", "AUTO"],
    "grain_effect": ["OFF", "WEAK", "STRONG"],
    "grain_size": ["SMALL", "LARGE"],
    "color_chrome_effect": ["OFF", "WEAK", "STRONG"],
    "color_chrome_effect_blue": ["OFF", "WEAK", "STRONG"],
}


def _slug(s):
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())[:20]


def _camera_from_preset(cam_id, preset_id, name=None):
    p = CAMERA_PRESETS.get(preset_id, CAMERA_PRESETS["xt3"])
    return {
        "id": cam_id, "name": name or p["name"], "slots": p["slots"],
        "features": dict(p["features"]), "film_sims": list(p["film_sims"]),
        "param_options": {k: list(v) for k, v in DEFAULT_DROPDOWNS.items()},
        "hidden": [], "custom_params": [], "slotmap": {},
    }


def _normalize_camera(c):
    """Ergänzt fehlende (neue) Felder bei einer Kamera."""
    c.setdefault("slots", 7)
    c.setdefault("features", {"clarity": False, "color_chrome_effect_blue": False, "grain_size": False})
    c.setdefault("film_sims", [])
    c.setdefault("param_options", {k: list(v) for k, v in DEFAULT_DROPDOWNS.items()})
    c.setdefault("hidden", [])
    c.setdefault("custom_params", [])
    c.setdefault("slotmap", {})
    return c


@synchronized
def read_cameras():
    if not os.path.exists(CAMERAS_PATH):
        return []
    try:
        with open(CAMERAS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


@synchronized
def write_cameras(cameras):
    with open(CAMERAS_PATH, "w", encoding="utf-8") as f:
        json.dump(cameras, f, ensure_ascii=False, indent=2)


def ensure_cameras():
    """Legt beim ersten Start die Standard-Kamera (X-T3) an."""
    if not read_cameras():
        write_cameras([_camera_from_preset("xt3", "xt3")])


def migrate_cameras():
    """Ordnet bestehende Rezepte der Standard-Kamera zu und übernimmt alte Plätze."""
    ensure_cameras()
    cameras = read_cameras()
    if not cameras:
        return
    for c in cameras:                   # neue Kamera-Felder bei Bedarf ergänzen
        _normalize_camera(c)
    write_cameras(cameras)
    default_id = cameras[0]["id"]
    recipes = read_recipes()            # liest ggf. noch die alte 'camera_slot'-Spalte
    slotmap = dict(cameras[0].get("slotmap", {}))
    changed = False
    for r in recipes:
        if not r.get("cameras"):
            r["cameras"] = default_id
            changed = True
        old_slot = r.get("camera_slot", "")   # alter fester Platz -> Standard-Kamera
        if old_slot:
            slotmap[old_slot] = r["id"]
    if changed:
        write_recipes(recipes)          # schreibt neue Spalten, verwirft 'camera_slot'
    valid = {r["id"] for r in recipes}
    slotmap = {k: v for k, v in slotmap.items() if v in valid}
    if slotmap != cameras[0].get("slotmap", {}):
        cameras[0]["slotmap"] = slotmap
        write_cameras(cameras)


@synchronized
def add_camera(data):
    cameras = read_cameras()
    existing = {c["id"] for c in cameras}
    cam_id = _slug(data.get("id") or data.get("name") or "") or ("cam" + str(int(time.time())))
    base, i = cam_id, 2
    while cam_id in existing:
        cam_id = f"{base}{i}"; i += 1
    cam = _camera_from_preset(cam_id, data.get("preset", "xt3"), data.get("name"))
    if isinstance(data.get("film_sims"), list):
        cam["film_sims"] = data["film_sims"]
    if isinstance(data.get("features"), dict):
        cam["features"].update(data["features"])
    if data.get("slots"):
        cam["slots"] = int(data["slots"])
    cameras.append(cam)
    write_cameras(cameras)
    return cam


@synchronized
def update_camera(cam_id, data):
    cameras = read_cameras()
    for c in cameras:
        if c["id"] == cam_id:
            if "name" in data:      c["name"] = data["name"]
            if isinstance(data.get("film_sims"), list):  c["film_sims"] = data["film_sims"]
            if isinstance(data.get("features"), dict):   c["features"] = data["features"]
            if data.get("slots"):   c["slots"] = int(data["slots"])
            if isinstance(data.get("param_options"), dict):  c["param_options"] = data["param_options"]
            if isinstance(data.get("hidden"), list):         c["hidden"] = data["hidden"]
            if isinstance(data.get("custom_params"), list):  c["custom_params"] = data["custom_params"]
            _normalize_camera(c)
            write_cameras(cameras)
            return c
    return None


@synchronized
def delete_camera(cam_id):
    cameras = [c for c in read_cameras() if c["id"] != cam_id]
    write_cameras(cameras)
    recipes = read_recipes()            # Kamera aus den Zugehörigkeiten entfernen
    changed = False
    for r in recipes:
        ids = [x for x in r.get("cameras", "").split(",") if x and x != cam_id]
        newval = ",".join(ids)
        if newval != r.get("cameras", ""):
            r["cameras"] = newval
            changed = True
    if changed:
        write_recipes(recipes)


@synchronized
def set_camera_slot(cam_id, slot, recipe_id):
    """Legt ein Rezept auf einen Platz DIESER Kamera (exklusiv pro Kamera)."""
    cameras = read_cameras()
    for c in cameras:
        if c["id"] == cam_id:
            sm = {k: v for k, v in c.get("slotmap", {}).items() if v != recipe_id}
            if recipe_id:
                sm[slot] = recipe_id
            else:
                sm.pop(slot, None)
            c["slotmap"] = sm
            write_cameras(cameras)
            return c
    return None


# --- Webserver -------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):
    """Beantwortet die Anfragen vom Browser: Seite ausliefern + kleine API."""

    def _send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path, content_type):
        # In Häppchen ausliefern – große Bilder brechen so nicht ab (ENOBUFS),
        # und ein Abbruch durch den Browser lässt den Server nicht abstürzen.
        size = os.path.getsize(path)
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(size))
        self.end_headers()
        try:
            with open(path, "rb") as f:
                while True:
                    chunk = f.read(64 * 1024)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass

    def _read_json_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return None
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            return None

    def _serve_image(self, path):
        """Ein gespeichertes Bild sicher ausliefern (kein Ausbruch aus dem Bilder-Ordner)."""
        rel = unquote(path[len("/images/"):])
        target = os.path.normpath(os.path.join(IMAGES_DIR, rel))
        if not target.startswith(IMAGES_DIR + os.sep) or not os.path.isfile(target):
            self.send_error(404, "Not found")
            return
        ctype = mimetypes.guess_type(target)[0] or "application/octet-stream"
        self._send_file(target, ctype)

    def _handle_image_upload(self, parsed):
        params = parse_qs(parsed.query)
        recipe_id = (params.get("id") or [""])[0]
        orig_name = (params.get("name") or ["bild"])[0]
        length = int(self.headers.get("Content-Length", 0))
        if length <= 0 or length > MAX_IMAGE_BYTES:
            self._send_json({"error": "Image missing or too large"}, status=400)
            return
        data = self.rfile.read(length)
        filename = save_image(recipe_id, orig_name, self.headers.get("Content-Type", ""), data)
        if filename is None:
            self._send_json({"error": "Not a valid image"}, status=400)
            return
        updated = add_image_to_recipe(recipe_id, filename)
        if updated is None:
            remove_image_from_recipe(recipe_id, filename)   # verwaistes Bild aufräumen
            self._send_json({"error": "Recipe not found"}, status=404)
            return
        self._send_json(updated, status=201)

    # GET = etwas abrufen (Seite, Rezepte oder ein Bild)
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path in ("/", "/index.html"):
            self._send_file(HTML_PATH, "text/html; charset=utf-8")
        elif parsed.path == "/ICON.png":
            self._send_file(os.path.join(BASE_DIR, "ICON.png"), "image/png")
        elif parsed.path == "/api/recipes":
            self._send_json(read_recipes())
        elif parsed.path == "/api/cameras":
            self._send_json(read_cameras())
        elif parsed.path.startswith("/images/"):
            self._serve_image(parsed.path)
        else:
            self.send_error(404, "Not found")

    # POST = neu anlegen (Rezept) oder Bild hochladen
    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/recipes":
            data = self._read_json_body()
            if data is None:
                self._send_json({"error": "Invalid data"}, status=400)
                return
            self._send_json(add_recipe(data), status=201)
        elif parsed.path == "/api/cameras":
            self._send_json(add_camera(self._read_json_body() or {}), status=201)
        elif parsed.path == "/api/images":
            self._handle_image_upload(parsed)
        elif parsed.path == "/api/examples":
            # Mitgelieferte Beispiel-Rezepte in die aktuelle Kamera laden.
            params = parse_qs(parsed.query)
            cam = (params.get("camera") or [""])[0]
            self._send_json(load_examples(cam), status=201)
        elif parsed.path == "/api/shutdown":
            # Server sauber beenden (für den "Beenden"-Button, wenn kein Fenster sichtbar ist)
            self._send_json({"ok": True})
            threading.Thread(target=self.server.shutdown, daemon=True).start()
        else:
            self.send_error(404, "Not found")

    # PUT = ein bestehendes Rezept ändern (anhand der ID)
    def do_PUT(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/recipes":
            params = parse_qs(parsed.query)
            recipe_id = (params.get("id") or [""])[0]
            data = self._read_json_body()
            if data is None:
                self._send_json({"error": "Invalid data"}, status=400)
                return
            set_original = (params.get("set_original") or ["0"])[0] == "1"
            updated = update_recipe(recipe_id, data, set_original=set_original)
            if updated is None:
                self._send_json({"error": "Not found"}, status=404)
                return
            self._send_json(updated)
        elif parsed.path == "/api/cameras":
            params = parse_qs(parsed.query)
            updated = update_camera((params.get("id") or [""])[0], self._read_json_body() or {})
            self._send_json(updated or {"error": "Not found"}, status=200 if updated else 404)
        elif parsed.path == "/api/cameras/slot":
            params = parse_qs(parsed.query)
            cam = (params.get("camera") or [""])[0]
            slot = (params.get("slot") or [""])[0]
            recipe_id = (params.get("recipe") or [""])[0]
            self._send_json(set_camera_slot(cam, slot, recipe_id) or {"error": "Not found"})
        else:
            self.send_error(404, "Not found")

    # DELETE = Rezept oder Bild löschen
    def do_DELETE(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        recipe_id = (params.get("id") or [""])[0]
        if parsed.path == "/api/recipes":
            delete_recipe(recipe_id)
            self._send_json({"ok": True})
        elif parsed.path == "/api/images":
            name = (params.get("name") or [""])[0]
            remove_image_from_recipe(recipe_id, name)
            self._send_json({"ok": True})
        elif parsed.path == "/api/cameras":
            delete_camera(recipe_id)   # 'id'-Parameter = Kamera-ID
            self._send_json({"ok": True})
        else:
            self.send_error(404, "Not found")

    def log_message(self, format, *args):
        pass   # Standard-Protokoll unterdrücken, damit das Terminal ruhig bleibt


def main():
    ensure_csv()
    migrate_cameras()   # zuerst: übernimmt alte camera_slot-Werte in die Kamera
    migrate()
    ensure_images_dir()
    url = f"http://{HOST}:{PORT}"
    print("=" * 54)
    print("  FujiRecipeVault is running!")
    print(f"  Open in your browser:  {url}")
    print(f"  Recipes file:          {CSV_PATH}")
    print("  To stop:               press Ctrl + C")
    print("=" * 54)

    if os.environ.get("APP_NO_BROWSER") != "1":
        try:
            webbrowser.open(url)
        except Exception:
            pass

    # Server starten. Ist der Port schon belegt, läuft FujiRecipeVault sehr
    # wahrscheinlich bereits – der Browser (oben schon geöffnet) zeigt dann die
    # laufende Instanz. Wir beenden diesen zweiten Start ruhig, statt abzustürzen.
    try:
        server = ThreadingHTTPServer((HOST, PORT), Handler)
    except OSError as exc:
        print()
        print("  FujiRecipeVault seems to be running already.")
        print(f"  Your browser should show it at {url} — nothing else to do.")
        print(f"  (If not, close the other instance and start again. Detail: {exc})")
        return

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped. See you!")
        server.server_close()


if __name__ == "__main__":
    main()
