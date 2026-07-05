# Paint.NET Session Protection v3.0.0

A lightweight Windows utility that protects an active Paint.NET `.pdn` project with timed saves and timestamped recovery copies.

[Download the latest release](https://github.com/OReid60/paintnet-session-protection/releases/latest)

## What is new in Version 3

- Uses a fixed `Ctrl+S` save command for predictable, non-destructive saves.
- Waits until you have been idle for two seconds before requesting a save.
- Uses Paint.NET's top-level window ownership to avoid saving while a dialog is open.
- Watches the selected file for up to 15 seconds after saving.
- Creates a recovery copy only after the file changes and remains stable for one second.
- Prevents overlapping recovery checks.
- Lets you choose the recovery folder name.
- Identifies Paint.NET only by the supported `paintdotnet.exe` executable name.

## Features

- Protects an existing `.pdn` document at a configurable save interval.
- Creates timestamped recovery copies after completed saves.
- Keeps only the configured number of versions for the selected document.
- Stores recovery copies in a custom-named folder beside the original document.
- Includes system-tray controls, optional Windows startup, and toast notifications.
- Saves settings locally and restores protection when configured to do so.

## How to use

1. Save your Paint.NET artwork as a `.pdn` file.
2. Open Paint.NET Session Protection and select that file.
3. Set the save interval, number of versions to keep, and recovery folder name.
4. Click **Enable Protection**.
5. Continue working in Paint.NET. Protection runs while Paint.NET is the foreground application.

Recovery copies are named with the document name and save timestamp. Use **Open Recovery Folder** to view them.

## Safety model

- Protection sends only `Ctrl+S`; it does not automate Save As dialogs.
- A save is requested only when `paintdotnet.exe` is in the foreground, the user is briefly idle, and its window layout contains one enabled main window plus no more than the four normal owned palette windows.
- The app waits for a changed and stable file before copying it.
- Recovery pruning affects only timestamped `.pdn` versions matching the selected document.
- The original `.pdn` document is never deleted by version pruning.
- The app does not inspect or modify Paint.NET memory.

## Run from source

```powershell
py -m pip install -r requirements.txt
.\launch.ps1
```

## Build the Windows executable

```powershell
.\build.ps1
```

The executable is written to `dist\Paint.NET Session Protection.exe`.

## Configuration

Settings are stored at `%APPDATA%\PaintNET Session Protection\settings.json`.

## Windows security notice

The application is currently unsigned, so Windows SmartScreen may display a warning. Only run binaries downloaded from this repository's official release page.
