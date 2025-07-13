# api/index.py
from flask import Flask, request, jsonify
import json
import os

app = Flask(__name__)

# File to store progress (in /tmp for Vercel)
PROGRESS_FILE = '/tmp/progress.json'

# Load progress from file
def load_progress_store():
    try:
        if os.path.exists(PROGRESS_FILE):
            with open(PROGRESS_FILE, 'r') as f:
                return json.load(f)
        return {}
    except Exception as e:
        print(f"Error loading progress store: {e}")
        return {}

# Save progress to file
def save_progress_store(store):
    try:
        with open(PROGRESS_FILE, 'w') as f:
            json.dump(store, f)
        print("Progress store saved successfully")
    except Exception as e:
        print(f"Error saving progress store: {e}")

# Initialize progress store
progress_store = load_progress_store()

@app.route('/save', methods=['POST'])
def save_progress():
    data = request.json
    uid = data.get('uid')
    state = data.get('state')
    print(f"Received save request: uid={uid}, state={state}")
    if uid and state:
        progress_store[uid] = state
        save_progress_store(progress_store)
        return jsonify({"status": "ok"})
    print("Save failed: Missing uid or state")
    return jsonify({"status": "error", "message": "Missing uid or state"}), 400

@app.route('/load', methods=['GET'])
def load_progress():
    uid = request.args.get('uid')
    print(f"Received load request: uid={uid}")
    if uid in progress_store:
        print(f"Returning state for uid={uid}: {progress_store[uid]}")
        return jsonify({"state": progress_store[uid]})
    print(f"No state found for uid={uid}")
    return jsonify({"state": None})
