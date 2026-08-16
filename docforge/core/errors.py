"""Human-readable wording for common conversion errors."""


def friendly_error(e: Exception) -> str:
    """Return a readable description of an error for the status line.

    Common cases (no permission, file locked, disk full) get plain wording;
    anything else is passed through as-is.
    """
    if isinstance(e, PermissionError):
        return f"нет прав на запись — возможно, файл открыт в другой программе ({e})"
    if isinstance(e, FileNotFoundError):
        return f"файл или папка не найдены ({e})"
    if isinstance(e, OSError):
        # covers "no space left", invalid path and similar
        return f"ошибка файловой системы ({e})"
    return str(e)
