"""Windows shell integration: an Explorer context-menu verb and a SendTo shortcut.

Everything lives under HKCU, so no administrator rights are required.
"""
import logging
import os
import subprocess
import sys
from pathlib import Path

from docforge.core.paths import app_dir, get_resource_path, is_frozen
from docforge.i18n import tr
from docforge.proc import NO_WINDOW

log = logging.getLogger(__name__)

VERB = "DocForge"


def verb_label() -> str:
    """Menu caption shown by Explorer (in the current UI language)."""
    return tr("Convert with DocForge")


SENDTO_NAME = "DocForge.lnk"

# Where the verb is registered for one extension
_SHELL_KEY = r"Software\Classes\SystemFileAssociations\{ext}\shell\{verb}"


def _repo_root() -> Path:
    """Repository root — the folder holding main.py."""
    return app_dir()


def launcher() -> tuple[str, Path]:
    """Return (executable/pythonw path, script/exe path)."""
    if is_frozen():
        return sys.executable, Path(sys.executable)
    exe = Path(sys.executable)
    windowless = exe.with_name("pythonw.exe")
    if not windowless.is_file():
        windowless = exe
    return str(windowless), _repo_root() / "main.py"


def icon_path() -> Path:
    return get_resource_path("app.ico")


def _command() -> str:
    if is_frozen():
        return f'"{sys.executable}" "%1"'
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
            winreg.SetValueEx(k, None, 0, winreg.REG_SZ, verb_label())
            if os.path.isfile(icon):
                winreg.SetValueEx(k, "Icon", 0, winreg.REG_SZ, icon)
            # ask Explorer to invoke us once with the whole selection
            winreg.SetValueEx(k, "MultiSelectModel", 0, winreg.REG_SZ, "Player")
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key + r"\command") as k:
            winreg.SetValueEx(k, None, 0, winreg.REG_SZ, command)
    log.info("Контекстное меню: зарегистрировано для %d расширений", len(exts))


def update_context_menu_label(exts: list[str]) -> None:
    """Update the context menu verb label for installed extensions to current language."""
    import winreg
    label = verb_label()
    updated = 0
    for ext in exts:
        key = _SHELL_KEY.format(ext=ext, verb=VERB)
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key, 0, winreg.KEY_SET_VALUE) as k:
                winreg.SetValueEx(k, None, 0, winreg.REG_SZ, label)
                updated += 1
        except OSError:
            pass
    if updated:
        log.info("Контекстное меню: обновлена надпись на «%s» для %d расширений", label, updated)


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
    if is_frozen():
        target = exe
        arguments = ""
        work_dir = Path(exe).parent
        icon_loc = str(icon_path()) if icon_path().is_file() else f"{exe},0"
    else:
        target = exe
        arguments = f'\"{script}\"'
        work_dir = script.parent
        icon_loc = str(icon_path())

    ps = (
        "$w = New-Object -ComObject WScript.Shell; "
        f"$s = $w.CreateShortcut('{lnk}'); "
        f"$s.TargetPath = '{target}'; "
        f"$s.Arguments = '{arguments}'; "
        f"$s.WorkingDirectory = '{work_dir}'; "
        f"$s.IconLocation = '{icon_loc}'; "
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
