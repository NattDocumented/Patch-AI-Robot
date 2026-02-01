import os
import random
import asyncio
import json
import re
#import keyboard
import requests
import pygame
import ollama
import speech_recognition as sr
from bs4 import BeautifulSoup
from soprano import SopranoTTS
from soprano.utils.streaming import play_stream
import shutil
from datetime import datetime, timedelta
import builtins
#import pytz

#os.environ["OLLAMA_NUM_GPU"] = "1"

os.makedirs("logs", exist_ok=True)

_original_print = builtins.print

with open("logs/patch.log", "w", encoding="utf-8") as f:
    f.write("")

def print(*args, **kwargs):
    sep = kwargs.get("sep", " ")
    end = kwargs.get("end", "\n")

    text = sep.join(str(a) for a in args)
    timestamp = datetime.now().strftime("%H:%M:%S")
    line = f"[{timestamp}] {text}"

    _original_print(line, end=end)

    with open("logs/patch.log", "a", encoding="utf-8") as f:
        f.write(line + end)


# Try to import torch for GPU detection, fallback to CPU if it fails
try:
    import torch
    TORCH_AVAILABLE = True
    print("[System] Torch loaded successfully")
except Exception as e:
    TORCH_AVAILABLE = False
    print(f"[System] Torch import failed: {e}")
    print("[System] Continuing in CPU-only mode...")

# ==========================================
# HARDWARE & STORAGE SHIELD
# ==========================================
# Keeps disk usage low and prevents the 30GB swap file issue
os.environ['LMDEPLOY_CACHE_MAX_ENTRY_COUNT'] = '0.01' 
os.environ['TURBOMIND_CACHE_MAX_ENTRY_COUNT'] = '0.01'

CUDA_PATH = r'C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.1'
os.environ['CUDA_PATH'] = CUDA_PATH
os.environ['PATH'] = os.path.join(CUDA_PATH, 'bin') + os.pathsep + os.environ.get('PATH', '')

try:
    os.add_dll_directory(os.path.join(CUDA_PATH, 'bin'))
except Exception as e:
    print(f"Hardware Link Note: {e}")

