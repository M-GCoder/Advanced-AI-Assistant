import os
import cv2
import numpy as np
import pickle
import time
import json
import threading
import queue  # For thread-safe communication
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
import speech_recognition as sr
import pyttsx3
from scipy.spatial.distance import cosine
import customtkinter as ctk  # Modern GUI
import pystray  # Tray icon
from PIL import Image  # For tray icon
#from grok import Grok  # For AI (Option 1)
import pyautogui
#from resemblyzer import VoiceEncoder, preprocess_wav
#from deepface import DeepFace

# ========================
# CONFIG & ENCRYPTION (Optimized: Lazy loading)
# ========================
KEY_FILE = "fortress.key"
FACE_FILE = "face.enc"
VOICE_FILE = "voice.enc"
LOCK_FILE = "lockdown.tmp"
GROK_API_KEY = "gsk"  # Replace with real key

ctk.set_appearance_mode("dark")  # Professional dark theme
ctk.set_default_color_theme("dark-blue")  # Sleek blue accents

engine = pyttsx3.init('sapi5')
voices = engine.getProperty('voices')
engine.setProperty('rate', 180)
engine.setProperty('voice', engine.getProperty('voices')[1].id)  # Female voice

def speak(text):
    print(f"[JARVIS] {text}")
    engine.say(text)
    engine.runAndWait()

def listen():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening...")
        r.pause_threshold = 1
        r.energy_threshold = 400
        audio = r.listen(source, timeout=5, phrase_time_limit=10)

    try:
        print("Recognizing...")
        query = r.recognize_google(audio, language='en-in').lower()
        print(f"You said: {query}")
    except Exception as e:
        speak("Sorry, I didn't catch that.")
        return "none"
    return query

# Encryption helpers (Optimized: Singleton cipher)
def get_cipher():
    key = get_key()
    return Fernet(key)

def get_key():
    if os.path.exists(KEY_FILE):
        return open(KEY_FILE, "rb").read()
    key = Fernet.generate_key()
    with open(KEY_FILE, "wb") as f:
        f.write(key)
    return key

cipher = get_cipher()

def encrypt(b): return cipher.encrypt(b)
def decrypt(b): return cipher.decrypt(b)

# ========================
# Daily Challenge (Optimized: Cache in memory)
# ========================
#TODAY_PHRASE = None
#def refresh_challenge():
#    global TODAY_PHRASE
#    phrases = [
#        "The quick brown fox jumps over the lazy dog",
#        "My voice is my passport verify me",
#        "Peter Piper picked a peck of pickled peppers",
#        "Unique New York you know you need unique New York",
#        "How much wood would a woodchuck chuck if a woodchuck could chuck wood"
#    ]
#    TODAY_PHRASE = np.random.choice(phrases)
#    data = {"date": datetime.now().strftime("%Y-%m-%d"), "phrase": TODAY_PHRASE}
#    with open(CHALLENGE_FILE, "w") as f:
#        json.dump(data, f)
#
#if not os.path.exists(CHALLENGE_FILE) or json.load(open(CHALLENGE_FILE))["date"] != datetime.now().strftime("%Y-%m-%d"):
#    refresh_challenge()
#else:
#    TODAY_PHRASE = json.load(open(CHALLENGE_FILE))["phrase"]

