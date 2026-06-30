# cotp — CLI OTP / QR vault

[![CI](https://github.com/ytensor42/qr-vault-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/ytensor42/qr-vault-cli/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**저장소:** [**qr-vault-cli**](https://github.com/ytensor42/qr-vault-cli) — **GitHub 소스**로 설치 (아래 참고). CLI 명령: **`cotp`**.

짧은 이름 **cotp** — `qr-vault.yaml`, PNG QR, TOTP, 랜덤 비밀번호를 다룹니다.

(영문 문서: [README.md](README.md))

## 요구사항

- **Python 3.11 이상**
- **zbar** (pyzbar): macOS `brew install zbar` · Debian/Ubuntu `sudo apt install libzbar0`
- **git** (clone 및 GitHub `pip install`용)

## 설정 파일

저장소의 [`config.example.yaml`](config.example.yaml) 참고.

| 위치 | |
|------|--|
| 기본 | `~/.config/cotp/config.yaml`, 또는 `XDG_CONFIG_HOME`이 있으면 `$XDG_CONFIG_HOME/cotp/config.yaml` |
| 덮어쓰기 | 환경 변수 **`COTP_CONFIG`** 에 설정 파일 경로 지정 |

| 키 | 의미 |
|----|------|
| `vault_path` | `qr-vault.yaml` 경로. **`get`** / **`put`** 에서 사용. 미설정 시 둘 다 기본값 `~/.config/cotp/qr-vault.yaml` (또는 `$XDG_CONFIG_HOME/cotp/qr-vault.yaml`)을 사용합니다. |
| `qr_image_dir` | **`put`** / **`read`** 에서 `-f` 생략 시 기본 PNG 폴더. 생략 시 `~/Downloads/Screenshots` |

## 명령

설치 후 **`cotp`** (또는 설치 venv 안에서 `python -m cotp_cli`).

### `cotp put` — QR → 시드 출력 + vault 갱신

vault **`labels`** 에는 **키·username 을 저장하지 않고**, **`-l` / `--labels`로 준 라벨만** 들어갑니다(PNG 파일명 접미사는 라벨로 쓰지 않음). **key·username·labels** 가 vault와 **정확히 1건** 일치할 때만 업데이트합니다.

```bash
cotp put
cotp put -f QR-tp00-alice-admin.png
cotp put tp00 alice -f /path/to/qr.png
cotp put tp00 admin -l test
cotp put tp00 admin -p
cotp put tp00 admin -p 'Base64문자열'
cotp put tp00 admin -l test -f qr.png
cotp tp00 admin -p
```

### `cotp get` — vault에서 TOTP + 비밀번호 클립보드

- stdout 기본 (한 줄): `17:49:08 tp00/admin 123456 test` (labels는 `-l`로 준 값만)
- **`-u` / `--user`**: KEY 없이 vault 전체에서 username 이 일치하는 **모든 엔트리** 출력. positional username 과 동시 사용 불가.
- **와일드카드 `*`**: KEY·username(`-u` 포함)·`-l` 라벨 검색에서 `*` = 임의 문자열(나머지는 리터럴·대소문자 구분). 셸에서 `*` 가 확장되지 않도록 따옴표로 감쌉니다: `cotp 'tc*'`, `cotp -u 'admin*'`, `cotp tc00 -l 'prod*'`. **`get` 검색에만** 적용되고 `put` 은 항상 문자 그대로 처리.

> **주의 (zsh/bash):** 따옴표 없는 `cotp git*` 는 셸이 먼저 확장합니다. zsh 는 매칭되는 파일이 없으면 `zsh: no matches found: git*` 로 중단되어 cotp 가 실행되지 않습니다. 패턴을 따옴표로 감싸거나(`cotp 'git*'`), 이스케이프하거나(`cotp git\*`), `noglob` 으로 실행하세요(`noglob cotp git*`). 매번 따옴표가 번거로우면 셸 rc 에 alias 를 추가합니다:
>
> ```bash
> alias cotp='noglob cotp'
> ```
>
> (alias 는 대화형 셸에만 적용됩니다. 스크립트에서는 따옴표 방식을 권장.)
- **`-w`**: 여러 줄 정렬 (`Timestamp:` / `Key:` / …)
- **`password`**: Base64(UTF-8) 가정 → 평문을 클립보드. **`-t`**: TOTP만 클립보드.

```bash
cotp get tp00
cotp get tp00 alice
cotp tp00 admin
cotp tp00 -l test
cotp -l test
cotp get tp00 alice -l test,prod
cotp get tp00 alice -t
cotp get tp00 admin -w
cotp get -u admin          # 모든 키에서 username admin 매칭
cotp -u admin              # 위와 동일 (암시적 get)
cotp 'tc*'                 # tc* 에 매칭되는 모든 키 (셸에서 * 따옴표 처리)
cotp -u 'admin*'           # admin 으로 시작하는 username
cotp tc00 -l 'prod*'       # prod* 에 매칭되는 라벨
```

### `cotp read` / `cotp random`

```bash
cotp read
cotp read -f ~/Downloads/Screenshots/cap.png
cotp random
```

## 다른 Mac에서 설치하기

**PyPI가 아니라 GitHub**에서 설치합니다. 다른 Mac에 올리기 전에 변경 사항을 **GitHub에 push** 하세요.

### 1. 사전 준비

```bash
brew install zbar git
python3 --version   # 3.11 이상
```

### 2. 권장: `install.sh` (`~/bin/cotp`)

```bash
git clone https://github.com/ytensor42/qr-vault-cli.git
cd qr-vault-cli
./install.sh --preflight    # 선택: 실패 원인만 먼저 확인
./install.sh --no-cleanup   # git clone이면 소스 유지
./install.sh --verify       # 설치 후 검증
```

**성공 시 마지막 줄:** `cotp install: === cotp is installed correctly on this machine ===`

요약:

1. 사전 검사 후 **`~/.config/cotp/config.yaml`** 생성.
2. **`~/.cotp/venv`** + `cotp-cli` (폴더에 `pyproject.toml` 있으면 **로컬 빌드**, 없으면 GitHub).
3. **`~/bin/cotp`** 설치 후 자동 검증.

**다른 Mac:** 이 저장소 폴더를 통째로 복사한 뒤 그 안에서 `./install.sh` 만 실행해도 됩니다 (GitHub 불필요).

**`File name too long`:** `rm -rf ~/.cotp ~/.local/share/cotp` 후 `./install.sh` 재실행.

**git clone** 안에서는 기본적으로 파일을 지우지 않습니다. `./install.sh --cleanup` 으로 clone 제거 가능.

### 3. 수동: GitHub에서 `pip install`

```bash
python3 -m venv ~/.cotp/venv
~/.cotp/venv/bin/pip install -U pip wheel
~/.cotp/venv/bin/pip install "cotp-cli @ git+https://github.com/ytensor42/qr-vault-cli.git"
```

`~/bin/cotp` 래퍼는 `install.sh` 를 참고하세요.

### 4. 설정 · vault

| 기본값 | |
|--------|--|
| **`vault_path`** | `~/.config/cotp/qr-vault.yaml` |
| **`qr_image_dir`** | `~/Downloads/Screenshots` |

기존 Mac의 **`qr-vault.yaml`** 을 새 Mac으로 복사합니다.

```bash
chmod 600 ~/.config/cotp/qr-vault.yaml
```

### 5. 확인

```bash
ls -la ~/bin/cotp ~/.cotp/venv/bin/python
cotp --help
cotp get tp00 admin
```

**`~/.cotp/venv/bin/cotp`만 있고 `~/bin/cotp`가 없을 때** (예: 예전 `unexpected venv python path` 오류 후):

```bash
mkdir -p ~/bin
./install.sh --bin-only
# 또는: export PATH="$HOME/.cotp/venv/bin:$PATH"  (config는 COTP_CONFIG=~/.config/cotp/config.yaml)
```

**`~/bin/cotp`가 없을 때:** 설치가 끝나지 않은 것입니다. `./install.sh --verify` 로 상태 확인. 성공 메시지가 없으면 `./install.sh --preflight` 출력을 보고 `brew install zbar git python@3.12` 후 재시도:

```bash
rm -rf ~/.cotp ~/.local/share/cotp
git pull
./install.sh --no-cleanup
```

다른 경로에 깔렸을 수 있으면: `find "$HOME" -name cotp -type f 2>/dev/null`

---

## 개발

```bash
git clone https://github.com/ytensor42/qr-vault-cli.git
cd qr-vault-cli
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
- [MIT](LICENSE)

[`AGENTS.md`](AGENTS.md) 참고.
