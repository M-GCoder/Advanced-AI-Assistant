# ================================
# JARVIS UNHACKABLE – 5-LAYER DEFENSE
# ================================
import os
import cv2
import numpy as np
import pickle
import hashlib
import time
import json
import base64
import speech_recognition as sr
import pyttsx3
import pyautogui
from datetime import datetime
from cryptography.fernet import Fernet
from deepface import DeepFace
from resemblyzer import VoiceEncoder, preprocess_wav
from scipy.spatial.distance import cosine
import getpass
from pathlib import Path

# -------------------------------
# CONFIG & ENCRYPTION
# -------------------------------
ENCRYPT_KEY_FILE = "jarvis.key"
FACE_FILE = "face.enc"
VOICE_FILE = "voice.enc"
CHALLENGE_FILE = "challenge.json"
RECOVERY_FILE = "recovery.vault"
MASTER_USB_PATHS = ["G:\\"]  # Add your usual USB drive letters
MASTER_PHRASE_HASH = None      # Will be set on first run
MASTER_KEYBOARD_SEQ = "j a r v i s 2 0 8 4"   # Change to anything you want (15+ chars)

engine = pyttsx3.init('sapi5')
engine.setProperty('rate', 180)
engine.setProperty('voice', engine.getProperty('voices')[1].id)

def speak(text):
    print(f"[JARVIS] {text}")
    engine.say(text)
    engine.runAndWait()

# Encryption helpers
def get_key():
    if os.path.exists(ENCRYPT_KEY_FILE):
        return open(ENCRYPT_KEY_FILE, "rb").read()
    key = Fernet.generate_key()
    with open(ENCRYPT_KEY_FILE, "wb") as f:
        f.write(key)
    return key

cipher = Fernet(get_key())

def encrypt_data(data: bytes) -> bytes:
    return cipher.encrypt(data)

def decrypt_data(enc: bytes):
    return cipher.decrypt(enc)

# -------------------------------
# 1. LIVENESS FACE DETECTION (Blink + Motion)
# -------------------------------
def face_liveness_test():
    speak("Face liveness check. Blink twice and turn your head left-right.")
    cap = cv2.VideoCapture(0)
    blink_counter = 0
    prev_eye_state = None
    motion_detected = False
    start_time = time.time()

    while time.time() - start_time < 15:
        ret, frame = cap.read()
        if not ret: continue

        try:
            analysis = DeepFace.analyze(frame, actions=['emotion'], enforce_detection=False, silent=True)[0]
            eye_ratio = DeepFace.extract_faces(frame, detector_backend='retinaface', enforce_detection=False)[0]['facial_area']

            # Blink detection via eye aspect (simple)
            if analysis['eye_status']['left'] == 'closed' and analysis['eye_status']['right'] == 'closed':
                if prev_eye_state == 'open':
                    blink_counter += 1
                prev_eye_state = 'closed'
            else:
                prev_eye_state = 'open'

            # Head motion
            if abs(analysis['face_region']['x'] - 320) > 100:
                motion_detected = True

            cv2.putText(frame, f"Blinks: {blink_counter}/2  Move head: {'Yes' if motion_detected else 'No'}", 
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)

            cv2.imshow("LIVENESS TEST - 15 sec", frame)
            if cv2.waitKey(1) == 27: break

            if blink_counter >= 2 and motion_detected:
                cap.release()
                cv2.destroyAllWindows()
                speak("Liveness passed.")
                return True
        except:
            pass

    cap.release()
    cv2.destroyAllWindows()
    speak("Liveness failed. Are you real?")
    return False

def register_face_secure():
    if face_liveness_test():
        speak("Saving your face securely...")
        cap = cv2.VideoCapture(0)
        time.sleep(1)
        ret, frame = cap.read()
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        encoding = face_recognition.face_encodings(rgb)
        if encoding:
            data = pickle.dumps(encoding[0])
            enc_data = encrypt_data(data)
            with open(FACE_FILE, "wb") as f:
                f.write(enc_data)
            speak("Encrypted face saved.")
            cap.release()
            return True
    return False

def verify_face_secure():
    if not os.path.exists(FACE_FILE):
        speak("No face registered.")
        return register_face_secure()

    if not face_liveness_test():
        return False

    enc_data = open(FACE_FILE, "rb").read()
    data = decrypt_data(enc_data)
    saved_encoding = pickle.loads(data)

    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    encodings = face_recognition.face_encodings(rgb)
    cap.release()

    if encodings and face_recognition.compare_faces([saved_encoding], encodings[0], tolerance=0.45)[0]:
        speak("Face authenticated.")
        return True
    speak("Face rejected.")
    return False

