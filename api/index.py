# api/index.py
from flask import Flask, request, jsonify
from vercel_kv import VercelKV
import os

app = Flask(__name__)

# Initialize Vercel KV client
kv = VercelKV()

# Load progress from Vercel KV
def load_progress_store(uid):
    try:
        state = kv.get(f"progress:{uid}")
        print(f"Loaded progress for uid={uid}: {state}")
        return state if state else {}
    except Exception as e:
        print(f"Error loading progress for uid={uid}: {e}")
        return {}

# Save progress to Vercel KV
def save_progress_store(uid, state):
    try:
        kv.set(f"progress:{uid}", state)
        print(f"Saved progress for uid={uid}: {state}")
    except Exception as e:
        print(f"Error saving progress for uid={uid}: {e}")

@app.route('/save', methods=['POST'])
def save_progress():
    data = request.json
    uid = data.get('uid')
    state = data.get('state')
    print(f"Received save request: uid={uid}, state={state}")
    if not uid or not state:
        print("Save failed: Missing uid or state")
        return jsonify({"status": "error", "message": "Missing uid or state"}), 400
    try:
        save_progress_store(uid, state)
        return jsonify({"status": "ok"})
    except Exception as e:
        print(f"Save failed for uid={uid}: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/load', methods=['GET'])
def load_progress():
    uid = request.args.get('uid')
    print(f"Received load request: uid={uid}")
    if not uid:
        print("Load failed: Missing uid")
        return jsonify({"state": None}), 400
    state = load_progress_store(uid)
    if state:
        print(f"Returning state for uid={uid}: {state}")
        return jsonify({"state": state})
    print(f"No state found for uid={uid}")
    return jsonify({"state": None})
