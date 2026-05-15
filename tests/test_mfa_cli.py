from __future__ import annotations

import string
from pathlib import Path

import pytest

from cotp_cli.main import main


def test_main_empty_argv_is_get_missing_cluster() -> None:
    """No args → implicit ``get`` → argparse still requires ``cluster``."""
    with pytest.raises(SystemExit):
        main([])


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
    assert out_explicit.strip() == "01:02:03 u 999111"
    assert copies_explicit == ["hunter2"]
    assert "password is copied to clipboard" in err_explicit
    assert "totp value is copied to clipboard" not in err_explicit


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
