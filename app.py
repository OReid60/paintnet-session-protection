import ctypes
import json
import os
import shutil
import subprocess
import sys
import threading
import tkinter as tk
import winreg
import customtkinter as ctk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox
from PIL import Image
import pystray

try:
    from winotify import Notification
except ImportError:
    Notification = None


APP_NAME = "Paint.NET Session Protection"
APP_DIR = Path(os.getenv("APPDATA", Path.home())) / "PaintNET Session Protection"
CONFIG_PATH = APP_DIR / "settings.json"
CHECK_INTERVAL_MS = 1000
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


class SessionProtectionApp:
    def __init__(self, root):
        self.root = root
        self.enabled = False
        self.last_hotkey_at = None
        self.last_file_mtime = None
        self.pending_snapshot = False
        self.tray_icon = None
        self.quitting = False
        self.settings = self.load_settings()

        self.document_var = tk.StringVar(value=self.settings.get("document", ""))
        self.interval_var = tk.IntVar(value=self.settings.get("interval", 5))
        self.hotkey_var = tk.StringVar(value=self.settings.get("hotkey", "Ctrl+S"))
        self.retention_var = tk.IntVar(value=self.settings.get("retention", 20))
        self.status_var = tk.StringVar(value="Protection disabled")
        self.startup_var = tk.BooleanVar(value=self.is_startup_enabled())

        self.configure_window()
        self.build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.hide_to_tray)
        self.create_tray_icon()
        if "--background" in sys.argv:
            self.root.withdraw()
        self.root.after(CHECK_INTERVAL_MS, self.monitor)
        if self.settings.get("protection_enabled", False):
            self.root.after(100, self.toggle)

    def configure_window(self):
        self.root.title(APP_NAME)
        self.root.geometry("900x570")
        self.root.minsize(780, 520)
        self.root.configure(bg="#1e1f22")
        icon_path = Path(__file__).parent / "assets" / "app_icon.ico"
        if icon_path.exists():
            self.root.iconbitmap(icon_path)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

    def build_ui(self):
        shell = ctk.CTkFrame(self.root, fg_color="#1e1f22", corner_radius=0)
        shell.pack(fill="both", expand=True)
        sidebar = ctk.CTkFrame(shell, fg_color="#2b2d31", width=218, corner_radius=0)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        ctk.CTkLabel(sidebar, text="PAINT.NET", font=("Segoe UI", 16, "bold"), text_color="#f2f3f5").pack(anchor="w", padx=18, pady=(18, 0))
        ctk.CTkLabel(sidebar, text="SESSION PROTECTION", font=("Segoe UI", 9, "bold"), text_color="#b5bac1").pack(anchor="w", padx=18, pady=(0, 20))
        ctk.CTkLabel(sidebar, text="#   protection", anchor="w", height=40, corner_radius=10, fg_color="#404249", font=("Segoe UI", 11, "bold")).pack(fill="x", padx=10)
        ctk.CTkLabel(sidebar, text="#   recovery-versions", anchor="w", height=40, text_color="#b5bac1").pack(fill="x", padx=18, pady=(3, 0))
        ctk.CTkLabel(sidebar, text="Protection only runs while\nPaint.NET is in the foreground.", text_color="#949ba4", justify="left").pack(side="bottom", anchor="w", padx=18, pady=18)

        content = ctk.CTkFrame(shell, fg_color="#313338", corner_radius=0)
        content.pack(side="left", fill="both", expand=True)
        ctk.CTkLabel(content, text="Session Protection", font=("Segoe UI", 25, "bold"), text_color="#f2f3f5").pack(anchor="w", padx=30, pady=(22, 0))
        ctk.CTkLabel(content, text="Keep your current canvas saved and maintain automatic recovery versions.", text_color="#dbdee1").pack(anchor="w", padx=30, pady=(0, 18))
        card = ctk.CTkFrame(content, fg_color="#2b2d31", corner_radius=16)
        card.pack(fill="both", expand=True, padx=30)
        card.columnconfigure(0, weight=1)
        label = lambda parent, text: ctk.CTkLabel(parent, text=text, text_color="#b5bac1", font=("Segoe UI", 10, "bold"), anchor="w")
        ctk.CTkLabel(card, text="Protection settings", font=("Segoe UI", 14, "bold")).grid(row=0, column=0, columnspan=3, sticky="w", padx=22, pady=(20, 14))
        label(card, "PDN DOCUMENT").grid(row=1, column=0, columnspan=3, sticky="w", padx=22)
        ctk.CTkEntry(card, textvariable=self.document_var, height=38, corner_radius=10, border_width=0, fg_color="#1e1f22").grid(row=2, column=0, columnspan=2, sticky="ew", padx=(22, 8), pady=(5, 3))
        ctk.CTkButton(card, text="Browse", command=self.choose_document, height=38, corner_radius=10, fg_color="#4e5058", hover_color="#6d6f78").grid(row=2, column=2, sticky="ew", padx=(0, 22), pady=(5, 3))
        ctk.CTkLabel(card, text="Choose the .pdn file you want to protect.", text_color="#949ba4").grid(row=3, column=0, columnspan=3, sticky="w", padx=22, pady=(0, 14))
        label(card, "SAVE INTERVAL").grid(row=4, column=0, sticky="w", padx=(22, 0))
        label(card, "SAVE HOTKEY").grid(row=4, column=1, sticky="w", padx=(16, 0))
        label(card, "VERSIONS TO KEEP").grid(row=4, column=2, sticky="w", padx=(16, 22))
        ctk.CTkEntry(card, textvariable=self.interval_var, height=38, corner_radius=10, border_width=0, fg_color="#1e1f22").grid(row=5, column=0, sticky="ew", padx=(22, 0), pady=(5, 16))
        ctk.CTkEntry(card, textvariable=self.hotkey_var, height=38, corner_radius=10, border_width=0, fg_color="#1e1f22").grid(row=5, column=1, sticky="ew", padx=(16, 0), pady=(5, 16))
        ctk.CTkEntry(card, textvariable=self.retention_var, height=38, corner_radius=10, border_width=0, fg_color="#1e1f22").grid(row=5, column=2, sticky="ew", padx=(16, 22), pady=(5, 16))
        ctk.CTkLabel(card, textvariable=self.status_var, height=44, corner_radius=10, fg_color="#232428", anchor="w", padx=14, font=("Segoe UI", 11, "bold")).grid(row=6, column=0, columnspan=2, sticky="ew", padx=(22, 8), pady=(2, 14))
        self.toggle_button = ctk.CTkButton(card, text="Enable Protection", command=self.toggle, height=44, corner_radius=12, fg_color="#5865f2", hover_color="#4752c4", font=("Segoe UI", 11, "bold"))
        self.toggle_button.grid(row=6, column=2, sticky="ew", padx=(8, 22), pady=(2, 14))
        ctk.CTkButton(card, text="Open Recovery Versions", command=self.open_versions, height=42, corner_radius=12, fg_color="#4e5058", hover_color="#6d6f78", font=("Segoe UI", 11, "bold")).grid(row=7, column=0, columnspan=3, sticky="ew", padx=22, pady=(0, 20))
        startup = ctk.CTkFrame(card, fg_color="transparent")
        startup.grid(row=8, column=0, columnspan=3, sticky="ew", padx=22, pady=(0, 18))
        ctk.CTkSwitch(startup, text="Start with Windows", variable=self.startup_var, command=self.toggle_startup, progress_color="#5865f2", button_color="#ffffff", button_hover_color="#dbdee1", font=("Segoe UI", 11, "bold")).pack(side="left")
        ctk.CTkLabel(startup, text="Launches quietly in the system tray", text_color="#949ba4").pack(side="right")
        ctk.CTkLabel(content, text="Save a new artwork once as .pdn before enabling protection.", text_color="#949ba4").pack(anchor="w", padx=30, pady=(10, 14))

    def create_tray_icon(self):
        icon_path = Path(__file__).parent / "assets" / "app_icon.ico"
        try:
            image = Image.open(icon_path)
        except OSError:
            image = Image.new("RGBA", (64, 64), "#5865f2")

        menu = pystray.Menu(
            pystray.MenuItem("Open Session Protection", self.restore_from_tray, default=True),
            pystray.MenuItem(
                lambda _item: "Disable Protection" if self.enabled else "Enable Protection",
                self.toggle_from_tray,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", self.quit_app),
        )
        self.tray_icon = pystray.Icon("paintnet_session_protection", image, APP_NAME, menu)
        self.tray_icon.run_detached()

    def hide_to_tray(self):
        self.root.withdraw()
        self.notify_windows("Still protecting your canvas", "The app is running in the Windows system tray.")

    def restore_from_tray(self, _icon=None, _item=None):
        self.root.after(0, self._show_window)

    def _show_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def toggle_from_tray(self, _icon=None, _item=None):
        self.root.after(0, self._toggle_from_tray)

    def _toggle_from_tray(self):
        if not self.enabled:
            self._show_window()
        self.toggle()

    def quit_app(self, _icon=None, _item=None):
        self.quitting = True
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.after(0, self.root.destroy)

    @staticmethod
    def startup_command():
        if getattr(sys, "frozen", False):
            parts = [sys.executable, "--background"]
        else:
            pythonw = Path(sys.executable).with_name("pythonw.exe")
            parts = [str(pythonw if pythonw.exists() else sys.executable), str(Path(__file__).resolve()), "--background"]
        return subprocess.list2cmdline(parts)

    @staticmethod
    def is_startup_enabled():
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
                winreg.QueryValueEx(key, APP_NAME)
            return True
        except OSError:
            return False

    def toggle_startup(self):
        try:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
                if self.startup_var.get():
                    winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, self.startup_command())
                else:
                    try:
                        winreg.DeleteValue(key, APP_NAME)
                    except FileNotFoundError:
                        pass
        except OSError as error:
            self.startup_var.set(self.is_startup_enabled())
            messagebox.showerror("Startup setting", f"Windows could not update the startup setting:\n{error}", parent=self.root)

    def choose_document(self):
        path = filedialog.askopenfilename(parent=self.root, filetypes=[("Paint.NET document", "*.pdn")])
        if path:
            self.document_var.set(path)
            self.save_settings()

    def toggle(self):
        if self.enabled:
            self.enabled = False
            self.status_var.set("Protection disabled")
            self.toggle_button.configure(text="Enable Protection", fg_color="#5865f2", hover_color="#4752c4")
            self.save_settings()
            return

        try:
            document = self.validated_document()
            interval = int(self.interval_var.get())
            retention = int(self.retention_var.get())
            if interval < 1 or retention < 1:
                raise ValueError("Interval and retention must be at least 1.")
            self.parse_hotkey(self.hotkey_var.get())
        except (ValueError, tk.TclError) as error:
            messagebox.showwarning("Invalid settings", str(error), parent=self.root)
            return

        self.enabled = True
        self.last_hotkey_at = None
        self.last_file_mtime = document.stat().st_mtime
        self.status_var.set("Enabled — waiting for Paint.NET to be active")
        self.toggle_button.configure(text="Disable Protection", fg_color="#da373c", hover_color="#a1282c")
        self.save_settings()

    def monitor(self):
        if self.enabled:
            try:
                now = datetime.now()
                interval_seconds = max(1, int(self.interval_var.get())) * 60
                due = self.last_hotkey_at is None or (now - self.last_hotkey_at).total_seconds() >= interval_seconds
                if due and self.is_paintnet_foreground():
                    self.send_hotkey()
                    self.last_hotkey_at = now
                    self.pending_snapshot = True
                    self.status_var.set("Save requested — checking for file changes")
                    self.notify_windows(
                        "Timed save requested",
                        f"{self.hotkey_var.get()} was sent to Paint.NET at {now:%I:%M %p}.",
                    )
                    self.root.after(2000, self.snapshot_if_changed)
            except Exception as error:
                self.status_var.set(f"Protection error: {error}")
        self.root.after(CHECK_INTERVAL_MS, self.monitor)

    def snapshot_if_changed(self):
        self.pending_snapshot = False
        if not self.enabled:
            return
        document = Path(self.document_var.get())
        if not document.is_file():
            self.status_var.set("Selected document is no longer available")
            return
        current_mtime = document.stat().st_mtime
        if self.last_file_mtime is not None and current_mtime <= self.last_file_mtime:
            self.status_var.set("No new saved changes detected")
            return

        self.last_file_mtime = current_mtime
        versions = document.parent / "Paint.NET Versions"
        versions.mkdir(exist_ok=True)
        target = versions / f"{document.stem}_{datetime.now():%Y-%m-%d_%H-%M-%S}{document.suffix}"
        shutil.copy2(document, target)
        self.prune_versions(versions, document.stem)
        self.status_var.set(f"Recovery version saved at {datetime.now():%I:%M %p}")
        self.notify_windows(
            "Recovery version saved",
            f"A new recovery copy of {document.name} was created.",
        )

    @staticmethod
    def notify_windows(title, message):
        """Show a Windows toast without interrupting the protection loop."""
        if Notification is None:
            return

        def show_toast():
            try:
                Notification(
                    app_id=APP_NAME,
                    title=title,
                    msg=message,
                    duration="short",
                ).show()
            except Exception:
                # Notifications are optional and must never prevent a save.
                pass

        threading.Thread(target=show_toast, daemon=True).start()

    def prune_versions(self, folder, stem):
        files = sorted(folder.glob(f"{stem}_*.pdn"), key=lambda item: item.stat().st_mtime, reverse=True)
        for old_file in files[max(1, int(self.retention_var.get())):]:
            try:
                old_file.unlink()
            except OSError:
                pass

    def open_versions(self):
        try:
            document = self.validated_document()
        except ValueError as error:
            messagebox.showwarning("Document required", str(error), parent=self.root)
            return
        versions = document.parent / "Paint.NET Versions"
        versions.mkdir(exist_ok=True)
        os.startfile(versions)

    def validated_document(self):
        document = Path(self.document_var.get().strip())
        if not document.is_file() or document.suffix.lower() != ".pdn":
            raise ValueError("Select an existing .pdn document first.")
        return document

    @staticmethod
    def parse_hotkey(text):
        parts = [part.strip().lower() for part in text.split("+") if part.strip()]
        modifiers = {"ctrl": 0x11, "control": 0x11, "alt": 0x12, "shift": 0x10, "win": 0x5B, "windows": 0x5B}
        if not parts:
            raise ValueError("Enter a hotkey such as Ctrl+S.")
        modifier_codes = []
        for part in parts[:-1]:
            if part not in modifiers:
                raise ValueError("Supported modifiers: Ctrl, Alt, Shift, and Win.")
            modifier_codes.append(modifiers[part])
        key = parts[-1]
        if len(key) == 1 and key.isalnum():
            key_code = ord(key.upper())
        elif key.startswith("f") and key[1:].isdigit() and 1 <= int(key[1:]) <= 12:
            key_code = 0x6F + int(key[1:])
        else:
            raise ValueError("Use a letter, number, or F1-F12 as the final key.")
        return modifier_codes, key_code

    def send_hotkey(self):
        modifiers, key_code = self.parse_hotkey(self.hotkey_var.get())
        for modifier in modifiers:
            ctypes.windll.user32.keybd_event(modifier, 0, 0, 0)
        ctypes.windll.user32.keybd_event(key_code, 0, 0, 0)
        ctypes.windll.user32.keybd_event(key_code, 0, 0x0002, 0)
        for modifier in reversed(modifiers):
            ctypes.windll.user32.keybd_event(modifier, 0, 0x0002, 0)

    @staticmethod
    def is_paintnet_foreground():
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        process_id = ctypes.c_ulong()
        ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))
        handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, process_id.value)
        if handle:
            try:
                buffer = ctypes.create_unicode_buffer(32768)
                length = ctypes.c_ulong(len(buffer))
                if ctypes.windll.kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(length)):
                    return Path(buffer.value).name.lower() in {"paintdotnet.exe", "paint.net.exe"}
            finally:
                ctypes.windll.kernel32.CloseHandle(handle)
        return False

    def load_settings(self):
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def save_settings(self):
        APP_DIR.mkdir(parents=True, exist_ok=True)
        settings = {
            "document": self.document_var.get(),
            "interval": self.interval_var.get(),
            "hotkey": self.hotkey_var.get(),
            "retention": self.retention_var.get(),
            "protection_enabled": self.enabled,
        }
        CONFIG_PATH.write_text(json.dumps(settings, indent=2), encoding="utf-8")


if __name__ == "__main__":
    window = ctk.CTk()
    SessionProtectionApp(window)
    window.mainloop()
