"""Saved Pandoc setting sets: a few built-ins plus whatever the user stores."""
import logging
from dataclasses import asdict, dataclass, fields

from docforge import settings
from docforge.i18n import tr

log = logging.getLogger(__name__)

_KEY = "pandoc/presets"


@dataclass
class Preset:
    """Everything the Pandoc tab remembers under one name."""
    format: str = "md"            # output extension
    toc: bool = False
    number_sections: bool = False
    highlight: str = ""           # value from HIGHLIGHT_STYLES
    engine: str = "chromium"
    margin: str = "2cm"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Preset":
        """Build from stored data, ignoring unknown or missing keys."""
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})


# Shipped with the app; these cannot be overwritten or deleted
BUILTIN: dict[str, Preset] = {
    "Print-ready — PDF, 2 cm margins": Preset(
        format="pdf", engine="chromium", margin="2cm"
    ),
    "Word document — with a table of contents": Preset(
        format="docx", toc=True, number_sections=True
    ),
    "For an LLM — Markdown": Preset(format="md"),
}


def user_presets() -> dict[str, Preset]:
    data = settings.get_json(_KEY, {})
    if not isinstance(data, dict):
        return {}
    result: dict[str, Preset] = {}
    for name, raw in data.items():
        if isinstance(raw, dict):
            try:
                result[name] = Preset.from_dict(raw)
            except TypeError:
                log.warning("Пресет «%s» повреждён и пропущен", name)
    return result


def all_presets() -> dict[str, Preset]:
    """Built-ins first, then the user's own."""
    return {**BUILTIN, **user_presets()}


def is_builtin(name: str) -> bool:
    return name in BUILTIN


def save(name: str, preset: Preset) -> None:
    """Store a user preset. Built-in names are refused."""
    name = name.strip()
    if not name:
        raise ValueError(tr("A preset name cannot be empty"))
    if is_builtin(name):
        raise ValueError(tr("«{name}» is a built-in preset, choose another name").format(name=name))
    data = {n: p.to_dict() for n, p in user_presets().items()}
    data[name] = preset.to_dict()
    settings.put_json(_KEY, data)
    log.info("Пресет сохранён: %s", name)


def delete(name: str) -> None:
    """Remove a user preset. Built-ins are refused."""
    if is_builtin(name):
        raise ValueError(tr("«{name}» is a built-in preset and cannot be deleted").format(name=name))
    data = {n: p.to_dict() for n, p in user_presets().items() if n != name}
    settings.put_json(_KEY, data)
    log.info("Пресет удалён: %s", name)
