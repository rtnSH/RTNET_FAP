# AGENTS.md

## 에이전트 응답 규칙
- 모든 대답은 한글로 한다.

## 저장소 구조
- 이 저장소는 전체 Redmine 소스가 아니라 작은 Flask 앱이다. 진입점은 `app.py`다.
- 사용자 동작과 직접 연결된 파일은 주로 `app.py`, `templates/index.html`, `static/js/script.js`, `static/css/style.css`에 모여 있다.
- 앱 동작을 조사할 때 `.opencode/`는 무시해도 된다. 제품 코드가 아니라 OpenCode 설정과 의존성 잡음이 들어 있다.
- 로컬 Python 환경 자체를 디버깅하는 경우가 아니면 검색이나 진단에서 `.venv/`는 제외하라.

## 설치 및 실행
- 의존성 설치: `pip install -r requirements.txt`
- 로컬 개발 서버 실행: `python3 app.py` (`app.py`의 `if __name__ == '__main__'` 블록으로 직접 실행 가능)
- 운영 실행 명령: `gunicorn app:app` (`Procfile`의 값은 `web: gunicorn app:app`)
- 이 작업 공간에서는 `python`이 `PATH`에 없으므로, 활성화된 가상환경이 `python`을 제공하는 경우가 아니면 `python3`를 우선 사용하라.

## 환경 변수 및 외부 의존성
- 앱은 import 시점에 `load_dotenv()`를 호출하며 `REDMINE_URL_INTERNAL`, `REDMINE_URL_EXTERNAL`, `SECRET_KEY`를 기대한다.
- `.env`는 gitignore에 포함되어 있다. 절대 커밋하지 말고, 값도 로그에 남기지 마라.
- `/api/search`, `/api/issue/<id>`, `/api/attachment/<id>`를 호출하는 기능은 모두 실제 Redmine 연결과 유효한 로그인 세션에 의존한다.

## 검증 가이드
- 이 저장소에는 테스트 스위트, 린트 설정, 타입체크 설정, 의미 있는 앱 검증용 CI가 없다. `.github/workflows/keep_alive.yml`은 배포된 Render 앱에 핑만 보내는 용도다.
- 네트워크가 필요 없는 변경은 집중 검증으로 확인하라. 예를 들어 의존성 설치 후 앱 import, Flask 라우트 확인, 로컬 서버 실행 같은 방법이 적절하다.
- UI 변경을 검증할 때는 프런트엔드 빌드 시스템을 찾지 말고 단일 템플릿과 정적 파일을 직접 확인하라. 이 저장소에는 패키지 매니저 매니페스트나 번들러가 없다.

## 코드 작업 시 주의점
- Redmine 접근 대상은 `network` 쿼리 파라미터(`internal` / `external`)로 결정된다. API나 프런트엔드 요청 코드를 수정할 때 이 흐름을 유지해야 한다.
- `python-redmine` 결과는 lazy evaluation일 수 있다. 필터링이나 순회 로직을 함수 사이로 옮길 때 실제 평가 시점이 바뀌지 않는지 주의하라.
- `static/js/script.js`는 이스케이프 처리와 함께 Redmine 포맷 텍스트/첨부파일 렌더링을 위해 의도적으로 `innerHTML`도 사용한다. sanitize 또는 렌더링 로직을 건드릴 때 특히 조심하라.
