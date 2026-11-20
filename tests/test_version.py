"""Marker for typed package."""


def test_version() -> None:
    from LocustLibrary import __version__

    assert __version__ == "1.0.3"
