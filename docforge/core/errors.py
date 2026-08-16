"""Human-readable wording for common conversion errors."""
from docforge.i18n import tr


def friendly_error(e: Exception) -> str:
    """Return a readable description of an error for the status line.

    Common cases (no permission, file locked, disk full) get plain wording;
    anything else is passed through as-is.
    """
    if isinstance(e, PermissionError):
        return tr("no write permission — the file may be open in another program ({e})").format(e=e)
    if isinstance(e, FileNotFoundError):
        return tr("file or folder not found ({e})").format(e=e)
    if isinstance(e, OSError):
        # covers "no space left", invalid path and similar
        return tr("file system error ({e})").format(e=e)
    return str(e)
