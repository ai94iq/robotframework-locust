"""Request log for a load run, written the way RequestsLibrary logs its calls.

A run makes thousands of calls, so the log keeps the first few of each request name and the
failed ones. Secrets in headers and bodies are masked before anything is kept.
"""

import html
import json
import re
import time
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import parse_qsl, unquote_plus, urlencode

PER_NAME = 3
MAX_FAILED = 50
_LIMIT = 10000
_MASK = "***"
_SECRET_HEADERS = {"authorization", "proxy-authorization", "cookie", "set-cookie",
                   "x-api-key", "api-key", "x-auth-token", "x-access-token"}
_SECRET_FIELDS = {"password", "client_secret", "access_token", "refresh_token", "id_token", "otp"}
_PRE = "white-space:pre-wrap;word-break:break-all"
_QUERY = re.compile(r"\?([^\s#'\"<>]*)")


def masked_names(names: str) -> frozenset[str]:
    """The comma-separated extra header and body field names to mask, lower-cased."""
    return frozenset(n.strip().lower() for n in names.split(",") if n.strip())


@dataclass
class CallLog:
    """Collects one HTML block per kept call; listens on Locust's request event."""

    entries: list[str] = field(default_factory=list)
    left_out: int = 0
    masked: frozenset[str] = frozenset()
    _seen: dict[str, int] = field(default_factory=dict)
    _failed: int = 0

    def record(self, request_type: str, name: str, response_time: float,
               response: Any = None, exception: Any = None, start_time: float | None = None,
               **_event: Any) -> None:
        if not self._wanted(name, exception is not None):
            self.left_out += 1
            return
        sent = time.localtime(start_time) if start_time is not None else time.localtime()
        call = f"{time.strftime('%H:%M:%S', sent)} {request_type} {name}"
        self.entries.append(_block(call, response_time, response, exception, self.masked))

    def _wanted(self, name: str, failed: bool) -> bool:
        seen = self._seen.get(name, 0)
        self._seen[name] = seen + 1
        if seen < PER_NAME:
            return True
        if failed and self._failed < MAX_FAILED:
            self._failed += 1
            return True
        return False


def _block(call: str, response_time: float, response: Any, exception: Any,
           extra: frozenset[str] = frozenset()) -> str:
    status = getattr(response, "status_code", "no response")
    summary = f"{call} {status} {response_time:.0f} ms"
    if exception is not None:
        summary += f" FAILED: {exception}"
    summary = mask_text(summary, extra)
    text = _exchange(response, extra) if response is not None else "no HTTP response recorded"
    return (f"<details><summary>{html.escape(summary)}</summary>"
            f'<pre style="{_PRE}">{html.escape(text)}</pre></details>')


def _exchange(response: Any, extra: frozenset[str] = frozenset()) -> str:
    request = response.request
    method = str(request.method).upper()
    return "\n".join([
        f"{method} Request : url={mask_url(request.url, extra)}",
        f"path_url={mask_url(request.path_url, extra)}",
        f"headers={mask_headers(request.headers, extra)}",
        f"body={mask_body(request.body, extra)}",
        "",
        f"{method} Response : url={mask_url(request.url, extra)}",
        f"status={response.status_code}, reason={response.reason}",
        f"headers={mask_headers(response.headers, extra)}",
        f"body={mask_body(response.text, extra)}",
    ])


def mask_headers(headers: Any, extra: frozenset[str] = frozenset()) -> dict[str, str]:
    names = _SECRET_HEADERS | extra
    return {k: _MASK if k.lower() in names else v for k, v in dict(headers).items()}


def mask_url(url: Any, extra: frozenset[str] = frozenset()) -> str:
    return mask_text(str(url), extra)


def mask_text(text: str, extra: frozenset[str] = frozenset()) -> str:
    """Mask secret values in every ?query of the text; bare keys and odd pairs stay as written."""
    names = _SECRET_FIELDS | _SECRET_HEADERS | extra
    return _QUERY.sub(lambda m: "?" + _masked_pairs(m[1], names), text)


def _masked_pairs(query: str, names: frozenset[str] | set[str]) -> str:
    parts = []
    for part in query.split("&"):
        key, sep, _ = part.partition("=")
        parts.append(f"{key}={_MASK}" if sep and unquote_plus(key).lower() in names else part)
    return "&".join(parts)


def mask_body(body: Any, extra: frozenset[str] = frozenset()) -> str:
    if not body:
        return ""
    text = body.decode("utf-8", "replace") if isinstance(body, bytes) else str(body)
    text = _masked_json(text, _SECRET_FIELDS | extra) or _masked_form(text, extra) or text
    if len(text) > _LIMIT:
        text = text[:_LIMIT] + f"... (cut at {_LIMIT} characters)"
    return text


def _masked_json(text: str, names: frozenset[str] | set[str]) -> str:
    try:
        data = json.loads(text)
    except ValueError:
        return ""
    return json.dumps(_mask_value(data, names), ensure_ascii=False)


def _mask_value(value: Any, names: frozenset[str] | set[str]) -> Any:
    if isinstance(value, dict):
        return {k: _MASK if str(k).lower() in names else _mask_value(v, names)
                for k, v in value.items()}
    if isinstance(value, list):
        return [_mask_value(item, names) for item in value]
    return value


def _masked_form(text: str, extra: frozenset[str] = frozenset()) -> str:
    try:
        pairs = parse_qsl(text, keep_blank_values=True, strict_parsing=True)
    except ValueError:
        return ""
    names = _SECRET_FIELDS | _SECRET_HEADERS | extra
    return urlencode([(k, _MASK if k.lower() in names else v) for k, v in pairs], safe="*")
