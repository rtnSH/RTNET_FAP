# Render 배포 가이드 (GitHub 연결)

이 문서는 이 저장소의 Flask 앱을 **GitHub에 올린 뒤 Render(onrender.com)에서 Web Service로 배포**하는 절차를 정리합니다.

이 앱은 정적 사이트가 아니라, `gunicorn`으로 실행되는 **서버(Web Service)** 입니다.

## 1) 사전 준비

- GitHub에 이 저장소가 푸시되어 있어야 합니다.
- Render 계정이 필요합니다.
- Redmine REST API를 호출할 수 있는 **Redmine API Key**가 필요합니다.
- Render에서 넣을 실제 환경 변수 값을 미리 준비해야 합니다.
  - `REDMINE_URL_INTERNAL`
  - `REDMINE_URL_EXTERNAL`
  - `REDMINE_API_KEY`

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

이 저장소의 안내와 동일하게 아래 명령을 사용합니다.

```bash
python3 -m pip install -r requirements.txt
```

### Start Command

이 저장소의 `Procfile`은 아래와 같습니다.

```text
web: gunicorn app:app
```

따라서 Start Command는 다음을 사용합니다.

```bash
gunicorn app:app
```

## 4) 환경 변수 설정 (중요)

이 앱은 import 시점에 `.env`를 읽고, 필수 환경 변수가 없으면 바로 실패합니다.
Render에서는 `.env` 파일을 커밋하지 말고, **Render의 Environment Variables**에 값을 넣어야 합니다.

### 필수 환경 변수

- `REDMINE_URL_INTERNAL`
- `REDMINE_URL_EXTERNAL`
- `REDMINE_API_KEY`

### 선택 환경 변수

- `APP_MODE`: `development` 또는 `deploy` (기본값은 `development`)
- `DEFAULT_NETWORK`: `internal` 또는 `external` (기본값은 `internal`)

### 선택 환경 변수 fallback 주의

- `APP_MODE`를 비워 두거나 잘못 적으면 앱은 자동으로 `development`로 돌아갑니다.
- `DEFAULT_NETWORK`를 비워 두거나 잘못 적으면 앱은 자동으로 `internal`로 돌아갑니다.
- 따라서 Render 배포에서는 `APP_MODE=deploy`를 명시적으로 넣는 편이 안전합니다.

### 배포에서 권장 값

- Render 배포에서는 보통 내부망 주소에 접근할 수 없으므로 `APP_MODE=deploy`를 권장합니다.
  - `APP_MODE=deploy`는 UI에서 네트워크 선택을 숨기고, 백엔드 요청을 항상 `external`로 처리합니다.
  - 이 모드에서는 들어온 `network` 쿼리 값이 무엇이든 무시됩니다.
  - 이 모드에서는 `DEFAULT_NETWORK` 값도 사실상 의미가 없습니다.

### 이 저장소 특이사항 (꼭 읽기)

- `APP_MODE=deploy`여도 **`REDMINE_URL_INTERNAL`은 누락되면 안 됩니다.**
  - 설정 검증 로직이 `REDMINE_URL_INTERNAL`, `REDMINE_URL_EXTERNAL`, `REDMINE_API_KEY` 3개 모두를 필수로 요구합니다.
  - 배포에서 internal을 실제로 쓰지 않더라도, 값은 반드시 채워야 합니다.
  - 내부망 주소를 Render에서 접근할 수 없다면, 임시로 `REDMINE_URL_INTERNAL`을 `REDMINE_URL_EXTERNAL`과 동일하게 두고 startup 검증 통과용 placeholder로 사용할 수 있습니다.
  - 다만 이 설정은 deploy 모드 전제에서만 현실적인 우회입니다. 나중에 `APP_MODE=development`로 바꾸면 internal/external 구분의 의미가 사라집니다.

## 5) 배포 확인

배포가 성공하면 Render가 서비스 URL(예: `https://<service>.onrender.com/`)을 제공합니다.

브라우저에서 아래를 확인합니다.

1. 메인 페이지 접속: `/`
2. 이슈 검색 및 상세가 동작하는지 확인
3. 첨부파일이 열리는지 확인

문제 분리를 위해 API도 직접 확인할 수 있습니다.

- `/api/search?q=<issue-id>&network=external`
- `/api/issue/<issue-id>?network=external`
- `/api/attachment/<attachment-id>?network=external`

`APP_MODE=deploy`에서는 `network=internal`을 줘도 외부망 대상으로 처리됩니다.

## 6) GitHub 푸시로 자동 배포되는 방식

Render에서 GitHub 저장소를 연결해 Web Service를 만들면, 보통 아래 흐름으로 동작합니다.

- Render가 선택한 브랜치의 최신 커밋을 감지
- Build Command 실행
- Start Command로 새 버전 기동

즉, GitHub에 푸시하면 Render가 자동으로 새 배포를 진행합니다.
자동 배포 여부는 Render 서비스 설정의 Deploy 관련 옵션에서 켜고 끌 수 있습니다.

## 7) keep-alive GitHub Actions (이 저장소에 이미 있음)

이 저장소에는 `.github/workflows/keep_alive.yml` 워크플로가 있으며, 5분마다 Render 앱 URL로 ping을 보냅니다.

- 현재 워크플로가 ping하는 주소는 다음으로 고정되어 있습니다.
  - `https://rtnet-fap-redmine.onrender.com/`

서비스 URL이 바뀌면, 워크플로의 대상 URL도 같이 바꿔야 계속 동작합니다.
새 Render 서비스를 다시 만들고 서비스 주소가 달라졌는데 워크플로를 수정하지 않으면, GitHub Actions는 새 서비스가 아니라 예전 서비스를 계속 ping하게 됩니다.
이 워크플로는 앱을 깨우기 위한 용도이며, 빌드나 테스트 파이프라인이 아닙니다.

## 8) 배포 시 주의사항

- 비밀 값(`REDMINE_API_KEY` 등)은 Git에 커밋하지 말고 Render 환경 변수로만 관리하세요.
- Render에서 내부망 Redmine 주소는 접근이 안 될 수 있습니다.
  - 이 경우 배포는 `APP_MODE=deploy` 기준으로 검증하는 것이 현실적입니다.
- Redmine 쪽 권한이 부족하면 이슈 조회나 첨부파일 다운로드가 실패합니다.
  - API Key 권한을 먼저 확인하세요.
