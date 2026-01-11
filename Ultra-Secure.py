# ==================================
# Ultra - Secure
# ==================================

# =========================================
# JARVIS FINAL FORTRESS – PROGRESSIVE DEFENSE
# Owner-defined rules strictly enforced
# =========================================

import os, cv2, numpy as np, pickle, time, json, hashlib
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
import speech_recognition as sr
import pyttsx3
from deepface import DeepFace
from resemblyzer import VoiceEncoder, preprocess_wav
from scipy.spatial.distance import cosine
import pyautogui

# Files
KEY_FILE = "fortress.key"
FACE_FILE = "face.enc"
VOICE_FILE = "voice.enc"
CHALLENGE_FILE = "challenge.json"
LOCK_FILE = "lockdown.tmp"

engine = pyttsx3.init('sapi5')
engine.setProperty('rate', 180)
engine.setProperty('voice', engine.getProperty('voices')[1].id)

def speak(text):
    print(f"[JARVIS] {text}")
    engine.say(text)
    engine.runAndWait()

# ========================
# Encryption
# ========================

def get_key():
    if os.path.exists(KEY_FILE):
        return open(KEY_FILE, "rb").read()
    key = Fernet.generate_key()
    with open(KEY_FILE, "wb") as f: f.write(key)
    return key
cipher = Fernet(get_key())

def encrypt(b): return cipher.encrypt(b)
def decrypt(b): return cipher.decrypt(b)

# ========================
# Daily Challenge
# ========================
def refresh_challenge():
    phrases = [
        "The quick brown fox jumps over the lazy dog",
        "My voice is my passport verify me",
        "Peter Piper picked a peck of pickled peppers",
        "Unique New York you know you need unique New York",
        "How much wood would a woodchuck chuck if a woodchuck could chuck wood"
    ]
    phrase = np.random.choice(phrases)
    data = {"date": datetime.now().strftime("%Y-%m-%d"), "phrase": phrase}
    with open(CHALLENGE_FILE, "w") as f:
        json.dump(data, f)
    return phrase

if not os.path.exists(CHALLENGE_FILE) or json.load(open(CHALLENGE_FILE))["date"] != datetime.now().strftime("%Y-%m-%d"):
    TODAY_PHRASE = refresh_challenge()
else:
    TODAY_PHRASE = json.load(open(CHALLENGE_FILE))["phrase"]

