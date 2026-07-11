"""Minimal localhost HTTP server for clipboard copy actions."""

from __future__ import annotations

import json
import re
import threading
from functools import cache
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote, urlparse

from PIL import Image

from cotp_web import package_version
from cotp_web.vault import (
    EntryRefError,
    load_entry_refs,
    load_vault,
    parse_entry_ref,
    password_plaintext_for_entry,
    resolve_vault_entry,
    summarize_entry_ref,
    totp_code_for_entry,
    username_for_entry,
)

_COPY_PATH = re.compile(r"^/api/copy/(password|otp|username)/(.+)$")
REPO_URL = "https://github.com/ytensor42/qr-vault-cli"


@cache
def favicon_png() -> bytes:
    return files("cotp_web").joinpath("favicon-32.png").read_bytes()


@cache
def favicon_ico() -> bytes:
    image = Image.open(BytesIO(favicon_png()))
    buffer = BytesIO()
    image.save(buffer, format="ICO", sizes=[(32, 32)])
    return buffer.getvalue()


def favicon_href(version: str, *, ico: bool = False) -> str:
    name = "favicon.ico" if ico else "favicon-32.png"
    return f"/{name}?v={quote(version, safe='')}"


def format_serving_message(host: str, port: int, *, until_ctrl_c: bool = False) -> str:
    base = f"==> {host}:{port}"
    if until_ctrl_c:
        return f"{base}  until CTRL-C"
    return base


