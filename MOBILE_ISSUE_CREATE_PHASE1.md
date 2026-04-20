# Mobile issue creation - Phase 1 checklist

## Scope
- [x] Document phase-1 backend-only scope
- [x] Exclude actual issue submission/create API in this pass
- [x] Exclude frontend create UI except future integration points

## Product rules locked for phase 1
- [x] Projects are loaded dynamically from Redmine
- [x] Tracker is treated as the issue type
- [x] Assignee candidates are derived from project-scoped assignable users, then limited to 김윤권/김창민/전상수/이수호
- [x] Default title is generated within project + tracker scope
- [x] If no prior issue exists in that scope, default title is the tracker name
- [x] Default parent is the oldest root issue in scope, but remains editable later
- [x] Description is optional
- [x] Default status is `신규`
- [x] Default priority is `보통`
- [x] Status/priority will be selectable later, but read-side defaults are exposed now

## Backend work
- [x] Add helper functions in `app.py` for create-flow option loading and prefill calculation
- [x] Add `GET /api/create/options`
- [x] Add `GET /api/create/prefill`
- [x] Reuse existing network handling (`get_request_network`, `get_redmine`)
- [x] Return JSON responses matching current route style
- [x] Keep errors consistent with existing API patterns

## Deferred
- [ ] Frontend form rendering
- [ ] Frontend submit flow
- [ ] Backend create/write endpoint
- [ ] Attachment upload
- [ ] Validation UX beyond backend response contracts

## Acceptance criteria
- [x] `/api/create/options` returns dynamic project data and read-side option data
- [x] `/api/create/prefill` returns computed defaults for the selected project/tracker scope
- [x] Assignee options are loaded from the selected project's assignable users and then filtered to 김윤권/김창민/전상수/이수호
- [x] Default title fallback uses tracker name when the scoped first issue is being created
- [x] Default parent is the oldest root issue candidate and is exposed as editable data
- [x] Status defaults to `신규`, priority defaults to `보통`
- [x] No create/write behavior is introduced in phase 1

## QA
- [x] `python3 -m py_compile app.py` passes
- [x] `GET /api/create/options` responds with `projects`, `trackers`, `statuses`, `priorities`
- [x] `GET /api/projects/<project_id>/assignable-users` responds with project-scoped assignee candidates filtered to 김윤권/김창민/전상수/이수호
- [x] `GET /api/create/prefill` responds with `subject_default`, `parent_issue_default_id`, `parent_issue_options`, `default_status`, `default_priority`
