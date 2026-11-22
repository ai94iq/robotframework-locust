"""Start Locust Web and Run Distributed check the host and the user count."""

import pytest

from LocustLibrary import LocustLibrary, distributed, webui


class _Proc:
    def poll(self) -> int | None:
        return 0


def _locustfile(tmp_path) -> str:
    path = tmp_path / "locustfile.py"
    path.write_text("x = 1\n", encoding="utf-8")
    return str(path)


@pytest.fixture
def argvs(monkeypatch) -> list[list[str]]:
    seen: list[list[str]] = []

    def popen(argv: list[str], **_unused: object) -> _Proc:
        seen.append(argv)
        return _Proc()

    monkeypatch.setattr(distributed.subprocess, "Popen", popen)
    assert webui.subprocess is distributed.subprocess
    monkeypatch.delenv("LOCUSTLIBRARY_ALLOWED_HOSTS", raising=False)
    return seen


def test_web_refuses_host_outside_list(tmp_path, argvs) -> None:
    with pytest.raises(ValueError, match="not in the allowed hosts"):
        LocustLibrary().start_locust_web(_locustfile(tmp_path), host="http://evil.test",
                                         allowed_hosts="good.test")
    assert argvs == []


def test_web_passes_allowed_host(tmp_path, argvs) -> None:
    LocustLibrary().start_locust_web(_locustfile(tmp_path), host="http://good.test",
                                     allowed_hosts="good.test")
    assert argvs[0][-2:] == ["--host", "http://good.test"]


def test_distributed_reads_env_list(tmp_path, argvs, monkeypatch) -> None:
    monkeypatch.setenv("LOCUSTLIBRARY_ALLOWED_HOSTS", "good.test")
    with pytest.raises(ValueError, match="not in the allowed hosts"):
        LocustLibrary().run_distributed(_locustfile(tmp_path), processes=1,
                                        host="http://evil.test")
    assert argvs == []


def test_distributed_refuses_users_over_ceiling(tmp_path, argvs) -> None:
    with pytest.raises(ValueError, match="over max_users=100"):
        LocustLibrary().run_distributed(_locustfile(tmp_path), processes=1, users=101)
    assert argvs == []


def test_distributed_passes_host_and_users(tmp_path, argvs, monkeypatch) -> None:
    monkeypatch.setattr("LocustLibrary.logger.warn", lambda _msg: None)
    LocustLibrary().run_distributed(_locustfile(tmp_path), processes=1, users=150,
                                    max_users=200, host="http://good.test")
    assert argvs[0][-5:] == ["--host", "http://good.test", "--users", "150", "--autostart"]
    assert "--host" not in argvs[1]
