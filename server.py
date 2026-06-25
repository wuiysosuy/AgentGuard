import os
import sys
import json
import time
import socket
import queue
import threading
from flask import Flask, render_template, request, jsonify, Response

app = Flask(__name__, template_folder='templates')

# File paths
SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'settings.json')
LOGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'command_history.json')

# In-memory storage
requests_db = {}
requests_order = []  # Maintain insertion order for history
subscribers = []
subscribers_lock = threading.Lock()

# Load settings (auto-approve list)
default_settings = {
    "auto_approve_list": [
        "git status",
        "git diff",
        "git branch",
        "dir",
        "ls",
        "pwd",
        "echo",
        "whoami"
    ],
    "auto_approve_enabled": True
}

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return default_settings.copy()

def save_settings(settings):
    try:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving settings: {e}")

settings = load_settings()

def load_history():
    if os.path.exists(LOGS_FILE):
        try:
            with open(LOGS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("requests", {}), data.get("order", [])
        except Exception:
            pass
    return {}, []

def save_history():
    try:
        with open(LOGS_FILE, 'w', encoding='utf-8') as f:
            json.dump({"requests": requests_db, "order": requests_order}, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving history: {e}")

# Load initial history
requests_db, requests_order = load_history()

def broadcast(data):
    with subscribers_lock:
        for q in list(subscribers):
            q.put(data)

def is_auto_approved(command):
    if not settings.get("auto_approve_enabled", True):
        return False
    
    cmd_clean = command.strip().lower()
    for whitelist_item in settings.get("auto_approve_list", []):
        whitelist_clean = whitelist_item.strip().lower()
        # Direct match or command starts with whitelist item followed by a space (e.g. "git status -s" matches "git status")
        if cmd_clean == whitelist_clean or cmd_clean.startswith(whitelist_clean + " "):
            return True
    return False

# Local IP detection
def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/requests', methods=['GET'])
def get_requests():
    # Return requests in reverse chronological order (newest first)
    history = []
    for req_id in reversed(requests_order):
        history.append(requests_db[req_id])
    return jsonify(history)

@app.route('/api/request', methods=['POST'])
def create_request():
    data = request.json or {}
    command = data.get('command', '').strip()
    client = data.get('client', 'Unknown Client').strip()
    
    if not command:
        return jsonify({"error": "Command is empty"}), 400
        
    req_id = str(int(time.time() * 1000))  # Simple millisecond-based ID
    
    # Check if auto-approved
    status = "approved" if is_auto_approved(command) else "pending"
    
    req_data = {
        "id": req_id,
        "command": command,
        "client": client,
        "status": status,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
        "decision_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) if status == "approved" else None,
        "auto_approved": status == "approved"
    }
    
    requests_db[req_id] = req_data
    requests_order.append(req_id)
    save_history()
    
    # Notify connected clients via SSE
    broadcast({
        "type": "new_request",
        "data": req_data
    })
    
    return jsonify({"id": req_id, "status": status})

@app.route('/api/status/<req_id>', methods=['GET'])
def get_status(req_id):
    req_data = requests_db.get(req_id)
    if not req_data:
        return jsonify({"error": "Request not found"}), 404
    return jsonify({
        "id": req_data["id"],
        "status": req_data["status"],
        "command": req_data["command"]
    })

@app.route('/api/approve/<req_id>', methods=['POST'])
def approve_request(req_id):
    req_data = requests_db.get(req_id)
    if not req_data:
        return jsonify({"error": "Request not found"}), 404
        
    if req_data["status"] == "pending":
        req_data["status"] = "approved"
        req_data["decision_time"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        save_history()
        
        broadcast({
            "type": "status_update",
            "data": req_data
        })
        return jsonify({"success": True})
    return jsonify({"error": f"Request status is already {req_data['status']}"}), 400

@app.route('/api/reject/<req_id>', methods=['POST'])
def reject_request(req_id):
    req_data = requests_db.get(req_id)
    if not req_data:
        return jsonify({"error": "Request not found"}), 404
        
    if req_data["status"] == "pending":
        req_data["status"] = "rejected"
        req_data["decision_time"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        save_history()
        
        broadcast({
            "type": "status_update",
            "data": req_data
        })
        return jsonify({"success": True})
    return jsonify({"error": f"Request status is already {req_data['status']}"}), 400

@app.route('/api/settings', methods=['GET', 'POST'])
def handle_settings():
    global settings
    if request.method == 'POST':
        data = request.json or {}
        settings["auto_approve_enabled"] = bool(data.get("auto_approve_enabled", True))
        
        # Ensure it's a list of strings
        raw_list = data.get("auto_approve_list", [])
        settings["auto_approve_list"] = [str(x).strip() for x in raw_list if str(x).strip()]
        
        save_settings(settings)
        return jsonify({"success": True, "settings": settings})
    return jsonify(settings)

@app.route('/api/stream')
def stream():
    def event_stream():
        q = queue.Queue()
        with subscribers_lock:
            subscribers.append(q)
        try:
            # Send initial connection event
            yield f"data: {json.dumps({'type': 'connected'})}\n\n"
            while True:
                # Block until we have a message to send
                data = q.get()
                yield f"data: {json.dumps(data)}\n\n"
        except GeneratorExit:
            pass
        finally:
            with subscribers_lock:
                if q in subscribers:
                    subscribers.remove(q)
    return Response(event_stream(), mimetype="text/event-stream")

if __name__ == '__main__':
    # Reconfigure standard output to support UTF-8 on Windows
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

    port = 5000
    local_ip = get_local_ip()
    local_url = f"http://{local_ip}:{port}"
    
    print("=" * 60)
    print("                 AGENTGUARD SERVER STARTING")
    print("=" * 60)
    print(f" * Local URL: http://127.0.0.1:{port}")
    print(f" * Network URL (Mobile Access): {local_url}")
    print("=" * 60)
    
    # Try to generate QR code in terminal
    try:
        import qrcode
        qr = qrcode.QRCode(version=1, box_size=1, border=1)
        qr.add_data(local_url)
        qr.make(fit=True)
        print("\n[MA QR TRUY CAP TREN DIEN THOAI DI DONG - SCAN TO OPEN ON MOBILE]")
        # print_ascii uses a compact character set that works on most Windows command prompts
        qr.print_ascii(invert=True)
        print("=" * 60)
    except ImportError:
        print("\nGoi y: De quet ma QR nhanh tren dien thoai, hay cai dat 'qrcode' library:")
        print("pip install qrcode")
        print("=" * 60)
    
    # Run the server on all interfaces so mobile can access it
    app.run(host='0.0.0.0', port=port, debug=False)