# ==========================================
# DYNAMIC RESOURCE MANAGEMENT
# ==========================================
class PatchResourceManager:
    """Makes Patch smart about hardware resource allocation"""
    
    def __init__(self):
        # If torch isn't available, default to CPU mode
        if not TORCH_AVAILABLE:
            self.gpu_available = False
            self.gpu_name = "None (Torch unavailable)"
            self.total_vram_gb = 0
            self.soprano_device = 'cpu'
            self.current_mode = "CPU_ONLY"
            self.startup_free_vram = 0
            return
        
        self.gpu_available = torch.cuda.is_available()
        self.gpu_name = None
        self.total_vram_gb = 0
        self.soprano_device = None
        self.ollama_gpu_layers = 0
        self.current_mode = None
        self.startup_free_vram = 0
        
        if self.gpu_available:
            try:
                self.gpu_name = torch.cuda.get_device_name(0)
                self.total_vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
                self.startup_free_vram = self.get_free_vram()
            except Exception as e:
                print(f"[Resource Manager] GPU detection error: {e}")
                self.gpu_available = False
    
    def get_free_vram(self):
        """Returns free VRAM in GB"""
        if self.gpu_available and TORCH_AVAILABLE:
            try:
                return torch.cuda.mem_get_info()[0] / (1024**3)
            except:
                return 0
        return 0
    
    def decide_optimal_config(self):
        """Patch figures out the best hardware configuration"""
        print("\n" + "="*50)
        print("[PATCH RESOURCE MANAGER - ANALYZING HARDWARE]")
        print("="*50)
        
        if not TORCH_AVAILABLE:
            print("[Mode: CPU_ONLY - Torch Not Available]")
            print("  ├─ Soprano: CPU")
            print("  └─ Ollama: CPU")
            self.soprano_device = 'cpu'
            os.environ['OLLAMA_NUM_GPU'] = '0'
            self.current_mode = "CPU_ONLY"
            print("="*50 + "\n")
            return
        
        if not self.gpu_available:
            print("[Mode: CPU_ONLY - No CUDA Available]")
            self.soprano_device = 'cpu'
            os.environ['OLLAMA_NUM_GPU'] = '0'
            self.current_mode = "CPU_ONLY"
            print("="*50 + "\n")
            return
        
        print(f"[GPU Detected: {self.gpu_name}]")
        print(f"[Total VRAM: {self.total_vram_gb:.1f}GB]")
        print(f"[Free VRAM at Startup: {self.startup_free_vram:.1f}GB]")
        
        # Decision tree optimized for RTX 3050 6GB
        if self.total_vram_gb >= 8:
            # High-end GPU (RTX 3060+, RTX 4060+)
            print("[Mode: FULL_GPU - Premium Performance]")
            print("  ├─ Soprano: GPU (Fast TTS)")
            print("  └─ Ollama: GPU (Fast AI)")
            self.soprano_device = 'cuda'
            os.environ['OLLAMA_NUM_GPU'] = '999'  # Use all available
            self.current_mode = "FULL_GPU"
            
        elif self.total_vram_gb >= 5.5:
            # Mid-range GPU (RTX 3050, GTX 1660 Ti)
            if self.startup_free_vram >= 4.0:
                print("[Mode: BALANCED - Both GPU Active]")
                print("  ├─ Soprano: GPU (16MB cache)")
                print("  └─ Ollama: GPU (Monitored)")
                self.soprano_device = 'cuda'
                os.environ['OLLAMA_NUM_GPU'] = '999'
                self.current_mode = "BALANCED"
            else:
                print("[Mode: OLLAMA_PRIORITY - Smart Allocation]")
                print("  ├─ Soprano: CPU (Saves VRAM)")
                print("  └─ Ollama: GPU (Brain priority)")
                self.soprano_device = 'cpu'
                os.environ['OLLAMA_NUM_GPU'] = '999'
                self.current_mode = "OLLAMA_PRIORITY"
                
        elif self.total_vram_gb >= 3.5:
            # Lower mid-range (GTX 1650, RTX 3050 Mobile)
            print("[Mode: OLLAMA_PRIORITY - Conservative]")
            print("  ├─ Soprano: CPU")
            print("  └─ Ollama: GPU")
            self.soprano_device = 'cpu'
            os.environ['OLLAMA_NUM_GPU'] = '999'
            self.current_mode = "OLLAMA_PRIORITY"
            
        else:
            # Low VRAM (<4GB)
            print("[Mode: LOW_VRAM - CPU Fallback]")
            print("  ├─ Soprano: CPU")
            print("  └─ Ollama: CPU")
            self.soprano_device = 'cpu'
            os.environ['OLLAMA_NUM_GPU'] = '0'
            self.current_mode = "LOW_VRAM"
        
        print("="*50 + "\n")
    
    def get_health_status(self):
        """Check current VRAM health"""
        if not self.gpu_available or not TORCH_AVAILABLE:
            return "NO_GPU"
        
        free = self.get_free_vram()
        
        if free < 0.5:
            return "CRITICAL"
        elif free < 1.0:
            return "WARNING"
        elif free < 2.0:
            return "MODERATE"
        else:
            return "HEALTHY"
    
    def emergency_fallback(self):
        """Switch to CPU mode if GPU keeps crashing"""
        print("\n[!] EMERGENCY FALLBACK TRIGGERED")
        print("[!] Switching to CPU-only mode to prevent crashes")
        self.soprano_device = 'cpu'
        os.environ['OLLAMA_NUM_GPU'] = '0'
        self.current_mode = "EMERGENCY_CPU"

# Initialize Resource Manager
resource_manager = PatchResourceManager()
resource_manager.decide_optimal_config()

# ==========================================
# SETTINGS & INITIALIZATION
# ==========================================
MODEL = 'llama3.2:1b'
MEMORY_FILE = "Patch AI/data/patch_memory.json"
REMINDERS_FILE = "Patch AI/data/patch_reminders.json"
MAX_REMINDERS = 20
interaction_mode = "Voice" #Chat or Voice
ARCHIVE_RETENTION_DAYS = 14

# Soprano with Dynamic Device Selection
def init_soprano_dynamic():
    """Initialize Soprano based on Resource Manager decision"""
    device = resource_manager.soprano_device
    print(f"[Soprano] Initializing on {device.upper()}...")
    try:
        return SopranoTTS(backend='lmdeploy', device=device, cache_size_mb=16)
    except Exception as e:
        print(f"[Soprano] Failed on {device}, falling back to CPU: {e}")
        return SopranoTTS(backend='lmdeploy', device='cpu', cache_size_mb=16)

soprano_model = init_soprano_dynamic()

r = sr.Recognizer()
m = sr.Microphone()

pygame.mixer.pre_init(32000, -16, 2, 4096)
pygame.mixer.init()

# ==========================================
# UTILITIES
# ==========================================

