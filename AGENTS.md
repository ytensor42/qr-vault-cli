# AGENTS.md — **qr-vault-cli** / **cotp-cli** (`cotp`)

이 파일은 **에이전트가 이 저장소를 다시 열었을 때** 빠르게 맥락을 잡도록 쓴다. 사용자용 설치·명령 예시는 [`README.md`](README.md) (영문), [`README-ko.md`](README-ko.md) (한글). 예시 설정 스켈레톤은 [`config.example.yaml`](config.example.yaml).

---

## 한 줄 요약

**GitHub:** https://github.com/ytensor42/qr-vault-cli · 설치: GitHub 소스(`install.sh` / `git+https://…`) · 로컬 **`~/Projects/cotp`** · import **`cotp_cli`** · 콘솔 **`cotp`** (`python -m cotp_cli`). QR PNG에서 otpauth 시드를 읽고, **`qr-vault.yaml`** vault와 **TOTP `get`**, **`random`** 을 다룬다.

---

## 사용자 요구 기능 요약

아래는 대화·이슈에서 **사용자가 명시한 동작 요구**를 모은 것이다. 구현 세부·함수명은 아래 **CLI 동작** 절을 따른다.

### 프로젝트·환경

| 요구 | 구현 상태 |
|------|-----------|
| 로컬 폴더명 **`otp` → `cotp`** (`~/Projects/cotp`) | 반영 |
| 경로 변경 후 **`.venv` 재생성** 및 `pip install -e ".[dev]"` | 반영 |

### `put` — vault 쓰기·갱신

| 요구 | 동작 |
|------|------|
| 저장 시 **`labels`에 key·username 항상 포함** | `labels_for_vault_entry(cluster, username, extra)` |
| 추가 라벨은 **위치 인자가 아니라 `-l` / `--labels`** (콤마 구분) | `put … -l test,prod` |
| **`-p`만** (값 없음) → **대화형** 입력 2회·검증 후 **Base64 저장**; `Ctrl+C` → 종료(130) | `read_password_interactive_b64` |
| **`-p <값>`** → 그 문자열을 vault에 그대로 저장(기존처럼 Base64 문자열 권장) | |
| **`-f` 생략** = PNG 미읽음, **메타데이터만** 갱신(labels/password), **기존 seed 유지** | `run_put_metadata_only`; 신규 키는 seed `""` |
| **`-f` 있을 때만** QR에서 시드 추출·stdout·vault merge | `run_save_from_png` |
| 갱신은 **key + username + labels(집합)** 이 vault와 **정확히 1건** 일치할 때만 | 그 외 **거부** + stderr **hints** (같은 key / username / labels 겹침 등) |
| 암시적 put: **`cotp <key> <username>` + `-f` 또는 `-p`만** (`-l` 단독은 put 아님) | `looks_like_implicit_put` |

### `get` — 조회·출력·클립보드

| 요구 | 동작 |
|------|------|
| **라벨은 위치 인자 없음**, **`-l` / `--labels`만** | `cotp tp00 -l admin`, `cotp -l test` 등 |
| **`-l` 없음** + KEY → 해당 키 1건; KEY+username → username 일치 | `label_mode=none` |
| **`-l` + KEY+username** → vault labels와 **집합 정확 일치** | `label_mode=exact` |
| **`-l`만** 또는 KEY+`-l`(username 생략) → vault labels가 **쿼리 라벨 전부 포함**(부분 집합) | `label_mode=subset` |
| KEY+username 주고 **`-l`에 추가만** 줄 때도 조회용 labels에 **key·username 포함** | `query_labels_for_get` |
| **`-t`** → TOTP만 클립보드, **password 복사 생략** | `totp_to_clipboard` |
| **인자 없음** → 도움말 (`cotp` = `cotp -h`) | `argv_for_dispatch` |
| 암시적 get: 서브커맨드 생략, **`-l` / `-t`로 시작**해도 get | `argv_for_dispatch` |
| **매칭 0건** → `no matched data` | |
| **매칭 1건** → stdout **한 줄** `HH:MM:SS key/username [otp] [labels]` | `format_get_output_line`; **`-w`** 이면 여러 줄 정렬 (`format_get_output`) |
| **매칭 2건 이상** → **엔트리당 한 줄** (동일 한 줄 형식) | 예: `22:39:11 tp00/admin 079724 tp00,admin,test` |
| **클립보드·stderr 복사 안내**는 **1건일 때만**; 다중 매칭 시 stdout만 | |

