"""The run-time gate that stops a converted suite while hand-port stubs remain."""

import importlib


def check_hand_ports(module_name: str, allow_stubs: bool) -> None:
    """Fail while functions marked __hand_port__ remain in the module, unless allow_stubs is True."""
    module = importlib.import_module(module_name)
    found = sorted(n for n, f in vars(module).items() if getattr(f, "__hand_port__", False) is True)
    if found and not allow_stubs:
        raise AssertionError("hand-port stubs not ported: " + ", ".join(found)
                             + "; set ALLOW_STUBS to True to run anyway")
