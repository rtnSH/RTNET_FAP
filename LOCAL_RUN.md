# 로컬 실행 상세 가이드

이 문서는 이 저장소를 **로컬에서 직접 실행하고 실제 Redmine에 연결해 확인하는 방법**을 자세히 설명합니다.

이 프로젝트는 전체 Redmine 애플리케이션이 아니라, Redmine 이슈를 조회하고 첨부파일을 확인하는 작은 Flask 앱입니다. 진입점은 `app.py`입니다.

---

## 1. 먼저 이해할 점

이 앱은 자체 데이터베이스를 쓰지 않습니다. 로컬에서 실행하더라도 실제 Redmine 서버에 연결해야 의미 있는 동작을 확인할 수 있습니다.

즉, 아래 세 가지가 준비되어 있어야 합니다.

1. `python3` 실행 환경
2. Redmine 서버 주소
3. Redmine API Key

앱은 `.env` 파일에서 환경 변수를 읽고, 내부망/외부망 Redmine 주소를 구분해서 사용합니다.

---

## 2. 저장소 구조 빠르게 보기

로컬 실행과 직접 관련 있는 파일은 아래 정도만 보면 됩니다.

- `app.py`: Flask 앱 진입점
- `templates/index.html`: 메인 화면 템플릿
- `static/js/script.js`: 검색/상세 조회/첨부 요청 처리
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

버전 확인:

```bash
python3 --version
```

### Redmine 접근 정보

다음 정보가 필요합니다.

- `REDMINE_URL_INTERNAL`: 내부망용 Redmine base URL
- `REDMINE_URL_EXTERNAL`: 외부망용 Redmine base URL
- `REDMINE_API_KEY`: 이슈/첨부파일을 읽을 수 있는 API Key
- `APP_MODE`: 앱 실행 모드 (`development` 또는 `deploy`, 기본값은 `development`)
- `DEFAULT_NETWORK`: 앱 첫 화면과 `network` 미지정 API 요청에 사용할 기본 네트워크 (`internal` 또는 `external`, 기본값은 `internal`)

예를 들면 URL은 이런 형태입니다.

```text
https://redmine.example.com
https://redmine-internal.example.com
```

주의:

- 실제 값은 절대 Git에 커밋하면 안 됩니다.
- 실제 값은 채팅이나 로그에도 그대로 붙이지 않는 것이 좋습니다.

---

## 4. 의존성 설치

두 가지 방법이 있지만, 가장 안전한 방법은 새 가상환경을 만드는 것입니다.

### 방법 A: 권장 방식 - 새 가상환경 사용

저장소 루트에서 실행합니다.

```bash
python3 -m venv .venv-local
source .venv-local/bin/activate
python3 -m pip install -r requirements.txt
```

설치가 끝나면 Flask, python-redmine, python-dotenv, requests, gunicorn이 들어갑니다.

### 방법 B: 시스템 Python에 바로 설치

가상환경을 쓰지 않으려면:

```bash
python3 -m pip install -r requirements.txt
```

다만 이후 기능 추가 작업까지 생각하면 가상환경 사용이 더 안전합니다.

---

## 5. 환경 변수 설정

앱은 import 시점에 `.env`를 읽습니다. 따라서 실행 전에 `.env`가 준비되어 있어야 합니다.

먼저 예시 파일을 복사합니다.

```bash
cp .env.example .env
```

그다음 `.env`를 열어서 실제 값으로 바꿉니다.

예시:

```dotenv
REDMINE_URL_INTERNAL=https://redmine-internal.example.com
REDMINE_URL_EXTERNAL=https://redmine.example.com
REDMINE_API_KEY=your-real-api-key
APP_MODE=development
DEFAULT_NETWORK=internal
```

### 변수 설명

#### `REDMINE_URL_INTERNAL`
- `network=internal`일 때 사용하는 주소입니다.
- 보통 사내망/VPN 환경에서만 접속 가능한 Redmine일 수 있습니다.

#### `REDMINE_URL_EXTERNAL`
- `network=external`일 때 사용하는 주소입니다.
- 로컬 테스트에서는 보통 이 주소부터 먼저 확인하는 게 편합니다.

#### `REDMINE_API_KEY`
- Redmine REST API 호출에 사용됩니다.
- 이슈 조회와 첨부파일 다운로드 모두 여기에 의존합니다.