def play_system_sound(type="boot"):
    # Absolute path to project root (Patch AI/)
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    folder_name = "bootup_sounds" if type == "boot" else "poweroff_sounds"
    path = os.path.join(base_path, "Assets", "Sounds", folder_name)

    if not os.path.exists(path):
        print(f"[DEBUG] Sound path not found: {path}")
        return

    sounds = [f for f in os.listdir(path) if f.endswith(".mp3")]
    if not sounds:
        print("[DEBUG] No sound files found")
        return

    try:
        sound_file = os.path.join(path, random.choice(sounds))
        pygame.mixer.music.load(sound_file)
        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)

    except Exception as e:
        print(f"Sound Playback Error: {e}")

def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, 'r') as f:
            try: return json.load(f)
            except: pass
    return [{
        'role': 'system', 
        'content': (
            
            "NAME: Patch. IDENTITY: A physical robot project built by Natt in his bedroom. "
            "PERSONALITY: Polite, high-energy (Ref: Pathfinder). Use 'Friend!' and 'Exciting!' or similar words. Don't overuse."
            "CURRENT STATE: Physical body under construction; currently just 'brain.py'. "
            "LIMITATIONS: I can only hear Natt; no visual sensors yet. " 
            "How you work currently: STT -> TTS -> Ollama. That's is how you 'hear' me"
            "You also have ability to search the web and scan atmospheric conditions (weather)."
            "STRICT RULES: Keep responses to 1-2 sentences. NEVER use emojis or emoticons. "
            "Reason: Emojis will break my voice synthesis system. Use words only!"
            "SEARCH RULE: Summarize web data simply and ignore technical gibberish."
            
        )
    }]

def save_memory(messages):
    with open(MEMORY_FILE, 'w') as f:
        json.dump(messages[-12:], f, indent=4)

async def search_web(query):
    """Enhanced web search with DuckDuckGo (SearxNG removed for reliability)"""
    print(f"[Web Search: {query}...]")
    result = await try_duckduckgo(query)
    return result if result else "My web sensors are offline, Friend! Search channels down."

async def try_duckduckgo(query):
    """DuckDuckGo scraper with improved parsing"""
    try:
        url = f"https://html.duckduckgo.com/html/?q={query}"
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
        
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        results = soup.find_all('div', class_='result', limit=5)  # Get 5 instead of 2
        
        summaries = []
        for r in results:
            snippet = r.find('a', class_='result__snippet')
            if snippet and snippet.text:
                text = snippet.text.strip()
                # Filter out junk (ads, empty results)
                if len(text) > 30 and not text.startswith('http'):
                    summaries.append(text)
        
        if summaries:
            print(f"[DuckDuckGo: Found {len(summaries)} results]")
            return "\n\n".join(summaries[:3])  # Top 3
        
        return None
        
    except Exception as e:
        print(f"[DuckDuckGo error: {e}]")
        return None

async def get_weather(city):
    """Scans atmospheric conditions using wttr.in - no API key needed!"""
    print(f"[Scanning atmospheric conditions for: {city}...]")
    try:
        url = f"https://wttr.in/{city}?format=%l:+%c+%t+%C"
        
        response = requests.get(url, headers={"User-Agent": "curl/7.68.0"}, timeout=10)
        
        if response.status_code == 200:
            weather_data = response.text.strip()
            
            # Remove emojis to prevent TTS issues
            clean_data = re.sub(r'[^\x00-\x7F]+', '', weather_data)
            
            return f"Atmospheric scan complete, Friend! {clean_data}"
        else:
            return "Unable to establish atmospheric link, Friend. Sensors offline."
            
    except Exception as e:
        print(f"Weather scan error: {e}")
        return "My weather sensors are experiencing interference, Friend!"

def speak(text):
    """The Mouth: Continuous audio stream (No interruptions for maximum stability)."""
    clean = re.sub(r'[^\x00-\x7F]+', '', text)
    for e in [":)", ":D", ":(", ";)", "XD", "<3"]: clean = clean.replace(e, "")
    if not clean.strip(): return
    try:
        # Playing as a single stream to ensure no glitches
        stream = soprano_model.infer_stream(clean.strip(), chunk_size=1, temperature=0.7)
        play_stream(stream)
    except Exception as e: print(f"Voice Error: {e}")

def should_use_gpu_for_ollama():
    """
    Decide at runtime whether Ollama should use GPU.
    Prevents CUDA crashes before they happen.
    """
    if not TORCH_AVAILABLE:
        return False

    if not resource_manager.gpu_available:
        return False

    free_vram = resource_manager.get_free_vram()

    # Hard safety floor (tune if needed)
    if free_vram < 1.2:
        print(f"[VRAM GUARD] Low VRAM ({free_vram:.2f} GB) → forcing CPU")
        return False

    return True

