from flask import Flask, request, jsonify
from flask_cors import CORS
from vercel_kv import KV
import os

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "https://telegram-tetris-chi.vercel.app"}})

# Vercel KV configuration
kv = KV()

def load_progress_store():
    try:
        data = kv.get("states") or {"states": {}, "highscores": []}
        print(f"Loaded progress store: {data}")
        return data
    except Exception as e:
        print(f"Error loading progress store: {e}")
        return {"states": {}, "highscores": []}

def save_progress_store(store):
    try:
        kv.set("states", store)
        print(f"Saved progress store: {store}")
    except Exception as e:
        print(f"Error saving progress store: {e}")
        raise

def load_highscores_store():
    try:
        data = kv.get("highscores") or []
        print(f"Loaded highscores: {data}")
        return data
    except Exception as e:
        print(f"Error loading highscores: {e}")
        return []

def save_highscores_store(highscores):
    try:
        kv.set("highscores", {"highscores": highscores})
        print(f"Saved highscores: {highscores}")
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
        return jsonify({"status": "ok"}), 200
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
        return jsonify({"status": "ok"}), 200
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
        combined_scores = []
        for entry in highscores_store:
            combined_scores.append({
                "uid": entry["uid"],
                "name": entry["name"],
                "score": entry["score"],
                "status": entry.get("status", "завершена")
            })
        for uid, state in progress_store["states"].items():
            if state and "score" in state:
                name = state.get("username", "Неизвестный игрок")
                combined_scores.append({
                    "uid": uid,
                    "name": name,
                    "score": state["score"],
                    "status": "в игре"
                })
        combined_scores.sort(key=lambda x: x["score"], reverse=True)
        combined_scores = combined_scores[:5]
        print(f"Returning combined highscores: {combined_scores}")
        return jsonify({"highscores": combined_scores})
    except Exception as e:
        print(f"Get highscores failed: {e}")
        return jsonify({"highscores": [], "message": str(e)}), 500

if __name__ == '__main__':
    app.run()
