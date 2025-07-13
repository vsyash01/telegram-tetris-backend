# api/index.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# File to store progress and high scores (in /tmp for Vercel)
PROGRESS_FILE = '/tmp/progress.json'

# Load progress from file
def load_progress_store():
    try:
        if os.path.exists(PROGRESS_FILE):
            with open(PROGRESS_FILE, 'r') as f:
                data = json.load(f)
                print(f"Loaded progress store: {data}")
                return data
        print("No progress file found, initializing empty store")
        return {"states": {}, "highscores": []}
    except Exception as e:
        print(f"Error loading progress store: {e}")
        return {"states": {}, "highscores": []}

# Save progress to file
def save_progress_store(store):
    try:
        with open(PROGRESS_FILE, 'w') as f:
            json.dump(store, f)
        print(f"Saved progress store: {store}")
    except Exception as e:
        print(f"Error saving progress store: {e}")

# Initialize progress store
progress_store = load_progress_store()

@app.route('/save', methods=['POST'])
def save_progress():
    try:
        data = request.json
        uid = data.get('uid')
        state = data.get('state')
        print(f"Received save request: uid={uid}, state={state}")
        if not uid or not state:
            print("Save failed: Missing uid or state")
            return jsonify({"status": "error", "message": "Missing uid or state"}), 400
        progress_store["states"][uid] = state
        save_progress_store(progress_store)
        return jsonify({"status": "ok"})
    except Exception as e:
        print(f"Save failed: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/load', methods=['GET'])
def load_progress():
    try:
        uid = request.args.get('uid')
        print(f"Received load request: uid={uid}")
        if not uid:
            print("Load failed: Missing uid")
            return jsonify({"state": None}), 400
        state = progress_store["states"].get(uid)
        print(f"Returning state for uid={uid}: {state}")
        return jsonify({"state": state})
    except Exception as e:
        print(f"Load failed: {e}")
        return jsonify({"state": None, "message": str(e)}), 500

@app.route('/save_score', methods=['POST'])
def save_score():
    try:
        data = request.json
        uid = data.get('uid')
        name = data.get('name')
        score = data.get('score')
        print(f"Received save score request: uid={uid}, name={name}, score={score}")
        if not uid or not name or score is None:
            print("Save score failed: Missing uid, name, or score")
            return jsonify({"status": "error", "message": "Missing uid, name, or score"}), 400
        # Update high scores
        progress_store["highscores"].append({"uid": uid, "name": name, "score": score})
        # Sort by score (descending) and keep top 5
        progress_store["highscores"].sort(key=lambda x: x["score"], reverse=True)
        progress_store["highscores"] = progress_store["highscores"][:5]
        save_progress_store(progress_store)
        return jsonify({"status": "ok"})
    except Exception as e:
        print(f"Save score failed: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/highscores', methods=['GET'])
def get_highscores():
    try:
        print(f"Returning highscores: {progress_store['highscores']}")
        return jsonify({"highscores": progress_store["highscores"]})
    except Exception as e:
        print(f"Get highscores failed: {e}")
        return jsonify({"highscores": [], "message": str(e)}), 500
