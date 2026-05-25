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

vault 항목의 **`labels`** 에는 항상 **키(cluster)·username** 이 들어가고, PNG 파일명이 `QR-<key>-<user>-<label>…` 형식이면 그 뒤 라벨도 합칩니다. **같은 key·username·labels** 로 이미 vault에 항목이 **정확히 하나** 있을 때만 업데이트합니다(일치 항목이 없거나 둘 이상이면 덮어쓰지 않음). 그때 stderr에 **요청한 identity**와 **같은 key / username / labels 겹침** 등으로 관련된 기존 항목을 나열합니다.

```bash
cotp put
cotp put -f QR-tp00-alice-admin.png
cotp put tp00 alice -f /path/to/qr.png      # QR PNG에서 시드 읽어 vault 갱신
cotp put tp00 admin -l test                 # -f 없음: PNG 미사용, 기존 항목 메타(labels/password)만 갱신
cotp put tp00 admin -p                      # -p만: 비밀번호 2회 입력·검증 후 Base64로 vault 저장 (Ctrl+C 중단)
cotp put tp00 admin -p 'Base64문자열'       # vault password 필드에 그대로 저장 (get 클립보드용)
cotp put tp00 admin -l test -f qr.png
cotp tp00 admin -p                          # put 생략 (-f / -p)
```

### `cotp get` — vault에서 TOTP + 비밀번호 클립보드

첫 토큰이 `put` / `get` / `read` / `random` 이 아니고 `-` 로 시작하지 않으면 **`get` 이 생략된 것**으로 봅니다. 예: `cotp tp00 alice` 는 `cotp get tp00 alice` 와 같습니다. 인자 없이 `cotp` 만 실행하면 **`cotp -h`** 와 같이 도움말을 출력합니다.

- stdout 예:

```
Timestamp: hh:mm:ss
Key      : tp00
Username : admin
OTP      : 123456
Labels   : tp00, admin, test
```

(`seed` 가 없으면 **OTP:** 줄은 출력하지 않음)
- vault 항목의 **`password`** 는 **Base64(UTF-8)** 로 저장된 값으로 가정하고, 디코드한 **평문을 클립보드에 복사**합니다. **`-t`** 를 주면 **TOTP만** 클립보드에 넣고 password는 복사하지 않습니다.
- 복사에 성공하면 **stderr** 에 `password is copied to clipboard` 및/또는 `totp value is copied to clipboard` 가 출력됩니다.

```bash
cotp get tp00
cotp get tp00 alice
cotp tp00 admin
cotp tp00 -l test
cotp -l test
cotp get tp00 alice -l test,prod
cotp get tp00 alice -t
```

**`-l` / `--labels`:** KEY·username 없이 라벨만으로도 조회 가능(vault `labels`에 지정한 값이 **모두 포함**되면 매칭). KEY+username과 함께 `-l`을 쓰면 labels **집합이 정확히 일치**해야 합니다. **`-l` 없이** KEY만 있으면 username 무관·해당 키 아래 1건, KEY+username이면 username만 맞으면 됩니다.

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
