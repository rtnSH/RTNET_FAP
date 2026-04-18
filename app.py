import os
import re
import secrets
from functools import wraps
from urllib.parse import urlparse

from flask import Flask, render_template, request, jsonify, Response, session
from flask_session import Session
from redminelib import Redmine
import requests
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
AUTH_CREDENTIALS = {}


class ConfigError(Exception):
    pass


class CreateIssueValidationError(Exception):
    pass


class AuthenticationRequiredError(Exception):
    pass


class AuthenticationFailedError(Exception):
    pass


class CsrfValidationError(Exception):
    pass

REDMINE_URL_INTERNAL = os.getenv('REDMINE_URL_INTERNAL')
REDMINE_URL_EXTERNAL = os.getenv('REDMINE_URL_EXTERNAL')
SECRET_KEY = os.getenv('SECRET_KEY')
SESSION_FILE_DIR = os.getenv('SESSION_FILE_DIR')

ASSIGNEE_MAP = {
    'admin': {'label': '김윤권', 'login': 'admin'},
    'cmkim': {'label': '김창민', 'login': 'cmkim'},
    'ssjeon': {'label': '전상수', 'login': 'ssjeon'},
    'sh.lee': {'label': '이수호', 'login': 'sh.lee'},
}
DEFAULT_TRACKER_NAME = '4_오류수정'
DEFAULT_STATUS_NAME = '신규'
DEFAULT_PRIORITY_NAME = '보통'
TITLE_SEGMENT_PATTERN = re.compile(r'^(\d+)[_\-](\d+)(?:[_\-]\d+)*')


def normalize_network(network_type):
    normalized = (network_type or '').strip().lower()
    return normalized if normalized in {'internal', 'external'} else 'internal'


def normalize_app_mode(app_mode):
    normalized = (app_mode or '').strip().lower()
    return normalized if normalized in {'development', 'deploy'} else 'development'


DEFAULT_NETWORK = normalize_network(os.getenv('DEFAULT_NETWORK'))
APP_MODE = normalize_app_mode(os.getenv('APP_MODE'))


def normalize_base_url(url):
    return url.rstrip('/') if url else url


REDMINE_URL_INTERNAL = normalize_base_url(REDMINE_URL_INTERNAL)
REDMINE_URL_EXTERNAL = normalize_base_url(REDMINE_URL_EXTERNAL)

session_file_dir = SESSION_FILE_DIR or os.path.join('/tmp', 'redmine-helper-sessions')
os.makedirs(session_file_dir, exist_ok=True)

app.config.update(
    SECRET_KEY=SECRET_KEY or 'dev-secret-key-change-me',
    SESSION_TYPE='filesystem',
    SESSION_FILE_DIR=session_file_dir,
    SESSION_PERMANENT=False,
    SESSION_USE_SIGNER=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=APP_MODE == 'deploy',
)
Session(app)


def validate_config():
    missing = []

    if not REDMINE_URL_INTERNAL:
        missing.append('REDMINE_URL_INTERNAL')
    if not REDMINE_URL_EXTERNAL:
        missing.append('REDMINE_URL_EXTERNAL')
    if not SECRET_KEY:
        missing.append('SECRET_KEY')

    if missing:
        raise ConfigError(
            'Missing required environment variables: '
            f"{', '.join(missing)}. Copy .env.example to .env and fill in real Redmine values."
        )

    invalid_urls = [
        name
        for name, value in {
            'REDMINE_URL_INTERNAL': REDMINE_URL_INTERNAL,
            'REDMINE_URL_EXTERNAL': REDMINE_URL_EXTERNAL,
        }.items()
        if not is_secure_redmine_url(value)
    ]

    if invalid_urls:
        raise ConfigError(
            'Redmine base URLs must use HTTPS unless they point to localhost for local-only testing: '
            f"{', '.join(invalid_urls)}"
        )


