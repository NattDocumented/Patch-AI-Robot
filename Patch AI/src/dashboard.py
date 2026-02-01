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

# File paths (same as brain.py)
MEMORY_FILE = "Patch AI/data/patch_memory.json"
REMINDERS_FILE = "Patch AI/data/patch_reminders.json"
STATUS_FILE = "Patch AI/data/patch_status.json"  # New file for real-time status

# Global state
dashboard_state = {
    "online": True,
    "mode": "BALANCED",
    "current_state": "idle",  # idle, listening, thinking, speaking, sleeping
    "last_message": "",
    "uptime_start": time.time()
}

def get_system_stats():
    """Get real-time system statistics"""
    try:
        # CPU
        cpu_percent = psutil.cpu_percent(interval=0.1)
        
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
        except:
            pass
        
        # Temperature (Windows - requires external tool, Linux - sensors)
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
            "ram_percent": ram.percent,
            "disk_free_gb": round(disk_free_gb, 1),
            "disk_total_gb": round(disk_total_gb, 1),
            "disk_percent": disk.percent,
            "temperature": temp,
            "gpu": gpu_stats
        }
    except Exception as e:
        print(f"[Dashboard] Error getting system stats: {e}")
        return {}

def get_conversation_log():
    """Get recent conversation from memory file"""
    try:
        if os.path.exists(MEMORY_FILE):
            with open(MEMORY_FILE, 'r') as f:
                messages = json.load(f)
                # Filter out system messages, return last 10
                conversation = []
                for msg in messages:
                    if msg['role'] in ['user', 'assistant']:
                        conversation.append({
                            "role": msg['role'],
                            "content": msg['content']
                        })
                return conversation[-10:]  # Last 10 messages
        return []
    except Exception as e:
        print(f"[Dashboard] Error reading conversation: {e}")
        return []

def get_reminders():
    """Get active reminders"""
    try:
        if os.path.exists(REMINDERS_FILE):
            with open(REMINDERS_FILE, 'r') as f:
                data = json.load(f)
                # Handle both old and new format
                if "active" in data:
                    reminders = data["active"]
                elif "reminders" in data:
                    reminders = data["reminders"]
                else:
                    reminders = []
                
                # Filter active only and sort by time
                active = [r for r in reminders if not r.get('triggered', False)]
                active.sort(key=lambda x: x['time'])
                return active[:10]  # Top 10
        return []
    except Exception as e:
        print(f"[Dashboard] Error reading reminders: {e}")
        return []

def get_patch_status():
    """Get Patch's current status from status file"""
    try:
        if os.path.exists(STATUS_FILE):
            with open(STATUS_FILE, 'r') as f:
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

@app.route('/api/control/<action>', methods=['POST'])
def api_control(action):
    """Control Patch (sleep, wake, mode switch, etc.)"""
    # This writes commands to a control file that brain.py reads
    try:
        command = {
            "action": action,
            "timestamp": datetime.now().isoformat()
        }
        
        # Write command to file
        with open("patch_command.json", 'w') as f:
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
        
        # Write to command file for brain.py to process
        command = {
            "action": "add_reminder",
            "task": task,
            "time": time_str,
            "timestamp": datetime.now().isoformat()
        }
        
        with open("patch_command.json", 'w') as f:
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
        
        with open("patch_command.json", 'w') as f:
            json.dump(command, f)
        
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    
@app.route("/api/logs")
def api_logs():
    try:
        with open("logs/patch.log", "r", encoding="utf-8") as f:
            lines = f.readlines()[-200:]  # last 200 lines
        return jsonify(lines)
    except:
        return jsonify([])

if __name__ == '__main__':
    print("\n" + "="*50)
    print("PATCH DASHBOARD SERVER STARTING")
    print("="*50)
    print("\nAccess dashboard at:")
    print("  Local:   http://localhost:5000")
    print("  Network: http://YOUR_IP:5000")
    print("\nPress Ctrl+C to stop\n")
    
    # Run Flask server
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)


## IM A FUCKING GENIUSSSSSS