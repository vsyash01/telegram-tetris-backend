from flask import Flask, request, jsonify
from flask_cors import CORS
import redis
import json
import os
import logging

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "https://telegram-tetris-chi.vercel.app"}})

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Redis client for Vercel KV
redis_url = os.getenv("REDIS_URL")
if not redis_url:
    logger.error("REDIS_URL is not set")
    raise ValueError("REDIS_URL environment variable is missing")

try:
    redis_client = redis.Redis.from_url(redis_url, decode_responses=True)
    redis_client.ping()  # Test connection
    logger.info("Connected to Vercel KV")
except redis.RedisError as e:
    logger.error(f"Error connecting to Vercel KV: {e}")
    raise

# In-memory cache for game states
progress_store = {"states": {}, "highscores": []}

# Helper function to load highscores from Vercel KV
def load_highscores_store():
    try:
        highscores_data = redis_client.get("highscores")
        if highscores_data:
            logger.info(f"Loaded highscores: {highscores_data}")
            return json.loads(highscores_data)
        logger.info("No highscores found, initializing empty list")
        return []
    except redis.RedisError as e:
        logger.error(f"Error loading highscores: {e}")
        return []

# Helper function to save highscores to Vercel KV
def save_highscores_store(highscores):
    try:
        redis_client.set("highscores", json.dumps(highscores))
        logger.info(f"Saved highscores: {highscores}")
    except redis.RedisError as e:
        logger.error(f"Error saving highscores: {e}")
        raise

# Helper function to load a player's state from Vercel KV
def load_player_state(uid):
    try:
        state_data = redis_client.get(f"state:{uid}")
        if state_data:
            logger.info(f"Loaded state for uid={uid}: {state_data}")
            return json.loads(state_data)
        logger.info(f"No state found for uid={uid}")
        return None
    except redis.RedisError as e:
        logger.error(f"Error loading state for uid={uid}: {e}")
        return None

# Helper function to save a player's state to Vercel KV
def save_player_state(uid, state):
    try:
        redis_client.setex(f"state:{uid}", 604800, json.dumps(state))  # Expires in 7 days
        logger.info(f"Saved state for uid={uid}: {state}")
    except redis.RedisError as e:
        logger.error(f"Error saving state for uid={uid}: {e}")
        raise

# Initialize highscores
try:
    progress_store["highscores"] = load_highscores_store()
except Exception as e:
    logger.error(f"Initialization failed: {e}")
    progress_store["highscores"] = []

@app.route('/api/save', methods=['POST', 'OPTIONS'])
def save_progress():
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200  # Handle CORS preflight
    try:
        data = request.json
        uid = data.get('uid')
        state = data.get('state')
        logger.info(f"Received save request: uid={uid}, state={state}")
        if not uid or not state:
            logger.error("Save failed: Missing uid or state")
            return jsonify({"status": "error", "message": "Missing uid or state"}), 400
        # Store in memory cache
        progress_store["states"][uid] = state
        # Persist to Vercel KV
        save_player_state(uid, state)
        return jsonify({"status": "ok"})
    except Exception as e:
        logger.error(f"Save failed: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/load', methods=['GET'])
def load_progress():
    try:
        uid = request.args.get('uid')
        logger.info(f"Received load request: uid={uid}")
        if not uid:
            logger.error("Load failed: Missing uid")
            return jsonify({"state": None}), 400
        # Check in-memory cache first
        state = progress_store["states"].get(uid)
        if not state:
            # Fall back to Vercel KV
            state = load_player_state(uid)
            if state:
                progress_store["states"][uid] = state
        logger.info(f"Returning state for uid={uid}: {state}")
        # Clear the player's state from KV after loading
        if state:
            try:
                redis_client.delete(f"state:{uid}")
                logger.info(f"Cleared state for uid={uid} from Vercel KV")
            except redis.RedisError as e:
                logger.error(f"Error clearing state for uid={uid}: {e}")
        return jsonify({"state": state})
    except Exception as e:
        logger.error(f"Load failed: {e}")
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
        logger.info(f"Received save score request: uid={uid}, name={name}, score={score}")
        if not uid or not name or score is None:
            logger.error("Save score failed: Missing uid, name, or score")
            return jsonify({"status": "error", "message": "Missing uid, name, or score"}), 400
        progress_store["highscores"].append({"uid": uid, "name": name, "score": score})
        progress_store["highscores"].sort(key=lambda x: x["score"], reverse=True)
        progress_store["highscores"] = progress_store["highscores"][:5]
        save_highscores_store(progress_store["highscores"])
        # Clear the player's state from both cache and KV after saving score
        if uid in progress_store["states"]:
            del progress_store["states"][uid]
        try:
            redis_client.delete(f"state:{uid}")
            logger.info(f"Cleared state for uid={uid} from Vercel KV after saving score")
        except redis.RedisError as e:
            logger.error(f"Error clearing state for uid={uid}: {e}")
        return jsonify({"status": "ok"})
    except Exception as e:
        logger.error(f"Save score failed: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/highscores', methods=['GET'])
def get_highscores():
    try:
        logger.info(f"Returning highscores: {progress_store['highscores']}")
        return jsonify({"highscores": progress_store["highscores"]})
    except Exception as e:
        logger.error(f"Get highscores failed: {e}")
        return jsonify({"highscores": [], "message": str(e)}), 500

@app.route('/api/usage', methods=['GET'])
def get_usage():
    try:
        info = redis_client.info()
        logger.info(f"Redis usage: {info}")
        return jsonify({
            "status": "ok",
            "used_memory": info.get("used_memory_human", "N/A"),
            "total_commands_processed": info.get("total_commands_processed", 0),
            "db_keys": redis_client.dbsize()
        })
    except redis.RedisError as e:
        logger.error(f"Error fetching usage: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run()
