"""Distributed spawn stays on loopback."""

from LocustLibrary import distributed


def test_master_listens_on_loopback(tmp_path, monkeypatch) -> None:
    locustfile = tmp_path / "locustfile.py"
    locustfile.write_text("user_classes = []\n", encoding="utf-8")
    seen: list[tuple[list[str], dict[str, object]]] = []

    def capture(argv: list[str], **kwargs: object) -> None:
        seen.append((argv, kwargs))

    monkeypatch.setattr(distributed.subprocess, "Popen", capture)
    distributed.run_distributed(str(locustfile), processes=1, master_port=5557)
    (master, master_kwargs), (worker, worker_kwargs) = seen
    assert master_kwargs == {}
    assert worker_kwargs == {}
    assert master[master.index("--master-bind-host") + 1] == "127.0.0.1"
    assert master[master.index("--web-host") + 1] == "127.0.0.1"
    assert worker[worker.index("--master-host") + 1] == "127.0.0.1"
    assert "--web-host" not in worker
