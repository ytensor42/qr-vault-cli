import pytest

from cotp_cli import __version__
from cotp_cli.main import main


def test_version() -> None:
    assert __version__ == "0.7.3"


def test_main_version_flag(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["-v"])
    assert exc_info.value.code == 0
    assert capsys.readouterr().out.strip() == f"cotp {__version__}"
