"""Find a k6 script's exec functions and the plain HTTP calls inside them.

A function is plain when every statement is an http.<verb> call with a string URL
and literal body and params, a check() or a sleep(). A sleep may name a top-level number constant, or one
read as Number(__ENV.X || n), which counts as its default n. Anything else needs a hand port,
and `reason` says which line stopped the scan.
"""

from dataclasses import dataclass, field, replace
from typing import Any

import tree_sitter_javascript as tsjs
from tree_sitter import Language, Node, Parser

_JS = Language(tsjs.language())
_HTTP = {"get": "GET", "post": "POST", "put": "PUT", "patch": "PATCH", "del": "DELETE"}
_WITH_BODY = {"POST", "PUT", "PATCH"}
_FUNCTIONS = {"function_declaration", "function_expression", "function"}
_Check = tuple[str, int | None]


class _NotPlain(ValueError):
    """The node needs a hand port; the message says why."""


class OptionsConflict(ValueError):
    """Two options k6 refuses together; no k6 inspect can resolve it."""


@dataclass(frozen=True, slots=True)
class HttpCall:
    method: str
    url: str
    endpoint: str = ""
    body: Any = None
    headers: dict[str, str] = field(default_factory=dict)
    expected_status: int | None = None


@dataclass(frozen=True, slots=True)
class ExecFunction:
    name: str
    line: int
    calls: tuple[HttpCall, ...] = ()
    think_s: float = 0.0
    reason: str = ""
    helpers: tuple[tuple[str, int], ...] = ()
    checks: tuple[tuple[str, int], ...] = ()
    sleeps: int = 0

    @property
    def simple(self) -> bool:
        return not self.reason


def scan_source(source: str) -> list[ExecFunction]:
    root = Parser(_JS).parse(source.encode("utf-8")).root_node
    constants = _constants(root)
    found = (_exported(node, constants) for node in root.named_children
             if node.type == "export_statement")
    return [fn for fn in found if fn is not None]


def static_options(source: str) -> dict[str, Any]:
    """`export const options` in the shape k6 inspect gives, when every value is a literal.

    Raises ValueError naming the first option that is computed, so the caller can fall back to k6 inspect.
    """
    root = Parser(_JS).parse(source.encode("utf-8")).root_node
    for node in root.named_children:
        declaration = node.child_by_field_name("declaration") if node.type == "export_statement" else None
        if declaration is None or declaration.type != "lexical_declaration":
            continue
        for declarator in declaration.named_children:
            if _text(declarator.child_by_field_name("name")) != "options":
                continue
            value = declarator.child_by_field_name("value")
            if value is None or value.type != "object":
                raise ValueError("options is not a literal object")
            return _with_default_scenario(_static(value, "options"))
    raise ValueError("no export const options")


def _static(node: Node, path: str) -> Any:
    if node.type == "object":
        found: dict[str, Any] = {}
        for pair in (c for c in node.named_children if c.type != "comment"):
            key = pair.child_by_field_name("key")
            if pair.type != "pair" or key is None or key.type not in ("property_identifier", "string"):
                raise ValueError(f"{path} has a key that is not a plain name")
            name = _text(key).strip("'\"")
            found[name] = _static(pair.child_by_field_name("value") or pair, f"{path}.{name}")
        return found
    if node.type == "array":
        items = [c for c in node.named_children if c.type != "comment"]
        return [_static(item, f"{path}[{i}]") for i, item in enumerate(items)]
    try:
        return _literal(node)
    except _NotPlain:
        raise ValueError(f"{path} is not a literal") from None


def _refuse_with(shortcut: str, data: dict[str, Any], others: tuple[str, ...]) -> None:
    for other in others:
        if other == "stages" and data.get("stages") or other == "scenarios" and data.get("scenarios") is not None:
            raise OptionsConflict(f"using `{shortcut}` and `{other}` options simultaneously is not allowed")


def _with_default_scenario(data: dict[str, Any]) -> dict[str, Any]:
    """k6 turns top-level vus, iterations, duration and stages into one scenario named default.

    The order and conflicts follow k6's DeriveScenariosFromShortcuts. k6's no-option default is
    per-vu-iterations with 1 VU and 1 iteration; shared-iterations 1/1 here gives the same load.
    """
    stages, vus = data.get("stages"), data.get("vus", 1)
    if "iterations" in data:
        _refuse_with("iterations", data, ("stages", "scenarios"))
        scenario = {"executor": "shared-iterations", "vus": vus, "iterations": data["iterations"]}
        if "duration" in data:
            scenario["maxDuration"] = data["duration"]
    elif "duration" in data:
        _refuse_with("duration", data, ("stages", "scenarios"))
        scenario = {"executor": "constant-vus", "vus": vus, "duration": data["duration"]}
    elif stages:
        _refuse_with("stages", data, ("scenarios",))
        scenario = {"executor": "ramping-vus", "startVUs": vus, "stages": stages}
    elif "vus" in data and stages is None:
        scenario = {"executor": "shared-iterations", "vus": vus, "iterations": vus}
    elif data.get("scenarios"):
        return data
    else:
        scenario = {"executor": "shared-iterations", "vus": 1, "iterations": 1}
    return {**data, "scenarios": {"default": scenario}}


def _constants(root: Node) -> dict[str, float]:
    values: dict[str, float] = {}
    for node in root.named_children:
        if node.type == "lexical_declaration":
            values.update(_declared_numbers(node))
    return values


