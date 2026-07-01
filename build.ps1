$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

py -m pip install -r .\requirements.txt
py .\tools\generate_icon.py
py -m PyInstaller --noconfirm --clean --windowed --onefile `
  --name "Paint.NET Session Protection" `
  --icon .\assets\app_icon.ico `
  --add-data ".\assets\app_icon.ico;assets" `
  .\app.py
