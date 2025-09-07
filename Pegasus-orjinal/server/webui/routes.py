from flask import Blueprint, render_template, request, jsonify
from .intelx_api import start_search, get_search_results

webui = Blueprint('webui', __name__, template_folder='templates', static_folder='static')

@webui.route('/')
def index():
    return render_template('index.html')

@webui.route('/intelx')
def intelx_search_page():
    return render_template('intelx_search.html')

@webui.route('/api/intelx/search', methods=['POST'])
def intelx_search():
    data = request.get_json()
    term = data.get('term')
    if not term:
        return jsonify({'error': 'Search term is required'}), 400

    search_id = start_search(term)
    if not search_id:
        return jsonify({'error': 'Failed to start search'}), 500

    results = get_search_results(search_id)
    if results is None:
        return jsonify({'error': 'Failed to get search results'}), 500

    return jsonify({'results': results})