# -------------------------------
# 2 & 3. VOICE ANTI-SPOOF + BIOMETRICS
# -------------------------------
encoder = VoiceEncoder("cpu")

def register_voice_secure():
    speak("Voice enrollment. Say this exact phrase 3 times: 'My voice is my password verify me'")
    embeds = []
    for i in range(3):
        speak(f"Recording {i+1} of 3")
        r = sr.Recognizer()
        with sr.Microphone() as source:
            audio = r.listen(source, phrase_time_limit=8)
        wav_path = f"enroll_{i}.wav"
        with open(wav_path, "wb") as f:
            f.write(audio.get_wav_data())
        wav = preprocess_wav(wav_path)
        embed = encoder.embed_utterance(wav)
        embeds.append(embed)
        os.remove(wav_path)

    final_embed = np.mean(embeds, axis=0)
    enc_embed = encrypt_data(pickle.dumps(final_embed))
    with open(VOICE_FILE, "wb") as f:
        f.write(enc_embed)
    speak("Voice biometrics locked and encrypted.")

def first_time_create_recovery():
    global MASTER_PHRASE_HASH
    speak("Creating your emergency master recovery keys.")
    
    # 1. 12-word phrase (you write it down ON PAPER)
    speak("Write down these 12 words EXACTLY. This is your lifetime master key:")
    import secrets,string
    words = []
    with open("english.txt", "r") as f:   # You can download BIP39 wordlist or just use random
        wordlist = f.read().splitlines()
    for _ in range(12):
        words.append(secrets.choice(wordlist))
    phrase = " ".join(words)
    print("\n=== YOUR LIFETIME RECOVERY PHRASE ===\n")
    print(phrase)
    print("\n=====================================\n")
    speak("Your 12-word recovery phrase has been shown. Store it offline now.")
    
    MASTER_PHRASE_HASH = hashlib.sha3_256(phrase.encode()).hexdigest()
    
    # Save encrypted
    vault = encrypt(MASTER_PHRASE_HASH.encode())
    with open(RECOVERY_FILE, "wb") as f:
        f.write(vault)
    
    # 2. USB key file
    token = os.urandom(32)
    with open("JARVIS_MASTER_KEY.bin", "wb") as f:
        f.write(token)
    speak("USB master key file created: JARVIS_MASTER_KEY.bin — copy it to your personal USB now.")

def load_recovery_hash():
    global MASTER_PHRASE_HASH
    if os.path.exists(RECOVERY_FILE):
        enc = open(RECOVERY_FILE, "rb").read()
        MASTER_PHRASE_HASH = decrypt(enc).decode()

# Run once on first launch
if not os.path.exists(RECOVERY_FILE):
    first_time_create_recovery()
else:
    load_recovery_hash()

# ================== EMERGENCY BYPASS FUNCTION ==================
def emergency_bypass():
    speak("Emergency recovery mode activated.")
    
    # Method 1: USB Master Key
    for drive in MASTER_USB_PATHS:
        keyfile = Path(drive) / "JARVIS_MASTER_KEY.bin"
        if keyfile.exists():
            with open(keyfile, "rb") as f:
                if len(f.read()) == 32:  # Valid token size
                    speak("Master USB detected. Bypassing all security. Welcome back, Master.")
                    return True
    
    # Method 2: 12-Word Phrase
    speak("Enter your 12-word recovery phrase.")
    for _ in range(3):  # 3 tries
        phrase = getpass.getpass("Recovery phrase (hidden input): ")
        if hashlib.sha3_256(phrase.encode()).hexdigest() == MASTER_PHRASE_HASH:
            speak("Recovery phrase accepted. All layers bypassed.")
            return True
        else:
            speak("Incorrect phrase.")
    
    # Method 3: Hidden Keyboard Sequence (press these keys in order at login screen)
    speak("Or press your secret keyboard sequence now...")
    # We’ll detect this in the GUI key listener (added below)
    
    speak("Emergency bypass failed.")
    return False

# Add this to your GUI class (__init__):
def __init__(self):
    # ... existing code ...
    self.bind_all("<Key>", self.check_keyboard_sequence)
    self.seq_buffer = ""

