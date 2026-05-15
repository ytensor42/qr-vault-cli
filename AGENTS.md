# AGENTS.md — **qr-vault-cli** / **cotp-cli** (`otp`)

이 파일은 **에이전트가 이 저장소를 다시 열었을 때** 빠르게 맥락을 잡도록 쓴다. 사용자용 설치·명령 예시는 [`README.md`](README.md) (영문), [`README-ko.md`](README-ko.md) (한글). 예시 설정 스켈레톤은 [`config.example.yaml`](config.example.yaml).

---

## 한 줄 요약

**GitHub:** https://github.com/ytensor42/qr-vault-cli · **PyPI** **`cotp-cli`** · 로컬 폴더명 **`otp`** (역사적) · import **`cotp_cli`** · 콘솔 **`cotp`** (`python -m cotp_cli`). QR PNG에서 otpauth 시드를 읽고, **`qr-vault.yaml`** vault와 **TOTP `get`**, **`random`** 을 다룬다.

---

## 오픈소스 레이아웃

| 경로 | 역할 |
|------|------|
| `LICENSE` | MIT |
| `CONTRIBUTING.md` | 기여·로컬 개발·PR 체크리스트 |
| `CODE_OF_CONDUCT.md` | Contributor Covenant |
| `SECURITY.md` | 취약점 신고 안내 |
| `CHANGELOG.md` | 사용자 대상 변경 요약 |
| `.github/workflows/ci.yml` | Ubuntu, Python 3.11–3.13, `ruff` + `pytest` |
| `.github/dependabot.yml` | Actions / pip 의존성 점검 |
| `.github/ISSUE_TEMPLATE/` | 버그·기능 요청 폼 |
| `.github/pull_request_template.md` | PR 본문 템플릿 |

배지·`pyproject.toml` `[project.urls]`·`CHANGELOG` 링크: **`ytensor42/qr-vault-cli`**.

---

## 디렉터리·엔트리

| 경로 | 역할 |
|------|------|
| `cotp_cli/main.py` | argparse, `put` / `get` / `read` / `random`, `run_query`, `run_save_from_png`, 경로·vault 로직 대부분 |
| `cotp_cli/config.py` | 선택 YAML 설정 로드 (`COTP_CONFIG`, XDG 기본 경로), `vault_path_for_put` |
| `tests/` | `pytest`; vault·클립보드는 `monkeypatch`로 고립 |
| `pyproject.toml` | 패키지 메타, `[project.scripts] cotp = cotp_cli.main:main` |

---

## CLI 동작 (에이전트용 체크리스트)

### 서브커맨드 생략 → 암시적 `get`

- `argv_for_dispatch` (`main.py`): 첫 토큰이 `put` / `get` / `read` / `random` 이 **아니고** `-` 로 시작하지 않으면 앞에 **`get`** 을 붙인다.
- 인자 없음 `cotp` → `get` 만 남음 → `cluster` 필수라 **argparse가 실패**한다.

### `put`

- PNG: `resolve_png_path` — 기본은 **`qr_image_dir`** (설정) 또는 `~/Downloads/Screenshots` 에서 최신 `.png`; `-f` 는 절대 경로 또는 위 디렉터리 기준 상대.
- vault 갱신 대상: 설정에 **`vault_path`** 가 있으면 **그 파일**에 merge; 없으면 **`PNG 부모 디렉터리/qr-vault.yaml`** (`vault_path_for_put`).
- 파일명이 `QR-<cluster>-<user>-<labels...>.png` 패턴이 아니면 vault 스킵(경고만).

### `get`

- **stdout 한 줄:** `HH:MM:SS <username> <6자리 TOTP>`.
  - CLI에 `username` 이 있으면 그 값( strip ); 없으면 vault entry 의 `first_username_from_entry`.
- **클립보드:** `password` 필드는 **표준 Base64(UTF-8)** 로 가정 → 디코드 평문 복사. **`-t`** 이면 TOTP 코드도 복사(클립보드 **마지막** 값이 TOTP).
- **stderr 안내(복사 성공 시만):** `password is copied to clipboard`, `totp value is copied to clipboard` (문구 고정, 영문).
- 파이프/스크립트는 **stdout만** 파싱하는 전제가 맞다.

### `read` / `random`

- `read`: vault 없이 PNG에서 시드만 stdout.
- `random`: `secrets` 기반 12자 + 한 줄에 `<plain> <base64>`.

---

## 설정 파일 (`cotp_cli/config.py`)

| 항목 | 내용 |
|------|------|
| 기본 경로 | `~/.config/cotp/config.yaml` 또는 `$XDG_CONFIG_HOME/cotp/config.yaml` |
| 덮어쓰기 | 환경 변수 **`COTP_CONFIG`** → 해당 YAML 경로 |
| **`vault_path`** | `get` 이 읽는 vault; 설정 시 **`put`** 도 이 파일에 merge |
| **`qr_image_dir`** | `put`/`read` 의 기본 PNG 폴더 및 상대 `-f` 기준 (미설정 시 `~/Downloads/Screenshots`) |

YAML 깨짐·잘못된 타입은 stderr 경고 후 **기본 경로 동작**으로 폴백.

---

## 구현·의존성

- **의존성:** Pillow, pyzbar, PyYAML, pyotp, `secrets`, 표준 `argparse`.
- **시스템:** pyzbar는 **zbar** 공유 라이브러리 필요(macOS `brew install zbar` 등).
- **클립보드:** `copy_text_to_clipboard` — macOS `pbcopy`, Linux `wl-copy` / `xclip` / `xsel`.

---

## 테스트·수정 시 주의

- 시드·비밀번호·TOTP를 **테스트 출력·로그·PR 본문**에 넣지 않는다.
- `tests/test_qr_seed.py`, `tests/test_mfa_cli.py`, `tests/test_config.py` 등에서 `default_vault_path`, `totp_parts`, `copy_text_to_clipboard` 를 **`monkeypatch`** 하는 패턴이 많다.
- 버전 문자열은 **`pyproject.toml`**, **`cotp_cli/__init__.py`**, **`tests/test_version.py`** 세 곳을 맞춘다.

---

## 에이전트에게 (불변 원칙)

- 시드·비밀번호·TOTP를 의도하지 않은 로그에 남기지 않는다.
- 동작 변경 시 **README(영/한)·CHANGELOG·이 AGENTS** 의 CLI/출력 설명을 함께 갱신하는 것이 좋다.
