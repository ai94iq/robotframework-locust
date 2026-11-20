"""Register the bundled Inter and JetBrains Mono faces with Qt."""

from pathlib import Path

from PySide6.QtGui import QFontDatabase

_FONTS = Path(__file__).parent / "fonts"


def load_fonts() -> list[str]:
    """Return the family names Qt took; a file Qt cannot read is skipped, Segoe UI and Consolas fill in."""
    families: set[str] = set()
    for path in sorted(_FONTS.glob("*.ttf")):
        font_id = QFontDatabase.addApplicationFont(str(path))
        if font_id >= 0:
            families.update(QFontDatabase.applicationFontFamilies(font_id))
    return sorted(families)