# ========================
# GUI Class – Professional Dashboard
# ========================
class JarvisGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("JARVIS ∞")
        self.geometry("1280x720")
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self.minimize_to_tray)  # Tray on close

        # Thread queues for updates
        self.status_queue = queue.Queue()
        self.chat_queue = queue.Queue()

        # Login Frame
        self.login_frame = ctk.CTkFrame(self)
        self.login_frame.pack(fill="both", expand=True)

        self.attempt_label = ctk.CTkLabel(self.login_frame, text="Attempt 1", font=("Arial", 24, "bold"))
        self.attempt_label.pack(pady=20)

        self.instructions_label = ctk.CTkLabel(self.login_frame, text="Welcome, Master. Starting security check.", wraplength=600, font=("Arial", 16))
        self.instructions_label.pack(pady=10)

        self.status_label = ctk.CTkLabel(self.login_frame, text="Status: Idle", font=("Arial", 14), text_color="yellow")
        self.status_label.pack(pady=10)

        self.progress_bar = ctk.CTkProgressBar(self.login_frame)
        self.progress_bar.pack(pady=10, padx=100)
        self.progress_bar.set(0)

        # Dashboard Frame (hidden initially)
        self.dashboard_frame = ctk.CTkFrame(self)
        self.chat_text = ctk.CTkTextbox(self.dashboard_frame, height=400, font=("Arial", 14))
        self.chat_text.pack(fill="x", pady=10, padx=10)
        self.chat_text.insert("end", "JARVIS: Welcome, Master.\n")

        self.mic_button = ctk.CTkButton(self.dashboard_frame, text="Toggle Mic", command=self.toggle_listening)
        self.mic_button.pack(pady=10)

        self.listening_status = ctk.CTkLabel(self.dashboard_frame, text="Listening...", text_color="green")
        self.listening_status.pack(pady=5)

        # Start update loops
        self.after(100, self.update_status)
        self.after(100, self.update_chat)

        # Listening thread control
        self.listening = False
        self.listen_thread = None
    
    def update_status(self):
        try:
            msg = self.status_queue.get_nowait()
            if "attempt" in msg:
                self.attempt_label.configure(text=msg["attempt"])
            if "instructions" in msg:
                self.instructions_label.configure(text=msg["instructions"])
            if "status" in msg:
                self.status_label.configure(text=msg["status"], text_color=msg.get("color", "yellow"))
            if "progress" in msg:
                self.progress_bar.set(msg["progress"])
        except queue.Empty:
            pass
        self.after(100, self.update_status)

    def update_chat(self):
        try:
            msg = self.chat_queue.get_nowait()
            self.chat_text.insert("end", msg + "\n")
            self.chat_text.see("end")
        except queue.Empty:
            pass
        self.after(100, self.update_chat)

    def show_dashboard(self):
        self.login_frame.pack_forget()
        self.dashboard_frame.pack(fill="both", expand=True)
        self.start_listening()

    def toggle_listening(self):
        if self.listening:
            self.listening = False
            self.listening_status.configure(text="Mic Off", text_color="red")
            self.mic_button.configure(text="Start Mic")
        else:
            self.start_listening()
            self.mic_button.configure(text="Stop Mic")

    def start_listening(self):
        self.listening = True
        self.listening_status.configure(text="Listening...", text_color="green")
        self.listen_thread = threading.Thread(target=voice_loop, args=(self.chat_queue, self.status_queue))
        self.listen_thread.daemon = True
        self.listen_thread.start()

    def minimize_to_tray(self):
        self.withdraw()
        image = Image.open("jarvis_icon.png")  # Create a simple icon file or download one
        menu = (pystray.MenuItem('Show', self.show_from_tray), pystray.MenuItem('Quit', self.quit_app))
        icon = pystray.Icon("JARVIS", image, "JARVIS ∞", menu)
        icon.run()

    def show_from_tray(self, icon):
        icon.stop()
        self.deiconify()

    def quit_app(self, icon):
        icon.stop()
        self.destroy()

# ========================
# Security Layers (Optimized: Threaded, Progress updates)
# ========================
#encoder = VoiceEncoder("cpu")  # Lazy load

def update_gui(queue, data):
    queue.put(data)

def face_liveness_and_recognition(gui_queue):
    update_gui(gui_queue, {"instructions": "Face liveness: Blink twice and move head."})
    cap = cv2.VideoCapture(0)
    blinks = 0
    moved = False
    prev_gray = None
    update_gui(gui_queue, {"progress": 0.2})

    if not os.path.exists(FACE_FILE):
        update_gui(gui_queue, {"status": "No face registered.", "color": "red"})
        return False

    saved_enc = pickle.loads(decrypt(open(FACE_FILE, "rb").read()))
    start = time.time()
    while time.time() - start < 14:
        ret, frame = cap.read()
        if not ret: continue
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    #    try:
    #        eyes = DeepFace.analyze(frame, actions=['emotion'], silent=True, enforce_detection=False)[0]
    #        if eyes['eye_status']['left'] == 'closed' and eyes['eye_status']['right'] == 'closed':
    #            blinks += 1
    #    except: pass

    #    if prev_gray is not None:
    #        diff = cv2.absdiff(prev_gray, gray)
    #        if np.mean(diff) > 15:
    #            moved = True
    #    prev_gray = gray.copy()

    #    encodings = face_recognition.face_encodings(rgb)
    #    if encodings and face_recognition.compare_faces([saved_enc], encodings[0], 0.45)[0]:
    #        if blinks >= 2 and moved:
    #            cap.release()
    #            cv2.destroyAllWindows()
    #            update_gui(gui_queue, {"status": "Face confirmed!", "color": "green"})
    #            return True

        update_gui(gui_queue, {"status": f"Blinks: {blinks}/2 | Moved: {moved}"})

    cap.release()
    cv2.destroyAllWindows()
    return False

def anti_spoof_cough_test(gui_queue):
    update_gui(gui_queue, {"instructions": "Cough loudly for anti-spoof."})
    r = sr.Recognizer()
    with sr.Microphone() as src:
        audio = r.listen(src, phrase_time_limit=5)
    samples = np.frombuffer(audio.get_wav_data(), np.int16)
    return np.max(np.abs(samples)) > 8000

