' ============================================================
'  FujiRecipeVault starten (Windows)
'  Startet die App unsichtbar (ohne Konsolenfenster).
'  Beenden: in der App oben rechts auf "Beenden" klicken.
' ============================================================
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")

' In den Ordner dieser Datei wechseln
sh.CurrentDirectory = fso.GetParentFolderName(WScript.ScriptFullName)

' Server ohne Fenster starten (pythonw = Python ohne Konsolenfenster)
sh.Run "pythonw app.py", 0, False

' kurz warten und Standard-Browser öffnen
WScript.Sleep 1500
sh.Run "http://127.0.0.1:8765"
