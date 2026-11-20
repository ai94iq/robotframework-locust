"""Find a k6 script's exec functions and the plain HTTP calls inside them.

A function is plain when every statement is an http.<verb> call with a string URL
and literal body and params, a check() or a sleep(). Anything else needs a hand port,
and `reason` says which line stopped the scan.
"""

from dataclasses import dataclass, field
from typing import Any

import tree_sitter_javascript as tsjs
from tree_sitter import Language, Node, Parser

_JS = Language(tsjs.language())
_HTTP = {"get": "GET", "post": "POST", "put": "PUT", "patch": "PATCH", "del": "DELETE"}
_WITH_BODY = {"POST", "PUT", "PATCH"}
_FUNCTIONS = {"function_declaration", "function_expression", "function"}


class _NotPlain(ValueError):
    """The node needs a hand port; the message says why."""


@dataclass(frozen=True, slots=True)
class HttpCall:
    method: str
    url: str
    endpoint: str = ""
    body: Any = None
    headers: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ExecFunction:
    name: str
    line: int
    calls: tuple[HttpCall, ...] = ()
    think_s: float = 0.0
    reason: str = ""

    @property
    def simple(self) -> bool:
        return not self.reason


def scan_source(source: str) -> list[ExecFunction]:
    root = Parser(_JS).parse(source.encode("utf-8")).root_node
    found = (_exported(node) for node in root.named_children if node.type == "export_statement")
    return [fn for fn in found if fn is not None]


def _exported(node: Node) -> ExecFunction | None:
    function = next((c for c in node.named_children if c.type in _FUNCTIONS), None)
    if function is None:
        return None
    name_node = function.child_by_field_name("name")
    is_default = any(c.type == "default" for c in node.children)
    name = "default" if is_default or name_node is None else _text(name_node)
    body = function.child_by_field_name("body")
    return _scan_body(name, function.start_point.row + 1, body.named_children if body else [])


def _scan_body(name: str, line: int, statements: list[Node]) -> ExecFunction:
    calls: list[HttpCall] = []
    think_s, reason = 0.0, ""
    for statement in statements:
        try:
            found = _statement(statement)
        except _NotPlain as err:
            reason = reason or f"line {statement.start_point.row + 1}: {err}"
            continue
        if isinstance(found, HttpCall):
            calls.append(found)
        elif isinstance(found, float):
            think_s = found
    return ExecFunction(name, line, tuple(calls), think_s, reason)


def _statement(statement: Node) -> HttpCall | float | None:
    expr = _expression(statement)
    if expr is None or expr.type != "call_expression":
        raise _NotPlain(statement.type if expr is None else f"{_text(expr)} is not a call")
    callee = _text(expr.child_by_field_name("function"))
    args_node = expr.child_by_field_name("arguments")
    args = args_node.named_children if args_node else []
    if callee == "sleep" and args:
        return float(_literal(args[0]))
    if callee == "check":
        return None
    verb = callee.removeprefix("http.")
    if callee.startswith("http.") and verb in _HTTP and args:
        return _http_call(_HTTP[verb], args)
    raise _NotPlain(f"{callee}() is not an HTTP call, check or sleep")


def _expression(statement: Node) -> Node | None:
    if statement.type == "expression_statement":
        return statement.named_children[0]
    if statement.type == "lexical_declaration":
        return statement.named_children[0].child_by_field_name("value")
    return None


def _http_call(method: str, args: list[Node]) -> HttpCall:
    if args[0].type != "string":
        raise _NotPlain("URL is not a plain string")
    rest = args[1:]
    body = None
    if method in _WITH_BODY and rest:
        body, rest = _body(rest[0]), rest[1:]
    params = _literal(rest[0]) if rest else {}
    tags = params.get("tags", {})
    endpoint = tags.get("endpoint") or tags.get("name") or ""
    return HttpCall(method, _literal(args[0]), endpoint, body, params.get("headers", {}))


def _body(node: Node) -> Any:
    if node.type == "call_expression" and _text(node.child_by_field_name("function")) == (
        "JSON.stringify"
    ):
        args = node.child_by_field_name("arguments")
        node = args.named_children[0] if args and args.named_children else node
    try:
        return _literal(node)
    except _NotPlain as err:
        raise _NotPlain("body is not a literal") from err


def _literal(node: Node) -> Any:
    kind = node.type
    if kind == "string":
        return _text(node)[1:-1]
    if kind == "number":
        text = _text(node)
        return float(text) if "." in text else int(text)
    if kind in ("true", "false", "null"):
        return {"true": True, "false": False, "null": None}[kind]
    if kind == "array":
        return [_literal(item) for item in node.named_children]
    if kind == "object":
        return dict(_pair(pair) for pair in node.named_children)
    raise _NotPlain(f"{_text(node)} is not a literal")


def _pair(pair: Node) -> tuple[str, Any]:
    key, value = pair.child_by_field_name("key"), pair.child_by_field_name("value")
    if pair.type != "pair" or key is None or value is None:
        raise _NotPlain(f"{_text(pair)} is not a literal pair")
    name = _literal(key) if key.type == "string" else _text(key)
    return name, _literal(value)


def _text(node: Node | None) -> str:
    return node.text.decode("utf-8") if node is not None and node.text is not None else ""
