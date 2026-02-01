# Patch AI 🤖  
*A personal humanoid AI robot project*

Patch is a locally-running AI assistant designed to eventually live inside a **physical humanoid robot**, inspired by **Pathfinder (Apex Legends)** and **MRVN (Titanfall)**.

Right now, Patch exists as a software “brain” (`brain.py`) that handles:
- Speech recognition  
- Text-to-speech  
- Local LLM reasoning (via Ollama)  
- A persistent reminder system  
- Daily summaries  
- Hardware-aware GPU / CPU fallback  
- System personality and behavior logic  

This project is being built **incrementally**, with stability, realism, and future robotics integration in mind.

---

## ✨ Features

- 🧠 **Local LLM Brain**  
  Uses Ollama for on-device reasoning (no cloud required)

- 🗣 **Voice I/O Pipeline**  
  STT → Reasoning → TTS using Soprano

- ⏰ **Reminder System**
  - Natural language time parsing  
  - Missed-reminder recovery  
  - Archiving with retention limits  
  - Daily summaries (manual trigger)

- ⚙️ **Smart Hardware Management / DYNAMIC RESOURCE MANAGEMENT** (It sounds cooler.)
  - Detects GPU availability  
  - Dynamically falls back to CPU if VRAM is low  
  - Prevents CUDA crashes automatically

- 🧹 **Storage & Cache Safety**
  - Automatic archive pruning  
  - Model cache cleanup tools  
  - Prevents multi-GB runaway folders

- 🎭 **Personality System**
  - Pathfinder-inspired tone (Apex Legends)
  - Short, expressive speech  
  - Voice-safe output (no emojis)

---

## 🎙 Voice Commands (Current)

Patch supports **voice and text interaction modes**, with wake/sleep states and safety-gated commands.  
Commands are designed to be **natural language**, not strict syntax.



### 🔊 Interaction & Power Control
- **“Patch wake up”**  
  Wakes Patch from sleep mode

- **“Patch sleep” / “Pause system” / “Temporarily sleep”**  
  Puts Patch into low-power listening mode (wake-word only)

- **“Switch to voice mode”**  
- **“Switch to chat mode”**  
  Changes the interaction method on the fly

- **“Exit” / “Shut down” / “Power down”**  
  Gracefully shuts down Patch with audio feedback



### 🧠 Memory & System Control
- **“Reset memory” / “Forget everything” / “Clear history”**  
  Clears conversation memory

- **“Clean your system”**  
  Removes cached junk and temporary files

- **“Total reset”** ⚠️  
  Performs a full storage reset (model cache + memory)  
  *Confirmation required*



### ⏰ Reminder System
#### Add Reminders
- **“Remind me to …”**
- **“Schedule task …”**
- **“Log reminder …”**
- **“Set alarm …”**
- **“Create reminder …”**

Patch:
- Extracts tasks using regex (no GPU required)
- Parses time from natural language
- Enforces reminder limits safely



#### List Reminders
- **“List reminders”**
- **“What’s on my schedule?”**
- **“Reminder status”**
- **“Mission log”**
- **“What’s on my agenda?”**

Patch will verbally read up to 5 active reminders.



#### Delete / Abort Reminders
- **“Delete task …”**
- **“Cancel reminder …”**
- **“Abort mission …”**
- **“Remove reminder …”**

Deletes reminders using keyword matching.



#### Wipe Reminders (Developer / Safety-Gated)
- **“Wipe active reminders”**
- **“Wipe reminder archive”**
- **“Wipe all reminders”** ⚠️  
  Requires spoken + typed confirmation



### 📊 Daily Summary
- **“Daily summary”**
- **“Mission summary”**
- **“Status report”**
- **“How did I do today?”**
- **“Today’s summary”**

Provides a spoken summary using Patch’s personality system.  
(Currently manual-trigger only.)



### 🌦 Weather Queries
- **“Weather in _[city]_”**
- **“Weather for _[city]_”**
- **“Atmospheric conditions in _[city]_”**
- **“Environmental report _[city]_”**

Patch fetches live weather data and reacts in a Pathfinder-inspired tone.



### 🔍 Web Search (Experimental)
- **“Search for …”**
- **“Look up …”**
- **“Open Google …”**
- **“Search engine active”**

Web search support is under active development.



### 🧠 Behavior Notes
- Patch ignores commands while sleeping (except wake-word)
- Some destructive actions require confirmation
- GPU is **never required** for command parsing
- Personality output is **voice-safe (no emojis)**



### 🚧 Planned
- Wake-word-only idle mode
- Contextual follow-ups
- Emotion-aware responses
- Robotics sensor integration

---

## 🚫 What is NOT committed

This repository intentionally ignores:
- Model weights and caches  
- Runtime memory and reminder data  
- Generated audio files  
- Experimental and offloaded folders  

See `.gitignore` for details.

---

## 🧪 Current Status

- ✅ Core systems stable  
- ✅ Reminder logic complete  
- ✅ GPU/CPU fallback working  
- 🚧 Robotics hardware integration (future)  
- 🚧 Vision and sensors (future)  

This project is under **active development** and frequently refactored.

---

## 🚀 Long-Term Goal

Patch will eventually become:
- A **physical humanoid robot**  
- With voice, personality, memory, and autonomy  
- Running **entirely locally**

This repository currently represents the **brain**, not the body.
(I mean... I don't even know if I can **represent** the body on GitHub)

---

## ⚠️ Disclaimer

This project is experimental and built for learning, exploration, and fun.  
APIs, structure, and behavior may often change.

PLEASE NOTE THAT I'm 15. I tried my best (┬┬﹏┬┬)
If you have any suggestions, comments, or would like to offer some help, please do so by contacting me

---

## 👤 Author

Built by **Natt** (currently a 15-year-old on January 30, 2026)
