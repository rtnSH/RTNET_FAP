import os
import re
from flask import Flask, render_template, request, jsonify, Response
from redminelib import Redmine
import requests
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)


class ConfigError(Exception):
    pass


class CreateIssueValidationError(Exception):
    pass

REDMINE_URL_INTERNAL = os.getenv('REDMINE_URL_INTERNAL')
REDMINE_URL_EXTERNAL = os.getenv('REDMINE_URL_EXTERNAL')
REDMINE_API_KEY = os.getenv('REDMINE_API_KEY')

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


def validate_config():
    missing = []

    if not REDMINE_URL_INTERNAL:
        missing.append('REDMINE_URL_INTERNAL')
    if not REDMINE_URL_EXTERNAL:
        missing.append('REDMINE_URL_EXTERNAL')
    if not REDMINE_API_KEY:
        missing.append('REDMINE_API_KEY')

    if missing:
        raise ConfigError(
            'Missing required environment variables: '
            f"{', '.join(missing)}. Copy .env.example to .env and fill in real Redmine values."
        )


validate_config()

def get_redmine(network_type):
    validate_config()
    network_type = normalize_network(network_type)
    url = REDMINE_URL_EXTERNAL if network_type == 'external' else REDMINE_URL_INTERNAL
    return Redmine(url, key=REDMINE_API_KEY)


def get_redmine_base_url(network_type):
    validate_config()
    network_type = normalize_network(network_type)
    return REDMINE_URL_EXTERNAL if network_type == 'external' else REDMINE_URL_INTERNAL


def get_request_network():
    if APP_MODE == 'deploy':
        return 'external'

    requested_network = (request.args.get('network') or '').strip().lower()
    if requested_network in {'internal', 'external'}:
        return requested_network
    return DEFAULT_NETWORK


def get_initial_network():
    return 'external' if APP_MODE == 'deploy' else DEFAULT_NETWORK

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
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 404

@app.route('/api/recent')
def get_recent_issues():
    network_type = get_request_network()
    try:
        limit = min(max(request.args.get('limit', default=10, type=int) or 10, 1), 20)
        redmine_url = f"{get_redmine_base_url(network_type)}/issues.json"
        response = requests.get(
            redmine_url,
            headers={'X-Redmine-API-Key': REDMINE_API_KEY},
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
        return jsonify({'error': str(e)}), 500
    except requests.exceptions.RequestException as e:
        return jsonify({'error': f'최근 이슈를 불러오지 못했습니다: {e}'}), 504
    except Exception as e:
        return jsonify({'error': str(e)}), 404

@app.route('/api/issue/<int:issue_id>')
def get_issue_detail(issue_id):
    network_type = get_request_network()
    try:
        redmine = get_redmine(network_type)
        issue = redmine.issue.get(issue_id, include=['journals', 'attachments'])
        return jsonify(format_issue(issue))
    except ConfigError as e:
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 404

@app.route('/api/attachment/<int:attachment_id>')
def get_attachment(attachment_id):
    network_type = get_request_network()
    try:
        redmine = get_redmine(network_type)
        attachment = redmine.attachment.get(attachment_id)
        
        headers = {'X-Redmine-API-Key': REDMINE_API_KEY}
        resp = requests.get(attachment.content_url, headers=headers, stream=True)
        
        return Response(
            resp.iter_content(chunk_size=1024),
            content_type=resp.headers.get('Content-Type'),
            headers={
                'Content-Disposition': f'inline; filename="{attachment.filename}"'
            }
        )
    except ConfigError as e:
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 404


@app.route('/api/create/options')
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
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 404


@app.route('/api/create/prefill')
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
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 404


@app.route('/api/issues', methods=['POST'])
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
        return jsonify({'error': str(e)}), 400
    except ConfigError as e:
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 404


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
