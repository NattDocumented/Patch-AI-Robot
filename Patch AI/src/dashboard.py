"""
PATCH Dashboard Server
Provides web interface for monitoring and controlling Patch AI
"""

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import json
import os
import psutil
import time
from datetime import datetime
import threading

app = Flask(__name__)
CORS(app)

# File paths - adjust these to match the structure
MEMORY_FILE = "Patch AI/data/patch_memory.json"
REMINDERS_FILE = "Patch AI/data/patch_reminders.json"
STATUS_FILE = "Patch AI/data/patch_status.json"
LOG_FILE = "Patch AI/logs/patch.log"

# Fallback paths if above don't exist
if not os.path.exists(MEMORY_FILE):
    MEMORY_FILE = "patch_memory.json"
if not os.path.exists(REMINDERS_FILE):
    REMINDERS_FILE = "patch_reminders.json"
if not os.path.exists(LOG_FILE):
    LOG_FILE = "patch.log"

# Global state
dashboard_state = {
    "online": True,
    "mode": "BALANCED",
    "current_state": "idle",
    "last_message": "",
    "uptime_start": time.time()
}

def get_system_stats():
    """Get real-time system statistics"""
    try:
        # CPU
        cpu_percent = round(psutil.cpu_percent(interval=0.1), 1)
        
        # RAM
        ram = psutil.virtual_memory()
        ram_used_gb = ram.used / (1024**3)
        ram_total_gb = ram.total / (1024**3)
        
        # Disk
        disk = psutil.disk_usage('C:' if os.name == 'nt' else '/')
        disk_free_gb = disk.free / (1024**3)
        disk_total_gb = disk.total / (1024**3)
        
        # GPU (if torch available)
        gpu_stats = {"available": False}
        try:
            import torch
            if torch.cuda.is_available():
                vram_free = torch.cuda.mem_get_info()[0] / (1024**3)
                vram_total = torch.cuda.get_device_properties(0).total_memory / (1024**3)
                vram_used = vram_total - vram_free
                gpu_stats = {
                    "available": True,
                    "name": torch.cuda.get_device_name(0),
                    "vram_used_gb": round(vram_used, 2),
                    "vram_total_gb": round(vram_total, 2),
                    "vram_percent": round((vram_used / vram_total) * 100, 1)
                }
        except Exception as e:
            print(f"[Dashboard] GPU stats unavailable: {e}")
        
        # Temperature
        temp = "N/A"
        try:
            if hasattr(psutil, "sensors_temperatures"):
                temps = psutil.sensors_temperatures()
                if temps:
                    temp = f"{list(temps.values())[0][0].current}°C"
        except:
            pass
        
        return {
            "cpu_percent": cpu_percent,
            "ram_used_gb": round(ram_used_gb, 2),
            "ram_total_gb": round(ram_total_gb, 2),
            "ram_percent": round(ram.percent, 1),
            "disk_free_gb": round(disk_free_gb, 1),
            "disk_total_gb": round(disk_total_gb, 1),
            "disk_percent": round(disk.percent, 1),
            "temperature": temp,
            "gpu": gpu_stats
        }
    except Exception as e:
        print(f"[Dashboard] Error getting system stats: {e}")
        return {
            "cpu_percent": 0,
            "ram_used_gb": 0,
            "ram_total_gb": 0,
            "ram_percent": 0,
            "disk_free_gb": 0,
            "disk_total_gb": 0,
            "disk_percent": 0,
            "temperature": "N/A",
            "gpu": {"available": False}
        }

def get_conversation_log():
    """Get recent conversation from memory file"""
    try:
        if os.path.exists(MEMORY_FILE):
            with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
                messages = json.load(f)
                conversation = []
                for msg in messages:
                    if msg['role'] in ['user', 'assistant']:
                        conversation.append({
                            "role": msg['role'],
                            "content": msg['content']
                        })
                return conversation[-10:]
        return []
    except Exception as e:
        print(f"[Dashboard] Error reading conversation: {e}")
        return []

