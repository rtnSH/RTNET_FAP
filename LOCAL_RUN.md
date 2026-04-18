# 로컬 실행 상세 가이드

이 문서는 이 저장소를 **로컬에서 직접 실행하고 실제 Redmine에 연결해 확인하는 방법**을 설명합니다.

이 프로젝트는 전체 Redmine 애플리케이션이 아니라, Redmine 이슈를 조회·확인·등록하는 작은 Flask 앱입니다. 진입점은 `app.py`입니다.

---

## 1. 먼저 이해할 점

이 앱은 자체 데이터베이스를 쓰지 않습니다. 로컬에서 실행하더라도 실제 Redmine 서버에 연결해야 의미 있는 동작을 확인할 수 있습니다.

즉, 아래가 준비되어 있어야 합니다.

1. `python3` 실행 환경
2. Redmine 서버 주소
3. Redmine에 로그인 가능한 사용자 계정(username/password)
4. Flask 세션 서명용 `SECRET_KEY`

앱은 `.env` 파일에서 환경 변수를 읽고, 내부망/외부망 Redmine 주소를 구분해서 사용합니다.

---

## 2. 저장소 구조 빠르게 보기

- `app.py`: Flask 앱 진입점
- `templates/index.html`: 메인 화면 템플릿
- `static/js/script.js`: 로그인/검색/상세/등록 요청 처리
- `static/css/style.css`: 화면 스타일
- `.env.example`: 환경 변수 예시 파일
- `README.md`: 짧은 실행 안내
- `LOCAL_RUN.md`: 이 상세 가이드

참고:

- `.opencode/`는 제품 코드가 아닙니다.
- 저장소 안에 이미 `.venv/`가 있어도 현재 OS에서 그대로 못 쓸 수 있습니다.
- 이 가이드에서는 새 로컬 가상환경인 `.venv-local/`을 사용하는 방법을 권장합니다.

---

## 3. 준비물

### Python

이 작업 공간에서는 `python` 명령이 없을 수 있으므로 **`python3`를 사용**하는 기준으로 진행하면 됩니다.

```bash
python3 --version
```

### Redmine 접근 정보

다음 정보가 필요합니다.

- `REDMINE_URL_INTERNAL`: 내부망용 Redmine base URL
- `REDMINE_URL_EXTERNAL`: 외부망용 Redmine base URL
- `SECRET_KEY`: Flask 세션 서명 키
- `SESSION_FILE_DIR`: 서버 측 세션 파일 저장 디렉터리(선택)
- `APP_MODE`: 앱 실행 모드 (`development` 또는 `deploy`)
- `DEFAULT_NETWORK`: 기본 네트워크 (`internal` 또는 `external`)
- Redmine username/password

주의:

- 실제 값은 절대 Git에 커밋하면 안 됩니다.
- `REDMINE_URL_INTERNAL`과 `REDMINE_URL_EXTERNAL`은 현재 환경에 맞춰 HTTP 또는 HTTPS를 사용할 수 있습니다.
- 다만 평문 HTTP를 쓰면 Redmine 아이디/비밀번호가 TLS 없이 전달되므로, 신뢰 가능한 사내망이나 VPN 안에서만 사용해야 합니다.

---

## 4. 의존성 설치

가장 안전한 방법은 새 가상환경을 만드는 것입니다.

```bash
python3 -m venv .venv-local
source .venv-local/bin/activate
python3 -m pip install -r requirements.txt
```

설치가 끝나면 Flask, Flask-Session, python-redmine, python-dotenv, requests, gunicorn이 들어갑니다.

---

## 5. 환경 변수 설정

앱은 import 시점에 `.env`를 읽습니다. 따라서 실행 전에 `.env`가 준비되어 있어야 합니다.

```bash
cp .env.example .env
```

예시:

```dotenv
REDMINE_URL_INTERNAL=https://redmine-internal.example.com
REDMINE_URL_EXTERNAL=https://redmine.example.com
SECRET_KEY=replace-with-a-long-random-secret
SESSION_FILE_DIR=/tmp/redmine-helper-sessions
APP_MODE=development
DEFAULT_NETWORK=internal
```

### 변수 설명

#### `REDMINE_URL_INTERNAL`
- `network=internal`일 때 사용하는 주소입니다.

#### `REDMINE_URL_EXTERNAL`
- `network=external`일 때 사용하는 주소입니다.

#### `SECRET_KEY`
- Flask 세션 쿠키를 서명하는 키입니다.
- 충분히 긴 랜덤 문자열을 사용해야 합니다.

#### `SESSION_FILE_DIR`
- 서버 측 세션 파일을 저장할 디렉터리입니다.
- 지정하지 않으면 `/tmp/redmine-helper-sessions`를 사용합니다.
- 이 디렉터리는 Git에 포함되면 안 됩니다.

#### `DEFAULT_NETWORK`
- 첫 화면에서 어느 네트워크가 기본 선택될지 결정합니다.

#### `APP_MODE`
- `development`: 내부망/외부망 선택 UI를 보여줍니다.
- `deploy`: 네트워크 선택 UI를 숨기고 모든 백엔드 요청을 `external`로 강제합니다.

