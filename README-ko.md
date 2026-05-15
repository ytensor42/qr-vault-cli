# cotp — CLI OTP / QR vault

[![CI](https://github.com/ytensor42/qr-vault-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/ytensor42/qr-vault-cli/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/cotp-cli)](https://pypi.org/project/cotp-cli/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**오픈소스 저장소:** [**qr-vault-cli**](https://github.com/ytensor42/qr-vault-cli) — PyPI 패키지 [**cotp-cli**](https://pypi.org/project/cotp-cli/), CLI **`cotp`**.

짧은 이름 **cotp**(CLI·OTP 류 도구로 쓰기 좋게) — `qr-vault.yaml` 과 PNG QR, TOTP, 랜덤 비밀번호를 다룹니다.

(영문 문서: [README.md](README.md))

## 요구사항

- **zbar** (pyzbar): macOS `brew install zbar` · Debian/Ubuntu `sudo apt install libzbar0`

## 설정 파일

저장소의 [`config.example.yaml`](config.example.yaml) 참고.

| 위치 | |
|------|--|
| 기본 | `~/.config/cotp/config.yaml`, 또는 `XDG_CONFIG_HOME`이 있으면 `$XDG_CONFIG_HOME/cotp/config.yaml` |
| 덮어쓰기 | 환경 변수 **`COTP_CONFIG`** 에 설정 파일 경로 지정 |

| 키 | 의미 |
|----|------|
| `vault_path` | `qr-vault.yaml` 경로. **`get`** 에 사용. 설정 시 **`put`** 은 PNG 옆이 아니라 이 파일에 병합합니다. |
| `qr_image_dir` | **`put`** / **`read`** 에서 `-f` 생략 시 기본 PNG 폴더(그 안에서 가장 최근 `.png`), 상대 `-f` 의 기준 디렉터리. 생략 시 `~/Downloads/Screenshots` |

## 명령

배포·설치 이름: **`cotp-cli`** (`pip install cotp-cli` 또는 로컬에서 `pip install -e .`). 실행 파일: **`cotp`**. 모듈 실행: `python -m cotp_cli …`.

### `cotp put` — QR → 시드 출력 + vault 갱신

```bash
cotp put
cotp put -f QR-tp00-alice-admin.png
cotp put -f /path/to/qr.png -p 'your-password'
```

### `cotp get` — vault에서 TOTP + 비밀번호 클립보드

첫 토큰이 `put` / `get` / `read` / `random` 이 아니고 `-` 로 시작하지 않으면 **`get` 이 생략된 것**으로 봅니다. 예: `cotp tp00 alice` 는 `cotp get tp00 alice` 와 같습니다. (`cotp`, `cotp --help` 는 그대로입니다.)

- stdout: **`hh:mm:ss`** + 공백 + **username** + 공백 + **6자리 TOTP**.
- vault 항목의 **`password`** 는 **Base64(UTF-8)** 로 저장된 값으로 가정하고, 디코드한 **평문을 클립보드에 복사**합니다. `-t` 를 주면 **TOTP 코드도** 클립보드에 넣습니다(이때 **마지막에 TOTP**가 남습니다).
- 복사에 성공하면 **stderr** 에 `password is copied to clipboard` 및/또는 `totp value is copied to clipboard` 가 출력됩니다.

```bash
cotp get tp00
cotp get tp00 alice
cotp get tp00 alice admin,prod
cotp get tp00 alice -t
```

- macOS: `pbcopy` · Linux: `wl-copy` / `xclip` / `xsel` 필요.

### `cotp read` — PNG QR에서 시드만 출력 (vault 없음)

```bash
cotp read
cotp read -f ~/Downloads/Screenshots/cap.png
```

### `cotp random` — 12자리 랜덤 비밀번호 (평문 + Base64)

한 줄: **`<plain> <base64>`** — plain은 12자, 뒤는 UTF-8 바이트의 표준 Base64.

```bash
cotp random
```

## 설치·개발

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
ruff check .
```

Git에서 설치:

```bash
pip install "cotp-cli @ git+https://github.com/ytensor42/qr-vault-cli.git"
```

## 커뮤니티

- [기여 가이드 (영문)](CONTRIBUTING.md)
- [행동 강령 (영문)](CODE_OF_CONDUCT.md)
- [보안 정책 (영문)](SECURITY.md)
- [변경 이력 (영문)](CHANGELOG.md)
- 라이선스: [MIT](LICENSE)

[`AGENTS.md`](AGENTS.md) 참고.
