# cotp — CLI OTP / QR vault

[![CI](https://github.com/ytensor42/qr-vault-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/ytensor42/qr-vault-cli/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/cotp-cli)](https://pypi.org/project/cotp-cli/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**오픈소스 저장소:** [**qr-vault-cli**](https://github.com/ytensor42/qr-vault-cli) — PyPI 패키지 [**cotp-cli**](https://pypi.org/project/cotp-cli/), CLI **`cotp`**.

짧은 이름 **cotp**(CLI·OTP 류 도구로 쓰기 좋게) — `qr-vault.yaml` 과 PNG QR, TOTP, 랜덤 비밀번호를 다룹니다.

(영문 문서: [README.md](README.md))

## 요구사항

- **Python 3.11 이상**
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

- stdout 기본 (한 줄): `17:49:08 tp00/admin 123456 tp00,admin,test` (`seed` 없으면 OTP 생략)
- **`-w`**: 여러 줄 정렬 (`Timestamp:` / `Key:` / `Username:` / …)
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
cotp get tp00 admin -w
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

## 다른 Mac에서 설치하기

### 1. 사전 준비 (Mac당 한 번)

```bash
brew install zbar
python3 --version   # 3.11 이상
```

Python이 3.11 미만이면: `brew install python@3.12` 후 `python3`가 그 버전을 가리키게 맞춥니다.

### 2. `~/bin`에 설치 (명령 하나)

`install.sh`가 있는 디렉터리에서:

```bash
./install.sh
```

동작 요약:

1. **`~/.local/share/cotp/venv`** 에 전용 venv를 만들고 cotp 설치 (Homebrew Python에 `pip install --user` 하지 않음 → **externally-managed-environment** 회피).
2. **`~/.config/cotp/config.yaml`** 이 없으면 생성.
3. **`~/bin/cotp`** 래퍼 설치 (venv + `COTP_CONFIG`).
4. 설치 폴더 파일(**`install.sh` 포함**) **삭제** — 남는 것: `~/bin/cotp`, 설정, venv.

**대안:** `pipx install cotp-cli` (격리 설치; `brew install pipx` 필요).

**`filename too long`:** 설치 폴더 경로가 길거나 안에 `.venv` 가 있으면 발생할 수 있습니다. `~/cotp-install` 처럼 짧은 경로에서 `./install.sh` 를 실행하거나, PyPI만 쓰려면 `COTP_INSTALL_FROM=pypi ./install.sh`.

**git clone** 안에서는 기본적으로 삭제하지 않습니다. 지우려면 `./install.sh --cleanup`. `install.sh`만 있는 폴더에서는 설치 후 스크립트까지 삭제됩니다.

다른 경로: `INSTALL_BINDIR=/usr/local/bin ./install.sh`

`~/bin`을 `PATH`에 넣은 뒤 `cotp --help`.

### 3. 설정

`install.sh`가 **`~/.config/cotp/config.yaml`** 을 만들며, 이것이 기본 설정입니다 (`cotp`가 `COTP_CONFIG`로 이 경로를 사용).

경로를 바꾸려면 해당 파일을 편집합니다. 다른 파일을 쓰려면 `export COTP_CONFIG=/path/to/config.yaml`.

| install.sh가 넣는 기본값 | |
|--------------------------|--|
| **`vault_path`** | `~/.config/cotp/qr-vault.yaml` |
| **`qr_image_dir`** | `~/Downloads/Screenshots` |

**`vault_path`** 가 있으면 **`put`** 은 PNG 옆이 아니라 **항상 그 파일**에 병합합니다.

### 4. vault 파일 옮기기

프로그램 설치만으로는 **시드·비밀번호가 따라오지 않습니다**. 기존 Mac의 **`qr-vault.yaml`**(또는 config의 `vault_path`)을 새 Mac으로 복사합니다 (AirDrop, `scp`, 암호화 백업 등).

```bash
chmod 600 ~/path/to/qr-vault.yaml
```

비밀번호 관리자보내기와 같이 취급하세요 (시드, Base64 `password` 포함).

### 5. 동작 확인

```bash
cotp --help
cotp get tp00 admin          # 또는: cotp -l your-label
```

stdout에 TOTP가 보이고, 항목에 유효한 Base64 **`password`** 가 있으면 stderr에 `password is copied to clipboard`가 나옵니다 (**`-t`** 는 TOTP만 클립보드).

---

## 개발 (저장소 기여)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
ruff check .
```

## 커뮤니티

- [기여 가이드 (영문)](CONTRIBUTING.md)
- [행동 강령 (영문)](CODE_OF_CONDUCT.md)
- [보안 정책 (영문)](SECURITY.md)
- [변경 이력 (영문)](CHANGELOG.md)
- 라이선스: [MIT](LICENSE)

[`AGENTS.md`](AGENTS.md) 참고.