### 그 외

| 요구 | 동작 |
|------|------|
| `password` vault 필드 → **표준 Base64(UTF-8)** 디코드 후 클립보드 | `decode_vault_password_for_clipboard` |
| 스크립트·파이프는 **stdout만** 파싱 전제 | stderr는 사람용 안내 |

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

- `argv_for_dispatch` (`main.py`): 인자 없음 → **`-h`**. **`<key> <username>`** 뒤에 **`-f` / `-p`** 가 있으면 implicit **`put`**. 그 외 positional → implicit **`get`**. **`-l` / `-t`로 시작**하면 앞에 `get` 삽입. **`-l` 단독은 put이 아님.**

### `put`

- **`-f` 있음:** `resolve_png_path` — QR PNG에서 시드 추출·stdout 출력·vault merge (`match_identity_labels=True`, key+username+labels 일치 1건).
- **`-f` 없음:** `run_put_metadata_only` — PNG·폴더 스캔 없음. **KEY+username 필수**. vault는 `default_vault_path()`. **key+username** 으로 1건 찾아 **labels/password** 만 갱신, **seed 유지**. 신규 키면 seed `""` 로 생성(QR 없는 항목).
- vault 갱신 대상: 설정에 **`vault_path`** 가 있으면 **그 파일**에 merge; 없으면 **`PNG 부모 디렉터리/qr-vault.yaml`** (`vault_path_for_put`). **`get`** 기본 vault: **`~/.config/cotp/qr-vault.yaml`** (config 없을 때).
- **`labels`**: `labels_for_vault_entry` — **cluster(key)·username** 을 항상 포함, PNG 파일명 `QR-…` 파싱 분 + **`put -l` / `--labels`** (콤마 구분) 추가 라벨(중복 제거).
- **업데이트 조건** (`merge_qr_vault_yaml`): vault 키 **`<key>`** 아래에서 **username·labels(집합)** 이 모두 일치하는 엔트리가 **정확히 1개**일 때만 seed/password 갱신. 0개면 키가 비어 있을 때만 신규 생성; 키는 있는데 일치 항목 없으면 덮어쓰지 않고 **`VaultUpdateError`** + stderr **hints**(같은 key / username 일치 / labels 겹침 등 관련 엔트리 목록). 2개 이상 exact match도 hints로 전부 표시.
- **`cotp put <key> <username> [-l …] [-f png]`** — **`-f` 생략** = 메타데이터만(기존 seed 유지). implicit put: **`<key> <username>`** + **`-f` 또는 `-p`**.
- 파일명 패턴·KEY/username 없이 `put -f` 만 쓰면: 파일명이 `QR-<cluster>-<user>-<labels...>.png` 가 아니면 vault 스킵(경고).

### `get`

- **labels 매칭 (`find_get_matches`):** **`-l` 없음** + KEY → 해당 키 1건; **`-l` 없음** + KEY+username → username 일치. **`-l` 있음** + KEY+username → labels **집합 정확히 일치**; **`-l`만**(또는 KEY+`-l`, username 생략) → vault labels가 **`-l` 값 전부 포함**(부분 집합). **0건** → `no matched data`.
- **stdout:** 기본 **한 줄** `HH:MM:SS key/username [otp] [labels]` (`format_get_output_line`). **`-w`** → **1건**일 때만 여러 줄 정렬 (`format_get_output`). **2건 이상** → 엔트리당 한 줄(동일 형식). **labels** 끼리는 **콤마만**. username 은 CLI 값 또는 vault entry.
- **클립보드:** **1건**일 때만. `password` 필드는 **표준 Base64(UTF-8)** 로 가정 → 디코드 평문 복사. **`-t`** 이면 **TOTP만** 복사(password 클립보드 생략). **다중 매칭** 시 클립보드·stderr 안내 없음.
- **stderr 안내(복사 성공 시만):** `password is copied to clipboard` 또는 `totp value is copied to clipboard` (`-t` 시 TOTP만 복사).
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
