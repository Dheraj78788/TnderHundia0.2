from flask import Flask, render_template, send_from_directory, jsonify
import json
import os

app = Flask(__name__, static_folder='static', static_url_path='')

# Serve static files directly
@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/tenders')
def tenders():
    return send_from_directory('static', 'tenders.html')

# API endpoint for tenders data (Flask Backend)
@app.route('/api/tenders')
def api_tenders():
    try:
        with open('scrapers/tenders_all3.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        return jsonify(data)
    except FileNotFoundError:
        return jsonify({"error": "Tenders data not found"}), 404
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid JSON format"}), 400

# Serve scrapers folder (fallback)
@app.route('/scrapers/<path:filename>')
def serve_scrapers(filename):
    return send_from_directory('scrapers', filename)


@app.route('/auth')
def auth():
    return send_from_directory('static', 'auth.html')


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