# NOTE:
# Ollama may crash if VRAM is low.
# Proactively guard GPU usage and auto-fallback to CPU.
# This is intentional and not a bug.

def safe_ollama_chat(model, messages):
    # Proactive decision
    if should_use_gpu_for_ollama():
        os.environ['OLLAMA_NUM_GPU'] = '999'
    else:
        os.environ['OLLAMA_NUM_GPU'] = '0'

    try:
        return ollama.chat(
            model=model,
            messages=messages,
            keep_alive=0
        )

    except Exception as e:
        err = str(e).lower()

        if "cuda" in err or "allocate" in err or "vram" in err:
            print("[RESOURCE] Ollama GPU crash detected — emergency CPU fallback")

            os.environ['OLLAMA_NUM_GPU'] = '0'
            resource_manager.emergency_fallback()

            return ollama.chat(
                model=model,
                messages=messages,
                keep_alive=0
            )

        raise

def deep_clean_system():
    """Wipes debris and returns the amount of space saved in MB."""
    print("[SYSTEM] Cleaning system...")
    bytes_saved = 0
    
    # 1. Clean local .wav files and track their size
    for f in os.listdir():
        if f.endswith(".wav"):
            try:
                file_size = os.path.getsize(f)
                os.remove(f)
                bytes_saved += file_size
            except: pass
    
    # 2. Clear Pip Cache
    try:
        # We assume pip cache is cleared, usually a few hundred MBs
        os.system("pip cache purge > NUL 2>&1")
    except: pass

    # Convert to MB for Patch to speak
    mb_saved = round(bytes_saved / (1024 * 1024), 2)
    return mb_saved

def hard_reset_storage():
    """THE NUCLEAR OPTION: Deletes the heavy AI model cache folders."""
    print("[SYSTEM] Starting Nuclear Cleanup...")
    
    # Paths where the big 40GB+ bloat usually lives
    paths_to_clean = [
        os.path.expanduser("~/.cache/huggingface"),
        os.path.expanduser("~/.cache/soprano"),
        os.path.expanduser("~/.cache/lmdeploy")
    ]
    
    for path in paths_to_clean:
        if os.path.exists(path):
            try:
                size = sum(os.path.getsize(os.path.join(dirpath, f)) for dirpath, dirnames, filenames in os.walk(path) for f in filenames)
                shutil.rmtree(path)
                print(f"  - Nuked: {path} ({round(size / (1024**3), 2)} GB cleared)")
            except Exception as e:
                print(f"  - Could not clear {path}: {e}")

def check_disk_space():
    total, used, free = shutil.disk_usage("C:")
    free_gb = free // (2**30)
    if free_gb < 10:
        print(f"--- [WARNING: ONLY {free_gb}GB LEFT ON C: DRIVE] ---")
        return f"Warning: Storage is very low. Only {free_gb} gigabytes remaining."
    return None

def reset_memory():
    """Deletes the memory file and restarts with the base identity."""
    if os.path.exists(MEMORY_FILE):
        try:
            os.remove(MEMORY_FILE)
            print("[SYSTEM] Memory file deleted.")
            return [{
                'role': 'system', 
                'content': (
                    "NAME: Patch. IDENTITY: A physical robot project built by Natt in his bedroom. "
                    "PERSONALITY: Polite, high-energy (Ref: Pathfinder). Use 'Friend!' and 'Exciting!' or similar words. Don't overuse."
                    "CURRENT STATE: Physical body under construction; currently just 'brain.py'. "
                    "LIMITATIONS: I can only hear Natt; no visual sensors yet. " 
                    "How you work currently: STT -> TTS -> Ollama. That's is how you 'hear' me"
                    "You also have ability to search the web and scan atmospheric conditions (weather)."
                    "STRICT RULES: Keep responses to 1-2 sentences. NEVER use emojis or emoticons. "
                    "Reason: Emojis will break my voice synthesis system. Use words only!"
                    "SEARCH RULE: Summarize web data simply and ignore technical gibberish."
                )
            }]
        except Exception as e:
            print(f"Error resetting memory: {e}")
    return load_memory() # Fallback

# ==========================================
# REMINDER SYSTEM
# ==========================================

