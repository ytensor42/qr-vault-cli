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
| `vault_path` | `qr-vault.yaml` 경로. **`get`** 에 사용. 설정 시 **`put`** 은 PNG 옆이 아니라 이 파일에 병합합니다. |
| `qr_image_dir` | **`put`** / **`read`** 에서 `-f` 생략 시 기본 PNG 폴더. 생략 시 `~/Downloads/Screenshots` |

## 명령

설치 후 **`cotp`** (또는 설치 venv 안에서 `python -m cotp_cli`).

### `cotp put` — QR → 시드 출력 + vault 갱신

vault **`labels`** 에는 항상 **키·username** 이 포함됩니다. **key·username·labels** 가 vault와 **정확히 1건** 일치할 때만 업데이트합니다.

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

- stdout 기본 (한 줄): `17:49:08 tp00/admin 123456 tp00,admin,test`
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
./install.sh
```

요약:

1. **`~/.cotp/venv`** 생성 후 **GitHub `main`** 에서 `cotp-cli` 설치.
2. **`~/.config/cotp/config.yaml`** 없으면 생성.
3. **`~/bin/cotp`** 설치.
4. 끝나면 clone 폴더 삭제 안내(스크립트 출력 참고).

**이 Mac 작업 트리 그대로** (아직 push 안 한 코드):

```bash
COTP_INSTALL_LOCAL=1 ./install.sh
```

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

**`~/bin/cotp`가 없을 때:** 설치가 중간에 실패한 것입니다. 터미널에 `cotp install: install complete:` 와 `cotp command: /Users/…/bin/cotp` 가 보였는지 확인하세요. `echo $HOME` 이 비어 있으면 안 됩니다. 재시도:

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
