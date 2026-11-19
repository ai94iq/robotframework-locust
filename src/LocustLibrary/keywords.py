"""RF keywords for LocustLibrary."""

from robot.api.deco import keyword


class KeywordsMixin:
    """Mixin providing RF keywords. Wired into LocustLibrary later."""

    @keyword
    def create_load_test(self, host: str) -> None:
        """Create a new load test scenario."""
        raise NotImplementedError