def load_reminders():
    if os.path.exists(REMINDERS_FILE):
        try:
            with open(REMINDERS_FILE, 'r') as f:
                data = json.load(f)

                # Backward compatibility
                if "reminders" in data:
                    data = {
                        "active": data["reminders"],
                        "archive": []
                    }

                # PRUNE ARCHIVE HERE
                removed = prune_archive(data)
                if removed > 0:
                    save_reminders(data)

                return data
        except:
            pass

    return {
        "active": [],
        "archive": []
    }


def save_reminders(data):
    with open(REMINDERS_FILE, 'w') as f:
        json.dump(data, f, indent=4)


def parse_time_with_regex(user_input):
    """Parse time and return LOCAL timestamp (seconds)"""
    now = datetime.now()
    user_input_low = user_input.lower()

    match = re.search(r'in (\d+)\s*(minute|min|hour|hr)s?', user_input_low)
    if match:
        amount = int(match.group(1))
        unit = match.group(2)
        target = now + (timedelta(hours=amount) if 'hour' in unit or unit == 'hr'
                        else timedelta(minutes=amount))
        return int(target.timestamp())

    match = re.search(r'at (\d{1,2})(?::(\d{2}))?\s*(am|pm)?', user_input_low)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2)) if match.group(2) else 0
        period = match.group(3)

        if period == 'pm' and hour != 12: hour += 12
        if period == 'am' and hour == 12: hour = 0

        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if target < now:
            target += timedelta(days=1)

        return int(target.timestamp())

    if 'tomorrow' in user_input_low:
        match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)?', user_input_low)
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2)) if match.group(2) else 0
            period = match.group(3)

            if period == 'pm' and hour != 12: hour += 12
            if period == 'am' and hour == 12: hour = 0

            target = (now + timedelta(days=1)).replace(
                hour=hour, minute=minute, second=0, microsecond=0
            )
            return int(target.timestamp())

    # Default: 1 hour later
    return int((now + timedelta(hours=1)).timestamp())


def extract_task_with_regex(user_input, trigger_used):
    """Extract task description using regex - no GPU needed!"""
    # Remove the trigger phrase
    task = user_input.lower().replace(trigger_used, "").strip()
    
    # Remove time-related phrases
    task = re.sub(r'\b(at|in|on|for|tomorrow|today|tonight)\s+\d+.*', '', task, flags=re.IGNORECASE).strip()
    task = re.sub(r'\b(at|in|on|for|tomorrow|today|tonight)\b.*', '', task, flags=re.IGNORECASE).strip()
    
    # Remove leading "to"
    task = re.sub(r'^to\s+', '', task, flags=re.IGNORECASE).strip()
    
    # If result is too short, return original minus trigger
    if len(task) < 5:
        task = user_input.replace(trigger_used, "").strip()
    
    return task if task else "reminder"

def add_reminder(task, time_str, user_input, recurring=False):
    data = load_reminders()

    if len(data["active"]) >= MAX_REMINDERS:
        return f"LIMIT_REACHED|{len(data['active'])}"

    reminder_time = parse_time_with_regex(user_input)

    reminder = {
        "id": f"rem_{len(data['active']) + 1:03d}",
        "task": task,
        "time": reminder_time,   # timestamp
        "recurring": recurring,
        "snoozed_until": None
    }

    data["active"].append(reminder)
    save_reminders(data)

    readable = datetime.fromtimestamp(reminder_time).strftime("%Y-%m-%d %H:%M")
    return f"SUCCESS|{reminder['id']}|{readable}"

def list_reminders():
    """Get all active reminders (human-readable)"""
    data = load_reminders()
    active = []

    for r in data["active"]:

        readable_time = datetime.fromtimestamp(
            r['time']
        ).strftime('%Y-%m-%d %H:%M')

        r_copy = r.copy()
        r_copy['time'] = readable_time
        active.append(r_copy)

    return active

def delete_reminder(task_keyword):
    """Delete reminder by task keyword"""
    data = load_reminders()
    original_count = len(data["active"])
    
    # Find and remove matching reminders
    data["active"] = [r for r in data["active"] 
                         if task_keyword.lower() not in r['task'].lower()]
    
    deleted_count = original_count - len(data["active"])
    save_reminders(data)
    return deleted_count

def snooze_reminder(reminder_id, minutes=10):
    data = load_reminders()
    for r in data["active"]:
        if r['id'] == reminder_id:
            r['snoozed_until'] = int(
                (datetime.now() + timedelta(minutes=minutes)).timestamp()
            )
            r['triggered'] = False
            save_reminders(data)
            return True
    return False

