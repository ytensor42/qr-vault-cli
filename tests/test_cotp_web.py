"""Tests for cotp_web vault resolution and HTTP API."""

from __future__ import annotations

import argparse
import base64
import json
from http.client import HTTPConnection
from pathlib import Path
from threading import Thread
from unittest.mock import patch

import pytest
import yaml

from cotp_web.__main__ import DEFAULT_BACKGROUND_SECONDS, _child_argv
from cotp_web.server import make_handler, run_server
from cotp_web.vault import (
    EntryRefError,
    load_entry_refs,
    parse_entry_ref,
    password_plaintext_for_entry,
    resolve_entries_path,
    resolve_vault_entry,
    totp_code_for_entry,
    username_for_entry,
)


def _sample_vault() -> dict:
    return {
        "test": [
            {
                "seed": "JBSWY3DPEHPK3PXP",
                "username": "admin",
                "password": base64.b64encode(b"admin11admin11").decode(),
                "labels": ["test", "admin"],
            },
        ],
        "github": [
            {
                "seed": "",
                "username": "deepsolo",
                "password": base64.b64encode(b"Dp1solo1@").decode(),
                "labels": ["github", "deepsolo"],
            },
        ],
    }


def test_child_argv_for_background_spawn() -> None:
    args = argparse.Namespace(
        entries="cotp-web.yaml",
        vault=Path("/vault/qr-vault.yaml"),
        host="127.0.0.1",
        port=9000,
    )
    assert _child_argv(args, DEFAULT_BACKGROUND_SECONDS) == [
        "cotp-web.yaml",
        "--foreground",
        "--max-runtime",
        "3600",
        "--vault",
        "/vault/qr-vault.yaml",
        "--port",
        "9000",
    ]


