"""Minimal localhost HTTP server for clipboard copy actions."""

from __future__ import annotations

import json
import re
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote

from cotp_web import package_version
from cotp_web.vault import (
    EntryRefError,
    load_entry_refs,
    load_vault,
    password_plaintext_for_entry,
    resolve_vault_entry,
    summarize_entry_ref,
    totp_code_for_entry,
)

_COPY_PATH = re.compile(r"^/api/copy/(password|otp)/(.+)$")
REPO_URL = "https://github.com/ytensor42/qr-vault-cli"


def format_serving_message(host: str, port: int, *, until_ctrl_c: bool = False) -> str:
    base = f"==> {host}:{port}"
    if until_ctrl_c:
        return f"{base}  until CTRL-C"
    return base


def _html_page(version: str) -> bytes:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>cotp-web v{version}</title>
  <style>
    :root {{ color-scheme: light dark; }}
    body {{
      font-family: system-ui, -apple-system, sans-serif;
      max-width: 42rem;
      margin: 0 auto;
      padding: 0 1rem 1.5rem;
      line-height: 1.4;
    }}
    .sticky-header {{
      position: sticky;
      top: 0;
      z-index: 2;
      margin: 0 -1rem;
      padding: 1.25rem 1rem 0.75rem;
      background: light-dark(#ffffff, #1c1c1e);
      border-bottom: 1px solid color-mix(in srgb, currentColor 14%, transparent);
    }}
    .title-link {{
      display: flex;
      align-items: center;
      gap: 0.45rem;
      margin: 0 0 0.5rem;
      font-size: 1rem;
      font-weight: 600;
      color: inherit;
      text-decoration: none;
      letter-spacing: 0.01em;
      flex-wrap: wrap;
      word-break: break-all;
    }}
    .title-link:hover {{
      color: color-mix(in srgb, currentColor 80%, #0969da);
    }}
    .title-icon {{
      flex-shrink: 0;
      line-height: 0;
    }}
    .title-sep {{
      font-weight: 400;
      color: color-mix(in srgb, currentColor 45%, transparent);
    }}
    .title-url {{
      font-weight: 400;
      font-size: 0.9rem;
      color: color-mix(in srgb, currentColor 65%, transparent);
    }}
    h1#second {{
      font-size: 3rem;
      font-weight: 700;
      margin: 0;
      line-height: 1;
      font-variant-numeric: tabular-nums;
    }}
    .entries-panel {{
      padding-top: 0.5rem;
    }}
    .row {{
      display: grid;
      grid-template-columns: 1fr 3.25rem 3.25rem;
      align-items: center;
      gap: 0.75rem;
      margin: 0 -0.5rem;
      padding: 0.6rem 0.5rem;
      border-bottom: 1px solid color-mix(in srgb, currentColor 12%, transparent);
      border-radius: 0.4rem;
      transition: background-color 0.15s ease;
    }}
    .row.is-hover {{
      background: color-mix(in srgb, #ffeb3b 55%, transparent);
    }}
    @media (prefers-color-scheme: dark) {{
      .row.is-hover {{
        background: color-mix(in srgb, #ffd54f 40%, transparent);
      }}
    }}
    .row.is-copied {{
      animation: copy-flash 0.9s ease-out forwards;
    }}
    @keyframes copy-flash {{
      0% {{ background-color: #5fe89a; }}
      65% {{ background-color: #5fe89a; }}
      100% {{ background-color: transparent; }}
    }}
    .name {{ font-weight: 500; word-break: break-all; min-width: 0; }}
    .btn-slot {{
      width: 3.25rem;
      justify-self: end;
    }}
    button {{
      font: inherit;
      width: 100%;
      box-sizing: border-box;
      padding: 0.35rem 0;
      border-radius: 0.35rem;
      border: 1px solid color-mix(in srgb, currentColor 25%, transparent);
      background: color-mix(in srgb, currentColor 6%, transparent);
      cursor: pointer;
      white-space: nowrap;
    }}
    button:hover {{ background: color-mix(in srgb, currentColor 12%, transparent); }}
    button:disabled {{ opacity: 0.5; cursor: not-allowed; }}
    .msg {{ min-height: 1.25rem; font-size: 0.85rem; color: color-mix(in srgb, currentColor 55%, transparent); }}
    .msg.err {{ color: #c0392b; }}
  </style>
</head>
<body>
  <header class="sticky-header">
    <a class="title-link" href="{REPO_URL}" target="_blank" rel="noopener noreferrer" title="qr-vault-cli on GitHub">
      <span class="title-icon" aria-hidden="true">
        <svg viewBox="0 0 16 16" width="18" height="18">
          <path fill="currentColor" d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.02.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/>
        </svg>
      </span>
      <span>cotp-web v{version}</span>
      <span class="title-sep">|</span>
      <span class="title-url">{REPO_URL}</span>
    </a>
    <h1 id="second" aria-live="polite">00</h1>
  </header>
  <main class="entries-panel">
    <div id="entries"></div>
  </main>
  <p id="status" class="msg" aria-live="polite"></p>
  <script>
    const statusEl = document.getElementById("status");
    const secondEl = document.getElementById("second");

    function updateSecond() {{
      secondEl.textContent = String(new Date().getSeconds()).padStart(2, "0");
    }}

    updateSecond();
    setInterval(updateSecond, 1000);

    function setStatus(text, isError) {{
      statusEl.textContent = text || "";
      statusEl.className = isError ? "msg err" : "msg";
    }}

    function flashCopied(row) {{
      row.classList.remove("is-copied");
      void row.offsetWidth;
      row.classList.add("is-copied");
      row.addEventListener(
        "animationend",
        () => row.classList.remove("is-copied"),
        {{ once: true }}
      );
    }}

    async function copyValue(entryId, kind, button, row) {{
      button.disabled = true;
      setStatus("");
      try {{
        const res = await fetch(
          `/api/copy/${{kind}}/${{encodeURIComponent(entryId)}}`,
          {{ method: "POST" }}
        );
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "copy failed");
        await navigator.clipboard.writeText(data.value);
        flashCopied(row);
        setStatus(kind === "password" ? "Password copied." : "OTP copied.");
      }} catch (err) {{
        setStatus(err.message || String(err), true);
      }} finally {{
        button.disabled = false;
      }}
    }}

    async function loadEntries() {{
      const root = document.getElementById("entries");
      const res = await fetch("/api/entries");
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "failed to load entries");
      root.replaceChildren();
      for (const entry of data.entries) {{
        const row = document.createElement("div");
        row.className = "row";
        row.addEventListener("mouseenter", () => row.classList.add("is-hover"));
        row.addEventListener("mouseleave", () => row.classList.remove("is-hover"));

        const name = document.createElement("div");
        name.className = "name";
        name.textContent = entry.id;

        const pwdBtn = document.createElement("button");
        pwdBtn.type = "button";
        pwdBtn.textContent = "Pwd";
        pwdBtn.addEventListener("click", () => copyValue(entry.id, "password", pwdBtn, row));

        const otpBtn = document.createElement("button");
        otpBtn.type = "button";
        otpBtn.textContent = "OTP";
        otpBtn.addEventListener("click", () => copyValue(entry.id, "otp", otpBtn, row));

        const pwdSlot = document.createElement("div");
        pwdSlot.className = "btn-slot";
        pwdSlot.append(pwdBtn);

        const otpSlot = document.createElement("div");
        otpSlot.className = "btn-slot";
        if (entry.has_otp) {{
          otpSlot.append(otpBtn);
        }}

        row.append(name, pwdSlot, otpSlot);
        root.append(row);
      }}
    }}

    loadEntries().catch((err) => setStatus(err.message || String(err), true));
  </script>
</body>
</html>
""".encode()


class CotpWebHandler(BaseHTTPRequestHandler):
    vault_data: dict[str, Any]
    entry_refs: list[str]
    app_version: str

    def log_message(self, format: str, *args: object) -> None:
        return

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, body: bytes) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/" or self.path.startswith("/?"):
            self._send_html(_html_page(self.app_version))
            return
        if self.path == "/api/entries":
            entries_payload: list[dict[str, str | bool]] = []
            for ref in self.entry_refs:
                try:
                    entries_payload.append(summarize_entry_ref(self.vault_data, ref))
                except EntryRefError as exc:
                    entries_payload.append({"id": ref, "has_otp": False, "error": str(exc)})
            self._send_json(HTTPStatus.OK, {"entries": entries_payload})
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def do_POST(self) -> None:
        match = _COPY_PATH.match(self.path)
        if not match:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return
        kind, raw_id = match.groups()
        entry_ref = unquote(raw_id)
        if entry_ref not in self.entry_refs:
            self._send_json(HTTPStatus.FORBIDDEN, {"error": "entry not listed"})
            return
        try:
            entry = resolve_vault_entry(self.vault_data, entry_ref)
            if kind == "password":
                value = password_plaintext_for_entry(entry)
            else:
                value = totp_code_for_entry(entry)
        except EntryRefError as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        self._send_json(HTTPStatus.OK, {"value": value})

    def do_HEAD(self) -> None:
        if self.path == "/":
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            return
        self.send_response(HTTPStatus.NOT_FOUND)
        self.end_headers()


def make_handler(
    vault_data: dict[str, Any],
    entry_refs: list[str],
    *,
    app_version: str | None = None,
) -> type[CotpWebHandler]:
    class Handler(CotpWebHandler):
        pass

    Handler.vault_data = vault_data
    Handler.entry_refs = entry_refs
    Handler.app_version = app_version or package_version()
    return Handler


def run_server(
    *,
    vault_path: Path,
    entries_path: Path,
    host: str = "127.0.0.1",
    port: int = 8765,
    max_runtime: int | None = None,
    interactive: bool = True,
) -> None:
    vault_data = load_vault(vault_path)
    entry_refs = load_entry_refs(entries_path)
    handler = make_handler(vault_data, entry_refs)
    server = ThreadingHTTPServer((host, port), handler)
    print(format_serving_message(host, port, until_ctrl_c=interactive))
    if max_runtime is not None and max_runtime > 0:

        def stop_after_timeout() -> None:
            server.shutdown()

        threading.Timer(max_runtime, stop_after_timeout).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print()
    finally:
        server.server_close()