def _html_page(
    version: str,
    *,
    max_runtime: int | None = None,
    started_at: float | None = None,
) -> bytes:
    max_runtime_js = "null" if max_runtime is None else str(max_runtime)
    started_at_js = "null" if started_at is None else str(int(started_at * 1000))
    countdown_markup = (
        '<span id="countdown" class="mode-timer">00:00:00</span>'
        if max_runtime is not None and max_runtime > 0
        else '<span id="countdown" class="mode-fg">FG</span>'
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>cotp-web v{version}</title>
  <link rel="icon" href="{favicon_href(version)}" type="image/png" sizes="32x32">
  <link rel="shortcut icon" href="{favicon_href(version, ico=True)}" type="image/x-icon">
  <link rel="apple-touch-icon" href="{favicon_href(version)}">
  <style>
    :root {{ color-scheme: light dark; }}
    body {{
      font-family: system-ui, -apple-system, sans-serif;
      max-width: 29.5rem;
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
    .status-bar {{
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      width: 100%;
      font-size: 3rem;
      font-weight: 700;
      margin: 0;
      line-height: 1;
      font-variant-numeric: tabular-nums;
    }}
    #second {{
      min-width: 2.5ch;
      color: #28a745;
      transition: color 0.35s ease;
    }}
    #countdown {{
      font-variant-numeric: tabular-nums;
    }}
    #countdown.mode-fg,
    #countdown.mode-timer {{
      color: light-dark(#2563eb, #60a5fa);
    }}
    #countdown.mode-fg,
    #countdown.mode-expired {{
      font-variant-numeric: normal;
    }}
    #countdown.mode-expired {{
      color: light-dark(#dc2626, #f87171);
    }}
    .entries-panel {{
      padding-top: 0.5rem;
      overflow-x: auto;
    }}
    .entries-table {{
      width: 100%;
      border-collapse: collapse;
      table-layout: fixed;
    }}
    .entries-table col.col-account {{ width: 3.5rem; }}
    .entries-table col.col-user {{ width: 4.55rem; }}
    .entries-table col.col-pwd {{ width: 1.93rem; }}
    .entries-table col.col-otp {{ width: 1.93rem; }}
    .entries-table th {{
      font-size: 0.72rem;
      font-weight: 600;
      color: color-mix(in srgb, currentColor 55%, transparent);
      text-align: left;
      padding: 0.35rem 0.4rem;
      border-bottom: 1px solid color-mix(in srgb, currentColor 14%, transparent);
    }}
    .entries-table th.col-action {{
      text-align: center;
      padding-left: 0.15rem;
      padding-right: 0.15rem;
    }}
    .entries-table td {{
      padding: 0.4rem 0.35rem;
      vertical-align: middle;
      border-bottom: 1px solid color-mix(in srgb, currentColor 10%, transparent);
    }}
    .entries-table td.col-action {{
      text-align: center;
      padding-left: 0.15rem;
      padding-right: 0.15rem;
    }}
    .entries-table td.col-user {{
      padding-left: 0.35rem;
    }}
    .entries-table tbody tr {{
      transition: background-color 0.15s ease;
    }}
    .entries-table tbody tr.is-hover {{
      background: color-mix(in srgb, #60a5fa 40%, transparent);
    }}
    @media (prefers-color-scheme: dark) {{
      .entries-table tbody tr.is-hover {{
        background: color-mix(in srgb, #3b82f6 35%, transparent);
      }}
    }}
    .col-key {{
      font-weight: 500;
      font-size: 0.85rem;
      color: color-mix(in srgb, currentColor 62%, transparent);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}
    .col-username {{
      font: inherit;
      font-weight: 700;
      font-size: inherit;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      width: 100%;
      max-width: 100%;
      box-sizing: border-box;
      text-align: left;
      padding: 0.35rem 0.4rem 0.35rem 0.55rem;
      border-radius: 0.35rem;
      border: 1px solid light-dark(#fff9c4, #fef08a);
      background: light-dark(#fff9c4, #fef08a);
      color: light-dark(#000000, #1c1c1e);
      cursor: pointer;
      transition: background-color 0.15s ease, border-color 0.15s ease, color 0.15s ease;
    }}
    .col-username:hover {{
      background: light-dark(#fff59d, #fde047);
      border-color: light-dark(#fff59d, #fde047);
    }}
    tr.is-hover .col-username,
    tr.is-hover .col-username:hover {{
      background: light-dark(#fff9c4, #fef08a);
      border-color: light-dark(#fff9c4, #fef08a);
      color: light-dark(#000000, #1c1c1e);
    }}
    .col-username:disabled {{
      opacity: 0.5;
      cursor: not-allowed;
    }}
    .entries-table button.btn-otp {{
      font: inherit;
      width: 100%;
      box-sizing: border-box;
      padding: 0.35rem 0;
      border-radius: 0.35rem;
      border: 1px solid color-mix(in srgb, currentColor 25%, transparent);
      background: color-mix(in srgb, currentColor 6%, transparent);
      cursor: pointer;
      white-space: nowrap;
      font-weight: 600;
      font-size: 0.8rem;
    }}
    button:not(.btn-pwd):not(.btn-otp):not(.col-username):hover {{
      background: color-mix(in srgb, currentColor 12%, transparent);
    }}
    button:disabled {{ opacity: 0.5; cursor: not-allowed; }}
    .entries-table button.btn-pwd {{
      font: inherit;
      width: 100%;
      box-sizing: border-box;
      padding: 0.35rem 0;
      border-radius: 0.35rem;
      cursor: pointer;
      white-space: nowrap;
      font-weight: 600;
      font-size: 0.8rem;
      background: light-dark(#ea580c, #d96655);
      border: 1px solid light-dark(#ea580c, #d96655);
      color: #ffffff;
    }}
    .entries-table button.btn-pwd:hover {{
      background: light-dark(#c2410c, #c45747);
      border-color: light-dark(#c2410c, #c45747);
    }}
    button.btn-otp {{
      color: #ffffff;
      border: 1px solid;
      transition: background-color 0.35s ease, border-color 0.35s ease;
    }}
    button.btn-otp:hover {{
      filter: brightness(1.08);
    }}
    .entries-table button.is-pressed {{
      transition: background-color 0.08s ease, border-color 0.08s ease, color 0.08s ease;
    }}
    .msg {{ min-height: 1.25rem; font-size: 0.85rem; color: color-mix(in srgb, currentColor 55%, transparent); }}
    .msg.err {{ color: #c0392b; }}
    .disclaimer {{
      margin: 1.5rem 0 0;
      font-size: 0.75rem;
      line-height: 1.35;
      color: color-mix(in srgb, currentColor 50%, transparent);
    }}
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
    <h1 class="status-bar" aria-live="polite">
      <span id="second">00</span>{countdown_markup}
    </h1>
  </header>
  <main class="entries-panel">
    <div id="entries"></div>
  </main>
  <p id="status" class="msg" aria-live="polite"></p>
  <p class="disclaimer">Provided &ldquo;as is&rdquo; without warranty. Authors accept no liability for use.</p>
  <script>
    const statusEl = document.getElementById("status");
    const secondEl = document.getElementById("second");
    const countdownEl = document.getElementById("countdown");
    const maxRuntime = {max_runtime_js};
    const startedAt = {started_at_js};
    const otpButtons = [];

    function formatCountdown(totalSec) {{
      const h = Math.floor(totalSec / 3600);
      const m = Math.floor((totalSec % 3600) / 60);
      const s = totalSec % 60;
      return `${{String(h).padStart(2, "0")}}:${{String(m).padStart(2, "0")}}:${{String(s).padStart(2, "0")}}`;
    }}

    function updateCountdown() {{
      if (!countdownEl) {{
        return;
      }}
      if (maxRuntime === null || startedAt === null) {{
        countdownEl.textContent = "FG";
        countdownEl.className = "mode-fg";
        return;
      }}
      const elapsed = Math.floor((Date.now() - startedAt) / 1000);
      const remaining = Math.max(0, maxRuntime - elapsed);
      if (remaining === 0) {{
        countdownEl.textContent = "Expired";
        countdownEl.className = "mode-expired";
        return;
      }}
      countdownEl.textContent = formatCountdown(remaining);
      countdownEl.className = "mode-timer";
    }}

    function colorForSecond(sec) {{
      const green = [40, 167, 69];
      const red = [239, 68, 68];
      if (sec < 50) {{
        return `rgb(${{green.join(",")}})`;
      }}
      const t = (sec - 50) / 9;
      const mix = (from, to) => Math.round(from + (to - from) * t);
      return `rgb(${{mix(green[0], red[0])}}, ${{mix(green[1], red[1])}}, ${{mix(green[2], red[2])}})`;
    }}

    function colorForOtpButton(sec) {{
      const green = [40, 167, 69];
      const white = [255, 255, 255];
      if (sec < 50) {{
        return {{ bg: `rgb(${{green.join(",")}})`, fg: "#ffffff" }};
      }}
      const t = (sec - 50) / 9;
      const mix = (from, to) => Math.round(from + (to - from) * t);
      const bg = `rgb(${{mix(green[0], white[0])}}, ${{mix(green[1], white[1])}}, ${{mix(green[2], white[2])}})`;
      const fgVal = mix(255, 0);
      return {{ bg, fg: `rgb(${{fgVal}}, ${{fgVal}}, ${{fgVal}})` }};
    }}

    function applyOtpButtonColors(sec) {{
      const {{ bg, fg }} = colorForOtpButton(sec);
      for (const btn of otpButtons) {{
        btn.style.backgroundColor = bg;
        btn.style.borderColor = bg;
        btn.style.color = fg;
      }}
    }}

    function updateSecond() {{
      const sec = new Date().getSeconds();
      secondEl.textContent = String(sec).padStart(2, "0");
      const color = colorForSecond(sec);
      secondEl.style.color = color;
      applyOtpButtonColors(sec);
      updateCountdown();
    }}

    updateSecond();
    setInterval(updateSecond, 1000);
    updateCountdown();

    function setStatus(text, isError) {{
      statusEl.textContent = text || "";
      statusEl.className = isError ? "msg err" : "msg";
    }}

    function flashPressed(button) {{
      const style = getComputedStyle(button);
      const bg = style.backgroundColor;
      const fg = style.color;
      button.classList.add("is-pressed");
      button.style.backgroundColor = fg;
      button.style.borderColor = fg;
      button.style.color = bg;
      window.setTimeout(() => {{
        button.classList.remove("is-pressed");
        button.style.backgroundColor = "";
        button.style.borderColor = "";
        button.style.color = "";
        if (button.classList.contains("btn-otp")) {{
          applyOtpButtonColors(new Date().getSeconds());
        }}
      }}, 280);
    }}

    async function copyValue(entryId, kind, trigger) {{
      flashPressed(trigger);
      trigger.disabled = true;
      setStatus("");
      try {{
        const res = await fetch(
          `/api/copy/${{kind}}/${{encodeURIComponent(entryId)}}`,
          {{ method: "POST" }}
        );
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "copy failed");
        await navigator.clipboard.writeText(data.value);
        const labels = {{
          password: "Password copied.",
          otp: "OTP copied.",
          username: "Username copied.",
        }};
        setStatus(labels[kind] || "Copied.");
      }} catch (err) {{
        setStatus(err.message || String(err), true);
      }} finally {{
        trigger.disabled = false;
      }}
    }}

    async function loadEntries() {{
      const root = document.getElementById("entries");
      const res = await fetch("/api/entries");
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "failed to load entries");
      root.replaceChildren();
      otpButtons.length = 0;

      if (!data.entries.length) {{
        const empty = document.createElement("p");
        empty.className = "msg";
        empty.textContent = "No entries.";
        root.append(empty);
        return;
      }}

      const table = document.createElement("table");
      table.className = "entries-table";
      const colgroup = document.createElement("colgroup");
      for (const name of ["col-account", "col-user", "col-pwd", "col-otp"]) {{
        const col = document.createElement("col");
        col.className = name;
        colgroup.append(col);
      }}
      table.append(colgroup);

      const tbody = document.createElement("tbody");
      for (const entry of data.entries) {{
        const row = document.createElement("tr");
        row.addEventListener("mouseenter", () => row.classList.add("is-hover"));
        row.addEventListener("mouseleave", () => row.classList.remove("is-hover"));

        const keyCell = document.createElement("td");
        keyCell.className = "col-key";
        const keyText = entry.key ?? entry.id.split(".")[0] ?? "";
        keyCell.textContent = keyText;
        keyCell.title = keyText;

        const userCell = document.createElement("td");
        userCell.className = "col-user";
        const userBtn = document.createElement("button");
        userBtn.type = "button";
        userBtn.className = "col-username";
        const userText = entry.username ?? entry.id.split(".").slice(1).join(".") ?? "";
        userBtn.textContent = userText;
        userBtn.title = userText;
        userBtn.addEventListener("click", () => copyValue(entry.id, "username", userBtn));
        userCell.append(userBtn);

        const pwdCell = document.createElement("td");
        pwdCell.className = "col-action";
        const pwdBtn = document.createElement("button");
        pwdBtn.type = "button";
        pwdBtn.className = "btn-pwd";
        pwdBtn.textContent = "Pwd";
        pwdBtn.addEventListener("click", () => copyValue(entry.id, "password", pwdBtn));
        pwdCell.append(pwdBtn);

        const otpCell = document.createElement("td");
        otpCell.className = "col-action";
        if (entry.has_otp) {{
          const otpBtn = document.createElement("button");
          otpBtn.type = "button";
          otpBtn.className = "btn-otp";
          otpBtn.textContent = "OTP";
          otpBtn.addEventListener("click", () => copyValue(entry.id, "otp", otpBtn));
          otpCell.append(otpBtn);
          otpButtons.push(otpBtn);
        }}

        row.append(keyCell, userCell, pwdCell, otpCell);
        tbody.append(row);
      }}
      table.append(tbody);
      root.append(table);
      applyOtpButtonColors(new Date().getSeconds());
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
    max_runtime: int | None
    started_at: float | None

    def log_message(self, format: str, *args: object) -> None:
        return

    def _path(self) -> str:
        return urlparse(self.path).path

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

    def _send_bytes(self, body: bytes, content_type: str) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = self._path()
        if path == "/favicon-32.png":
            self._send_bytes(favicon_png(), "image/png")
            return
        if path == "/favicon.ico":
            self._send_bytes(favicon_ico(), "image/x-icon")
            return
        if path == "/" or self.path.startswith("/?"):
            self._send_html(
                _html_page(
                    self.app_version,
                    max_runtime=self.max_runtime,
                    started_at=self.started_at,
                )
            )
            return
        if self.path == "/api/entries":
            entries_payload: list[dict[str, str | bool]] = []
            for ref in self.entry_refs:
                try:
                    entries_payload.append(summarize_entry_ref(self.vault_data, ref))
                except EntryRefError as exc:
                    try:
                        key, username = parse_entry_ref(ref)
                    except EntryRefError:
                        key, username = "", ref
                    entries_payload.append(
                        {
                            "id": ref,
                            "key": key,
                            "username": username,
                            "has_otp": False,
                            "error": str(exc),
                        }
                    )
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
            elif kind == "otp":
                value = totp_code_for_entry(entry)
            else:
                value = username_for_entry(entry)
        except EntryRefError as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        self._send_json(HTTPStatus.OK, {"value": value})

    def do_HEAD(self) -> None:
        path = self._path()
        if path == "/favicon-32.png":
            body = favicon_png()
            content_type = "image/png"
        elif path == "/favicon.ico":
            body = favicon_ico()
            content_type = "image/x-icon"
        else:
            body = None
        if body is not None:
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            return
        if path == "/":
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
    max_runtime: int | None = None,
    started_at: float | None = None,
) -> type[CotpWebHandler]:
    class Handler(CotpWebHandler):
        pass

    Handler.vault_data = vault_data
    Handler.entry_refs = entry_refs
    Handler.app_version = app_version or package_version()
    Handler.max_runtime = max_runtime
    Handler.started_at = started_at
    return Handler


def run_server(
    *,
    vault_path: Path,
    entries_path: Path,
    host: str = "127.0.0.1",
    port: int = 8765,
    max_runtime: int | None = None,
    started_at: float | None = None,
    interactive: bool = True,
) -> None:
    vault_data = load_vault(vault_path)
    entry_refs = load_entry_refs(entries_path)
    handler = make_handler(
        vault_data,
        entry_refs,
        max_runtime=max_runtime,
        started_at=started_at,
    )
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
