"""Windows shell integration: an Explorer context-menu verb and a SendTo shortcut.

Everything lives under HKCU, so no administrator rights are required.
"""
import logging
import os
import subprocess
import sys
from pathlib import Path

from docforge.proc import NO_WINDOW

log = logging.getLogger(__name__)

VERB = "DocForge"
VERB_LABEL = "Конвертировать через DocForge"
SENDTO_NAME = "DocForge.lnk"

# Where the verb is registered for one extension
_SHELL_KEY = r"Software\Classes\SystemFileAssociations\{ext}\shell\{verb}"


def _repo_root() -> Path:
    """Repository root — the folder holding main.py."""
    return Path(__file__).resolve().parents[2]


def launcher() -> tuple[str, Path]:
    """Return (pythonw path, main.py path) used to start the app windowless."""
    exe = Path(sys.executable)
    windowless = exe.with_name("pythonw.exe")
    if not windowless.is_file():
        windowless = exe
    return str(windowless), _repo_root() / "main.py"


def icon_path() -> Path:
    return Path(__file__).resolve().parents[1] / "resources" / "app.ico"


def _command() -> str:
    exe, script = launcher()
    return f'"{exe}" "{script}" "%1"'


# --------------------------------------------------------------- context menu

def context_menu_installed(ext: str) -> bool:
    import winreg
    key = _SHELL_KEY.format(ext=ext, verb=VERB)
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key):
            return True
    except OSError:
        return False


def install_context_menu(exts: list[str]) -> None:
    """Register the verb for the given extensions (".docx" style)."""
    import winreg
    command = _command()
    icon = str(icon_path())
    for ext in exts:
        key = _SHELL_KEY.format(ext=ext, verb=VERB)
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key) as k:
            winreg.SetValueEx(k, None, 0, winreg.REG_SZ, VERB_LABEL)
            if os.path.isfile(icon):
                winreg.SetValueEx(k, "Icon", 0, winreg.REG_SZ, icon)
            # ask Explorer to invoke us once with the whole selection
            winreg.SetValueEx(k, "MultiSelectModel", 0, winreg.REG_SZ, "Player")
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key + r"\command") as k:
            winreg.SetValueEx(k, None, 0, winreg.REG_SZ, command)
    log.info("Контекстное меню: зарегистрировано для %d расширений", len(exts))


def uninstall_context_menu(exts: list[str]) -> None:
    import winreg
    removed = 0
    for ext in exts:
        key = _SHELL_KEY.format(ext=ext, verb=VERB)
        for sub in (key + r"\command", key):
            try:
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, sub)
            except OSError:
                pass
        if not context_menu_installed(ext):
            removed += 1
    log.info("Контекстное меню: удалено для %d расширений", removed)


# -------------------------------------------------------------------- SendTo

def sendto_dir() -> Path:
    return Path(os.getenv("APPDATA", str(Path.home()))) / "Microsoft" / "Windows" / "SendTo"


def sendto_shortcut() -> Path:
    return sendto_dir() / SENDTO_NAME


def sendto_installed() -> bool:
    return sendto_shortcut().is_file()


def install_sendto() -> None:
    """Create the SendTo shortcut via WScript.Shell (PowerShell, no extra deps)."""
    exe, script = launcher()
    lnk = sendto_shortcut()
    lnk.parent.mkdir(parents=True, exist_ok=True)
    ps = (
        "$w = New-Object -ComObject WScript.Shell; "
        f"$s = $w.CreateShortcut('{lnk}'); "
        f"$s.TargetPath = '{exe}'; "
        f"$s.Arguments = '\"{script}\"'; "
        f"$s.WorkingDirectory = '{script.parent}'; "
        f"$s.IconLocation = '{icon_path()}'; "
        "$s.Description = 'DocForge'; "
        "$s.Save()"
    )
    subprocess.check_call(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=NO_WINDOW,
    )
    log.info("SendTo: создан ярлык %s", lnk)


def uninstall_sendto() -> None:
    lnk = sendto_shortcut()
    try:
        lnk.unlink()
        log.info("SendTo: ярлык удалён")
    except FileNotFoundError:
        pass
