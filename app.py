import os
from flask import Flask, render_template, request, jsonify, Response
from redminelib import Redmine
import requests
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)


class ConfigError(Exception):
    pass

REDMINE_URL_INTERNAL = os.getenv('REDMINE_URL_INTERNAL')
REDMINE_URL_EXTERNAL = os.getenv('REDMINE_URL_EXTERNAL')
REDMINE_API_KEY = os.getenv('REDMINE_API_KEY')


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

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
