from flask import Flask, jsonify
import redis
import os
import sys


# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from routes.users import users_bp


app = Flask(__name__)

# Register blueprints
app.register_blueprint(users_bp)

# Redis connection
redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    password=os.getenv("REDIS_PASSWORD", "yourpassword"),
    decode_responses=True,
)


@app.route("/")
def home():
    return jsonify(
        {
            "message": "ChipIn API",
            "version": "0.0.1",
            "status": "running",
            "endpoints": {
                "users": "/users",
            },
        }
    )


@app.route("/test-redis")
def test_redis():
    try:
        # Set a test value
        _ = redis_client.set("test_key", "Hello from Redis!")
        # Get it back
        value = redis_client.get("test_key")

        return jsonify({"success": True, "value": value}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    # Only for debugging while developing
    app.run(host="0.0.0.0", debug=True, port=80)