def get_reminders():
    """Get active reminders"""
    try:
        if os.path.exists(REMINDERS_FILE):
            with open(REMINDERS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if "active" in data:
                    reminders = data["active"]
                elif "reminders" in data:
                    reminders = data["reminders"]
                else:
                    reminders = []
                
                active = [r for r in reminders if not r.get('triggered', False)]
                active.sort(key=lambda x: x.get('time', ''))
                return active[:10]
        return []
    except Exception as e:
        print(f"[Dashboard] Error reading reminders: {e}")
        return []

def get_patch_status():
    """Get Patch's current status from status file"""
    try:
        if os.path.exists(STATUS_FILE):
            with open(STATUS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return dashboard_state
    except:
        return dashboard_state

@app.route('/')
def index():
    """Serve the main dashboard"""
    return render_template('dashboard.html')

@app.route('/api/status')
def api_status():
    """Get current Patch status"""
    status = get_patch_status()
    status['uptime'] = int(time.time() - dashboard_state['uptime_start'])
    return jsonify(status)

@app.route('/api/stats')
def api_stats():
    """Get system statistics"""
    return jsonify(get_system_stats())

@app.route('/api/conversation')
def api_conversation():
    """Get conversation log"""
    return jsonify(get_conversation_log())

@app.route('/api/reminders')
def api_reminders():
    """Get active reminders"""
    return jsonify(get_reminders())

@app.route('/api/logs')
def api_logs():
    """Get terminal logs"""
    try:
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()[-100:]  # Last 100 lines
            return jsonify(lines)
        else:
            # Fallback: return conversation as logs
            conv = get_conversation_log()
            logs = []
            for msg in conv:
                prefix = "YOU:" if msg['role'] == 'user' else "PATCH:"
                logs.append(f"{prefix} {msg['content']}\n")
            return jsonify(logs)
    except Exception as e:
        print(f"[Dashboard] Error reading logs: {e}")
        return jsonify(["[System] Log file not found"])

@app.route('/api/control/<action>', methods=['POST'])
def api_control(action):
    """Control Patch (sleep, wake, mode switch, etc.)"""
    try:
        command = {
            "action": action,
            "timestamp": datetime.now().isoformat()
        }
        
        with open("patch_command.json", 'w', encoding='utf-8') as f:
            json.dump(command, f)
        
        return jsonify({"success": True, "action": action})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/reminder/add', methods=['POST'])
def api_add_reminder():
    """Add new reminder"""
    try:
        data = request.json
        task = data.get('task')
        time_str = data.get('time')
        
        command = {
            "action": "add_reminder",
            "task": task,
            "time": time_str,
            "timestamp": datetime.now().isoformat()
        }
        
        with open("patch_command.json", 'w', encoding='utf-8') as f:
            json.dump(command, f)
        
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/reminder/delete/<reminder_id>', methods=['DELETE'])
def api_delete_reminder(reminder_id):
    """Delete reminder"""
    try:
        command = {
            "action": "delete_reminder",
            "reminder_id": reminder_id,
            "timestamp": datetime.now().isoformat()
        }
        
        with open("patch_command.json", 'w', encoding='utf-8') as f:
            json.dump(command, f)
        
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    print("\n" + "="*60)
    print(" "*15 + "PATCH DASHBOARD SERVER")
    print("="*60)
    print("\n📡 Dashboard Access:")
    print("  → Local:   http://localhost:5000")
    print("  → Network: http://YOUR_IP:5000")
    print("\n📁 File Paths:")
    print(f"  → Memory:    {MEMORY_FILE}")
    print(f"  → Reminders: {REMINDERS_FILE}")
    print(f"  → Logs:      {LOG_FILE}")
    print("\n💡 Tip: Run brain.py first, then this dashboard")
    print("\nPress Ctrl+C to stop\n")
    
    # Run Flask server
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)