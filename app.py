import os
from flask import Flask, render_template, request, jsonify
from redminelib import Redmine
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

REDMINE_URL_INTERNAL = os.getenv('REDMINE_URL_INTERNAL')
REDMINE_URL_EXTERNAL = os.getenv('REDMINE_URL_EXTERNAL')
REDMINE_API_KEY = os.getenv('REDMINE_API_KEY')

def get_redmine(network_type):
    url = REDMINE_URL_EXTERNAL if network_type == 'external' else REDMINE_URL_INTERNAL
    return Redmine(url, key=REDMINE_API_KEY)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/search')
def search_issue():
    query = request.args.get('q', '')
    network_type = request.args.get('network', 'internal')
    if not query:
        return jsonify({'error': 'Search query is required'}), 400
    
    try:
        redmine = get_redmine(network_type)
        
        # Check if query is an ID
        if query.isdigit():
            try:
                issue = redmine.issue.get(query, include=['journals'])
                return jsonify({'type': 'single', 'data': format_issue(issue)})
            except:
                pass # If ID search fails, proceed to keyword search
        
        # Keyword search
        issues = redmine.issue.filter(subject=f'~{query}', status_id='*')
        
        results = []
        for issue in issues:
            results.append({
                'id': issue.id,
                'subject': issue.subject,
                'status': issue.status.name,
                'updated_on': issue.updated_on.isoformat()
            })
            
        return jsonify({'type': 'list', 'data': results})
    except Exception as e:
        return jsonify({'error': str(e)}), 404

@app.route('/api/issue/<int:issue_id>')
def get_issue_detail(issue_id):
    network_type = request.args.get('network', 'internal')
    try:
        redmine = get_redmine(network_type)
        issue = redmine.issue.get(issue_id, include=['journals'])
        return jsonify(format_issue(issue))
    except Exception as e:
        return jsonify({'error': str(e)}), 404

def format_issue(issue):
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
    
    return {
        'id': issue.id,
        'subject': issue.subject,
        'status': issue.status.name,
        'priority': issue.priority.name,
        'author': issue.author.name,
        'assigned_to': getattr(issue, 'assigned_to', None).name if hasattr(issue, 'assigned_to') else 'None',
        'description': issue.description,
        'created_on': issue.created_on.isoformat(),
        'updated_on': issue.updated_on.isoformat(),
        'journals': journals[::-1]
    }

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
