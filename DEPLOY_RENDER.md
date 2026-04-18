# Render 배포 가이드 (GitHub 연결)

이 문서는 이 저장소의 Flask 앱을 **GitHub에 올린 뒤 Render(onrender.com)에서 Web Service로 배포**하는 절차를 정리합니다.

이 앱은 정적 사이트가 아니라, `gunicorn`으로 실행되는 **서버(Web Service)** 입니다.

## 1) 사전 준비

- GitHub에 이 저장소가 푸시되어 있어야 합니다.
- Render 계정이 필요합니다.
- 사용자가 로그인할 Redmine URL과 Flask 세션 서명용 비밀값을 미리 준비해야 합니다.
- Render에서 넣을 실제 환경 변수 값을 정리해 둡니다.
  - `REDMINE_URL_INTERNAL`
  - `REDMINE_URL_EXTERNAL`
  - `SECRET_KEY`

## 2) GitHub 연결 (Render)

1. Render 대시보드에서 **New +** 를 누릅니다.
2. **Web Service** 를 선택합니다.
3. GitHub를 연결하지 않았다면, 안내에 따라 **GitHub 계정을 연결**하고 이 저장소에 대한 접근을 허용합니다.
4. 배포할 **Repository** 를 선택합니다.

## 3) Render Web Service 생성

Render의 서비스 생성 화면에서 아래 항목을 설정합니다.

### Runtime

- Python

### Build Command

```bash
python3 -m pip install -r requirements.txt
```

### Start Command

이 저장소의 `Procfile`은 아래와 같습니다.

```text
web: gunicorn --workers 1 app:app
```

따라서 Start Command는 다음을 사용합니다.

```bash
gunicorn --workers 1 app:app
```

이 저장소는 로그인된 Redmine 비밀번호를 서버 프로세스 메모리에만 보관하고, 세션 파일에는 참조값만 저장합니다.
따라서 현재 설계에서는 **단일 프로세스(단일 Gunicorn worker)** 로 실행해야 세션과 자격 증명 참조가 항상 같은 프로세스에서 해석됩니다.

## 4) 환경 변수 설정 (중요)

이 앱은 import 시점에 `.env`를 읽고, 필수 환경 변수가 없으면 바로 실패합니다. Render에서는 `.env` 파일을 커밋하지 말고, **Render의 Environment Variables**에 값을 넣어야 합니다.

### 필수 환경 변수

- `REDMINE_URL_INTERNAL`
- `REDMINE_URL_EXTERNAL`
- `SECRET_KEY`

### 선택 환경 변수

- `SESSION_FILE_DIR`: 서버 측 세션 파일 저장 경로
- `APP_MODE`: `development` 또는 `deploy` (기본값은 `development`)
- `DEFAULT_NETWORK`: `internal` 또는 `external` (기본값은 `internal`)

### fallback 주의

- `APP_MODE`를 비워 두거나 잘못 적으면 앱은 자동으로 `development`로 돌아갑니다.
- `DEFAULT_NETWORK`를 비워 두거나 잘못 적으면 앱은 자동으로 `internal`로 돌아갑니다.
- 따라서 Render 배포에서는 `APP_MODE=deploy`를 명시적으로 넣는 편이 안전합니다.

### 배포에서 권장 값

- Render 배포에서는 보통 내부망 주소에 접근할 수 없으므로 `APP_MODE=deploy`를 권장합니다.
  - 이 모드에서는 UI에서 네트워크 선택이 숨겨집니다.
  - 백엔드 요청은 항상 `external` Redmine 대상으로 처리됩니다.
  - 들어온 `network` 쿼리 값은 무시됩니다.

### 이 저장소 특이사항