def voice_full_verification(gui_queue):
    if not os.path.exists(VOICE_FILE):
        update_gui(gui_queue, {"status": "Voice not enrolled.", "color": "red"})
        return False

    if not anti_spoof_cough_test(gui_queue):
        update_gui(gui_queue, {"status": "Spoof detected!", "color": "red"})
        return False

    update_gui(gui_queue, {"instructions": f"Say: {TODAY_PHRASE}"})
    r = sr.Recognizer()
    with sr.Microphone() as src:
        r.adjust_for_ambient_noise(src, duration=0.3)  # Optimized: Shorter noise adjust
        audio = r.listen(src, phrase_time_limit=12)

    try:
        said = r.recognize_google(audio).lower()
        if TODAY_PHRASE.lower() not in said:
            update_gui(gui_queue, {"status": "Wrong phrase.", "color": "red"})
            return False
    except:
        update_gui(gui_queue, {"status": "Speech error.", "color": "red"})
        return False

    #wav_path = "temp.wav"
    #with open(wav_path, "wb") as f: f.write(audio.get_wav_data())
    #live_embed = encoder.embed_utterance(preprocess_wav(wav_path))
    #os.remove(wav_path)

    #saved_embed = pickle.loads(decrypt(open(VOICE_FILE, "rb").read()))
    #similarity = 1 - cosine(saved_embed, live_embed)

    #if similarity >= 0.82:
    #    update_gui(gui_queue, {"status": "Voice passed!", "color": "green"})
    #    return True
    #else:
    #    update_gui(gui_queue, {"status": "Voice mismatch.", "color": "red"})
    #    return False

# ========================
# Progressive Login (Threaded)
# ========================
def progressive_login(gui):
    gui_queue = gui.status_queue
    attempt = 1

    while True:
        update_gui(gui_queue, {"attempt": f"Attempt {attempt}"})
        update_gui(gui_queue, {"progress": 0})

        if attempt <= 3:
            update_gui(gui_queue, {"instructions": "Voice Only"})
            if voice_full_verification(gui_queue):
                return True

        elif attempt <= 5:
            update_gui(gui_queue, {"instructions": "Voice + Face required."})
            if voice_full_verification(gui_queue) and face_liveness_and_recognition(gui_queue):
                return True

        else:
            update_gui(gui_queue, {"instructions": "Full security. Checking lock..."})
            if os.path.exists(LOCK_FILE):
                lock_time = datetime.fromtimestamp(os.path.getmtime(LOCK_FILE))
                if datetime.now() < lock_time + timedelta(minutes=10):
                    wait = (lock_time + timedelta(minutes=10) - datetime.now()).seconds
                    update_gui(gui_queue, {"status": f"Locked. Wait {wait//60 + 1} mins.", "color": "red"})
                    time.sleep(wait + 5)
                os.remove(LOCK_FILE)

            update_gui(gui_queue, {"instructions": "All layers required."})
            if voice_full_verification(gui_queue) and face_liveness_and_recognition(gui_queue):
                if os.path.exists(LOCK_FILE): os.remove(LOCK_FILE)
                return True
            else:
                open(LOCK_FILE, "w").close()
                update_gui(gui_queue, {"status": "Locked for 10 mins.", "color": "red"})
                attempt = 5  # Reset for next cycle

        update_gui(gui_queue, {"status": "Denied. Try again.", "color": "red"})
        attempt += 1
        time.sleep(2)  # Anti-brute force

# ========================
# AI Integration (Threaded Grok-4)
# ========================
#client = Grok(api_key=GROK_API_KEY)
#conversation_history = [
#    {"role": "system", "content": f"You are JARVIS – unhackable AI. Date: {datetime.now().strftime('%B %d, %Y')} Loyal, sarcastic, intelligent."}
#]
#
#def ask_jarvis(question, chat_queue):
#    conversation_history.append({"role": "user", "content": question})
#    response = client.chat.completions.create(
#        model="grok-4",
#        messages=conversation_history,
#        temperature=0.8,
#        max_tokens=1500
#    )
#    answer = response.choices[0].message.content
#    conversation_history.append({"role": "assistant", "content": answer})
#    update_gui(chat_queue, f"JARVIS: {answer}")
#    speak(answer)