def json_error(message, status_code, code=None):
    payload = {'error': message}
    if code:
        payload['code'] = code
    return jsonify(payload), status_code


def get_effective_network(requested_network=None):
    if APP_MODE == 'deploy':
        return 'external'

    normalized_network = (requested_network or '').strip().lower()
    if normalized_network in {'internal', 'external'}:
        return normalized_network
    return DEFAULT_NETWORK


def get_request_network():
    return get_effective_network((request.args.get('network') or '').strip().lower())


def ensure_csrf_token():
    token = session.get('csrf_token')
    if not token:
        token = secrets.token_urlsafe(32)
        session['csrf_token'] = token
    return token


def regenerate_session_id():
    regenerate = getattr(app.session_interface, 'regenerate', None)
    if callable(regenerate):
        regenerate(session)


def rotate_session_boundary():
    session['_rotation_marker'] = secrets.token_urlsafe(8)
    regenerate_session_id()
    session.pop('_rotation_marker', None)


def clear_auth_session(preserve_csrf=True):
    credential_id = session.get('credential_id')
    if credential_id:
        AUTH_CREDENTIALS.pop(credential_id, None)

    csrf_token = session.get('csrf_token') if preserve_csrf else None
    session.clear()
    if preserve_csrf and csrf_token:
        session['csrf_token'] = csrf_token


def build_user_payload(username, display_name=None):
    return {
        'username': username,
        'display_name': display_name or username,
    }


def get_session_user():
    username = session.get('redmine_username')
    credential_id = session.get('credential_id')
    credential = AUTH_CREDENTIALS.get(credential_id)

    if not username or not credential_id or not credential:
        clear_auth_session()
        raise AuthenticationRequiredError('로그인이 필요합니다.')

    return {
        'username': username,
        'password': credential['password'],
        'display_name': session.get('redmine_display_name') or username,
    }


def is_secure_redmine_url(url):
    parsed = urlparse(url or '')
    hostname = (parsed.hostname or '').lower()
    return parsed.scheme == 'https' or hostname in {'localhost', '127.0.0.1'}


validate_config()


def remember_session_user(user_payload, password):
    credential_id = secrets.token_urlsafe(32)
    AUTH_CREDENTIALS[credential_id] = {
        'password': password,
    }
    session['credential_id'] = credential_id
    session['redmine_username'] = user_payload['username']
    session['redmine_display_name'] = user_payload['display_name']


def get_redmine(network_type):
    validate_config()
    user = get_session_user()
    url = get_redmine_base_url(network_type)
    return Redmine(url, username=user['username'], password=user['password'])


def get_redmine_base_url(network_type):
    validate_config()
    network_type = normalize_network(network_type)
    return REDMINE_URL_EXTERNAL if network_type == 'external' else REDMINE_URL_INTERNAL


def get_redmine_basic_auth():
    user = get_session_user()
    return (user['username'], user['password'])


def verify_redmine_credentials(network_type, username, password):
    response = requests.get(
        f"{get_redmine_base_url(network_type)}/users/current.json",
        auth=(username, password),
        timeout=10,
    )

    if response.status_code == 401:
        raise AuthenticationFailedError('Redmine 로그인 정보가 올바르지 않거나 2차 인증 정책으로 인해 비밀번호 로그인이 허용되지 않습니다.')

    response.raise_for_status()

    user = (response.json() or {}).get('user') or {}
    first_name = (user.get('firstname') or '').strip()
    last_name = (user.get('lastname') or '').strip()
    display_name = ' '.join(part for part in [last_name, first_name] if part).strip() or user.get('login') or username
    return build_user_payload(user.get('login') or username, display_name)


