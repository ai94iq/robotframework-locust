"""Request log for a load run, written the way RequestsLibrary logs its calls.

A run makes thousands of calls, so the log keeps the first few of each request name and the
failed ones. Secrets in headers and bodies are masked before anything is kept.
"""

import html
import json
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import parse_qsl, urlencode

PER_NAME = 3
MAX_FAILED = 50
_LIMIT = 10000
_MASK = "***"
_SECRET_HEADERS = {"authorization", "proxy-authorization", "cookie", "set-cookie"}
_SECRET_FIELDS = {"password", "client_secret", "access_token", "refresh_token", "id_token", "otp"}


@dataclass
class CallLog:
    """Collects one HTML block per kept call; listens on Locust's request event."""

    entries: list[str] = field(default_factory=list)
    left_out: int = 0
    _seen: dict[str, int] = field(default_factory=dict)
    _failed: int = 0

    def record(self, request_type: str, name: str, response_time: float,
               response: Any = None, exception: Any = None, **_event: Any) -> None:
        if not self._wanted(name, exception is not None):
            self.left_out += 1
            return
        self.entries.append(_block(f"{request_type} {name}", response_time, response, exception))

    def _wanted(self, name: str, failed: bool) -> bool:
        seen = self._seen.get(name, 0)
        self._seen[name] = seen + 1
        if seen < PER_NAME:
            return True
        if failed and self._failed < MAX_FAILED:
            self._failed += 1
            return True
        return False


def _block(call: str, response_time: float, response: Any, exception: Any) -> str:
    status = getattr(response, "status_code", "no response")
    summary = f"{call} {status} {response_time:.0f} ms"
    if exception is not None:
        summary += f" FAILED: {exception}"
    text = _exchange(response) if response is not None else "no HTTP response recorded"
    return (f"<details><summary>{html.escape(summary)}</summary>"
            f"<pre>{html.escape(text)}</pre></details>")


def _exchange(response: Any) -> str:
    request = response.request
    method = str(request.method).upper()
    return "\n".join([
        f"{method} Request : url={request.url}",
        f"path_url={request.path_url}",
        f"headers={mask_headers(request.headers)}",
        f"body={mask_body(request.body)}",
        "",
        f"{method} Response : url={response.url}",
        f"status={response.status_code}, reason={response.reason}",
        f"headers={mask_headers(response.headers)}",
        f"body={mask_body(response.text)}",
    ])


def mask_headers(headers: Any) -> dict[str, str]:
    return {k: _MASK if k.lower() in _SECRET_HEADERS else v for k, v in dict(headers).items()}


def mask_body(body: Any) -> str:
    if not body:
        return ""
    text = body.decode("utf-8", "replace") if isinstance(body, bytes) else str(body)
    text = _masked_json(text) or _masked_form(text) or text
    if len(text) > _LIMIT:
        text = text[:_LIMIT] + f"... (cut at {_LIMIT} characters)"
    return text


def _masked_json(text: str) -> str:
    try:
        data = json.loads(text)
    except ValueError:
        return ""
    return json.dumps(_mask_value(data), ensure_ascii=False)


def _mask_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _MASK if str(k).lower() in _SECRET_FIELDS else _mask_value(v)
                for k, v in value.items()}
    if isinstance(value, list):
        return [_mask_value(item) for item in value]
    return value


def _masked_form(text: str) -> str:
    try:
        pairs = parse_qsl(text, keep_blank_values=True, strict_parsing=True)
    except ValueError:
        return ""
    return urlencode([(k, _MASK if k.lower() in _SECRET_FIELDS else v) for k, v in pairs], safe="*")