- `APP_MODE=deploy`여도 **`REDMINE_URL_INTERNAL`은 누락되면 안 됩니다.**
  - 설정 검증 로직이 `REDMINE_URL_INTERNAL`, `REDMINE_URL_EXTERNAL`, `SECRET_KEY`를 모두 확인합니다.
  - 배포에서 internal을 실제로 쓰지 않더라도 값은 채워야 합니다.
  - Render에서 internal에 접근할 수 없다면, startup 검증용으로 `REDMINE_URL_INTERNAL`을 `REDMINE_URL_EXTERNAL`과 동일하게 둘 수 있습니다.
- 실제 Redmine URL은 HTTPS여야 합니다. 평문 HTTP는 localhost 기반의 로컬 mock 테스트만 허용됩니다.

## 5) 배포 확인

배포가 성공하면 Render가 서비스 URL(예: `https://<service>.onrender.com/`)을 제공합니다.

브라우저에서 아래를 확인합니다.

1. 메인 페이지 접속: `/`
2. 로그인 패널이 보이는지 확인
3. Redmine 계정으로 로그인 후 최근 이슈/검색/상세/첨부가 동작하는지 확인
4. 이슈 등록 옵션과 생성이 실제 권한 범위 안에서 동작하는지 확인

API를 직접 확인할 수도 있지만, 이제 보호된 API는 먼저 로그인 세션과 CSRF 토큰이 있어야 합니다.

1. `GET /api/auth/session?network=external`
2. `POST /api/auth/login` (+ `X-CSRF-Token`)
3. 이후 `/api/search?q=<issue-id>&network=external`, `/api/issue/<issue-id>?network=external`, `/api/attachment/<attachment-id>?network=external`

`APP_MODE=deploy`에서는 `network=internal`을 주더라도 외부망 대상으로 처리됩니다.

## 6) GitHub 푸시로 자동 배포되는 방식

Render에서 GitHub 저장소를 연결해 Web Service를 만들면, 보통 아래 흐름으로 동작합니다.

- Render가 선택한 브랜치의 최신 커밋을 감지
- Build Command 실행
- Start Command로 새 버전 기동

즉, GitHub에 푸시하면 Render가 자동으로 새 배포를 진행합니다. 자동 배포 여부는 Render 서비스 설정의 Deploy 관련 옵션에서 켜고 끌 수 있습니다.

## 7) keep-alive GitHub Actions (이 저장소에 이미 있음)

이 저장소에는 `.github/workflows/keep_alive.yml` 워크플로가 있으며, 5분마다 Render 앱 URL로 ping을 보냅니다.

- 현재 워크플로가 ping하는 주소는 다음으로 고정되어 있습니다.
  - `https://rtnet-fap-redmine.onrender.com/`

서비스 URL이 바뀌면 워크플로의 대상 URL도 같이 바꿔야 계속 동작합니다. 이 워크플로는 앱을 깨우기 위한 용도이며, 빌드나 테스트 파이프라인이 아닙니다.

## 8) 배포 시 주의사항

- 비밀 값(`SECRET_KEY` 등)은 Git에 커밋하지 말고 Render 환경 변수로만 관리하세요.
- Render에서 내부망 Redmine 주소는 접근이 안 될 수 있습니다.
  - 이 경우 배포 검증은 `APP_MODE=deploy` 기준으로 하는 것이 현실적입니다.
- 실제 사용자 계정 권한에 따라 이슈 조회/첨부/생성 가능 범위가 달라질 수 있습니다.
- 이 설계는 Redmine 비밀번호를 디스크 세션 파일에 직접 저장하지 않고 서버 프로세스 메모리에만 보관합니다.
  - 따라서 프로세스 재시작 뒤에는 사용자가 다시 로그인해야 합니다.
  - 같은 이유로 배포도 `gunicorn --workers 1 app:app` 기준으로 유지해야 합니다.
  - worker 수를 늘리거나 여러 인스턴스로 확장하려면, 세션과 동일한 수명의 공유 서버측 저장소로 자격 증명을 옮기는 재설계가 먼저 필요합니다.