def require_auth(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        try:
            get_session_user()
        except AuthenticationRequiredError:
            return json_error('로그인이 필요합니다.', 401, code='auth_required')
        return view_func(*args, **kwargs)

    return wrapped


def require_csrf(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        expected_token = ensure_csrf_token()
        provided_token = (request.headers.get('X-CSRF-Token') or '').strip()
        if not provided_token or provided_token != expected_token:
            return json_error('유효하지 않은 요청입니다. 페이지를 새로고침한 뒤 다시 시도해주세요.', 403, code='csrf_invalid')
        return view_func(*args, **kwargs)

    return wrapped


def is_authentication_error(error):
    message = str(error).lower()
    return any(keyword in message for keyword in ['401', 'unauthorized', 'authentication failed', 'invalid credentials'])


def is_permission_error(error):
    message = str(error).lower()
    return any(keyword in message for keyword in ['403', 'forbidden', 'permission denied'])


def handle_redmine_error(error, default_status=404):
    if isinstance(error, AuthenticationRequiredError):
        return json_error('로그인이 필요합니다.', 401, code='auth_required')

    if isinstance(error, AuthenticationFailedError) or is_authentication_error(error):
        clear_auth_session()
        return json_error('Redmine 로그인 세션이 만료되었거나 인증에 실패했습니다. 다시 로그인해주세요.', 401, code='auth_invalid')

    if is_permission_error(error):
        return json_error('현재 로그인한 Redmine 계정에 이 작업 권한이 없습니다.', 403, code='forbidden')

    return json_error(str(error), default_status)


def get_initial_network():
    return 'external' if APP_MODE == 'deploy' else DEFAULT_NETWORK


@app.route('/api/auth/session')
def get_auth_session():
    csrf_token = ensure_csrf_token()
    authenticated = bool(session.get('redmine_username') and session.get('credential_id') in AUTH_CREDENTIALS)

    if not authenticated and session.get('redmine_username'):
        clear_auth_session()
        csrf_token = ensure_csrf_token()

    return jsonify({
        'authenticated': authenticated,
        'csrf_token': csrf_token,
        'user': build_user_payload(
            session.get('redmine_username') or '',
            session.get('redmine_display_name') or session.get('redmine_username') or ''
        ) if authenticated else None,
        'network': get_request_network(),
    })


@app.route('/api/auth/login', methods=['POST'])
@require_csrf
def login():
    payload = request.get_json(silent=True) or {}
    username = (payload.get('username') or '').strip()
    password = (payload.get('password') or '').strip()
    network_type = get_effective_network(payload.get('network'))

    if not username or not password:
        return json_error('아이디와 비밀번호를 모두 입력해주세요.', 400, code='login_invalid')

    try:
        verified_user = verify_redmine_credentials(network_type, username, password)
        clear_auth_session(preserve_csrf=False)
        rotate_session_boundary()
        remember_session_user(verified_user, password)
        session['csrf_token'] = secrets.token_urlsafe(32)

        return jsonify({
            'authenticated': True,
            'csrf_token': session['csrf_token'],
            'user': verified_user,
            'network': network_type,
        })
    except AuthenticationFailedError as error:
        return json_error(str(error), 401, code='login_failed')
    except requests.exceptions.RequestException as error:
        return json_error(f'Redmine 서버에 연결하지 못했습니다: {error}', 504, code='login_unreachable')


@app.route('/api/auth/logout', methods=['POST'])
@require_csrf
def logout():
    clear_auth_session(preserve_csrf=False)
    rotate_session_boundary()
    session['csrf_token'] = secrets.token_urlsafe(32)
    return jsonify({'authenticated': False, 'csrf_token': session['csrf_token']})

@app.route('/')
def index():
    default_network = get_initial_network()
    return render_template(
        'index.html',
        app_mode=APP_MODE,
        default_network=default_network,
        redmine_entry_url=get_redmine_base_url(default_network),
        redmine_url_internal=REDMINE_URL_INTERNAL,
        redmine_url_external=REDMINE_URL_EXTERNAL,
    )

@app.route('/api/search')
@require_auth
def search_issue():
    query = request.args.get('q', '')
    network_type = get_request_network()
    if not query:
        return jsonify({'error': 'Search query is required'}), 400
    
    try:
        redmine = get_redmine(network_type)
        
        # Check if query is an ID
        if query.isdigit():
            try:
                issue = redmine.issue.get(query, include=['journals', 'attachments'])
                return jsonify({'type': 'single', 'data': format_issue(issue)})
            except:
                pass # If ID search fails, proceed to keyword search
        
        # Keyword search
        issues = redmine.issue.filter(subject=f'~{query}', status_id='*')

        results = [format_issue_summary(issue) for issue in issues]
        
        return jsonify({'type': 'list', 'data': results})
    except ConfigError as e:
        return json_error(str(e), 500)
    except Exception as e:
        return handle_redmine_error(e)

@app.route('/api/recent')
@require_auth
def get_recent_issues():
    network_type = get_request_network()
    try:
        limit = min(max(request.args.get('limit', default=10, type=int) or 10, 1), 20)
        redmine_url = f"{get_redmine_base_url(network_type)}/issues.json"
        response = requests.get(
            redmine_url,
            auth=get_redmine_basic_auth(),
            params={
                'status_id': '*',
                'sort': 'updated_on:desc',
                'limit': limit,
            },
            timeout=10,
        )
        response.raise_for_status()
        issues = response.json().get('issues', [])
        results = [format_issue_summary_from_json(issue) for issue in issues]
        return jsonify({'type': 'list', 'data': results})
    except ConfigError as e:
        return json_error(str(e), 500)
    except requests.exceptions.RequestException as e:
        status_code = getattr(getattr(e, 'response', None), 'status_code', None)
        if status_code == 401:
            clear_auth_session()
            return json_error('Redmine 로그인 세션이 만료되었거나 인증에 실패했습니다. 다시 로그인해주세요.', 401, code='auth_invalid')
        if status_code == 403:
            return json_error('현재 로그인한 Redmine 계정에 최근 이슈를 조회할 권한이 없습니다.', 403, code='forbidden')
        return json_error(f'최근 이슈를 불러오지 못했습니다: {e}', 504)
    except Exception as e:
        return handle_redmine_error(e)

@app.route('/api/issue/<int:issue_id>')
@require_auth
def get_issue_detail(issue_id):
    network_type = get_request_network()
    try:
        redmine = get_redmine(network_type)
        issue = redmine.issue.get(issue_id, include=['journals', 'attachments'])
        return jsonify(format_issue(issue))
    except ConfigError as e:
        return json_error(str(e), 500)
    except Exception as e:
        return handle_redmine_error(e)

@app.route('/api/attachment/<int:attachment_id>')
@require_auth
def get_attachment(attachment_id):
    network_type = get_request_network()
    try:
        redmine = get_redmine(network_type)
        attachment = redmine.attachment.get(attachment_id)
        
        resp = requests.get(
            attachment.content_url,
            auth=get_redmine_basic_auth(),
            stream=True,
            timeout=10,
        )
        resp.raise_for_status()
        
        return Response(
            resp.iter_content(chunk_size=1024),
            content_type=resp.headers.get('Content-Type'),
            headers={
                'Content-Disposition': f'inline; filename="{attachment.filename}"'
            }
        )
    except ConfigError as e:
        return json_error(str(e), 500)
    except requests.exceptions.RequestException as e:
        status_code = getattr(getattr(e, 'response', None), 'status_code', None)
        if status_code == 401:
            clear_auth_session()
            return json_error('Redmine 로그인 세션이 만료되었거나 인증에 실패했습니다. 다시 로그인해주세요.', 401, code='auth_invalid')
        if status_code == 403:
            return json_error('현재 로그인한 Redmine 계정에 첨부 파일을 볼 권한이 없습니다.', 403, code='forbidden')
        return json_error(f'첨부 파일을 불러오지 못했습니다: {e}', 504)
    except Exception as e:
        return handle_redmine_error(e)


@app.route('/api/create/options')
@require_auth
def get_create_options():
    network_type = get_request_network()
    try:
        redmine = get_redmine(network_type)
        projects = get_project_options(redmine)
        trackers = get_tracker_options(redmine)
        statuses = get_status_options(redmine)
        priorities = get_priority_options(redmine)

        return jsonify({
            'projects': projects,
            'trackers': trackers,
            'statuses': statuses,
            'priorities': priorities,
            'assignees': get_assignee_options(),
            'defaults': {
                'tracker': find_named_option(trackers, DEFAULT_TRACKER_NAME),
                'status': find_named_option(statuses, DEFAULT_STATUS_NAME),
                'priority': find_named_option(priorities, DEFAULT_PRIORITY_NAME),
            }
        })
    except ConfigError as e:
        return json_error(str(e), 500)
    except Exception as e:
        return handle_redmine_error(e)


@app.route('/api/create/prefill')
@require_auth
def get_create_prefill():
    project_id = (request.args.get('project_id') or '').strip()
    tracker_id = (request.args.get('tracker_id') or '').strip()
    network_type = get_request_network()

    if not project_id or not tracker_id:
        return jsonify({'error': 'project_id와 tracker_id는 필수입니다.'}), 400

    try:
        redmine = get_redmine(network_type)
        tracker = get_tracker_by_id(redmine, tracker_id)
        if not tracker:
            return jsonify({'error': '유효한 tracker_id를 찾지 못했습니다.'}), 404

        scoped_issues = list(redmine.issue.filter(
            project_id=project_id,
            tracker_id=tracker_id,
            status_id='*',
            sort='created_on:asc',
        ))

        subject_default, subject_mode = resolve_subject_default(scoped_issues, tracker.name)
        parent_issue_options = build_parent_issue_options(scoped_issues)
        statuses = get_status_options(redmine)
        priorities = get_priority_options(redmine)
        default_parent = parent_issue_options[0] if parent_issue_options else None

        return jsonify({
            'project_id': project_id,
            'tracker_id': tracker_id,
            'subject_default': subject_default,
            'subject_mode': subject_mode,
            'parent_issue_default_id': default_parent['id'] if default_parent else None,
            'parent_issue_options': parent_issue_options,
            'default_status': find_named_option(statuses, DEFAULT_STATUS_NAME),
            'default_priority': find_named_option(priorities, DEFAULT_PRIORITY_NAME),
            'default_description': '',
        })
    except ConfigError as e:
        return json_error(str(e), 500)
    except Exception as e:
        return handle_redmine_error(e)


@app.route('/api/issues', methods=['POST'])
@require_auth
@require_csrf
def create_issue():
    network_type = get_request_network()
    try:
        payload = parse_create_issue_payload()
        redmine = get_redmine(network_type)
        project = get_project_by_id(redmine, payload['project_id'])
        if not project:
            raise CreateIssueValidationError('유효한 프로젝트를 찾지 못했습니다.')

        tracker = get_tracker_by_id(redmine, payload['tracker_id'])
        if not tracker:
            raise CreateIssueValidationError('유효한 유형을 찾지 못했습니다.')

        statuses = get_status_options(redmine)
        priorities = get_priority_options(redmine)
        selected_status = resolve_selected_option(statuses, payload['status_id'], DEFAULT_STATUS_NAME, '상태')
        selected_priority = resolve_selected_option(priorities, payload['priority_id'], DEFAULT_PRIORITY_NAME, '우선순위')
        assignee = get_assignee_user(redmine, payload['assignee_key'])

        scoped_issues = list(redmine.issue.filter(
            project_id=payload['project_id'],
            tracker_id=payload['tracker_id'],
            status_id='*',
            sort='created_on:asc',
        ))
        parent_issue_options = build_parent_issue_options(scoped_issues)
        parent_issue_id = resolve_parent_issue_id(payload['parent_issue_id'], parent_issue_options)
        uploads = upload_issue_files(redmine, payload['files'])

        issue = redmine.issue.create(
            project_id=payload['project_id'],
            tracker_id=payload['tracker_id'],
            subject=payload['subject'],
            description=payload['description'],
            status_id=selected_status['id'],
            priority_id=selected_priority['id'],
            assigned_to_id=assignee['id'],
            parent_issue_id=parent_issue_id,
            uploads=uploads,
        )

        return jsonify(format_created_issue_response(issue)), 201
    except CreateIssueValidationError as e:
        return json_error(str(e), 400)
    except ConfigError as e:
        return json_error(str(e), 500)
    except Exception as e:
        return handle_redmine_error(e)


def build_project_hierarchy(project_name=None, parent_project_name=None):
    names = [name for name in [parent_project_name, project_name] if name]
    if len(names) == 2 and names[0] == names[1]:
        names = names[:1]

    return {
        'project_name': project_name,
        'parent_project_name': parent_project_name,
        'project_hierarchy': ' / '.join(names)
    }


def format_project_hierarchy(project):
    project_name = getattr(project, 'name', None) if project else None

    try:
        parent_project = getattr(project, 'parent', None) if project else None
    except Exception:
        parent_project = None

    parent_project_name = getattr(parent_project, 'name', None) if parent_project else None
    return build_project_hierarchy(project_name, parent_project_name)


def format_project_hierarchy_from_json(issue):
    project = issue.get('project') or {}
    if not isinstance(project, dict):
        project = {}

    parent_project = project.get('parent') or {}
    if not isinstance(parent_project, dict):
        parent_project = {}

    return build_project_hierarchy(project.get('name'), parent_project.get('name'))

def format_issue(issue):
    internal_issue_url = f"{REDMINE_URL_INTERNAL}/issues/{issue.id}"

    journals = []
    for journal in issue.journals:
        details = []
        for detail in journal.details:
            details.append({
                'property': detail.get('property'),
                'name': detail.get('name'),
                'old_value': detail.get('old_value'),
                'new_value': detail.get('new_value')
            })
        
        journals.append({
            'id': journal.id,
            'user': journal.user.name,
            'notes': journal.notes,
            'created_on': journal.created_on.isoformat(),
            'details': details
        })
    
    attachments = []
    for att in getattr(issue, 'attachments', []):
        attachments.append({
            'id': att.id,
            'filename': att.filename,
            'filesize': att.filesize,
            'content_type': att.content_type,
            'description': att.description
        })

    return {
        'id': issue.id,
        'subject': issue.subject,
        'status': issue.status.name,
        'priority': issue.priority.name,
        'author': issue.author.name,
        'assigned_to': issue.assigned_to.name if getattr(issue, 'assigned_to', None) else 'None',
        'description': issue.description,
        'created_on': issue.created_on.isoformat(),
        'updated_on': issue.updated_on.isoformat(),
        'journals': journals[::-1],
        'attachments': attachments,
        'redmine_url_internal': internal_issue_url,
        'redmine_url_external': f"{REDMINE_URL_EXTERNAL}/issues/{issue.id}",
        **format_project_hierarchy(getattr(issue, 'project', None))
    }


def format_issue_summary(issue):
    return {
        'id': issue.id,
        'subject': issue.subject,
        'status': issue.status.name,
        'updated_on': issue.updated_on.isoformat(),
        **format_project_hierarchy(getattr(issue, 'project', None))
    }


def format_issue_summary_from_json(issue):
    status = issue.get('status') or {}
    return {
        'id': issue.get('id'),
        'subject': issue.get('subject'),
        'status': status.get('name', 'Unknown'),
        'updated_on': issue.get('updated_on'),
        **format_project_hierarchy_from_json(issue)
    }


def get_project_options(redmine):
    projects = [format_project_option(project) for project in redmine.project.all()]
    children_by_parent_id = {}
    root_projects = []

    for project in projects:
        parent_id = project.get('parent_id')
        if parent_id is None:
            root_projects.append(project)
            continue

        children_by_parent_id.setdefault(str(parent_id), []).append(project)

    ordered_projects = []

    def append_project_branch(project, depth=0):
        project['depth'] = depth
        ordered_projects.append(project)

        for child in sort_named_resources(children_by_parent_id.get(str(project.get('id')), [])):
            append_project_branch(child, depth + 1)

    for root_project in sort_named_resources(root_projects):
        append_project_branch(root_project)

    return ordered_projects


def get_tracker_options(redmine):
    trackers = [format_tracker_option(tracker) for tracker in redmine.tracker.all()]
    return sort_named_resources(trackers)


def get_tracker_by_id(redmine, tracker_id):
    tracker_id = str(tracker_id)
    return next((tracker for tracker in redmine.tracker.all() if str(getattr(tracker, 'id', '')) == tracker_id), None)


def get_status_options(redmine):
    statuses = [format_named_option(status) for status in redmine.issue_status.all()]
    return sort_named_resources(statuses)


def get_priority_options(redmine):
    priorities = [format_named_option(priority) for priority in redmine.enumeration.filter(resource='issue_priorities')]
    return sort_named_resources(priorities)


def get_assignee_options():
    return [
        {
            'key': key,
            'label': value['label'],
            'login': value['login'],
        }
        for key, value in ASSIGNEE_MAP.items()
    ]


def format_project_option(project):
    parent = None

    try:
        parent = getattr(project, 'parent', None)
    except Exception:
        parent = None

    return {
        'id': getattr(project, 'id', None),
        'name': getattr(project, 'name', None),
        'identifier': getattr(project, 'identifier', None),
        'parent_id': getattr(parent, 'id', None) if parent else None,
        'parent_name': getattr(parent, 'name', None) if parent else None,
        'depth': 0,
    }


def format_tracker_option(tracker):
    return {
        'id': getattr(tracker, 'id', None),
        'name': getattr(tracker, 'name', None),
    }


def format_named_option(resource):
    return {
        'id': getattr(resource, 'id', None),
        'name': getattr(resource, 'name', None),
    }


def find_named_option(options, target_name):
    return next((option for option in options if option.get('name') == target_name), None)


def find_option_by_id(options, target_id):
    target_id = str(target_id)
    return next((option for option in options if str(option.get('id')) == target_id), None)


def get_name_sort_key(name):
    normalized_name = (name or '').strip()
    match = re.match(r'^(\d+)', normalized_name)

    if not match:
        return (1, float('inf'), normalized_name.lower())

    return (0, int(match.group(1)), normalized_name.lower())


def sort_named_resources(resources):
    return sorted(resources, key=lambda item: get_name_sort_key(item.get('name')))


def get_tracker_prefix(tracker_name):
    match = re.match(r'^(\d+)', (tracker_name or '').strip())
    if not match:
        return None

    return int(match.group(1))


def get_project_by_id(redmine, project_id):
    project_id = str(project_id)
    return next((project for project in redmine.project.all() if str(getattr(project, 'id', '')) == project_id), None)


def parse_create_issue_payload():
    payload = {
        'project_id': clean_required_field(request.form.get('project_id'), 'project_id'),
        'tracker_id': clean_required_field(request.form.get('tracker_id'), 'tracker_id'),
        'subject': clean_required_field(request.form.get('subject'), 'subject'),
        'description': clean_optional_field(request.form.get('description')) or '',
        'status_id': clean_optional_field(request.form.get('status_id')),
        'priority_id': clean_optional_field(request.form.get('priority_id')),
        'parent_issue_id': clean_optional_field(request.form.get('parent_issue_id')),
        'assignee_key': clean_required_field(request.form.get('assignee_key'), 'assignee_key'),
        'files': [file for file in request.files.getlist('files') if file and file.filename],
    }
    return payload


def clean_required_field(value, field_name):
    cleaned = (value or '').strip()
    if not cleaned:
        raise CreateIssueValidationError(f'{field_name}는 필수입니다.')
    return cleaned


def clean_optional_field(value):
    cleaned = (value or '').strip()
    return cleaned or None


def resolve_selected_option(options, selected_id, default_name, field_label):
    if selected_id:
        option = find_option_by_id(options, selected_id)
        if not option:
            raise CreateIssueValidationError(f'유효한 {field_label}을 찾지 못했습니다.')
        return option

    default_option = find_named_option(options, default_name)
    if not default_option:
        raise CreateIssueValidationError(f'기본 {field_label}을 찾지 못했습니다.')
    return default_option


def get_assignee_user(redmine, assignee_key):
    assignee = ASSIGNEE_MAP.get(assignee_key)
    if not assignee:
        raise CreateIssueValidationError('유효한 담당자를 선택해주세요.')

    candidates = redmine.user.filter(name=assignee['login'])
    for user in candidates:
        user_login = getattr(user, 'login', '')
        user_name = getattr(user, 'name', '')
        if user_login == assignee['login'] or user_name == assignee['label']:
            return {
                'id': getattr(user, 'id', None),
                'login': user_login,
                'label': assignee['label'],
            }

    raise CreateIssueValidationError(f"담당자 계정({assignee['login']})을 찾지 못했습니다.")


def resolve_parent_issue_id(selected_parent_issue_id, parent_issue_options):
    if selected_parent_issue_id:
        selected_option = find_option_by_id(parent_issue_options, selected_parent_issue_id)
        if not selected_option:
            raise CreateIssueValidationError('유효한 상위일감을 찾지 못했습니다.')
        return selected_option['id']

    return parent_issue_options[0]['id'] if parent_issue_options else None


def upload_issue_files(redmine, files):
    uploads = []
    for file in files:
        upload = redmine.upload(file.stream, filename=file.filename)
        uploads.append({
            'token': upload['token'],
            'filename': file.filename,
            'content_type': file.mimetype,
        })
    return uploads


def format_created_issue_response(issue):
    return {
        'id': issue.id,
        'subject': issue.subject,
        'redmine_url_internal': f"{REDMINE_URL_INTERNAL}/issues/{issue.id}",
        'redmine_url_external': f"{REDMINE_URL_EXTERNAL}/issues/{issue.id}",
    }


def resolve_subject_default(issues, tracker_name):
    if not issues:
        return tracker_name, 'tracker_name'

    tracker_prefix = get_tracker_prefix(tracker_name)
    highest_number = None
    highest_width = 2

    for issue in issues:
        subject = (getattr(issue, 'subject', '') or '').strip()
        match = TITLE_SEGMENT_PATTERN.match(subject)
        if not match:
            continue

        prefix_number = int(match.group(1))
        if tracker_prefix is not None and prefix_number != tracker_prefix:
            continue

        current_number = int(match.group(2))
        current_width = max(len(match.group(2)), 2)

        if highest_number is None or current_number > highest_number:
            highest_number = current_number
            highest_width = current_width

    if highest_number is None:
        return tracker_name, 'tracker_name'

    if tracker_prefix is None:
        return tracker_name, 'tracker_name'

    next_number = highest_number + 1
    padded_prefix = str(tracker_prefix).zfill(2)
    padded_number = str(next_number).zfill(highest_width)
    return f"{padded_prefix}_{padded_number} ", 'increment'


def build_parent_issue_options(issues):
    root_issues = []
    for issue in issues:
        try:
            parent = getattr(issue, 'parent', None)
        except Exception:
            parent = None

        if parent:
            continue

        root_issues.append({
            'id': getattr(issue, 'id', None),
            'subject': getattr(issue, 'subject', None),
        })

    return root_issues

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
