from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
from vercel_blob import put, get, delete  # Vercel Blob Store Client SDK

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "https://telegram-tetris-chi.vercel.app"}})

# Vercel Blob Store configuration
STATES_BLOB_KEY = "states.json"
HIGHSCORES_BLOB_KEY = "highscores.json"
BLOB_READ_WRITE_TOKEN = os.getenv("BLOB_READ_WRITE_TOKEN")

# Check if token is available
if not BLOB_READ_WRITE_TOKEN:
    print("Error: BLOB_READ_WRITE_TOKEN is not set")

# Load progress store from Blob Store
def load_progress_store():
    try:
        print(f"Attempting to load progress store from {STATES_BLOB_KEY}")
        blob = get(STATES_BLOB_KEY)
        if blob:
            data = json.loads(blob)
            print(f"Loaded progress store: {data}")
            return data.get("data", {"states": {}, "highscores": []})
        else:
            print("No progress store found, initializing empty store")
            return {"states": {}, "highscores": []}
    except Exception as e:
        print(f"Error loading progress store: {e}")
        if "404" in str(e):
            print("No progress store found, initializing empty store")
            return {"states": {}, "highscores": []}
        raise

# Save progress store to Blob Store
def save_progress_store(store):
    try:
        print(f"Saving progress store to {STATES_BLOB_KEY}: {store}")
        put(STATES_BLOB_KEY, json.dumps(store), {"access": "public", "add_random_suffix": False})
        print(f"Saved progress store to {STATES_BLOB_KEY}")
    except Exception as e:
        print(f"Error saving progress store: {e}")
        raise

# Load highscores from Blob Store
def load_highscores_store():
    try:
        print(f"Attempting to load highscores from {HIGHSCORES_BLOB_KEY}")
        blob = get(HIGHSCORES_BLOB_KEY)
        if blob:
            data = json.loads(blob)
            print(f"Loaded highscores: {data}")
            return data.get("data", [])
        else:
            print("No highscores found, initializing empty list")
            return []
    except Exception as e:
        print(f"Error loading highscores: {e}")
        if "404" in str(e):
            print("No highscores found, initializing empty list")
            return []
        raise

# Save highscores to Blob Store
def save_highscores_store(highscores):
    try:
        print(f"Saving highscores to {HIGHSCORES_BLOB_KEY}: {highscores}")
        put(HIGHSCORES_BLOB_KEY, json.dumps({"highscores": highscores}), {"access": "public", "add_random_suffix": False})
        print(f"Saved highscores to {HIGHSCORES_BLOB_KEY}")
    except Exception as e:
        print(f"Error saving highscores: {e}")
        raise

# Initialize stores
try:
    progress_store = load_progress_store()
    highscores_store = load_highscores_store()
except Exception as e:
    print(f"Initialization failed: {e}")
    progress_store = {"states": {}}
    highscores_store = []

@app.route('/api/save', methods=['POST', 'OPTIONS'])
def save_progress():
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200  # Handle CORS preflight
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

@app.route('/api/load', methods=['GET'])
def load_progress():
    try:
        uid = request.args.get('uid')
        print(f"Received load request: uid={uid}")
        if not uid:
            print("Load failed: Missing uid")
            return jsonify({"state": None}), 400
        state = progress_store["states"].get(uid)
        print(f"Returning state for uid={uid}: {state}")
        # Clear the player's state after loading to ensure only the latest state is kept
        if state:
            del progress_store["states"][uid]
            save_progress_store(progress_store)
        return jsonify({"state": state})
    except Exception as e:
        print(f"Load failed: {e}")
        return jsonify({"state": None, "message": str(e)}), 500

@app.route('/api/save_score', methods=['POST', 'OPTIONS'])
def save_score():
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200  # Handle CORS preflight
    try:
        data = request.json
        uid = data.get('uid')
        name = data.get('name')
        score = data.get('score')
        print(f"Received save score request: uid={uid}, name={name}, score={score}")
        if not uid or not name or score is None:
            print("Save score failed: Missing uid, name, or score")
            return jsonify({"status": "error", "message": "Missing uid, name, or score"}), 400
        highscores_store.append({"uid": uid, "name": name, "score": score})
        highscores_store.sort(key=lambda x: x["score"], reverse=True)
        highscores_store[:] = highscores_store[:5]
        save_highscores_store(highscores_store)
        # Clear the player's state after saving score to prevent reloading game-over state
        if uid in progress_store["states"]:
            del progress_store["states"][uid]
            save_progress_store(progress_store)
        return jsonify({"status": "ok"})
    except Exception as e:
        print(f"Save score failed: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/highscores', methods=['GET'])
def get_highscores():
    try:
        print(f"Returning highscores: {highscores_store}")
        return jsonify({"highscores": highscores_store})
    except Exception as e:
        print(f"Get highscores failed: {e}")
        return jsonify({"highscores": [], "message": str(e)}), 500

if __name__ == '__main__':
    app.run()
