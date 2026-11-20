"""A run never starts more users than the ceiling, so it cannot flood the host."""

import pytest

import LocustLibrary as lib_module
from LocustLibrary import LocustLibrary
from LocustLibrary.scenario import Stats


@pytest.fixture
def lib(monkeypatch) -> LocustLibrary:
    monkeypatch.setattr(lib_module, "run_load_test", lambda _s, _c: Stats())
    library = LocustLibrary()
    library.create_load_test("http://127.0.0.1")
    return library


def test_users_over_ceiling_are_refused(lib: LocustLibrary) -> None:
    with pytest.raises(ValueError, match="101 users"):
        lib.run_load_test(users=101)


def test_stage_peak_over_ceiling_is_refused(lib: LocustLibrary) -> None:
    lib.set_load_stages("1m:20", "1m:150", "1m:0")
    with pytest.raises(ValueError, match="150 users"):
        lib.run_load_test()


def test_fixed_counts_add_up(lib: LocustLibrary) -> None:
    lib.add_user_class("a", fixed_count=60)
    lib.add_user_class("b", fixed_count=50)
    with pytest.raises(ValueError, match="110 users"):
        lib.run_load_test(users=10)


def test_raised_ceiling_allows_the_run(lib: LocustLibrary) -> None:
    lib.run_load_test(users=150, max_users=200)
    lib.run_load_test(users=100)
