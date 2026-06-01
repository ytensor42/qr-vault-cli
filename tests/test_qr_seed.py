from __future__ import annotations

import time
from pathlib import Path

import pytest

from cotp_cli.main import (
    VaultUpdateError,
    argv_for_dispatch,
    build_vault_update_hints,
    decode_vault_password_for_clipboard,
    encode_password_plain_to_vault_b64,
    entry_matches_identity,
    extract_seeds_from_png,
    find_vault_entry_matches,
    format_get_output,
    format_get_output_line,
    format_totp_with_clock,
    labels_for_vault_entry,
    labels_from_csv,
    looks_like_implicit_put,
    merge_qr_vault_yaml,
    NO_MATCH_LINE,
    otpauth_secret,
    parse_qr_filename,
    query_labels_for_get,
    random_password_12,
    read_password_interactive_b64,
    resolve_put_password,
    resolve_png_path,
    run_query,
    run_put_metadata_only,
    run_save_from_png,
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


def test_encode_password_plain_to_vault_b64() -> None:
    import base64

    assert encode_password_plain_to_vault_b64("pw") == base64.standard_b64encode(b"pw").decode("ascii")


def test_resolve_put_password_none_and_literal() -> None:
    assert resolve_put_password(None) is None
    assert resolve_put_password("already-b64") == "already-b64"


def test_read_password_interactive_b64_success(monkeypatch: pytest.MonkeyPatch) -> None:
    import base64

    prompts: list[str] = []

    def fake_getpass(prompt: str = "") -> str:
        prompts.append(prompt)
        return "hunter2"

    monkeypatch.setattr("getpass.getpass", fake_getpass)
    assert read_password_interactive_b64() == base64.standard_b64encode(b"hunter2").decode()
    assert prompts == ["Password: ", "Verify password: "]


def test_read_password_interactive_b64_retries_on_mismatch(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import base64

    answers = iter(["a", "b", "same", "same"])

    monkeypatch.setattr("getpass.getpass", lambda _prompt="": next(answers))
    assert read_password_interactive_b64() == base64.standard_b64encode(b"same").decode()
    assert "passwords do not match" in capsys.readouterr().err


def test_read_password_interactive_b64_ctrl_c_exits_130(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raise_interrupt(_prompt: str = "") -> str:
        raise KeyboardInterrupt

    monkeypatch.setattr("getpass.getpass", raise_interrupt)
    with pytest.raises(SystemExit) as exc:
        read_password_interactive_b64()
    assert exc.value.code == 130


def test_decode_vault_password_for_clipboard() -> None:
    import base64

    assert decode_vault_password_for_clipboard(base64.b64encode(b"pw").decode()) == "pw"
    assert decode_vault_password_for_clipboard("") is None
    bad_utf8_b64 = base64.standard_b64encode(bytes([0xFF])).decode("ascii")
    assert decode_vault_password_for_clipboard(bad_utf8_b64) is None


def test_run_query_clipboard_totp_only_with_t(
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

    run_query("tp", "u", None, totp_to_clipboard=True)

    assert copies == ["999111"]
    cap = capsys.readouterr()
    out = cap.out.strip()
    assert out == format_get_output_line(
        "tp",
        "u",
        {"username": "u", "labels": ["tp", "u"]},
        timestamp="01:02:03",
        otp_code="999111",
        clipboard="totp",
    )
    assert cap.err == ""


def test_run_query_wide_output_multiline(
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
                    "labels": ["tp", "u"],
                },
            },
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(vm, "default_vault_path", lambda: vault)
    monkeypatch.setattr(vm, "copy_text_to_clipboard", lambda _t: None)
    monkeypatch.setattr(vm, "totp_parts", lambda _seed: ("01:02:03", "999111"))

    run_query("tp", "u", None, wide_output=True)

    cap = capsys.readouterr()
    assert cap.out.strip() == format_get_output(
        "tp", "u", {"username": "u", "labels": ["tp", "u"]}, timestamp="01:02:03", otp_code="999111"
    )


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
                    "labels": ["tp", "u"],
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
    assert cap.err == ""
    assert cap.out.strip() == format_get_output_line(
        "tp",
        "u",
        {"username": "u", "labels": ["tp", "u"]},
        timestamp="01:02:03",
        otp_code="999111",
        clipboard="password",
    )


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
                    "labels": ["tp", "u"],
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
    assert cap.err == ""
    assert cap.out.strip() == format_get_output_line(
        "tp",
        "u",
        {"username": "u", "labels": ["tp", "u"]},
        timestamp="01:02:03",
        otp_code="999111",
        clipboard="totp",
    )


def test_run_query_multiple_matches_space_delimited_lines(
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
                    "labels": ["tp00", "admin", "shared"],
                },
                "tp01": {
                    "username": "bob",
                    "seed": "JBSWY3DPEHPK3PXP",
                    "labels": ["tp01", "bob", "shared"],
                },
            },
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(vm, "default_vault_path", lambda: vault)
    copies: list[str] = []
    monkeypatch.setattr(vm, "copy_text_to_clipboard", lambda t: copies.append(t))
    monkeypatch.setattr(vm, "totp_parts", lambda _seed: ("01:02:03", "999111"))

    run_query(None, None, ["shared"], strict_labels=True)

    cap = capsys.readouterr()
    assert copies == []
    assert cap.err == ""
    lines = [ln for ln in cap.out.strip().split("\n") if ln]
    assert len(lines) == 2
    for line in lines:
        labels_field = line.rsplit(" ", 1)[-1]
        assert ", " not in labels_field
        assert labels_field.count(",") >= 1
    assert "tp00/admin" in lines[0]
    assert lines[0] == format_get_output_line(
        "tp00",
        "admin",
        {"username": "admin", "labels": ["tp00", "admin", "shared"]},
        timestamp="01:02:03",
        otp_code="999111",
    )
    assert lines[1] == format_get_output_line(
        "tp01",
        "bob",
        {"username": "bob", "labels": ["tp01", "bob", "shared"]},
        timestamp="01:02:03",
        otp_code="999111",
    )


def test_format_get_output_omits_otp_without_seed() -> None:
    out = format_get_output(
        "tp00",
        "admin",
        {"username": "admin", "seed": "", "labels": ["tp00", "admin"]},
        timestamp="12:00:00",
        otp_code=None,
    )
    assert "OTP:" not in out
    assert "Labels   : tp00, admin" in out


def test_labels_from_csv() -> None:
    assert labels_from_csv("a, b , c") == ["a", "b", "c"]
    assert labels_from_csv("") == []


def test_labels_for_vault_entry_dedupes_and_orders() -> None:
    assert labels_for_vault_entry("tp00", "alice", ["admin", "tp00"]) == [
        "tp00",
        "alice",
        "admin",
    ]


def test_query_labels_for_get_includes_key_username_when_extras_empty() -> None:
    assert query_labels_for_get("tp00", "alice", None) == ["tp00", "alice"]
    assert query_labels_for_get("tp00", "alice", "") == ["tp00", "alice"]
    assert query_labels_for_get("tp00", "alice", "admin,prod") == [
        "tp00",
        "alice",
        "admin",
        "prod",
    ]


def test_run_query_labels_only_subset_match(
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

    run_query("tp00", None, ["test"], strict_labels=True)
    assert "999111" in capsys.readouterr().out

    run_query(None, None, ["test"], strict_labels=True)
    assert "999111" in capsys.readouterr().out


def test_run_query_strict_labels_requires_full_label_set(
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

    run_query("tp00", "admin", None, strict_labels=False)
    assert "999111" in capsys.readouterr().out

    run_query(
        "tp00",
        "admin",
        query_labels_for_get("tp00", "admin", None),
        strict_labels=True,
    )
    assert capsys.readouterr().out.strip() == NO_MATCH_LINE

    run_query(
        "tp00",
        "admin",
        query_labels_for_get("tp00", "admin", "test"),
        strict_labels=True,
    )
    assert "999111" in capsys.readouterr().out


def test_argv_for_dispatch_implicit_put() -> None:
    assert looks_like_implicit_put(["tp00", "alice", "-f", "x.png"])
    assert argv_for_dispatch(["tp00", "alice", "-f", "x.png"]) == [
        "put",
        "tp00",
        "alice",
        "-f",
        "x.png",
    ]
    assert not looks_like_implicit_put(["tp00", "admin", "-l", "test"])
    assert argv_for_dispatch(["tp00", "admin", "-l", "test"]) == [
        "get",
        "tp00",
        "admin",
        "-l",
        "test",
    ]
    assert argv_for_dispatch(["tp00", "alice"]) == ["get", "tp00", "alice"]
    assert not looks_like_implicit_put(["tp00", "-f", "x.png"])
    assert not looks_like_implicit_put(["tp00", "alice", "-t"])


def test_run_save_from_png_explicit_key_user_labels(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import yaml  # noqa: PLC0415

    import cotp_cli.main as vm

    png = tmp_path / "any-name.png"
    png.write_bytes(b"x")
    vault = tmp_path / "qr-vault.yaml"
    monkeypatch.setattr(vm, "extract_seeds_from_png", lambda _p: ["SEEDX"])
    monkeypatch.setattr(vm, "vault_path_for_put", lambda _p: vault)

    run_save_from_png(png, None, cluster="tp00", username="alice")

    data = yaml.safe_load(vault.read_text(encoding="utf-8"))
    assert data["tp00"][0]["seed"] == "SEEDX"
    assert data["tp00"][0]["username"] == "alice"
    assert data["tp00"][0]["labels"] == ["tp00", "alice"]


def test_run_put_metadata_only_updates_labels_preserves_seed(
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
                    "seed": "SEEDKEEP",
                    "password": "old",
                    "labels": ["tp00", "admin"],
                },
            },
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(vm, "default_vault_path", lambda: vault)

    run_put_metadata_only(None, cluster="tp00", username="admin", labels_csv="test")

    data = yaml.safe_load(vault.read_text(encoding="utf-8"))
    assert data["tp00"][0]["seed"] == "SEEDKEEP"
    assert data["tp00"][0]["labels"] == ["tp00", "admin", "test"]
    assert data["tp00"][0]["password"] == "old"


def test_run_put_metadata_only_requires_key_user(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        run_save_from_png(None, None)
    assert exc.value.code == 1
    assert "without -f requires KEY and username" in capsys.readouterr().err


def test_run_save_from_png_cli_labels(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import yaml  # noqa: PLC0415

    import cotp_cli.main as vm

    png = tmp_path / "any.png"
    png.write_bytes(b"x")
    vault = tmp_path / "qr-vault.yaml"
    monkeypatch.setattr(vm, "extract_seeds_from_png", lambda _p: ["SEEDZ"])
    monkeypatch.setattr(vm, "vault_path_for_put", lambda _p: vault)

    run_save_from_png(
        png,
        None,
        cluster="tp00",
        username="admin",
        labels_csv="test,prod",
    )

    data = yaml.safe_load(vault.read_text(encoding="utf-8"))
    assert data["tp00"][0]["labels"] == ["tp00", "admin", "test", "prod"]


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
    with pytest.raises(ValueError, match="username"):
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
    labels_alice = labels_for_vault_entry("tp00", "alice", ["admin"])
    merge_qr_vault_yaml(vault, "tp00", "alice", labels_alice, "SEED1", None)
    merge_qr_vault_yaml(vault, "other", "bob", labels_for_vault_entry("other", "bob", ["x", "y"]), "SEED2", "pw2")
    merge_qr_vault_yaml(vault, "tp00", "alice", labels_alice, "SEED3", None)

    data = yaml.safe_load(vault.read_text(encoding="utf-8"))
    assert data["tp00"][0]["seed"] == "SEED3"
    assert data["tp00"][0]["username"] == "alice"
    assert data["tp00"][0]["password"] == ""
    assert data["tp00"][0]["labels"] == labels_alice
    assert data["other"][0]["seed"] == "SEED2"
    assert data["other"][0]["username"] == "bob"
    assert data["other"][0]["password"] == "pw2"


def test_merge_qr_vault_yaml_rejects_label_change(tmp_path: Path) -> None:
    vault = tmp_path / "qr-vault.yaml"
    labels_alice = labels_for_vault_entry("tp00", "alice", ["admin"])
    merge_qr_vault_yaml(vault, "tp00", "alice", labels_alice, "SEED1", None)
    want = labels_for_vault_entry("tp00", "alice", ["admin", "prod"])
    with pytest.raises(VaultUpdateError, match="different labels") as exc:
        merge_qr_vault_yaml(vault, "tp00", "alice", want, "SEED3", None)
    assert "tp00" in exc.value.hints
    assert "alice" in exc.value.hints
    assert "admin" in exc.value.hints


def test_merge_qr_vault_yaml_rejects_ambiguous_matches(tmp_path: Path) -> None:
    import yaml  # noqa: PLC0415

    vault = tmp_path / "qr-vault.yaml"
    labels = labels_for_vault_entry("tp00", "alice", [])
    dup = {"username": "alice", "seed": "A", "password": "", "labels": labels}
    vault.write_text(
        yaml.safe_dump({"tp00": [dup, dict(dup)]}, sort_keys=False),
        encoding="utf-8",
    )
    with pytest.raises(VaultUpdateError, match="2 vault entries match") as exc:
        merge_qr_vault_yaml(vault, "tp00", "alice", labels, "SEED2", None)
    assert "exact matches (2)" in exc.value.hints


def test_build_vault_update_hints_lists_username_and_label_overlap() -> None:
    import yaml  # noqa: PLC0415

    data = yaml.safe_load(
        """
        tp00:
          username: admin
          seed: X
          labels: []
        other:
          username: alice
          seed: Y
          labels: [other, alice, shared]
        """
    )
    want = labels_for_vault_entry("tp00", "alice", ["shared"])
    hints = build_vault_update_hints(data, "tp00", "alice", want, [])
    assert "key='tp00'" in hints
    assert "admin" in hints
    assert "key='other'" in hints
    assert "username matches" in hints
    assert "shared labels" in hints


def test_find_vault_entry_matches_list_slot() -> None:
    labels = labels_for_vault_entry("tp00", "alice", ["admin"])
    data = {
        "tp00": [
            {"username": "bob", "seed": "X", "labels": labels_for_vault_entry("tp00", "bob", [])},
            {"username": "alice", "seed": "Y", "labels": labels},
        ],
    }
    assert find_vault_entry_matches(data, "tp00", "alice", labels) == [("tp00", 1)]
    assert entry_matches_identity(data["tp00"][1], "alice", labels)


def test_merge_qr_vault_yaml_appends_new_username_under_key(tmp_path: Path) -> None:
    import yaml  # noqa: PLC0415

    vault = tmp_path / "qr-vault.yaml"
    labels_u = labels_for_vault_entry("handemo", "han.cho@goteleport.com", ["internal"])
    merge_qr_vault_yaml(vault, "handemo", "han.cho@goteleport.com", labels_u, "SEED1", "pw1")
    labels_admin = labels_for_vault_entry("handemo", "admin", ["internal"])
    merge_qr_vault_yaml(vault, "handemo", "admin", labels_admin, "SEED2", "pw2")

    data = yaml.safe_load(vault.read_text(encoding="utf-8"))
    assert len(data["handemo"]) == 2
    assert data["handemo"][0]["username"] == "han.cho@goteleport.com"
    assert data["handemo"][0]["seed"] == "SEED1"
    assert data["handemo"][1]["username"] == "admin"
    assert data["handemo"][1]["seed"] == "SEED2"


def test_merge_qr_vault_yaml_password_preserve_and_override(tmp_path: Path) -> None:
    import yaml  # noqa: PLC0415

    vault = tmp_path / "qr-vault.yaml"
    labels = labels_for_vault_entry("c", "u", [])
    merge_qr_vault_yaml(vault, "c", "u", labels, "S1", "secret1")
    merge_qr_vault_yaml(vault, "c", "u2", labels_for_vault_entry("c", "u2", ["l"]), "S2", None)
    data = yaml.safe_load(vault.read_text())
    assert len(data["c"]) == 2
    assert data["c"][0]["password"] == "secret1"
    assert data["c"][1]["username"] == "u2"
    merge_qr_vault_yaml(vault, "c", "u", labels, "S3", "newpw")
    assert yaml.safe_load(vault.read_text())["c"][0]["password"] == "newpw"


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
