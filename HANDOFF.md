# HANDOFF

## Goal
- `AGENTS.md`에 에이전트 응답 규칙을 추가해 모든 답변을 한글로 하도록 명시한다.
- 모바일 홈 화면 바로가기 아이콘이 로그인 화면에서 쓰는 CI와 같은 계열의 아이콘을 사용하도록 연결한다.
- 그래프 산출물 디렉터리(`graphify-out/`)가 Git 작업 트리에 잡음으로 남지 않게 정리한다.

## Current Progress
- 완료: `AGENTS.md` 상단에 `## 에이전트 응답 규칙` 섹션을 추가하고 `- 모든 대답은 한글로 한다.` 문구를 넣었다.
- 완료: `static/logo-ci.svg`를 새로 추가했다. 로그인 화면의 인라인 SVG CI(파란 그라디언트 동심원)를 기반으로, 모바일 아이콘에 맞는 192x192 정사각형 SVG로 분리했다.
- 완료: `static/site.webmanifest`를 새로 추가했다. `standalone` 표시 모드, 다크 배경/테마 컬러, `/static/logo-ci.svg` 아이콘을 포함한다.
- 완료: `templates/index.html`의 `<head>`에 아래 항목을 추가했다.
  - `meta name="theme-color"`
  - `meta name="apple-mobile-web-app-capable"`
  - `link rel="icon"`
  - `link rel="apple-touch-icon"`
  - `link rel="manifest"`
- 완료: 위 변경은 이미 원격 브랜치 `feature/redmine-userpass-auth`에 푸시되었다.
- 진행 예정: 이 `HANDOFF.md`를 저장소 안에서 추적하고, `graphify-out/`를 `.gitignore`에 추가한다.

## What Worked
- 기존 로그인 화면 CI는 `templates/index.html` 안의 인라인 SVG였고, 별도 이미지 자산이 없었다. 같은 시각 언어를 유지한 새 정적 SVG 아이콘을 추가하는 방식이 가장 작은 변경이었다.
- 정적 검증 성공:
  - `site.webmanifest` JSON 파싱 성공
  - `logo-ci.svg` 파일 존재 및 내용 확인 성공
- 앱 검증 성공:
  - 환경변수 더미값을 넣고 `python3`로 `app` import 성공
  - Flask test client로 `/static/logo-ci.svg` 200 응답
  - Flask test client로 `/static/site.webmanifest` 200 응답
  - Flask test client로 `/` 200 응답
- Git 반영 성공:
  - `4dc85d8` `agent docs`
  - `6617968` `mobile icon`

## What Didn't Work
- 배경 `explore` 에이전트 2개가 모두 `ProviderModelNotFoundError`로 실패했다. 따라서 추가 탐색은 에이전트 대신 직접 `read`, `glob`, `grep` 결과를 근거로 진행했다.
- Oracle 검토 작업(`bg_bf080f40`)은 시작은 되었지만 최종 검토 문장을 남기지 못했다. 실제 검증은 직접 읽기/실행 결과를 기준으로 완료했다.
- 이 환경에서는 HTML/manifest 전용 LSP 진단이 제대로 동작하지 않았다.
  - `.html`은 `biome` 미설치 오류
  - `.md`, `.webmanifest`는 LSP 미구성

## Next Steps
- 실제 모바일 기기에서 "홈 화면에 추가"를 해 아이콘이 의도대로 보이는지 수동 확인한다.
- iOS에서 SVG `apple-touch-icon` 처리 호환성이 불안정하면 PNG 아이콘(예: 180x180)을 추가로 생성해 `apple-touch-icon`만 PNG로 분기하는 것을 검토한다.
- 필요하면 `favicon.ico` 또는 PNG 파비콘도 함께 추가해 데스크톱/구형 브라우저 호환성을 보강한다.
- `graphify-out/`가 다시 필요해지면 로컬 분석 산출물로만 유지하고, 기본적으로는 Git 추적 대상에 포함하지 않는다.

## Changed Files
- `/home/sh/projects/redmine_sync/redmine/AGENTS.md`
- `/home/sh/projects/redmine_sync/redmine/templates/index.html`
- `/home/sh/projects/redmine_sync/redmine/static/logo-ci.svg`
- `/home/sh/projects/redmine_sync/redmine/static/site.webmanifest`
- `/home/sh/projects/redmine_sync/redmine/HANDOFF.md`

## Branch / Remote
- Branch: `feature/redmine-userpass-auth`
- Remote: `origin https://github.com/rtnSH/RTNET_FAP.git`