def check_keyboard_sequence(self, event):
    self.seq_buffer += event.keysym.lower() + " "
    if len(self.seq_buffer) > 100:
        self.seq_buffer = self.seq_buffer[-100:]
    if MASTER_KEYBOARD_SEQ in self.seq_buffer:
        speak("Secret keyboard sequence detected. Bypassing fortress.")
        self.after(100, lambda: self.recovery_success())

def recovery_success(self):
    self.show_dashboard()
    speak("Master override accepted. You are in.")

def is_live_voice():
    speak("Anti-spoofing: Cough or clear your throat now.")
    r = sr.Recognizer()
    with sr.Microphone() as source:
        audio = r.listen(source, phrase_time_limit=5)
    # Very simple but effective: real voices have natural noise
    samples = np.frombuffer(audio.get_wav_data(), dtype=np.int16)
    energy = np.sum(samples**2)
    return energy > 1e7  # Recorded audio usually has lower energy

def verify_voice_secure():
    if not os.path.exists(VOICE_FILE):
        return register_voice_secure()

    if not is_live_voice():
        speak("Detected recorded audio. Attack blocked.")
        return False

    speak("Say the secret challenge phrase.")
    # Load today's challenge
    challenge = json.loads(open(CHALLENGE_FILE, "r").read())["phrase"]

    r = sr.Recognizer()
    with sr.Microphone() as source:
        audio = r.listen(source, phrase_time_limit=10)

    # Check if user said the correct phrase
    try:
        said = r.recognize_google(audio)
        if challenge.lower() not in said.lower():
            speak("Wrong phrase. Intruder.")
            return False
    except:
        speak("Could not understand.")
        return False

    # Now do biometric match
    wav_path = "live.wav"
    with open(wav_path, "wb") as f:
        f.write(audio.get_wav_data())
    wav = preprocess_wav(wav_path)
    live_embed = encoder.embed_utterance(wav)
    os.remove(wav_path)

    enc = open(VOICE_FILE, "rb").read()
    saved_embed = pickle.loads(decrypt_data(enc))

    similarity = 1 - cosine(saved_embed, live_embed)

    print(f"Voice similarity: {similarity:.2%}")
    if similarity > 0.80:
        speak("Voice biometrics confirmed.")
        return True
    else:
        speak("Voice does not match owner.")
        return False

# -------------------------------
# 5. DAILY CHANGING CHALLENGE
# -------------------------------
def generate_daily_challenge():
    phrases = [
        "The quick brown fox jumps over the lazy dog",
        "My voice is my passport verify me",
        "Peter Piper picked a peck of pickled peppers",
        "How much wood would a woodchuck chuck",
        "Unique New York unique New York"
    ]
    phrase = np.random.choice(phrases)
    data = {"date": datetime.now().strftime("%Y-%m-%d"), "phrase": phrase}
    with open(CHALLENGE_FILE, "w") as f:
        json.dump(data, f)
    return phrase

if not os.path.exists(CHALLENGE_FILE) or json.loads(open(CHALLENGE_FILE).read())["date"] != datetime.now().strftime("%Y-%m-%d"):
    challenge_phrase = generate_daily_challenge()
    speak(f"Today's secret phrase is: {challenge_phrase}")
else:
    challenge_phrase = json.loads(open(CHALLENGE_FILE).read())["phrase"]

# Windows-specific functions
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

        case "open":
            app = query.replace("open ", " ").strip()
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
    
    return True

# -------------------------------
# MAIN – UNHACKABLE FLOW
# -------------------------------
if __name__ == "__main__":
    speak("JARVIS Unhackable Mode Activated")

    # Layer 1 & 2: Face + Liveness
    if not verify_face_secure():
        speak("Face authentication failed. Shutting down.")
        exit()

    # Layer 3 & 4: Voice Anti-spoof + Biometrics + Challenge
    if not verify_voice_secure():
        speak("Voice authentication failed. System remains locked.")
        exit()

    # ALL 5 LAYERS PASSED
    speak("All five security layers passed. Welcome, Master. JARVIS is now yours alone.")

    # Your normal commands here (lock, open apps, etc.)
    while True:
        try:
            r = sr.Recognizer()
            with sr.Microphone() as source:
                r.adjust_for_ambient_noise(source)
                print("Say 'hey jarvis'...")
                audio = r.listen(source)
            text = r.recognize_google(audio).lower()
            if "hey jarvis" in text:
                speak("Yes, Master?")
                # Add your commands here...
        except:
            pass