# ========================
# Voice Loop (Optimized: Threaded, Low latency)
# ========================
def voice_loop(chat_queue, status_queue):
    r = sr.Recognizer()
    r.energy_threshold = 300  # Optimized: Lower for faster detection
    while app.listening:
        try:
            with sr.Microphone() as source:
                r.adjust_for_ambient_noise(source, duration=0.3)
                update_gui(status_queue, {"status": "Listening...", "color": "green"})
                audio = r.listen(source, timeout=10, phrase_time_limit=12)
            text = r.recognize_google(audio).lower()
            update_gui(chat_queue, f"You: {text}")

            #if "jarvis" in text or len(text) > 5:  # Wake or long phrase
            #    threading.Thread(target=ask_jarvis, args=(text, chat_queue), daemon=True).start()

            # Process OS commands (from previous)
            process_command(text)
            def lock_windows():
                speak("Locking the computer")
                os.system("rundll32.exe user32.dll,LockWorkStation")

            def shutdown():
                speak("Shutting down the computer")
                os.system("shutdown /s /t 1")

            def restart():
                speak("Restarting the computer")
                os.system("shutdown /r /t 1")

            def sleep_pc():
                speak("Putting computer to sleep")
                os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")

            def open_app(app_name):
                speak(f"Opening {app_name}")
                try:
                    os.startfile(app_name)
                except:
                    pyautogui.press('win')
                    time.sleep(1)
                    pyautogui.write(app_name)
                    time.sleep(1)
                    pyautogui.press('enter')

            def switch_desktop(direction="next"):
                # Virtual Desktop switching using Ctrl + Win + Left/Right
                speak(f"Switching to {direction} desktop")
                pyautogui.hotkey('ctrl', 'win', 'right' if direction == "next" else 'left')

            def volume_up():
                speak("Volume up")
                for _ in range(5): pyautogui.press('volumeup')

            def volume_down():
                speak("Volume down")
                for _ in range(5): pyautogui.press('volumedown')

            def mute():
                speak("Muting volume")
                pyautogui.press('volumemute')

            def take_screenshot():
                speak("Taking screenshot")
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                pyautogui.screenshot(f"screenshot_{timestamp}.png")

            def empty_recycle_bin():
                speak("Emptying recycle bin")
                try:
                    import winshell 
                    winshell.recycle_bin().empty(confirm=False, show_progress=False, sound=False)
                    speak("Recycle bin emptied")
                except ImportError:
                    speak("Please install winshell module")

            def open_website(site):
                speak(f"Opening {site}")
                import webbrowser
                webbrowser.open(f"https://{site}.com")

            # Main command processor
            def process_command(query):
                query = query.lower()

                match query:
                    case "lock":
                        lock_windows()

                    case "shutdown" :
                        shutdown()

                    case "restart":
                        restart()

                    case "sleep" | "hibernate":
                        sleep_pc()

                    case "open ":
                        app = query.replace("open ", "").strip()
                        # Common app mappings
                        app_map = {
                            "notepad": r"C:\Windows\system32\notepad.exe",
                            "calculator": "calc",
                            "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                            "vscode": r"C:\Users\{}\AppData\Local\Programs\Microsoft VS Code\Code.exe".format(os.getlogin()),
                            "paint": "mspaint",
                            "command prompt": "cmd",
                            "task manager": "taskmgr"
                        }
                        path = app_map.get(app, app)
                        open_app(path)

                    case "switch desktop" | "next desktop":
                        switch_desktop("next")
                    case "previous desktop":
                        switch_desktop("previous")

                    case "volume up":
                        volume_up()
                    case "volume down":
                        volume_down()
                    case "mute":
                        mute()

                    case "screenshot":
                        take_screenshot()

                    case "empty recycle bin"  :
                        empty_recycle_bin()

                    case "open youtube"  :
                        open_website("youtube")
                    case "open google"  :
                        open_website("google")
                    case "open github"  :
                        open_website("github")

                    case "exit"   | "quit"   | "bye"  :
                        speak("Goodbye! Have a great day!")
                        return False

                    case _:
                        speak("Sorry, I don't know that command yet.")

                return True  # Add your lock/open_app etc. here

        except sr.WaitTimeoutError:
            pass
        except Exception as e:
            update_gui(status_queue, {"status": f"Error: {str(e)}", "color": "red"})

# ========================
# First-Time Setup (Stub – Implement as needed)
# ========================
def first_time_setup():
    speak("First time setup beginning.")
    # Register face
    #if face_liveness_and_recognition():  # This will auto-register if missing
    #    with open(FACE_FILE, "wb") as f:
    #        f.write(encrypt(pickle.dumps(face_recognition.face_encodings(cv2.cvtColor(cv2.VideoCapture(0).read()[1], cv2.COLOR_BGR2RGB))[0])))
    # Register voice
    speak("Now enrolling your voice. Say the phrase 3 times.")
    # ... (same as previous register_voice_secure, omitted for brevity)
    speak("Fortress ready. Only you can enter now.")

# ========================
# Main
# ========================
if __name__ == "__main__":
    app = JarvisGUI()
    login_thread = threading.Thread(target=progressive_login, args=(app,))
    login_thread.start()

    while login_thread.is_alive():
        app.update()  # Keep GUI responsive during login

    app.show_dashboard()
    app.mainloop()

    speak("Jarvis Activated. Say Hey Jarvis to wake up!")
    while True:
        query = listen().lower()

        if "Hey Jarvis" or "Hello Jarvis" or "wake up":
            speak("How can I help you?")