def _declared_numbers(declaration: Node) -> dict[str, float]:
    values: dict[str, float] = {}
    for declarator in declaration.named_children:
        name = declarator.child_by_field_name("name")
        number = _number(declarator.child_by_field_name("value"))
        if name is not None and number is not None:
            values[_text(name)] = number
    return values


def _number(node: Node | None) -> float | None:
    if node is not None and node.type == "call_expression" and _text(
        node.child_by_field_name("function")
    ) in ("Number", "parseFloat", "parseInt"):
        args = node.child_by_field_name("arguments")
        node = args.named_children[0] if args and args.named_children else None
    if node is not None and node.type == "binary_expression" and _text(
        node.child_by_field_name("left")
    ).startswith("__ENV."):
        node = node.child_by_field_name("right")
    return _js_number(_text(node)) if node is not None and node.type == "number" else None


def _exported(node: Node, constants: dict[str, float]) -> ExecFunction | None:
    function = next((c for c in node.named_children if c.type in _FUNCTIONS), None)
    if function is None:
        return None
    name_node = function.child_by_field_name("name")
    is_default = any(c.type == "default" for c in node.children)
    name = "default" if is_default or name_node is None else _text(name_node)
    return _scan_body(name, function, constants)


def _scan_body(name: str, function: Node, constants: dict[str, float]) -> ExecFunction:
    body = function.child_by_field_name("body")
    statements = body.named_children if body else []
    calls: list[HttpCall] = []
    helpers: list[tuple[str, int]] = []
    checks: list[tuple[str, int]] = []
    think_s, reason, sleeps = 0.0, "", 0
    open_call = False
    for statement in statements:
        try:
            found = _statement(statement, constants)
        except _NotPlain as err:
            reason = reason or f"line {statement.start_point.row + 1}: {err}"
            continue
        line = statement.start_point.row + 1
        if isinstance(found, list):
            for label, status in found:
                if status is None or not open_call or calls[-1].expected_status is not None:
                    checks.append((label, line))
                else:
                    calls[-1] = replace(calls[-1], expected_status=status)
        elif isinstance(found, str):
            helpers.append((found, line))
            open_call = False
        elif isinstance(found, HttpCall):
            calls.append(found)
            open_call = True
        elif isinstance(found, float):
            think_s, sleeps = found, sleeps + 1
    return ExecFunction(name, function.start_point.row + 1, tuple(calls), think_s, reason,
                        tuple(helpers), tuple(checks), sleeps)


def _statement(statement: Node,
               constants: dict[str, float]) -> HttpCall | float | str | list[_Check]:
    expr = _expression(statement)
    if expr is None or expr.type != "call_expression":
        raise _NotPlain(statement.type if expr is None else f"{_text(expr)} is not a call")
    callee = _text(expr.child_by_field_name("function"))
    args_node = expr.child_by_field_name("arguments")
    args = args_node.named_children if args_node else []
    if callee == "sleep" and args:
        return _think(args[0], constants)
    if callee == "check":
        return _checks(args)
    verb = callee.removeprefix("http.")
    if callee.startswith("http.") and verb in _HTTP and args:
        return _http_call(_HTTP[verb], args)
    function = expr.child_by_field_name("function")
    if function is not None and function.type == "identifier" and not args:
        # A local helper call: the report lists it; the calls around it still convert.
        return callee
    shown = _text(expr) if function is not None and function.type == "identifier" else f"{callee}()"
    raise _NotPlain(f"{shown} is not an HTTP call, check or sleep")


def _checks(args: list[Node]) -> list[_Check]:
    """Each named check with its status when it is a plain r.status === N, else None."""
    if len(args) < 2 or args[1].type != "object":
        return [("check", None)]
    found: list[_Check] = []
    for pair in args[1].named_children:
        key = pair.child_by_field_name("key")
        name = _text(key if key is not None else pair).strip("'\"`")
        found.append((name, _status(pair.child_by_field_name("value"))))
    return found


def _status(fn: Node | None) -> int | None:
    body = fn.child_by_field_name("body") if fn is not None else None
    if body is None or body.type != "binary_expression":
        return None
    op = _text(body.child_by_field_name("operator"))
    left, right = body.child_by_field_name("left"), body.child_by_field_name("right")
    if op not in ("===", "==") or right is None or right.type != "number" \
            or left is None or left.type != "member_expression":
        return None
    target = left.child_by_field_name("object")
    if _text(left.child_by_field_name("property")) != "status" or target is None \
            or fn is None or _text(target) != _parameter(fn):
        return None
    value = _js_number(_text(right))
    return int(value) if value is not None and value.is_integer() else None


def _parameter(fn: Node) -> str:
    """The name of an arrow callback's single parameter, as in (r) => or r =>."""
    single = fn.child_by_field_name("parameter")
    if single is not None:
        return _text(single)
    params = fn.child_by_field_name("parameters")
    names = params.named_children if params is not None else []
    return _text(names[0]) if len(names) == 1 and names[0].type == "identifier" else ""


def _js_number(text: str) -> float | None:
    """A JS number literal as a float: decimal, exponent, 0x, 0o, 0b and _ separators; else None."""
    try:
        return float(int(text, 0)) if text[:2].lower() in ("0x", "0o", "0b") else float(text)
    except ValueError:
        return None


def _think(node: Node, constants: dict[str, float]) -> float:
    if node.type == "identifier" and _text(node) in constants:
        return constants[_text(node)]
    return float(_literal(node))


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
        value = _js_number(_text(node))
        if value is None:
            raise _NotPlain(f"{_text(node)} is not a plain number")
        return int(value) if value.is_integer() and "." not in _text(node) else value
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