#### `DEFAULT_NETWORK`
- 첫 화면에서 어느 라디오 버튼이 기본 선택될지 결정합니다.
- API 요청에 `network` 파라미터가 없거나 잘못된 값이면 이 값을 기준으로 정규화합니다.
- `internal`, `external` 외의 값이 들어오면 안전하게 `internal`로 처리됩니다.

#### `APP_MODE`
- `development`: 현재처럼 내부망/외부망 선택 UI를 보여주고 `DEFAULT_NETWORK`를 그대로 사용합니다.
- `deploy`: 네트워크 선택 UI를 숨기고, 모든 백엔드 요청을 강제로 `external`로 처리합니다.
- 값이 없거나 잘못되어도 앱은 안전하게 `development`로 돌아갑니다.

### 실무 팁

- 현재 내 PC에서 내부망 주소에 접근이 안 된다면, 우선 `external`만 검증해도 됩니다.
- 로컬에서 한쪽 주소만 접근 가능하면, 임시로 internal/external 둘 다 같은 URL로 넣어도 됩니다.
- URL 끝의 `/`는 없어도 되고, 들어가 있어도 앱이 정리합니다.

---

## 6. 이 앱이 internal / external 을 고르는 방식

이 앱은 `network` 쿼리 파라미터를 기준으로 Redmine 대상 서버를 고릅니다.

기준은 아래와 같습니다.

- `APP_MODE=development`일 때:
  - `network=external` → `REDMINE_URL_EXTERNAL` 사용
  - `network=internal` → `REDMINE_URL_INTERNAL` 사용
  - `network`가 없거나 잘못된 값 → `DEFAULT_NETWORK`를 정규화해서 사용 (미설정/이상값이면 `internal`)
- `APP_MODE=deploy`일 때:
  - 들어온 `network` 값과 무관하게 항상 `REDMINE_URL_EXTERNAL` 사용
  - 즉 `network=internal` 요청도 외부망 대상으로 강제됩니다.

이 흐름은 UI와 API 양쪽에 연결되어 있습니다.

예를 들어:

- `/api/search?q=123&network=external`
- `/api/issue/123?network=internal`

같은 요청이라도 `network` 값에 따라 접속 대상 Redmine이 달라집니다.

---

## 7. 로컬에서 앱 실행하기

### 개발용 실행

가상환경을 만들었다면 먼저 활성화합니다.

```bash
source .venv-local/bin/activate
```

그다음 앱을 실행합니다.

```bash
python3 app.py
```

기본 포트는 `5000`입니다. 실행되면 보통 아래 주소로 접속합니다.

```text
http://localhost:5000
```

### 실행 실패 시

만약 `.env`가 없거나 값이 비어 있으면 import 단계에서 아래와 비슷한 에러가 납니다.

```text
Missing required environment variables: REDMINE_URL_INTERNAL, REDMINE_URL_EXTERNAL, REDMINE_API_KEY
```

이 경우 `.env`를 다시 확인하면 됩니다.

---

## 8. production 스타일로 실행하기

배포에 더 가까운 방식으로 보고 싶다면 gunicorn으로도 실행할 수 있습니다.

```bash
gunicorn app:app
```

`Procfile`도 같은 엔트리포인트를 사용합니다.

```text
web: gunicorn app:app
```

즉, 로컬에서 `python3 app.py`로 먼저 확인하고, 필요하면 `gunicorn app:app`로 한 번 더 보는 흐름이면 충분합니다.

---

## 9. 브라우저에서 기능 확인하기

앱이 뜨면 브라우저에서 아래 순서로 확인하면 됩니다.

### 1) 메인 화면 접속

```text
http://localhost:5000
```

### 2) network 선택

`APP_MODE=development`에서는 먼저 `external` 쪽부터 확인하는 것을 권장합니다.

이유는:

- 로컬 PC에서 바로 접근 가능할 확률이 높고
- 내부망/VPN 이슈를 먼저 배제할 수 있기 때문입니다.

`APP_MODE=deploy`에서는 network 선택 UI가 보이지 않으며, 검색/상세/첨부 요청이 모두 외부망 기준으로 동작합니다.

### 3) known issue ID로 먼저 검색

처음에는 키워드보다 **이미 존재를 아는 이슈 번호**로 테스트하는 게 좋습니다.

예:

- `12345`

