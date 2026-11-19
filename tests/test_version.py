"""Marker for typed package."""


def test_version() -> None:
    from LocustLibrary import __version__

    assert __version__ == "0.1.0"