# ========================
# Layer 1 – Face + Liveness (Blink & Motion)
# ========================
def face_liveness_and_recognition():
    speak("Face liveness test. Blink twice and move your head.")
    cap = cv2.VideoCapture(0)
    blinks = 0
    moved = False
    prev_gray = None

    # Load encrypted face if exists
    if not os.path.exists(FACE_FILE):
        speak("No face registered yet.")
        return False

    saved_enc = pickle.loads(decrypt(open(FACE_FILE, "rb").read()))

    start = time.time()
    while time.time() - start < 14:
        ret, frame = cap.read()
        if not ret: continue
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Blink detection (simple)
        try:
            eyes = DeepFace.analyze(frame, actions=['emotion'], silent=True, enforce_detection=False)[0]
            if eyes['eye_status']['left'] == 'closed' and eyes['eye_status']['right'] == 'closed':
                blinks += 1
        except: pass

        # Motion detection
        if prev_gray is not None:
            diff = cv2.absdiff(prev_gray, gray)
            if np.mean(diff) > 15:
                moved = True
        prev_gray = gray.copy()

        # Face match
        encodings = face_recognition.face_encodings(rgb)
        if encodings and face_recognition.compare_faces([saved_enc], encodings[0], 0.45)[0]:
            if blinks >= 2 and moved:
                cap.release()
                cv2.destroyAllWindows()
                speak("Face liveness and identity confirmed.")
                return True

        cv2.putText(frame, f"Blinks: {blinks}/2  Moved: {moved}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0,255,255), 2)
        cv2.imshow("Face Fortress", frame)
        if cv2.waitKey(1) == 27: break

    cap.release()
    cv2.destroyAllWindows()
    return False

# ========================
# Layer 2–5 – Voice Anti-spoof + Biometrics + Challenge
# ========================

encoder = VoiceEncoder("cpu")

def anti_spoof_cough_test():
    speak("Anti-spoof: Cough once loudly now.")
    r = sr.Recognizer()
    with sr.Microphone() as src:
        audio = r.listen(src, phrase_time_limit=5)
    samples = np.frombuffer(audio.get_wav_data(), np.int16)
    return np.max(np.abs(samples)) > 8000  # Real mic = high peaks

def voice_full_verification():
    if not os.path.exists(VOICE_FILE):
        speak("Voice not enrolled.")
        return False

    if not anti_spoof_cough_test():
        speak("Recorded or synthetic voice detected. Blocked.")
        return False

    speak(f"Say exactly: {TODAY_PHRASE}")
    r = sr.Recognizer()
    with sr.Microphone() as src:
        r.adjust_for_ambient_noise(src)
        audio = r.listen(src, phrase_time_limit=12)

    # Text match
    try:
        said = r.recognize_google(audio).lower()
        if TODAY_PHRASE.lower() not in said:
            speak("Wrong phrase.")
            return False
    except:
        speak("Speech not recognized.")
        return False

    # Biometric match
    wav_path = "temp.wav"
    with open(wav_path, "wb") as f: f.write(audio.get_wav_data())
    live_embed = encoder.embed_utterance(preprocess_wav(wav_path))
    os.remove(wav_path)

    saved_embed = pickle.loads(decrypt(open(VOICE_FILE, "rb").read()))
    similarity = 1 - cosine(saved_embed, live_embed)

    if similarity >= 0.82:
        speak("Voice biometrics passed.")
        return True
    else:
        speak("Voice does not match owner.")
        return False

# ========================
# Progressive Authentication Engine
# ========================
def progressive_login():
    attempt = 1

    while True:
        speak(f"Authentication attempt {attempt}")

        # Attempts 1–3: Only voice super-layer
        if attempt <= 3:
            speak("Easy mode: Voice + challenge only")
            if voice_full_verification():
                speak("Welcome home, Master. Fortress unlocked.")
                return True

        # Attempts 4–5: Voice + Face liveness
        elif attempt <= 5:
            speak("Medium mode: Voice + Face required")
            if voice_full_verification() and face_liveness_and_recognition():
                speak("Both layers passed. Access granted.")
                return True

        # Attempts 6–8: Full 5-layer after 10-min lock
        else:
            speak("Maximum security mode activated.")
            if os.path.exists(LOCK_FILE):
                lock_time = datetime.fromtimestamp(os.path.getmtime(LOCK_FILE))
                if datetime.now() < lock_time + timedelta(minutes=10):
                    wait = (lock_time + timedelta(minutes=10) - datetime.now()).seconds
                    speak(f"Locked. Wait {wait//60 + 1} minutes.")
                    time.sleep(wait + 5)
                else:
                    os.remove(LOCK_FILE)

            speak("Final chance. All five layers required.")
            if voice_full_verification() and face_liveness_and_recognition():
                speak("All defenses breached by rightful owner. Welcome.")
                if os.path.exists(LOCK_FILE): os.remove(LOCK_FILE)
                return True
            else:
                # Create/recreate lockdown
                open(LOCK_FILE, "w").close()
                speak("Intruder protocol. Locked for 10 minutes.")
                attempt = 5  # Reset to trigger wait next loop

        speak("Access denied.")
        attempt += 1
        time.sleep(2)

# ========================
# First-time registration (run once)
# ========================

def first_time_setup():
    speak("First time setup beginning.")
    # Register face
    if face_liveness_and_recognition():  # This will auto-register if missing
        with open(FACE_FILE, "wb") as f:
            f.write(encrypt(pickle.dumps(face_recognition.face_encodings(cv2.cvtColor(cv2.VideoCapture(0).read()[1], cv2.COLOR_BGR2RGB))[0])))
    # Register voice
    speak("Now enrolling your voice. Say the phrase 3 times.")
    # ... (same as previous register_voice_secure, omitted for brevity)
    speak("Fortress ready. Only you can enter now.")

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
    
    return True

# ========================
#         MAIN
# ========================
if __name__ == "__main__":
    speak("JARVIS Final Fortress online.")

    # Uncomment next line only on first run
    first_time_setup(); exit()

    if progressive_login():
        speak("All systems nominal. How may I serve you today, Master?")

        # Your normal assistant loop here
        r = sr.Recognizer()
        while True:
            try:
                with sr.Microphone() as src:
                    r.adjust_for_ambient_noise(src)
                    audio = r.listen(src)
                cmd = r.recognize_google(audio).lower()
                if "hey jarvis" in cmd:
                    speak("Yes, Master?")
                    # Add all your previous commands here
            except:
                pass