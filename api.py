import json
import os
import time
import requests
from flask import Flask, request, jsonify
from datetime import datetime, timedelta

app = Flask(__name__)

# ---------- CONFIGURATION ----------
USERS_FILE = "users.json"
REAL_APIS = {
    "number": "https://dark-info.site/test/api.php?key=Demo&num={}",
    "aadhar": "https://dark-info.site/familyinfo/api.php?key=JSON-4325&num={}",
    "tg_to_num": "https://dark-info.site/tg/api.php?key=Tg-to+number&num={}"
}

# ---------- USER DATABASE ----------
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

# ---------- CHECK USER ACCESS ----------
def check_user_access(api_key):
    """Check if user has valid access to any API"""
    users = load_users()
    if api_key not in users:
        return None, "❌ Invalid API key. Contact admin to get access."
    
    user = users[api_key]
    expiry = datetime.fromisoformat(user["expiry"])
    
    if datetime.now() > expiry:
        return None, "❌ Your API access has expired. Contact admin to renew."
    
    if not user["active"]:
        return None, "❌ Your API access is currently disabled by admin."
    
    return user, None

# ---------- MAIN API ENDPOINT ----------
@app.route('/api', methods=['GET'])
def proxy_api():
    """Main API endpoint - user hits this with their key"""
    api_key = request.args.get('key')
    query = request.args.get('num') or request.args.get('query')
    api_type = request.args.get('type', 'number')  # number, aadhar, tg_to_num
    
    if not api_key or not query:
        return jsonify({
            "success": False,
            "message": "Please provide: ?key=YOUR_KEY&num=QUERY&type=number"
        }), 400
    
    # Check user access
    user, error = check_user_access(api_key)
    if error:
        return jsonify({"success": False, "message": error}), 403
    
    # Get real API URL
    if api_type not in REAL_APIS:
        return jsonify({
            "success": False,
            "message": "Invalid API type. Use: number, aadhar, or tg_to_num"
        }), 400
    
    real_url = REAL_APIS[api_type].format(query)
    
    try:
        response = requests.get(real_url, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        # Add our wrapper info
        result = {
            "success": True,
            "type": api_type,
            "query": query,
            "developer": "𐙚 𓆩𝘼𝙠𝙖𝙨𝙝 𝙊𝙨𝙞𝙣𝙩𓆪𓂃🧑‍💻🎀⃤",
            "data": data
        }
        return jsonify(result)
    
    except requests.exceptions.RequestException:
        return jsonify({
            "success": False,
            "message": "Service temporarily unavailable. Please try again later."
        }), 503
    except json.JSONDecodeError:
        return jsonify({
            "success": False,
            "message": "Invalid response from upstream API."
        }), 502

# ---------- ADMIN FUNCTIONS ----------
@app.route('/admin/create_user', methods=['GET'])
def create_user():
    """Create a new user with API key"""
    admin_key = request.args.get('admin_key')
    
    # Simple admin check - change this to your own
    if admin_key != "YOUR_ADMIN_SECRET_123":
        return jsonify({"success": False, "message": "Invalid admin key"}), 403
    
    users = load_users()
    import uuid
    new_key = str(uuid.uuid4())[:12]  # Generate random API key
    
    users[new_key] = {
        "created": datetime.now().isoformat(),
        "expiry": (datetime.now() + timedelta(days=30)).isoformat(),  # 30 days default
        "active": True,
        "usage": 0,
        "last_used": None
    }
    save_users(users)
    
    return jsonify({
        "success": True,
        "api_key": new_key,
        "expiry": users[new_key]["expiry"],
        "message": "User created. Share this API key with the user."
    })

@app.route('/admin/manage', methods=['GET'])
def manage_user():
    """Enable/Disable or Extend user access"""
    admin_key = request.args.get('admin_key')
    
    if admin_key != "YOUR_ADMIN_SECRET_123":
        return jsonify({"success": False, "message": "Invalid admin key"}), 403
    
    action = request.args.get('action')  # enable, disable, extend
    api_key = request.args.get('api_key')
    days = request.args.get('days', 30)
    
    users = load_users()
    if api_key not in users:
        return jsonify({"success": False, "message": "User not found"}), 404
    
    if action == "enable":
        users[api_key]["active"] = True
        msg = "User enabled."
    elif action == "disable":
        users[api_key]["active"] = False
        msg = "User disabled."
    elif action == "extend":
        users[api_key]["expiry"] = (datetime.now() + timedelta(days=int(days))).isoformat()
        msg = f"User extended by {days} days."
    else:
        return jsonify({"success": False, "message": "Invalid action"}), 400
    
    save_users(users)
    return jsonify({"success": True, "message": msg})

@app.route('/admin/users', methods=['GET'])
def list_users():
    """List all users (admin only)"""
    admin_key = request.args.get('admin_key')
    
    if admin_key != "YOUR_ADMIN_SECRET_123":
        return jsonify({"success": False, "message": "Invalid admin key"}), 403
    
    users = load_users()
    # Remove sensitive info if needed
    safe_users = {}
    for key, data in users.items():
        safe_users[key] = {
            "expiry": data.get("expiry"),
            "active": data.get("active"),
            "usage": data.get("usage", 0)
        }
    
    return jsonify({
        "success": True,
        "total_users": len(safe_users),
        "users": safe_users
    })

# ---------- HEALTH CHECK ----------
@app.route('/ping')
def ping():
    return "API is running!", 200

# ---------- MAIN ----------
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 8080)))
