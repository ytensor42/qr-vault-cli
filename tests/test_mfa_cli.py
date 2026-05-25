from __future__ import annotations

import string
from pathlib import Path

import pytest

from cotp_cli.main import main


def test_main_empty_argv_prints_help(capsys: pytest.CaptureFixture[str]) -> None:
    """No args → same as ``-h``."""
    with pytest.raises(SystemExit) as exc_info:
        main([])
    assert exc_info.value.code == 0
    out = capsys.readouterr().out
    assert "usage:" in out
    assert "cotp" in out


def test_main_implicit_get_equivalent_to_get_keyword(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import base64

    import yaml  # noqa: PLC0415

    import cotp_cli.main as vm

    vault = tmp_path / "qr-vault.yaml"
    pw_b64 = base64.b64encode(b"hunter2").decode()
    vault.write_text(
        yaml.safe_dump(
            {
                "tp": {
                    "username": "u",
                    "seed": "JBSWY3DPEHPK3PXP",
                    "password": pw_b64,
                    "labels": ["tp", "u"],
                },
            },
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(vm, "default_vault_path", lambda: vault)
    copies: list[str] = []
    monkeypatch.setattr(vm, "copy_text_to_clipboard", lambda t: copies.append(t))
    monkeypatch.setattr(vm, "totp_parts", lambda _seed: ("01:02:03", "999111"))

    main(["get", "tp"])
    cap_explicit = capsys.readouterr()
    out_explicit = cap_explicit.out
    err_explicit = cap_explicit.err
    copies_explicit = list(copies)

    copies.clear()
    main(["tp"])
    cap_implicit = capsys.readouterr()
    out_implicit = cap_implicit.out
    err_implicit = cap_implicit.err
    copies_implicit = list(copies)

    assert out_explicit == out_implicit
    assert err_explicit == err_implicit
    assert copies_explicit == copies_implicit
    assert out_explicit.strip() == "01:02:03 tp/u/[**pwd**] 999111 tp,u"
    assert copies_explicit == ["hunter2"]
    assert err_explicit == ""


def test_main_implicit_put_dispatches_to_put(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import yaml  # noqa: PLC0415

    import cotp_cli.main as vm

    png = tmp_path / "cap.png"
    png.write_bytes(b"x")
    vault = tmp_path / "qr-vault.yaml"
    monkeypatch.setattr(vm, "extract_seeds_from_png", lambda _p: ["SEEDY"])
    monkeypatch.setattr(vm, "vault_path_for_put", lambda _p: vault)

    main(["lab", "bob", "-f", str(png)])

    data = yaml.safe_load(vault.read_text(encoding="utf-8"))
    assert data["lab"]["username"] == "bob"
    assert data["lab"]["labels"] == ["lab", "bob"]


def test_main_put_interactive_password_b64(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import base64
    import yaml  # noqa: PLC0415

    import cotp_cli.main as vm

    vault = tmp_path / "qr-vault.yaml"
    vault.write_text(
        yaml.safe_dump(
            {
                "hanlab": {
                    "username": "u@example.com",
                    "seed": "SEEDKEEP",
                    "password": "",
                    "labels": ["hanlab", "u@example.com"],
                },
            },
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(vm, "default_vault_path", lambda: vault)
    monkeypatch.setattr(vm, "read_password_interactive_b64", lambda: base64.b64encode(b"newpw").decode())

    main(["put", "hanlab", "u@example.com", "-p"])

    data = yaml.safe_load(vault.read_text(encoding="utf-8"))
    assert data["hanlab"]["seed"] == "SEEDKEEP"
    assert data["hanlab"]["password"] == base64.b64encode(b"newpw").decode()


def test_main_implicit_put_without_file_flag(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import yaml  # noqa: PLC0415

    import cotp_cli.main as vm

    vault = tmp_path / "qr-vault.yaml"
    vault.write_text(
        yaml.safe_dump(
            {
                "tp00": {
                    "username": "admin",
                    "seed": "KEEPSEED",
                    "password": "",
                    "labels": ["tp00", "admin"],
                },
            },
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(vm, "default_vault_path", lambda: vault)
    called: list[object] = []

    def _no_extract(_p: object) -> list[str]:
        called.append(_p)
        return ["SHOULD_NOT_RUN"]

    monkeypatch.setattr(vm, "extract_seeds_from_png", _no_extract)

    main(["put", "tp00", "admin", "-l", "test"])

    assert called == []
    data = yaml.safe_load(vault.read_text(encoding="utf-8"))
    assert data["tp00"]["seed"] == "KEEPSEED"
    assert data["tp00"]["labels"] == ["tp00", "admin", "test"]


def test_main_get_key_and_labels_without_username(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import yaml  # noqa: PLC0415

    import cotp_cli.main as vm

    vault = tmp_path / "qr-vault.yaml"
    vault.write_text(
        yaml.safe_dump(
            {
                "tp00": {
                    "username": "admin",
                    "seed": "JBSWY3DPEHPK3PXP",
                    "labels": ["tp00", "admin", "test"],
                },
            },
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(vm, "default_vault_path", lambda: vault)
    monkeypatch.setattr(vm, "copy_text_to_clipboard", lambda _t: None)
    monkeypatch.setattr(vm, "totp_parts", lambda _seed: ("01:02:03", "999111"))

    main(["tp00", "-l", "test"])

    assert "999111" in capsys.readouterr().out


def test_main_get_accepts_labels_flag(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import yaml  # noqa: PLC0415

    import cotp_cli.main as vm

    vault = tmp_path / "qr-vault.yaml"
    vault.write_text(
        yaml.safe_dump(
            {
                "tp00": {
                    "username": "admin",
                    "seed": "JBSWY3DPEHPK3PXP",
                    "labels": ["tp00", "admin", "test"],
                },
            },
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(vm, "default_vault_path", lambda: vault)
    monkeypatch.setattr(vm, "copy_text_to_clipboard", lambda _t: None)
    monkeypatch.setattr(vm, "totp_parts", lambda _seed: ("01:02:03", "999111"))

    main(["tp00", "admin", "-l", "test"])

    assert "999111" in capsys.readouterr().out


def test_main_put_accepts_labels_flag(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import yaml  # noqa: PLC0415

    import cotp_cli.main as vm

    png = tmp_path / "q.png"
    png.write_bytes(b"x")
    vault = tmp_path / "qr-vault.yaml"
    monkeypatch.setattr(vm, "extract_seeds_from_png", lambda _p: ["S"])
    monkeypatch.setattr(vm, "vault_path_for_put", lambda _p: vault)

    main(["put", "lab", "bob", "-l", "test", "-f", str(png)])

    data = yaml.safe_load(vault.read_text(encoding="utf-8"))
    assert data["lab"]["labels"] == ["lab", "bob", "test"]


def test_main_random_prints_plain_and_base64(capsys: pytest.CaptureFixture[str]) -> None:
    import base64

    main(["random"])
    out = capsys.readouterr().out.strip()
    parts = out.split()
    assert len(parts) == 2
    plain, b64 = parts
    assert len(plain) == 12
    assert any(c in string.ascii_uppercase for c in plain)
    assert any(c in string.ascii_lowercase for c in plain)
    assert any(c in string.digits for c in plain)
    assert base64.standard_b64decode(b64).decode("utf-8") == plain
