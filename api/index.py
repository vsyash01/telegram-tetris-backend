from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import json
import os

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "https://telegram-tetris-chi.vercel.app"}})

# Vercel Blob Store configuration
BLOB_STORE_URL = "https://blob.vercel-storage.com"
BLOB_READ_WRITE_TOKEN = os.getenv("BLOB_READ_WRITE_TOKEN")
STATES_BLOB_KEY = "states.json"
HIGHSCORES_BLOB_KEY = "highscores.json"

# Check if token is available
if not BLOB_READ_WRITE_TOKEN:
    print("Error: BLOB_READ_WRITE_TOKEN is not set")
    raise EnvironmentError("BLOB_READ_WRITE_TOKEN is not set")

# Helper function to interact with Vercel Blob Store
def blob_request(method, path, data=None):
    headers = {
        "Authorization": f"Bearer {BLOB_READ_WRITE_TOKEN}",
        "Content-Type": "application/json" if data else "application/octet-stream",
        "x-add-random-suffix": "false"  # Explicitly disable random suffixes
    }
    url = f"{BLOB_STORE_URL}/{path}?overwrite=true"
    print(f"Blob request: {method} {url}, headers={headers}, data={data}")
    try:
        response = requests.request(method, url, headers=headers, data=json.dumps(data) if data else None, timeout=10)
        print(f"Blob response: status={response.status_code}, body={response.text}")
        response.raise_for_status()
        return response
    except requests.RequestException as e:
        print(f"Blob request failed: {e}, response={e.response.text if e.response else 'No response'}")
        raise

# Load progress store from Blob Store
def load_progress_store():
    try:
        response = blob_request("GET", f"{STATES_BLOB_KEY}")
        data = response.json()
        print(f"Loaded progress store: {data}")
        return data.get("data", {"states": {}, "highscores": []})
    except requests.RequestException as e:
        if e.response and e.response.status_code == 404:
            print("No progress store found, initializing empty store")
            return {"states": {}, "highscores": []}
        print(f"Error loading progress store: {e}")
        raise

# Save progress store to Blob Store
def save_progress_store(store):
    try:
        blob_request("PUT", f"{STATES_BLOB_KEY}", data=store)
        print(f"Saved progress store: {store}")
    except requests.RequestException as e:
        print(f"Error saving progress store: {e}")
        raise

# Load highscores from Blob Store
def load_highscores_store():
    try:
        response = blob_request("GET", f"{HIGHSCORES_BLOB_KEY}")
        data = response.json()
        print(f"Loaded highscores: {data}")
        return data.get("data", [])
    except requests.RequestException as e:
        if e.response and e.response.status_code == 404:
            print("No highscores found, initializing empty list")
            return []
        print(f"Error loading highscores: {e}")
        raise

# Save highscores to Blob Store
def save_highscores_store(highscores):
    try:
        blob_request("PUT", f"{HIGHSCORES_BLOB_KEY}", data={"highscores": highscores})
        print(f"Saved highscores: {highscores}")
    except requests.RequestException as e:
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
        highscores_store.append({"uid": uid, "name": name, "score": score, "status": "завершена"})
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
        # Combine completed games (from highscores_store) and in-progress games (from progress_store)
        combined_scores = []
        # Add completed games
        for entry in highscores_store:
            combined_scores.append({
                "uid": entry["uid"],
                "name": entry["name"],
                "score": entry["score"],
                "status": entry.get("status", "завершена")
            })
        # Add in-progress games
        for uid, state in progress_store["states"].items():
            if state and "score" in state:
                name = state.get("username", "Неизвестный игрок")
                combined_scores.append({
                    "uid": uid,
                    "name": name,
                    "score": state["score"],
                    "status": "в игре"
                })
        # Sort by score and take top 5
        combined_scores.sort(key=lambda x: x["score"], reverse=True)
        combined_scores = combined_scores[:5]
        print(f"Returning combined highscores: {combined_scores}")
        return jsonify({"highscores": combined_scores})
    except Exception as e:
        print(f"Get highscores failed: {e}")
        return jsonify({"highscores": [], "message": str(e)}), 500

if __name__ == '__main__':
    app.run()
