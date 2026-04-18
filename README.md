# Redmine local development

## Prerequisites

- Use `python3` in this workspace.
- Prepare a Redmine username/password account that can read and create issues in the target Redmine.
- Make sure you can reach the Redmine URL you plan to test from your current network.

## Install dependencies

```bash
python3 -m pip install -r requirements.txt
```

If you prefer a virtual environment, create a fresh local one for your current OS:

```bash
python3 -m venv .venv-local
source .venv-local/bin/activate
python3 -m pip install -r requirements.txt
```

This repository may already contain a platform-specific `.venv` directory from another environment. If that existing directory is not usable on your machine, ignore it and use `.venv-local` instead.

## Configure environment variables

Copy `.env.example` to `.env` and fill in real values:

```bash
cp .env.example .env
```

Required variables:

- `REDMINE_URL_INTERNAL`: Base URL used when `network=internal`
- `REDMINE_URL_EXTERNAL`: Base URL used when `network=external`
- `SECRET_KEY`: Flask session signing key

Optional variables:

- `SESSION_FILE_DIR`: Filesystem directory used by Flask-Session. If omitted, the app uses `/tmp/redmine-helper-sessions`.
- `APP_MODE`: App behavior mode. Supported values are `development` and `deploy`; missing or invalid values fall back to `development`.
- `DEFAULT_NETWORK`: Initial UI selection and backend fallback network. Supported values are `internal` and `external`; missing or invalid values fall back to `internal`.

Notes:

- Do not commit `.env`.
- `APP_MODE=development` keeps the current network selector behavior and continues to honor `DEFAULT_NETWORK`.
- `APP_MODE=deploy` hides the selector in the UI, always uses the external Redmine target, and ignores any incoming `network` request value.
- If your local machine can only access one Redmine endpoint, you can temporarily set both URL variables to the same reachable base URL.
- Do not add a trailing slash unless you want it normalized automatically.
- Set `DEFAULT_NETWORK=external` if you want the app to open with the external network selected by default.
- The app now stores the logged-in Redmine account in a server-side filesystem session. Do not point `SESSION_FILE_DIR` at a path that should be committed.
- The app keeps the Redmine password only in server process memory and stores a session reference on disk. If the app process restarts, users must log in again.
- For the same reason, keep production-style runs on a single Gunicorn worker unless you redesign the credential store to be shared across workers.
- This login flow depends on Redmine username/password auth. If your Redmine account enforces 2FA or disables password-based API access, login may fail.
- Use HTTPS for real Redmine base URLs. Plain HTTP is only tolerated for localhost-style mock testing.

## Run locally

```bash
python3 app.py
```

The app runs on `http://localhost:5000` by default.

For a production-style run:

```bash
gunicorn --workers 1 app:app
```

The current auth design keeps the Redmine password only in the serving process memory, so multi-worker Gunicorn is not supported in this version.

## How to test against a real Redmine

1. Open `http://localhost:5000`.
2. In `APP_MODE=development`, start with your configured `DEFAULT_NETWORK`, or switch to `external` first unless you know the internal URL is reachable from your machine.
3. In `APP_MODE=deploy`, the app always searches against the external Redmine and hides the network selector.
4. Log in with a valid Redmine username/password.
5. Search with a known issue ID first.
6. Confirm issue details, journals, attachments, and the external Redmine entry button render correctly.
7. Open the issue create panel and confirm options/prefill/issue creation work with your account permissions.
8. Repeat with the `internal` option only when you are in `APP_MODE=development` and that network is reachable.

You can also verify API responses directly, but protected endpoints now require a login session cookie and CSRF token first:

1. `GET /api/auth/session?network=external` to receive a CSRF token and session cookie.
2. `POST /api/auth/login` with JSON `{ "username": "...", "password": "...", "network": "external" }` and the `X-CSRF-Token` header.
3. Call protected endpoints such as `/api/search?q=<issue-id>&network=external`, `/api/issue/<issue-id>?network=external`, and `/api/attachment/<attachment-id>?network=external` with the same cookie jar.

## Troubleshooting

- If app import or startup fails with a missing environment variable error, copy `.env.example` to `.env` and fill the required values.
- If `APP_MODE` is missing or invalid, the app safely falls back to `development` mode.
- If login fails with authentication errors, verify the Redmine username/password and whether password-based API access is allowed for that account.
- If only one network option fails, the corresponding Redmine base URL may be unreachable from your current machine or VPN state.