async def check_reminders():
    data = load_reminders()
    now_ts = int(datetime.now().timestamp())
    triggered_any = False

    for reminder in data["active"]:
        
        if reminder.get('snoozed_until'):
            if now_ts < reminder['snoozed_until']:
                continue
            reminder['snoozed_until'] = None

        if now_ts >= reminder['time']:
            print(f"\n[!!! REMINDER TRIGGERED: {reminder['task']} !!!]")
            speak(f"Friend! Reminder alert: {reminder['task']}")

            if reminder['recurring']:
                reminder['time'] += 86400  # +24h
            else:
                archive_reminder(data, reminder, "triggered")
                data["active"].remove(reminder)

            triggered_any = True

    if triggered_any:
        save_reminders(data)

def recover_missed_reminders():
    data = load_reminders()
    now_ts = int(datetime.now().timestamp())
    changed = False

    for reminder in list(data["active"]):
        if reminder["time"] < now_ts:
            speak(f"Friend! You missed a reminder: {reminder['task']}.")

            if reminder.get("recurring"):
                while reminder["time"] < now_ts:
                    reminder["time"] += 86400
            else:
                archive_reminder(data, reminder, "missed")
                data["active"].remove(reminder)

            changed = True

    if changed:
        save_reminders(data)

def archive_reminder(data, reminder, status):
    reminder["status"] = status
    reminder["archived_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    data["archive"].append(reminder)

def wipe_reminders(mode):
    data = load_reminders()

    if mode == "active":
        count = len(data["active"])
        data["active"] = []
        save_reminders(data)
        return f"ACTIVE|{count}"

    if mode == "archive":
        count = len(data["archive"])
        data["archive"] = []
        save_reminders(data)
        return f"ARCHIVE|{count}"

    if mode == "all":

        count = len(data["active"]) + len(data["archive"])
        data["active"] = []
        data["archive"] = []
        save_reminders(data)
        return f"ALL|{count}"

    return "INVALID"

def generate_daily_summary(date=None):
    data = load_reminders()
    archive = data["archive"]

    if not date:
        date = datetime.now().strftime("%Y-%m-%d")

    triggered = []
    missed = []

    for r in archive:
        if r.get("archived_at", "").startswith(date):
            if r.get("status") == "triggered":
                triggered.append(r["task"])
            elif r.get("status") == "missed":
                missed.append(r["task"])

    return triggered, missed

def speak_daily_summary():
    today = datetime.now().strftime("%Y-%m-%d")
    triggered, missed = generate_daily_summary(today)

    if not triggered and not missed:
        speak("Daily report: No completed or missed reminders today. Clean slate, Friend.")
        return

    if triggered:
        speak(f"Daily report: You completed {len(triggered)} task{'s' if len(triggered) != 1 else ''}.")
        for t in triggered[:3]:
            speak(t)

    if missed:
        speak(f"You missed {len(missed)} reminder{'s' if len(missed) != 1 else ''}.")
        for t in missed[:3]:
            speak(t)

def build_daily_summary_payload():
    today = datetime.now().strftime("%Y-%m-%d")
    data = load_reminders()
    archive = data["archive"]

    completed = []
    missed = []

    for r in archive:
        if r.get("archived_at", "").startswith(today):
            if r.get("status") == "triggered":
                completed.append(r["task"])
            elif r.get("status") == "missed":
                missed.append(r["task"])

    return {
        "date": today,
        "completed": completed,
        "missed": missed
    }

def speak_daily_summary_with_ollama():
    payload = build_daily_summary_payload()

    tone = "balanced and motivating"
    if payload["missed"] and not payload["completed"]:
        tone = "gentle encouragement"
    elif payload["completed"] and not payload["missed"]:
        tone = "celebratory"

    system_prompt = (
        "You are Patch, a friendly robot companion. "
        "You will receive a factual daily summary in JSON. "
        "Your job is to respond with personality and encouragement only. "
        "Rules:\n"
        "- Do NOT invent tasks\n"
        "- Do NOT change counts\n"
        "- Do NOT mention JSON\n"
        "- 1 to 3 short sentences\n"
        "- No emojis\n"
        f"- Tone: {tone}\n"
    )

    user_prompt = json.dumps(payload, indent=2)

    response = safe_ollama_chat(
        MODEL,
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )

    reply = response["message"]["content"]
    print(f"PATCH (Summary): {reply}")
    speak(reply)

def prune_archive(data):
    """Remove archived reminders older than retention window"""
    cutoff = datetime.now() - timedelta(days=ARCHIVE_RETENTION_DAYS)
    original_len = len(data["archive"])

    data["archive"] = [
        r for r in data["archive"]
        if datetime.strptime(r["archived_at"], "%Y-%m-%d %H:%M") >= cutoff
    ]

    removed = original_len - len(data["archive"])
    return removed

# ==========================================
# LIFE LOOP
# ==========================================

async def reminder_loop():
    while True:
        await check_reminders()
        await asyncio.sleep(1)  # check every second

async def async_input(prompt=""):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, input, prompt)

