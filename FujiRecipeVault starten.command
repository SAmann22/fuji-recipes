#!/bin/bash
# ============================================================
#  FujiRecipeVault starten (macOS)
#  Startet die App unsichtbar: der kleine Server läuft im Hintergrund weiter,
#  dieses Terminal-Fenster schließt sich automatisch.
#  Beenden: in der App oben rechts auf „⏻ Beenden" klicken.
# ============================================================
cd "$(dirname "$0")"
URL="http://127.0.0.1:8765"

# Server nur starten, wenn er nicht bereits läuft
if ! curl -s --max-time 1 -o /dev/null "$URL" 2>/dev/null; then
  nohup python3 app.py >/dev/null 2>&1 &
fi

# kurz warten, dann Standard-Browser öffnen
sleep 1
open "$URL"

# dieses Terminal-Fenster schließen (der Server läuft losgelöst weiter)
osascript -e 'tell application "Terminal" to close (every window whose name contains "FujiRecipeVault starten")' >/dev/null 2>&1 &
