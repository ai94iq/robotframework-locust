"""Proxy from HTTPS_PROXY / HTTP_PROXY and a no_proxy bypass list (Locust sets trust_env off)."""

import pytest
from locust.env import Environment
from requests.utils import select_proxy

from LocustLibrary import LocustLibrary, users
from LocustLibrary.scenario import Scenario

_ENV = ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy", "NO_PROXY", "no_proxy")


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in _ENV:
        monkeypatch.delenv(name, raising=False)


def _proxy(**kwargs: str) -> tuple[str, str]:
    lib = LocustLibrary()
    lib.create_load_test("https://h", allowed_hosts="h", **kwargs)
    assert lib._scenario is not None
    return lib._scenario.proxy, lib._scenario.no_proxy


@pytest.mark.parametrize("name", ["HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy"])
def test_empty_proxy_reads_the_environment(monkeypatch: pytest.MonkeyPatch, name: str) -> None:
    monkeypatch.setenv(name, "http://env:3128")
    assert _proxy()[0] == "http://env:3128"


def test_https_proxy_wins_over_http_proxy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HTTP_PROXY", "http://plain:1")
    monkeypatch.setenv("HTTPS_PROXY", "http://tls:2")
    assert _proxy()[0] == "http://tls:2"


def test_no_proxy_env_joins_when_proxy_came_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HTTPS_PROXY", "http://env:3128")
    monkeypatch.setenv("no_proxy", "inside, other")
    assert _proxy(no_proxy="mine") == ("http://env:3128", "mine,inside,other")


def test_explicit_proxy_ignores_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HTTPS_PROXY", "http://env:3128")
    monkeypatch.setenv("NO_PROXY", "inside")
    assert _proxy(proxy="http://mine:1") == ("http://mine:1", "")


def test_none_turns_the_env_read_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HTTPS_PROXY", "http://env:3128")
    assert _proxy(proxy="NONE") == ("", "")


def test_no_proxy_hosts_go_direct() -> None:
    scenario = Scenario(host="https://h", proxy="http://p:1", no_proxy="inside, Other.Host")
    user = users._user_class(scenario, [])(Environment())
    proxies = user.client.proxies
    assert select_proxy("https://inside/x", proxies) is None
    assert select_proxy("http://other.host:8080/x", proxies) is None
    assert select_proxy("https://h/x", proxies) == "http://p:1"


def test_no_proxy_suffix_and_port_forms_go_direct() -> None:
    scenario = Scenario(host="https://h", proxy="http://p:1", no_proxy=".example.com, inside:8080")
    user = users._user_class(scenario, [])(Environment())

    def proxy(url: str) -> str | None:
        return select_proxy(url, user.client.merge_environment_settings(url, {}, False, True, None)["proxies"])

    assert proxy("https://api.example.com/x") is None
    assert proxy("https://example.com/x") is None
    assert proxy("http://inside:8080/x") is None
    assert proxy("http://inside:9090/x") == "http://p:1"
    assert proxy("https://notexample.com/x") == "http://p:1"


def test_add_user_class_keeps_no_proxy() -> None:
    lib = LocustLibrary()
    lib.create_load_test("https://h", allowed_hosts="h", proxy="http://p:1", no_proxy="inside")
    lib.add_user_class("a")
    assert [s.no_proxy for s in lib._scenarios] == ["inside"]
