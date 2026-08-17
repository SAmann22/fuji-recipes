#!/bin/bash
# ============================================================
#  FujiRecipeVault starten (Linux)
#  Startet die App im Hintergrund (ohne Terminal).
#  Beenden: in der App oben rechts auf "Beenden" klicken.
# ============================================================
cd "$(dirname "$0")"
URL="http://127.0.0.1:8765"

# Server nur starten, wenn er nicht bereits läuft
if ! curl -s --max-time 1 -o /dev/null "$URL" 2>/dev/null; then
  nohup python3 app.py >/dev/null 2>&1 &
fi

# kurz warten, dann Standard-Browser öffnen
sleep 1
xdg-open "$URL" >/dev/null 2>&1 &
