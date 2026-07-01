# Paint.NET Session Protection

A standalone Windows utility that periodically sends a configurable save hotkey to Paint.NET while Paint.NET is the foreground application. When the selected `.pdn` file changes, it creates a timestamped recovery copy.

## Safety model

- Save a new artwork once as `.pdn` before enabling protection.
- The hotkey is sent only when the foreground executable is `paintdotnet.exe` or `paint.net.exe`.
- Recovery copies are stored in `Paint.NET Versions` beside the selected document.
- Only versions belonging to the selected document are pruned.
- The app does not automate Save As dialogs or inspect Paint.NET memory.

## Run from source

```powershell
py -m pip install -r requirements.txt
.\launch.ps1
```

## Build a Windows executable

```powershell
.\build.ps1
```

The executable is written to `dist\Paint.NET Session Protection.exe`.

## Configuration

Settings are stored at `%APPDATA%\PaintNET Session Protection\settings.json`.

Supported hotkeys use Ctrl, Alt, Shift, or Win plus a letter, number, or F1-F12. Examples: `Ctrl+S`, `Ctrl+Shift+S`, `F5`.

`Ctrl+S` is strongly recommended. A Save As hotkey can open a dialog and is therefore not intervention-free.