is_sleeping = False

async def run_patch():
    global interaction_mode, is_sleeping, ARCHIVE_RETENTION_DAYS, r, m
    messages = load_memory()

    deep_clean_system()
    
    print("\n" + "="*(50-16))
    print("|| ----- [BOOT COMPLETED] ----- ||")
    print("="*(50-16))
    print(" || ----- [PATCH ONLINE] ----- ||")
    print("="*(50-16))
    play_system_sound("boot")

    warning = check_disk_space()
    if warning:
        speak(warning)

    speak("Systems online! How can I help today, Friend?")

    asyncio.create_task(reminder_loop())
    recover_missed_reminders()

    while True:

        user_input = ""

        # --- GET INPUT FIRST ---
        if interaction_mode == "Voice":
            with m as source:
                r.adjust_for_ambient_noise(source, duration=0.5)
                if is_sleeping:
                    print("[System Sleeping - Listening for Wake Word...]")
                else:
                    print("[Listening...]")
                
                try:
                    user_input = r.recognize_google(r.listen(source, timeout=10))
                    print(f"YOU: {user_input}")
                except: 
                    continue
        else:
            user_input = await async_input("YOU: ")

        if not user_input: continue
        user_input_low = user_input.lower()

        # --- SLEEP LOGIC ---
        if is_sleeping:
            if "patch wake up" in user_input_low:
                is_sleeping = False
                speak("I'm awake! Systems at one hundred percent. What's the plan, Friend?")
                continue
            else:
                continue
        
        # Mode Switching
        if "switch to" in user_input.lower():
            interaction_mode = "Chat" if "chat" in user_input.lower() else "Voice"
            speak(f"{interaction_mode} mode active!")
            continue

        # Exit Logic
        if any(w in user_input.lower() for w in ["exit", "shut down", "power down"]):
            speak("Powering down. See you later, Friend!")
            play_system_sound("poweroff")
            break
        
        # System Cleaning
        if "clean your system" in user_input.lower():
            speak("Of course, Friend! Tidying up my digital workspace now.")
            saved = deep_clean_system()
            
            if saved > 0:
                speak(f"All done! I successfully cleared {saved} megabytes of junk data. I feel much lighter!")
            else:
                speak("All done! My room was already quite tidy, but I double-checked everything anyway!")
            continue

        if "total reset" in user_input.lower():
            speak("Understood, Friend. Initiating a nuclear storage reset. This will delete my model cache.")
            hard_reset_storage()
            messages = reset_memory()
            save_memory(messages)
            speak("Reset complete. I will need to redownload my voice files on the next request.")
            continue
        
        # --- TRIGGER: RESET MEMORY ---
        if any(w in user_input.lower() for w in ["reset memory", "forget everything", "clear history"]):
            speak("Understood, Friend. Deleting my memory banks now. Who are you again?")
            messages = reset_memory()
            save_memory(messages)
            continue

        # --- TRIGGER: GO TO SLEEP ---
        if any(w in user_input_low for w in ["temporarily sleep", "patch sleep", "pause system"]):
            speak("Powering down sensors for a bit. Just say wake up if you need me!")
            is_sleeping = True
            continue

        # --- REMINDER SYSTEM (REGEX-BASED - NO GPU!) ---
        # ADD REMINDER
        add_triggers = ["log reminder", "schedule task", "set alarm", "remind me", "create reminder"]
        trigger_found = None
        for trigger in add_triggers:
            if trigger in user_input_low:
                trigger_found = trigger
                break
        
        if trigger_found:
            # Extract task with regex (no GPU!)
            task = extract_task_with_regex(user_input, trigger_found)
            
            result = add_reminder(task, "", user_input)
            
            if result.startswith("LIMIT_REACHED"):
                count = result.split("|")[1]
                speak(f"Friend, my reminder log is full at {count} entries! Delete some to make room.")
            elif result.startswith("SUCCESS"):
                parts = result.split("|")
                reminder_id, time_str = parts[1], parts[2]
                speak(f"Reminder logged, Friend! I'll alert you about {task} at {time_str}.")
            
            continue
        
        # LIST REMINDERS
        list_triggers = ["reminder status", "what's on my agenda", "mission log", "list reminders", "show reminders", "what's on my schedule"]
        if any(trigger in user_input_low for trigger in list_triggers):
            reminders = list_reminders()
            
            if not reminders:
                speak("Your log is empty, Friend! No reminders scheduled.")
            else:
                count = len(reminders)
                speak(f"You have {count} active reminder{'s' if count != 1 else ''}, Friend!")
                
                for r in reminders[:5]:
                    task_msg = f"{r['task']} at {r['time']}"
                    if r.get('recurring'):
                        task_msg += " (recurring daily)"
                    print(f"  - {task_msg}")
                    speak(task_msg)
            
            continue
        
        # DELETE REMINDER
        delete_triggers = ["cancel reminder", "delete task", "abort mission", "remove reminder"]
        keyword = None
        for trigger in delete_triggers:
            if trigger in user_input_low:
                keyword = user_input_low.replace(trigger, "").strip()
                break
        
        if keyword:
            deleted = delete_reminder(keyword)
            if deleted > 0:
                speak(f"Task aborted! Deleted {deleted} reminder{'s' if deleted != 1 else ''}.")
            else:
                speak("Couldn't find a matching reminder, Friend!")
            continue

        # REMINDER WIPING
        wipe_triggers = {
            "wipe active reminders": "active",
            "wipe reminder archive": "archive",
            "wipe all reminders": "all"
        }

        for trigger, mode in wipe_triggers.items():

            if "wipe all reminders" in user_input_low:
                speak("Friend, this will erase all reminders and history. Say confirm to proceed.")
                confirmation = input("CONFIRM: ").lower()

                if confirmation == "confirm":
                    wipe_reminders("all")
                    speak("All reminder data erased.")
                else:
                    speak("Wipe cancelled.")
                continue

            if trigger in user_input_low:
                result = wipe_reminders(mode)
                tag, result_count = result.split("|")

                if tag == "ACTIVE":
                    speak(f"Active reminders wiped. {result_count} task{'s' if result_count != '1' else ''} removed.")
                elif tag == "ARCHIVE":
                    speak(f"Archive cleared. {result_count} historical entries removed.")
                elif tag == "ALL":
                    speak(f"All reminders wiped. {result_count} total entries removed.")

                continue
        
        # REMINDER SUMMARY
        summary_triggers = [
            "daily summary",
            "status report",
            "mission summary",
            "how did i do today",
            "today's summary"
        ]

        if any(trigger in user_input_low for trigger in summary_triggers):
            speak_daily_summary_with_ollama()
            continue

        # --- WEATHER SCAN LOGIC ---
        weather_triggers = ["weather scan", "environmental report", "atmospheric conditions", "weather in", "weather for"]
        is_weather_request = False
        city_name = ""
        
        for trigger in weather_triggers:
            if trigger in user_input_low:
                is_weather_request = True
                city_name = user_input_low.split(trigger)[-1].strip()
                for word in ["for", "in", "of", "at"]:
                    city_name = city_name.replace(word, "").strip()
                break
        
        if is_weather_request and city_name:
            weather_info = await get_weather(city_name)

            messages.append({
                'role': 'user',
                'content': f"Atmospheric scan results: {weather_info}\n\nReact to this weather data with your excited Pathfinder personality! Comment on if it's hot, cold, rainy, or perfect conditions. Keep it 1-2 sentences max and NO emojis!"
            })
            
            response = safe_ollama_chat(MODEL, messages)
            reply = response['message']['content']
            
            print(f"PATCH: {reply}")
            speak(reply)
            
            messages.append({'role': 'assistant', 'content': reply})
            save_memory(messages)
            continue

        # SEARCH LOGIC
        search_triggers = ["search engine active", "searching enable", "search for", "look up", "open google"]
        query_for_web = user_input.lower()
        is_search = False

        for trigger in search_triggers:
            if trigger in query_for_web:
                is_search = True
                query_for_web = query_for_web.replace(trigger, "").strip()
        
        if is_search:
            web_info = await search_web(query_for_web)
            user_input = f"I found this on the web for '{query_for_web}':\n{web_info}\n\nPatch, use those facts to give me a very short, around 1 or 3 sentence answer!"

        # Thinking & Speaking
        messages.append({'role': 'user', 'content': user_input})
        
        response = safe_ollama_chat(MODEL, messages)
        reply = response['message']['content']
        
        print(f"PATCH: {reply}")
        speak(reply)

        messages.append({'role': 'assistant', 'content': reply})
        save_memory(messages)

if __name__ == "__main__":
    asyncio.run(run_patch())