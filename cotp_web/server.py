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
    parse_entry_ref,
    password_plaintext_for_entry,
    resolve_vault_entry,
    summarize_entry_ref,
    totp_code_for_entry,
    username_for_entry,
)

_COPY_PATH = re.compile(r"^/api/copy/(password|otp|username)/(.+)$")
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
      color: #28a745;
      transition: color 0.35s ease;
    }}
    .entries-panel {{
      padding-top: 0.5rem;
    }}
    .row {{
      display: grid;
      grid-template-columns: minmax(0, 0.75fr) minmax(0, 1.25fr) 3.25rem 3.25rem;
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
    .col-key {{
      font-weight: 500;
      font-size: 0.85rem;
      color: color-mix(in srgb, currentColor 62%, transparent);
      word-break: break-all;
      min-width: 0;
    }}
    .col-username {{
      font: inherit;
      font-weight: 700;
      font-size: inherit;
      word-break: break-all;
      min-width: 0;
      width: 100%;
      box-sizing: border-box;
      text-align: left;
      padding: 0.35rem 0.4rem;
      border-radius: 0.35rem;
      border: 1px solid light-dark(#2563eb, #60a5fa);
      background: light-dark(transparent, #2c2c2e);
      color: light-dark(#000000, #f2f2f7);
      cursor: pointer;
      transition: background-color 0.15s ease, border-color 0.15s ease, color 0.15s ease;
    }}
    .col-username:hover {{
      background: light-dark(
        color-mix(in srgb, #2563eb 10%, transparent),
        color-mix(in srgb, #60a5fa 16%, #2c2c2e)
      );
      border-color: light-dark(#1d4ed8, #93c5fd);
    }}
    .row.is-hover .col-username,
    .row.is-hover .col-username:hover {{
      background: light-dark(#ffffff, #1c1c1e);
      color: light-dark(#000000, #f2f2f7);
    }}
    .col-username:disabled {{
      opacity: 0.5;
      cursor: not-allowed;
    }}
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
      font-weight: 600;
      font-size: 0.8rem;
    }}
    button:hover {{ background: color-mix(in srgb, currentColor 12%, transparent); }}
    button:disabled {{ opacity: 0.5; cursor: not-allowed; }}
    button.btn-pwd {{
      background: #ea580c;
      border-color: #ea580c;
      color: #ffffff;
    }}
    button.btn-pwd:hover {{
      background: #c2410c;
      border-color: #c2410c;
    }}
    button.btn-otp {{
      color: #ffffff;
      border: 1px solid;
      transition: background-color 0.35s ease, border-color 0.35s ease;
    }}
    button.btn-otp:hover {{
      filter: brightness(1.08);
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
    <h1 id="second" aria-live="polite">00</h1>
  </header>
  <main class="entries-panel">
    <div id="entries"></div>
  </main>
  <p id="status" class="msg" aria-live="polite"></p>
  <p class="disclaimer">Provided &ldquo;as is&rdquo; without warranty. Authors accept no liability for use.</p>
  <script>
    const statusEl = document.getElementById("status");
    const secondEl = document.getElementById("second");
    const otpButtons = [];

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

    async function copyValue(entryId, kind, trigger, row) {{
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
        flashCopied(row);
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
      for (const entry of data.entries) {{
        const row = document.createElement("div");
        row.className = "row";
        row.addEventListener("mouseenter", () => row.classList.add("is-hover"));
        row.addEventListener("mouseleave", () => row.classList.remove("is-hover"));

        const keyCell = document.createElement("div");
        keyCell.className = "col-key";
        keyCell.textContent = entry.key ?? entry.id.split(".")[0] ?? "";

        const userCell = document.createElement("button");
        userCell.type = "button";
        userCell.className = "col-username";
        userCell.textContent = entry.username ?? entry.id.split(".").slice(1).join(".") ?? "";
        userCell.addEventListener("click", () => copyValue(entry.id, "username", userCell, row));

        const pwdBtn = document.createElement("button");
        pwdBtn.type = "button";
        pwdBtn.className = "btn-pwd";
        pwdBtn.textContent = "Pwd";
        pwdBtn.addEventListener("click", () => copyValue(entry.id, "password", pwdBtn, row));

        const otpBtn = document.createElement("button");
        otpBtn.type = "button";
        otpBtn.className = "btn-otp";
        otpBtn.textContent = "OTP";
        otpBtn.addEventListener("click", () => copyValue(entry.id, "otp", otpBtn, row));

        const pwdSlot = document.createElement("div");
        pwdSlot.className = "btn-slot";
        pwdSlot.append(pwdBtn);

        const otpSlot = document.createElement("div");
        otpSlot.className = "btn-slot";
        if (entry.has_otp) {{
          otpSlot.append(otpBtn);
          otpButtons.push(otpBtn);
        }}

        row.append(keyCell, userCell, pwdSlot, otpSlot);
        root.append(row);
      }}
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