이렇게 하면 검색 로직과 상세 조회 로직을 한 번에 더 확실하게 볼 수 있습니다.

### 4) 화면에서 확인할 것

아래가 정상적으로 보이면 기본 흐름은 통과한 것입니다.

- 이슈 제목
- 상태, 우선순위, 작성자, 담당자
- 설명(description)
- 저널(journals) 목록
- 첨부파일 목록
- `APP_MODE=development`에서는 internal / external Redmine 링크
- `APP_MODE=deploy`에서는 강조된 external Redmine 링크

### 5) internal도 반복 확인

내 PC나 VPN 환경에서 내부망 주소가 열리면, 같은 이슈로 `internal`도 반복해서 확인합니다.

---

## 10. API로 직접 확인하기

UI 말고 API 응답도 직접 보면 문제를 분리하기 쉽습니다.

### 이슈 검색

```text
/api/search?q=<issue-id>&network=external
```

예:

```text
http://localhost:5000/api/search?q=12345&network=external
```

동작:

- 숫자만 넣으면 먼저 ID 조회를 시도합니다.
- 실패하면 키워드 검색으로 넘어갑니다.

### 이슈 상세

```text
/api/issue/<issue-id>?network=external
```

예:

```text
http://localhost:5000/api/issue/12345?network=external
```

동작:

- 저널과 첨부파일을 포함한 상세 JSON을 돌려줍니다.

### 첨부파일 조회

```text
/api/attachment/<attachment-id>?network=external
```

동작:

- 실제 첨부파일 내용을 스트리밍합니다.
- 파일 확인은 먼저 이슈 상세 응답에서 attachment ID를 확인한 뒤 하는 것이 자연스럽습니다.

---

## 11. 자주 만나는 문제와 해결 방법

### 문제 1: 앱이 바로 시작되지 않음

원인:

- `.env` 없음
- 필수 환경 변수 누락

해결:

1. `.env.example`을 `.env`로 복사했는지 확인
2. 세 변수 모두 채웠는지 확인
3. 오타가 없는지 확인

### 문제 2: 메인 페이지는 뜨는데 검색이 실패함

원인 후보:

- API Key 오류
- Redmine URL 오타
- 현재 네트워크에서 해당 Redmine 접근 불가

해결:

1. `external`로 먼저 테스트
2. known issue ID로 테스트
3. API Key 권한 확인
4. VPN/사내망 연결 여부 확인

### 문제 2-1: deploy로 실행했는데 internal로 바뀌지 않음

원인:

- 정상 동작입니다. `APP_MODE=deploy`는 내부망 선택과 `network=internal` 요청을 허용하지 않습니다.

해결:

- 내부망 전환 테스트가 필요하면 `APP_MODE=development`로 다시 실행합니다.

### 문제 3: external은 되는데 internal은 안 됨

원인:

- 내부망 주소는 현재 PC에서 접근 불가

해결:

- VPN 또는 사내망 연결 상태 확인
- 내부 테스트가 당장 필요 없으면 우선 external 기준으로 기능 작업 진행
- 필요 시 임시로 두 URL을 같은 reachable URL로 맞춰서 UI 흐름만 검증

### 문제 4: 첨부파일만 안 열림

원인 후보:

- 해당 attachment ID가 잘못됨
- API Key 권한 부족
- Redmine 쪽 첨부 접근 제한

해결:

- 먼저 `/api/issue/<id>` 응답에서 attachment ID가 맞는지 확인
- 권한 있는 계정의 API Key인지 확인

---

## 12. 빠른 실행용 명령 모음

처음부터 다시 세팅할 때는 아래 순서대로 하면 됩니다.

```bash
cd /home/sh/ai-agents/Redmine
python3 -m venv .venv-local
source .venv-local/bin/activate
python3 -m pip install -r requirements.txt
cp .env.example .env
python3 app.py
```

그다음 브라우저에서:

```text
http://localhost:5000
```

---

## 13. 이 저장소에서 굳이 찾지 않아도 되는 것

이 저장소는 구조가 단순하므로 아래를 찾느라 시간을 쓸 필요는 없습니다.

- 프런트엔드 번들러
- npm 기반 빌드 시스템
- 정식 테스트 스위트
- 앱 검증용 CI

UI는 단일 템플릿과 정적 파일로 동작하고, 로컬 검증은 실제 실행과 API 확인 중심으로 보면 됩니다.