def test_run_server_prints_url_only(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    import yaml  # noqa: PLC0415

    vault = tmp_path / "qr-vault.yaml"
    entries = tmp_path / "entries.yaml"
    vault.write_text("{}", encoding="utf-8")
    entries.write_text(
        yaml.safe_dump({"test": [{"username": "admin"}]}, sort_keys=False),
        encoding="utf-8",
    )

    with patch("cotp_web.server.ThreadingHTTPServer") as mock_http:
        instance = mock_http.return_value
        instance.server_address = ("127.0.0.1", 8765)

        def serve() -> None:
            return None

        instance.serve_forever.side_effect = serve
        run_server(
            vault_path=vault,
            entries_path=entries,
            interactive=True,
        )

    out = capsys.readouterr().out
    assert out.strip() == "==> 127.0.0.1:8765  until CTRL-C"
    assert "vault=" not in out
    assert "entries=" not in out


def test_parse_entry_ref_splits_on_first_dot() -> None:
    assert parse_entry_ref("test.admin") == ("test", "admin")
    assert parse_entry_ref("hanlab.han.cho@example.com") == (
        "hanlab",
        "han.cho@example.com",
    )


def test_load_entry_refs_from_yaml(tmp_path: Path) -> None:
    import yaml  # noqa: PLC0415

    path = tmp_path / "entries.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "test": [{"username": "admin"}, {"username": "alica"}],
                "github": [{"username": "deepsolo"}],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    assert load_entry_refs(path) == ["test.admin", "test.alica", "github.deepsolo"]


def test_load_entry_refs_accepts_single_entry_mapping(tmp_path: Path) -> None:
    import yaml  # noqa: PLC0415

    path = tmp_path / "entries.yaml"
    path.write_text(
        yaml.safe_dump({"github": {"username": "deepsolo"}}, sort_keys=False),
        encoding="utf-8",
    )
    assert load_entry_refs(path) == ["github.deepsolo"]


def test_resolve_entries_path_bare_filename_in_vault_dir(tmp_path: Path) -> None:
    vault_dir = tmp_path / "vault"
    vault_dir.mkdir()
    vault = vault_dir / "qr-vault.yaml"
    vault.write_text("{}", encoding="utf-8")
    entries = vault_dir / "cotp-web.yaml"
    entries.write_text("test:\n- username: admin\n", encoding="utf-8")

    resolved = resolve_entries_path(Path("cotp-web.yaml"), vault, entries_raw="cotp-web.yaml")
    assert resolved == entries.resolve()


def test_resolve_entries_path_prefixed_os_then_vault_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    vault_dir = tmp_path / "vault"
    vault_dir.mkdir()
    vault = vault_dir / "qr-vault.yaml"
    vault.write_text("{}", encoding="utf-8")

    other = tmp_path / "other"
    other.mkdir()
    monkeypatch.chdir(other)

    fallback = vault_dir / "list.yaml"
    fallback.write_text("test:\n- username: admin\n", encoding="utf-8")

    assert resolve_entries_path(Path("list.yaml"), vault, entries_raw="list.yaml") == fallback.resolve()
    assert resolve_entries_path(Path("list.yaml"), vault, entries_raw="./list.yaml") == fallback.resolve()

    explicit = other / "local.yaml"
    explicit.write_text("test:\n- username: admin\n", encoding="utf-8")
    assert (
        resolve_entries_path(Path("local.yaml"), vault, entries_raw="./local.yaml")
        == explicit.resolve()
    )


def test_resolve_vault_entry_and_secrets() -> None:
    data = _sample_vault()
    test_entry = resolve_vault_entry(data, "test.admin")
    assert password_plaintext_for_entry(test_entry) == "admin11admin11"
    assert len(totp_code_for_entry(test_entry)) == 6

    gh_entry = resolve_vault_entry(data, "github.deepsolo")
    assert password_plaintext_for_entry(gh_entry) == "Dp1solo1@"
    assert username_for_entry(test_entry) == "admin"
    assert username_for_entry(gh_entry) == "deepsolo"
    with pytest.raises(EntryRefError, match="no usable seed"):
        totp_code_for_entry(gh_entry)


def test_api_does_not_leak_secrets_in_entries_list(tmp_path: Path) -> None:
    from http.server import ThreadingHTTPServer

    vault = tmp_path / "qr-vault.yaml"
    entries = tmp_path / "entries.yaml"
    vault.write_text(yaml.safe_dump(_sample_vault(), sort_keys=False), encoding="utf-8")
    entries.write_text(
        yaml.safe_dump(
            {"test": [{"username": "admin"}], "github": [{"username": "deepsolo"}]},
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    data = yaml.safe_load(vault.read_text(encoding="utf-8"))
    refs = load_entry_refs(entries)
    handler = make_handler(data, refs)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    port = server.server_address[1]
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        conn = HTTPConnection("127.0.0.1", port, timeout=5)
        conn.request("GET", "/api/entries")
        res = conn.getresponse()
        payload = json.loads(res.read().decode())
        assert res.status == 200
        assert payload == {
            "entries": [
                {"id": "test.admin", "has_otp": True},
                {"id": "github.deepsolo", "has_otp": False},
            ],
        }
        body_text = json.dumps(payload)
        assert "admin11" not in body_text
        assert "JBSWY3DPEHPK3PXP" not in body_text

        conn.request("POST", "/api/copy/password/test.admin")
        res = conn.getresponse()
        pwd_payload = json.loads(res.read().decode())
        assert res.status == 200
        assert pwd_payload["value"] == "admin11admin11"

        conn.request("POST", "/api/copy/username/test.admin")
        res = conn.getresponse()
        user_payload = json.loads(res.read().decode())
        assert res.status == 200
        assert user_payload["value"] == "admin"

        conn.request("POST", "/api/copy/otp/github.deepsolo")
        res = conn.getresponse()
        otp_payload = json.loads(res.read().decode())
        assert res.status == 400
        assert "seed" in otp_payload["error"]
        conn.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
