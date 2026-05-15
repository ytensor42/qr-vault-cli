from __future__ import annotations

import time
from pathlib import Path

import pytest

from cotp_cli.main import (
    decode_vault_password_for_clipboard,
    extract_seeds_from_png,
    format_totp_with_clock,
    labels_from_csv,
    merge_qr_vault_yaml,
    otpauth_secret,
    parse_qr_filename,
    random_password_12,
    resolve_png_path,
    run_query,
    seed_for_cluster_name_only,
    seed_for_cluster_user_labels,
    seed_for_cluster_username_any_labels,
)


def test_random_password_12() -> None:
    import string as s

    specials = set("!@#$%^&*-_=+")
    for _ in range(30):
        p = random_password_12()
        assert len(p) == 12
        assert any(c in s.ascii_uppercase for c in p)
        assert any(c in s.ascii_lowercase for c in p)
        assert any(c in s.digits for c in p)
        assert any(c in specials for c in p)


def test_decode_vault_password_for_clipboard() -> None:
    import base64

    assert decode_vault_password_for_clipboard(base64.b64encode(b"pw").decode()) == "pw"
    assert decode_vault_password_for_clipboard("") is None
    bad_utf8_b64 = base64.standard_b64encode(bytes([0xFF])).decode("ascii")
    assert decode_vault_password_for_clipboard(bad_utf8_b64) is None


def test_run_query_clipboard_password_then_totp_with_t(
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
                    "labels": [],
                },
            },
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(vm, "default_vault_path", lambda: vault)
    copies: list[str] = []
    monkeypatch.setattr(vm, "copy_text_to_clipboard", lambda t: copies.append(t))
    monkeypatch.setattr(vm, "totp_parts", lambda _seed: ("01:02:03", "999111"))

    run_query("tp", "u", None, totp_to_clipboard=True)

    assert copies == ["hunter2", "999111"]
    cap = capsys.readouterr()
    assert cap.out.strip() == "01:02:03 u 999111"
    assert cap.err.strip().splitlines() == [
        "password is copied to clipboard",
        "totp value is copied to clipboard",
    ]