실무 팁:

- 현재 PC에서 내부망 주소에 접근이 안 된다면 우선 `external`만 검증해도 됩니다.
- 한쪽 주소만 접근 가능하면 임시로 internal/external 둘 다 같은 URL로 넣어 UI 흐름만 검증할 수 있습니다.

---

## 6. internal / external 선택 방식

- `APP_MODE=development`
  - `network=external` → `REDMINE_URL_EXTERNAL`
  - `network=internal` → `REDMINE_URL_INTERNAL`
  - `network`가 없거나 잘못된 값 → `DEFAULT_NETWORK`
- `APP_MODE=deploy`
  - 들어온 `network` 값과 무관하게 항상 `REDMINE_URL_EXTERNAL`

---

## 7. 로컬에서 앱 실행하기

```bash
source .venv-local/bin/activate
python3 app.py
```

기본 주소:

```text
http://localhost:5000
```

실행 실패 시 `.env` 누락이나 값 비어 있음 때문에 아래와 비슷한 에러가 날 수 있습니다.

```text
Missing required environment variables: REDMINE_URL_INTERNAL, REDMINE_URL_EXTERNAL, SECRET_KEY
```

---

## 8. 브라우저에서 기능 확인하기

1. `http://localhost:5000` 접속
2. `APP_MODE=development`면 필요에 따라 network 선택
3. 상단 로그인 패널에서 Redmine username/password 입력
4. 로그인 성공 후 최근 이슈 자동 로드 확인
5. known issue ID로 검색
6. 상세 화면에서 제목/상태/우선순위/작성자/담당자/설명/저널/첨부 확인
7. 작성 패널을 열어 옵션/프리필/이슈 생성 확인

중요:

- 검색/상세/첨부/등록은 모두 로그인 후에만 동작합니다.
- 서버 프로세스가 재시작되면 다시 로그인해야 합니다.

---

## 9. API로 직접 확인하기

보호된 API를 직접 테스트하려면 먼저 세션 쿠키와 CSRF 토큰을 받아야 합니다.

### 1) 세션/CSRF 토큰 받기

```text
GET /api/auth/session?network=external
```

### 2) 로그인

```text
POST /api/auth/login
X-CSRF-Token: <step-1 token>
Content-Type: application/json

{
  "username": "your-login",
  "password": "your-password",
  "network": "external"
}
```

### 3) 보호된 API 호출

- `/api/search?q=<issue-id>&network=external`
- `/api/issue/<issue-id>?network=external`
- `/api/attachment/<attachment-id>?network=external`

이때는 로그인에서 받은 **같은 세션 쿠키**를 계속 사용해야 합니다.

---

## 10. 자주 만나는 문제와 해결 방법

### 문제 1: 앱이 바로 시작되지 않음

원인:

- `.env` 없음
- 필수 환경 변수 누락
- Redmine URL 규칙이 맞지 않음

해결:

1. `.env.example`을 `.env`로 복사했는지 확인
2. `REDMINE_URL_INTERNAL`, `REDMINE_URL_EXTERNAL`, `SECRET_KEY`를 모두 채웠는지 확인
3. `REDMINE_URL_INTERNAL`/`REDMINE_URL_EXTERNAL`가 올바른 URL 형식인지 확인
   - internal/external 모두 HTTP/HTTPS 허용
   - hostname이 실제로 들어 있어야 함

### 문제 2: 로그인 실패

원인 후보:

- username/password 오타
- 해당 Redmine 계정이 password 기반 API 사용 불가
- 2FA 정책 때문에 비밀번호 API 로그인이 차단됨

해결:

1. 브라우저에서 Redmine 자체 로그인 가능 여부 확인
2. 계정의 password-based API 사용 가능 여부 확인
3. 네트워크가 맞는지(`internal`/`external`) 확인

### 문제 3: external은 되는데 internal은 안 됨

원인:

- 내부망 주소는 현재 PC에서 접근 불가

해결:

- VPN 또는 사내망 연결 상태 확인
- 내부 테스트가 당장 필요 없으면 우선 external 기준으로 진행

### 문제 4: 첨부파일만 안 열림

원인 후보:

- attachment ID가 잘못됨
- 현재 로그인한 계정 권한 부족
- Redmine 쪽 첨부 접근 제한

해결:

- 먼저 `/api/issue/<id>` 응답에서 attachment ID가 맞는지 확인
- 해당 사용자 계정에 첨부 조회 권한이 있는지 확인

---

## 11. 빠른 실행용 명령 모음

```bash
python3 -m venv .venv-local
source .venv-local/bin/activate
python3 -m pip install -r requirements.txt
cp .env.example .env
python3 app.py
```

브라우저:

```text
http://localhost:5000
```

---

## 12. 이 저장소에서 굳이 찾지 않아도 되는 것

- 프런트엔드 번들러
- npm 기반 빌드 시스템
- 정식 테스트 스위트
- 앱 검증용 CI

UI는 단일 템플릿과 정적 파일로 동작하고, 로컬 검증은 실제 실행과 API 확인 중심으로 보면 됩니다.
