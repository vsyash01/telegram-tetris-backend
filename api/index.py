# api/index.py
from flask import Flask, request, jsonify

app = Flask(__name__)

# Сохраняем прогресс в памяти (для теста)
progress_store = {}

@app.route('/save', methods=['POST'])
def save_progress():
    data = request.json
    uid = data.get('uid')
    state = data.get('state')
    if uid and state:
        progress_store[uid] = state
        return jsonify({"status": "ok"})
    return jsonify({"status": "error"}), 400

@app.route('/load', methods=['GET'])
def load_progress():
    uid = request.args.get('uid')
    state = progress_store.get(uid)
    return jsonify({"state": state})