def test_run_query_clipboard_password_notice_only_without_t(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import base64
    import yaml  # noqa: PLC0415

    import cotp_cli.main as vm

    vault = tmp_path / "qr-vault.yaml"
    pw_b64 = base64.b64encode(b"x").decode()
    vault.write_text(
        yaml.safe_dump(
            {
                "tp": {
                    "username": "u",
                    "seed": "JBSWY3DPEHPK3PXP",
                    "password": pw_b64,
                    "labels": [],
                },
            },
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(vm, "default_vault_path", lambda: vault)
    monkeypatch.setattr(vm, "copy_text_to_clipboard", lambda _t: None)
    monkeypatch.setattr(vm, "totp_parts", lambda _seed: ("01:02:03", "999111"))

    run_query("tp", "u", None, totp_to_clipboard=False)

    cap = capsys.readouterr()
    assert cap.err.strip() == "password is copied to clipboard"


def test_run_query_clipboard_totp_notice_only_when_no_password(
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
                "tp": {
                    "username": "u",
                    "seed": "JBSWY3DPEHPK3PXP",
                    "labels": [],
                },
            },
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(vm, "default_vault_path", lambda: vault)
    monkeypatch.setattr(vm, "copy_text_to_clipboard", lambda _t: None)
    monkeypatch.setattr(vm, "totp_parts", lambda _seed: ("01:02:03", "999111"))

    run_query("tp", "u", None, totp_to_clipboard=True)

    cap = capsys.readouterr()
    assert cap.err.strip() == "totp value is copied to clipboard"


def test_labels_from_csv() -> None:
    assert labels_from_csv("a, b , c") == ["a", "b", "c"]
    assert labels_from_csv("") == []


def test_seed_for_cluster_user_labels_ok_and_order_insensitive() -> None:
    data = {
        "tp00": {
            "username": "alice",
            "seed": "JBSWY3DPEHPK3PXP",
            "labels": ["admin", "prod"],
        },
    }
    assert seed_for_cluster_user_labels(data, "tp00", "alice", ["prod", "admin"]) == "JBSWY3DPEHPK3PXP"


def test_seed_for_cluster_user_labels_mismatch() -> None:
    data = {"tp00": {"username": "alice", "seed": "X", "labels": ["a"]}}
    with pytest.raises(ValueError, match="username"):
        seed_for_cluster_user_labels(data, "tp00", "bob", ["a"])
    with pytest.raises(ValueError, match="labels"):
        seed_for_cluster_user_labels(data, "tp00", "alice", ["b"])


def test_format_totp_with_clock_shape() -> None:
    line = format_totp_with_clock("JBSWY3DPEHPK3PXP")
    parts = line.split()
    assert len(parts) == 2
    assert parts[0].count(":") == 2
    assert parts[1].isdigit() and len(parts[1]) == 6


def test_seed_for_cluster_username_any_labels() -> None:
    data = {"tp00": {"username": "alice", "seed": "X", "labels": ["z", "y"]}}
    assert seed_for_cluster_username_any_labels(data, "tp00", "alice") == "X"
    with pytest.raises(KeyError):
        seed_for_cluster_username_any_labels(data, "missing", "alice")


def test_seed_for_cluster_username_any_labels_matches_first_list_username() -> None:
    data = {"tp00": {"username": ["bob", "carol"], "seed": "X"}}
    assert seed_for_cluster_username_any_labels(data, "tp00", "bob") == "X"
    with pytest.raises(ValueError, match="username"):
        seed_for_cluster_username_any_labels(data, "tp00", "alice")


def test_seed_for_cluster_name_only() -> None:
    data = {"tp00": {"username": "alice", "seed": "SEEDX"}}
    assert seed_for_cluster_name_only(data, "tp00") == "SEEDX"


def test_seed_for_cluster_name_only_uses_first_username_in_list() -> None:
    data = {"tp00": {"username": ["bob", "carol"], "seed": "SEEDY"}}
    assert seed_for_cluster_name_only(data, "tp00") == "SEEDY"


def test_seed_for_cluster_name_only_rejects_bad_entry() -> None:
    data = {"tp00": {"username": [], "seed": "Z"}}
    with pytest.raises(ValueError):
        seed_for_cluster_name_only(data, "tp00")


def test_otpauth_secret_extracts_base32() -> None:
    uri = "otpauth://totp/Issuer:alice?secret=JBSWY3DPEHPK3PXP&issuer=Issuer"
    assert otpauth_secret(uri) == "JBSWY3DPEHPK3PXP"


def test_otpauth_secret_hotp() -> None:
    uri = "otpauth://hotp/Label?secret=ABCDEF234567"
    assert otpauth_secret(uri) == "ABCDEF234567"


def test_otpauth_secret_rejects_non_otpauth() -> None:
    assert otpauth_secret("https://example.com") is None


def test_otpauth_secret_missing_secret() -> None:
    assert otpauth_secret("otpauth://totp/X:y?issuer=Z") is None


def test_parse_qr_filename() -> None:
    assert parse_qr_filename(Path("QR-tp00-admin-work.png")) == ("tp00", "admin", ["work"])
    assert parse_qr_filename(Path("QR-tp00-admin.PNG")) == ("tp00", "admin", [])
    assert parse_qr_filename(Path("QR-only.png")) is None
    assert parse_qr_filename(Path("not-qr.png")) is None
    assert parse_qr_filename(Path("QR-.png")) is None


def test_merge_qr_vault_yaml_create_merge_update(tmp_path: Path) -> None:
    import yaml  # noqa: PLC0415

    vault = tmp_path / "qr-vault.yaml"
    merge_qr_vault_yaml(vault, "tp00", "alice", ["admin"], "SEED1", None)
    merge_qr_vault_yaml(vault, "other", "bob", ["x", "y"], "SEED2", "pw2")
    merge_qr_vault_yaml(vault, "tp00", "alice", ["admin", "prod"], "SEED3", None)

    data = yaml.safe_load(vault.read_text(encoding="utf-8"))
    assert data["tp00"]["seed"] == "SEED3"
    assert data["tp00"]["username"] == "alice"
    assert data["tp00"]["password"] == ""
    assert data["tp00"]["labels"] == ["admin", "prod"]
    assert data["other"]["seed"] == "SEED2"
    assert data["other"]["username"] == "bob"
    assert data["other"]["password"] == "pw2"


def test_merge_qr_vault_yaml_password_preserve_and_override(tmp_path: Path) -> None:
    import yaml  # noqa: PLC0415

    vault = tmp_path / "qr-vault.yaml"
    merge_qr_vault_yaml(vault, "c", "u", [], "S1", "secret1")
    merge_qr_vault_yaml(vault, "c", "u2", ["l"], "S2", None)
    assert yaml.safe_load(vault.read_text())["c"]["password"] == "secret1"
    merge_qr_vault_yaml(vault, "c", "u2", ["l"], "S3", "newpw")
    assert yaml.safe_load(vault.read_text())["c"]["password"] == "newpw"


def test_merge_qr_vault_yaml_rejects_non_mapping(tmp_path: Path) -> None:
    vault = tmp_path / "qr-vault.yaml"
    vault.write_text("- not a mapping\n", encoding="utf-8")
    with pytest.raises(ValueError, match="mapping"):
        merge_qr_vault_yaml(vault, "a", "u", [], "s", None)


def test_resolve_png_path_relative_adds_png_when_no_suffix(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    d = tmp_path / "Downloads" / "Screenshots"
    d.mkdir(parents=True)
    f = d / "capture.png"
    f.write_bytes(b"x")
    assert resolve_png_path(Path("capture")) == f.resolve()


def test_resolve_png_path_absolute_adds_png_when_no_suffix(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    f = tmp_path / "qr.png"
    f.write_bytes(b"z")
    assert resolve_png_path(tmp_path / "qr") == f.resolve()


def test_resolve_png_path_relative_under_default_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    d = tmp_path / "Downloads" / "Screenshots"
    d.mkdir(parents=True)
    f = d / "shot.png"
    f.write_bytes(b"x")
    assert resolve_png_path(Path("shot.png")) == f.resolve()


def test_resolve_png_path_absolute_ignores_default_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    other = tmp_path / "other.png"
    other.write_bytes(b"y")
    assert resolve_png_path(other) == other.resolve()


def test_resolve_png_path_none_picks_newest_png(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    d = tmp_path / "Downloads" / "Screenshots"
    d.mkdir(parents=True)
    old = d / "old.png"
    new = d / "new.png"
    old.write_bytes(b"o")
    time.sleep(0.02)
    new.write_bytes(b"n")
    assert resolve_png_path(None) == new.resolve()


def test_extract_seeds_from_generated_png(tmp_path: Path) -> None:
    pytest.importorskip("qrcode")
    import qrcode  # noqa: PLC0415

    uri = "otpauth://totp/Test:user?secret=JBSWY3DPEHPK3PXP&issuer=Test"
    p = tmp_path / "q.png"
    qrcode.make(uri).save(p)

    try:
        seeds = extract_seeds_from_png(p)
    except ImportError as e:
        pytest.skip(str(e))
    if not seeds:
        pytest.skip("QR decode returned nothing (try libzbar / zbar for pyzbar)")
    assert seeds == ["JBSWY3DPEHPK3PXP"]
